from copy import deepcopy

from langgraph.types import Command

from ontoproduct.graph.execution import execute_agent
from ontoproduct.graph.nodes import WorkflowNodes
from ontoproduct.graph.state import initial_state
from ontoproduct.graph.workflow import build_workflow
from ontoproduct.services.normalization_service import (
    apply_overrides,
    merge_extraction_retry,
)
from conftest import count_runs
from test_human_interrupt import EDIT_SPEED


def test_targeted_retry_merge_preserves_metadata_unrequested_and_locked():
    existing = {
        "product_name": "Human product",
        "candidate_class": "BLDCMotor",
        "attributes": {
            "rated_power": {"value": 500},
            "rated_speed": {"value": 3000},
            "manufacturer": {"value": "ABC"},
        },
    }
    state = {
        "extracted_product": existing,
        "review_result": {
            "decision": "RE_EXTRACT",
            "retry_fields": ["rated_power", "rated_speed"],
        },
        "locked_fields": ["attributes.rated_speed"],
    }
    incoming = {
        "product_name": "Wrong name",
        "candidate_class": "Bearing",
        "attributes": {
            "rated_power": {"value": 600},
            "rated_speed": {"value": 1},
            "manufacturer": {"value": "Bad"},
        },
    }
    before = deepcopy(state)
    merged = merge_extraction_retry(state, incoming)
    assert merged["attributes"]["rated_power"]["value"] == 600
    assert merged["attributes"]["rated_speed"]["value"] == 3000
    assert merged["attributes"]["manufacturer"]["value"] == "ABC"
    assert (
        merged["product_name"] == "Human product"
        and merged["candidate_class"] == "BLDCMotor"
    )
    assert state == before


def test_ai_retries_do_not_overwrite_effective_human_value(registry, ontology, config):
    graph = build_workflow(registry, ontology=ontology)
    graph.invoke(initial_state(), config)
    graph.invoke(Command(resume=EDIT_SPEED), config)
    state = graph.get_state(config).values
    original = deepcopy(state)
    # Exercise both real registry agents again, then the exclusive writer node.
    state["review_result"] = {
        "decision": "RE_EXTRACT",
        "reason": "test",
        "retry_fields": ["rated_speed"],
        "can_register": False,
    }
    extraction = execute_agent(registry, "extraction", state)
    state["extracted_product"] = merge_extraction_retry(
        state, extraction["extracted_product"]
    )
    state.update(execute_agent(registry, "ontology", state))
    effective = apply_overrides(state, ontology)
    assert (
        effective["normalized_product"]["attributes"]["rated_speed"]
        == original["normalized_product"]["attributes"]["rated_speed"]
    )
    assert effective["manual_overrides"] == original["manual_overrides"]


def test_class_change_orphans_and_restores_overrides(registry, ontology, config):
    graph = build_workflow(registry, ontology=ontology)
    graph.invoke(initial_state(), config)
    graph.invoke(
        Command(
            resume={
                "action": "EDIT",
                "edits": {
                    "attributes.rated_speed": {"value": 3000, "unit": "rpm"},
                    "attributes.rated_voltage": {"value": 48, "unit": "V"},
                },
            }
        ),
        config,
    )
    result = graph.invoke(
        Command(
            resume={
                "action": "EDIT",
                "changed_class": "Bearing",
                "edits": {
                    "attributes.inner_diameter": {"value": 10, "unit": "mm"},
                    "attributes.outer_diameter": {"value": 20, "unit": "mm"},
                },
            }
        ),
        config,
    )
    assert result["__interrupt__"]
    state = graph.get_state(config).values
    assert state["normalized_product"]["product_class"] == "Bearing"
    assert state["orphaned_overrides"]["attributes.rated_voltage"]["value"] == 48
    assert "attributes.rated_voltage" not in state["manual_overrides"]
    assert "attributes.rated_voltage" in state["locked_fields"]
    assert (
        count_runs(state, "ontology") == 3
    )  # Two extraction passes, then class remapping.
    graph.invoke(
        Command(resume={"action": "EDIT", "changed_class": "BLDCMotor"}), config
    )
    state = graph.get_state(config).values
    assert state["normalized_product"]["attributes"]["rated_voltage"]["value"] == 48
    assert state["manual_overrides"]["attributes.rated_speed"]["value"] == 3000
    assert "attributes.inner_diameter" in state["orphaned_overrides"]


def test_human_units_are_canonicalized_without_fake_confidence(config):
    graph = build_workflow()
    graph.invoke(initial_state(), config)
    graph.invoke(
        Command(
            resume={
                "action": "EDIT",
                "edits": {
                    "attributes.rated_speed": {
                        "value": 3000,
                        "unit": "rpm",
                        "confidence": 1,
                    },
                    "attributes.rated_power": {"value": 0.6, "unit": "kW"},
                },
            }
        ),
        config,
    )
    state = graph.get_state(config).values
    power = state["normalized_product"]["attributes"]["rated_power"]
    assert (power["value"], power["unit"]) == (600, "W")
    assert power["provenance"] == "HUMAN" and power["confidence"] is None


def test_apply_overrides_is_pure(paused_state, ontology):
    before = deepcopy(paused_state)
    WorkflowNodes(None, ontology).apply_manual_overrides(paused_state)
    assert paused_state == before
