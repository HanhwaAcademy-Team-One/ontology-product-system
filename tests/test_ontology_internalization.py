"""The operational ontology is self-contained: no IOF, GoodRelations or QUDT business URIs."""

import json
import re
import socket
from pathlib import Path

import pytest
from rdflib import URIRef
from rdflib.namespace import DCTERMS, RDF

from ontoproduct.agents.extraction_agent import ExtractionAgent
from ontoproduct.agents.ontology_agent import OntologyAgent
from ontoproduct.schemas.semantic_ontology import SOURCE_ID
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.services.product_ontology_service import ProductOntology
from ontoproduct.services.rdf_ontology_service import RdfOntologyService
from extraction_ontology_helpers import FIXTURES, constant_transport, document, motor_response

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "src" / "ontoproduct"
# URI forms only: attribution names such as "QUDT.org" must stay for license notices.
EXTERNAL_BUSINESS = re.compile(r"purl\.org/goodrelations|qudt\.org/|industrialontologies\.org|iofoundry", re.I)
# Standard vocabularies that remain in use. Everything else must be in the project namespace.
STANDARD_NAMESPACES = (
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "http://www.w3.org/2000/01/rdf-schema#",
    "http://www.w3.org/2002/07/owl#", "http://www.w3.org/2001/XMLSchema#", "http://www.w3.org/ns/shacl#",
    "http://purl.org/dc/terms/",
)


@pytest.fixture
def rdf_service():
    return RdfOntologyService()


@pytest.fixture
def products():
    return json.loads((FIXTURES / "semantic_products.json").read_text(encoding="utf-8"))


def iris(graph):
    for triple in graph:
        for term in triple:
            if isinstance(term, URIRef):
                yield str(term)


def test_operational_package_files_contain_no_external_business_uris():
    offenders = []
    for path in PACKAGE.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".yaml", ".yml", ".ttl", ".json", ".toml"} and "__pycache__" not in path.parts:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if EXTERNAL_BUSINESS.search(line):
                    offenders.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
    assert offenders == []
    assert not (PACKAGE / "ontology" / "external_mappings.yaml").exists()


def test_generated_graphs_use_only_local_or_standard_iris(rdf_service, products):
    graphs = [rdf_service.ontology_graph(), rdf_service.shapes_graph()]
    graphs += [rdf_service.product_graph(products[code], record_id=code) for code in products]
    graphs.append(rdf_service.product_graph(products["motor"], record_id="m", item_id="s-1", manufacturer_is_organization=True))
    for graph in graphs:
        for iri in iris(graph):
            assert iri.startswith("urn:ontoproduct:") or iri.startswith(STANDARD_NAMESPACES), iri
        for _, ns in graph.namespaces():
            assert not EXTERNAL_BUSINESS.search(str(ns))


def test_stored_ttl_artifacts_are_regenerated_without_external_business_uris():
    for path in (PACKAGE / "ontology" / "rdf").glob("*.ttl"):
        assert not EXTERNAL_BUSINESS.search(path.read_text(encoding="utf-8")), path.name


def test_sources_are_local_records_with_license_and_attribution(rdf_service):
    graph = rdf_service.ontology_graph()
    model = rdf_service.model.model
    for subject, obj in graph.subject_objects(DCTERMS.source):
        assert str(obj).startswith(str(rdf_service.src)), (subject, obj)
    for key, source in model.sources.items():
        assert re.fullmatch(SOURCE_ID, key)
        node = rdf_service.source_uri(key)
        assert graph.value(node, DCTERMS.license).toPython() == source.license
        assert graph.value(node, DCTERMS.creator).toPython() == source.attribution
    assert {str(rdf_service.source_uri(k)) for k in ("qudt-3.5.2", "goodrelations-1.0", "iof-202603")} <= {str(o) for o in graph.objects(None, DCTERMS.source)}


def test_rdf_unit_metadata_matches_shared_unit_service(rdf_service):
    graph, catalog = rdf_service.ontology_graph(), rdf_service.model.units.catalog
    for symbol in rdf_service.model.used_units():
        node = rdf_service.unit_uri(symbol)
        assert (node, RDF.type, rdf_service.unit_class) in graph
        assert graph.value(node, rdf_service.op.conversionMultiplier).toPython() == catalog.units[symbol].multiplier
        assert graph.value(node, rdf_service.op.conversionTargetUnit) == rdf_service.unit_uri(catalog.units[symbol].canonical)
    ontology = OntologyService()
    assert ontology.unit_service is ontology.semantic_model.units


def test_unknown_unit_is_kept_as_literal_and_fails_shacl(rdf_service, products):
    product = products["motor"]
    product["attributes"]["rated_power"].update(value=1, unit="hp")
    graph = rdf_service.product_graph(product, record_id="hp")
    power = graph.value(rdf_service.record_uri("hp"), rdf_service.op.ratedPower)
    assert str(graph.value(power, rdf_service.has_unit)) == "hp"
    assert not rdf_service.validate_graph(graph)["valid"]


def test_explicit_supertypes_are_stored_without_inference(rdf_service, products):
    op = rdf_service.op
    graph = rdf_service.product_graph(products["motor"], record_id="m", item_id="s-1", manufacturer_is_organization=True)
    manufacturer = graph.value(rdf_service.record_uri("m"), op.hasManufacturer)
    assert {op.Manufacturer, op.BusinessEntity, op.ManufacturerOrganization, op.Organization} == set(graph.objects(manufacturer, RDF.type))
    item = next(graph.subjects(op.hasMakeAndModel, rdf_service.record_uri("m")))
    assert {op.ManufacturedItem, op.PhysicalArtifact} <= set(graph.objects(item, RDF.type))
    assert (rdf_service.record_uri("m"), RDF.type, op.PhysicalArtifact) not in graph


def test_agent_payloads_carry_internal_definitions_only():
    ontology = OntologyService()
    extraction = constant_transport(motor_response())
    ExtractionAgent(extraction, ontology=ontology).run({"parsed_documents": [document()]})
    classification = constant_transport({"product_class": "BLDCMotor", "confidence": 0.9})
    OntologyAgent(ontology, classification).run({"extracted_product": motor_response()})
    for call in (*extraction.calls, *classification.calls):
        text = json.dumps(call["payload"])
        assert "://" not in text and not EXTERNAL_BUSINESS.search(text)
        assert call["payload"]["semantic_model"]["units"]["rpm"]["quantity"] == "rotational_frequency"


def test_definitions_load_rdf_and_shacl_run_with_network_blocked(monkeypatch, products):
    def disallow_network(*args, **kwargs):
        raise AssertionError("Ontology loading must not use the network")

    monkeypatch.setattr(socket, "create_connection", disallow_network)
    monkeypatch.setattr(socket.socket, "connect", disallow_network)
    service = RdfOntologyService(ProductOntology())
    assert service.validate_product(products["bearing"])["valid"]
    assert OntologyService().validate_semantics(products["motor"])["valid"]


def test_concordance_document_records_every_internal_unit_and_quantity_kind():
    text = (ROOT / "docs" / "team" / "03_EXTERNAL_CONCORDANCE.md").read_text(encoding="utf-8")
    model = ProductOntology()
    for symbol in model.used_units():
        assert f"`op:unit/{symbol}`" in text
    for key in model.used_quantities():
        assert f"`op:quantitykind/{key}`" in text
    for name in model.model.entity_classes:
        assert f"op:{name}" in text
