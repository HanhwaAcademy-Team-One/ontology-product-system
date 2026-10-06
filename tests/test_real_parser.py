import json
import re
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest

from ontoproduct.agents.parser_agent import ParserAgent
from ontoproduct.graph.execution import execute_agent
from ontoproduct.graph.state import initial_state
from ontoproduct.graph.workflow import build_workflow
from ontoproduct.schemas.product import ParsedDocument
from ontoproduct.services.document_service import DocumentService
from ontoproduct.services.parser_service import ParserService

FIXTURES = Path(__file__).parent / "fixtures" / "documents"


@pytest.fixture
def workspace(tmp_path):
    return tmp_path / "uploads"


@pytest.fixture
def upload(workspace):
    documents, session = DocumentService(workspace), str(uuid4())

    def save(fixture, name=None):
        return documents.save(session, name or fixture, (FIXTURES / fixture).read_bytes())
    return save


@pytest.fixture
def parser(workspace):
    return ParserService(workspace)


def assert_valid_output(parsed):
    assert parsed
    for item in parsed:
        assert ParsedDocument.model_validate(item).model_dump(mode="json") == item
    json.dumps(parsed, allow_nan=False)


def test_txt_returns_real_text_without_page(parser, upload):
    parsed = parser.parse([upload("motor_spec.txt")])
    assert_valid_output(parsed)
    assert len(parsed) == 1
    assert parsed[0]["source_file"] == "motor_spec.txt"
    assert "Product: DM-600" in parsed[0]["text"]
    assert parsed[0]["page"] is None


@pytest.mark.parametrize("fixture", ["motor_spec.txt", "motor_spec_cp949.txt"])
def test_mixed_korean_english_text_is_not_broken(parser, upload, fixture):
    text = parser.parse([upload(fixture)])[0]["text"]
    assert "비고: 한글 English 혼합 문서" in text
    assert "�" not in text


def test_pdf_returns_one_item_per_page(parser, upload):
    parsed = parser.parse([upload("two_page_spec.pdf")])
    assert_valid_output(parsed)
    assert [item["page"] for item in parsed] == [1, 2]
    assert "Manufacturer: XYZ Motors" in parsed[0]["text"]
    assert "Power" not in parsed[0]["text"]
    assert "Electrical Ratings" in parsed[1]["text"]


def test_pdf_table_keeps_item_value_unit_relation(parser, upload):
    text = parser.parse([upload("two_page_spec.pdf")])[1]["text"]
    assert "Item | Value | Unit" in text
    assert "Power | 0.6 | kW" in text
    assert "Speed | 3200 | rpm" in text


def test_xlsx_keeps_both_sheets_and_cell_positions(parser, upload):
    parsed = parser.parse([upload("two_sheet_spec.xlsx")])
    assert_valid_output(parsed)
    assert all(item["page"] is None for item in parsed)
    spec, electrical = (item["text"] for item in parsed)
    assert "[Sheet: Spec, Row: 3] A3=Manufacturer | B3=XYZ Motors" in spec
    assert "[Sheet: Spec, Row: 4] A4=정격 전압 | B4=24 | C4=V" in spec
    assert "[Sheet: Electrical, Row: 1] A1=Rated Power | B1=0.6 | C1=kW" in electrical
    assert "[Sheet: Electrical, Row: 3] A3=Rated Speed | B3=3200 | C3=rpm" in electrical


def test_multiple_documents_all_appear_with_distinct_sources(parser, upload):
    refs = [upload("motor_spec.txt"), upload("two_page_spec.pdf"), upload("two_sheet_spec.xlsx"),
            upload("motor_spec_cp949.txt", "motor_spec.txt")]
    parsed = parser.parse(refs)
    assert_valid_output(parsed)
    sources = {item["source_file"] for item in parsed}
    duplicate_labels = {f"motor_spec.txt ({ref['file_id'][:8]})" for ref in (refs[0], refs[3])}
    assert sources == {"two_page_spec.pdf", "two_sheet_spec.xlsx"} | duplicate_labels


def test_parse_does_not_mutate_references(parser, upload):
    refs = [upload("motor_spec.txt")]
    before = deepcopy(refs)
    parser.parse(refs)
    assert refs == before


@pytest.mark.parametrize("fixture, message", [
    ("corrupt.pdf", "corrupt.pdf: 문서를 읽을 수 없습니다"),
    ("corrupt.xlsx", "corrupt.xlsx: 문서를 읽을 수 없습니다"),
    ("scanned.pdf", "scanned.pdf: 읽을 수 있는 텍스트가 없습니다 (스캔 PDF OCR 미지원)"),
])
def test_unreadable_documents_raise_clear_errors(parser, upload, fixture, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        parser.parse([upload(fixture)])


def test_missing_or_outside_paths_are_rejected(parser, upload, tmp_path):
    missing = upload("motor_spec.txt")
    Path(missing["path"]).unlink()
    outside = tmp_path / "outside.txt"
    outside.write_bytes((FIXTURES / "motor_spec.txt").read_bytes())
    escaped = {**upload("motor_spec.txt"), "path": str(outside)}
    for refs in ([missing], [escaped], []):
        with pytest.raises(ValueError):
            parser.parse(refs)


def test_agent_satisfies_contract_through_wrapper(registry, parser, upload):
    agent = ParserAgent(parser)
    registry.register(agent, replace=True)
    inputs = {"source_documents": [upload("motor_spec.txt"), upload("two_page_spec.pdf")]}
    before = deepcopy(inputs)
    events = []
    result = execute_agent(registry, agent.name, inputs, writer=events.append)
    assert inputs == before
    assert result["agent_logs"][-1]["status"] == "success"
    assert not result["error_events"]
    assert set(result) == set(agent.writes) | {"agent_logs", "error_events"}
    assert [item["page"] for item in result["parsed_documents"]] == [None, 1, 2]
    json.dumps(result, allow_nan=False)
    assert [event["event"] for event in events] == ["agent_started", "agent_finished"]


def test_wrapper_records_error_event_for_corrupt_document(registry, parser, upload):
    registry.register(ParserAgent(parser), replace=True)
    result = execute_agent(registry, "parser", {"source_documents": [upload("corrupt.pdf")]},
                           writer=lambda event: None)
    assert "parsed_documents" not in result
    assert result["agent_logs"][-1]["status"] == "error"
    [error] = result["error_events"]
    assert error["stage"] == "parser" and error["status"] == "OPEN"
    assert error["message"].startswith("corrupt.pdf: 문서를 읽을 수 없습니다")


def test_graph_carries_real_parsed_text(complete_registry, ontology, config, parser, upload):
    complete_registry.register(ParserAgent(parser), replace=True)
    graph = build_workflow(complete_registry, ontology=ontology)
    graph.invoke(initial_state([upload("motor_spec.txt")]), config)
    [document] = graph.get_state(config).values["parsed_documents"]
    assert "Product: DM-600" in document["text"]
    assert document["page"] is None
