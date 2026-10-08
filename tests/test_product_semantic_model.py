import json
from copy import deepcopy

import pytest

from ontoproduct.agents.ontology_agent import OntologyAgent
from ontoproduct.services.agent_errors import OntologyClassificationError
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
    assert set(service.resolve_required_properties("BLDCMotor")) == {
        "manufacturer",
        "rated_voltage",
        "rated_power",
        "rated_speed",
    }
    assert set(service.resolve_properties("Motor")) == {"manufacturer"}
    assert model.model.entity_classes["ManufacturedItem"].parents == [
        "PhysicalArtifact"
    ]
    assert "Organization" not in model.entity_ancestors("Manufacturer")
    assert set(model.entity_ancestors("ManufacturerOrganization")) == {
        "Manufacturer",
        "Organization",
        "BusinessEntity",
    }
    assert "PhysicalArtifact" not in model.entity_ancestors("ProductModel")


def test_agent_uses_editable_ontology_rules_not_a_separate_hardcoded_classifier():
    model = ProductOntology()
    data = model.model.model_dump(mode="json")
    data["classification_rules"][1]["minimum_matches"] = 3
    custom_model = ProductOntology(definition=data)
    ontology = OntologyService(
        definition=custom_model.operational_definition().model_dump(),
        semantic_model=custom_model,
    )
    extracted = motor_response()
    del extracted["attributes"]["rated_speed"]
    with pytest.raises(OntologyClassificationError):
        OntologyAgent(ontology).run({"extracted_product": extracted})
    assert (
        OntologyAgent(OntologyService()).run({"extracted_product": extracted})[
            "ontology_mapping"
        ]["product_class"]
        == "BLDCMotor"
    )


def test_custom_ontology_contract_stays_supported_and_mismatched_projection_rejected():
    assert (
        OntologyService(definition={"classes": {"Custom": {}}}).semantic_model is None
    )
    with pytest.raises(ValueError, match="projection"):
        OntologyService(
            definition={"classes": {"Custom": {}}}, semantic_model=ProductOntology()
        )


def test_operational_and_rdf_normalization_share_injected_catalog():
    model = ProductOntology()
    ontology = OntologyService(semantic_model=model)
    assert ontology.unit_service is model.units
    data = model.units.catalog.model_dump(mode="json")
    data["units"]["kW"]["multiplier"] = 999
    with pytest.raises(ValueError, match="same unit catalog"):
        OntologyService(semantic_model=model, unit_service=UnitService(definition=data))


@pytest.mark.parametrize(
    "mutation",
    [
        "parent",
        "unit",
        "quantity",
        "domain",
        "refinement",
        "comparison",
        "entity_cycle",
        "duplicate",
        "unknown_parent",
        "unknown_source",
        "source_id",
        "measurement_clash",
    ],
)
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
        data["classification_rules"][1]["candidate_refinements"]["BLDCMotor"] = (
            "Bearing"
        )
    elif mutation == "comparison":
        data["comparisons"][0]["right"] = "rated_power"
    elif mutation == "entity_cycle":
        data["entity_classes"]["BusinessEntity"]["parents"] = [
            "ManufacturerOrganization"
        ]
    elif mutation == "unknown_parent":
        data["entity_classes"]["Manufacturer"]["parents"] = ["Missing"]
    elif mutation == "unknown_source":
        data["relations"]["hasManufacturer"]["sources"] = ["missing-1.0"]
    elif mutation == "source_id":
        data["sources"]["qudt"] = data["sources"].pop("qudt-3.5.2")
    elif mutation == "measurement_clash":
        data["measurement"]["numeric_value"]["name"] = "ratedPower"
    else:
        data["classes"]["Motor"]["item_class"] = "MotorModel"
    with pytest.raises(ValueError):
        ProductOntology(definition=data)


@pytest.mark.parametrize("target", ["model", "units"])
def test_operational_ontology_data_rejects_external_urls(target):
    data = ProductOntology().model.model_dump(mode="json")
    units = UnitService().catalog.model_dump(mode="json")
    if target == "model":
        data["entity_classes"]["ProductModel"]["description"] = (
            "See http://purl.org/goodrelations/v1#ProductOrServiceModel"
        )
    else:
        units["quantity_definitions"]["power"]["description"] = (
            "http://qudt.org/vocab/quantitykind/Power"
        )
    with pytest.raises(ValueError, match="external URLs"):
        ProductOntology(definition=data, units=UnitService(definition=units))


def test_used_units_and_quantities_need_local_definitions():
    units = UnitService().catalog.model_dump(mode="json")
    units["units"]["kW"]["label"] = None
    with pytest.raises(ValueError, match="label"):
        ProductOntology(units=UnitService(definition=units))
    units = UnitService().catalog.model_dump(mode="json")
    units["quantity_definitions"]["mass"]["sources"] = ["unknown-1.0"]
    with pytest.raises(ValueError, match="source"):
        ProductOntology(units=UnitService(definition=units))


def test_llm_gets_operational_semantics_and_context_cannot_mutate_model():
    ontology = OntologyService()
    transport = constant_transport({"product_class": "BLDCMotor", "confidence": 0.9})
    OntologyAgent(ontology, transport).run({"extracted_product": motor_response()})
    context = transport.calls[0]["payload"]["semantic_model"]
    assert context["record_kind"] == "product_model"
    assert context["quantity_kinds"]["power"]["label"] == "Power"
    assert context["units"]["kW"] == {
        "label": "kilowatt",
        "quantity": "power",
        "canonical": "W",
        "multiplier": 1000.0,
    }
    assert context["measurement"]["quantity_value"]["name"] == "QuantityValue"
    assert "://" not in json.dumps(context)
    assert context["properties"]["weight"]["quantity"] == "mass"
    before = deepcopy(ontology.semantic_model.model)
    context["classes"]["BLDCMotor"]["required"].clear()
    assert ontology.semantic_model.model == before
