from typing import Literal

from pydantic import Field

from .common import DomainModel


class AgentExecution(DomainModel):
    execution_id: str
    agent: str
    status: Literal["running", "success", "warning", "error"]
    message: str
    attempt: int = Field(ge=1)
    execution_time: float | None = Field(default=None, ge=0)
    timestamp: str


class CustomStreamEvent(AgentExecution):
    event: Literal["agent_started", "agent_finished"]
