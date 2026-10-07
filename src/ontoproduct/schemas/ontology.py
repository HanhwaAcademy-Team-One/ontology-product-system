from typing import Literal

from pydantic import Field, model_validator

from .common import DomainModel


class PropertyDefinition(DomainModel):
    type: Literal["string", "number", "integer", "boolean"]
    canonical_unit: str | None = None
    units: list[str] = Field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None

    @model_validator(mode="after")
    def coherent(self):
        if self.canonical_unit and self.canonical_unit not in self.units:
            raise ValueError("canonical_unit must be an allowed unit")
        if self.units and not self.canonical_unit:
            raise ValueError("units require canonical_unit")
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError("minimum exceeds maximum")
        return self


class OntologyClass(DomainModel):
    parent: str | None = None
    required_properties: dict[str, PropertyDefinition] = Field(default_factory=dict)
    optional_properties: dict[str, PropertyDefinition] = Field(default_factory=dict)

    @model_validator(mode="after")
    def disjoint(self):
        if self.required_properties.keys() & self.optional_properties.keys():
            raise ValueError("A property cannot be both required and optional")
        return self


class OntologyDefinition(DomainModel):
    classes: dict[str, OntologyClass]

    @model_validator(mode="after")
    def valid_hierarchy(self):
        for name in self.classes:
            seen = set()
            current = name
            while current is not None:
                if current in seen:
                    raise ValueError(f"Ontology inheritance cycle at {current}")
                if current not in self.classes:
                    raise ValueError(f"Unknown parent class: {current}")
                seen.add(current)
                current = self.classes[current].parent
        return self


class OntologyMapping(DomainModel):
    product_class: str
    confidence: float = Field(ge=0, le=1)
    required_properties: dict[str, PropertyDefinition]
    optional_properties: dict[str, PropertyDefinition]
