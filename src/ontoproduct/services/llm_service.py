"""OpenAI adapter for the provider-independent LlmService protocol.

The model receives a strict JSON schema derived from the requested Pydantic
model: open-keyed maps (``dict[str, X]``) are not expressible in strict mode, so
they are sent as ``[{key, value}]`` arrays and restored before local Pydantic
validation. Trusted ``instructions`` and untrusted document data travel separately.
"""

import json
import os

from openai import OpenAI
from pydantic import ValidationError

from ontoproduct.services.settings import LLM_AGENTS, SettingsError

# Leaf keywords sent to the model. Numeric/length constraints and defaults are
# enforced locally by Pydantic after the response is parsed.
LEAF_KEYWORDS = {"type", "enum", "const", "description"}


class LlmResponseError(ValueError):
    """The model returned no usable structured result. Messages never echo raw text."""


class OpenAiLlmService:
    """Responses API (`client.responses.create`) with a strict json_schema text format."""

    def __init__(self, model, *, timeout_seconds, max_retries, client=None):
        self.model = model
        # The SDK reads OPENAI_API_KEY itself when no client is supplied.
        self.client = (
            client
            if client is not None
            else OpenAI(timeout=timeout_seconds, max_retries=max_retries)
        )

    def __repr__(self):
        return f"OpenAiLlmService(model={self.model!r})"

    def generate_structured(self, *, task, payload, response_schema):
        instructions, data = _split_payload(task, payload)
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=[{"role": "user", "content": data}],
            text={
                "format": {
                    "type": "json_schema",
                    "name": response_schema.__name__,
                    "schema": strict_json_schema(response_schema),
                    "strict": True,
                }
            },
        )
        return _parse_structured(task, _openai_text(task, response), response_schema)


def create_llm_services(settings, environ=None):
    """Build one LlmService per LLM agent from validated real-mode settings."""
    env = os.environ if environ is None else environ
    if settings.mode != "real":
        raise SettingsError("LLM 서비스는 AGENT_MODE=real에서만 만듭니다")
    if settings.provider != "openai":
        raise SettingsError(
            f"지원하는 LLM_PROVIDER는 openai입니다 (현재 {settings.provider!r})"
        )
    api_key = env.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SettingsError(
            "AGENT_MODE=real, LLM_PROVIDER=openai 실행에는 OPENAI_API_KEY 환경변수가 필요합니다"
        )
    client = OpenAI(
        api_key=api_key,
        timeout=settings.timeout_seconds,
        max_retries=settings.max_retries,
    )
    return {
        agent: OpenAiLlmService(
            settings.model_for(agent),
            timeout_seconds=settings.timeout_seconds,
            max_retries=settings.max_retries,
            client=client,
        )
        for agent in LLM_AGENTS
    }


def _split_payload(task, payload):
    instructions = payload.get("instructions")
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError(f"{task}: payload requires trusted instructions")
    data = {key: value for key, value in payload.items() if key != "instructions"}
    return instructions, json.dumps(data, ensure_ascii=False, sort_keys=True)


def _parse_structured(task, text, response_schema):
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        raise LlmResponseError(f"{task}: 모델 응답이 JSON이 아닙니다") from None
    schema = response_schema.model_json_schema()
    restored = _restore(task, value, schema, schema.get("$defs", {}))
    try:
        return response_schema.model_validate(restored)
    except ValidationError as exc:
        fields = sorted(
            {
                ".".join(str(part) for part in error["loc"]) or "<root>"
                for error in exc.errors(include_input=False, include_url=False)
            }
        )
        raise LlmResponseError(
            f"{task}: 모델 응답이 {response_schema.__name__} 스키마와 맞지 않습니다 "
            f"({', '.join(fields)})"
        ) from None


def strict_json_schema(model):
    """Strict-mode schema for a Pydantic model: inlined, all required, closed objects."""
    schema = model.model_json_schema()
    return _strict(schema, schema.get("$defs", {}))


def _resolve(node, defs):
    while True:
        if "$ref" in node:
            node = defs[node["$ref"].rsplit("/", 1)[-1]]
        elif len(node.get("allOf", ())) == 1:
            node = node["allOf"][0]
        else:
            return node


def _is_map(node):
    return (
        node.get("type") == "object"
        and not node.get("properties")
        and isinstance(node.get("additionalProperties"), dict)
    )


def _strict(node, defs):
    node = _resolve(node, defs)
    if "anyOf" in node:
        return {"anyOf": [_strict(option, defs) for option in node["anyOf"]]}
    if _is_map(node):
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": _strict(node["additionalProperties"], defs),
                },
                "required": ["key", "value"],
                "additionalProperties": False,
            },
        }
    if node.get("type") == "object":
        properties = {
            key: _strict(value, defs)
            for key, value in node.get("properties", {}).items()
        }
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        }
    if node.get("type") == "array":
        return {"type": "array", "items": _strict(node.get("items", {}), defs)}
    return {key: value for key, value in node.items() if key in LEAF_KEYWORDS}


def _restore(task, value, node, defs):
    """Turn [{key, value}] arrays back into dicts wherever the real schema has a map."""
    node = _resolve(node, defs)
    if "anyOf" in node:
        for option in node["anyOf"]:
            option = _resolve(option, defs)
            kind = "array" if _is_map(option) else option.get("type")
            if (kind == "array" and isinstance(value, list)) or (
                kind == "object" and isinstance(value, dict)
            ):
                return _restore(task, value, option, defs)
        return value
    if _is_map(node) and isinstance(value, list):
        restored = {}
        for item in value:
            if not isinstance(item, dict) or set(item) != {"key", "value"}:
                raise LlmResponseError(
                    f"{task}: 모델 응답의 key/value 항목 형식이 잘못되었습니다"
                )
            key = item["key"]
            if key in restored:
                raise LlmResponseError(
                    f"{task}: 모델 응답에 중복 항목 {key!r}가 있습니다"
                )
            restored[key] = _restore(
                task, item["value"], node["additionalProperties"], defs
            )
        return restored
    if node.get("type") == "object" and isinstance(value, dict):
        properties = node.get("properties", {})
        return {
            key: _restore(task, item, properties[key], defs)
            if key in properties
            else item
            for key, item in value.items()
        }
    if node.get("type") == "array" and isinstance(value, list):
        return [_restore(task, item, node.get("items", {}), defs) for item in value]
    return value


def _openai_text(task, response):
    status = getattr(response, "status", None)
    if status == "incomplete":
        details = getattr(response, "incomplete_details", None)
        reason = getattr(details, "reason", None) or "unknown"
        raise LlmResponseError(
            f"{task}: 모델 응답이 완료되지 않았습니다 (incomplete: {reason})"
        )
    if status not in (None, "completed"):
        raise LlmResponseError(f"{task}: 모델 응답 상태가 {status}입니다")
    texts = []
    for output in getattr(response, "output", None) or []:
        # Like the SDK's parse helper, only final-answer messages carry the result.
        if output.type != "message" or getattr(output, "phase", None) not in (
            None,
            "final_answer",
        ):
            continue
        for item in output.content or []:
            if item.type == "refusal":
                raise LlmResponseError(f"{task}: 모델이 요청을 거부했습니다")
            if item.type == "output_text" and item.text:
                texts.append(item.text)
    text = "".join(texts).strip()
    if not text:
        raise LlmResponseError(f"{task}: 모델이 빈 응답을 반환했습니다")
    return text
