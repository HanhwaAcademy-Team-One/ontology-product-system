"""Read-only semantic ontology and product graph views."""

import json

import streamlit as st
from rdflib.namespace import RDFS

from ontoproduct.services.ontology_visualization import OntologyVisualization


def _graph_details(viewer, graph, diagram, *, key, filename):
    st.mermaid_chart(diagram["mermaid"])
    st.caption(
        f"표시 노드 {len(diagram['nodes'])}개 · 관계 {len(diagram['edges'])}개 · 전체 RDF 데이터 {len(graph)}개"
    )
    with st.expander("그래프 데이터와 원본 RDF"):
        st.dataframe(viewer.triple_rows(graph), hide_index=True, width="stretch")
        st.json({"nodes": diagram["nodes"], "edges": diagram["edges"]}, expanded=False)
        st.code(graph.serialize(format="turtle"), language="turtle")
    left, right = st.columns(2)
    left.download_button(
        "RDF 다운로드",
        graph.serialize(format="turtle"),
        file_name=f"{filename}.ttl",
        mime="text/turtle",
        key=f"{key}_rdf",
        on_click="ignore",
    )
    right.download_button(
        "그래프 JSON 다운로드",
        json.dumps(
            {"nodes": diagram["nodes"], "edges": diagram["edges"]},
            ensure_ascii=False,
            indent=2,
        ),
        file_name=f"{filename}_graph.json",
        mime="application/json",
        key=f"{key}_json",
        on_click="ignore",
    )


def render(runtime, selected_class):
    model = runtime.ontology.semantic_model
    if model is None:
        st.info("이 온톨로지에는 시각화할 의미 모델이 없습니다.")
        return
    viewer = OntologyVisualization(model)
    st.subheader("개념 관계와 제품 데이터")
    structure, products = st.tabs(["온톨로지 관계", "제품 데이터 그래프"])
    with structure:
        scope = st.radio(
            "그래프 범위",
            ["선택 제품군", "전체 구조"],
            horizontal=True,
            key="semantic_graph_scope",
        )
        graph = viewer.rdf.ontology_graph()
        diagram = viewer.diagram(
            graph,
            kind="ontology",
            product_class=selected_class if scope == "선택 제품군" else None,
        )
        st.caption(
            "보라색: 자체 개념·내부 출처 · 분홍색: 물리량 종류 · 초록색: 단위 · 회색: XSD 데이터 타입. 화살표의 이름은 실제 RDF 관계입니다."
        )
        _graph_details(
            viewer, graph, diagram, key="ontology_graph", filename="product_ontology"
        )
        with st.expander("클래스·속성·관계 정의"):
            st.json(model.model.model_dump(mode="json"), expanded=False)
    with products:
        source = st.selectbox(
            "제품 데이터 선택", ["샘플 사양", "저장된 제품"], key="rdf_product_source"
        )
        if source == "샘플 사양":
            examples = viewer.example_graphs()
            if not examples:
                st.info("표시할 샘플 제품이 없습니다.")
                return

            def label(key):
                root = next(examples[key].subjects(None, viewer.op.ProductModel))
                return str(examples[key].value(root, RDFS.label) or key)

            keys = list(examples)
            selected = st.selectbox(
                "샘플 제품",
                keys,
                index=keys.index("motor") if "motor" in keys else 0,
                format_func=label,
                key="rdf_product_example",
            )
            graph, filename = examples[selected], f"example_{selected}"
            st.caption(
                "모터·베어링 샘플 사양입니다. 원문 값과 표준 단위로 변환한 값을 함께 확인할 수 있습니다."
            )
        else:
            records = runtime.products.list()
            if not records:
                st.info(
                    "저장된 제품이 없습니다. 샘플 사양을 선택하면 예제 그래프를 볼 수 있습니다."
                )
                return
            lookup = {record["product_id"]: record for record in records}
            selected = st.selectbox(
                "저장 제품",
                list(lookup),
                format_func=lambda key: (
                    f"{lookup[key]['product'].get('product_name') or key} · {lookup[key]['product']['product_class']}"
                ),
                key="rdf_stored_product",
            )
            try:
                graph = runtime.ontology.to_rdf(
                    lookup[selected]["product"], record_id=selected
                )
            except ValueError as exc:
                st.error(f"이 제품의 RDF 그래프를 만들 수 없습니다: {exc}")
                return
            filename = "stored_product"
        include_evidence = st.checkbox(
            "파일·페이지·원문 근거도 그래프에 표시", key="rdf_show_evidence"
        )
        diagram = viewer.diagram(
            graph, kind="product", include_evidence=include_evidence
        )
        st.caption(
            "파란색: 제품 모델 · 노란색: 제조사 · 청록색: 물리량 값 · 주황색: 값 · 초록색: 단위 · 분홍색: 물리량 종류 · 보라색: 자체 개념·내부 출처"
        )
        _graph_details(viewer, graph, diagram, key="product_graph", filename=filename)
        st.dataframe(viewer.attribute_rows(graph), hide_index=True, width="stretch")
        if st.button("사양 제약 검사", key="rdf_validate_product"):
            result = viewer.rdf.validate_graph(graph)
            if result["valid"]:
                st.success("필수값·수치·단위·물리량·치수 관계 검사를 통과했습니다.")
            else:
                st.error("사양 제약을 만족하지 않는 항목이 있습니다.")
                st.dataframe(result["issues"], hide_index=True, width="stretch")
