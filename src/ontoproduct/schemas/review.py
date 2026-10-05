from enum import Enum

from pydantic import Field, model_validator

from .common import DomainModel


class ReviewDecision(str, Enum):
    READY_FOR_HUMAN = "READY_FOR_HUMAN"
    RE_EXTRACT = "RE_EXTRACT"
    REMAP_ONTOLOGY = "REMAP_ONTOLOGY"
    NEEDS_FIX = "NEEDS_FIX"
    REJECT = "REJECT"


class ReviewResult(DomainModel):
    decision: ReviewDecision
    reason: str
    retry_fields: list[str] = Field(default_factory=list)
    can_register: bool

    @model_validator(mode="after")
    def coherent(self):
        if self.can_register != (self.decision == ReviewDecision.READY_FOR_HUMAN):
            raise ValueError("Only READY_FOR_HUMAN may set can_register=true")
        return self
