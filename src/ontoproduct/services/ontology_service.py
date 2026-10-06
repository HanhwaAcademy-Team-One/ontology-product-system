from pathlib import Path

import yaml

from ontoproduct.schemas.ontology import OntologyDefinition, PropertyDefinition
from ontoproduct.services.mapping_service import UnitService
from ontoproduct.services.product_ontology_service import ProductOntology


class OntologyService:
    def __init__(self, path: str | Path | None = None, *, definition: dict | None = None,
                 unit_service: UnitService | None = None, semantic_model: ProductOntology | None = None):
        use_default = path is None and definition is None
        if definition is None:
            path = Path(path) if path else Path(__file__).parents[1] / "ontology" / "ontology.yaml"
            definition = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.definition = OntologyDefinition.model_validate(definition)
        self.unit_service = (unit_service if unit_service is not None
                             else semantic_model.units if semantic_model is not None else UnitService())
        self.semantic_model = semantic_model
        if use_default and self.semantic_model is None:
            self.semantic_model = ProductOntology(units=self.unit_service)
        if self.semantic_model is not None:
            if self.semantic_model.units.catalog != self.unit_service.catalog:
                raise ValueError("Operational and semantic ontology must share the same unit catalog")
            projected = self.semantic_model.operational_definition()
            if projected != self.definition:
                raise ValueError("ontology.yaml differs from the product semantic model projection")
            self.definition = projected

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

    def _rdf_service(self):
        if self.semantic_model is None:
            raise ValueError("RDF operations require an explicitly aligned product semantic model")
        from ontoproduct.services.rdf_ontology_service import RdfOntologyService

        return RdfOntologyService(self.semantic_model)

    def to_rdf(self, product, *, record_id, item_id=None, manufacturer_is_organization=False):
        return self._rdf_service().product_graph(
            product, record_id=record_id, item_id=item_id,
            manufacturer_is_organization=manufacturer_is_organization,
        )

    def validate_semantics(self, product, *, record_id="validation"):
        return self._rdf_service().validate_product(product, record_id=record_id)
