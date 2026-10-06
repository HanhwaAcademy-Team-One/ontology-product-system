from copy import deepcopy

import pytest
from langgraph.types import Command

from ontoproduct.agents.extraction_agent import ExtractionAgent
from ontoproduct.agents.ontology_agent import OntologyAgent
from ontoproduct.graph.execution import execute_agent
from ontoproduct.graph.state import initial_state
from ontoproduct.graph.workflow import build_workflow
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.schemas.error import unresolved_errors
from ontoproduct.services.normalization_service import apply_overrides, merge_extraction_retry
from ontoproduct.services.ontology_service import OntologyService
from conftest import count_runs
from extraction_ontology_helpers import RecordingTransport, attribute, document, motor_response


def document_registry(ontology, docs, transport, *, classify_with_llm=False):
    registry = mock_registry(ontology)
    # Parser is outside this task: pass pre-parsed fixtures through its slot.
    registry.get("parser").run = lambda state: {"parsed_documents": deepcopy(docs)}
    registry.register(ExtractionAgent(transport, ontology=ontology), replace=True)
    registry.register(OntologyAgent(ontology, transport if classify_with_llm else None), replace=True)
    registry.validate_complete()
    return registry


def fixture_handler(task, payload):
    if task == "ontology":
        return {"product_class": "BLDCMotor", "confidence": 0.5}
    doc = payload["documents"][0]
    if doc["source_file"] == "motor.txt":
        return motor_response()
    key = "weight" if "Weight" in doc["text"] else "rated_speed"
    value, unit = (800, "g") if key == "weight" else (3000, "rpm")
    return {"candidate_class": "BLDCMotor", "attributes": {
        key: attribute(value, unit, evidence=doc["text"], source_file=doc["source_file"])}}


def test_complete_real_agents_graph_human_edit_and_approval(ontology, config):
    transport = RecordingTransport(fixture_handler)
    registry = document_registry(ontology, [document()], transport)
    graph = build_workflow(registry, ontology=ontology)
    result = graph.invoke(initial_state(), config)
    assert result["__interrupt__"][0].value["kind"] == "human_review"
    assert result["review_result"]["can_register"] and "final_product" not in result
    assert result["normalized_product"]["attributes"]["rated_power"]["value"] == 600
    graph.invoke(Command(resume={"action": "EDIT", "edits": {"attributes.rated_power": {"value": 0.8, "unit": "kW"}}}), config)
    state = graph.get_state(config).values
    power = state["normalized_product"]["attributes"]["rated_power"]
    assert power["value"] == 800 and power["provenance"] == "HUMAN" and power["confidence"] is None
    state = {**deepcopy(state), "review_result": {"decision": "RE_EXTRACT", "retry_fields": ["rated_power"], "reason": "test", "can_register": False}}
    calls = len(transport.calls)
    incoming = execute_agent(registry, "extraction", state)
    assert len(transport.calls) == calls and incoming["extracted_product"]["attributes"] == {}
    state["extracted_product"] = merge_extraction_retry(state, incoming["extracted_product"])
    state.update(execute_agent(registry, "ontology", state))
    assert apply_overrides(state, ontology)["normalized_product"]["attributes"]["rated_power"] == power
    approved = graph.invoke(Command(resume={"action": "APPROVE"}), config)
    assert approved["case_status"] == "REGISTERED" and approved["final_product"]["attributes"]["rated_power"]["value"] == 800
    assert count_runs(approved, "extraction") == 1
    assert ontology.validate_semantics(approved["final_product"])["valid"]


def conflicted_graph(ontology, config):
    docs = [document(), {"source_file": "speed.txt", "text": "Rated Speed: 3000 rpm", "page": None}]
    transport = RecordingTransport(fixture_handler)
    graph = build_workflow(document_registry(ontology, docs, transport), ontology=ontology)
    result = graph.invoke(initial_state(), config)
    return graph, result, transport


def test_required_conflict_retry_limit_then_human_repair(ontology, config):
    graph, result, transport = conflicted_graph(ontology, config)
    assert result["case_status"] == "NEEDS_FIX"
    assert result["extraction_retry_count"] == 1 and count_runs(result, "extraction") == 2
    assert result["review_result"]["reason"] == "Extraction retry limit reached."
    assert result["__interrupt__"][0].value["kind"] == "human_review"
    assert len(transport.calls) == 4  # Two documents per run, one additional run.
    assert all(c["payload"]["requested_fields"] == ["rated_speed"] for c in transport.calls[2:])
    assert result["normalized_product"]["attributes"]["rated_speed"]["value"] is None
    repaired = graph.invoke(Command(resume={"action": "EDIT", "edits": {"attributes.rated_speed": {"value": 3000, "unit": "rpm"}}}), config)
    assert repaired["review_result"]["can_register"]
    approved = graph.invoke(Command(resume={"action": "APPROVE"}), config)
    assert approved["final_product"]["attributes"]["rated_speed"]["provenance"] == "HUMAN"


@pytest.mark.parametrize("optional", [False, True])
def test_human_class_change_rechecks_required_to_optional_or_outside_conflict(ontology, config, optional):
    target = "Motor"
    if optional:
        definition = ontology.definition.model_dump(mode="json")
        definition["classes"]["OptionalSpeedMotor"] = {"parent": "BLDCMotor", "optional_properties": {
            "rated_speed": definition["classes"]["BLDCMotor"]["required_properties"]["rated_speed"]}}
        ontology = OntologyService(definition=definition)
        target = "OptionalSpeedMotor"
    graph, _, transport = conflicted_graph(ontology, config)
    result = graph.invoke(Command(resume={"action": "EDIT", "changed_class": target}), config)
    assert result["__interrupt__"][0].value["kind"] == "error"
    errors = unresolved_errors(result["error_events"])
    assert errors[-1]["stage"] == "ontology" and errors[-1]["exception_type"] == "DocumentConflictError"
    assert result["manual_overrides"]["product_class"] == target
    assert "final_product" not in result
    graph.invoke(Command(resume={"action": "STOP"}), config)


def test_deterministic_optional_conflict_retry_reproduces_error_then_stop(ontology, config):
    docs = [document(), {"source_file": "weight.txt", "text": "Weight: 800 g", "page": None}]
    transport = RecordingTransport(fixture_handler)
    graph = build_workflow(document_registry(ontology, docs, transport), ontology=ontology)
    first = graph.invoke(initial_state(), config)
    assert first["__interrupt__"][0].value["actions"] == ["RETRY", "STOP"]
    assert unresolved_errors(first["error_events"])[0]["exception_type"] == "DocumentConflictError"
    retried = graph.invoke(Command(resume={"action": "RETRY"}), config)
    assert retried["__interrupt__"][0].value["kind"] == "error"
    assert len(unresolved_errors(retried["error_events"])) == 2
    assert all(e["recoverable"] for e in unresolved_errors(retried["error_events"]))
    assert retried["extraction_retry_count"] == 0 and len(transport.calls) == 4
    stopped = graph.invoke(Command(resume={"action": "STOP"}), config)
    assert stopped["case_status"] == "STOPPED" and "final_product" not in stopped
    assert not graph.get_state(config).next


def test_deterministic_classification_error_retry_does_not_reextract(ontology, config):
    transport = RecordingTransport(lambda task, payload: {"candidate_class": "Unknown", "attributes": {}})
    graph = build_workflow(document_registry(ontology, [document()], transport), ontology=ontology)
    first = graph.invoke(initial_state(), config)
    assert unresolved_errors(first["error_events"])[0]["exception_type"] == "OntologyClassificationError"
    retried = graph.invoke(Command(resume={"action": "RETRY"}), config)
    assert retried["__interrupt__"][0].value["kind"] == "error"
    assert count_runs(retried, "ontology") == 2 and count_runs(retried, "extraction") == 1
    assert len(transport.calls) == 1
    assert graph.invoke(Command(resume={"action": "STOP"}), config)["case_status"] == "STOPPED"


def test_low_llm_class_score_remaps_then_manual_class_supersedes_it(ontology, config):
    transport = RecordingTransport(fixture_handler)
    graph = build_workflow(document_registry(ontology, [document()], transport, classify_with_llm=True), ontology=ontology)
    result = graph.invoke(initial_state(), config)
    assert result["case_status"] == "NEEDS_FIX" and result["ontology_retry_count"] == 1
    assert result["extraction_retry_count"] == 0 and count_runs(result, "ontology") == 2
    ontology_calls = sum(c["task"] == "ontology" for c in transport.calls)
    repaired = graph.invoke(Command(resume={"action": "EDIT", "changed_class": "BLDCMotor"}), config)
    assert repaired["review_result"]["can_register"] and repaired["ontology_mapping"]["confidence"] == 1
    assert sum(c["task"] == "ontology" for c in transport.calls) == ontology_calls
    assert graph.invoke(Command(resume={"action": "APPROVE"}), config)["case_status"] == "REGISTERED"
