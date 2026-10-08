from copy import deepcopy

import pytest
from langgraph.types import Command

from ontoproduct.graph.execution import execute_agent
from ontoproduct.graph.state import initial_state
from ontoproduct.graph.workflow import build_workflow
from ontoproduct.schemas.product import ProductAttribute
from conftest import count_runs


@pytest.mark.parametrize(
    "documents", [[object()], [{"bad": float("nan")}], [ProductAttribute(value=1)]]
)
def test_initial_documents_must_be_serializable(documents):
    with pytest.raises((TypeError, ValueError)):
        initial_state(documents)


@pytest.mark.parametrize(
    "value,unit", [(float("nan"), "W"), (float("inf"), "W"), (1e308, "kW")]
)
def test_unit_conversion_rejects_nonfinite_and_overflow(ontology, value, unit):
    with pytest.raises(ValueError):
        ontology.normalize_unit(
            ontology.resolve_properties("BLDCMotor")["rated_power"], value, unit
        )


def test_human_conversion_overflow_is_repairable_not_unhandled(config):
    graph = build_workflow()
    graph.invoke(initial_state(), config)
    result = graph.invoke(
        Command(
            resume={
                "action": "EDIT",
                "edits": {
                    "attributes.rated_speed": {"value": 3000, "unit": "rpm"},
                    "attributes.rated_power": {"value": 1e308, "unit": "kW"},
                },
            }
        ),
        config,
    )
    assert result["__interrupt__"][0].value["review"]["decision"] == "NEEDS_FIX"
    assert not graph.get_state(config).values["validation_result"]["valid"]


def test_approve_with_hidden_edits_is_blocked(complete_registry, ontology, config):
    graph = build_workflow(complete_registry, ontology=ontology)
    graph.invoke(initial_state(), config)
    result = graph.invoke(
        Command(
            resume={
                "action": "APPROVE",
                "edits": {"attributes.rated_speed": {"value": 4000, "unit": "rpm"}},
            }
        ),
        config,
    )
    assert result["__interrupt__"]
    assert "final_product" not in graph.get_state(config).values
    assert (
        graph.invoke(Command(resume={"action": "APPROVE"}), config)["case_status"]
        == "REGISTERED"
    )


@pytest.mark.parametrize("retry_kind", ["RE_EXTRACT", "REMAP_ONTOLOGY"])
def test_graph_retry_after_human_edit_preserves_value(
    complete_registry, ontology, config, retry_kind
):
    agent = complete_registry.get("reviewer")
    original = agent.run
    requested = []

    def review(state):
        attr = state["normalized_product"]["attributes"]["rated_speed"]
        if attr.get("provenance") == "HUMAN" and not requested:
            requested.append(True)
            return {
                "review_result": {
                    "decision": retry_kind,
                    "reason": "Test adaptive replan",
                    "retry_fields": ["rated_voltage"]
                    if retry_kind == "RE_EXTRACT"
                    else [],
                    "can_register": False,
                }
            }
        return original(state)

    agent.run = review
    graph = build_workflow(complete_registry, ontology=ontology)
    graph.invoke(initial_state(), config)
    graph.invoke(
        Command(
            resume={
                "action": "EDIT",
                "edits": {"attributes.rated_speed": {"value": 4000, "unit": "rpm"}},
            }
        ),
        config,
    )
    state = graph.get_state(config).values
    attr = state["normalized_product"]["attributes"]["rated_speed"]
    assert (
        attr["value"] == 4000
        and attr["confidence"] is None
        and attr["provenance"] == "HUMAN"
    )
    assert state["manual_overrides"]["attributes.rated_speed"]["value"] == 4000
    assert "attributes.rated_speed" in state["locked_fields"]
    assert state["review_result"]["decision"] == "READY_FOR_HUMAN"
    counter = (
        "extraction_retry_count"
        if retry_kind == "RE_EXTRACT"
        else "ontology_retry_count"
    )
    assert state[counter] == 1
    assert (
        count_runs(state, "extraction" if retry_kind == "RE_EXTRACT" else "ontology")
        == 2
    )


def test_partial_multi_output_failure_drops_every_business_output(
    registry, paused_state
):
    original = registry.get("ontology").run

    def run(state):
        output = original(state)
        output["base_normalized_product"] = {"invalid": True}
        return output

    registry.get("ontology").run = run
    result = execute_agent(registry, "ontology", deepcopy(paused_state))
    assert result["agent_logs"][-1]["status"] == "error"
    assert "ontology_mapping" not in result and "base_normalized_product" not in result
