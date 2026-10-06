"""Executable application model aligned to verified external vocabularies."""

import re

from ontoproduct.schemas.ontology import OntologyDefinition
from ontoproduct.schemas.semantic_ontology import ProductSemanticDefinition
from ontoproduct.services.agent_errors import OntologyClassificationError
from ontoproduct.services.external_mapping_service import ExternalMappings
from ontoproduct.services.mapping_service import UnitService, read_mapping


class ProductOntology:
    def __init__(self, path=None, *, definition=None, units=None, references=None):
        self.model = ProductSemanticDefinition.model_validate(
            read_mapping("product_model.yaml", path) if definition is None else definition
        )
        self.units = units if units is not None else UnitService()
        self.references = references if references is not None else ExternalMappings()
        self._validate()

    def reference_uri(self, key):
        reference = self.references.catalog.mappings.get(key)
        if reference is None or reference.status != "verified" or reference.uri is None:
            raise ValueError(f"Semantic model requires a verified external reference: {key}")
        return str(reference.uri)

    def operational_definition(self):
        return OntologyDefinition.model_validate({"classes": {
            key: {"parent": profile.parent,
                  "required_properties": {p: self.model.properties[p].definition.model_dump() for p in profile.required},
                  "optional_properties": {p: self.model.properties[p].definition.model_dump() for p in profile.optional}}
            for key, profile in self.model.classes.items()
        }})

    def _validate(self):
        model = self.model
        if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", k) for k in model.classes):
            raise ValueError("Application profile names must be safe local names")
        identifiers = [*model.entity_classes, *model.relations]
        identifiers.extend(p.model_class for p in model.classes.values())
        identifiers.extend(p.item_class for p in model.classes.values())
        identifiers.extend(p.predicate for p in model.properties.values() if p.kind == "quantity")
        if len(identifiers) != len(set(identifiers)) or any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", k) for k in identifiers):
            raise ValueError("Semantic identifiers must be unique safe local names")
        entity_names = set(model.entity_classes)
        if not {"ProductModel", "ManufacturedItem", "Manufacturer", "ManufacturerOrganization"} <= entity_names:
            raise ValueError("Missing core semantic entity classes")
        all_classes = entity_names | {p.model_class for p in model.classes.values()} | {p.item_class for p in model.classes.values()}
        for key, entity in model.entity_classes.items():
            seen, current = set(), key
            while current is not None:
                if current in seen or current not in entity_names:
                    raise ValueError("Unknown or cyclic entity class parent")
                seen.add(current)
                current = model.entity_classes[current].parent
            for ref in entity.external_parents:
                self.reference_uri(ref)
        for relation in model.relations.values():
            if relation.domain not in entity_names or relation.range not in entity_names:
                raise ValueError("Unknown relation domain or range")
            self.reference_uri(relation.external_parent)
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
                quantity = self.units.catalog.quantity_definitions.get(prop.quantity)
                if quantity is None or self.units.catalog.property_quantities.get(name) != prop.quantity:
                    raise ValueError(f"Missing or inconsistent property quantity: {name}")
                self.reference_uri(quantity.reference)
                for unit in prop.definition.units:
                    entry = self.units.catalog.units.get(unit)
                    if entry is None or entry.quantity != prop.quantity:
                        raise ValueError(f"Wrong unit dimension for property: {name}")
                    self.reference_uri(unit)
        for ref in ("quantity_value", "quantity_unit", "numeric_value", "quantity_kind"):
            self.reference_uri(ref)
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
        return {"namespace": self.model.namespace, "version": self.model.version,
                "record_kind": "product_model", "entities": {k: v.model_dump(mode="json") for k, v in self.model.entity_classes.items()},
                "relations": {k: {**v.model_dump(mode="json"), "external_uri": self.reference_uri(v.external_parent)} for k, v in self.model.relations.items()},
                "classes": {k: v.model_dump(mode="json") for k, v in self.model.classes.items() if k in allowed},
                "properties": {k: v.model_dump(mode="json") for k, v in self.model.properties.items()},
                "quantity_kinds": {k: {"uri": self.reference_uri(v.reference), "dimension": dict(v.dimension)}
                                   for k, v in self.units.catalog.quantity_definitions.items()},
                "classification_rules": [r.model_dump(mode="json") for r in self.model.classification_rules],
                "comparisons": [c.model_dump(mode="json") for c in self.model.comparisons]}
