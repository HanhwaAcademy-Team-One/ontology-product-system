"""Provider-independent contract. The integration owner supplies the adapter."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LlmService(Protocol):
    def generate_structured(
        self, *, task: str, payload: dict, response_schema: type[T]
    ) -> T:
        """Return a validated model; keep instructions separate from document data."""
        ...


def validated_response(service: LlmService, *, task: str, payload: dict, schema: type[T]) -> T:
    response = service.generate_structured(task=task, payload=payload, response_schema=schema)
    if not isinstance(response, schema):
        raise ValueError(f"{task}: LLM adapter must return {schema.__name__}, not {type(response).__name__}")
    # Revalidate even models constructed without validation by an adapter.
    return schema.model_validate(response.model_dump(mode="python"))
