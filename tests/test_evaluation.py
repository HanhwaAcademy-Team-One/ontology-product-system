import pytest

from ontoproduct.evaluation.metrics import evaluate_extraction, equal_value


def test_null_prediction_is_not_detected_and_missing_value_is_wrong():
    samples = [
        {
            "ground_truth": {
                "product": {"attributes": {"speed": {"value": 0, "unit": "rpm"}}}
            },
            "outputs": {
                "extracted_product": {"attributes": {"speed": {"value": None}}},
                "normalized_product": {"attributes": {}},
            },
        }
    ]
    result = evaluate_extraction(samples)
    assert result["detection_counts"] == {"tp": 0, "fp": 0, "fn": 1}
    assert result["Attribute Detection Precision"]["value"] is None
    assert result["Attribute Detection Recall"]["value"] == 0
    assert result["Attribute Value Accuracy"]["value"] == 0
    assert result["Unit Normalization Accuracy"]["value"] == 0


@pytest.mark.parametrize(
    "actual,expected,correct",
    [(500.0, 500, True), ("500", 500, False), (True, 1, False), (0, 0, True)],
)
def test_value_comparison_preserves_types(actual, expected, correct):
    assert equal_value(actual, expected) is correct
