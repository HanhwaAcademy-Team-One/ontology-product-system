from typing import Literal

from pydantic import Field, StrictBool, StrictFloat, StrictInt, StrictStr

from .common import DomainModel


class DuplicateEvidence(DomainModel):
    field: str
    status: Literal["MATCH", "NEAR", "CONFLICT", "MISSING"]
    query_value: StrictStr | StrictInt | StrictFloat | StrictBool | None = None
    candidate_value: StrictStr | StrictInt | StrictFloat | StrictBool | None = None
    unit: str | None = None


class DuplicateCandidate(DomainModel):
    product_id: str
    product_name: str
    score: float = Field(ge=0, le=1)
    reason: str
    # Optional so existing producers (e.g. DuplicateMock) stay valid; the rule engine always fills them.
    verdict: Literal["LIKELY_DUPLICATE", "POSSIBLE_DUPLICATE"] | None = None
    evidence: list[DuplicateEvidence] = Field(default_factory=list)
