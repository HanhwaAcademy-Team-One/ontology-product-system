from collections import defaultdict

from ontoproduct.schemas.error import unresolved_errors


class AnalyticsService:
    """Read persisted facts; monitoring never inspects Agent implementation code."""

    def __init__(self, runtime):
        self.runtime = runtime

    def recent_states(self, *, limit=100):
        return [
            {"case": case, "state": self.runtime.snapshot(case["thread_id"]).values}
            for case in self.runtime.cases.list(limit=limit)
        ]

    def overview(self):
        cases = self.runtime.cases.summary()
        products = self.runtime.products.summary()
        recent = self.recent_states()
        return {
            "cases": cases,
            "products": products,
            "recent": recent,
            "sample_count": len(recent),
            "open_errors": sum(
                len(unresolved_errors(item["state"].get("error_events", [])))
                for item in recent
            ),
            "extraction_retries": sum(
                item["state"].get("extraction_retry_count", 0) for item in recent
            ),
            "ontology_retries": sum(
                item["state"].get("ontology_retry_count", 0) for item in recent
            ),
        }

    def monitor(self, thread_id=None):
        items = (
            [
                {
                    "case": self.runtime.cases.get(thread_id),
                    "state": self.runtime.snapshot(thread_id).values,
                }
            ]
            if thread_id
            else self.recent_states()
        )
        logs, errors = [], []
        for item in items:
            if not item["case"]:
                continue
            case_id = item["case"]["thread_id"]
            latest = {}
            for log in item["state"].get("agent_logs", []):
                latest[log["execution_id"]] = {**log, "thread_id": case_id}
            logs.extend(latest.values())
            errors.extend(
                {**error, "thread_id": case_id}
                for error in item["state"].get("error_events", [])
            )
        grouped = defaultdict(list)
        for log in logs:
            grouped[log["agent"]].append(log)
        metadata = self.runtime.agent_metadata(thread_id)
        for agent in metadata:
            executions = grouped[agent["name"]]
            timed = [
                e["execution_time"]
                for e in executions
                if e["status"] != "running" and e["execution_time"] is not None
            ]
            agent["executions"] = len(executions)
            agent["errors"] = sum(e["status"] == "error" for e in executions)
            agent["average_execution_time"] = sum(timed) / len(timed) if timed else None
            agent["latest_status"] = (
                max(executions, key=lambda e: e["timestamp"])["status"]
                if executions
                else "not_run"
            )
        return {
            "agents": metadata,
            "logs": sorted(logs, key=lambda e: e["timestamp"], reverse=True),
            "errors": errors,
            "sample_count": len(items),
        }
