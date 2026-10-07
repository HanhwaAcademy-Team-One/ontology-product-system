import json
from copy import deepcopy

import pytest

from ontoproduct.agents.validation_agent import ValidationAgent
from ontoproduct.graph.execution import execute_agent
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.services.validation_service import validate_product


def make_input():
    """검증을 통과하는 BLDCMotor 제품과 온톨로지 매핑을 만든다."""
    product = {
        "product_name": "DM-600",
        "product_class": "BLDCMotor",
        "attributes": {
            "manufacturer": {
                "value": "XYZ Motors",
                "unit": None,
                "confidence": 0.82,
                "evidence": "Manufacturer: XYZ Motors",
                "source_file": "motor_spec.txt",
                "page": None,
                "provenance": "AI",
            },
            "rated_voltage": {
                "value": 24,
                "unit": "V",
                "confidence": 0.82,
                "evidence": "Rated Voltage: 24 V",
                "source_file": "motor_spec.txt",
                "page": None,
                "provenance": "AI",
            },
            "rated_power": {
                "value": 600.0,
                "unit": "W",
                "confidence": 0.82,
                "evidence": "Rated Power: 0.6 kW",
                "source_file": "motor_spec.txt",
                "page": None,
                "provenance": "AI",
            },
            "rated_speed": {
                "value": 3200,
                "unit": "rpm",
                "confidence": 0.82,
                "evidence": "Rated Speed: 3200 rpm",
                "source_file": "motor_spec.txt",
                "page": None,
                "provenance": "AI",
            },
        },
    }

    mapping = {
        "product_class": "BLDCMotor",
        "confidence": 0.82,
        "required_properties": {
            "manufacturer": {
                "type": "string",
                "canonical_unit": None,
                "units": [],
                "minimum": None,
                "maximum": None,
            },
            "rated_voltage": {
                "type": "number",
                "canonical_unit": "V",
                "units": ["V"],
                "minimum": 0.0,
                "maximum": None,
            },
            "rated_power": {
                "type": "number",
                "canonical_unit": "W",
                "units": ["W", "kW"],
                "minimum": 0.0,
                "maximum": None,
            },
            "rated_speed": {
                "type": "number",
                "canonical_unit": "rpm",
                "units": ["rpm"],
                "minimum": 0.0,
                "maximum": None,
            },
        },
        "optional_properties": {
            "weight": {
                "type": "number",
                "canonical_unit": "kg",
                "units": ["g", "kg"],
                "minimum": 0.0,
                "maximum": None,
            }
        },
    }

    return {
        "normalized_product": product,
        "ontology_mapping": mapping,
    }


def run_validation(inputs):
    """ValidationAgent의 업무 출력을 반환한다."""
    return ValidationAgent().run(inputs)["validation_result"]


def find_issue(result, code, field):
    """결과에서 코드와 필드가 일치하는 issue를 찾는다."""
    return next(
        issue
        for issue in result["issues"]
        if issue["code"] == code and issue["field"] == field
    )


def test_agent_obeys_contract_and_matches_existing_service():
    agent = ValidationAgent()

    # 공통 약속에 따라 Mock Registry의 Validation 슬롯을 교체한다.
    registry = mock_registry()
    registry.register(agent, replace=True)
    registry.validate_complete()

    inputs = make_input()
    original_inputs = deepcopy(inputs)
    events = []

    result = execute_agent(
        registry,
        agent.name,
        inputs,
        writer=events.append,
    )

    assert inputs == original_inputs
    assert result["agent_logs"][-1]["status"] == "success"
    assert not result["error_events"]
    assert set(result) == set(agent.writes) | {"agent_logs", "error_events"}
    assert result["validation_result"] == validate_product(
        inputs["normalized_product"],
        inputs["ontology_mapping"],
    )

    # 결과가 JSON으로 직렬화 가능한지 확인한다.
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("missing_value", ["absent", "null"])
def test_missing_required_property_is_an_error(missing_value):
    inputs = make_input()
    attributes = inputs["normalized_product"]["attributes"]

    if missing_value == "absent":
        attributes.pop("rated_speed")
    else:
        attributes["rated_speed"]["value"] = None

    result = run_validation(inputs)

    issue = find_issue(
        result,
        "MISSING_REQUIRED",
        "attributes.rated_speed",
    )
    assert issue["severity"] == "error"
    assert result["valid"] is False


def test_missing_optional_property_is_a_warning():
    # 샘플에는 선택 속성인 weight가 없다.
    result = run_validation(make_input())

    issue = find_issue(
        result,
        "MISSING_OPTIONAL",
        "attributes.weight",
    )
    assert issue["severity"] == "warning"
    assert result["valid"] is True


@pytest.mark.parametrize("bad_value", ["24", True])
def test_non_numeric_voltage_is_a_type_error(bad_value):
    inputs = make_input()
    inputs["normalized_product"]["attributes"]["rated_voltage"]["value"] = bad_value

    result = run_validation(inputs)

    issue = find_issue(
        result,
        "TYPE",
        "attributes.rated_voltage",
    )
    assert issue["severity"] == "error"
    assert result["valid"] is False


def test_noncanonical_unit_is_a_unit_error():
    inputs = make_input()

    # 정규화된 제품의 표준 단위는 W여야 한다.
    inputs["normalized_product"]["attributes"]["rated_power"]["unit"] = "kW"

    result = run_validation(inputs)

    issue = find_issue(
        result,
        "UNIT",
        "attributes.rated_power",
    )
    assert issue["severity"] == "error"
    assert result["valid"] is False


def test_zero_is_allowed_but_negative_value_is_out_of_range():
    inputs = make_input()
    inputs["normalized_product"]["attributes"]["rated_speed"]["value"] = 0

    # 최솟값이 0이므로 0은 허용된다.
    assert run_validation(inputs)["valid"] is True

    inputs["normalized_product"]["attributes"]["rated_speed"]["value"] = -1
    result = run_validation(inputs)

    issue = find_issue(
        result,
        "RANGE",
        "attributes.rated_speed",
    )
    assert issue["severity"] == "error"
    assert result["valid"] is False


def test_class_mismatch_and_unknown_property_keep_existing_meaning():
    inputs = make_input()
    inputs["normalized_product"]["product_class"] = "Bearing"
    inputs["normalized_product"]["attributes"]["unexpected_property"] = {
        "value": "extra",
        "unit": None,
        "confidence": 0.82,
        "evidence": "Unexpected property",
        "source_file": "motor_spec.txt",
        "page": None,
        "provenance": "AI",
    }

    result = run_validation(inputs)

    class_issue = find_issue(result, "CLASS", "product_class")
    unknown_issue = find_issue(
        result,
        "UNKNOWN_PROPERTY",
        "attributes.unexpected_property",
    )

    assert class_issue["severity"] == "error"
    assert unknown_issue["severity"] == "warning"
    assert result["valid"] is False


def test_human_corrected_required_property_clears_missing_error():
    inputs = make_input()
    attributes = inputs["normalized_product"]["attributes"]
    attributes.pop("rated_speed")

    missing_result = run_validation(inputs)
    find_issue(
        missing_result,
        "MISSING_REQUIRED",
        "attributes.rated_speed",
    )

    # 사람이 값을 입력한 뒤 만들어진 normalized_product를 다시 검증한다.
    attributes["rated_speed"] = {
        "value": 3200,
        "unit": "rpm",
        "confidence": None,
        "evidence": "Human entered: 3200 rpm",
        "source_file": None,
        "page": None,
        "provenance": "HUMAN",
    }

    corrected_result = run_validation(inputs)

    assert not any(
        issue["code"] == "MISSING_REQUIRED"
        and issue["field"] == "attributes.rated_speed"
        for issue in corrected_result["issues"]
    )
    assert corrected_result["valid"] is True


def test_multiple_errors_are_preserved():
    inputs = make_input()
    attributes = inputs["normalized_product"]["attributes"]

    attributes.pop("rated_speed")
    attributes["rated_power"]["unit"] = "kW"

    result = run_validation(inputs)

    find_issue(result, "MISSING_REQUIRED", "attributes.rated_speed")
    find_issue(result, "UNIT", "attributes.rated_power")
    assert result["valid"] is False