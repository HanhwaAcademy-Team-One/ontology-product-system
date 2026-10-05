import json

import pytest
from langgraph.types import Command

from ontoproduct.graph.state import initial_state
from ontoproduct.graph.workflow import build_workflow
from conftest import count_runs

EDIT_SPEED = {"action": "EDIT", "edits": {"attributes.rated_speed": {"value": 3000, "unit": "rpm"}}}


def test_real_interrupt_edit_revalidate_approve(config):
    graph = build_workflow()
    result = graph.invoke(initial_state(), config)
    assert result["__interrupt__"][0].value["kind"] == "human_review"
    state = graph.get_state(config).values
    assert state["case_status"] == "NEEDS_FIX"
    assert state["extraction_retry_count"] == 1
    assert count_runs(state, "extraction") == 2
    assert state["review_result"]["can_register"] is False
    assert "final_product" not in state
    result = graph.invoke(Command(resume=EDIT_SPEED), config)
    assert result["__interrupt__"][0].value["review"]["can_register"] is True
    state = graph.get_state(config).values
    assert count_runs(state, "validation") == count_runs(state, "duplicate") == 3
    assert state["normalized_product"]["attributes"]["rated_speed"]["provenance"] == "HUMAN"
    assert state["normalized_product"]["attributes"]["rated_speed"]["confidence"] is None
    assert "attributes.rated_speed" in state["locked_fields"]
    assert state["manual_overrides"]["attributes.rated_speed"]["value"] == 3000
    assert state["review_result"]["retry_fields"] == []
    result = graph.invoke(Command(resume={"action": "APPROVE"}), config)
    assert "__interrupt__" not in result
    assert result["case_status"] == "REGISTERED"
    assert result["final_product"]["attributes"]["rated_speed"]["value"] == 3000
    assert not graph.get_state(config).next
    json.dumps(graph.get_state(config).values, allow_nan=False)


@pytest.mark.parametrize("command", [
    {"action": "APPROVE"}, {"action": "EDIT"}, {"action": "INVALID"},
    {"action": "EDIT", "changed_class": "UnknownClass"},
    {"action": "EDIT", "edits": {"attributes.typo": {"value": 1}}},
    {"action": "EDIT", "edits": {"attributes.rated_speed": {"value": {"nested": 1}}}},
])
def test_invalid_resume_reinterrupts_without_registration(config, command):
    graph = build_workflow()
    graph.invoke(initial_state(), config)
    result = graph.invoke(Command(resume=command), config)
    assert result["__interrupt__"]
    state = graph.get_state(config).values
    assert state["case_status"] == "NEEDS_FIX" and "final_product" not in state
    assert state["human_review"]["feedback"]
    graph.invoke(Command(resume=EDIT_SPEED), config)
    result = graph.invoke(Command(resume={"action": "APPROVE"}), config)
    assert result["case_status"] == "REGISTERED"


def test_reject_stops(config):
    graph = build_workflow()
    graph.invoke(initial_state(), config)
    result = graph.invoke(Command(resume={"action": "REJECT"}), config)
    assert result["case_status"] == "REJECTED"
    assert "final_product" not in result and not graph.get_state(config).next


def test_other_thread_does_not_resume_original(config):
    graph = build_workflow()
    graph.invoke(initial_state(), config)
    other = {"configurable": {"thread_id": "different-thread"}}
    assert not graph.get_state(other).values
    assert graph.get_state(config).next == ("human_review",)
