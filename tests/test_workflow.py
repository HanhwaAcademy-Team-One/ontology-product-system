from copy import deepcopy

import pytest
from langgraph.types import Command

from ontoproduct.graph.routing import route_review
from ontoproduct.graph.state import initial_state
from ontoproduct.graph.workflow import build_workflow
from ontoproduct.schemas.agent import CustomStreamEvent
from conftest import count_runs


@pytest.mark.parametrize("limit", [0, 1, 2])
def test_extraction_retry_limit_means_additional_runs(config, limit):
    graph = build_workflow()
    graph.invoke(initial_state(max_extraction_retries=limit), config)
    state = graph.get_state(config).values
    assert count_runs(state, "extraction") == limit + 1
    assert state["extraction_retry_count"] == limit
    assert state["review_result"]["decision"] == "NEEDS_FIX"
    assert not state["review_result"]["can_register"]
    assert state["review_result"]["reason"] == "Extraction retry limit reached."


@pytest.mark.parametrize("limit", [0, 1, 2])
def test_ontology_retry_limit_is_independent(complete_registry, ontology, config, limit):
    agent = complete_registry.get("ontology")
    original = agent.run

    def run(state):
        output = original(state)
        output["ontology_mapping"]["confidence"] = 0.5
        return output
    agent.run = run
    graph = build_workflow(complete_registry, ontology=ontology)
    graph.invoke(initial_state(max_ontology_retries=limit), config)
    state = graph.get_state(config).values
    assert count_runs(state, "ontology") == limit + 1
    assert state["ontology_retry_count"] == limit and state["extraction_retry_count"] == 0
    assert state["review_result"]["reason"] == "Ontology retry limit reached."
    assert state["case_status"] == "NEEDS_FIX"


def test_selective_retry_can_recover_missing_field(registry, ontology, config):
    agent = registry.get("extraction")
    original = agent.run

    def run(state):
        output = original(state)
        if state.get("review_result", {}).get("decision") == "RE_EXTRACT":
            output["extracted_product"]["attributes"]["rated_speed"] = {
                "value": 3000, "unit": "rpm", "confidence": 0.9, "provenance": "AI"}
        return output
    agent.run = run
    graph = build_workflow(registry, ontology=ontology)
    result = graph.invoke(initial_state(), config)
    assert result["__interrupt__"][0].value["review"]["can_register"]
    state = graph.get_state(config).values
    assert state["normalized_product"]["attributes"]["manufacturer"]["value"] == "ABC Motors"
    assert state["normalized_product"]["attributes"]["rated_power"]["value"] == 500
    assert state["extraction_retry_count"] == 1
    assert graph.invoke(Command(resume={"action": "APPROVE"}), config)["case_status"] == "REGISTERED"


@pytest.mark.parametrize("decision", ["RE_EXTRACT", "REMAP_ONTOLOGY", "NEEDS_FIX", "REJECT", "READY_FOR_HUMAN"])
def test_router_does_not_mutate_state(decision):
    state = initial_state()
    state["review_result"] = {"decision": decision, "can_register": decision == "READY_FOR_HUMAN",
                             "reason": "x", "retry_fields": []}
    before = deepcopy(state)
    route_review(state)
    assert state == before


def test_reviewer_rejection_has_no_registration(complete_registry, ontology, config):
    complete_registry.get("reviewer").run = lambda state: {"review_result": {
        "decision": "REJECT", "can_register": False, "reason": "Not a supported product", "retry_fields": []}}
    graph = build_workflow(complete_registry, ontology=ontology)
    result = graph.invoke(initial_state(), config)
    assert result["case_status"] == "REJECTED" and "final_product" not in result
    assert "__interrupt__" not in result


def test_custom_stream_reports_running_and_completion(config):
    graph = build_workflow()
    events = [data for mode, data in graph.stream(initial_state(), config, stream_mode=["custom", "updates"])
              if mode == "custom"]
    for data in events:
        CustomStreamEvent.model_validate(data)
    for execution_id in {data["execution_id"] for data in events}:
        pair = [data for data in events if data["execution_id"] == execution_id]
        assert [data["event"] for data in pair] == ["agent_started", "agent_finished"]
        assert pair[0]["status"] == "running" and pair[0]["execution_time"] is None
        assert pair[1]["execution_time"] >= 0
    assert [e["attempt"] for e in events if e["agent"] == "extraction" and e["event"] == "agent_finished"] == [1, 2]


def test_threads_keep_cases_separate(config):
    graph = build_workflow()
    other = {"configurable": {"thread_id": "case-two"}}
    graph.invoke(initial_state(case_id="case-one"), config)
    graph.invoke(initial_state(case_id="case-two"), other)
    graph.invoke(Command(resume={"action": "REJECT"}), config)
    assert graph.get_state(config).values["case_status"] == "REJECTED"
    assert graph.get_state(other).values["case_status"] == "NEEDS_FIX"
    assert graph.get_state(other).values["registration_case_id"] == "case-two"


@pytest.mark.parametrize("limit", [-1, True, 0.5])
def test_retry_limits_reject_invalid_values(limit):
    with pytest.raises(ValueError):
        initial_state(max_extraction_retries=limit)
