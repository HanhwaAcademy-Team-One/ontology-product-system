import json
from pathlib import Path
from uuid import uuid4

from ontoproduct.evaluation.runner import run_evaluation
from ontoproduct.graph.workflow import build_workflow
from ontoproduct.services.analytics_service import AnalyticsService
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.seed_service import seed_products
from ontoproduct.services.workflow_runtime import WorkflowRuntime


def test_final_upload_checkpoint_review_registration_analytics_evaluation(tmp_path):
    paths = ApplicationPaths(tmp_path)
    runtime = WorkflowRuntime(paths)
    seed_products(runtime.products)
    session = str(uuid4())
    case = runtime.create_case(session)
    refs = [
        runtime.documents.save(session, "motor.pdf", b"%PDF fixture"),
        runtime.documents.save(session, "bom.xlsx", b"fixture"),
    ]
    list(runtime.start(case, refs))
    assert runtime.snapshot(case).values["case_status"] == "NEEDS_FIX"
    assert AnalyticsService(runtime).overview()["cases"]["statuses"]["NEEDS_FIX"] == 1
    list(
        runtime.resume(
            case,
            {
                "action": "EDIT",
                "edits": {"attributes.rated_speed": {"value": 3000, "unit": "rpm"}},
            },
        )
    )
    runtime.close()
    runtime = WorkflowRuntime(paths)
    assert runtime.snapshot(case).values["case_status"] == "READY_FOR_HUMAN"
    list(runtime.resume(case, {"action": "APPROVE"}))
    list(runtime.resume(case, {"action": "APPROVE"}))
    record = runtime.products.get_by_case(case)
    assert (
        json.loads((paths.exports / f"{record['product_id']}.json").read_text())
        == record["product"]
    )
    overview = AnalyticsService(runtime).overview()
    assert overview["products"]["registered"] == 1
    assert overview["products"]["seed"] == 3
    assert overview["cases"]["statuses"] == {"REGISTERED": 1}
    assert overview["open_errors"] == 0
    monitor = AnalyticsService(runtime).monitor(case)
    assert len(monitor["logs"]) == len({log["execution_id"] for log in monitor["logs"]})
    agents = {agent["name"]: agent for agent in monitor["agents"]}
    assert agents["extraction"]["executions"] == 2
    assert agents["extraction"]["is_mock"]
    assert not agents["registration"]["is_mock"]
    assert agents["registration"]["executions"] == 1
    assert agents["registration"]["average_execution_time"] >= 0
    assert runtime.compiled_diagram() == build_workflow().get_graph().draw_mermaid()
    assert (
        len(runtime.products.list(origin="REGISTRATION", product_class="BLDCMotor"))
        == 1
    )
    assert not runtime.products.list(product_class="Bearing")
    original_count = runtime.products.count()
    report = run_evaluation(
        Path(__file__).resolve().parents[1] / "eval" / "ground_truth",
        paths.root / "evaluation",
    )
    assert report["dataset"]["case_count"] == 3
    assert runtime.products.count() == original_count
    assert runtime.snapshot(case).values["case_status"] == "REGISTERED"
    runtime.close()


def test_empty_analytics_has_no_invented_execution_times(tmp_path):
    runtime = WorkflowRuntime(ApplicationPaths(tmp_path))
    overview = AnalyticsService(runtime).overview()
    assert overview["cases"]["total"] == overview["products"]["total"] == 0
    monitor = AnalyticsService(runtime).monitor()
    assert not monitor["logs"]
    assert all(
        agent["executions"] == 0 and agent["average_execution_time"] is None
        for agent in monitor["agents"]
    )
    assert runtime.cases.summary()["total"] == 0
    runtime.close()
