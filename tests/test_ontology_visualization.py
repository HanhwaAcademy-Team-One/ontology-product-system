import json
import re
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest
import streamlit as st
from rdflib import Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SH, XSD
from streamlit.delta_generator import DeltaGenerator

from ontoproduct.services.ontology_visualization import OntologyVisualization
from ontoproduct.services.product_ontology_service import ProductOntology
from ontoproduct.services.rdf_ontology_service import RdfOntologyService
from test_streamlit_app import app, fill_speed


COLORS = {
    "local": ("#ede9fe", "#7c3aed"),
    "quantity_kind": ("#fce7f3", "#db2777"),
    "datatype": ("#f3f4f6", "#64748b"),
    "product": ("#dbeafe", "#2563eb"),
    "entity": ("#fef3c7", "#d97706"),
    "quantity": ("#cffafe", "#0891b2"),
    "unit": ("#dcfce7", "#16a34a"),
    "value": ("#fff7ed", "#ea580c"),
}
ONTOLOGY_LEGEND = "보라색: 자체 개념·내부 출처 · 분홍색: 물리량 종류 · 초록색: 단위 · 회색: XSD 데이터 타입"
PRODUCT_LEGEND = "파란색: 제품 모델 · 노란색: 제조사 · 청록색: 물리량 값 · 주황색: 값 · 초록색: 단위 · 분홍색: 물리량 종류 · 보라색: 자체 개념·내부 출처"


def assert_classes(diagram):
    for group in {node["group"] for node in diagram["nodes"]}:
        fill, stroke = COLORS[group]
        assert f"classDef {group} fill:{fill},stroke:{stroke},color:#111827" in diagram["mermaid"]
        identifiers = [node["id"] for node in diagram["nodes"] if node["group"] == group]
        assert f"class {','.join(identifiers)} {group}" in diagram["mermaid"]
    assert len({COLORS[node["group"]][0] for node in diagram["nodes"]}) == len({node["group"] for node in diagram["nodes"]})


def db_rows(root):
    snapshot = {}
    for path in sorted((root / "data").glob("*.db")):
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
            tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            snapshot[path.name] = {
                name: sorted(connection.execute('SELECT * FROM "' + name.replace('"', '""') + '"').fetchall(), key=repr)
                for (name,) in tables
            }
    return snapshot


@pytest.fixture
def graph_calls(monkeypatch):
    calls = {"diagram": [], "attribute_rows": [], "downloads": [], "validate_graph": [], "mermaid": [], "serialize": []}
    methods = [
        (OntologyVisualization, "diagram"),
        (OntologyVisualization, "attribute_rows"),
        (RdfOntologyService, "validate_graph"),
    ]
    for owner, method in methods:
        original = getattr(owner, method)

        def checked(self, graph, *args, _method=method, _original=original, **kwargs):
            before = set(graph)
            result = _original(self, graph, *args, **kwargs)
            assert set(graph) == before
            calls[_method].append(result)
            return result

        monkeypatch.setattr(owner, method, checked)
    original_serialize = Graph.serialize

    def serialize(self, *args, **kwargs):
        before = set(self)
        result = original_serialize(self, *args, **kwargs)
        assert set(self) == before
        calls["serialize"].append(result)
        return result

    monkeypatch.setattr(Graph, "serialize", serialize)
    original_download = DeltaGenerator.download_button

    def download(self, label, data, *args, **kwargs):
        calls["downloads"].append((kwargs.get("key"), data))
        return original_download(self, label, data, *args, **kwargs)

    monkeypatch.setattr(DeltaGenerator, "download_button", download)
    original_mermaid = st.mermaid_chart

    def mermaid(code, *args, **kwargs):
        calls["mermaid"].append(code)
        return original_mermaid(code, *args, **kwargs)

    monkeypatch.setattr(st, "mermaid_chart", mermaid)
    return calls


@pytest.mark.parametrize("suffix,expected", [
    ("unit/W", "opunit:W"),
    ("quantitykind/power", "opqk:power"),
    ("source/qudt-3.5.2", "opsrc:qudt-3.5.2"),
    ("source/iof-202603", "opsrc:iof-202603"),
    ("source/goodrelations-1.0", "opsrc:goodrelations-1.0"),
    ("ProductModel", "op:ProductModel"),
])
def test_term_label_internal_prefixes(suffix, expected):
    viewer = OntologyVisualization(ProductOntology())
    assert viewer.term_label(URIRef(str(viewer.op) + suffix)) == expected


@pytest.mark.parametrize("term,expected", [
    (XSD.double, "xsd:double"), (XSD.string, "xsd:string"),
    (RDF.type, "rdf:type"), (RDFS.range, "rdfs:range"),
    (OWL.Class, "owl:Class"), (SH.NodeShape, "sh:NodeShape"),
    (DCTERMS.source, "dcterms:source"),
])
def test_term_label_standard_prefixes(term, expected):
    assert OntologyVisualization(ProductOntology()).term_label(term) == expected


@pytest.mark.parametrize("kind", ["ontology", "product"])
def test_diagram_groups_use_iri_and_type_with_label_priority(kind):
    viewer = OntologyVisualization(ProductOntology())
    graph = viewer.rdf.ontology_graph() if kind == "ontology" else viewer.example_graphs()["motor"]
    terms = {
        viewer.rdf.unit_uri("W"): ("watt", "unit"),
        viewer.rdf.quantity_uri("power"): ("Power", "quantity_kind"),
        XSD.double: ("double datatype", "datatype"),
        XSD.string: ("string datatype", "datatype"),
        **{viewer.rdf.source_uri(key): ("Internal source", "local") for key in viewer.model.model.sources},
    }
    # Sources are absent from the usual projection; exercise existing visible relations,
    # without adding dcterms:source to the production projection.
    original = viewer.diagram(graph, kind=kind)
    sources = {viewer.rdf.source_uri(key).n3() for key in viewer.model.model.sources}
    assert not any(node["term"] in sources for node in original["nodes"])
    for term, (label, _) in terms.items():
        graph.set((term, RDFS.label, Literal(label)))
        graph.add((viewer.op.groupProbe, RDFS.range if kind == "ontology" else viewer.op.attributeEvidence, term))
    quantity = URIRef("urn:ontoproduct:record:labelled-quantity")
    graph.add((quantity, RDF.type, viewer.rdf.quantity_value))
    graph.add((quantity, RDFS.label, Literal("Explicit quantity label")))
    graph.add((viewer.op.groupProbe, RDFS.range if kind == "ontology" else viewer.op.ratedPower, quantity))
    terms[quantity] = ("Explicit quantity label", "quantity")
    before = set(graph)
    diagram = viewer.diagram(graph, kind=kind, include_evidence=True)
    nodes = {node["term"]: node for node in diagram["nodes"]}
    for term, (label, group) in terms.items():
        assert (nodes[term.n3()]["label"], nodes[term.n3()]["group"]) == (label, group)
    assert_classes(diagram)
    assert set(graph) == before


def test_diagram_uses_actual_rdf_and_preserves_graph_with_distinct_literal_nodes():
    viewer = OntologyVisualization(ProductOntology())
    graph = viewer.example_graphs()["motor"]
    before = set(graph)
    diagram = viewer.diagram(graph, kind="product")
    labels = {node["label"] for node in diagram["nodes"]}
    assert {"DM-600", "XYZ Motors", "600.0", "opunit:W", "opqk:power"} <= labels
    nodes = {node["id"]: node["term"] for node in diagram["nodes"]}
    actual_edges = {(nodes[edge["source"]], edge["relation"], nodes[edge["target"]]) for edge in diagram["edges"]}
    root = next(graph.subjects(RDF.type, viewer.op.ProductModel))
    manufacturer = graph.value(root, viewer.op.hasManufacturer)
    power = graph.value(root, viewer.op.ratedPower)
    assert (root.n3(), "op:hasManufacturer", manufacturer.n3()) in actual_edges
    assert (manufacturer, RDF.type, viewer.op.Manufacturer) in graph
    assert (root.n3(), "op:ratedPower", power.n3()) in actual_edges
    for predicate in (viewer.rdf.numeric_value, viewer.rdf.has_unit, viewer.rdf.has_quantity_kind):
        assert (power.n3(), viewer.term_label(predicate), graph.value(power, predicate).n3()) in actual_edges
    assert not any(edge["relation"] == "op:candidateEvidence" for edge in diagram["edges"])
    assert not re.search(r"(?:gr|qudt|iof):|purl\.org/goodrelations|qudt\.org/|industrialontologies\.org", diagram["mermaid"])
    detailed = viewer.diagram(graph, kind="product", include_evidence=True)
    assert len(detailed["nodes"]) > len(diagram["nodes"])
    assert any(edge["relation"] == "op:source_file" for edge in detailed["edges"])
    assert_classes(diagram)
    assert_classes(detailed)
    assert set(graph) == before
    assert viewer._node(graph, Literal(24))["id"] != viewer._node(graph, Literal("24"))["id"]


def test_ontology_diagram_focus_shows_inheritance_internal_concepts_and_properties():
    viewer = OntologyVisualization(ProductOntology())
    graph = viewer.rdf.ontology_graph()
    before = set(graph)
    full = viewer.diagram(graph, kind="ontology")
    focus = viewer.diagram(graph, kind="ontology", product_class="Bearing")
    motor = viewer.diagram(graph, kind="ontology", product_class="BLDCMotor")
    assert len(focus["nodes"]) < len(full["nodes"])
    assert any(node["label"] == "Bearing model" for node in focus["nodes"])
    assert not any(node["label"] == "Brushless DC motor model" for node in focus["nodes"])
    assert any(node["label"] == "Brushless DC motor model" for node in motor["nodes"])
    assert not any(node["label"] == "Bearing model" for node in motor["nodes"])
    ids = {node["term"]: node["id"] for node in focus["nodes"]}
    assert {
        "source": ids[viewer.op.BearingModel.n3()],
        "relation": "rdfs:subClassOf",
        "target": ids[viewer.op.MechanicalPartModel.n3()],
    } in focus["edges"]
    assert {
        "source": ids[viewer.op.ManufacturedItem.n3()],
        "relation": "rdfs:subClassOf",
        "target": ids[viewer.op.PhysicalArtifact.n3()],
    } in focus["edges"]
    assert any(node["label"] == "Physical artifact" for node in focus["nodes"])
    assert any(node["term"] == viewer.op.innerDiameter.n3() for node in focus["nodes"])
    assert not any(node["term"] == viewer.op.ratedPower.n3() for node in focus["nodes"])
    assert any(node["term"] == viewer.op.ratedPower.n3() for node in motor["nodes"])
    assert_classes(full)
    assert_classes(focus)
    assert set(graph) == before
    with pytest.raises(ValueError):
        viewer.diagram(graph, kind="other")


def test_attributes_show_raw_and_normalized_values_with_original_evidence():
    viewer = OntologyVisualization(ProductOntology())
    graphs = viewer.example_graphs()
    rows = {row["키"]: row for row in viewer.attribute_rows(graphs["motor"])}
    assert (rows["rated_power"]["원문 값"], rows["rated_power"]["원문 단위"]) == ("0.6", "kW")
    assert (rows["rated_power"]["정규화 값"], rows["rated_power"]["표준 단위"]) == ("600.0", "W")
    assert (rows["rated_power"]["파일"], rows["rated_power"]["페이지"]) == ("motor_spec.pdf (22222222)", "2")
    assert rows["rated_power"]["근거"] == "Rated Power: 0.6 kW"
    assert (
        rows["weight"]["원문 값"], rows["weight"]["원문 단위"],
        rows["weight"]["정규화 값"], rows["weight"]["표준 단위"],
    ) == ("750", "g", "0.75", "kg")
    assert (
        rows["weight"]["파일"], rows["weight"]["페이지"], rows["weight"]["근거"],
    ) == ("motor_spec.pdf (22222222)", "2", "Weight: 750 g")
    bearing_rows = viewer.attribute_rows(graphs["bearing"])
    assert "[Sheet: Spec, Row:" in bearing_rows[0]["근거"]
    assert len(viewer.triple_rows(graphs["motor"])) == len(graphs["motor"])


@pytest.mark.parametrize("sample", ["motor", "bearing"])
def test_projection_attributes_download_payloads_and_validation_preserve_rdf(sample):
    viewer = OntologyVisualization(ProductOntology())
    graph = viewer.example_graphs()[sample]
    before = set(graph)
    diagram = viewer.diagram(graph, kind="product", include_evidence=True)
    assert set(graph) == before
    assert viewer.attribute_rows(graph)
    assert set(graph) == before
    rdf_data = graph.serialize(format="turtle")
    assert set(graph) == before
    assert isomorphic(graph, Graph().parse(data=rdf_data, format="turtle"))
    json_data = json.dumps({"nodes": diagram["nodes"], "edges": diagram["edges"]}, ensure_ascii=False, indent=2)
    assert json.loads(json_data) == {"nodes": diagram["nodes"], "edges": diagram["edges"]}
    assert set(graph) == before
    assert viewer.rdf.validate_graph(graph)["valid"]
    assert set(graph) == before


def test_product_diagram_includes_actual_item_model_relation():
    viewer = OntologyVisualization(ProductOntology())
    fixture = Path(__file__).parent / "fixtures" / "extraction_ontology" / "semantic_products.json"
    product = json.loads(fixture.read_text(encoding="utf-8"))["motor"]
    graph = viewer.rdf.product_graph(product, record_id="model", item_id="item")
    diagram = viewer.diagram(graph, kind="product")
    nodes = {node["id"]: node["term"] for node in diagram["nodes"]}
    for subject, target in graph.subject_objects(viewer.op.hasMakeAndModel):
        assert any(
            nodes[edge["source"]] == subject.n3()
            and nodes[edge["target"]] == target.n3()
            and edge["relation"] == "op:hasMakeAndModel"
            for edge in diagram["edges"]
        )



def test_mermaid_label_entities_preserve_text_without_reinterpreting_source():
    viewer = OntologyVisualization(ProductOntology())
    label = 'a|[b] "c" <d> & #quot;'
    assert viewer._safe_label(label) == (
        'a|[b] #quot;c#quot; #lt;d#gt; #amp; #35;quot;'
    )
    assert viewer._safe_label("it's") == "it#39;s"

def test_untrusted_labels_cannot_break_mermaid_diagram():
    viewer = OntologyVisualization(ProductOntology())
    graph = viewer.example_graphs()["motor"]
    root = next(graph.subjects(RDF.type, viewer.op.ProductModel))
    injected = '"]\nunsafe --> injected\n<script>alert(1)</script>|['
    graph.set((root, RDFS.label, Literal(injected)))
    diagram = viewer.diagram(graph, kind="product")
    assert "\nunsafe --> injected" not in diagram["mermaid"] and "<script>" not in diagram["mermaid"]
    assert "#quot;" in diagram["mermaid"] and "|[" in diagram["mermaid"]
    assert any(node["label"] == injected for node in diagram["nodes"])


def test_ui_sample_graph_switching_evidence_validation_and_downloads_are_read_only(app, graph_calls):
    page, runtime, root = app
    before = db_rows(root)
    page.switch_page("src/ontoproduct/views/ontology_explorer.py").run()
    assert not page.exception
    assert db_rows(root) == before
    assert page.download_button(key="ontology_graph_rdf")
    assert page.download_button(key="product_graph_json")
    assert page.selectbox(key="rdf_product_example").value == "motor"
    captions = "\n".join(caption.value for caption in page.caption)
    assert ONTOLOGY_LEGEND in captions and PRODUCT_LEGEND in captions
    assert "외부 온톨로지" not in captions
    assert any("원문 값" in frame.value.columns and "600.0" in frame.value["정규화 값"].values for frame in page.dataframe)
    assert any("원문 값" in frame.value.columns and "0.75" in frame.value["정규화 값"].values for frame in page.dataframe)
    assert all(diagram["mermaid"] in graph_calls["mermaid"] for diagram in graph_calls["diagram"])
    for diagram in graph_calls["diagram"]:
        assert_classes(diagram)
    downloads = dict(graph_calls["downloads"])
    assert downloads["ontology_graph_rdf"] in graph_calls["serialize"]
    assert downloads["product_graph_rdf"] in graph_calls["serialize"]
    assert len(Graph().parse(data=downloads["ontology_graph_rdf"], format="turtle")) > 0
    assert json.loads(downloads["product_graph_json"]) == {key: graph_calls["diagram"][-1][key] for key in ("nodes", "edges")}
    page.checkbox(key="rdf_show_evidence").check().run()
    page.button(key="rdf_validate_product").click().run()
    assert not page.exception and page.success
    assert graph_calls["validate_graph"][-1]["valid"]
    assert db_rows(root) == before
    page.selectbox(key="rdf_product_example").select("bearing").run()
    assert not page.exception
    assert any("원문 값" in frame.value.columns and len(frame.value) == 2 for frame in page.dataframe)
    assert any(node["label"] == "op:BearingModel" for node in graph_calls["diagram"][-1]["nodes"])
    page.button(key="rdf_validate_product").click().run()
    assert not page.exception and page.success
    assert graph_calls["validate_graph"][-1]["valid"]
    page.radio(key="semantic_graph_scope").set_value("전체 구조").run()
    assert not page.exception and runtime.products.count() == 0
    assert any(node["label"] == "Bearing model" for node in graph_calls["diagram"][-2]["nodes"])
    page.selectbox(key="rdf_product_example").select("motor").run()
    assert not page.exception
    assert any(node["label"] == "DM-600" for node in graph_calls["diagram"][-1]["nodes"])
    assert db_rows(root) == before
    page.selectbox(key="rdf_product_source").select("저장된 제품").run()
    assert not page.exception
    assert any("저장된 제품이 없습니다" in info.value for info in page.info)
    assert db_rows(root) == before


def test_ui_saved_product_graph_uses_actual_record_without_modifying_it(app, graph_calls):
    page, runtime, root = app
    page.button(key="start_demo").click().run()
    fill_speed(page)
    page.button(key="approve_case").click().run()
    before = deepcopy(runtime.products.list())
    rows_before = db_rows(root)
    page.switch_page("src/ontoproduct/views/ontology_explorer.py").run()
    assert not page.exception
    page.selectbox(key="rdf_product_source").select("저장된 제품").run()
    assert not page.exception and page.selectbox(key="rdf_stored_product")
    assert db_rows(root) == rows_before
    stored = before[0]["product"]["attributes"]["rated_power"]
    displayed = next(frame.value for frame in page.dataframe if "원문 값" in frame.value.columns)
    power = displayed.loc[displayed["키"] == "rated_power"].iloc[0]
    assert power["원문 값"] == str(stored["value"])
    assert power["원문 단위"] == stored["unit"]
    assert power["정규화 값"] == str(stored["value"])
    assert power["표준 단위"] == stored["unit"]
    assert dict(graph_calls["downloads"])["product_graph_rdf"]
    assert json.loads(dict(graph_calls["downloads"])["product_graph_json"])["nodes"] == graph_calls["diagram"][-1]["nodes"]
    page.button(key="rdf_validate_product").click().run()
    assert not page.exception and page.success
    assert graph_calls["validate_graph"][-1]["valid"]
    assert runtime.products.list() == before
    assert db_rows(root) == rows_before
    page.selectbox(key="rdf_product_source").select("샘플 사양").run()
    assert not page.exception
    assert db_rows(root) == rows_before
