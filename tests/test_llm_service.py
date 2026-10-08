import json
from types import SimpleNamespace

import pytest
import yaml

from ontoproduct.agents.extraction_agent import ExtractionResponse
from ontoproduct.agents.ontology_agent import ClassSelection
from ontoproduct.services.llm_protocol import validated_response
from ontoproduct.services.llm_service import (
    LlmResponseError,
    OpenAiLlmService,
    create_llm_services,
    strict_json_schema,
)
from ontoproduct.services.settings import CONFIG_PATH, Settings, SettingsError

SECRET_TEXT = "secret-document-line"
PAYLOAD = {
    "instructions": "TRUSTED RULES",
    "prompt_version": "v1",
    "documents": [{"source_file": "a.txt", "page": None, "text": SECRET_TEXT}],
}
WIRE_EXTRACTION = {
    "product_name": "DM-600",
    "candidate_class": "BLDCMotor",
    "attributes": [
        {
            "key": "rated_power",
            "value": {
                "value": 0.6,
                "unit": "kW",
                "confidence": 0.9,
                "evidence": "Rated Power: 0.6 kW",
                "source_file": "a.txt",
                "page": None,
                "provenance": "AI",
            },
        }
    ],
}


class FakeResponses:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def fake_client(response):
    return SimpleNamespace(responses=FakeResponses(response))


def message(text, *, phase=None, refusal=False):
    item = (
        SimpleNamespace(type="refusal", refusal=text)
        if refusal
        else SimpleNamespace(type="output_text", text=text)
    )
    return SimpleNamespace(type="message", phase=phase, content=[item])


def response(*outputs, status="completed", reason=None):
    details = SimpleNamespace(reason=reason) if reason else None
    return SimpleNamespace(
        status=status, incomplete_details=details, output=list(outputs)
    )


def service_for(resp, model="test-model"):
    client = fake_client(resp)
    return OpenAiLlmService(
        model, timeout_seconds=5, max_retries=0, client=client
    ), client


def test_request_separates_trusted_instructions_from_document_data():
    service, client = service_for(response(message(json.dumps(WIRE_EXTRACTION))))
    service.generate_structured(
        task="extraction", payload=PAYLOAD, response_schema=ExtractionResponse
    )
    [call] = client.responses.calls
    assert call["model"] == "test-model"
    assert call["instructions"] == "TRUSTED RULES"
    [user] = call["input"]
    assert user["role"] == "user"
    assert "TRUSTED RULES" not in user["content"]
    assert json.loads(user["content"]) == {
        k: v for k, v in PAYLOAD.items() if k != "instructions"
    }
    fmt = call["text"]["format"]
    assert (fmt["type"], fmt["name"], fmt["strict"]) == (
        "json_schema",
        "ExtractionResponse",
        True,
    )
    assert fmt["schema"] == strict_json_schema(ExtractionResponse)


def walk(node):
    yield node
    for value in node.values():
        if isinstance(value, dict):
            yield from walk(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield from walk(item)


@pytest.mark.parametrize("schema", [ExtractionResponse, ClassSelection])
def test_wire_schema_satisfies_strict_mode(schema):
    wire = strict_json_schema(schema)
    assert "$defs" not in json.dumps(wire) and "$ref" not in json.dumps(wire)
    for node in walk(wire):
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert node["required"] == list(node["properties"])
        assert "default" not in node


def test_open_keyed_maps_become_key_value_arrays():
    attributes = strict_json_schema(ExtractionResponse)["properties"]["attributes"]
    assert attributes["type"] == "array"
    assert attributes["items"]["required"] == ["key", "value"]


def test_returns_validated_schema_instances_with_maps_restored():
    service, _ = service_for(response(message(json.dumps(WIRE_EXTRACTION))))
    result = validated_response(
        service, task="extraction", payload=PAYLOAD, schema=ExtractionResponse
    )
    assert isinstance(result, ExtractionResponse)
    assert result.attributes["rated_power"].value == 0.6
    service, _ = service_for(
        response(message('{"product_class": "Bearing", "confidence": 0.7}'))
    )
    selection = validated_response(
        service, task="ontology", payload=PAYLOAD, schema=ClassSelection
    )
    assert (selection.product_class, selection.confidence) == ("Bearing", 0.7)


def test_only_final_answer_text_is_parsed():
    service, _ = service_for(
        response(
            message("thinking about it", phase="commentary"),
            message(
                '{"product_class": "Motor", "confidence": 0.5}', phase="final_answer"
            ),
        )
    )
    result = service.generate_structured(
        task="ontology", payload=PAYLOAD, response_schema=ClassSelection
    )
    assert result.product_class == "Motor"


@pytest.mark.parametrize(
    "resp, reason",
    [
        (response(message(SECRET_TEXT, refusal=True)), "거부"),
        (
            response(status="incomplete", reason="max_output_tokens"),
            "max_output_tokens",
        ),
        (response(status="incomplete", reason="content_filter"), "content_filter"),
        (response(status="failed"), "failed"),
        (response(), "빈 응답"),
        (response(message("   ")), "빈 응답"),
        (response(message(f"not json {SECRET_TEXT}")), "JSON"),
        (
            response(message(f'{{"product_class": "{SECRET_TEXT}", "confidence": 2}}')),
            "스키마",
        ),
    ],
)
def test_bad_responses_raise_clear_errors_without_leaking_text(resp, reason):
    service, _ = service_for(resp)
    with pytest.raises(LlmResponseError, match=reason) as error:
        service.generate_structured(
            task="ontology", payload=PAYLOAD, response_schema=ClassSelection
        )
    assert SECRET_TEXT not in str(error.value)
    assert "ontology" in str(error.value)


def test_duplicate_map_keys_are_rejected():
    wire = {**WIRE_EXTRACTION, "attributes": WIRE_EXTRACTION["attributes"] * 2}
    service, _ = service_for(response(message(json.dumps(wire))))
    with pytest.raises(LlmResponseError, match="rated_power"):
        service.generate_structured(
            task="extraction", payload=PAYLOAD, response_schema=ExtractionResponse
        )


def test_missing_instructions_are_rejected_before_any_call():
    service, client = service_for(response())
    with pytest.raises(ValueError, match="instructions"):
        service.generate_structured(
            task="ontology", payload={"documents": []}, response_schema=ClassSelection
        )
    assert client.responses.calls == []


def shipped_models():
    models = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["models"]
    return {agent: models.get(agent) or models["default"] for agent in models}


def test_create_llm_services_uses_configured_models_and_client_settings():
    settings = Settings.from_environment({"AGENT_MODE": "real"})
    services = create_llm_services(settings, environ={"OPENAI_API_KEY": "sk-test-key"})
    expected = shipped_models()["default"]
    assert {agent: s.model for agent, s in services.items()} == {
        "extraction": expected,
        "ontology": expected,
    }
    client = services["extraction"].client
    assert services["ontology"].client is client
    assert client.timeout == settings.timeout_seconds
    assert client.max_retries == settings.max_retries
    assert "sk-test-key" not in repr(services)


def test_create_llm_services_applies_per_agent_model():
    settings = Settings.from_environment(
        {"AGENT_MODE": "real", "LLM_MODEL_ONTOLOGY": "cheaper-model"}
    )
    services = create_llm_services(settings, environ={"OPENAI_API_KEY": "sk-test"})
    assert services["ontology"].model == "cheaper-model"
    assert services["extraction"].model == shipped_models()["default"]


@pytest.mark.parametrize(
    "environ, settings_env, message",
    [
        ({}, {"AGENT_MODE": "real"}, "OPENAI_API_KEY"),
        ({"OPENAI_API_KEY": "  "}, {"AGENT_MODE": "real"}, "OPENAI_API_KEY"),
        (
            {"OPENAI_API_KEY": "sk"},
            {"AGENT_MODE": "real", "LLM_PROVIDER": "other"},
            "openai",
        ),
        ({"OPENAI_API_KEY": "sk"}, {}, "AGENT_MODE=real"),
    ],
)
def test_create_llm_services_rejects_unusable_settings(environ, settings_env, message):
    with pytest.raises(SettingsError, match=message):
        create_llm_services(Settings.from_environment(settings_env), environ=environ)
