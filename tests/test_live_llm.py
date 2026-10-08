"""Opt-in real LLM calls. Default pytest skips this file so no data leaves the machine.

The models come from config/llm.yaml or LLM_* environment variables.
Run explicitly (with OPENAI_API_KEY set):
  ONTOPRODUCT_LIVE_LLM=1 .venv/Scripts/python.exe -m pytest tests/test_live_llm.py -q -s
"""

import os
import time
from pathlib import Path

import pytest

from ontoproduct.agents.real_registry import build_document_registry
from ontoproduct.graph.execution import execute_agent
from ontoproduct.services.document_service import DocumentService
from ontoproduct.services.llm_service import create_llm_services
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.services.parser_service import ParserService
from ontoproduct.services.settings import Settings

pytestmark = pytest.mark.skipif(
    os.environ.get("ONTOPRODUCT_LIVE_LLM") != "1",
    reason="live LLM test: set ONTOPRODUCT_LIVE_LLM=1 and OPENAI_API_KEY",
)

FIXTURES = Path(__file__).parent / "fixtures" / "documents"


@pytest.mark.parametrize("name", ["motor_spec.txt", "two_page_spec.pdf"])
def test_real_model_extracts_and_classifies_sample(tmp_path, name):
    settings = Settings.from_environment({**os.environ, "AGENT_MODE": "real"})
    ontology = OntologyService()
    registry = build_document_registry(
        ontology,
        parser_service=ParserService(tmp_path),
        llm_services=create_llm_services(settings),
    )
    ref = DocumentService(tmp_path).save(
        "11111111-1111-4111-8111-111111111111", name, (FIXTURES / name).read_bytes()
    )

    def run(agent, inputs):
        result = execute_agent(registry, agent, inputs, writer=lambda event: None)
        assert not result["error_events"], [
            e["message"] for e in result["error_events"]
        ]
        return result

    parsed = run("parser", {"source_documents": [ref]})["parsed_documents"]
    started = time.perf_counter()
    extracted = run("extraction", {"parsed_documents": parsed})["extracted_product"]
    extraction_seconds = time.perf_counter() - started
    result = run("ontology", {"extracted_product": extracted})
    total_seconds = time.perf_counter() - started
    product = result["base_normalized_product"]
    mapping = result["ontology_mapping"]
    print(
        f"\n[{name}] {settings.provider} {settings.models}"
        f" extraction={extraction_seconds:.1f}s total={total_seconds:.1f}s"
        f"\n  class={mapping['product_class']} confidence={mapping['confidence']}"
        f"\n  attributes={product['attributes']}"
    )
    assert product["product_name"] == "DM-600"
    assert result["ontology_mapping"]["product_class"] == "BLDCMotor"
    power = product["attributes"]["rated_power"]
    assert (power["value"], power["unit"]) == (600.0, "W")
    texts = {(d["source_file"], d["page"]): d["text"] for d in parsed}
    # Extraction already verified the quote; check it is a real line of the source.
    assert power["evidence"] in texts[(power["source_file"], power["page"])]
    assert product["attributes"]["manufacturer"]["value"] == "XYZ Motors"
