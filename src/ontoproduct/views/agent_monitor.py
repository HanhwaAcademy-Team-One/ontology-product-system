import streamlit as st

from ontoproduct.services.analytics_service import AnalyticsService
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.views.presentation import AGENT_LABELS
from ontoproduct.views.resources import get_runtime


def render():
    runtime = get_runtime(str(ApplicationPaths.from_environment().root))
    st.title("Agent 모니터")
    st.caption("Registry 메타데이터와 저장된 실행 이력입니다. Health는 Agent health_check 응답이며 외부 모델 연결 검사가 아닙니다.")
    cases = runtime.cases.list()
    selected = st.selectbox("실행 이력 범위", [None, *[case["thread_id"] for case in cases]],
                            format_func=lambda value: "최근 최대 100개 작업" if value is None else value[:8],
                            key="monitor_case")
    if st.button("모니터 새로고침", key="refresh_monitor"):
        st.rerun()
    result = AnalyticsService(runtime).monitor(selected)
    status_tab, history_tab, graph_tab = st.tabs(["Agent 상태", "실행 이력", "Workflow Graph"])
    with status_tab:
        st.caption(f"{result['sample_count']}개 작업의 execution_id별 최종 이벤트를 집계했습니다. 평균 시간은 실제 측정값입니다.")
        st.dataframe([{"Agent": agent["name"], "역할": AGENT_LABELS[agent["name"]],
                       "Provider": agent["provider"], "Version": agent["version"],
                       "모드": "Mock" if agent["is_mock"] else "Real",
                       "Health": "응답 정상" if agent["health"] else "응답 실패",
                       "최근 상태": agent["latest_status"].upper(), "실행 수": agent["executions"],
                       "오류 수": agent["errors"], "평균 실행 시간 (초)": agent["average_execution_time"]}
                      for agent in result["agents"]], hide_index=True, width="stretch")
        name = st.selectbox("Agent 계약", [agent["name"] for agent in result["agents"]], key="monitor_agent")
        agent = next(agent for agent in result["agents"] if agent["name"] == name)
        for label, key in [("Required Reads", "required_reads"), ("Optional Reads", "optional_reads"), ("Writes", "writes")]:
            st.write(f"**{label}**: " + (", ".join(agent[key]) or "—"))
    with history_tab:
        if result["logs"]:
            st.dataframe(result["logs"], hide_index=True, width="stretch")
        else:
            st.info("아직 실행 이력이 없습니다.")
        st.subheader("오류 이벤트")
        if result["errors"]:
            st.dataframe(result["errors"], hide_index=True, width="stretch")
        else:
            st.info("기록된 오류가 없습니다.")
    with graph_tab:
        diagram = runtime.compiled_diagram()
        st.caption("실제 compiled graph에서 생성했습니다. 점선은 조건부 경로이며 Validation/Duplicate는 barrier join으로 합류합니다.")
        st.mermaid_chart(diagram)
        st.download_button("Graph Mermaid 다운로드", diagram, file_name="workflow.mmd",
                           on_click="ignore", key="download_graph")
        with st.expander("Mermaid 소스"):
            st.code(diagram, language="mermaid")


if __name__ == "__main__":
    render()
