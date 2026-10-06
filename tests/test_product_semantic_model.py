from copy import deepcopy

import pytest

from ontoproduct.agents.ontology_agent import OntologyAgent
from ontoproduct.services.agent_errors import OntologyClassificationError
from ontoproduct.services.external_mapping_service import ExternalMappings
from ontoproduct.services.mapping_service import UnitService
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.services.product_ontology_service import ProductOntology
from extraction_ontology_helpers import constant_transport, motor_response


def test_product_model_projects_existing_business_contract_and_drives_default_service():
    model = ProductOntology()
    service = OntologyService()
    assert service.definition == model.operational_definition()
    assert service.semantic_model is not None
    assert service.get_parent("BLDCMotor") == "Motor"
    assert set(service.resolve_required_properties("BLDCMotor")) == {"manufacturer", "rated_voltage", "rated_power", "rated_speed"}
    assert set(service.resolve_properties("Motor")) == {"manufacturer"}
    assert model.model.entity_classes["ManufacturedItem"].external_parents == ["physical_artifact", "individual_product"]
    assert "organization" not in model.model.entity_classes["Manufacturer"].external_parents
    assert model.model.entity_classes["ManufacturerOrganization"].parent == "Manufacturer"


def test_agent_uses_editable_ontology_rules_not_a_separate_hardcoded_classifier():
    model = ProductOntology()
    data = model.model.model_dump(mode="json")
    data["classification_rules"][1]["minimum_matches"] = 3
    custom_model = ProductOntology(definition=data)
    ontology = OntologyService(definition=custom_model.operational_definition().model_dump(), semantic_model=custom_model)
    extracted = motor_response()
    del extracted["attributes"]["rated_speed"]
    with pytest.raises(OntologyClassificationError):
        OntologyAgent(ontology).run({"extracted_product": extracted})
    assert OntologyAgent(OntologyService()).run({"extracted_product": extracted})["ontology_mapping"]["product_class"] == "BLDCMotor"


def test_custom_ontology_contract_stays_supported_and_mismatched_projection_rejected():
    assert OntologyService(definition={"classes": {"Custom": {}}}).semantic_model is None
    with pytest.raises(ValueError, match="projection"):
        OntologyService(definition={"classes": {"Custom": {}}}, semantic_model=ProductOntology())


def test_operational_and_rdf_normalization_share_injected_catalog():
    model = ProductOntology()
    ontology = OntologyService(semantic_model=model)
    assert ontology.unit_service is model.units
    data = model.units.catalog.model_dump(mode="json")
    data["units"]["kW"]["multiplier"] = 999
    with pytest.raises(ValueError, match="same unit catalog"):
        OntologyService(semantic_model=model, unit_service=UnitService(definition=data))


@pytest.mark.parametrize("mutation", ["parent", "unit", "quantity", "domain", "refinement", "comparison", "entity_cycle", "duplicate"])
def test_invalid_semantics_cannot_silently_load(mutation):
    data = ProductOntology().model.model_dump(mode="json")
    if mutation == "parent":
        data["classes"]["Product"]["parent"] = "BLDCMotor"
    elif mutation == "unit":
        data["properties"]["rated_power"]["definition"]["units"].append("kg")
    elif mutation == "quantity":
        data["properties"]["rated_power"]["quantity"] = "mass"
    elif mutation == "domain":
        data["relations"]["hasManufacturer"]["range"] = "Missing"
    elif mutation == "refinement":
        data["classification_rules"][1]["candidate_refinements"]["BLDCMotor"] = "Bearing"
    elif mutation == "comparison":
        data["comparisons"][0]["right"] = "rated_power"
    elif mutation == "entity_cycle":
        data["entity_classes"]["Manufacturer"]["parent"] = "ManufacturerOrganization"
    else:
        data["classes"]["Motor"]["item_class"] = "MotorModel"
    with pytest.raises(ValueError):
        ProductOntology(definition=data)


def test_unverified_external_superclass_is_rejected():
    references = ExternalMappings().catalog.model_dump(mode="json")
    references["mappings"]["physical_artifact"]["status"] = "unverified"
    with pytest.raises(ValueError, match="verified"):
        ProductOntology(references=ExternalMappings(definition=references))


def test_llm_gets_operational_semantics_and_context_cannot_mutate_model():
    ontology = OntologyService()
    transport = constant_transport({"product_class": "BLDCMotor", "confidence": 0.9})
    OntologyAgent(ontology, transport).run({"extracted_product": motor_response()})
    context = transport.calls[0]["payload"]["semantic_model"]
    assert context["record_kind"] == "product_model"
    assert context["quantity_kinds"]["power"]["uri"].endswith("/Power")
    assert context["properties"]["weight"]["quantity"] == "mass"
    before = deepcopy(ontology.semantic_model.model)
    context["classes"]["BLDCMotor"]["required"].clear()
    assert ontology.semantic_model.model == before
