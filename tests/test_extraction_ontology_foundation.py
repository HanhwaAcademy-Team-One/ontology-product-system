from copy import deepcopy

import pytest
from pydantic import ValidationError

from ontoproduct.schemas.product import ParsedDocument, ProductAttribute
from ontoproduct.services.evidence_service import (
    CONFLICT_PREFIX, evidence_candidates, is_conflict, pack_evidence, validate_evidence,
)
from ontoproduct.services.mapping_service import PropertyAliases, UnitService


def test_aliases_are_explicit_and_unknown_names_are_preserved():
    aliases = PropertyAliases()
    assert aliases.resolve("  RATED   POWER ") == aliases.resolve("정격 출력") == "rated_power"
    assert aliases.resolve("특수 출력") == "특수 출력"
    with pytest.raises(ValueError, match="Ambiguous"):
        PropertyAliases(definition={"aliases": {"a": ["X"], "b": ["x"]}})


def test_shared_conversions_including_reverse_and_tolerance(ontology):
    units = ontology.unit_service
    props = ontology.resolve_properties("BLDCMotor")
    assert units.normalize(props["rated_power"], 0.6, "kW") == (600, "W")
    assert units.normalize(props["weight"], 750, "g") == (0.75, "kg")
    assert units.normalize({"type": "number", "canonical_unit": "kW", "units": ["kW", "W"]}, 600, "W") == (0.6, "kW")
    assert units.equal("rated_power", ProductAttribute(value=0.6, unit="kW"), ProductAttribute(value=600.0000000000001, unit="W"))
    assert not units.equal("rated_power", ProductAttribute(value=0, unit="W"), ProductAttribute(value=1e-20, unit="W"))
    assert not units.equal("x", ProductAttribute(value=True), ProductAttribute(value=1))
    assert not units.equal("x", ProductAttribute(value="1"), ProductAttribute(value=1))
    assert not units.equal("rated_power", ProductAttribute(value=1, unit="kg"), ProductAttribute(value=1, unit="W"))


@pytest.mark.parametrize("value,unit", [(True, "W"), ("600", "W"), (float("nan"), "W"), (float("inf"), "W"), (1, "hp"), (1, None), (1e308, "kW")])
def test_invalid_conversion_is_explicit(ontology, value, unit):
    with pytest.raises(ValueError):
        ontology.normalize_unit(ontology.resolve_properties("BLDCMotor")["rated_power"], value, unit)


def test_dimension_and_catalog_validation():
    units = UnitService()
    prop = {"type": "number", "canonical_unit": "W", "units": ["W", "kg"]}
    with pytest.raises(ValueError, match="dimension"):
        units.normalize(prop, 1, "kg")
    with pytest.raises(ValidationError):
        UnitService(definition={"units": {"W": {"quantity": "power", "canonical": "W", "multiplier": float("inf")}}, "property_quantities": {}})
    with pytest.raises(ValidationError):
        UnitService(definition={"units": {"W": {"quantity": "power", "canonical": "missing", "multiplier": 1}}, "property_quantities": {}})


def test_evidence_recovers_original_whitespace_and_exact_location():
    doc = ParsedDocument(source_file="motor_spec.pdf (22222222)", page=2, text="Rated  Power:\n0.6\t kW")
    attr = ProductAttribute(value=0.6, unit="kW", source_file=doc.source_file, page=2, evidence="Rated Power: 0.6 kW", confidence=0.8)
    before = deepcopy(attr)
    result = validate_evidence(attr, [doc])
    assert result.evidence == doc.text and result.provenance == "AI"
    assert attr == before


@pytest.mark.parametrize("changes", [
    {"evidence": "rated Power: 0.6 kW"}, {"evidence": "Rated Power: 0.7 kW"},
    {"evidence": "Rated Power： 0.6 kW"}, {"page": 1}, {"source_file": "motor_spec.pdf"},
    {"evidence": None}, {"source_file": None},
])
def test_wrong_evidence_is_rejected(changes):
    doc = ParsedDocument(source_file="motor_spec.pdf (22222222)", page=2, text="Rated Power: 0.6 kW")
    attr = ProductAttribute(value=0.6, unit="kW", source_file=doc.source_file, page=2, evidence=doc.text).model_copy(update=changes)
    with pytest.raises(ValueError):
        validate_evidence(attr, [doc])


def test_excel_cell_quote_expands_to_original_row_and_rejects_ambiguity():
    line = "[Sheet: Spec, Row: 3] A3=Manufacturer | B3=XYZ Motors"
    attr = ProductAttribute(value="XYZ Motors", source_file="spec.xlsx", evidence="B3=XYZ Motors")
    assert validate_evidence(attr, [ParsedDocument(source_file="spec.xlsx", text=line)]).evidence == line
    with pytest.raises(ValueError, match="Ambiguous"):
        validate_evidence(attr, [ParsedDocument(source_file="spec.xlsx", text=line + "\n" + line.replace("Spec", "Other"))])


def test_aggregate_evidence_preserves_each_candidate_and_conflict_marker():
    attrs = [ProductAttribute(value=v, unit="V", confidence=0.9, evidence=f"Voltage: {v} V", source_file=f"{v}.pdf", page=1) for v in (24, 48)]
    packed = pack_evidence(attrs, conflict=True)
    assert is_conflict(packed) and packed.evidence.startswith(CONFLICT_PREFIX)
    assert packed.value is packed.unit is packed.confidence is packed.source_file is packed.page is None
    assert evidence_candidates(packed) == attrs
    assert not is_conflict(ProductAttribute(value="CONFLICT", evidence="CONFLICT in ordinary source text"))
    with pytest.raises(ValueError, match="reserved"):
        validate_evidence(packed, [])


def test_merged_score_is_minimum_or_null():
    attrs = [ProductAttribute(value=1, confidence=score, evidence=f"one {i}", source_file="a.txt") for i, score in enumerate((0.8, 0.9))]
    assert pack_evidence(attrs).confidence == 0.8
    attrs[1].confidence = None
    assert pack_evidence(attrs).confidence is None


@pytest.mark.parametrize("value,unit,evidence", [
    (999, "V", "Voltage: 24 V"), (24, "kW", "Voltage: 24 V"),
    ("Other Motors", None, "Manufacturer: XYZ Motors"),
    (3, "V", "[Sheet: Spec, Row: 3] A3=Voltage | B3=24 V"),
    (True, None, "Enabled: false"),
])
def test_real_quote_cannot_support_a_fabricated_value_or_unit(value, unit, evidence):
    with pytest.raises(ValueError, match="quoted evidence"):
        validate_evidence(ProductAttribute(value=value, unit=unit, evidence=evidence, source_file="a.txt"),
                          [ParsedDocument(source_file="a.txt", text=evidence)])


@pytest.mark.parametrize("value,unit,evidence", [
    (3200, "rpm", "Speed: 3,200 rpm"), (0.6, "kW", "Power: 6e-1kW"),
    (True, None, "Enabled: Yes"), (False, None, "Enabled: false"),
])
def test_quoted_value_anchor_accepts_explicit_numeric_and_boolean_forms(value, unit, evidence):
    assert validate_evidence(ProductAttribute(value=value, unit=unit, evidence=evidence, source_file="a.txt"),
                             [ParsedDocument(source_file="a.txt", text=evidence)]).value == value
