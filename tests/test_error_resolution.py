from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest

from ontoproduct.agents.real_registry import build_document_registry
from ontoproduct.evaluation.document_runner import ReferenceLlm, load_cases
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.parser_service import ParserService
from ontoproduct.services.workflow_runtime import WorkflowRuntime

DATA = Path(__file__).parents[1] / "inputdata"


@pytest.mark.parametrize("case_id", ["D004", "D005"])
def test_deterministic_conflict_blocks_retry_and_new_corrected_case_works(
    tmp_path, case_id
):
    [case] = load_cases(DATA, [case_id])
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
        state = runtime.snapshot(thread).values
        assert state["error_events"][0]["exception_type"] == "DocumentConflictError"
        assert state["error_events"][0]["recoverable"] is False
        assert runtime.snapshot(thread).tasks[0].interrupts[0].value["actions"] == [
            "STOP"
        ]
        list(runtime.resume(thread, {"action": "RETRY"}))
        assert runtime.snapshot(thread).values["error_events"] == state["error_events"]
        list(runtime.resume(thread, {"action": "STOP"}))
        stopped = runtime.snapshot(thread).values
        assert stopped["case_status"] == "STOPPED"
        assert stopped["source_documents"] == refs
        assert runtime.products.count() == 0
        corrected = deepcopy(case)
        corrected["documents"][1] = deepcopy(corrected["documents"][0])

        def corrected_factory(ontology):
            transport = ReferenceLlm(corrected)
            return build_document_registry(
                ontology,
                parser_service=ParserService(paths.uploads),
                llm_services={"extraction": transport, "ontology": transport},
            )

        runtime.registry_factory = corrected_factory
        new_thread = runtime.create_case(session)
        first_bytes = (DATA / case["files"][0]).read_bytes()
        new_refs = [
            runtime.documents.save(session, Path(f).name, first_bytes)
            for f in case["files"]
        ]
        list(runtime.start(new_thread, new_refs))
        assert runtime.snapshot(new_thread).values["review_result"]["can_register"]
        assert runtime.products.count() == 0
        list(runtime.resume(new_thread, {"action": "APPROVE"}))
        list(runtime.resume(new_thread, {"action": "APPROVE"}))
        assert runtime.products.count() == 1
        assert runtime.snapshot(thread).values == stopped
    finally:
        runtime.close()


def test_legacy_recoverable_conflict_command_is_blocked(monkeypatch):
    from ontoproduct.graph import nodes

    payloads = []

    def interrupt(payload):
        payloads.append(payload)
        return {"action": "RETRY"}

    monkeypatch.setattr(nodes, "interrupt", interrupt)
    error = {
        "error_id": "old",
        "stage": "extraction",
        "status": "OPEN",
        "recoverable": True,
        "exception_type": "DocumentConflictError",
    }
    command = nodes.WorkflowNodes.error_handler({"error_events": [error]})
    assert payloads[0]["actions"] == ["STOP"]
    assert command.goto == "error_handler"


@pytest.mark.parametrize(
    "exception_type,retry", [("DocumentConflictError", False), ("TimeoutError", True)]
)
def test_error_ui_respects_legacy_conflict_and_transient_retry(exception_type, retry):
    from streamlit.testing.v1 import AppTest

    payload = {
        "errors": [
            {
                "stage": "extraction",
                "message": "test",
                "recoverable": True,
                "exception_type": exception_type,
            }
        ],
        "actions": ["RETRY", "STOP"],
    }
    page = AppTest.from_string(
        "from ontoproduct.views.registration import _error_review\n"
        + f"_error_review(None, 'case', {payload!r})"
    ).run()
    assert not page.exception
    assert any(b.key == "retry_error" for b in page.button) is retry
    assert any(b.key == "stop_error" for b in page.button)
    if not retry:
        assert any("새 등록 작업" in item.value for item in page.info)
