"""Build local ontology artifacts and validate the included model examples.

Run with the installed project: python scripts/build_product_ontology.py
This command uses local data only and does not invoke a model or write a database.
"""

import argparse
import json
from pathlib import Path

from ontoproduct.services.rdf_ontology_service import RdfOntologyService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("src/ontoproduct/ontology/rdf"))
    parser.add_argument("--examples", type=Path, default=Path("tests/fixtures/extraction_ontology/semantic_products.json"))
    args = parser.parse_args()
    service = RdfOntologyService()
    service.write_artifacts(args.output)
    products = json.loads(args.examples.read_text(encoding="utf-8"))
    for code, product in products.items():
        graph = service.product_graph(product, record_id=code)
        result = service.validate_graph(graph)
        if not result["valid"]:
            raise ValueError(f"Example {code} fails SHACL: {result['report']}")
        graph.serialize(destination=str(args.output / f"example_{code}.ttl"), format="turtle", encoding="utf-8")
        print(f"{code}: {len(graph)} RDF triples, SHACL conforms")
    print(f"Ontology and shapes written to {args.output}")


if __name__ == "__main__":
    main()
