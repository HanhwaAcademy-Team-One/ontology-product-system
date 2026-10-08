import json
from pathlib import Path

import pytest

DATA = Path(__file__).parents[1] / "inputdata"


def run(tmp_path, ids):
    from ontoproduct.evaluation.document_runner import run_document_evaluation

    return run_document_evaluation(DATA, tmp_path / "reports", case_ids=ids)


def test_manifest_groups_all_formats_and_conflicts(tmp_path):
    from ontoproduct.evaluation.document_runner import load_cases

    groups = load_cases(DATA)
    assert len(groups) == 75
    assert len({f for g in groups for f in g["files"]}) == 80
    assert len([g for g in groups if g["id"] == "D003"]) == 1
    assert len(next(g for g in groups if g["id"] == "D003")["files"]) == 2
    assert len([g for g in groups if g["id"] == "M001"]) == 3
    assert len(load_cases(DATA, ["M001", "B001", "E008", "E009"], "txt")) == 4


def test_real_formats_are_isolated_and_reports_include_failures(tmp_path):
    report = run(
        tmp_path, ["M001", "B001", "E002", "E007", "E008", "D003", "D004", "D005"]
    )
    assert report["mode"] == "offline_reference"
    assert report["live_llm_verified"] is False
    samples = report["suites"][0]["samples"]
    assert len(samples) == 12
    assert {s["observed_outcome"] for s in samples} >= {
        "valid",
        "missing_required",
        "semantic_error",
        "required_conflict",
        "document_conflict",
    }
    assert report["suites"][0]["metrics"]["Expected Outcome Accuracy"]["total"] == 12
    assert report["suites"][0]["metrics"]["Expected Outcome Accuracy"]["correct"] == 12
    assert all(s["saved_products"] == 0 for s in samples)
    assert all(
        s["outputs"].get("error_events")
        for s in samples
        if s["observed_outcome"] == "document_conflict"
    )
    assert all(s["integration_after_human"] is None for s in samples)
    assert all(
        s["source_hashes"] and s["ground_truth"]["ground_truth_sha256"] for s in samples
    )
    assert (Path(report["report_directory"]) / "evaluation.json").is_file()
    markdown = (Path(report["report_directory"]) / "evaluation.md").read_text(
        encoding="utf-8"
    )
    assert all(
        label in markdown
        for label in [
            "Service calls:",
            "Normalized truth:",
            "Prompt versions:",
            "Failures/limits:",
            "RANGE",
            "ReferenceLlm",
        ]
    )
    other = run(tmp_path, ["M001"])
    assert report["run_id"] != other["run_id"]
    assert Path(report["report_directory"]).is_dir()


def test_reference_hash_mismatch_fails_before_execution(tmp_path):
    from ontoproduct.evaluation.document_runner import load_cases

    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    manifest["cases"] = [manifest["cases"][0]]
    manifest["cases"][0]["files"] = ["changed.txt"]
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "changed.txt").write_text("changed", encoding="utf-8")
    (tmp_path / "verification.json").write_text(
        json.dumps({"files": [{"file": "changed.txt", "sha256": "old"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="hash"):
        load_cases(tmp_path)


def test_failed_known_truth_stays_in_metric_denominator(tmp_path):
    from ontoproduct.evaluation.document_runner import run_document_evaluation

    class Failing:
        def generate_structured(self, **kwargs):
            raise TimeoutError("injected timeout")

    report = run_document_evaluation(
        DATA,
        tmp_path / "reports",
        case_ids=["M001"],
        llm_services={"extraction": Failing(), "ontology": Failing()},
        mode="offline_reference",
    )
    metrics = report["suites"][0]["metrics"]
    assert metrics["Attribute Value Accuracy"]["correct"] == 0
    assert metrics["Attribute Value Accuracy"]["total"] == 15
    assert metrics["Expected Outcome Accuracy"]["total"] == 3
    assert len(report["failures"]) == 3


def test_model_call_limit_preserves_unexecuted_cases_in_report(tmp_path):
    from ontoproduct.evaluation.document_runner import run_document_evaluation

    report = run_document_evaluation(
        DATA, tmp_path / "reports", case_ids=["M001"], max_calls=1
    )
    assert report["call_count"] == 1
    assert len(report["limited_cases"]) == 3
    assert report["suites"][0]["metrics"]["Expected Outcome Accuracy"]["total"] == 3
    assert report["suites"][0]["metrics"]["Attribute Value Accuracy"]["total"] == 15


def test_conflict_has_no_reextract_and_repaired_checkpoint_restores(tmp_path):
    from uuid import uuid4

    from ontoproduct.agents.real_registry import build_document_registry
    from ontoproduct.evaluation.document_runner import ReferenceLlm, load_cases
    from ontoproduct.services.application_paths import ApplicationPaths
    from ontoproduct.services.parser_service import ParserService
    from ontoproduct.services.workflow_runtime import WorkflowRuntime

    [case] = load_cases(DATA, ["D003"])
    paths = ApplicationPaths(tmp_path)
    llm = ReferenceLlm(case)

    def factory(ontology):
        return build_document_registry(
            ontology,
            parser_service=ParserService(paths.uploads),
            llm_services={"extraction": llm, "ontology": llm},
        )

    runtime = WorkflowRuntime(paths, registry_factory=factory)
    session = str(uuid4())
    thread = runtime.create_case(session)
    try:
        refs = [
            runtime.documents.save(session, Path(f).name, (DATA / f).read_bytes())
            for f in case["files"]
        ]
        list(runtime.start(thread, refs))
        before = runtime.snapshot(thread).values
        assert before["review_result"]["decision"] == "NEEDS_FIX"
        assert before["extraction_retry_count"] == 0
        assert (
            sum(
                log["agent"] == "extraction" and log["status"] == "success"
                for log in before["agent_logs"]
            )
            == 1
        )
        assert runtime.products.count() == 0
        list(
            runtime.resume(
                thread,
                {
                    "action": "EDIT",
                    "edits": {"attributes.rated_power": {"value": 800, "unit": "W"}},
                },
            )
        )
        attr = runtime.snapshot(thread).values["normalized_product"]["attributes"][
            "rated_power"
        ]
        assert attr["provenance"] == "HUMAN" and attr["confidence"] is None
        assert (
            before["normalized_product"]["attributes"]["rated_power"]["value"] is None
        )
    finally:
        runtime.close()
    restored = WorkflowRuntime(paths, registry_factory=factory)
    try:
        state = restored.snapshot(thread).values
        assert state["normalized_product"]["attributes"]["rated_power"] == attr
        assert "attributes.rated_power" in state["locked_fields"]
        list(restored.resume(thread, {"action": "APPROVE"}))
        list(restored.resume(thread, {"action": "APPROVE"}))
        [record] = restored.products.list()
        [export] = list(paths.exports.glob("*.json"))
        assert json.loads(export.read_text(encoding="utf-8")) == record["product"]
    finally:
        restored.close()
