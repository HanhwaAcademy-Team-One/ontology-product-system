from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest

from ontoproduct.agents.duplicate_agent import DuplicateAgent
from ontoproduct.agents.registry import AgentRegistry, validate_contract
from ontoproduct.graph.execution import execute_agent
from ontoproduct.repositories.database import Database
from ontoproduct.repositories.product_repository import ProductRepository
from ontoproduct.schemas.duplicate import DuplicateCandidate
from ontoproduct.services.duplicate_service import DuplicateService, compare_names, normalize, structure, tokens
from ontoproduct.services.seed_service import seed_products


def motor(name, voltage=24, power=500, speed=3000, *, manufacturer="ABC Motors", power_unit="W", **extra):
    attributes = {"manufacturer": {"value": manufacturer}, "rated_voltage": {"value": voltage, "unit": "V"},
                  "rated_power": {"value": power, "unit": power_unit},
                  "rated_speed": {"value": speed, "unit": "rpm"}, **extra}
    return {"product_name": name, "product_class": "BLDCMotor",
            "attributes": {k: v for k, v in attributes.items() if v["value"] is not None}}


def mapping(ontology, cls="BLDCMotor"):
    dump = lambda props: {k: p.model_dump(mode="json") for k, p in props.items()}
    return {"product_class": cls, "confidence": 1,
            "required_properties": dump(ontology.resolve_required_properties(cls)),
            "optional_properties": dump(ontology.resolve_optional_properties(cls))}


@pytest.fixture
def repository(tmp_path):
    return ProductRepository(Database(tmp_path / "products.db"))


@pytest.fixture
def service(repository, ontology):
    return DuplicateService(repository, ontology)


@pytest.fixture
def find(service, ontology):
    return lambda product, **kwargs: service.find(product, mapping(ontology, product["product_class"]), **kwargs)


def save(repository, product):
    return repository.save(f"case:{product['product_name']}:{len(repository.list(limit=None))}", product)["record"]


def test_identical_product_returns_real_db_id_as_likely_duplicate(repository, find):
    record = save(repository, motor("DM-600", 24, 600, 3200))
    [candidate] = find(motor("DM-600", 24, 600, 3200))
    assert candidate["product_id"] == record["product_id"]
    assert candidate["score"] == 1 and candidate["verdict"] == "LIKELY_DUPLICATE"
    assert {e["field"]: e["status"] for e in candidate["evidence"]} == {
        "product_name": "MATCH", "manufacturer": "MATCH", "rated_voltage": "MATCH",
        "rated_power": "MATCH", "rated_speed": "MATCH"}
    assert "핵심 사양 4/4 일치" in candidate["reason"]


def test_seed_false_positives_are_removed(repository, find):
    seed_products(repository)
    assert [c["product_name"] for c in find(motor("DM-500", 24, 500, 3000))] == ["DM-500A"]
    assert [c["product_name"] for c in find(motor("DM-510", 24, 510, 3200))] == ["DM-510"]


def test_similar_name_with_different_model_number_and_specs_is_excluded(repository, find):
    save(repository, motor("DM-510", 24, 510, 3200))
    assert find(motor("DM-500", 24, 500, 3000)) == []


def test_same_series_variant_with_conflicting_key_spec_is_excluded(repository, find):
    save(repository, motor("DM-500B", 48, 500, 3000))
    assert find(motor("DM-500", 24, 500, 3000)) == []


def test_same_name_with_conflicting_specs_is_still_flagged_for_review(repository, find):
    save(repository, motor("DM-600", 48, 600, 3200))
    [candidate] = find(motor("DM-600", 24, 600, 3200))
    assert candidate["verdict"] == "POSSIBLE_DUPLICATE"
    assert "충돌: rated_voltage" in candidate["reason"]
    voltage = next(e for e in candidate["evidence"] if e["field"] == "rated_voltage")
    assert voltage == {"field": "rated_voltage", "status": "CONFLICT", "query_value": 24,
                       "candidate_value": 48, "unit": "V"}


def test_renamed_product_with_identical_specs_is_possible_duplicate(repository, find):
    save(repository, motor("ZX-9", 24, 600, 3200))
    [candidate] = find(motor("DM-600", 24, 600, 3200))
    assert candidate["verdict"] == "POSSIBLE_DUPLICATE"
    assert "제품명의 시리즈/모델번호 상이" in candidate["reason"]


def test_rounding_gap_is_near_not_conflict(repository, find):
    save(repository, motor("DM-600", 24, 605, 3200))
    [candidate] = find(motor("DM-600", 24, 600, 3200))
    assert candidate["verdict"] == "LIKELY_DUPLICATE" and candidate["score"] < 1
    assert "근사: rated_power" in candidate["reason"]


def test_different_class_is_excluded(repository, find):
    save(repository, {"product_name": "DM-600", "product_class": "Bearing",
                      "attributes": {"inner_diameter": {"value": 10, "unit": "mm"}}})
    assert find(motor("DM-600", 24, 600, 3200)) == []


def test_sparse_record_cannot_look_certain(repository, find):
    save(repository, motor("DM-700", None, None, None))
    sparse = find(motor("DM-701", 24, 700, 3000))
    assert sparse == []  # One shared attribute used to give a perfect attribute ratio.
    [named] = find(motor("DM-700", 24, 700, 3000))
    assert named["verdict"] == "POSSIBLE_DUPLICATE" and named["score"] < 0.6
    assert "비교 불가: rated_power, rated_speed, rated_voltage" in named["reason"]


def test_missing_attributes_and_names_do_not_raise(repository, find):
    save(repository, {"product_name": None, "product_class": "BLDCMotor", "attributes": {}})
    assert find({"product_name": None, "product_class": "BLDCMotor", "attributes": {}}) == []


def test_empty_database_returns_empty_list(find):
    assert find(motor("DM-600")) == []


def test_ties_are_ordered_by_product_id_and_top_k_keeps_best(repository, find):
    for _ in range(4):
        save(repository, motor("DM-600", 24, 600, 3200))
    save(repository, motor("DM-600", 24, 605, 3200))
    candidates = find(motor("DM-600", 24, 600, 3200))
    assert len(candidates) == 3 and all(c["score"] == 1 for c in candidates)
    assert [c["product_id"] for c in candidates] == sorted(c["product_id"] for c in candidates)
    assert len(find(motor("DM-600", 24, 600, 3200), top_k=5)) == 5


def test_kilowatt_input_is_compared_on_canonical_watts(repository, find):
    save(repository, motor("DM-600", 24, 600, 3200))
    [candidate] = find(motor("DM-600", 24, 0.6, 3200, power_unit="kW"))
    power = next(e for e in candidate["evidence"] if e["field"] == "rated_power")
    assert power["status"] == "MATCH" and power["query_value"] == 600 and power["unit"] == "W"


def test_name_and_text_normalization():
    assert tokens("ＤＭ－５００ａ") == tokens("dm 500 A") == ("dm", "500", "a")
    product = lambda name: normalize(structure({"product_name": name, "product_class": "BLDCMotor"}), {}, None)
    assert compare_names(product("DM-500"), product("dm500")).status == "MATCH"
    assert compare_names(product("DM-500"), product("DM-500A")).status == "NEAR"
    assert compare_names(product("DM-500"), product("DM-510")).status == "CONFLICT"
    assert compare_names(product("DM-500"), product("MX-500")).status == "CONFLICT"


def test_optional_conflict_lowers_score_but_does_not_block(repository, find):
    save(repository, motor("DM-600", 24, 600, 3200, weight={"value": 2.0, "unit": "kg"}))
    [candidate] = find(motor("DM-600", 24, 600, 3200, weight={"value": 3.0, "unit": "kg"}))
    assert candidate["verdict"] == "LIKELY_DUPLICATE" and candidate["score"] < 1


def test_works_without_mapping_using_query_attributes(repository, service):
    save(repository, motor("DM-600", 24, 600, 3200))
    assert [c["product_name"] for c in service.find(motor("DM-600", 24, 600, 3200))] == ["DM-600"]


def test_verification_rejects_fabricated_or_misordered_candidates(repository, service):
    record = save(repository, motor("DM-600"))
    real = DuplicateCandidate(product_id=record["product_id"], product_name="DM-600", score=0.9,
                              reason="x", verdict="LIKELY_DUPLICATE").model_dump(mode="json")
    fake = {**real, "product_id": "not-in-db"}
    with pytest.raises(ValueError, match="does not exist"):
        service.verify([fake], "BLDCMotor", top_k=3)
    with pytest.raises(ValueError, match="another product class"):
        service.verify([real], "Bearing", top_k=3)
    with pytest.raises(ValueError, match="not unique"):
        service.verify([real, real], "BLDCMotor", top_k=3)
    with pytest.raises(ValueError, match="exceed top_k"):
        service.verify([real, real], "BLDCMotor", top_k=1)
    with pytest.raises(ValueError, match="no verdict"):
        service.verify([{**real, "verdict": None}], "BLDCMotor", top_k=3)
    assert service.verify([real], "BLDCMotor", top_k=3) == [real]


def test_agent_contract_no_mutation_and_no_new_products(repository, service, ontology):
    seed_products(repository)
    agent = DuplicateAgent(service)
    validate_contract(agent)
    registry = AgentRegistry()
    registry.register(agent)
    state = {"normalized_product": motor("DM-500"), "ontology_mapping": mapping(ontology)}
    before, count = deepcopy(state), repository.count()
    output = execute_agent(registry, "duplicate", state, writer=lambda event: None)
    assert output["agent_logs"][-1]["status"] == "success"
    assert [c["product_name"] for c in output["duplicate_candidates"]] == ["DM-500A"]
    assert state == before and repository.count() == count


def test_verification_failure_follows_agent_error_path(repository, service, ontology):
    save(repository, motor("DM-600"))
    service.verify = lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("verification failed"))
    registry = AgentRegistry()
    registry.register(DuplicateAgent(service))
    output = execute_agent(registry, "duplicate",
                           {"normalized_product": motor("DM-600"), "ontology_mapping": mapping(ontology)},
                           writer=lambda event: None)
    assert output["agent_logs"][-1]["status"] == "error"
    assert "duplicate_candidates" not in output


def test_concurrent_queries_do_not_mix_candidates(repository, find):
    seed_products(repository)
    queries = [motor("DM-500", 24, 500, 3000), motor("DM-510", 24, 510, 3200)] * 10
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(find, queries))
    assert [[c["product_name"] for c in r] for r in results] == [["DM-500A"], ["DM-510"]] * 10
