"""Offline verified references, without OWL equivalence or runtime lookup."""

from typing import Literal

from pydantic import AnyHttpUrl, Field, model_validator

from ontoproduct.schemas.common import DomainModel
from ontoproduct.services.mapping_service import read_mapping


class ReferenceSource(DomainModel):
    url: AnyHttpUrl
    version: str = Field(min_length=1)
    license: str = Field(min_length=1)
    license_url: AnyHttpUrl
    attribution: str = Field(min_length=1)
    verified_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class ExternalReference(DomainModel):
    source: str
    uri: AnyHttpUrl | None = None
    relation: Literal["reference", "unit"]
    status: Literal["verified", "unverified"]
    note: str


class ExternalCatalog(DomainModel):
    sources: dict[str, ReferenceSource]
    mappings: dict[str, ExternalReference]

    @model_validator(mode="after")
    def coherent(self):
        for key, item in self.mappings.items():
            if item.source not in self.sources:
                raise ValueError(f"Unknown external source: {key}")
            if item.status == "verified" and item.uri is None:
                raise ValueError(f"Verified reference needs a URI: {key}")
        return self


class ExternalMappings:
    def __init__(self, path=None, *, definition=None):
        self.catalog = ExternalCatalog.model_validate(
            read_mapping("external_mappings.yaml", path) if definition is None else definition
        )

    def verified(self):
        return {key: item.model_dump(mode="json") for key, item in self.catalog.mappings.items()
                if item.status == "verified"}
