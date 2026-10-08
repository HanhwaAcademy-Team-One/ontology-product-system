import pytest
from langgraph.types import Command

from ontoproduct.graph.state import initial_state
from ontoproduct.graph.workflow import build_workflow
from ontoproduct.schemas.error import unresolved_errors
from conftest import count_runs, fail_once


@pytest.mark.parametrize(
    "name", ["parser", "extraction", "ontology", "reviewer", "registration"]
)
def test_real_error_interrupt_retry_resolves_same_error(
    complete_registry, ontology, config, name
):
    fail_once(complete_registry.get(name))
    graph = build_workflow(complete_registry, ontology=ontology)
    result = graph.invoke(initial_state(), config)
    if name == "registration":
        result = graph.invoke(Command(resume={"action": "APPROVE"}), config)
    assert result["__interrupt__"][0].value["kind"] == "error"
    state = graph.get_state(config).values
    error = unresolved_errors(state["error_events"])[0]
    assert error["stage"] == name and error["attempt"] == 1
    result = graph.invoke(Command(resume={"action": "RETRY"}), config)
    state = graph.get_state(config).values
    assert not unresolved_errors(state["error_events"])
    assert [
        e["status"] for e in state["error_events"] if e["error_id"] == error["error_id"]
    ] == ["OPEN", "RESOLVED"]
    assert count_runs(state, name) == 2
    assert state["extraction_retry_count"] == state["ontology_retry_count"] == 0
    if name == "registration":
        assert state["case_status"] == "REGISTERED"
    else:
        assert result["__interrupt__"][0].value["kind"] == "human_review"
        result = graph.invoke(Command(resume={"action": "APPROVE"}), config)
        assert result["case_status"] == "REGISTERED"


def test_failed_error_retry_preserves_each_open_event_then_resolves(
    registry, ontology, config
):
    agent = registry.get("parser")
    original = agent.run
    calls = []

    def run(state):
        calls.append(1)
        if len(calls) < 3:
            raise OSError("Still broken")
        return original(state)

    agent.run = run
    graph = build_workflow(registry, ontology=ontology)
    graph.invoke(initial_state(), config)
    graph.invoke(Command(resume={"action": "RETRY"}), config)
    state = graph.get_state(config).values
    assert len(unresolved_errors(state["error_events"])) == 2
    assert [e["attempt"] for e in state["error_events"]] == [1, 2]
    graph.invoke(Command(resume={"action": "RETRY"}), config)
    state = graph.get_state(config).values
    assert not unresolved_errors(state["error_events"])
    assert [e["status"] for e in state["error_events"]] == [
        "OPEN",
        "OPEN",
        "RESOLVED",
        "RESOLVED",
    ]
    assert count_runs(state, "parser") == 3


def test_stop_retains_unresolved_history(registry, ontology, config):
    fail_once(registry.get("parser"))
    graph = build_workflow(registry, ontology=ontology)
    graph.invoke(initial_state(), config)
    result = graph.invoke(Command(resume={"action": "STOP"}), config)
    assert result["case_status"] == "STOPPED" and "final_product" not in result
    assert len(unresolved_errors(result["error_events"])) == 1
    assert not graph.get_state(config).next


def test_invalid_error_command_remains_suspended(registry, ontology, config):
    fail_once(registry.get("parser"))
    graph = build_workflow(registry, ontology=ontology)
    graph.invoke(initial_state(), config)
    result = graph.invoke(Command(resume={"action": "APPROVE"}), config)
    assert result["__interrupt__"][0].value["kind"] == "error"
    assert len(unresolved_errors(graph.get_state(config).values["error_events"])) == 1
    graph.invoke(Command(resume={"action": "RETRY"}), config)
    assert not unresolved_errors(graph.get_state(config).values["error_events"])
