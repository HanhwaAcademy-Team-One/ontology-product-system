"""Executable application model defined entirely by local project vocabulary."""

import re

from ontoproduct.schemas.ontology import OntologyDefinition
from ontoproduct.schemas.semantic_ontology import ProductSemanticDefinition
from ontoproduct.services.agent_errors import OntologyClassificationError
from ontoproduct.services.mapping_service import UnitService, read_mapping

LOCAL_NAME = r"[A-Za-z][A-Za-z0-9_]*"
CORE_ENTITIES = {"ProductModel", "ManufacturedItem", "Manufacturer", "ManufacturerOrganization"}


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


class ProductOntology:
    def __init__(self, path=None, *, definition=None, units=None):
        self.model = ProductSemanticDefinition.model_validate(
            read_mapping("product_model.yaml", path) if definition is None else definition
        )
        self.units = units if units is not None else UnitService()
        self._validate()

    def operational_definition(self):
        return OntologyDefinition.model_validate({"classes": {
            key: {"parent": profile.parent,
                  "required_properties": {p: self.model.properties[p].definition.model_dump() for p in profile.required},
                  "optional_properties": {p: self.model.properties[p].definition.model_dump() for p in profile.optional}}
            for key, profile in self.model.classes.items()
        }})

    def entity_ancestors(self, name):
        """All transitive entity superclasses of name, excluding name itself."""
        result, pending = [], list(self.model.entity_classes[name].parents)
        while pending:
            current = pending.pop(0)
            if current not in result:
                result.append(current)
                pending.extend(self.model.entity_classes[current].parents)
        return result

    def used_units(self):
        return {unit for prop in self.model.properties.values() if prop.kind == "quantity" for unit in prop.definition.units}

    def used_quantities(self):
        return {prop.quantity for prop in self.model.properties.values() if prop.kind == "quantity"}

    def _check_sources(self, owner, sources):
        if len(sources) != len(set(sources)) or set(sources) - self.model.sources.keys():
            raise ValueError(f"Unknown or duplicate source id for {owner}")

    def _validate(self):
        model, catalog = self.model, self.units.catalog
        # Operational data is local only: original URLs belong in documentation.
        for text in [*_strings(model.model_dump(mode="json")), *_strings(catalog.model_dump(mode="json"))]:
            if "://" in text:
                raise ValueError(f"Operational ontology data must not contain external URLs: {text!r}")
        if any(not re.fullmatch(LOCAL_NAME, k) for k in model.classes):
            raise ValueError("Application profile names must be safe local names")
        identifiers = [*model.entity_classes, *model.relations, *(t.name for t in model.measurement.terms().values())]
        identifiers.extend(p.model_class for p in model.classes.values())
        identifiers.extend(p.item_class for p in model.classes.values())
        identifiers.extend(p.predicate for p in model.properties.values() if p.kind == "quantity")
        if len(identifiers) != len(set(identifiers)) or any(not re.fullmatch(LOCAL_NAME, k) for k in identifiers):
            raise ValueError("Semantic identifiers must be unique safe local names")
        self._check_sources("measurement", model.measurement.sources)
        entity_names = set(model.entity_classes)
        if not CORE_ENTITIES <= entity_names:
            raise ValueError("Missing core semantic entity classes")
        all_classes = entity_names | {p.model_class for p in model.classes.values()} | {p.item_class for p in model.classes.values()}
        for key, entity in model.entity_classes.items():
            self._check_sources(key, entity.sources)
            if len(entity.parents) != len(set(entity.parents)) or set(entity.parents) - entity_names:
                raise ValueError("Unknown or duplicate entity class parent")
            # Multiple inheritance forms a DAG; reject any path that returns to the start.
            if key in self.entity_ancestors(key):
                raise ValueError("Cyclic entity class parent")
        for key, relation in model.relations.items():
            self._check_sources(key, relation.sources)
            if relation.domain not in entity_names or relation.range not in entity_names:
                raise ValueError("Unknown relation domain or range")
        for profile in model.classes.values():
            if len(profile.required) != len(set(profile.required)) or len(profile.optional) != len(set(profile.optional)):
                raise ValueError("Duplicate profile properties")
            if set(profile.required) & set(profile.optional):
                raise ValueError("A profile property cannot be both required and optional")
            if set(profile.required + profile.optional) - model.properties.keys():
                raise ValueError("Unknown profile property")
        definition = self.operational_definition()  # also checks profile parent cycles
        for name, prop in model.properties.items():
            if prop.domain not in all_classes:
                raise ValueError(f"Unknown property domain: {name}")
            if prop.kind == "entity":
                if prop.predicate not in model.relations or model.relations[prop.predicate].range != "Manufacturer":
                    raise ValueError(f"Unknown entity relationship: {name}")
            else:
                quantity = catalog.quantity_definitions.get(prop.quantity)
                if quantity is None or catalog.property_quantities.get(name) != prop.quantity:
                    raise ValueError(f"Missing or inconsistent property quantity: {name}")
                for unit in prop.definition.units:
                    entry = catalog.units.get(unit)
                    if entry is None or entry.quantity != prop.quantity:
                        raise ValueError(f"Wrong unit dimension for property: {name}")
        for key in self.used_quantities():
            quantity = catalog.quantity_definitions[key]
            if not quantity.label or not quantity.description:
                raise ValueError(f"Quantity kind needs a local label and description: {key}")
            self._check_sources(f"quantity {key}", quantity.sources)
        for key in self.used_units():
            unit = catalog.units[key]
            if not unit.label:
                raise ValueError(f"Unit needs a local label: {key}")
            self._check_sources(f"unit {key}", unit.sources)
        for rule in model.classification_rules:
            if rule.product_class not in model.classes or set(rule.all_of + rule.any_of + rule.none_of) - model.properties.keys():
                raise ValueError("Unknown classification rule class or property")
            for refined in rule.candidate_refinements.values():
                current = refined
                while current is not None and current != rule.product_class:
                    if current not in model.classes:
                        raise ValueError("Unknown classification refinement")
                    current = model.classes[current].parent
                if current != rule.product_class:
                    raise ValueError("Classification refinement must be a descendant")
        for comparison in model.comparisons:
            if comparison.product_class not in definition.classes:
                raise ValueError("Unknown comparison class")
            left, right = model.properties.get(comparison.left), model.properties.get(comparison.right)
            if left is None or right is None or left.kind != "quantity" or left.quantity != right.quantity:
                raise ValueError("Comparison requires compatible quantities")
            supported, current = set(), comparison.product_class
            while current is not None:
                profile = model.classes[current]
                supported.update(profile.required + profile.optional)
                current = profile.parent
            if not {comparison.left, comparison.right} <= supported:
                raise ValueError("Comparison properties must belong to the selected profile")
            if left.definition.canonical_unit != right.definition.canonical_unit:
                raise ValueError("Comparison properties require the same canonical unit")

    def classify(self, candidate, present):
        selected = set()
        for rule in self.model.classification_rules:
            if (set(rule.all_of) <= present and not (set(rule.none_of) & present)
                    and len(set(rule.any_of) & present) >= rule.minimum_matches):
                selected.add(rule.candidate_refinements.get(candidate, rule.product_class))
        if len(selected) != 1:
            raise OntologyClassificationError("No unambiguous product ontology classification; supply a supported manual class or LLM adapter")
        return selected.pop()

    def as_context(self, allowed_classes=None):
        allowed = set(self.model.classes if allowed_classes is None else allowed_classes)
        catalog = self.units.catalog
        return {"namespace": self.model.namespace, "version": self.model.version,
                "record_kind": "product_model",
                "entities": {k: v.model_dump(mode="json") for k, v in self.model.entity_classes.items()},
                "relations": {k: v.model_dump(mode="json") for k, v in self.model.relations.items()},
                "measurement": self.model.measurement.model_dump(mode="json"),
                "classes": {k: v.model_dump(mode="json") for k, v in self.model.classes.items() if k in allowed},
                "properties": {k: v.model_dump(mode="json") for k, v in self.model.properties.items()},
                "quantity_kinds": {k: {"label": catalog.quantity_definitions[k].label,
                                       "description": catalog.quantity_definitions[k].description,
                                       "dimension": dict(catalog.quantity_definitions[k].dimension)}
                                   for k in sorted(self.used_quantities())},
                "units": {k: {"label": catalog.units[k].label, "quantity": catalog.units[k].quantity,
                              "canonical": catalog.units[k].canonical, "multiplier": catalog.units[k].multiplier}
                          for k in sorted(self.used_units())},
                "sources": {k: {"title": v.title, "version": v.version, "license": v.license}
                            for k, v in self.model.sources.items()},
                "classification_rules": [r.model_dump(mode="json") for r in self.model.classification_rules],
                "comparisons": [c.model_dump(mode="json") for c in self.model.comparisons]}
