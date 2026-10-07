from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from streamlit.testing.v1 import AppTest

from ontoproduct.agents.real_registry import build_document_registry
from ontoproduct.graph.execution import execute_agent
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.document_service import DocumentService
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.services.parser_service import ParserService
from ontoproduct.services.settings import CONFIG_PATH, Settings
from ontoproduct.services.workflow_runtime import WorkflowRuntime
from ontoproduct.views import resources
from real_llm_helpers import HonestLlm

FIXTURES = Path(__file__).parent / "fixtures" / "documents"
APP = Path(__file__).resolve().parents[1] / "app.py"
SESSION = "11111111-1111-4111-8111-111111111111"
MIME = {
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def registry_for(root, llm=None, ontology=None):
    llm = llm or HonestLlm()
    return build_document_registry(
        ontology or OntologyService(),
        parser_service=ParserService(root),
        llm_services={"extraction": llm, "ontology": llm},
    )


def run_chain(tmp_path, *names):
    documents = DocumentService(tmp_path)
    refs = [documents.save(SESSION, n, (FIXTURES / n).read_bytes()) for n in names]
    registry = registry_for(tmp_path)

    def run(agent, inputs):
        result = execute_agent(registry, agent, inputs, writer=lambda event: None)
        assert not result["error_events"], result["error_events"]
        return result

    parsed = run("parser", {"source_documents": refs})["parsed_documents"]
    extracted = run("extraction", {"parsed_documents": parsed})["extracted_product"]
    ontology = run("ontology", {"extracted_product": extracted})
    return parsed, extracted, ontology


def attribute(product, key):
    item = product["attributes"][key]
    return item["value"], item["unit"], item["source_file"], item["page"]


def test_document_registry_replaces_only_document_slots(tmp_path):
    registry = registry_for(tmp_path)
    modes = {a["name"]: a["is_mock"] for a in registry.metadata()}
    assert modes == {
        "parser": False,
        "extraction": False,
        "ontology": False,
        "validation": True,
        "duplicate": True,
        "reviewer": True,
        "registration": True,
    }
    registry.validate_complete()


def test_shared_ontology_instance_is_used_by_extraction_and_ontology(tmp_path):
    ontology = OntologyService()
    registry = registry_for(tmp_path, ontology=ontology)
    assert registry.get("extraction").ontology is ontology
    assert registry.get("ontology").ontology is ontology


def test_txt_reaches_ontology_with_real_text_and_unit_conversion(tmp_path):
    parsed, extracted, result = run_chain(tmp_path, "motor_spec.txt")
    assert [d["page"] for d in parsed] == [None]
    assert "Product: DM-600" in parsed[0]["text"]
    assert (extracted["product_name"], extracted["candidate_class"]) == (
        "DM-600",
        "BLDCMotor",
    )
    assert result["ontology_mapping"]["product_class"] == "BLDCMotor"
    product = result["base_normalized_product"]
    assert attribute(product, "rated_power") == (600.0, "W", "motor_spec.txt", None)
    assert product["attributes"]["rated_power"]["evidence"] == "Rated Power: 0.6 kW"


def test_pdf_pages_are_preserved_through_ontology(tmp_path):
    parsed, _, result = run_chain(tmp_path, "two_page_spec.pdf")
    assert [d["page"] for d in parsed] == [1, 2]
    product = result["base_normalized_product"]
    assert attribute(product, "manufacturer") == (
        "XYZ Motors",
        None,
        "two_page_spec.pdf",
        1,
    )
    assert attribute(product, "rated_power") == (600.0, "W", "two_page_spec.pdf", 2)


def test_xlsx_row_evidence_passes_extraction_validation(tmp_path):
    parsed, extracted, result = run_chain(tmp_path, "two_sheet_spec.xlsx")
    assert all(d["page"] is None for d in parsed)
    evidence = extracted["attributes"]["rated_power"]["evidence"]
    assert evidence == "[Sheet: Electrical, Row: 1] A1=Rated Power | B1=0.6 | C1=kW"
    assert result["ontology_mapping"]["product_class"] == "BLDCMotor"
    assert attribute(result["base_normalized_product"], "rated_power")[:2] == (
        600.0,
        "W",
    )


@pytest.fixture
def runtime_with_fake_llm(tmp_path):
    paths = ApplicationPaths(tmp_path)
    llm = HonestLlm()

    def factory(ontology):
        return build_document_registry(
            ontology,
            parser_service=ParserService(paths.uploads),
            llm_services={"extraction": llm, "ontology": llm},
        )

    runtime = WorkflowRuntime(paths, registry_factory=factory)
    yield runtime, llm
    runtime.close()


def start(runtime, *names):
    session = str(uuid4())
    thread = runtime.create_case(session)
    refs = [
        runtime.documents.save(session, n, (FIXTURES / n).read_bytes()) for n in names
    ]
    list(runtime.start(thread, refs))
    return thread, runtime.snapshot(thread).values


def test_runtime_runs_real_documents_to_human_review_without_saving(
    runtime_with_fake_llm,
):
    runtime, _ = runtime_with_fake_llm
    thread, state = start(runtime, "motor_spec.txt", "two_page_spec.pdf")
    assert "Product: DM-600" in state["parsed_documents"][0]["text"]
    assert state["extracted_product"]["product_name"] == "DM-600"
    assert state["ontology_mapping"]["product_class"] == "BLDCMotor"
    assert state["normalized_product"]["attributes"]["rated_power"]["value"] == 600.0
    assert state["review_result"]["decision"] == "READY_FOR_HUMAN"
    assert runtime.products.count() == 0
    modes = {a["name"]: a["is_mock"] for a in runtime.agent_metadata(thread)}
    assert [n for n, mock in modes.items() if not mock] == [
        "parser",
        "extraction",
        "ontology",
        "duplicate",
        "registration",
    ]


def test_runtime_corrupt_pdf_stops_at_parser(runtime_with_fake_llm):
    runtime, llm = runtime_with_fake_llm
    _, state = start(runtime, "corrupt.pdf")
    [error] = state["error_events"]
    assert (error["stage"], error["status"]) == ("parser", "OPEN")
    assert error["message"].startswith("corrupt.pdf: 문서를 읽을 수 없습니다")
    assert not state.get("extracted_product")
    assert llm.calls == []
    assert runtime.products.count() == 0


@pytest.fixture
def real_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ONTOPRODUCT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AGENT_MODE", "real")
    for name in (
        "LLM_PROVIDER",
        "LLM_MODEL",
        "LLM_MODEL_EXTRACTION",
        "LLM_MODEL_ONTOLOGY",
    ):
        monkeypatch.delenv(name, raising=False)
    resources.get_runtime.clear()
    yield tmp_path
    resources.get_runtime.clear()


def test_real_mode_without_api_key_shows_settings_error(real_app, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    page = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not page.exception
    assert any("OPENAI_API_KEY" in error.value for error in page.error)
    assert not any(b.key in {"start_demo", "start_upload"} for b in page.button)
    assert not any("Mock 추출 모드" in c.value for c in page.caption)


def test_real_mode_with_injected_llm_processes_uploads(real_app, monkeypatch):
    llm = HonestLlm()
    monkeypatch.setattr(
        resources,
        "create_llm_services",
        lambda settings: {"extraction": llm, "ontology": llm},
    )
    page = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not page.exception
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    label = f"{config['provider']}/{config['models']['default']}"
    captions = " ".join(c.value for c in page.caption)
    assert "실제 문서 분석" in captions and label in captions
    assert not any(b.key == "start_demo" for b in page.button)
    names = ["motor_spec.txt", "two_page_spec.pdf"]
    page.file_uploader[0].set_value(
        [(n, (FIXTURES / n).read_bytes(), MIME[Path(n).suffix]) for n in names]
    ).run()
    page.button(key="start_upload").click().run()
    assert not page.exception
    runtime = resources.get_runtime(
        str(real_app), resources.settings_json(Settings.from_environment())
    )
    state = runtime.snapshot(page.session_state["thread_id"]).values
    assert state["extracted_product"]["product_name"] == "DM-600"
    assert state["review_result"]["decision"] == "READY_FOR_HUMAN"
    assert runtime.products.count() == 0
    assert set(llm.calls) == {"extraction", "ontology"}
    page.switch_page("src/ontoproduct/views/agent_monitor.py").run()
    assert not page.exception
    [table] = [f.value for f in page.dataframe if "모드" in f.value.columns]
    modes = dict(zip(table["Agent"], table["모드"]))
    assert {k: modes[k] for k in ("parser", "extraction", "ontology")} == {
        "parser": "Real",
        "extraction": "Real",
        "ontology": "Real",
    }
    assert (modes["validation"], modes["reviewer"]) == ("Mock", "Mock")
