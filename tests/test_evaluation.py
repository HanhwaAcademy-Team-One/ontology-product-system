import json
from copy import deepcopy
from pathlib import Path

import pytest

from ontoproduct.evaluation.metrics import (
    evaluate_duplicate,
    evaluate_extraction,
    equal_value,
)
from ontoproduct.evaluation.runner import load_ground_truth, run_evaluation
from ontoproduct.evaluation.report import markdown_report

TRUTH = Path(__file__).resolve().parents[1] / "eval" / "ground_truth"


@pytest.fixture(scope="module")
def measured_report():
    return run_evaluation(TRUTH)


def test_measured_report_uses_unmodified_outputs_and_separates_modes(measured_report):
    mock, rule = measured_report["suites"]
    assert mock["label"] == "MOCK EVALUATION"
    assert rule["label"] == "RULE ENGINE EVALUATION"
    assert all(agent["is_mock"] for agent in mock["agents"])
    assert not any(agent["is_mock"] for agent in rule["agents"])
    assert all(
        sample["outputs"]["extracted_product"]["product_name"] == "DM-500"
        for sample in mock["samples"]
    )
    assert all(
        "rated_speed" not in sample["outputs"]["extracted_product"]["attributes"]
        for sample in mock["samples"]
    )
    assert mock["metrics"]["detection_counts"] == {"tp": 6, "fp": 3, "fn": 4}
    assert mock["metrics"]["Attribute Detection F1"]["value"] == pytest.approx(12 / 19)
    assert mock["metrics"]["Attribute Value Accuracy"] == {
        "value": 0.5,
        "correct": 5,
        "total": 10,
    }
    assert mock["metrics"]["Unit Normalization Accuracy"] == {
        "value": 0.5,
        "correct": 4,
        "total": 8,
    }
    assert mock["metrics"]["Ontology Classification Accuracy"]["correct"] == 2
    assert mock["metrics"]["Required Field Detection Accuracy"]["correct"] == 8
    assert mock["metrics"]["Duplicate Recall@3"]["value"] == 0
    assert rule["metrics"]["Duplicate Precision@3"]["value"] == pytest.approx(2 / 9)
    assert rule["metrics"]["Duplicate Recall@3"]["value"] == 1
    assert all(sample["case_status"] == "NEEDS_FIX" for sample in mock["samples"])


def test_metric_changes_when_recorded_output_changes(measured_report):
    samples = deepcopy(measured_report["suites"][0]["samples"])
    before = evaluate_extraction(samples)
    samples[0]["outputs"]["normalized_product"]["attributes"]["rated_power"][
        "value"
    ] = 999
    samples[0]["outputs"]["normalized_product"]["attributes"]["rated_power"]["unit"] = (
        "kW"
    )
    after = evaluate_extraction(samples)
    assert (
        after["Attribute Value Accuracy"]["correct"]
        == before["Attribute Value Accuracy"]["correct"] - 1
    )
    assert (
        after["Unit Normalization Accuracy"]["correct"]
        == before["Unit Normalization Accuracy"]["correct"] - 1
    )
    assert after["detection_counts"] == before["detection_counts"]


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


def test_duplicate_slots_negatives_and_duplicate_hits_are_explicit():
    samples = [
        {
            "ground_truth": {"case_id": "a", "relevant_duplicates": ["A"]},
            "outputs": {
                "duplicate_candidates": [{"product_name": "A"}, {"product_name": "A"}]
            },
        },
        {
            "ground_truth": {"case_id": "b", "relevant_duplicates": []},
            "outputs": {"duplicate_candidates": []},
        },
    ]
    result = evaluate_duplicate(samples, k=3)
    assert result["Duplicate Precision@3"] == {"value": 1 / 6, "correct": 1, "total": 6}
    assert result["Duplicate Recall@3"]["value"] == 1
    assert result["Negative Query Accuracy"]["value"] == 1
    assert evaluate_duplicate([], k=3)["Duplicate Recall@3"]["value"] is None
    with pytest.raises(ValueError):
        evaluate_duplicate(samples, k=0)


def test_ground_truth_loader_rejects_empty_duplicate_ids_and_path_escape(tmp_path):
    with pytest.raises(ValueError):
        load_ground_truth(tmp_path)
    truth = json.loads((TRUTH / "product_001.json").read_text(encoding="utf-8"))
    truth["source_document"] = "../../outside.txt"
    (tmp_path / "a.json").write_text(json.dumps(truth), encoding="utf-8")
    with pytest.raises(ValueError, match="source"):
        load_ground_truth(tmp_path)


def test_ground_truth_duplicate_ids_rejected(tmp_path):
    truth = json.loads((TRUTH / "product_001.json").read_text(encoding="utf-8"))
    truth["source_document"] = "source.txt"
    (tmp_path / "source.txt").write_text("data", encoding="utf-8")
    for name in ["a", "b"]:
        (tmp_path / f"{name}.json").write_text(json.dumps(truth), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        load_ground_truth(tmp_path)


def test_report_files_include_auditable_outputs_and_sources(tmp_path):
    report = run_evaluation(TRUTH, tmp_path)
    saved = json.loads((tmp_path / "evaluation.json").read_text(encoding="utf-8"))
    assert saved == report
    assert (tmp_path / "evaluation.md").read_text(encoding="utf-8") == markdown_report(
        report
    )
    assert len(report["suites"][0]["samples"][0]["ground_truth"]["source_sha256"]) == 64
    assert report["suites"][0]["samples"][0]["outputs"]["agent_logs"]
    assert not list(tmp_path.glob("*.tmp"))
