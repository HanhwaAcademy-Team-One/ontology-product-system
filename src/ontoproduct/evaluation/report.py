def markdown_report(report):
    lines = [
        "# OntoProduct Evaluation",
        "",
        f"Run: {report['run_id']}",
        f"Generated (UTC): {report['generated_at']}",
        "",
        f"Dataset: {report['dataset']['name']} ({report['dataset']['case_count']} cases)",
        "",
        report["dataset"]["limitations"],
        "",
    ]
    if "mode" in report:
        coverage = report["truth_coverage"]
        calls = report["calls"]
        lines += [
            f"Mode: {report['mode']}",
            f"Service calls: {report['call_count']} (SDK retries excluded)",
            f"Normalized truth: {coverage['normalized_truth_groups']} known / {coverage['unknown_normalized_truth_groups']} unknown; independent human review: {coverage['independently_human_reviewed']}",
            "Provider/model: "
            + ", ".join(sorted({f"{c['provider']}/{c['model']}" for c in calls})),
            "Prompt versions: "
            + ", ".join(sorted({f"{c['task']}={c['prompt_version']}" for c in calls})),
            f"Failures/limits: {report['failures']} / {report.get('limited_cases', [])}",
            f"Manifest SHA-256: {report['manifest_sha256']}",
            f"Verification SHA-256: {report['verification_sha256']}",
            "",
        ]
    for suite in report["suites"]:
        lines += [
            f"## {suite['label']}",
            "",
            suite["input_mode"],
            "",
            "| Metric | Calculated value | Numerator / denominator |",
            "| --- | ---: | ---: |",
        ]
        for name, metric in suite["metrics"].items():
            if isinstance(metric, dict) and "value" in metric:
                value = "N/A" if metric["value"] is None else f"{metric['value']:.4f}"
                lines.append(
                    f"| {name} | {value} | {metric['correct']} / {metric['total']} |"
                )
        lines += [
            "",
            "Agents: "
            + ", ".join(
                f"{a['name']} ({a['provider']}, {'Mock' if a['is_mock'] else 'Real'})"
                for a in suite["agents"]
            ),
            "",
        ]
        for sample in suite["samples"]:
            lines.append(
                f"- {sample['ground_truth']['case_id']}: source SHA-256 {sample['ground_truth']['source_sha256']}"
            )
            if "observed_outcome" in sample:
                lines.append(
                    f"  Expected: {sample['expected_outcome']}; observed: {sample['observed_outcome']}; status: {sample['case_status']}; after-human result: {sample['integration_after_human']}"
                )
                for issue in (
                    sample["outputs"].get("validation_result", {}).get("issues", [])
                ):
                    lines.append(
                        f"  {issue['field']} / {issue['code']}: {issue['message']}"
                    )
                for error in sample["outputs"].get("error_events", []):
                    lines.append(
                        f"  Error: {error['stage']} / {error['exception_type']} / {error['status']}"
                    )
        if "mode" in report:
            lines.append(
                "Agent versions: "
                + ", ".join(f"{a['name']}={a['version']}" for a in suite["agents"])
            )
        lines.append("")
    lines += ["## Metric definitions", ""]
    lines += [f"- {name}: {value}" for name, value in report["definitions"].items()]
    return "\n".join(lines) + "\n"
