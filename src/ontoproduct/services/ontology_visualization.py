"""Read-only Mermaid projections of actual ontology and product RDF graphs."""

import hashlib
import html
import json

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from ontoproduct.schemas.product import ProductAttribute
from ontoproduct.services.mapping_service import DATA_DIR
from ontoproduct.services.rdf_ontology_service import RdfOntologyService


class OntologyVisualization:
    def __init__(self, model):
        self.rdf = RdfOntologyService(model)
        self.model, self.op = model, self.rdf.op

    def term_label(self, term):
        if isinstance(term, Literal):
            return str(term)
        if isinstance(term, BNode):
            return "_:" + str(term)
        value = str(term)
        prefixes = {
            "op": str(self.op),
            "gr": "http://purl.org/goodrelations/v1#",
            "qudt": "http://qudt.org/schema/qudt/",
            "unit": "http://qudt.org/vocab/unit/",
            "qk": "http://qudt.org/vocab/quantitykind/",
            "iof": "https://spec.industrialontologies.org/ontology/construct/",
            "rdf": str(RDF),
            "rdfs": str(RDFS),
            "owl": str(OWL),
        }
        for prefix, namespace in prefixes.items():
            if value.startswith(namespace):
                return f"{prefix}:{value[len(namespace) :]}"
        if value.startswith("urn:ontoproduct:record:"):
            return "record:" + value.removeprefix("urn:ontoproduct:record:")
        return value

    @staticmethod
    def _safe_label(value):
        # Mermaid identifiers are generated separately; source text is only a label.
        value = " ".join(str(value).split())
        if len(value) > 90:
            value = value[:87] + "…"
        return (
            html.escape(value, quote=True)
            .replace("[", "&#91;")
            .replace("]", "&#93;")
            .replace("|", "&#124;")
        )

    def _node(self, graph, term):
        group = "reference"
        if isinstance(term, Literal):
            label, group = str(term), "value"
        else:
            label = str(graph.value(term, RDFS.label) or self.term_label(term))
            if (term, RDF.type, self.op.ProductModel) in graph:
                group = "product"
            elif (term, RDF.type, self.op.Manufacturer) in graph:
                group = "entity"
            elif (term, RDF.type, self.rdf._reference("quantity_value")) in graph:
                group = "quantity"
                names = [
                    self.model.model.properties[key].label
                    for key, prop in self.model.model.properties.items()
                    if list(graph.subjects(self.op[prop.predicate], term))
                ]
                label = names[0] if names else "Quantity value"
            elif str(term).startswith("http://qudt.org/vocab/unit/"):
                group = "unit"
            elif str(term).startswith(str(self.op)):
                group = "local"
        return {
            "id": "n" + hashlib.sha256(term.n3().encode()).hexdigest()[:16],
            "term": term.n3(),
            "label": label,
            "group": group,
        }

    def diagram(self, graph, *, kind, product_class=None, include_evidence=False):
        if kind not in ("ontology", "product"):
            raise ValueError("Diagram kind must be ontology or product")
        op = self.op
        if kind == "ontology":
            predicates = {
                RDFS.subClassOf,
                RDFS.subPropertyOf,
                RDFS.domain,
                RDFS.range,
                OWL.disjointWith,
                op.quantityKind,
                op.canonicalUnit,
            }
            triples = [
                (s, p, o)
                for s, p, o in graph
                if p in predicates and isinstance(s, URIRef) and isinstance(o, URIRef)
            ]
            if product_class is not None:
                profiles = self.model.model.classes
                ancestors = self.rdf._ancestors(product_class)
                required, optional = self.rdf._properties(product_class)
                subjects = {op[name] for name in self.model.model.entity_classes} | {
                    op[name] for name in self.model.model.relations
                }
                subjects |= {op[profiles[c].model_class] for c in ancestors} | {
                    op[profiles[c].item_class] for c in ancestors
                }
                subjects |= {
                    op[prop.predicate] for prop in {**required, **optional}.values()
                }
                triples = [t for t in triples if t[0] in subjects]
        else:
            predicates = {
                self.rdf._reference(key)
                for key in (
                    "manufacturer",
                    "make_and_model",
                    "numeric_value",
                    "quantity_unit",
                    "quantity_kind",
                )
            }
            predicates |= {
                op[prop.predicate]
                for prop in self.model.model.properties.values()
                if prop.kind == "quantity"
            }
            triples = [t for t in graph if t[1] in predicates]
            # Show the most specific local type, instead of every ancestor.
            for subject in set(graph.subjects(RDF.type, op.ProductModel)):
                codes = [
                    c
                    for c, profile in self.model.model.classes.items()
                    if (subject, RDF.type, op[profile.model_class]) in graph
                ]
                if codes:
                    code = max(codes, key=lambda c: len(self.rdf._ancestors(c)))
                    triples.append(
                        (
                            subject,
                            RDF.type,
                            op[self.model.model.classes[code].model_class],
                        )
                    )
            if include_evidence:
                evidence_predicates = {
                    op.attributeEvidence,
                    op.candidateEvidence,
                    op.applicationField,
                    op.hasConflict,
                }
                evidence_predicates |= {
                    op[field]
                    for field in (
                        "value",
                        "unit",
                        "evidence",
                        "source_file",
                        "page",
                        "confidence",
                        "provenance",
                    )
                }
                triples.extend(t for t in graph if t[1] in evidence_predicates)
        triples = sorted(set(triples), key=lambda t: tuple(v.n3() for v in t))
        terms = sorted(
            {term for s, _, o in triples for term in (s, o)}, key=lambda t: t.n3()
        )
        nodes = {term: self._node(graph, term) for term in terms}
        edges = [
            {
                "source": nodes[s]["id"],
                "target": nodes[o]["id"],
                "relation": self.term_label(p),
            }
            for s, p, o in triples
        ]
        lines = ["flowchart LR"]
        for node in nodes.values():
            lines.append(f'  {node["id"]}["{self._safe_label(node["label"])}"]')
        for edge in edges:
            lines.append(
                f'  {edge["source"]} -->|"{self._safe_label(edge["relation"])}"| {edge["target"]}'
            )
        colors = {
            "local": ("#e0e7ff", "#6366f1"),
            "reference": ("#f3f4f6", "#64748b"),
            "product": ("#dbeafe", "#2563eb"),
            "entity": ("#fef3c7", "#d97706"),
            "quantity": ("#ede9fe", "#7c3aed"),
            "unit": ("#dcfce7", "#16a34a"),
            "value": ("#fff7ed", "#ea580c"),
        }
        for group, (fill, stroke) in colors.items():
            lines.append(
                f"  classDef {group} fill:{fill},stroke:{stroke},color:#111827"
            )
            identifiers = [n["id"] for n in nodes.values() if n["group"] == group]
            if identifiers:
                lines.append(f"  class {','.join(identifiers)} {group}")
        return {
            "mermaid": "\n".join(lines),
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    def triple_rows(self, graph):
        return [
            {
                "주어": self.term_label(s),
                "관계": self.term_label(p),
                "목적어": self.term_label(o),
                "목적어 유형": "값" if isinstance(o, Literal) else "개체",
            }
            for s, p, o in sorted(graph, key=lambda t: tuple(v.n3() for v in t))
        ]

    def attribute_rows(self, graph):
        rows = []
        unit_names = {
            self.rdf._reference(unit): unit for unit in self.model.units.catalog.units
        }
        for product in graph.subjects(RDF.type, self.op.ProductModel):
            for evidence in graph.objects(product, self.op.attributeEvidence):
                key = str(graph.value(evidence, self.op.applicationField))
                payload = graph.value(evidence, self.op.recordJSON)
                if payload is None:
                    continue
                attr = ProductAttribute.model_validate(json.loads(str(payload)))
                prop = self.model.model.properties.get(key)
                value, unit = attr.value, attr.unit
                if prop is not None and prop.kind == "quantity":
                    target = graph.value(product, self.op[prop.predicate])
                    if target is not None:
                        numeric = graph.value(
                            target, self.rdf._reference("numeric_value")
                        )
                        rdf_unit = graph.value(
                            target, self.rdf._reference("quantity_unit")
                        )
                        value = numeric.toPython() if numeric is not None else None
                        unit = unit_names.get(
                            rdf_unit, str(rdf_unit) if rdf_unit else None
                        )
                rows.append(
                    {
                        "속성": prop.label if prop else key,
                        "키": key,
                        "원문 값": "—" if attr.value is None else str(attr.value),
                        "원문 단위": attr.unit or "—",
                        "정규화 값": "—" if value is None else str(value),
                        "표준 단위": unit or "—",
                        "파일": attr.source_file or "—",
                        "페이지": str(attr.page) if attr.page is not None else "—",
                        "근거": attr.evidence or "—",
                        "출처": attr.provenance or "—",
                    }
                )
        return sorted(rows, key=lambda row: row["키"])

    def example_graphs(self):
        return {
            path.stem.removeprefix("example_"): Graph().parse(path, format="turtle")
            for path in sorted((DATA_DIR / "rdf").glob("example_*.ttl"))
        }
