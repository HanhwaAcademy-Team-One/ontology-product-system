import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ontoproduct.views.resources import get_runtime


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("ONTOPRODUCT_DATA_DIR", str(tmp_path))
    value = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "app.py", default_timeout=20
    ).run()
    assert not value.exception
    yield value, get_runtime(str(tmp_path)), tmp_path
    get_runtime.clear()


def fill_speed(app, value="3000"):
    next(field for field in app.text_input if field.label == "정격 속도 *").set_value(
        value
    )
    app.button(key="submit_edit").click().run()


def test_ui_demo_edit_approve_rerun_and_download(app):
    page, runtime, root = app
    page.button(key="start_demo").click().run()
    thread = page.session_state["thread_id"]
    assert not page.exception
    assert page.button(key="approve_case").disabled
    assert runtime.products.count() == 0
    fill_speed(page)
    assert not page.exception
    assert not page.button(key="approve_case").disabled
    assert runtime.products.count() == 0
    page.run()
    assert page.session_state["thread_id"] == thread
    page.button(key="approve_case").click().run()
    assert not page.exception
    assert runtime.products.count() == 1
    assert page.download_button(key="download_registered")
    record = runtime.products.get_by_case(thread)
    assert (
        json.loads((root / "exports" / f"{record['product_id']}.json").read_text())
        == record["product"]
    )
    page.run()
    assert runtime.products.count() == 1


def test_ui_file_uploads_store_references_without_uploadedfile_in_state(app):
    page, runtime, root = app
    page.file_uploader[0].set_value(
        [
            ("motor_spec.pdf", b"%PDF mock", "application/pdf"),
            (
                "bom.xlsx",
                b"mock workbook",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        ]
    ).run()
    assert not page.button(key="start_upload").disabled
    page.button(key="start_upload").click().run()
    assert not page.exception
    state = runtime.snapshot(page.session_state["thread_id"]).values
    assert [ref["name"] for ref in state["source_documents"]] == [
        "motor_spec.pdf",
        "bom.xlsx",
    ]
    assert all(
        Path(ref["path"]).is_relative_to(root / "uploads")
        for ref in state["source_documents"]
    )
    json.dumps(state)
    assert runtime.products.count() == 0


def test_ui_invalid_numeric_edit_keeps_checkpoint(app):
    page, runtime, _ = app
    page.button(key="start_demo").click().run()
    thread = page.session_state["thread_id"]
    before = runtime.snapshot(thread).values["agent_logs"]
    fill_speed(page, "fast")
    assert not page.exception
    assert page.error
    assert runtime.snapshot(thread).values["agent_logs"] == before
    assert page.button(key="approve_case").disabled


def test_ui_registration_error_retry_reuses_saved_product(app):
    page, runtime, _ = app
    page.button(key="start_demo").click().run()
    fill_speed(page)
    original = runtime.registration.export
    calls = []

    def export(record):
        calls.append(1)
        if len(calls) == 1:
            raise OSError("Export unavailable")
        return original(record)

    runtime.registration.export = export
    page.button(key="approve_case").click().run()
    assert not page.exception
    assert runtime.products.count() == 1
    assert page.button(key="retry_error")
    page.button(key="retry_error").click().run()
    assert not page.exception
    assert page.download_button(key="download_registered")
    assert runtime.products.count() == 1


def test_ui_reject_new_case_and_restore_saved_review(app):
    page, runtime, _ = app
    page.button(key="start_demo").click().run()
    first = page.session_state["thread_id"]
    page.button(key="new_case").click().run()
    assert page.button(key="start_demo")
    page.selectbox(key="resume_case_selection").select(first).run()
    page.button(key="load_case").click().run()
    assert page.session_state["thread_id"] == first
    assert page.button(key="approve_case").disabled
    page.button(key="reject_case").click().run()
    assert not page.exception
    assert runtime.snapshot(first).values["case_status"] == "REJECTED"
    assert runtime.products.count() == 0


def test_ui_product_page_seed_search_and_json_download(app):
    page, runtime, _ = app
    page.switch_page("src/ontoproduct/views/product_database.py").run()
    assert not page.exception
    page.button(key="seed_database").click().run()
    page.button(key="seed_database").click().run()
    assert runtime.products.count() == 3
    page.text_input(key="product_search").set_value("DM-").run()
    assert not page.exception
    assert len(page.selectbox(key="selected_product").options) == 2
    assert page.download_button(key="download_product")
    page.button(key="new_case").click().run()
    assert not page.exception
    assert page.button(key="start_demo")


def test_ui_class_change_preserves_orphaned_overrides(app):
    page, runtime, _ = app
    page.button(key="start_demo").click().run()
    fill_speed(page)
    next(box for box in page.selectbox if box.label == "제품 분류").select(
        "Bearing"
    ).run()
    next(field for field in page.text_input if field.label == "내경 *").set_value("10")
    next(field for field in page.text_input if field.label == "외경 *").set_value("20")
    page.button(key="submit_edit").click().run()
    assert not page.exception
    state = runtime.snapshot(page.session_state["thread_id"]).values
    assert state["normalized_product"]["product_class"] == "Bearing"
    assert "attributes.rated_speed" in state["orphaned_overrides"]
    assert page.warning
    assert not page.button(key="approve_case").disabled
