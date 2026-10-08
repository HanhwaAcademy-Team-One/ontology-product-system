from copy import deepcopy

import pytest

from ontoproduct.services.validation_service import validate_product


@pytest.mark.parametrize(
    "value,unit,code",
    [
        ("fast", "rpm", "TYPE"),
        (True, "rpm", "TYPE"),
        (-1, "rpm", "RANGE"),
        (3000, "Hz", "UNIT"),
    ],
)
def test_deterministic_type_range_unit_checks(paused_state, value, unit, code):
    product = deepcopy(paused_state["normalized_product"])
    product["attributes"]["rated_speed"].update(value=value, unit=unit)
    result = validate_product(product, paused_state["ontology_mapping"])
    assert not result["valid"]
    assert code in [i["code"] for i in result["issues"]]


def test_optional_missing_is_warning_only(paused_state):
    assert paused_state["validation_result"]["valid"]
    assert all(
        i["severity"] == "warning" for i in paused_state["validation_result"]["issues"]
    )
    assert paused_state["review_result"]["decision"] == "READY_FOR_HUMAN"


@pytest.mark.parametrize(
    "provenance,confidence,locked,expected",
    [
        ("AI", 0.69, [], "RE_EXTRACT"),
        ("AI", 0.70, [], "READY_FOR_HUMAN"),
        ("AI", None, [], "RE_EXTRACT"),
        ("HUMAN", None, [], "READY_FOR_HUMAN"),
        ("AI", None, ["attributes.rated_speed"], "READY_FOR_HUMAN"),
        ("DOCUMENT", None, [], "READY_FOR_HUMAN"),
        ("RULE", None, [], "READY_FOR_HUMAN"),
    ],
)
def test_reviewer_confidence_and_human_exclusion(
    registry, paused_state, provenance, confidence, locked, expected
):
    state = deepcopy(paused_state)
    state["normalized_product"]["attributes"]["rated_speed"].update(
        provenance=provenance, confidence=confidence
    )
    state["locked_fields"] = locked
    output = registry.get("reviewer").run(state)["review_result"]
    assert output["decision"] == expected
    if expected == "RE_EXTRACT":
        assert output["retry_fields"] == ["rated_speed"]
    else:
        assert output["retry_fields"] == []


def test_missing_locked_field_needs_human_fix_without_retry(registry, paused_state):
    state = deepcopy(paused_state)
    del state["normalized_product"]["attributes"]["rated_speed"]
    state["locked_fields"] = ["attributes.rated_speed"]
    state["validation_result"] = validate_product(
        state["normalized_product"], state["ontology_mapping"]
    )
    output = registry.get("reviewer").run(state)["review_result"]
    assert output["decision"] == "NEEDS_FIX" and output["retry_fields"] == []
