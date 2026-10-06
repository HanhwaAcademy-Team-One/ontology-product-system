from pathlib import Path

import yaml

from ontoproduct.schemas.ontology import OntologyDefinition, PropertyDefinition
from ontoproduct.services.mapping_service import UnitService


class OntologyService:
    def __init__(self, path: str | Path | None = None, *, definition: dict | None = None,
                 unit_service: UnitService | None = None):
        if definition is None:
            path = Path(path) if path else Path(__file__).parents[1] / "ontology" / "ontology.yaml"
            definition = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.definition = OntologyDefinition.model_validate(definition)
        self.unit_service = unit_service if unit_service is not None else UnitService()

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
        return self.unit_service.normalize(property, value, unit)
