import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from ontoproduct.agents.ontology_agent import OntologyAgent
from ontoproduct.graph.execution import execute_agent
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.schemas.product import ProductAttribute
from ontoproduct.services.agent_errors import DocumentConflictError, OntologyClassificationError
from ontoproduct.services.evidence_service import evidence_candidates, is_conflict, pack_evidence
from ontoproduct.services.external_mapping_service import ExternalMappings
from ontoproduct.services.normalization_service import apply_overrides
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.services.validation_service import validate_product
from extraction_ontology_helpers import attribute, constant_transport, motor_response


def test_rule_motor_mapping_inheritance_units_and_input_contract(ontology):
    agent = OntologyAgent(ontology)
    state = {"extracted_product": motor_response()}
    before = deepcopy(state)
    result = agent.run(state)
    assert state == before and set(result) == {"ontology_mapping", "base_normalized_product"}
    mapping, product = result["ontology_mapping"], result["base_normalized_product"]
    assert mapping["product_class"] == "BLDCMotor" and mapping["confidence"] == 1
    assert set(mapping["required_properties"]) == {"manufacturer", "rated_voltage", "rated_power", "rated_speed"}
    assert product["attributes"]["rated_power"]["value"] == 600
    assert product["attributes"]["weight"]["value"] == 0.75
    assert product["attributes"]["rated_power"]["evidence"] == before["extracted_product"]["attributes"]["rated_power"]["evidence"]
    assert validate_product(product, mapping)["valid"]
    registry = mock_registry(ontology)
    registry.register(agent, replace=True)
    wrapped = execute_agent(registry, "ontology", state)
    assert wrapped["agent_logs"][-1]["status"] == "success" and not wrapped["error_events"]
    assert not agent.is_mock
    json.dumps(wrapped, allow_nan=False)


def test_bearing_signature_can_correct_candidate_and_aliases(ontology):
    extracted = {"product_name": "BR-6201", "candidate_class": "BLDCMotor", "attributes": {
        "내경": {"value": 12, "unit": "mm"}, "Outer Diameter": {"value": 32, "unit": "mm"}}}
    output = OntologyAgent(ontology).run({"extracted_product": extracted})
    assert output["ontology_mapping"]["product_class"] == "Bearing"
    assert set(output["base_normalized_product"]["attributes"]) == {"inner_diameter", "outer_diameter"}


def test_motor_rule_requires_support_and_does_not_blindly_reuse_candidate(ontology):
    extracted = motor_response()
    extracted["candidate_class"] = "Bearing"
    assert OntologyAgent(ontology).run({"extracted_product": extracted})["ontology_mapping"]["product_class"] == "Motor"
    with pytest.raises(OntologyClassificationError):
        OntologyAgent(ontology).run({"extracted_product": {"candidate_class": "BLDCMotor", "attributes": {}}})


def test_mixed_signatures_are_explicit_uncertainty(ontology):
    extracted = motor_response()
    extracted["attributes"].update({"inner_diameter": {"value": 12, "unit": "mm"}, "outer_diameter": {"value": 32, "unit": "mm"}})
    with pytest.raises(OntologyClassificationError):
        OntologyAgent(ontology).run({"extracted_product": extracted})


def test_manual_class_wins_without_model_call_and_stays_locked(ontology):
    transport = constant_transport({"product_class": "BLDCMotor", "confidence": 0.99})
    output = OntologyAgent(ontology, transport).run({"extracted_product": motor_response(), "manual_overrides": {"product_class": "Bearing"}, "locked_fields": ["product_class"]})
    assert output["ontology_mapping"]["product_class"] == "Bearing"
    assert output["ontology_mapping"]["confidence"] == 1
    assert not transport.calls
    with pytest.raises(ValueError, match="requires"):
        OntologyAgent(ontology).run({"extracted_product": motor_response(), "locked_fields": ["product_class"]})


@pytest.mark.parametrize("manual", ["Unknown", "", None, 42])
def test_invalid_manual_class_is_not_fallback(ontology, manual):
    with pytest.raises(ValueError):
        OntologyAgent(ontology).run({"extracted_product": motor_response(), "manual_overrides": {"product_class": manual}})


def test_llm_low_score_is_preserved_and_allowed_classes_are_explicit(ontology):
    transport = constant_transport({"product_class": "BLDCMotor", "confidence": 0.5})
    result = OntologyAgent(ontology, transport).run({"extracted_product": motor_response()})
    assert result["ontology_mapping"]["confidence"] == 0.5
    payload = transport.calls[0]["payload"]
    assert "BLDCMotor" in payload["allowed_classes"] and "Product" not in payload["allowed_classes"]
    assert "untrusted data" in payload["instructions"]
    assert payload["external_references"]["kW"]["uri"] == "http://qudt.org/vocab/unit/KiloW"


@pytest.mark.parametrize("selection", [
    {"product_class": None, "confidence": 0}, {"product_class": "Unknown", "confidence": 0.9},
    {"product_class": "Product", "confidence": 1}, {"product_class": "", "confidence": 0.9},
    {"product_class": "BLDCMotor"}, {"product_class": "BLDCMotor", "confidence": None},
    {"product_class": "BLDCMotor", "confidence": float("inf")},
    {"product_class": "BLDCMotor", "confidence": True},
    {"product_class": "BLDCMotor", "confidence": "0.9"},
])
def test_invalid_llm_selection_is_error(ontology, selection):
    with pytest.raises((OntologyClassificationError, ValidationError)):
        OntologyAgent(ontology, constant_transport(selection)).run({"extracted_product": motor_response()})


def test_unsupported_unit_is_kept_for_validation(ontology):
    extracted = motor_response()
    extracted["attributes"]["rated_power"]["unit"] = "hp"
    output = OntologyAgent(ontology).run({"extracted_product": extracted})
    power = output["base_normalized_product"]["attributes"]["rated_power"]
    assert power["value"] == 0.6 and power["unit"] == "hp"
    validation = validate_product(output["base_normalized_product"], output["ontology_mapping"])
    assert any(i["code"] == "UNIT" for i in validation["issues"])


def speed_conflict():
    candidates = [ProductAttribute.model_validate(attribute(v, "rpm", evidence=f"Speed: {v}", source_file=f"{v}.pdf", page=2)) for v in (3000, 3200)]
    return pack_evidence(candidates, conflict=True).model_dump(mode="json")


def conflicting_motor():
    extracted = motor_response()
    extracted["attributes"]["rated_speed"] = speed_conflict()
    return extracted


def test_required_conflict_and_all_candidate_sources_survive_ontology(ontology):
    result = OntologyAgent(ontology).run({"extracted_product": conflicting_motor()})
    attr = ProductAttribute.model_validate(result["base_normalized_product"]["attributes"]["rated_speed"])
    assert is_conflict(attr) and attr.value is None
    assert {a.source_file for a in evidence_candidates(attr)} == {"3000.pdf", "3200.pdf"}


@pytest.mark.parametrize("mode", ["manual", "llm", "rule"])
def test_final_class_change_cannot_hide_outside_conflict(ontology, mode):
    extracted = conflicting_motor()
    state = {"extracted_product": extracted}
    transport = None
    if mode == "manual":
        state["manual_overrides"] = {"product_class": "Motor"}
        state["locked_fields"] = ["product_class"]
    elif mode == "llm":
        transport = constant_transport({"product_class": "Motor", "confidence": 0.9})
    else:
        extracted["candidate_class"] = "Motor"
    with pytest.raises(DocumentConflictError, match="rated_speed"):
        OntologyAgent(ontology, transport).run(state)


def test_final_required_to_optional_change_is_rechecked():
    prop = {"type": "number", "canonical_unit": "rpm", "units": ["rpm"], "minimum": 0}
    ontology = OntologyService(definition={"classes": {
        "Required": {"required_properties": {"rated_speed": prop}},
        "Optional": {"parent": "Required", "optional_properties": {"rated_speed": prop}},
    }})
    with pytest.raises(DocumentConflictError):
        OntologyAgent(ontology).run({"extracted_product": {"candidate_class": "Required", "attributes": {"rated_speed": speed_conflict()}}, "manual_overrides": {"product_class": "Optional"}})


def test_alias_collision_becomes_conflict_instead_of_overwrite(ontology):
    extracted = motor_response()
    extracted["attributes"]["정격 출력"] = attribute(0.7, "kW", evidence="Power: 0.7 kW", source_file="other.pdf")
    output = OntologyAgent(ontology).run({"extracted_product": extracted})
    power = ProductAttribute.model_validate(output["base_normalized_product"]["attributes"]["rated_power"])
    assert is_conflict(power) and power.value is None
    extracted["attributes"]["Weight"] = attribute(800, "g", evidence="Weight: 800 g")
    with pytest.raises(DocumentConflictError, match="weight"):
        OntologyAgent(ontology).run({"extracted_product": extracted})


def test_valid_human_resolution_of_optional_conflict_respects_exclusive_graph_writer(ontology):
    extracted = motor_response()
    extracted["attributes"]["Weight"] = attribute(800, "g", evidence="Weight: 800 g")
    state = {"extracted_product": extracted, "manual_overrides": {"attributes.weight": {"value": 0.8, "unit": "kg"}}, "locked_fields": ["attributes.weight"]}
    state.update(OntologyAgent(ontology).run(state))
    assert state["base_normalized_product"]["attributes"]["weight"]["value"] is None
    effective = apply_overrides(state, ontology)["normalized_product"]["attributes"]["weight"]
    assert effective["value"] == 0.8 and effective["provenance"] == "HUMAN" and effective["confidence"] is None


@pytest.mark.parametrize("overrides", [{}, {"attributes.weight": {"value": None}}, {"attributes.weight": {"value": -1, "unit": "kg"}}, {"attributes.weight": {"value": 1, "unit": "hp"}}])
def test_lock_or_invalid_human_value_is_not_conflict_resolution(ontology, overrides):
    extracted = motor_response()
    extracted["attributes"]["Weight"] = attribute(800, "g", evidence="Weight: 800 g")
    with pytest.raises(DocumentConflictError):
        OntologyAgent(ontology).run({"extracted_product": extracted, "manual_overrides": overrides, "locked_fields": ["attributes.weight"]})


def test_orphaned_manual_value_cannot_resolve_outside_class_conflict(ontology):
    with pytest.raises(DocumentConflictError):
        OntologyAgent(ontology).run({"extracted_product": conflicting_motor(), "manual_overrides": {"product_class": "Motor", "attributes.rated_speed": {"value": 3000, "unit": "rpm"}}})


def test_external_references_are_verified_and_unknowns_excluded():
    mappings = ExternalMappings()
    assert len(mappings.verified()) == 12
    definition = mappings.catalog.model_dump(mode="json")
    definition["mappings"]["unverified"] = {"source": "iof", "relation": "reference", "status": "unverified", "uri": None, "note": "Unable to verify; excluded"}
    assert "unverified" not in ExternalMappings(definition=definition).verified()
    definition["mappings"]["unverified"]["status"] = "verified"
    with pytest.raises(ValidationError):
        ExternalMappings(definition=definition)
    definition = mappings.catalog.model_dump(mode="json")
    definition["mappings"]["manufacturer"]["relation"] = "equivalentProperty"
    with pytest.raises(ValidationError):
        ExternalMappings(definition=definition)
