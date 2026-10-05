from threading import Barrier

import pytest
from langgraph.types import Command

from ontoproduct.graph.state import initial_state
from ontoproduct.graph.workflow import build_workflow
from ontoproduct.schemas.error import unresolved_errors
from conftest import count_runs, fail_once


def test_branches_execute_concurrently_and_join_once(complete_registry, ontology, config):
    barrier = Barrier(2, timeout=5)
    for name in ("validation", "duplicate"):
        agent = complete_registry.get(name)
        original = agent.run

        def run(state, original=original):
            barrier.wait()
            return original(state)
        agent.run = run
    graph = build_workflow(complete_registry, ontology=ontology)
    events = list(graph.stream(initial_state(), config, stream_mode="updates"))
    updates = [key for event in events for key in event if key != "__interrupt__"]
    assert updates.count("post_parallel_gate") == 1
    assert updates.index("post_parallel_gate") > max(updates.index("validation"), updates.index("duplicate"))
    state = graph.get_state(config).values
    assert count_runs(state, "validation") == count_runs(state, "duplicate") == 1
    assert state["error_events"] == []
    assert len(state["agent_logs"]) == 12
    assert state["case_status"] == "READY_FOR_HUMAN"


@pytest.mark.parametrize("failed", [("validation",), ("duplicate",), ("validation", "duplicate")])
def test_branch_errors_join_then_retry_entire_stage(complete_registry, ontology, config, failed):
    for name in failed:
        fail_once(complete_registry.get(name))
    graph = build_workflow(complete_registry, ontology=ontology)
    events = list(graph.stream(initial_state(), config, stream_mode="updates"))
    updates = [key for event in events for key in event if key != "__interrupt__"]
    assert updates.index("post_parallel_gate") > max(updates.index("validation"), updates.index("duplicate"))
    state = graph.get_state(config).values
    assert state["case_status"] == "ERROR"
    assert {e["stage"] for e in unresolved_errors(state["error_events"])} == set(failed)
    assert count_runs(state, "reviewer") == 0
    assert graph.get_state(config).next == ("error_handler",)
    result = graph.invoke(Command(resume={"action": "RETRY"}), config)
    assert result["__interrupt__"][0].value["kind"] == "human_review"
    state = graph.get_state(config).values
    assert count_runs(state, "validation") == count_runs(state, "duplicate") == 2
    assert count_runs(state, "ontology") == 1
    assert not unresolved_errors(state["error_events"])
    assert len(state["error_events"]) == 2 * len(failed)
    for error_id in {e["error_id"] for e in state["error_events"]}:
        assert [e["status"] for e in state["error_events"] if e["error_id"] == error_id] == ["OPEN", "RESOLVED"]
    assert count_runs(state, "reviewer") == 1


def test_parallel_nodes_never_write_shared_scalar_fields(complete_registry, ontology, paused_state):
    from ontoproduct.graph.nodes import WorkflowNodes
    nodes = WorkflowNodes(complete_registry, ontology)
    forbidden = {"case_status", "extraction_retry_count", "ontology_retry_count",
                 "review_result", "human_review", "normalized_product"}
    for name in ("validation", "duplicate"):
        assert not nodes.agent_node(name)(paused_state).keys() & forbidden
