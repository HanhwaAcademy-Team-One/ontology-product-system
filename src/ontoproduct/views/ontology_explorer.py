import streamlit as st

from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.views.presentation import CLASS_LABELS, LABELS, parse_value
from ontoproduct.views.resources import get_runtime
from ontoproduct.views.ontology_graphs import render as render_graphs


def render():
    runtime = get_runtime(str(ApplicationPaths.from_environment().root))
    ontology = runtime.ontology
    st.title("온톨로지 탐색")
    st.caption("클래스 상속과 필수·선택 속성, 허용 단위 및 범위를 확인하세요.")
    classes = list(ontology.definition.classes)
    names = {name: f"c{index}" for index, name in enumerate(classes)}
    diagram = ["graph TD"]
    for name in classes:
        diagram.append(f'    {names[name]}["{CLASS_LABELS.get(name, name)} ({name})"]')
        parent = ontology.get_parent(name)
        if parent:
            diagram.append(f"    {names[parent]} --> {names[name]}")
    st.mermaid_chart("\n".join(diagram))
    selected = st.selectbox("제품 분류 탐색", classes, index=classes.index("BLDCMotor") if "BLDCMotor" in classes else 0, key="ontology_class",
                            format_func=lambda name: CLASS_LABELS.get(name, name))
    chain = [*reversed(ontology.get_ancestors(selected)), selected]
    st.write("상속 경로: " + " → ".join(chain))
    required = ontology.resolve_required_properties(selected)
    props = ontology.resolve_properties(selected)
    rows = []
    for key, prop in props.items():
        owner = next(name for name in reversed(chain)
                     if key in ontology.get_class(name).required_properties or key in ontology.get_class(name).optional_properties)
        rows.append({"속성": LABELS.get(key, key), "키": key, "필수": key in required, "정의 클래스": owner,
                     "유형": prop.type, "표준 단위": prop.canonical_unit or "—",
                     "허용 단위": ", ".join(prop.units) or "—",
                     "최솟값": "—" if prop.minimum is None else str(prop.minimum),
                     "최댓값": "—" if prop.maximum is None else str(prop.maximum)})
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.info("이 클래스에는 상속된 속성을 포함해 정의된 속성이 없습니다.")
    convertible = [key for key, prop in props.items() if prop.units]
    if convertible:
        with st.expander("단위 정규화 미리보기"):
            key = st.selectbox("변환 속성", convertible, format_func=lambda value: LABELS.get(value, value), key="preview_property")
            value = st.text_input("변환할 값", value="0.5", key="preview_value")
            unit = st.selectbox("입력 단위", props[key].units, key="preview_unit")
            if st.button("단위 변환", key="preview_convert"):
                try:
                    number = parse_value(value, props[key].type)
                    normalized, canonical = ontology.normalize_unit(props[key], number, unit)
                    st.success(f"{number} {unit} → {normalized} {canonical}")
                except ValueError as exc:
                    st.error(str(exc))
    with st.expander("온톨로지 원본 정의"):
        st.json(ontology.definition.model_dump(mode="json"), expanded=False)
    render_graphs(runtime, selected)


if __name__ == "__main__":
    render()
