import json
from pathlib import Path
import streamlit as st

from ontoproduct.evaluation.document_runner import load_cases, run_document_evaluation
from ontoproduct.evaluation.report import markdown_report
from ontoproduct.services.application_paths import ApplicationPaths


def render():
    st.title("평가")
    st.caption(
        "inputdata 문서를 실제 Parser·Extraction·Ontology·Validation·Reviewer Agent로 처리하고 manifest 정답과 비교합니다."
    )
    dataset = Path.cwd() / "inputdata"
    output = ApplicationPaths.from_environment().root / "evaluation"
    try:
        groups = load_cases(dataset)
    except (ValueError, OSError) as exc:
        st.error(f"평가 데이터를 읽을 수 없습니다: {exc}")
        return
    st.info(
        f"평가 사례 {len(groups)}개입니다. 모델 호출 대신 정답 기반 참조 응답을 사용하므로 LLM 정확도가 아니라 파이프라인 동작을 측정합니다."
    )
    if st.button("평가 실행", type="primary", key="run_evaluation"):
        with st.spinner("Agent 출력과 정답을 비교하고 있습니다."):
            try:
                run_document_evaluation(dataset, output)
            except Exception as exc:
                st.error(f"평가 실행 실패: {exc}")
                return
        st.success("계산 결과와 실행 출력을 저장했습니다.")
    reports = sorted(
        output.glob("*/evaluation.json"), key=lambda path: path.stat().st_mtime
    )
    if not reports:
        st.info("평가 실행을 누르면 계산된 결과가 표시됩니다.")
        return
    report_path = reports[-1]
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        st.error(f"평가 보고서를 읽을 수 없습니다: {exc}")
        return
    st.caption(
        f"평가 시각 (UTC): {report['generated_at']} · Run ID: {report['run_id']}"
    )
    left, right = st.columns(2)
    left.download_button(
        "평가 JSON 다운로드",
        json.dumps(report, ensure_ascii=False, indent=2),
        file_name="evaluation.json",
        mime="application/json",
        on_click="ignore",
        key="download_evaluation_json",
    )
    right.download_button(
        "평가 보고서 다운로드",
        markdown_report(report),
        file_name="evaluation.md",
        mime="text/markdown",
        on_click="ignore",
        key="download_evaluation_report",
    )
    tabs = st.tabs([suite["label"] for suite in report["suites"]])
    for index, (tab, suite) in enumerate(zip(tabs, report["suites"])):
        with tab:
            st.subheader(suite["label"])
            st.write(suite["input_mode"])
            st.dataframe(
                [
                    {
                        "지표": name,
                        "계산 결과": "N/A"
                        if metric["value"] is None
                        else f"{metric['value']:.2%}",
                        "분자": metric["correct"],
                        "분모": metric["total"],
                    }
                    for name, metric in suite["metrics"].items()
                    if isinstance(metric, dict) and "value" in metric
                ],
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "N/A는 평가 대상이 없는 경우입니다. 지표 정의와 원본 출력은 다운로드 보고서에 포함됩니다."
            )
            selected = st.selectbox(
                "사례별 출력",
                [sample["ground_truth"]["case_id"] for sample in suite["samples"]],
                key=f"evaluation_sample_{index}",
            )
            sample = next(
                sample
                for sample in suite["samples"]
                if sample["ground_truth"]["case_id"] == selected
            )
            st.json(sample["outputs"], expanded=False)
    with st.expander("지표 계산 정의"):
        for name, definition in report["definitions"].items():
            st.write(f"**{name}**: {definition}")


if __name__ == "__main__":
    render()
