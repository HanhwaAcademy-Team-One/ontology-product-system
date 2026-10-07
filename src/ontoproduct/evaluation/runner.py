import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from pydantic import Field

from ontoproduct.agents.duplicate_agent import DuplicateAgent
from ontoproduct.agents.registry import AgentRegistry
from ontoproduct.graph.execution import execute_agent
from ontoproduct.graph.state import initial_state
from ontoproduct.graph.workflow import build_workflow
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.repositories.database import Database
from ontoproduct.repositories.product_repository import ProductRepository
from ontoproduct.schemas.common import DomainModel
from ontoproduct.schemas.product import NormalizedProduct
from ontoproduct.services.duplicate_service import DuplicateService
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.services.seed_service import seed_products
from .metrics import evaluate_duplicate, evaluate_extraction, evaluate_ontology
from .report import markdown_report


class GroundTruthCase(DomainModel):
    case_id: str
    description: str
    source_document: str
    product: NormalizedProduct
    relevant_duplicates: list[str] = Field(default_factory=list)


def load_ground_truth(directory):
    directory = Path(directory).resolve()
    cases = []
    for path in sorted(directory.glob("*.json")):
        case = GroundTruthCase.model_validate_json(
            path.read_text(encoding="utf-8")
        ).model_dump(mode="json")
        document = (directory / case["source_document"]).resolve()
        if not document.is_relative_to(directory.parent) or not document.is_file():
            raise ValueError("Ground truth source must exist inside the eval directory")
        case["source_text"] = document.read_text(encoding="utf-8")
        case["source_sha256"] = hashlib.sha256(document.read_bytes()).hexdigest()
        case["ground_truth_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        cases.append(case)
    if not cases or len({case["case_id"] for case in cases}) != len(cases):
        raise ValueError("Ground truth needs at least one case and unique case IDs")
    return cases


def run_evaluation(directory, output_directory=None):
    ontology = OntologyService()
    cases = load_ground_truth(directory)
    mock_samples = []
    registry = mock_registry(ontology)
    for truth in cases:
        graph = build_workflow(registry, ontology=ontology)
        config = {"configurable": {"thread_id": str(uuid4())}, "recursion_limit": 100}
        state = graph.invoke(
            initial_state(
                [
                    {
                        "name": Path(truth["source_document"]).name,
                        "text": truth["source_text"],
                    }
                ],
                max_extraction_retries=0,
                max_ontology_retries=0,
            ),
            config,
        )
        if any(log["status"] == "error" for log in state["agent_logs"]):
            raise RuntimeError(
                "Evaluation workflow failed; no success metric will be written"
            )
        mock_samples.append(
            {
                "ground_truth": truth,
                "outputs": {
                    key: state[key]
                    for key in (
                        "extracted_product",
                        "normalized_product",
                        "ontology_mapping",
                        "validation_result",
                        "duplicate_candidates",
                        "agent_logs",
                    )
                },
                "case_status": state["case_status"],
            }
        )
    mock_metrics = {
        **evaluate_extraction(mock_samples),
        **evaluate_ontology(mock_samples, ontology),
        **evaluate_duplicate(mock_samples),
    }
    rule_samples = []
    # An isolated database prevents evaluation from touching the user's products or checkpoints.
    with TemporaryDirectory(prefix="ontoproduct_eval_") as temporary:
        repository = ProductRepository(Database(Path(temporary) / "reference.db"))
        seed_products(repository)
        duplicate_registry = AgentRegistry()
        duplicate_registry.register(DuplicateAgent(DuplicateService(repository)))
        for truth in cases:
            cls = truth["product"]["product_class"]
            mapping = {
                "product_class": cls,
                "confidence": 1,
                "required_properties": {
                    k: p.model_dump(mode="json")
                    for k, p in ontology.resolve_required_properties(cls).items()
                },
                "optional_properties": {
                    k: p.model_dump(mode="json")
                    for k, p in ontology.resolve_optional_properties(cls).items()
                },
            }
            output = execute_agent(
                duplicate_registry,
                "duplicate",
                {"normalized_product": truth["product"], "ontology_mapping": mapping},
                writer=lambda event: None,
            )
            if any(log["status"] == "error" for log in output["agent_logs"]):
                raise RuntimeError("Duplicate evaluation failed")
            rule_samples.append({"ground_truth": truth, "outputs": output})
        rule_metadata = duplicate_registry.metadata()
    report = {
        "schema_version": 1,
        "run_id": str(uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "name": "OntoProduct synthetic teaching fixtures",
            "case_count": len(cases),
            "limitations": "Three authored fixtures; not real document extraction or production accuracy.",
        },
        "definitions": {
            "detection": "Micro precision/recall/F1 of non-null raw extracted attribute names.",
            "value": "Correct canonical normalized values / all non-null truth attributes; missing is wrong.",
            "unit": "Correct canonical units / unit-bearing truth attributes; missing is wrong.",
            "required": "Per truth-class required property, compare missing normalized values with MISSING_REQUIRED issues.",
            "duplicate": "Precision@K = hits/(K*query_count); Recall@K = hits/all relevant labels. Empty denominators are null.",
        },
        "suites": [
            {
                "label": "MOCK EVALUATION",
                "agents": registry.metadata(),
                "metrics": mock_metrics,
                "samples": mock_samples,
                "input_mode": "Unmodified Mock workflow, no manual edits, zero automatic retries.",
            },
            {
                "label": "RULE ENGINE EVALUATION",
                "agents": rule_metadata,
                "metrics": evaluate_duplicate(rule_samples),
                "samples": rule_samples,
                "input_mode": "Canonical ground-truth query directly to the real SQLite DuplicateAgent; isolated seed catalog.",
            },
        ],
    }
    if output_directory is not None:
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)
        for name, content in [
            (
                "evaluation.json",
                json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2),
            ),
            ("evaluation.md", markdown_report(report)),
        ]:
            temporary = output / f".{name}.{uuid4().hex}.tmp"
            try:
                temporary.write_text(content, encoding="utf-8")
                temporary.replace(output / name)
            finally:
                temporary.unlink(missing_ok=True)
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Measured MOCK and separate SQLite rule evaluation"
    )
    parser.add_argument("--ground-truth", type=Path, default=Path("eval/ground_truth"))
    parser.add_argument("--output", type=Path, default=Path("eval/reports"))
    args = parser.parse_args()
    report = run_evaluation(args.ground_truth, args.output)
    print(markdown_report(report))


if __name__ == "__main__":
    main()
