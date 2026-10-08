from pathlib import Path


def test_null_confidence_is_measured_without_raising_scores(tmp_path):
    from ontoproduct.evaluation.document_runner import (
        ReferenceLlm,
        load_cases,
        run_document_evaluation,
    )

    data = Path(__file__).parents[1] / "inputdata"
    case = load_cases(data, ["M001"])[0]

    class UncertainReference(ReferenceLlm):
        def generate_structured(self, **kwargs):
            result = super().generate_structured(**kwargs)
            if kwargs["task"] == "extraction":
                for attr in result.attributes.values():
                    attr.confidence = None
            return result

    llm = UncertainReference(case)
    report = run_document_evaluation(
        data,
        tmp_path / "reports",
        case_ids=["M001"],
        llm_services={"extraction": llm, "ontology": llm},
    )
    metric = report["suites"][0]["metrics"]["AI Confidence Null Rate"]
    assert metric == {"value": 1.0, "correct": 15, "total": 15}
    assert report["suites"][0]["metrics"]["Attribute Value Accuracy"]["value"] == 1.0
    assert all(
        s["outputs"]["review_result"]["decision"] == "NEEDS_FIX"
        for s in report["suites"][0]["samples"]
    )
