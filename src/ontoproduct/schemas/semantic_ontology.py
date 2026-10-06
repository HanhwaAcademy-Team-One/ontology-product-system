"""Internal ontology design schema, separate from workflow JSON contracts."""

from typing import Literal

from pydantic import Field, model_validator

from .common import DomainModel
from .ontology import PropertyDefinition


class EntityClass(DomainModel):
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    parent: str | None = None
    external_parents: list[str] = Field(default_factory=list)


class SemanticRelation(DomainModel):
    label: str
    description: str
    domain: str
    range: str
    external_parent: str


class ProductProfile(DomainModel):
    label: str
    description: str
    parent: str | None = None
    model_class: str
    item_class: str
    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)


class SemanticProperty(DomainModel):
    label: str
    description: str
    kind: Literal["entity", "quantity"]
    predicate: str
    domain: str
    quantity: str | None = None
    definition: PropertyDefinition

    @model_validator(mode="after")
    def coherent(self):
        if self.kind == "quantity":
            if not self.quantity or self.definition.type not in ("number", "integer") or not self.definition.canonical_unit:
                raise ValueError("Quantity properties require a numeric type, quantity kind and unit")
        elif self.quantity or self.definition.type != "string" or self.definition.canonical_unit:
            raise ValueError("Manufacturer name projection must be a unitless string")
        return self


class ClassificationRule(DomainModel):
    product_class: str
    all_of: list[str] = Field(default_factory=list)
    any_of: list[str] = Field(default_factory=list)
    minimum_matches: int = Field(default=0, ge=0)
    none_of: list[str] = Field(default_factory=list)
    candidate_refinements: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def coherent(self):
        if self.minimum_matches > len(set(self.any_of)):
            raise ValueError("Classification rule requires too many matches")
        if not self.all_of and self.minimum_matches == 0:
            raise ValueError("Classification rule requires positive evidence")
        return self


class PropertyComparison(DomainModel):
    product_class: str
    left: str
    right: str
    operator: Literal["less_than"]


class ProductSemanticDefinition(DomainModel):
    namespace: str = Field(pattern=r"^urn:ontoproduct:[A-Za-z0-9:._-]+:$")
    version: str
    entity_classes: dict[str, EntityClass]
    relations: dict[str, SemanticRelation]
    classes: dict[str, ProductProfile]
    properties: dict[str, SemanticProperty]
    classification_rules: list[ClassificationRule]
    comparisons: list[PropertyComparison] = Field(default_factory=list)
