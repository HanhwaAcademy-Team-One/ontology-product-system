from pathlib import Path
from math import isfinite

import yaml

from ontoproduct.schemas.ontology import OntologyDefinition, PropertyDefinition


class OntologyService:
    def __init__(self, path: str | Path | None = None, *, definition: dict | None = None):
        if definition is None:
            path = Path(path) if path else Path(__file__).parents[1] / "ontology" / "ontology.yaml"
            definition = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.definition = OntologyDefinition.model_validate(definition)

    def get_class(self, name: str):
        if name not in self.definition.classes:
            raise ValueError(f"Unknown product class: {name}")
        return self.definition.classes[name].model_copy(deep=True)

    def get_parent(self, name: str) -> str | None:
        return self.get_class(name).parent

    def get_ancestors(self, name: str) -> list[str]:
        ancestors = []
        parent = self.get_parent(name)
        while parent is not None:
            ancestors.append(parent)
            parent = self.get_parent(parent)
        return ancestors

    def _resolve(self, name: str):
        required, optional = {}, {}
        for current in [*reversed(self.get_ancestors(name)), name]:
            cls = self.get_class(current)
            for key, prop in cls.required_properties.items():
                optional.pop(key, None)
                required[key] = prop
            for key, prop in cls.optional_properties.items():
                required.pop(key, None)
                optional[key] = prop
        return required, optional

    def resolve_required_properties(self, name: str) -> dict[str, PropertyDefinition]:
        return self._resolve(name)[0]

    def resolve_optional_properties(self, name: str) -> dict[str, PropertyDefinition]:
        return self._resolve(name)[1]

    def resolve_properties(self, name: str) -> dict[str, PropertyDefinition]:
        required, optional = self._resolve(name)
        return {**required, **optional}

    def normalize_unit(self, property: PropertyDefinition | dict, value, unit: str | None):
        prop = PropertyDefinition.model_validate(property) if isinstance(property, dict) else property
        if prop.canonical_unit is None:
            if unit is not None:
                raise ValueError(f"Unit {unit} is not allowed for a unitless property")
            return value, None
        if unit not in prop.units:
            raise ValueError(f"Unsupported unit {unit}; expected one of {prop.units}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Unit conversion requires a numeric value")
        if isinstance(value, float) and not isfinite(value):
            raise ValueError("Unit conversion requires a finite value")
        if unit == prop.canonical_unit:
            return value, unit
        factors = {("kW", "W"): 1000, ("g", "kg"): 0.001,
                   ("W", "kW"): 0.001, ("kg", "g"): 1000}
        factor = factors.get((unit, prop.canonical_unit))
        if factor is None:
            raise ValueError(f"No conversion from {unit} to {prop.canonical_unit}")
        try:
            converted = value * factor
        except OverflowError as exc:
            raise ValueError("Unit conversion overflow") from exc
        if isinstance(converted, float) and not isfinite(converted):
            raise ValueError("Unit conversion overflow")
        return converted, prop.canonical_unit
