import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from ontoproduct.repositories.database import Database
from ontoproduct.repositories.product_repository import ProductRepository
from ontoproduct.services.registration_service import RegistrationService
from ontoproduct.services.seed_service import seed_products


@pytest.fixture
def registration(tmp_path, ontology):
    repository = ProductRepository(Database(tmp_path / "products.db"))
    return RegistrationService(repository, ontology, tmp_path / "exports")


def test_same_case_registers_once_and_returns_original(registration, paused_state):
    product = paused_state["normalized_product"]
    first = registration.register("case-one", product, {"action": "APPROVE"})
    second = registration.register("case-one", product, {"action": "APPROVE"})
    assert first["status"] == "REGISTERED" and second["status"] == "ALREADY_REGISTERED"
    assert first["record"] == second["record"]
    assert registration.repository.count() == 1
    assert json.loads(open(first["export_path"], encoding="utf-8").read()) == product


def test_concurrent_same_case_unique_constraint(registration, paused_state):
    barrier = Barrier(2, timeout=5)

    def register():
        barrier.wait()
        return registration.register("same-case", paused_state["normalized_product"], {"action": "APPROVE"})
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: register(), range(2)))
    assert sorted(r["status"] for r in results) == ["ALREADY_REGISTERED", "REGISTERED"]
    assert registration.repository.count() == 1
    assert len({r["record"]["product_id"] for r in results}) == 1


@pytest.mark.parametrize("command", [{"action": "REJECT"}, {"action": "EDIT"}, {}])
def test_registration_requires_approval(registration, paused_state, command):
    with pytest.raises(ValueError):
        registration.register("case-one", paused_state["normalized_product"], command)
    assert registration.repository.count() == 0


def test_invalid_product_cannot_be_registered(registration, paused_state):
    product = paused_state["normalized_product"]
    del product["attributes"]["rated_speed"]
    with pytest.raises(ValueError):
        registration.register("case-one", product, {"action": "APPROVE"})
    assert registration.repository.count() == 0


def test_seed_is_idempotent_and_search_reads_database(registration):
    first = seed_products(registration.repository)
    second = seed_products(registration.repository)
    assert all(r["status"] == "REGISTERED" for r in first)
    assert all(r["status"] == "ALREADY_REGISTERED" for r in second)
    assert registration.repository.count() == 3
    assert {r["product"]["product_name"] for r in registration.repository.list()} == {"DM-500A", "DM-510", "MX-500"}
    assert len(registration.repository.list(search="DM-")) == 2


def test_search_treats_like_wildcards_literally(registration):
    seed_products(registration.repository)
    product = {"product_name": "DM_100%", "product_class": "BLDCMotor", "attributes": {}}
    registration.repository.save("case-wildcard", product)
    assert [r["product"]["product_name"] for r in registration.repository.list(search="_")] == ["DM_100%"]
    assert [r["product"]["product_name"] for r in registration.repository.list(search="%")] == ["DM_100%"]


def test_duplicate_search_covers_products_beyond_listing_limit(registration):
    from ontoproduct.services.duplicate_service import DuplicateService
    seed_products(registration.repository)
    for index in range(600):
        registration.repository.save(f"filler-{index}", {"product_name": f"Bearing-{index}",
                                                         "product_class": "Bearing", "attributes": {}})
    target = registration.repository.list(search="DM-500A")[0]["product"]
    candidates = DuplicateService(registration.repository).find(target)
    assert "DM-500A" in {c["product_name"] for c in candidates}
