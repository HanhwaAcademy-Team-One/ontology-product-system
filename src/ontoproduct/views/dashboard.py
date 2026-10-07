from pathlib import Path
import streamlit as st

from ontoproduct.services.analytics_service import AnalyticsService
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.views.presentation import CLASS_LABELS, STATUS_LABELS
from ontoproduct.views.resources import get_runtime


def render():
    runtime = get_runtime(str(ApplicationPaths.from_environment().root))
    overview = AnalyticsService(runtime).overview()
    st.title("대시보드")
    st.caption(
        "SQLite에 저장된 제품과 등록 작업 현황입니다. 현재 정보 추출은 Mock 모드입니다."
    )
    if st.button("현황 새로고침", key="refresh_dashboard"):
        st.rerun()
    products, cases = overview["products"], overview["cases"]
    columns = st.columns(4)
    columns[0].metric("등록 제품", products["registered"])
    columns[1].metric("예제 제품", products["seed"])
    columns[2].metric("전체 등록 작업", cases["total"])
    columns[3].metric(
        "검토 대기 작업",
        sum(
            cases["statuses"].get(status, 0)
            for status in ["NEEDS_FIX", "READY_FOR_HUMAN"]
        ),
    )
    left, right = st.columns(2)
    with left:
        st.subheader("작업 상태")
        if cases["statuses"]:
            st.bar_chart(
                [
                    {"상태": STATUS_LABELS.get(status, status), "작업 수": count}
                    for status, count in cases["statuses"].items()
                ],
                x="상태",
                y="작업 수",
            )
        else:
            st.info("아직 등록 작업이 없습니다.")
    with right:
        st.subheader("제품 분류")
        if products["groups"]:
            st.bar_chart(
                [
                    {
                        "분류": CLASS_LABELS.get(
                            group["product_class"], group["product_class"]
                        ),
                        "구분": "예제" if group["origin"] == "SEED" else "등록 제품",
                        "제품 수": group["count"],
                    }
                    for group in products["groups"]
                ],
                x="분류",
                y="제품 수",
                color="구분",
            )
        else:
            st.info("아직 저장된 제품이 없습니다.")
    st.subheader("최근 작업")
    st.caption(
        f"아래 실행 이력 집계는 최근 최대 100개 작업 중 {overview['sample_count']}개 기준입니다."
    )
    columns = st.columns(3)
    columns[0].metric("미해결 오류", overview["open_errors"])
    columns[1].metric("추출 추가 실행", overview["extraction_retries"])
    columns[2].metric("분류 추가 실행", overview["ontology_retries"])
    recent = overview["recent"]
    if recent:
        st.dataframe(
            [
                {
                    "작업": item["case"]["thread_id"][:8],
                    "제품명": item["state"]
                    .get("normalized_product", {})
                    .get("product_name")
                    or "—",
                    "상태": STATUS_LABELS.get(
                        item["case"]["status"], item["case"]["status"]
                    ),
                    "수정 시각 (UTC)": item["case"]["updated_at"],
                }
                for item in recent
            ],
            hide_index=True,
            width="stretch",
        )
        selected = st.selectbox(
            "이어갈 작업",
            [item["case"]["thread_id"] for item in recent],
            key="dashboard_case",
            format_func=lambda value: next(
                f"{item['case']['thread_id'][:8]} · {item['case']['status']}"
                for item in recent
                if item["case"]["thread_id"] == value
            ),
        )
        if st.button("등록 화면에서 열기", key="open_dashboard_case", type="primary"):
            st.session_state.thread_id = selected
            st.switch_page(
                Path(__file__).parent / "registration.py",
                query_params={"case": selected},
            )
    else:
        if st.button("제품 등록 시작", key="dashboard_start", type="primary"):
            st.switch_page(Path(__file__).parent / "registration.py")


if __name__ == "__main__":
    render()
