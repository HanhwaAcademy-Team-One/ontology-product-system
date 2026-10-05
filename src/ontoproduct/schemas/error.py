from typing import Literal

from pydantic import Field

from .common import DomainModel


class WorkflowErrorEvent(DomainModel):
    error_id: str
    stage: str
    attempt: int = Field(ge=1)
    status: Literal["OPEN", "RESOLVED"]
    message: str
    recoverable: bool
    exception_type: str | None = None
    timestamp: str


def unresolved_errors(events: list[dict]) -> list[dict]:
    latest = {}
    for event in events:
        latest[event["error_id"]] = event
    return [e for e in latest.values() if e["status"] == "OPEN"]
