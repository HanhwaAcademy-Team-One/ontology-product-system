from typing import Literal

from pydantic import Field, StrictBool, StrictFloat, StrictInt, StrictStr

from .common import DomainModel


class ProductAttribute(DomainModel):
    value: StrictStr | StrictInt | StrictFloat | StrictBool | None
    unit: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence: str | None = None
    source_file: str | None = None
    page: int | None = Field(default=None, ge=1)
    provenance: Literal["AI", "HUMAN", "DOCUMENT", "RULE"] | None = None


class ExtractedProduct(DomainModel):
    product_name: str | None = None
    candidate_class: str | None = None
    attributes: dict[str, ProductAttribute] = Field(default_factory=dict)


class NormalizedProduct(DomainModel):
    product_name: str | None = None
    product_class: str
    attributes: dict[str, ProductAttribute] = Field(default_factory=dict)


class ParsedDocument(DomainModel):
    source_file: str
    text: str
    page: int | None = Field(default=None, ge=1)


class FileReference(DomainModel):
    file_id: str
    name: str
    path: str
    mime_type: str
    size: int = Field(ge=0)
