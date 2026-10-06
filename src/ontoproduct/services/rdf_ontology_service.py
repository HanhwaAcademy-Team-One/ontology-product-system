"""RDF/OWL product modeling and offline SHACL validation.

The workflow JSON remains a model specification. Physical items and identified
organizations are added only when explicitly supplied by the caller. Every business
concept, quantity kind and unit is a local IRI; only standard RDF/RDFS/OWL/XSD/SHACL
and Dublin Core terms come from outside the project namespace.
"""

import json
from pathlib import Path
from urllib.parse import quote

from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SH, XSD

from ontoproduct.schemas.product import NormalizedProduct
from ontoproduct.services.evidence_service import evidence_candidates, is_conflict
from ontoproduct.services.product_ontology_service import ProductOntology


class RdfOntologyService:
    def __init__(self, model=None):
        self.model = model if model is not None else ProductOntology()
        namespace = self.model.model.namespace
        self.op = Namespace(namespace)
        self.qk = Namespace(namespace + "quantitykind/")
        self.unit = Namespace(namespace + "unit/")
        self.src = Namespace(namespace + "source/")
        terms = self.model.model.measurement
        self.quantity_value = self.op[terms.quantity_value.name]
        self.quantity_kind_class = self.op[terms.quantity_kind.name]
        self.unit_class = self.op[terms.unit.name]
        self.numeric_value = self.op[terms.numeric_value.name]
        self.has_unit = self.op[terms.has_unit.name]
        self.has_quantity_kind = self.op[terms.has_quantity_kind.name]

    def unit_uri(self, symbol):
        return URIRef(self.unit + quote(symbol, safe=""))

    def quantity_uri(self, key):
        return URIRef(self.qk + quote(key, safe=""))

    def source_uri(self, key):
        return URIRef(self.src + quote(key, safe=""))

    def entity_types(self, name):
        return [self.op[name], *(self.op[a] for a in self.model.entity_ancestors(name))]

    def _graph(self):
        graph = Graph()
        for prefix, uri in {"op": self.op, "opqk": self.qk, "opunit": self.unit, "opsrc": self.src,
                            "sh": SH, "owl": OWL, "dcterms": DCTERMS}.items():
            graph.bind(prefix, uri)
        return graph

    def _describe(self, graph, node, label, description, sources):
        graph.add((node, RDFS.label, Literal(label)))
        if description:
            graph.add((node, RDFS.comment, Literal(description)))
        for key in sources:
            graph.add((node, DCTERMS.source, self.source_uri(key)))

    @staticmethod
    def _list(graph, values):
        head = BNode()
        Collection(graph, head, values)
        return head

    def _ancestors(self, code):
        profiles = self.model.model.classes
        if code not in profiles:
            raise ValueError(f"Unknown product semantic class: {code}")
        result = []
        while code is not None:
            result.append(code)
            code = profiles[code].parent
        return result

    def _properties(self, code):
        required, optional = {}, {}
        for current in reversed(self._ancestors(code)):
            profile = self.model.model.classes[current]
            for key in profile.required:
                optional.pop(key, None)
                required[key] = self.model.model.properties[key]
            for key in profile.optional:
                required.pop(key, None)
                optional[key] = self.model.model.properties[key]
        return required, optional

    def ontology_graph(self):
        graph, op, model = self._graph(), self.op, self.model.model
        graph.add((URIRef(model.namespace), RDF.type, OWL.Ontology))
        graph.add((URIRef(model.namespace), OWL.versionInfo, Literal(model.version)))
        graph.add((URIRef(model.namespace), RDFS.label, Literal("OntoProduct manufacturing product ontology")))
        # Provenance uses local source records; original URLs stay in documentation.
        graph.add((op.SourceRecord, RDF.type, OWL.Class))
        graph.add((op.SourceRecord, RDFS.label, Literal("Design source record")))
        graph.add((op.SourceRecord, RDFS.comment, Literal("Local record of an outside work used as a design reference.")))
        for key, source in model.sources.items():
            node = self.source_uri(key)
            graph.add((URIRef(model.namespace), DCTERMS.source, node))
            graph.add((node, RDF.type, op.SourceRecord))
            graph.add((node, DCTERMS.title, Literal(source.title)))
            graph.add((node, OWL.versionInfo, Literal(source.version)))
            graph.add((node, DCTERMS.license, Literal(source.license)))
            graph.add((node, DCTERMS.creator, Literal(source.attribution)))
            graph.add((node, RDFS.comment, Literal(source.usage)))
        for name, entity in model.entity_classes.items():
            cls = op[name]
            graph.add((cls, RDF.type, OWL.Class))
            self._describe(graph, cls, entity.label, entity.description, entity.sources)
            for parent in entity.parents:
                graph.add((cls, RDFS.subClassOf, op[parent]))
        graph.add((op.ProductModel, OWL.disjointWith, op.ManufacturedItem))
        for code, profile in model.classes.items():
            for category, root in (("model_class", "ProductModel"), ("item_class", "ManufacturedItem")):
                cls = op[getattr(profile, category)]
                parent = op[getattr(model.classes[profile.parent], category)] if profile.parent else op[root]
                graph.add((cls, RDF.type, OWL.Class))
                graph.add((cls, RDFS.subClassOf, parent))
                graph.add((cls, RDFS.label, Literal(profile.label if category == "model_class" else f"{code} physical item")))
                description = profile.description if category == "model_class" else f"Physical item of the {code} category; its model specification is represented separately."
                graph.add((cls, RDFS.comment, Literal(description)))
                graph.add((cls, op.applicationClass, Literal(code)))
        for name, relation in model.relations.items():
            predicate = op[name]
            graph.add((predicate, RDF.type, OWL.ObjectProperty))
            graph.add((predicate, RDFS.label, Literal(relation.label)))
            graph.add((predicate, RDFS.comment, Literal(relation.description)))
            graph.add((predicate, RDFS.domain, op[relation.domain]))
            graph.add((predicate, RDFS.range, op[relation.range]))
            for key in relation.sources:
                graph.add((predicate, DCTERMS.source, self.source_uri(key)))
        self._measurement_vocabulary(graph)
        for name, prop in model.properties.items():
            predicate = op[prop.predicate]
            graph.add((predicate, op.applicationField, Literal(name)))
            if prop.kind == "entity":
                continue
            graph.add((predicate, RDF.type, OWL.ObjectProperty))
            graph.add((predicate, RDFS.label, Literal(prop.label)))
            graph.add((predicate, RDFS.comment, Literal(prop.description)))
            graph.add((predicate, RDFS.domain, op[prop.domain]))
            graph.add((predicate, RDFS.range, self.quantity_value))
            graph.add((predicate, op.quantityKind, self.quantity_uri(prop.quantity)))
            graph.add((predicate, op.canonicalUnit, self.unit_uri(prop.definition.canonical_unit)))
            # Type restrictions express meanings; requiredness stays in SHACL.
            restriction = BNode()
            graph.add((op[prop.domain], RDFS.subClassOf, restriction))
            graph.add((restriction, RDF.type, OWL.Restriction))
            graph.add((restriction, OWL.onProperty, predicate))
            graph.add((restriction, OWL.allValuesFrom, self.quantity_value))
        return graph

    def _measurement_vocabulary(self, graph):
        """Local quantity-value structure, quantity kinds and units."""
        op, terms, catalog = self.op, self.model.model.measurement, self.model.units.catalog
        for cls, term in ((self.quantity_value, terms.quantity_value), (self.quantity_kind_class, terms.quantity_kind),
                          (self.unit_class, terms.unit)):
            graph.add((cls, RDF.type, OWL.Class))
            self._describe(graph, cls, term.label, term.description, terms.sources)
        graph.add((self.numeric_value, RDF.type, OWL.DatatypeProperty))
        graph.add((self.numeric_value, RDFS.domain, self.quantity_value))
        self._describe(graph, self.numeric_value, terms.numeric_value.label, terms.numeric_value.description, terms.sources)
        for predicate, term, target in ((self.has_unit, terms.has_unit, self.unit_class),
                                        (self.has_quantity_kind, terms.has_quantity_kind, self.quantity_kind_class)):
            graph.add((predicate, RDF.type, OWL.ObjectProperty))
            graph.add((predicate, RDFS.domain, self.quantity_value))
            graph.add((predicate, RDFS.range, target))
            self._describe(graph, predicate, term.label, term.description, terms.sources)
        # Unit metadata is descriptive; conversion is performed by the shared UnitService.
        for name, kind, range_ in (("measuresQuantityKind", OWL.ObjectProperty, self.quantity_kind_class),
                                   ("conversionTargetUnit", OWL.ObjectProperty, self.unit_class),
                                   ("conversionMultiplier", OWL.DatatypeProperty, XSD.double),
                                   ("symbol", OWL.DatatypeProperty, XSD.string)):
            graph.add((op[name], RDF.type, kind))
            graph.add((op[name], RDFS.domain, self.unit_class))
            graph.add((op[name], RDFS.range, range_))
        for key in sorted(self.model.used_quantities()):
            quantity, node = catalog.quantity_definitions[key], self.quantity_uri(key)
            graph.add((node, RDF.type, self.quantity_kind_class))
            self._describe(graph, node, quantity.label, quantity.description, quantity.sources)
            graph.add((node, op.siDimensions, Literal(json.dumps(quantity.dimension, sort_keys=True))))
        for symbol in sorted(self.model.used_units()):
            unit, node = catalog.units[symbol], self.unit_uri(symbol)
            graph.add((node, RDF.type, self.unit_class))
            self._describe(graph, node, unit.label, None, unit.sources)
            graph.add((node, op.symbol, Literal(symbol)))
            graph.add((node, op.measuresQuantityKind, self.quantity_uri(unit.quantity)))
            graph.add((node, op.conversionTargetUnit, self.unit_uri(unit.canonical)))
            graph.add((node, op.conversionMultiplier, Literal(float(unit.multiplier), datatype=XSD.double)))

    def _property_shape(self, graph, parent, path, *, required=False):
        shape = BNode()
        graph.add((parent, SH.property, shape))
        graph.add((shape, SH.path, path))
        graph.add((shape, SH.maxCount, Literal(1)))
        if required:
            graph.add((shape, SH.minCount, Literal(1)))
        return shape

    def shapes_graph(self):
        graph, op, model = self._graph(), self.op, self.model.model
        manufacturer_shape = op.ManufacturerShape
        graph.add((manufacturer_shape, RDF.type, SH.NodeShape))
        graph.add((manufacturer_shape, SH.targetClass, op.Manufacturer))
        name_shape = self._property_shape(graph, manufacturer_shape, RDFS.label, required=True)
        graph.add((name_shape, SH.datatype, XSD.string))
        graph.add((name_shape, SH.pattern, Literal(r"\S")))
        # Catalog models and physical items cannot be the same RDF individual.
        root = op.ProductModelShape
        graph.add((root, RDF.type, SH.NodeShape))
        graph.add((root, SH.targetClass, op.ProductModel))
        not_item = BNode()
        graph.add((root, SH["not"], not_item))
        graph.add((not_item, SH["class"], op.ManufacturedItem))
        for code, profile in model.classes.items():
            shape = op[f"{code}Shape"]
            graph.add((shape, RDF.type, SH.NodeShape))
            graph.add((shape, SH.targetClass, op[profile.model_class]))
            required, optional = self._properties(code)
            for key, prop in {**required, **optional}.items():
                field_shape = self._property_shape(graph, shape, op[prop.predicate], required=key in required)
                graph.add((field_shape, SH.name, Literal(key)))
                graph.add((field_shape, SH.nodeKind, SH.BlankNodeOrIRI))
                if prop.kind == "entity":
                    graph.add((field_shape, SH["class"], op[model.relations[prop.predicate].range]))
                    graph.add((field_shape, SH.node, manufacturer_shape))
                    continue
                graph.add((field_shape, SH["class"], self.quantity_value))
                quantity_shape = BNode()
                graph.add((field_shape, SH.node, quantity_shape))
                graph.add((quantity_shape, RDF.type, SH.NodeShape))
                value_shape = self._property_shape(graph, quantity_shape, self.numeric_value, required=True)
                datatypes = (XSD.integer,) if prop.definition.type == "integer" else (XSD.integer, XSD.decimal, XSD.double, XSD.float)
                choices = []
                for datatype in datatypes:
                    alternative = BNode()
                    graph.add((alternative, SH.datatype, datatype))
                    choices.append(alternative)
                graph.add((value_shape, SH["or"], self._list(graph, choices)))
                graph.add((value_shape, SH.pattern, Literal(r"^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$")))
                if prop.definition.minimum is not None:
                    graph.add((value_shape, SH.minInclusive, Literal(prop.definition.minimum)))
                if prop.definition.maximum is not None:
                    graph.add((value_shape, SH.maxInclusive, Literal(prop.definition.maximum)))
                unit_shape = self._property_shape(graph, quantity_shape, self.has_unit, required=True)
                graph.add((unit_shape, SH.hasValue, self.unit_uri(prop.definition.canonical_unit)))
                kind_shape = self._property_shape(graph, quantity_shape, self.has_quantity_kind, required=True)
                graph.add((kind_shape, SH.hasValue, self.quantity_uri(prop.quantity)))
        for comparison in model.comparisons:
            shape = op[f"{comparison.product_class}Shape"]
            constraint = BNode()
            left = op[model.properties[comparison.left].predicate]
            right = op[model.properties[comparison.right].predicate]
            numeric = self.numeric_value
            graph.add((shape, SH.sparql, constraint))
            graph.add((constraint, SH.message, Literal(f"{comparison.left} must be less than {comparison.right}")))
            graph.add((constraint, SH.select, Literal(
                f"SELECT $this WHERE {{ $this <{left}>/<{numeric}> ?left ; <{right}>/<{numeric}> ?right . FILTER (?left >= ?right) }}"
            )))
        item_shape = op.ManufacturedItemShape
        graph.add((item_shape, RDF.type, SH.NodeShape))
        graph.add((item_shape, SH.targetClass, op.ManufacturedItem))
        model_shape = self._property_shape(graph, item_shape, op.hasMakeAndModel, required=True)
        graph.add((model_shape, SH["class"], op.ProductModel))
        return graph

    @staticmethod
    def record_uri(record_id):
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("record_id must be a nonempty explicit identifier")
        return URIRef("urn:ontoproduct:record:" + quote(record_id, safe=""))

    def _evidence(self, graph, product_node, key, attr):
        op = self.op
        evidence = URIRef(f"{product_node}:attribute:{quote(key, safe='')}")
        graph.add((product_node, op.attributeEvidence, evidence))
        graph.add((evidence, op.applicationField, Literal(key)))
        graph.add((evidence, op.recordJSON, Literal(json.dumps(attr.model_dump(mode="json"), ensure_ascii=False, allow_nan=False))))
        graph.add((evidence, op.hasConflict, Literal(is_conflict(attr))))
        for candidate in evidence_candidates(attr):
            node = BNode()
            graph.add((evidence, op.candidateEvidence, node))
            for field in ("value", "unit", "evidence", "source_file", "page", "confidence", "provenance"):
                value = getattr(candidate, field)
                if value is not None:
                    graph.add((node, op[field], Literal(value)))
        return evidence

    def product_graph(self, product, *, record_id, item_id=None, manufacturer_is_organization=False):
        if type(manufacturer_is_organization) is not bool:
            raise ValueError("Organization status must be explicitly supplied as a boolean")
        product = NormalizedProduct.model_validate(product)
        codes = self._ancestors(product.product_class)
        graph, op, node = self._graph(), self.op, self.record_uri(record_id)
        model = self.model.model
        for code in codes:
            graph.add((node, RDF.type, op[model.classes[code].model_class]))
        for cls in self.entity_types("ProductModel"):
            graph.add((node, RDF.type, cls))
        if product.product_name is not None:
            graph.add((node, RDFS.label, Literal(product.product_name)))
        required, optional = self._properties(product.product_class)
        supported = {**required, **optional}
        for key, attr in product.attributes.items():
            evidence = self._evidence(graph, node, key, attr)
            if key not in supported or attr.value is None:
                continue  # Preserve the complete record without inventing a value.
            prop = supported[key]
            target = URIRef(f"{node}:value:{quote(key, safe='')}")
            graph.add((node, op[prop.predicate], target))
            graph.add((target, op.attributeEvidence, evidence))
            if prop.kind == "entity":
                entity = "ManufacturerOrganization" if manufacturer_is_organization else model.relations[prop.predicate].range
                for cls in self.entity_types(entity):
                    graph.add((target, RDF.type, cls))
                graph.add((target, RDFS.label, Literal(attr.value)))
            else:
                value, unit = attr.value, attr.unit
                try:
                    value, unit = self.model.units.normalize(prop.definition, value, unit, property_name=key)
                except ValueError:
                    pass  # Invalid types/units survive and fail validation.
                graph.add((target, RDF.type, self.quantity_value))
                graph.add((target, self.numeric_value, Literal(value)))
                if unit is not None:
                    # Unknown units stay literal so SHACL reports them instead of guessing an IRI.
                    unit_node = self.unit_uri(unit) if unit in self.model.units.catalog.units else Literal(unit)
                    graph.add((target, self.has_unit, unit_node))
                graph.add((target, self.has_quantity_kind, self.quantity_uri(prop.quantity)))
        if item_id is not None:
            if not isinstance(item_id, str) or not item_id.strip():
                raise ValueError("item_id must be a nonempty explicit identifier")
            item = URIRef("urn:ontoproduct:item:" + quote(item_id, safe=""))
            for code in codes:
                graph.add((item, RDF.type, op[model.classes[code].item_class]))
            for cls in self.entity_types("ManufacturedItem"):
                graph.add((item, RDF.type, cls))
            graph.add((item, op.hasMakeAndModel, node))
        return graph

    def validate_graph(self, graph):
        if not isinstance(graph, Graph):
            raise TypeError("Pass an in-memory RDF graph; remote graph loading is not supported")
        conforms, report, report_text = validate(
            graph, shacl_graph=self.shapes_graph(), ont_graph=self.ontology_graph(),
            inference="rdfs", inplace=False, do_owl_imports=False, advanced=False,
        )
        issues = []
        for result in report.subjects(RDF.type, SH.ValidationResult):
            issues.append({"focus_node": str(report.value(result, SH.focusNode)),
                           "path": str(report.value(result, SH.resultPath) or ""),
                           "message": str(report.value(result, SH.resultMessage) or ""),
                           "constraint": str(report.value(result, SH.sourceConstraintComponent) or "")})
        return {"valid": bool(conforms), "issues": issues, "report": report_text}

    def validate_product(self, product, *, record_id="validation"):
        return self.validate_graph(self.product_graph(product, record_id=record_id))

    def write_artifacts(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        for filename, graph in (("product_ontology.ttl", self.ontology_graph()), ("product_shapes.ttl", self.shapes_graph())):
            graph.serialize(destination=str(directory / filename), format="turtle", encoding="utf-8")
