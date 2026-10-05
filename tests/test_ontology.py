import pytest
from pydantic import ValidationError

from ontoproduct.services.ontology_service import OntologyService


def test_inheritance(ontology):
    assert ontology.get_parent("BLDCMotor") == "Motor"
    assert ontology.get_ancestors("BLDCMotor") == ["Motor", "ElectricalPart", "Product"]
    assert set(ontology.resolve_required_properties("BLDCMotor")) == {
        "manufacturer", "rated_voltage", "rated_power", "rated_speed"}
    assert set(ontology.resolve_optional_properties("BLDCMotor")) == {"weight"}
    assert ontology.resolve_properties("BLDCMotor")["rated_power"].canonical_unit == "W"


def test_child_redefinition_changes_requiredness():
    service = OntologyService(definition={"classes": {
        "Parent": {"required_properties": {"x": {"type": "number", "minimum": 1}}},
        "Child": {"parent": "Parent", "optional_properties": {"x": {"type": "string"}}}}})
    assert service.resolve_required_properties("Child") == {}
    assert service.resolve_properties("Child")["x"].type == "string"


@pytest.mark.parametrize("property_name,value,unit,expected,canonical", [
    ("rated_power", 0.5, "kW", 500, "W"),
    ("weight", 1000, "g", 1, "kg"),
    ("rated_speed", 3000, "rpm", 3000, "rpm"),
    ("manufacturer", "ABC Motors", None, "ABC Motors", None),
])
def test_unit_conversion(ontology, property_name, value, unit, expected, canonical):
    prop = ontology.resolve_properties("BLDCMotor")[property_name]
    assert ontology.normalize_unit(prop, value, unit) == (expected, canonical)


@pytest.mark.parametrize("value,unit", [(1, "hp"), (True, "W"), ("500", "W"), (500, None)])
def test_unsupported_units_or_numeric_types(ontology, value, unit):
    with pytest.raises(ValueError):
        ontology.normalize_unit(ontology.resolve_properties("BLDCMotor")["rated_power"], value, unit)


@pytest.mark.parametrize("classes", [
    {"A": {"parent": "Missing"}},
    {"A": {"parent": "B"}, "B": {"parent": "A"}},
    {"A": {"required_properties": {"x": {"type": "number", "canonical_unit": "W", "units": ["kW"]}}}},
])
def test_invalid_ontology_rejected(classes):
    with pytest.raises(ValidationError):
        OntologyService(definition={"classes": classes})


def test_unknown_class_and_returned_class_isolation(ontology):
    with pytest.raises(ValueError):
        ontology.get_class("Missing")
    cls = ontology.get_class("BLDCMotor")
    cls.required_properties.clear()
    assert ontology.resolve_required_properties("BLDCMotor")
