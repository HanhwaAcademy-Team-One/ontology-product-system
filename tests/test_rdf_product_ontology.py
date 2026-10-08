import json
from copy import deepcopy
from pathlib import Path

import pytest
from rdflib import Graph, Literal
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS

from ontoproduct.schemas.product import NormalizedProduct, ProductAttribute
from ontoproduct.services.evidence_service import pack_evidence
from ontoproduct.services.rdf_ontology_service import RdfOntologyService

FIXTURES = Path(__file__).parent / "fixtures" / "extraction_ontology"


@pytest.fixture
def rdf_service():
    return RdfOntologyService()


@pytest.fixture
def semantic_products():
    return json.loads((FIXTURES / "semantic_products.json").read_text(encoding="utf-8"))


def test_actual_ontology_defines_distinct_model_item_manufacturer_and_quantities_locally(
    rdf_service,
):
    service, op = rdf_service, rdf_service.op
    graph = service.ontology_graph()
    assert (op.ManufacturedItem, RDFS.subClassOf, op.PhysicalArtifact) in graph
    assert (op.Manufacturer, RDFS.subClassOf, op.BusinessEntity) in graph
    assert (op.ManufacturerOrganization, RDFS.subClassOf, op.Manufacturer) in graph
    assert (op.ManufacturerOrganization, RDFS.subClassOf, op.Organization) in graph
    assert (op.ProductModel, OWL.disjointWith, op.ManufacturedItem) in graph
    assert (op.hasManufacturer, RDFS.domain, op.ProductModel) in graph
    assert (op.hasManufacturer, RDFS.range, op.Manufacturer) in graph
    assert not list(graph.triples((op.hasManufacturer, RDFS.subPropertyOf, None)))
    assert (op.ratedPower, RDFS.range, service.quantity_value) in graph
    assert (op.ratedPower, op.quantityKind, service.quantity_uri("power")) in graph
    assert (service.numeric_value, RDF.type, OWL.DatatypeProperty) in graph
    assert (service.has_unit, RDFS.range, service.unit_class) in graph
    assert (
        service.unit_uri("kW"),
        op.conversionTargetUnit,
        service.unit_uri("W"),
    ) in graph
    assert (
        graph.value(service.unit_uri("kW"), op.conversionMultiplier).toPython()
        == 1000.0
    )
    assert (
        service.unit_uri("rpm"),
        op.measuresQuantityKind,
        service.quantity_uri("rotational_frequency"),
    ) in graph
    assert str(graph.value(service.quantity_uri("mass"), RDFS.label)) == "Mass"
    for predicate in (
        OWL.equivalentClass,
        OWL.equivalentProperty,
        OWL.sameAs,
        OWL.imports,
        OWL.minCardinality,
    ):
        assert not list(graph.triples((None, predicate, None)))
    rows = list(
        graph.query(
            f"SELECT ?ancestor WHERE {{ <{op.BLDCMotorModel}> <{RDFS.subClassOf}>+ ?ancestor . FILTER(isIRI(?ancestor)) }}"
        )
    )
    ancestors = {row.ancestor for row in rows}
    assert {op.MotorModel, op.ProductModel} <= ancestors
    assert all(str(a).startswith(str(op)) for a in ancestors)


def test_product_export_uses_local_entity_and_quantity_relationships_with_source_preserved(
    rdf_service, semantic_products
):
    service, op = rdf_service, rdf_service.op
    product = semantic_products["motor"]
    before = deepcopy(product)
    graph = service.product_graph(product, record_id="DM-600")
    root = service.record_uri("DM-600")
    power = graph.value(root, op.ratedPower)
    manufacturer = graph.value(root, op.hasManufacturer)
    assert {
        (manufacturer, RDF.type, op.Manufacturer),
        (manufacturer, RDF.type, op.BusinessEntity),
    } <= set(graph)
    assert graph.value(manufacturer, RDFS.label) == Literal("XYZ Motors")
    assert graph.value(power, service.numeric_value).toPython() == 600
    assert graph.value(power, service.has_unit) == service.unit_uri("W")
    assert graph.value(power, service.has_quantity_kind) == service.quantity_uri(
        "power"
    )
    mass = graph.value(root, op.mass)
    assert graph.value(mass, service.numeric_value).toPython() == 0.75
    assert graph.value(mass, service.has_unit) == service.unit_uri("kg")
    assert not list(graph.subjects(RDF.type, op.ManufacturedItem))
    assert not list(graph.subjects(RDF.type, op.Organization))
    evidence = graph.value(power, op.attributeEvidence)
    recovered = json.loads(str(graph.value(evidence, op.recordJSON)))
    assert recovered == NormalizedProduct.model_validate(product).attributes[
        "rated_power"
    ].model_dump(mode="json")
    assert product == before and service.validate_graph(graph)["valid"]


def test_manufacturer_names_do_not_merge_global_identity(
    rdf_service, semantic_products
):
    service, op = rdf_service, rdf_service.op
    first = service.product_graph(semantic_products["motor"], record_id="first")
    second = service.product_graph(semantic_products["motor"], record_id="second")
    assert first.value(service.record_uri("first"), op.hasManufacturer) != second.value(
        service.record_uri("second"), op.hasManufacturer
    )
    assert not list((first + second).triples((None, OWL.sameAs, None)))


def test_explicit_item_and_organization_are_separate_and_valid(
    rdf_service, semantic_products
):
    service, op = rdf_service, rdf_service.op
    graph = service.product_graph(
        semantic_products["motor"],
        record_id="motor",
        item_id="serial-001",
        manufacturer_is_organization=True,
    )
    item = next(graph.subjects(RDF.type, op.ManufacturedItem))
    assert item != service.record_uri("motor")
    assert graph.value(item, op.hasMakeAndModel) == service.record_uri("motor")
    assert (item, RDF.type, op.PhysicalArtifact) in graph
    assert list(graph.subjects(RDF.type, op.Organization))
    assert service.validate_graph(graph)["valid"]
    assert service.record_uri("a:b") != service.record_uri("a%3Ab")


@pytest.mark.parametrize(
    "key,value,unit",
    [
        ("rated_power", -1, "W"),
        ("rated_power", "600", "W"),
        ("rated_power", True, "W"),
        ("rated_power", 600, "kg"),
        ("rated_power", 600, "hp"),
        ("rated_power", 600, None),
        ("manufacturer", True, None),
        ("manufacturer", "   ", None),
    ],
)
def test_invalid_types_units_dimensions_ranges_and_names_fail_shacl(
    rdf_service, semantic_products, key, value, unit
):
    product = semantic_products["motor"]
    product["attributes"][key].update(value=value, unit=unit)
    result = rdf_service.validate_product(product)
    assert not result["valid"] and result["issues"]


def test_missing_required_conflict_preserves_candidates_but_fails_shacl(
    rdf_service, semantic_products
):
    service, op = rdf_service, rdf_service.op
    product = semantic_products["motor"]
    candidates = [
        ProductAttribute(
            value=v,
            unit="rpm",
            evidence=f"Speed: {v} rpm",
            source_file=f"{v}.pdf",
            page=2,
        )
        for v in (3000, 3200)
    ]
    product["attributes"]["rated_speed"] = pack_evidence(
        candidates, conflict=True
    ).model_dump(mode="json")
    product["attributes"]["custom_field"] = {"value": "preserve me"}
    graph = service.product_graph(product, record_id="conflict")
    root = service.record_uri("conflict")
    assert graph.value(root, op.ratedSpeed) is None
    records = {
        str(graph.value(e, op.applicationField)): e
        for e in graph.objects(root, op.attributeEvidence)
    }
    assert "custom_field" in records
    evidence = records["rated_speed"]
    assert graph.value(evidence, op.hasConflict).toPython() is True
    sources = {
        str(graph.value(c, op.source_file))
        for c in graph.objects(evidence, op.candidateEvidence)
    }
    assert sources == {"3000.pdf", "3200.pdf"}
    assert not service.validate_graph(graph)["valid"]


@pytest.mark.parametrize(
    "inner,outer,valid", [(12, 32, True), (32, 12, False), (12, 12, False)]
)
def test_bearing_dimensions_have_actual_cross_property_constraint(
    rdf_service, semantic_products, inner, outer, valid
):
    product = semantic_products["bearing"]
    product["attributes"]["inner_diameter"]["value"] = inner
    product["attributes"]["outer_diameter"]["value"] = outer
    result = rdf_service.validate_product(product)
    assert result["valid"] is valid
    if not valid:
        assert any("less than" in i["message"] for i in result["issues"])


def test_tampered_quantity_kind_and_model_item_conflation_fail(
    rdf_service, semantic_products
):
    service, op = rdf_service, rdf_service.op
    graph = service.product_graph(semantic_products["motor"], record_id="motor")
    power = graph.value(service.record_uri("motor"), op.ratedPower)
    graph.set((power, service.has_quantity_kind, service.quantity_uri("mass")))
    assert not service.validate_graph(graph)["valid"]
    graph = service.product_graph(semantic_products["motor"], record_id="motor")
    graph.add((service.record_uri("motor"), RDF.type, op.ManufacturedItem))
    assert not service.validate_graph(graph)["valid"]


def test_stored_artifacts_match_executable_model_and_roundtrip(
    tmp_path, rdf_service, semantic_products
):
    directory = Path(__file__).parents[1] / "src" / "ontoproduct" / "ontology" / "rdf"
    assert isomorphic(
        Graph().parse(directory / "product_ontology.ttl", format="turtle"),
        rdf_service.ontology_graph(),
    )
    assert isomorphic(
        Graph().parse(directory / "product_shapes.ttl", format="turtle"),
        rdf_service.shapes_graph(),
    )
    rdf_service.write_artifacts(tmp_path)
    assert isomorphic(
        Graph().parse(tmp_path / "product_shapes.ttl", format="turtle"),
        rdf_service.shapes_graph(),
    )
    graph = rdf_service.product_graph(semantic_products["bearing"], record_id="bearing")
    assert isomorphic(
        graph, Graph().parse(data=graph.serialize(format="json-ld"), format="json-ld")
    )


def test_graph_validation_is_offline_and_does_not_mutate_input(
    monkeypatch, rdf_service, semantic_products
):
    import socket

    def disallow_network(*args, **kwargs):
        raise AssertionError("RDF/SHACL execution must not fetch external ontologies")

    monkeypatch.setattr(socket, "create_connection", disallow_network)
    monkeypatch.setattr(socket.socket, "connect", disallow_network)
    graph = rdf_service.product_graph(semantic_products["motor"], record_id="offline")
    before = set(graph)
    assert rdf_service.validate_graph(graph)["valid"]
    assert set(graph) == before
    with pytest.raises(TypeError):
        rdf_service.validate_graph("https://example.com/remote.ttl")


@pytest.mark.parametrize("value", [float("inf"), float("nan")])
def test_nonfinite_rdf_numeric_literals_fail_even_without_json_validation(
    rdf_service, semantic_products, value
):
    graph = rdf_service.product_graph(semantic_products["motor"], record_id="motor")
    power = graph.value(rdf_service.record_uri("motor"), rdf_service.op.ratedPower)
    graph.set((power, rdf_service.numeric_value, Literal(value)))
    assert not rdf_service.validate_graph(graph)["valid"]
