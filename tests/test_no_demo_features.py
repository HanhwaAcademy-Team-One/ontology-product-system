import json
from pathlib import Path

import pytest
from test_streamlit_app import app as app  # noqa: PLC0414

from ontoproduct.services.duplicate_service import DuplicateService


def product():
    path = Path(__file__).parent / "fixtures/extraction_ontology/semantic_products.json"
    return json.loads(path.read_text(encoding="utf-8"))["motor"]


@pytest.mark.parametrize("view", ["product_database", "dashboard", "ontology_explorer"])
def test_empty_views_do_not_offer_or_create_demo_products(app, view):
    page, runtime, _ = app
    page.switch_page(f"src/ontoproduct/views/{view}.py").run()
    assert not page.exception
    assert not any(button.key == "seed_database" for button in page.button)
    assert not any(
        box.key
        in {"rdf_product_source", "rdf_product_example", "product_origin_filter"}
        for box in page.selectbox
    )
    assert not any(metric.label == "예제 제품" for metric in page.metric)
    assert not any("예제" in text.value or "샘플" in text.value for text in page.info)
    assert runtime.products.list(origin=None) == []
    if view == "ontology_explorer":
        assert any("저장된 제품이 없습니다" in text.value for text in page.info)
        assert not any(
            button.key == "product_graph_rdf" for button in page.download_button
        )


def test_legacy_seed_is_preserved_but_excluded_from_product_flows(app):
    page, runtime, _ = app
    legacy = runtime.products.save("seed:old", product(), origin="SEED")["record"]
    assert runtime.products.list() == []
    assert runtime.products.count() == 0
    assert runtime.products.summary()["total"] == 0
    assert DuplicateService(runtime.products, runtime.ontology).find(product()) == []

    registered = runtime.products.save("registered", product())["record"]
    assert runtime.products.count() == 1
    assert runtime.products.summary()["total"] == 1
    assert [row["product_id"] for row in runtime.products.list()] == [
        registered["product_id"]
    ]
    assert [
        row["product_id"]
        for row in DuplicateService(runtime.products, runtime.ontology).find(product())
    ] == [registered["product_id"]]

    page.switch_page("src/ontoproduct/views/product_database.py").run()
    assert not page.exception
    assert len(page.selectbox(key="selected_product").options) == 1
    assert page.download_button(key="download_product")
    page.switch_page("src/ontoproduct/views/ontology_explorer.py").run()
    assert not page.exception
    assert len(page.selectbox(key="rdf_stored_product").options) == 1
    assert page.download_button(key="product_graph_rdf")
    page.switch_page("src/ontoproduct/views/dashboard.py").run()
    assert not page.exception
    assert page.metric[0].value == "1"
    assert runtime.products.get(legacy["product_id"]) == legacy
    assert len(runtime.products.list(origin=None)) == 2
