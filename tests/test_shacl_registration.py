import json
from copy import deepcopy
from pathlib import Path

import pytest

from ontoproduct.agents.validation_agent import ValidationAgent
from ontoproduct.repositories.database import Database
from ontoproduct.repositories.product_repository import ProductRepository
from ontoproduct.schemas.product import ProductAttribute
from ontoproduct.services.evidence_service import pack_evidence
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.services.registration_service import RegistrationService


class BearingLlm:
    def generate_structured(self, *, task, payload, response_schema):
        if task == "ontology":
            return response_schema.model_validate(
                {"product_class": "Bearing", "confidence": 0.9}
            )
        chunk = payload["documents"][0]
        lines = dict(
            line.split(": ", 1) for line in chunk["text"].splitlines() if ": " in line
        )
        attrs = {}
        for label, key in [
            ("Inner Diameter", "inner_diameter"),
            ("Outer Diameter", "outer_diameter"),
        ]:
            value, unit = lines[label].split()
            attrs[key] = {
                "value": float(value),
                "unit": unit,
                "confidence": 0.9,
                "evidence": f"{label}: {lines[label]}",
                "source_file": chunk["source_file"],
                "page": chunk["page"],
            }
        return response_schema.model_validate(
            {
                "product_name": lines["Product Name"],
                "candidate_class": "Bearing",
                "attributes": attrs,
            }
        )


@pytest.fixture
def product():
    path = Path(__file__).parent / "fixtures/extraction_ontology/semantic_products.json"
    return json.loads(path.read_text(encoding="utf-8"))["bearing"]


def mapping(ontology, cls):
    return {
        "product_class": cls,
        "confidence": 0.9,
        "required_properties": {
            k: p.model_dump()
            for k, p in ontology.resolve_required_properties(cls).items()
        },
        "optional_properties": {
            k: p.model_dump()
            for k, p in ontology.resolve_optional_properties(cls).items()
        },
    }


@pytest.mark.parametrize("inner,outer", [(32, 12), (12, 12)])
def test_direct_approval_cannot_bypass_shacl(tmp_path, product, inner, outer):
    ontology = OntologyService()
    repository = ProductRepository(Database(tmp_path / "products.db"))
    service = RegistrationService(repository, ontology, tmp_path / "exports")
    product["attributes"]["inner_diameter"]["value"] = inner
    product["attributes"]["outer_diameter"]["value"] = outer
    with pytest.raises(ValueError, match="validation"):
        service.register("case", product, {"action": "APPROVE"})
    assert repository.count() == 0
    assert not list((tmp_path / "exports").glob("*.json"))


def test_real_validation_preserves_input_and_maps_comparison(product):
    ontology = OntologyService()
    product["attributes"]["inner_diameter"]["value"] = 32
    state = {
        "normalized_product": product,
        "ontology_mapping": mapping(ontology, "Bearing"),
    }
    before = deepcopy(state)
    result = ValidationAgent(ontology).run(state)["validation_result"]
    assert state == before
    assert not result["valid"]
    assert [(i["field"], i["code"]) for i in result["issues"]] == [
        ("attributes.inner_diameter", "RANGE")
    ]


def test_conflict_dedup_keeps_candidates_and_other_violation(product):
    from ontoproduct.services.validation_service import validate_registration_product

    ontology = OntologyService()
    product["attributes"]["inner_diameter"] = pack_evidence(
        [
            ProductAttribute(value=12, unit="mm", source_file="a.txt"),
            ProductAttribute(value=20, unit="mm", source_file="b.txt"),
        ],
        conflict=True,
    ).model_dump(mode="json")
    product["attributes"]["outer_diameter"]["value"] = -1
    before = deepcopy(product)
    result = validate_registration_product(
        product, mapping(ontology, "Bearing"), ontology
    )
    assert product == before
    assert [(i["field"], i["code"]) for i in result["issues"]] == [
        ("attributes.inner_diameter", "MISSING_REQUIRED"),
        ("attributes.outer_diameter", "RANGE"),
    ]
    assert "conflicting document values" in result["issues"][0]["message"]


def test_shacl_exception_prevents_save(tmp_path, product, monkeypatch):
    ontology = OntologyService()

    def fail(*args, **kwargs):
        raise RuntimeError("SHACL unavailable")

    monkeypatch.setattr(ontology, "validate_semantics", fail)
    repository = ProductRepository(Database(tmp_path / "products.db"))
    with pytest.raises(RuntimeError, match="SHACL unavailable"):
        RegistrationService(repository, ontology, tmp_path / "exports").register(
            "case", product, {"action": "APPROVE"}
        )
    assert repository.count() == 0


def test_unmapped_shacl_violation_is_not_hidden(product, monkeypatch):
    from ontoproduct.services.validation_service import validate_registration_product

    ontology = OntologyService()
    monkeypatch.setattr(
        ontology,
        "validate_semantics",
        lambda p: {
            "valid": False,
            "issues": [{"path": "", "constraint": "unknown", "message": "unstable"}],
        },
    )
    result = validate_registration_product(
        product, mapping(ontology, "Bearing"), ontology
    )
    assert not result["valid"]
    assert result["issues"][0]["code"] == "CLASS"


def test_independent_same_field_shacl_violation_survives_range_error(
    product, monkeypatch
):
    from ontoproduct.services.validation_service import validate_registration_product

    ontology = OntologyService()
    product["attributes"]["inner_diameter"]["value"] = -1
    monkeypatch.setattr(
        ontology,
        "validate_semantics",
        lambda p: {
            "valid": False,
            "issues": [
                {
                    "focus_node": "urn:ontoproduct:record:validation",
                    "path": "urn:ontoproduct:ontology:innerDiameter",
                    "constraint": "http://www.w3.org/ns/shacl#NodeConstraintComponent",
                    "message": "Unexplained node violation",
                }
            ],
        },
    )
    result = validate_registration_product(
        product, mapping(ontology, "Bearing"), ontology
    )
    assert [i["code"] for i in result["issues"]] == ["RANGE", "CLASS"]


@pytest.mark.parametrize("case_id", ["E008", "E009"])
def test_inputdata_graph_blocks_then_human_repair_saves_once(tmp_path, case_id):
    from uuid import uuid4

    from ontoproduct.agents.real_registry import build_document_registry
    from ontoproduct.services.application_paths import ApplicationPaths
    from ontoproduct.services.parser_service import ParserService
    from ontoproduct.services.workflow_runtime import WorkflowRuntime

    paths = ApplicationPaths(tmp_path)
    llm = BearingLlm()

    def factory(ontology):
        return build_document_registry(
            ontology,
            parser_service=ParserService(paths.uploads),
            llm_services={"extraction": llm, "ontology": llm},
        )

    runtime = WorkflowRuntime(paths, registry_factory=factory)
    try:
        session = str(uuid4())
        thread = runtime.create_case(session)
        path = next(
            (Path(__file__).parents[1] / "inputdata/03_edge_cases").glob(
                f"{case_id}*.txt"
            )
        )
        refs = [runtime.documents.save(session, path.name, path.read_bytes())]
        list(runtime.start(thread, refs))
        state = runtime.snapshot(thread).values
        assert not state["validation_result"]["valid"]
        assert state["review_result"]["decision"] == "NEEDS_FIX"
        assert runtime.products.count() == 0
        assert not list(paths.exports.glob("*.json"))
        list(runtime.resume(thread, {"action": "APPROVE"}))
        assert runtime.products.count() == 0
        list(
            runtime.resume(
                thread,
                {
                    "action": "EDIT",
                    "edits": {
                        "attributes.inner_diameter": {"value": 12, "unit": "mm"},
                        "attributes.outer_diameter": {"value": 32, "unit": "mm"},
                    },
                },
            )
        )
        assert runtime.snapshot(thread).values["validation_result"]["valid"]
        list(runtime.resume(thread, {"action": "APPROVE"}))
        list(runtime.resume(thread, {"action": "APPROVE"}))
        [record] = runtime.products.list()
        [export] = list(paths.exports.glob("*.json"))
        assert json.loads(export.read_text(encoding="utf-8")) == record["product"]
    finally:
        runtime.close()
