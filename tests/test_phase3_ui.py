import json

from test_streamlit_app import app, fill_speed


def test_dashboard_empty_and_registered_stats_and_reopen(app):
    page, runtime, _ = app
    page.switch_page("src/ontoproduct/views/dashboard.py").run()
    assert not page.exception
    assert [metric.value for metric in page.metric[:4]] == ["0", "0", "0", "0"]
    page.button(key="dashboard_start").click().run()
    assert page.button(key="start_demo")
    # AppTest keeps its explicit page hash after st.switch_page; synchronize the next simulated request.
    page.switch_page("src/ontoproduct/views/registration.py").run()
    page.button(key="start_demo").click().run()
    case = page.session_state["thread_id"]
    fill_speed(page)
    page.button(key="approve_case").click().run()
    page.switch_page("src/ontoproduct/views/dashboard.py").run()
    assert not page.exception
    assert [metric.value for metric in page.metric[:4]] == ["1", "0", "1", "0"]
    page.button(key="open_dashboard_case").click().run()
    assert not page.exception
    assert page.session_state["thread_id"] == case
    assert page.query_params["case"] == [case]
    assert page.download_button(key="download_registered")


def test_ontology_hierarchy_inherited_fields_and_real_unit_conversion(app):
    page, _, _ = app
    page.switch_page("src/ontoproduct/views/ontology_explorer.py").run()
    assert not page.exception
    rows = page.dataframe[0].value
    assert len(rows) == 5
    assert rows.loc[rows["키"] == "manufacturer", "정의 클래스"].item() == "Motor"
    page.selectbox(key="preview_property").select("rated_power").run()
    page.selectbox(key="preview_unit").select("kW").run()
    page.button(key="preview_convert").click().run()
    assert not page.exception
    assert "500.0 W" in page.success[0].value
    page.selectbox(key="ontology_class").select("Bearing").run()
    assert not page.exception
    assert len(page.dataframe[0].value) == 2


def test_monitor_metadata_logs_and_compiled_graph(app):
    page, runtime, _ = app
    page.switch_page("src/ontoproduct/views/agent_monitor.py").run()
    assert not page.exception
    table = page.dataframe[0].value
    assert len(table) == 7
    assert set(table["모드"]) == {"Mock", "Real"}
    assert table["실행 수"].sum() == 0
    assert page.download_button(key="download_graph")
    page.button(key="new_case").click().run()
    assert page.button(key="start_demo")
    page.switch_page("src/ontoproduct/views/registration.py").run()
    page.button(key="start_demo").click().run()
    page.switch_page("src/ontoproduct/views/agent_monitor.py").run()
    assert not page.exception
    table = page.dataframe[0].value
    assert table.loc[table["Agent"] == "extraction", "실행 수"].item() == 2
    page.selectbox(key="monitor_agent").select("registration").run()
    assert not page.exception
    assert any("human_review" in element.value for element in page.markdown)


def test_evaluation_ui_calculates_downloads_and_leaves_products_untouched(app):
    page, runtime, root = app
    page.switch_page("src/ontoproduct/views/evaluation.py").run()
    assert not page.exception
    page.button(key="run_evaluation").click().run()
    assert not page.exception
    assert runtime.products.count() == 0
    report = json.loads((root / "evaluation" / "evaluation.json").read_text(encoding="utf-8"))
    assert report["suites"][0]["label"] == "MOCK EVALUATION"
    assert report["suites"][1]["label"] == "RULE ENGINE EVALUATION"
    assert page.download_button(key="download_evaluation_json")
    assert page.download_button(key="download_evaluation_report")
    assert len(page.dataframe) == 2
    page.selectbox(key="evaluation_sample_0").select("product_003").run()
    assert not page.exception


def test_database_filters_registration_and_class(app):
    page, runtime, _ = app
    page.switch_page("src/ontoproduct/views/product_database.py").run()
    page.button(key="seed_database").click().run()
    page.selectbox(key="product_origin_filter").select("REGISTRATION").run()
    assert not page.exception
    assert not any(box.key == "selected_product" for box in page.selectbox)
    page.selectbox(key="product_origin_filter").select("SEED").run()
    assert len(page.selectbox(key="selected_product").options) == 3
    page.selectbox(key="product_class_filter").select("Bearing").run()
    assert not page.exception
    assert any("표시할 제품" in info.value for info in page.info)
