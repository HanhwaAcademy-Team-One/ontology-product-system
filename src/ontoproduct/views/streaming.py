import streamlit as st

from ontoproduct.views.presentation import AGENT_LABELS


def consume(iterator):
    with st.status("등록 워크플로 실행 중", expanded=True) as progress:
        columns = st.columns(3)
        placeholders = {}
        for index, (agent, label) in enumerate(AGENT_LABELS.items()):
            with columns[index % 3]:
                placeholders[agent] = st.empty()
                placeholders[agent].markdown(f"**{label}** · 대기")
        has_error = False
        for mode, event in iterator:
            if mode != "custom":
                continue
            if event.get("event") == "case_already_registered":
                st.info("이미 등록된 작업입니다. 기존 제품을 유지했습니다.")
                continue
            agent = event.get("agent")
            if agent not in placeholders:
                continue
            status = event["status"]
            label = {"running": "🔵 RUNNING", "success": "🟢 SUCCESS",
                     "warning": "🟡 WARNING", "error": "🔴 ERROR"}[status]
            placeholders[agent].markdown(f"**{AGENT_LABELS[agent]}** · {label}  \n시도 {event['attempt']}")
            has_error |= status == "error"
        progress.update(label="오류 확인이 필요합니다" if has_error else "실행 완료 · 결과를 확인하세요",
                        state="error" if has_error else "complete", expanded=has_error)
