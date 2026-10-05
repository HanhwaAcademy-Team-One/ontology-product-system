from pydantic import Field

from .common import DomainModel


class DuplicateCandidate(DomainModel):
    product_id: str
    product_name: str
    score: float = Field(ge=0, le=1)
    reason: str
