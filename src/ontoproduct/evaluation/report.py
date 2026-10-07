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
        lines.append("")
    lines += ["## Metric definitions", ""]
    lines += [f"- {name}: {value}" for name, value in report["definitions"].items()]
    return "\n".join(lines) + "\n"
