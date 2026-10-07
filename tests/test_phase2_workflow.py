import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest

from ontoproduct.agents.registry import validate_contract
from ontoproduct.agents.duplicate_agent import DuplicateAgent
from ontoproduct.agents.registration_agent import RegistrationAgent
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.schemas.error import unresolved_errors
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.duplicate_service import DuplicateService
from ontoproduct.services.seed_service import seed_products
from ontoproduct.services.workflow_runtime import WorkflowRuntime
from conftest import count_runs, fail_once


def create_case(runtime):
    session = str(uuid4())
    thread = runtime.create_case(session)
    references = [
        runtime.documents.save(session, "motor_spec.pdf", b"%PDF mock"),
        runtime.documents.save(session, "bom.xlsx", b"mock bom"),
    ]
    return thread, references


def edit_speed(runtime, thread):
    list(
        runtime.resume(
            thread,
            {
                "action": "EDIT",
                "edits": {"attributes.rated_speed": {"value": 3000, "unit": "rpm"}},
            },
        )
    )


@pytest.fixture
def runtime(tmp_path):
    value = WorkflowRuntime(ApplicationPaths(tmp_path))
    yield value
    value.close()


def test_sqlite_checkpoint_reopens_before_edit_and_before_approve(tmp_path):
    paths = ApplicationPaths(tmp_path)
    runtime = WorkflowRuntime(paths)
    thread, references = create_case(runtime)
    events = list(runtime.start(thread, references))
    assert runtime.snapshot(thread).values["case_status"] == "NEEDS_FIX"
    assert runtime.products.count() == 0
    assert any(
        mode == "custom" and event.get("event") == "agent_started"
        for mode, event in events
    )
    runtime.close()
    runtime = WorkflowRuntime(paths)
    edit_speed(runtime, thread)
    assert runtime.snapshot(thread).values["case_status"] == "READY_FOR_HUMAN"
    assert runtime.products.count() == 0
    runtime.close()
    runtime = WorkflowRuntime(paths)
    list(runtime.resume(thread, {"action": "APPROVE"}))
    state = runtime.snapshot(thread).values
    assert state["case_status"] == "REGISTERED"
    assert runtime.cases.get(thread)["status"] == "REGISTERED"
    record = runtime.products.get_by_case(thread)
    assert record["product"] == state["final_product"]
    assert (
        json.loads((paths.exports / f"{record['product_id']}.json").read_text())
        == state["final_product"]
    )
    assert (
        list(runtime.resume(thread, {"action": "APPROVE"}))[0][1]["status"]
        == "ALREADY_REGISTERED"
    )
    assert runtime.products.count() == 1
    assert all(Path(ref["path"]).is_file() for ref in state["source_documents"])
    json.dumps(state)
    runtime.close()


def test_export_error_after_db_commit_retries_without_duplicate(runtime):
    thread, references = create_case(runtime)
    list(runtime.start(thread, references))
    edit_speed(runtime, thread)
    original = runtime.registration.export
    attempts = []

    def export(record):
        attempts.append(1)
        if len(attempts) == 1:
            raise OSError("Injected export failure")
        return original(record)

    runtime.registration.export = export
    list(runtime.resume(thread, {"action": "APPROVE"}))
    snapshot = runtime.snapshot(thread)
    assert snapshot.tasks[0].interrupts[0].value["kind"] == "error"
    assert runtime.products.count() == 1
    assert (
        unresolved_errors(snapshot.values["error_events"])[0]["stage"] == "registration"
    )
    list(runtime.resume(thread, {"action": "RETRY"}))
    state = runtime.snapshot(thread).values
    assert state["case_status"] == "REGISTERED"
    assert not unresolved_errors(state["error_events"])
    assert runtime.products.count() == 1
    assert count_runs(state, "registration") == 2


def test_parallel_error_retry_with_sqlite_join(tmp_path):
    def registry_factory(ontology):
        registry = mock_registry(ontology)
        fail_once(registry.get("validation"))
        return registry

    runtime = WorkflowRuntime(
        ApplicationPaths(tmp_path), registry_factory=registry_factory
    )
    thread, references = create_case(runtime)
    list(runtime.start(thread, references))
    assert runtime.cases.get(thread)["status"] == "ERROR"
    assert runtime.snapshot(thread).next == ("error_handler",)
    list(runtime.resume(thread, {"action": "RETRY"}))
    state = runtime.snapshot(thread).values
    assert not unresolved_errors(state["error_events"])
    assert count_runs(state, "validation") == count_runs(state, "duplicate") == 3
    runtime.close()


def test_simultaneous_cases_do_not_mix_state_or_records(runtime):
    cases = [create_case(runtime), create_case(runtime)]

    def run(case):
        thread, references = case
        list(runtime.start(thread, references))
        edit_speed(runtime, thread)
        list(runtime.resume(thread, {"action": "APPROVE"}))
        return runtime.snapshot(thread).values

    with ThreadPoolExecutor(max_workers=2) as executor:
        states = list(executor.map(run, cases))
    assert {s["registration_case_id"] for s in states} == {case[0] for case in cases}
    assert all(state["case_status"] == "REGISTERED" for state in states)
    assert runtime.products.count() == 2


def test_restart_input_and_invalid_approval_do_not_bypass_hitl(runtime):
    thread, references = create_case(runtime)
    list(runtime.start(thread, references))
    with pytest.raises(ValueError):
        list(runtime.start(thread, references))
    list(runtime.resume(thread, {"action": "APPROVE"}))
    assert runtime.snapshot(thread).values["case_status"] == "NEEDS_FIX"
    assert runtime.products.count() == 0


def test_case_graph_is_reused_and_adapters_obey_frozen_contract(runtime):
    thread, references = create_case(runtime)
    assert runtime.graph(thread) is runtime.graph(thread)
    validate_contract(RegistrationAgent(thread, runtime.registration))
    validate_contract(DuplicateAgent(DuplicateService(runtime.products)))
    assert (
        "registration_case_id"
        not in RegistrationAgent(thread, runtime.registration).required_reads
    )


def test_seed_candidates_appear_in_sqlite_workflow(runtime):
    seed_products(runtime.products)
    thread, references = create_case(runtime)
    list(runtime.start(thread, references))
    state = runtime.snapshot(thread).values
    assert "DM-500A" in [c["product_name"] for c in state["duplicate_candidates"]]
    assert all(0 <= c["score"] <= 1 for c in state["duplicate_candidates"])


def test_stopped_case_cannot_be_restarted_by_resume(runtime):
    thread, references = create_case(runtime)
    list(runtime.start(thread, references))
    list(runtime.resume(thread, {"action": "REJECT"}))
    with pytest.raises(ValueError):
        list(runtime.resume(thread, {"action": "APPROVE"}))
    assert runtime.products.count() == 0


def test_interrupted_stream_can_continue_saved_execution(runtime):
    thread, references = create_case(runtime)
    stream = runtime.start(thread, references)
    next(stream)
    stream.close()
    snapshot = runtime.snapshot(thread)
    assert snapshot.next or snapshot.tasks
    assert not any(task.interrupts for task in snapshot.tasks)
    list(runtime.continue_run(thread))
    assert runtime.snapshot(thread).values["case_status"] == "NEEDS_FIX"


def test_same_thread_cannot_run_concurrently(runtime):
    thread, references = create_case(runtime)
    stream = runtime.start(thread, references)
    next(stream)
    try:
        with pytest.raises(ValueError, match="already running"):
            list(runtime.start(thread, references))
    finally:
        stream.close()
