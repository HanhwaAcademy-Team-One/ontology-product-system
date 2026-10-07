from copy import deepcopy

import pytest
from rdflib import Literal
from rdflib.namespace import RDF, RDFS

from ontoproduct.services.ontology_visualization import OntologyVisualization
from ontoproduct.services.product_ontology_service import ProductOntology
from test_streamlit_app import app, fill_speed


def test_diagram_uses_actual_rdf_and_preserves_graph_with_distinct_literal_nodes():
    viewer = OntologyVisualization(ProductOntology())
    graph = viewer.example_graphs()["motor"]
    before = set(graph)
    diagram = viewer.diagram(graph, kind="product")
    labels = {node["label"] for node in diagram["nodes"]}
    assert {"DM-600", "XYZ Motors", "600.0", "unit:W", "qk:Power"} <= labels
    assert any(edge["relation"] == "gr:hasManufacturer" for edge in diagram["edges"])
    assert any(edge["relation"] == "qudt:hasUnit" for edge in diagram["edges"])
    assert not any(edge["relation"] == "op:candidateEvidence" for edge in diagram["edges"])
    detailed = viewer.diagram(graph, kind="product", include_evidence=True)
    assert len(detailed["nodes"]) > len(diagram["nodes"])
    assert any(edge["relation"] == "op:source_file" for edge in detailed["edges"])
    assert set(graph) == before
    assert viewer._node(graph, Literal(24))["id"] != viewer._node(graph, Literal("24"))["id"]


def test_ontology_diagram_focus_shows_inheritance_external_alignment_and_properties():
    viewer = OntologyVisualization(ProductOntology())
    graph = viewer.rdf.ontology_graph()
    full = viewer.diagram(graph, kind="ontology")
    focus = viewer.diagram(graph, kind="ontology", product_class="Bearing")
    assert len(focus["nodes"]) < len(full["nodes"])
    assert any(node["label"] == "Bearing model" for node in focus["nodes"])
    assert not any(node["label"] == "Brushless DC motor model" for node in focus["nodes"])
    assert any(edge["relation"] == "rdfs:subClassOf" for edge in focus["edges"])
    assert any(node["label"] == "iof:MaterialArtifact" for node in focus["nodes"])
    with pytest.raises(ValueError):
        viewer.diagram(graph, kind="other")


def test_attributes_show_raw_and_normalized_values_with_original_evidence():
    viewer = OntologyVisualization(ProductOntology())
    graphs = viewer.example_graphs()
    rows = {row["키"]: row for row in viewer.attribute_rows(graphs["motor"])}
    assert rows["rated_power"]["원문 값"] == "0.6" and rows["rated_power"]["원문 단위"] == "kW"
    assert rows["rated_power"]["정규화 값"] == "600.0" and rows["rated_power"]["표준 단위"] == "W"
    assert rows["rated_power"]["파일"] == "motor_spec.pdf (22222222)" and rows["rated_power"]["페이지"] == "2"
    bearing_rows = viewer.attribute_rows(graphs["bearing"])
    assert "[Sheet: Spec, Row:" in bearing_rows[0]["근거"]
    assert len(viewer.triple_rows(graphs["motor"])) == len(graphs["motor"])


def test_untrusted_labels_cannot_break_mermaid_diagram():
    viewer = OntologyVisualization(ProductOntology())
    graph = viewer.example_graphs()["motor"]
    root = next(graph.subjects(RDF.type, viewer.op.ProductModel))
    injected = '"]\nunsafe --> injected\n<script>alert(1)</script>|['
    graph.set((root, RDFS.label, Literal(injected)))
    diagram = viewer.diagram(graph, kind="product")
    assert "\nunsafe --> injected" not in diagram["mermaid"] and "<script>" not in diagram["mermaid"]
    assert "&quot;" in diagram["mermaid"] and "&#124;" in diagram["mermaid"]
    assert any(node["label"] == injected for node in diagram["nodes"])


def test_ui_sample_graph_switching_evidence_validation_and_downloads_are_read_only(app):
    page, runtime, _ = app
    page.switch_page("src/ontoproduct/views/ontology_explorer.py").run()
    assert not page.exception
    assert page.download_button(key="ontology_graph_rdf")
    assert page.download_button(key="product_graph_json")
    assert page.selectbox(key="rdf_product_example").value == "motor"
    assert any("원문 값" in frame.value.columns and "600.0" in frame.value["정규화 값"].values for frame in page.dataframe)
    page.checkbox(key="rdf_show_evidence").check().run()
    page.button(key="rdf_validate_product").click().run()
    assert not page.exception and page.success
    page.selectbox(key="rdf_product_example").select("bearing").run()
    assert not page.exception
    assert any("원문 값" in frame.value.columns and len(frame.value) == 2 for frame in page.dataframe)
    page.radio(key="semantic_graph_scope").set_value("전체 구조").run()
    assert not page.exception and runtime.products.count() == 0
    page.selectbox(key="rdf_product_source").select("저장된 제품").run()
    assert any("저장된 제품이 없습니다" in info.value for info in page.info)


def test_ui_saved_product_graph_uses_actual_record_without_modifying_it(app):
    page, runtime, _ = app
    page.button(key="start_demo").click().run()
    fill_speed(page)
    page.button(key="approve_case").click().run()
    before = deepcopy(runtime.products.list())
    page.switch_page("src/ontoproduct/views/ontology_explorer.py").run()
    page.selectbox(key="rdf_product_source").select("저장된 제품").run()
    assert not page.exception and page.selectbox(key="rdf_stored_product")
    page.button(key="rdf_validate_product").click().run()
    assert not page.exception and page.success
    assert runtime.products.list() == before
