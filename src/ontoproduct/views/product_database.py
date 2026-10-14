import streamlit as st

from ontoproduct.views.presentation import CLASS_LABELS
from ontoproduct.views.resources import current_runtime


def render():
    runtime = current_runtime()
    st.title("제품 데이터베이스")
    st.caption("등록 승인으로 저장한 제품을 확인하세요.")
    search = st.text_input(
        "제품명 검색", key="product_search", placeholder="예: DM-500"
    )
    product_class = st.selectbox(
        "분류 필터",
        [None, *runtime.ontology.definition.classes],
        format_func=lambda value: (
            "전체 분류" if value is None else CLASS_LABELS.get(value, value)
        ),
        key="product_class_filter",
    )
    records = runtime.products.list(
        search=search, product_class=product_class
    )
    st.caption(f"검색 결과 {len(records)}개 · 최신 최대 500개를 표시합니다.")
    st.metric("전체 저장 제품", runtime.products.count())
    if not records:
        st.info("표시할 제품이 없습니다. 제품 등록 화면에서 문서를 업로드하고 승인하세요.")
        return
    st.dataframe(
        [
            {
                "제품명": r["product"].get("product_name") or "—",
                "분류": CLASS_LABELS.get(
                    r["product"]["product_class"], r["product"]["product_class"]
                ),
                "등록 시각 (UTC)": r["created_at"],
            }
            for r in records
        ],
        hide_index=True,
        width="stretch",
    )
    selected = st.selectbox(
        "제품 상세",
        [r["product_id"] for r in records],
        format_func=lambda value: next(
            f"{r['product'].get('product_name')} · {value[:8]}"
            for r in records
            if r["product_id"] == value
        ),
        key="selected_product",
    )
    record = runtime.products.get(selected)
    st.caption(
        f"제품 ID: {record['product_id']} · 등록 작업: {record['registration_case_id']}"
    )
    st.dataframe(
        [
            {
                "속성": key,
                "값": str(attr["value"]),
                "단위": attr.get("unit") or "—",
                "출처": attr.get("provenance") or "—",
                "AI 신뢰도": attr.get("confidence"),
                "원본": attr.get("source_file") or "—",
                "페이지": attr.get("page"),
                "근거": attr.get("evidence") or "—",
            }
            for key, attr in record["product"]["attributes"].items()
        ],
        hide_index=True,
        width="stretch",
    )
    st.json(record["product"], expanded=True)
    st.download_button(
        "선택 제품 JSON 다운로드",
        runtime.registration.json_bytes(record),
        file_name=f"{record['product_id']}.json",
        mime="application/json",
        on_click="ignore",
        key="download_product",
    )


if __name__ == "__main__":
    render()
