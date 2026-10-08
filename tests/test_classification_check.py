"""AI 분류가 원문 근거와 다르면 유형·근거를 남기고 사람이 분류를 정한다."""

import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from extraction_ontology_helpers import attribute, constant_transport, motor_response
from test_shacl_registration import BearingLlm
from test_streamlit_app import app  # noqa: F401  (pytest fixture)

from ontoproduct.agents.ontology_agent import OntologyAgent
from ontoproduct.agents.real_registry import build_document_registry
from ontoproduct.agents.reviewer_agent import ReviewerAgent
from ontoproduct.mocks.agents import ExtractionMock, mock_registry
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.parser_service import ParserService
from ontoproduct.services.validation_service import validate_registration_product
from ontoproduct.services.workflow_runtime import WorkflowRuntime

E009 = Path(__file__).parents[1] / "inputdata/03_edge_cases/E009_bearing.txt"


def bearing_response(*, outer=True):
    attrs = {
        "inner_diameter": attribute(30, "mm", evidence="Inner Diameter: 30 mm"),
        "outer_diameter": attribute(20, "mm", evidence="Outer Diameter: 20 mm"),
    }
    if not outer:
        del attrs["outer_diameter"]
    return {"product_name": "DEMO-E009", "candidate_class": "Bearing", "attributes": attrs}


def generic_motor_response():
    response = motor_response()
    response["candidate_class"] = "Motor"
    return response


def classify(ontology, extracted, selected, **state):
    transport = constant_transport({"product_class": selected, "confidence": 0.6})
    result = OntologyAgent(ontology, transport).run(
        {"extracted_product": extracted, **state}
    )
    return result, transport


@pytest.mark.parametrize(
    "extracted,selected,evidence_class,category",
    [
        (bearing_response(), "MechanicalPart", "Bearing", "PARENT_CLASS"),
        (bearing_response(), "BLDCMotor", "Bearing", "OTHER_BRANCH"),
        (generic_motor_response(), "BLDCMotor", "Motor", "UNSUPPORTED_SUBCLASS"),
    ],
)
def test_ai_class_against_evidence_is_categorized(
    ontology, extracted, selected, evidence_class, category
):
    before = deepcopy(extracted)
    result, _ = classify(ontology, extracted, selected)
    assert extracted == before
    mapping = result["ontology_mapping"]
    assert mapping["product_class"] == selected
    check = mapping["classification_check"]
    assert (check["ai_class"], check["evidence_class"], check["category"]) == (
        selected,
        evidence_class,
        category,
    )
    assert check["evidence"] == {
        key: attr["evidence"] for key, attr in extracted["attributes"].items()
    }


@pytest.mark.parametrize(
    "extracted,selected",
    [(bearing_response(), "Bearing"), (bearing_response(outer=False), "MechanicalPart")],
)
def test_matching_or_unjudgeable_evidence_has_no_check(ontology, extracted, selected):
    result, _ = classify(ontology, extracted, selected)
    assert result["ontology_mapping"]["classification_check"] is None


def test_manual_class_is_a_human_decision_without_check(ontology):
    result, transport = classify(
        ontology,
        bearing_response(),
        "Bearing",
        manual_overrides={"product_class": "MechanicalPart"},
        locked_fields=["product_class"],
    )
    assert result["ontology_mapping"]["classification_check"] is None
    assert transport.calls == []


def test_reviewer_sends_mismatch_to_human_with_category_and_evidence(ontology):
    result, _ = classify(ontology, bearing_response(), "MechanicalPart")
    mapping, product = result["ontology_mapping"], result["base_normalized_product"]
    state = {
        "normalized_product": product,
        "ontology_mapping": mapping,
        "validation_result": validate_registration_product(product, mapping, ontology),
        "duplicate_candidates": [],
        "locked_fields": [],
    }
    before = deepcopy(state)
    review = ReviewerAgent().run(state)["review_result"]
    assert state == before
    assert (review["decision"], review["can_register"]) == ("NEEDS_FIX", False)
    assert review["retry_fields"] == []
    for text in ("PARENT_CLASS", "MechanicalPart", "Bearing", "Inner Diameter: 30 mm"):
        assert text in review["reason"]


def test_graph_mismatch_goes_to_human_who_sets_evidence_class(tmp_path):
    paths = ApplicationPaths(tmp_path)
    llm = BearingLlm("MechanicalPart", 0.6)

    def factory(ontology):
        return build_document_registry(
            ontology,
            parser_service=ParserService(paths.uploads),
            llm_services={"extraction": llm, "ontology": llm},
        )

    runtime = WorkflowRuntime(paths, registry_factory=factory)
    try:
        session = str(uuid4())
        thread = runtime.create_case(session)
        refs = [runtime.documents.save(session, E009.name, E009.read_bytes())]
        list(runtime.start(thread, refs))
        state = runtime.snapshot(thread).values
        assert state["ontology_mapping"]["classification_check"]["category"] == (
            "PARENT_CLASS"
        )
        assert state["review_result"]["decision"] == "NEEDS_FIX"
        assert state.get("ontology_retry_count", 0) == 0
        list(runtime.resume(thread, {"action": "EDIT", "changed_class": "Bearing"}))
        state = runtime.snapshot(thread).values
        assert state["ontology_mapping"]["classification_check"] is None
        assert [(i["field"], i["code"]) for i in state["validation_result"]["issues"]] == [
            ("attributes.inner_diameter", "RANGE")
        ]
        assert state["review_result"]["decision"] == "NEEDS_FIX"
        list(
            runtime.resume(
                thread,
                {
                    "action": "EDIT",
                    "edits": {
                        "attributes.inner_diameter": {"value": 12, "unit": "mm"},
                        "attributes.outer_diameter": {"value": 32, "unit": "mm"},
                    },
                },
            )
        )
        assert runtime.snapshot(thread).values["review_result"]["can_register"]
        list(runtime.resume(thread, {"action": "APPROVE"}))
        [record] = runtime.products.list()
        assert record["product"]["product_class"] == "Bearing"
        [export] = list(paths.exports.glob("*.json"))
        assert json.loads(export.read_text(encoding="utf-8")) == record["product"]
    finally:
        runtime.close()


def parent_class_registry(ontology):
    registry = mock_registry(ontology)
    registry.register(ExtractionMock(), replace=True)
    transport = constant_transport({"product_class": "ElectricalPart", "confidence": 0.9})
    registry.register(OntologyAgent(ontology, transport), replace=True)
    registry.register(ReviewerAgent(), replace=True)
    return registry


def test_ui_shows_ai_class_mismatch(app):  # noqa: F811
    page, runtime, _ = app
    runtime.registry_factory = parent_class_registry
    page.button(key="start_demo").click().run()
    assert not page.exception
    assert page.button(key="approve_case").disabled
    shown = " ".join(w.value for w in page.warning)
    assert "근거보다 넓은 상위 분류" in shown
