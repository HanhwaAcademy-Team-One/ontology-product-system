"""Validated local vocabulary and a single unit conversion implementation."""

from math import isclose, isfinite
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, model_validator

from ontoproduct.schemas.common import DomainModel
from ontoproduct.schemas.ontology import PropertyDefinition
from ontoproduct.schemas.product import ProductAttribute

DATA_DIR = Path(__file__).parents[1] / "ontology"


def read_mapping(filename: str, path: str | Path | None = None):
    return yaml.safe_load((Path(path) if path is not None else DATA_DIR / filename).read_text(encoding="utf-8"))


def alias_key(value: str) -> str:
    return " ".join(value.split()).casefold()


class AliasDefinition(DomainModel):
    aliases: dict[str, list[str]]


class PropertyAliases:
    def __init__(self, path=None, *, definition=None):
        model = AliasDefinition.model_validate(
            read_mapping("property_aliases.yaml", path) if definition is None else definition
        )
        self._lookup = {}
        for canonical, aliases in model.aliases.items():
            if not canonical or "." in canonical or canonical.strip() != canonical:
                raise ValueError(f"Invalid canonical property: {canonical!r}")
            for name in [canonical, *aliases]:
                key = alias_key(name)
                if not key or (key in self._lookup and self._lookup[key] != canonical):
                    raise ValueError(f"Ambiguous or empty property alias: {name!r}")
                self._lookup[key] = canonical

    def resolve(self, name: str) -> str:
        if not isinstance(name, str) or not name.strip() or "." in name:
            raise ValueError(f"Invalid property name: {name!r}")
        return self._lookup.get(alias_key(name), name.strip())

    def as_payload(self) -> dict[str, str]:
        return dict(self._lookup)


class UnitDefinition(DomainModel):
    quantity: str = Field(min_length=1)
    canonical: str = Field(min_length=1)
    multiplier: float = Field(gt=0)
    label: str | None = Field(default=None, min_length=1)
    sources: list[str] = Field(default_factory=list)


class QuantityDefinition(DomainModel):
    label: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    dimension: dict[Literal["mass", "length", "time", "current", "temperature", "amount", "luminosity"], int]
    sources: list[str] = Field(default_factory=list)


class UnitCatalog(DomainModel):
    units: dict[str, UnitDefinition]
    property_quantities: dict[str, str]
    quantity_definitions: dict[str, QuantityDefinition] = Field(default_factory=dict)

    @model_validator(mode="after")
    def coherent(self):
        for name, unit in self.units.items():
            base = self.units.get(unit.canonical)
            if not name or base is None or base.quantity != unit.quantity:
                raise ValueError(f"Missing or incompatible canonical unit for {name}")
            if base.canonical != unit.canonical or base.multiplier != 1:
                raise ValueError(f"Canonical multiplier must be one: {name}")
        if set(self.property_quantities.values()) - {u.quantity for u in self.units.values()}:
            raise ValueError("Unknown property quantity")
        if self.quantity_definitions and {u.quantity for u in self.units.values()} - self.quantity_definitions.keys():
            raise ValueError("Unit quantity lacks a dimension definition")
        return self


class UnitService:
    def __init__(self, path=None, *, definition=None):
        self.catalog = UnitCatalog.model_validate(
            read_mapping("unit_mappings.yaml", path) if definition is None else definition
        )

    @staticmethod
    def _number(value):
        if type(value) not in (int, float):
            raise ValueError("Unit conversion requires a numeric value")
        if isinstance(value, float) and not isfinite(value):
            raise ValueError("Unit conversion requires a finite value")

    def normalize(self, prop, value, unit, *, property_name=None):
        prop = PropertyDefinition.model_validate(prop) if isinstance(prop, dict) else prop
        if prop.canonical_unit is None:
            if unit is not None:
                raise ValueError(f"Unit {unit} is not allowed for a unitless property")
            return value, None
        if unit not in prop.units:
            raise ValueError(f"Unsupported unit {unit}; expected one of {prop.units}")
        self._number(value)
        source = self.catalog.units.get(unit)
        target = self.catalog.units.get(prop.canonical_unit)
        expected = self.catalog.property_quantities.get(property_name)
        if source and target:
            dimensions = self.catalog.quantity_definitions
            if dimensions and dimensions[source.quantity].dimension != dimensions[target.quantity].dimension:
                raise ValueError("Incompatible SI dimensions")
            if source.quantity != target.quantity or (expected and source.quantity != expected):
                raise ValueError("Incompatible quantity or dimension")
        elif unit != prop.canonical_unit:
            raise ValueError(f"No conversion from {unit} to {prop.canonical_unit}")
        if unit == prop.canonical_unit:
            return value, unit
        try:
            converted = value * (source.multiplier / target.multiplier)
        except OverflowError as exc:
            raise ValueError("Unit conversion overflow") from exc
        if not isfinite(converted):
            raise ValueError("Unit conversion overflow")
        return converted, prop.canonical_unit

    def equal(self, name: str, left: ProductAttribute, right: ProductAttribute, prop=None) -> bool:
        a, b = left.value, right.value
        if a is None or b is None:
            return a is None and b is None and left.unit == right.unit
        if type(a) not in (int, float) or type(b) not in (int, float):
            return type(a) is type(b) and a == b and left.unit == right.unit
        self._number(a)
        self._number(b)
        if left.unit != right.unit:
            if prop is None:
                quantity = self.catalog.property_quantities.get(name)
                units = [k for k, u in self.catalog.units.items() if u.quantity == quantity]
                if not units:
                    return False
                prop = PropertyDefinition(type="number", canonical_unit=self.catalog.units[units[0]].canonical, units=units)
            try:
                a, _ = self.normalize(prop, a, left.unit, property_name=name)
                b, _ = self.normalize(prop, b, right.unit, property_name=name)
            except ValueError:
                return False
        try:
            return isclose(a, b, rel_tol=1e-9, abs_tol=0.0)
        except OverflowError:
            return a == b
