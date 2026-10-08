from uuid import uuid4
from pathlib import Path

import streamlit as st

from ontoproduct.views.resources import current_runtime


def main():
    st.set_page_config(
        page_title="OntoProduct", page_icon=":material/category:", layout="wide"
    )
    st.session_state.setdefault("session_id", str(uuid4()))
    st.session_state.setdefault("upload_generation", 0)
    runtime = current_runtime()
    if not st.session_state.get("thread_id") and st.query_params.get("case"):
        candidate = st.query_params["case"]
        if runtime.cases.get(candidate):
            st.session_state.thread_id = candidate
    with st.sidebar:
        st.title("OntoProduct")
        st.caption("제조 제품 등록 · PHASE 3")
    view_directory = Path(__file__).parent / "views"
    page = st.navigation(
        [
            st.Page(
                view_directory / "dashboard.py",
                title="대시보드",
                icon=":material/dashboard:",
                url_path="dashboard",
            ),
            st.Page(
                view_directory / "registration.py",
                title="제품 등록",
                icon=":material/add_box:",
                default=True,
            ),
            st.Page(
                view_directory / "product_database.py",
                title="제품 데이터베이스",
                icon=":material/database:",
                url_path="products",
            ),
            st.Page(
                view_directory / "ontology_explorer.py",
                title="온톨로지 탐색",
                icon=":material/account_tree:",
                url_path="ontology",
            ),
            st.Page(
                view_directory / "agent_monitor.py",
                title="Agent 모니터",
                icon=":material/monitoring:",
                url_path="agents",
            ),
            st.Page(
                view_directory / "evaluation.py",
                title="평가",
                icon=":material/analytics:",
                url_path="evaluation",
            ),
        ]
    )
    with st.sidebar:
        st.divider()
        if st.button("새 등록 작업", key="new_case", width="stretch"):
            st.session_state.thread_id = None
            st.session_state.upload_generation += 1
            st.query_params.pop("case", None)
            st.switch_page(view_directory / "registration.py")
        cases = runtime.cases.list()
        selected = st.selectbox(
            "최근 작업",
            options=[case["thread_id"] for case in cases],
            index=None,
            placeholder="저장된 작업 선택",
            format_func=lambda value: next(
                f"{c['thread_id'][:8]} · {c['status']}"
                for c in cases
                if c["thread_id"] == value
            ),
            key="resume_case_selection",
        )
        if st.button(
            "선택한 작업 불러오기",
            key="load_case",
            disabled=selected is None,
            width="stretch",
        ):
            st.session_state.thread_id = selected
            st.query_params["case"] = selected
            st.switch_page(
                view_directory / "registration.py", query_params={"case": selected}
            )
        st.caption("작업과 제품은 SQLite에 저장됩니다.")
    page.run()


if __name__ == "__main__":
    main()
