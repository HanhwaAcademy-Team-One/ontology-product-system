"""docs/team/REVIEW_01_05.md의 항목별 회귀 테스트.

- 통과하는 테스트: Graph가 이미 지원하는 동작을 고정한다(막힌 곳은 UI뿐).
- xfail(strict=True): 아직 수정하지 않은 동작. 수정하면 XPASS로 실패하므로 표시를 제거한다.
"""

from uuid import uuid4

import pytest
from langgraph.types import Command
from real_llm_helpers import HonestLlm
from test_streamlit_app import app  # noqa: F401  (pytest fixture)

from ontoproduct.agents.real_registry import build_document_registry
from ontoproduct.agents.validation_agent import ValidationAgent
from ontoproduct.graph.state import initial_state
from ontoproduct.graph.workflow import build_workflow
from ontoproduct.mocks.agents import ExtractionMock, OntologyMock, mock_registry
from ontoproduct.schemas.product import ProductAttribute
from ontoproduct.services import workflow_runtime
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.evidence_service import pack_evidence
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.services.parser_service import ParserService
from ontoproduct.services.validation_service import validate_product
from ontoproduct.services.workflow_runtime import WorkflowRuntime


def attributes(confidence):
    """검증을 모두 통과하는 DM-500 필수 속성. confidence만 바꿔 쓴다."""
    base = {"confidence": confidence, "provenance": "AI"}
    return {
        "manufacturer": {"value": "ABC Motors", **base},
        "rated_voltage": {"value": 24, "unit": "V", **base},
        "rated_power": {"value": 0.5, "unit": "kW", **base},
        "rated_speed": {"value": 3000, "unit": "rpm", **base},
    }


def conflicting_voltage():
    """두 문서가 24 V / 48 V로 다른 값을 말하는 충돌 속성(Extraction이 만드는 형식)."""
    first = ProductAttribute(
        value=24,
        unit="V",
        confidence=0.9,
        evidence="Rated Voltage: 24 V",
        source_file="a.txt",
        page=1,
        provenance="AI",
    )
    second = first.model_copy(
        update={
            "value": 48,
            "evidence": "Rated Voltage: 48 V",
            "source_file": "b.txt",
        }
    )
    return pack_evidence([first, second], conflict=True).model_dump(mode="json")


class LowConfidenceOntology(OntologyMock):
    """LLM 분류가 낮은 confidence를 낸 상황. 수동 분류는 실제 Agent처럼 1.0이다."""

    def run(self, state):
        result = super().run(state)
        manual = "product_class" in state.get("manual_overrides", {})
        result["ontology_mapping"]["confidence"] = 1.0 if manual else 0.5
        return result


def registry_with(ontology, extraction, ontology_agent=OntologyMock):
    registry = mock_registry(ontology)
    registry.register(ExtractionMock(attributes=extraction), replace=True)
    registry.register(ontology_agent(ontology), replace=True)
    return registry


def null_confidence_registry(ontology):
    return registry_with(ontology, attributes(None))


def low_class_confidence_registry(ontology):
    return registry_with(ontology, attributes(0.95), LowConfidenceOntology)


def conflict_registry(ontology):
    extraction = attributes(0.95)
    extraction["rated_voltage"] = conflicting_voltage()
    return registry_with(ontology, extraction)


def run_to_review(registry_factory):
    ontology = OntologyService()
    graph = build_workflow(registry_factory(ontology), ontology=ontology)
    config = {"configurable": {"thread_id": str(uuid4())}}
    graph.invoke(initial_state(), config)
    return graph, config


def confirm_as_is(state):
    """UI가 보내야 하는 '값을 바꾸지 않고 확인' edits (재검토 대상 항목 그대로)."""
    attrs = state["normalized_product"]["attributes"]
    return {
        f"attributes.{key}": {"value": attrs[key]["value"], "unit": attrs[key]["unit"]}
        for key in state["review_result"]["retry_fields"]
    }


# --- #1, #3 Graph: 같은 값/같은 분류 확인을 이미 받아들인다 -----------------------


def test_graph_accepts_unchanged_ai_values_when_confidence_is_missing():
    graph, config = run_to_review(null_confidence_registry)
    state = graph.get_state(config).values
    assert state["case_status"] == "NEEDS_FIX"
    assert state["validation_result"]["valid"]
    assert state["review_result"]["retry_fields"]
    graph.invoke(
        Command(resume={"action": "EDIT", "edits": confirm_as_is(state)}), config
    )
    review = graph.get_state(config).values["review_result"]
    assert (review["decision"], review["can_register"]) == ("READY_FOR_HUMAN", True)


def test_graph_accepts_current_class_as_manual_classification():
    graph, config = run_to_review(low_class_confidence_registry)
    state = graph.get_state(config).values
    assert state["case_status"] == "NEEDS_FIX"
    assert state["validation_result"]["valid"]
    current = state["normalized_product"]["product_class"]
    graph.invoke(Command(resume={"action": "EDIT", "changed_class": current}), config)
    review = graph.get_state(config).values["review_result"]
    assert (review["decision"], review["can_register"]) == ("READY_FOR_HUMAN", True)


# --- #1, #2A, #3 UI --------------------------------------------------------------


def test_ui_confirming_ai_values_releases_needs_fix(app):  # noqa: F811
    page, runtime, _ = app
    runtime.registry_factory = null_confidence_registry
    page.button(key="start_demo").click().run()
    assert not page.exception
    assert page.button(key="approve_case").disabled
    boxes = [box for box in page.checkbox if "AI 값 확인" in box.label]
    assert boxes
    for box in boxes:
        box.check()
    page.button(key="submit_edit").click().run()
    assert not page.exception
    assert not page.button(key="approve_case").disabled


def test_ui_confirming_ai_class_releases_needs_fix(app):  # noqa: F811
    page, runtime, _ = app
    runtime.registry_factory = low_class_confidence_registry
    page.button(key="start_demo").click().run()
    assert not page.exception
    assert page.button(key="approve_case").disabled
    boxes = [box for box in page.checkbox if "AI 분류 확정" in box.label]
    assert boxes
    boxes[0].check()
    page.button(key="submit_edit").click().run()
    assert not page.exception
    assert not page.button(key="approve_case").disabled


def test_ui_shows_conflicting_document_values(app):  # noqa: F811
    page, runtime, _ = app
    runtime.registry_factory = conflict_registry
    page.button(key="start_demo").click().run()
    assert not page.exception
    shown = " ".join(frame.value.to_string() for frame in page.dataframe)
    assert "Rated Voltage: 24 V" in shown
    assert "Rated Voltage: 48 V" in shown


# --- #2B Validation --------------------------------------------------------------


def conflict_validation():
    ontology = OntologyService()
    required = ontology.resolve_required_properties("BLDCMotor")
    optional = ontology.resolve_optional_properties("BLDCMotor")
    mapping = {
        "product_class": "BLDCMotor",
        "confidence": 1,
        "required_properties": {
            k: p.model_dump(mode="json") for k, p in required.items()
        },
        "optional_properties": {
            k: p.model_dump(mode="json") for k, p in optional.items()
        },
    }
    good = {"confidence": 0.9, "provenance": "AI"}
    product = {
        "product_name": "DM-500",
        "product_class": "BLDCMotor",
        "attributes": {
            "manufacturer": {"value": "ABC Motors", **good},
            "rated_voltage": conflicting_voltage(),
            "rated_power": {"value": 500.0, "unit": "W", **good},
            "rated_speed": {"value": 3000, "unit": "rpm", **good},
        },
    }
    result = validate_product(product, mapping)
    return next(
        i for i in result["issues"] if i["field"] == "attributes.rated_voltage"
    ), result


def test_validation_keeps_missing_required_code_for_conflict():
    issue, result = conflict_validation()
    assert (issue["code"], issue["severity"]) == ("MISSING_REQUIRED", "error")
    assert not result["valid"]


def test_validation_message_tells_conflict_apart_from_missing():
    issue, _ = conflict_validation()
    assert "conflict" in issue["message"].lower()
    assert "missing" not in issue["message"].lower()


# --- #4 Real 모드 연결 -----------------------------------------------------------


def test_real_registry_runs_real_validation_agent(tmp_path):
    registry = build_document_registry(
        OntologyService(),
        parser_service=ParserService(tmp_path),
        llm_services={"extraction": HonestLlm(), "ontology": HonestLlm()},
    )
    assert isinstance(registry.get("validation"), ValidationAgent)
    assert not {a["name"]: a for a in registry.metadata()}["validation"]["is_mock"]


# --- #5 Duplicate 슬롯 생성 위치 -------------------------------------------------


def test_every_duplicate_service_receives_the_runtime_ontology(tmp_path, monkeypatch):
    received = []
    original = workflow_runtime.DuplicateService

    def recording(repository, ontology=None):
        received.append(ontology)
        return original(repository, ontology)

    monkeypatch.setattr(workflow_runtime, "DuplicateService", recording)
    runtime = WorkflowRuntime(ApplicationPaths(tmp_path))
    try:
        runtime.agent_metadata()
        runtime.graph(str(uuid4()))
    finally:
        runtime.close()
    assert len(received) == 2
    assert all(ontology is runtime.ontology for ontology in received)
