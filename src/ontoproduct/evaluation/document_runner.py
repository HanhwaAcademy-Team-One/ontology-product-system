"""Isolated inputdata evaluation; offline reference responses never measure LLM quality."""

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from uuid import uuid4

from ontoproduct.agents.real_registry import build_document_registry
from ontoproduct.schemas.product import ProductAttribute
from ontoproduct.services.agent_errors import OntologyClassificationError
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.evidence_service import is_conflict, validate_quoted_value
from ontoproduct.services.mapping_service import PropertyAliases
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.services.parser_service import ParserService
from ontoproduct.services.workflow_runtime import WorkflowRuntime

from .metrics import evaluate_extraction, evaluate_ontology, ratio
from .report import markdown_report

OUTCOMES = {
    "valid": "valid",
    "equivalent_values": "valid",
    "classification_error": "classification_error",
    "missing_required": "missing_required",
    "unsupported_unit": "unsupported_unit",
    "semantic_error": "semantic_error",
    "required_conflict": "required_conflict",
    "optional_conflict": "document_conflict",
    "identity_conflict": "document_conflict",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_hash(value):
    return sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode(
            "utf-8"
        )
    )


def load_cases(directory, case_ids=None, file_format=None):
    root = Path(directory).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    verification = json.loads((root / "verification.json").read_text(encoding="utf-8"))
    hashes = {item["file"]: item["sha256"] for item in verification["files"]}
    cases = manifest["cases"]
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate manifest case ID")
    if case_ids is not None:
        if set(case_ids) - {c["id"] for c in cases}:
            raise ValueError("Unknown case IDs")
        cases = [c for c in cases if c["id"] in case_ids]
    groups = []
    for case in cases:
        if case["expected_outcome"] not in OUTCOMES:
            raise ValueError("Unknown expected outcome")
        if case["upload_mode"] not in {"together", "choose_one_format"}:
            raise ValueError("Unsupported upload mode")
        selected = (
            [case["files"]]
            if case["upload_mode"] == "together"
            else [[f] for f in case["files"]]
        )
        for files in selected:
            if file_format and any(Path(f).suffix != f".{file_format}" for f in files):
                continue
            source_hashes = {}
            for name in files:
                path = (root / name).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    raise ValueError("Source must be inside the dataset")
                digest = sha256(path.read_bytes())
                if digest != hashes.get(name):
                    raise ValueError(f"Source hash mismatch: {name}")
                source_hashes[name] = digest
            groups.append(
                {
                    **deepcopy(case),
                    "files": files,
                    "source_hashes": source_hashes,
                    "group_id": f"{case['id']}-{len(groups):03d}",
                }
            )
    if not groups:
        raise ValueError("No evaluation groups selected")
    return groups


class ReferenceLlm:
    """Manifest raw values anchored to parsed lines; synthetic transport fixture only."""

    def __init__(self, case):
        self.case = case
        self.ontology = OntologyService()
        self.aliases = PropertyAliases().as_payload()

    def generate_structured(self, *, task, payload, response_schema):
        if task == "ontology":
            product = payload["extracted_product"]
            present = {
                k
                for k, a in product["attributes"].items()
                if a["value"] is not None
                or is_conflict(ProductAttribute.model_validate(a))
            }
            try:
                cls = self.ontology.semantic_model.classify(
                    product.get("candidate_class"), present
                )
            except OntologyClassificationError:
                cls = None
            return response_schema.model_validate(
                {"product_class": cls, "confidence": 0.9 if cls else 0.0}
            )
        chunk = payload["documents"][0]
        doc = self.case
        if self.case["documents"]:
            index = next(
                i
                for i, name in enumerate(self.case["files"])
                if Path(name).name in chunk["source_file"]
            )
            doc = self.case["documents"][index]
        attrs = {}
        for key, raw in doc.get("attributes", self.case["raw_attributes"]).items():
            for line in chunk["text"].splitlines():
                if not any(
                    self.aliases[label] == key and label.casefold() in line.casefold()
                    for label in self.aliases
                ):
                    continue
                attr = ProductAttribute(
                    **raw,
                    evidence=line,
                    source_file=chunk["source_file"],
                    page=chunk["page"],
                    confidence=0.9,
                )
                try:
                    validate_quoted_value(attr)
                except ValueError:
                    continue
                attrs[key] = attr.model_dump(mode="json")
                break
        name = doc["product_name"]
        return response_schema.model_validate(
            {
                "product_name": name if name in chunk["text"] else None,
                "candidate_class": self.case["product_class"],
                "attributes": attrs,
            }
        )


class EvaluationLimit(RuntimeError):
    """No further model calls are permitted in this evaluation run."""


class CountedLlm:
    def __init__(self, service, budget):
        self.service, self.calls, self.budget = service, [], budget

    def generate_structured(self, **kwargs):
        budget = self.budget
        if (
            budget["max_calls"] is not None and budget["calls"] >= budget["max_calls"]
        ) or (
            budget["seconds"] is not None
            and perf_counter() - budget["started"] >= budget["seconds"]
        ):
            raise EvaluationLimit("Evaluation call/time limit reached; no request sent")
        budget["calls"] += 1
        started = perf_counter()
        call = {
            "task": kwargs["task"],
            "prompt_version": kwargs["payload"].get("prompt_version"),
            "provider": getattr(self.service, "provider", type(self.service).__name__),
            "model": getattr(self.service, "model", None),
        }
        self.calls.append(call)
        try:
            result = self.service.generate_structured(**kwargs)
            call["status"] = "success"
            return result
        except Exception as exc:
            call.update(status="error", exception_type=type(exc).__name__)
            raise
        finally:
            call["seconds"] = perf_counter() - started


def observed_outcome(state):
    errors = [e for e in state.get("error_events", []) if e["status"] == "OPEN"]
    if errors:
        kind = errors[-1]["exception_type"]
        return {
            "DocumentConflictError": "document_conflict",
            "OntologyClassificationError": "classification_error",
            "EvaluationLimit": "limit_reached",
        }.get(kind, "execution_error")
    issues = [
        i for i in state["validation_result"]["issues"] if i["severity"] == "error"
    ]
    if any(
        is_conflict(ProductAttribute.model_validate(a))
        for a in state["normalized_product"]["attributes"].values()
    ):
        return "required_conflict"
    if any(i["code"] == "UNIT" for i in issues):
        return "unsupported_unit"
    if any(i["code"] != "MISSING_REQUIRED" for i in issues):
        return "semantic_error"
    return "missing_required" if issues else "valid"


def run_document_evaluation(
    directory,
    output_directory,
    *,
    case_ids=None,
    llm_services=None,
    mode="offline_reference",
    file_format=None,
    max_calls=None,
    time_limit_seconds=None,
):
    if mode not in {"offline_reference", "live"} or (
        mode == "live" and llm_services is None
    ):
        raise ValueError("Live mode requires explicitly supplied model services")
    if mode == "live" and (max_calls is None or time_limit_seconds is None):
        raise ValueError("Live mode requires call and time limits")
    if max_calls is not None and (type(max_calls) is not int or max_calls < 1):
        raise ValueError("max_calls must be a positive integer")
    if time_limit_seconds is not None and time_limit_seconds <= 0:
        raise ValueError("time limit must be positive")
    groups = load_cases(directory, case_ids, file_format)
    budget = {
        "started": perf_counter(),
        "calls": 0,
        "max_calls": max_calls,
        "seconds": time_limit_seconds,
    }
    run_id = str(uuid4())
    output = Path(output_directory).resolve() / run_id
    output.mkdir(parents=True, exist_ok=False)
    samples, metric_samples, metadata, calls = [], [], [], []
    for group in groups:
        temporary = TemporaryDirectory(prefix="op_eval_")
        paths = ApplicationPaths(Path(temporary.name))
        reference = ReferenceLlm(group) if llm_services is None else None
        services = {
            slot: CountedLlm(llm_services[slot] if llm_services else reference, budget)
            for slot in ["extraction", "ontology"]
        }

        def factory(ontology, paths=paths, services=services):
            return build_document_registry(
                ontology,
                parser_service=ParserService(paths.uploads),
                llm_services=services,
            )

        runtime = WorkflowRuntime(paths, registry_factory=factory)
        state = {}
        try:
            session = str(uuid4())
            thread = runtime.create_case(session)
            refs = [
                runtime.documents.save(
                    session, Path(f).name, (Path(directory) / f).read_bytes()
                )
                for f in group["files"]
            ]
            list(
                runtime.start(
                    thread, refs, max_extraction_retries=0, max_ontology_retries=0
                )
            )
            state = runtime.snapshot(thread).values
            metadata = runtime.agent_metadata(thread)
            saved = runtime.products.count()
        finally:
            runtime.close()
            temporary.cleanup()
        outputs = {
            k: deepcopy(state[k])
            for k in [
                "parsed_documents",
                "extracted_product",
                "normalized_product",
                "ontology_mapping",
                "validation_result",
                "duplicate_candidates",
                "review_result",
                "agent_logs",
                "error_events",
            ]
            if k in state
        }
        outcome = observed_outcome(state)
        truth = {
            "case_id": group["group_id"],
            "source_sha256": json_hash(group["source_hashes"]),
            "ground_truth_sha256": json_hash(
                {
                    k: v
                    for k, v in group.items()
                    if k not in {"source_hashes", "group_id"}
                }
            ),
            "product": {
                "product_name": group["product_name"],
                "product_class": group["product_class"],
                "attributes": group["expected_normalized_attributes"] or {},
            },
            "relevant_duplicates": [],
        }
        group_calls = [c for s in services.values() for c in s.calls]
        calls.extend(group_calls)
        sample = {
            "ground_truth": truth,
            "outputs": outputs,
            "case_status": state["case_status"],
            "source_hashes": group["source_hashes"],
            "expected_outcome": group["expected_outcome"],
            "observed_outcome": outcome,
            "outcome_matches": outcome == OUTCOMES[group["expected_outcome"]],
            "saved_products": saved,
            "integration_after_human": None,
            "calls": group_calls,
            "truth_review": "manifest_candidate; lexical reference anchors checked; no independent human review",
            "extraction_retry_count": state.get("extraction_retry_count", 0),
            "ontology_retry_count": state.get("ontology_retry_count", 0),
        }
        samples.append(sample)
        if group["expected_normalized_attributes"] is not None:
            measured = deepcopy(sample)
            for k, fallback in {
                "extracted_product": {"attributes": {}},
                "normalized_product": {"attributes": {}},
                "ontology_mapping": {"product_class": None},
                "validation_result": {"issues": []},
            }.items():
                measured["outputs"].setdefault(k, fallback)
            metric_samples.append(measured)
    ai_attributes = [
        attr
        for s in samples
        for attr in s["outputs"]
        .get("normalized_product", {})
        .get("attributes", {})
        .values()
        if attr["value"] is not None and attr.get("provenance") == "AI"
    ]
    metrics = {
        **evaluate_extraction(metric_samples),
        **evaluate_ontology(metric_samples, OntologyService()),
        "Expected Outcome Accuracy": ratio(
            sum(s["outcome_matches"] for s in samples), len(samples)
        ),
        "AI Confidence Null Rate": ratio(
            sum(a.get("confidence") is None for a in ai_attributes), len(ai_attributes)
        ),
        "Human Repair Case Rate": ratio(
            sum(
                s["outputs"].get("review_result", {}).get("decision") == "NEEDS_FIX"
                for s in samples
            ),
            len(samples),
        ),
    }
    report = {
        "schema_version": 1,
        "run_id": run_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "live_llm_verified": mode == "live",
        "report_directory": str(output),
        "manifest_sha256": sha256((Path(directory) / "manifest.json").read_bytes()),
        "verification_sha256": sha256(
            (Path(directory) / "verification.json").read_bytes()
        ),
        "dataset": {
            "name": "inputdata synthetic documents",
            "case_count": len(samples),
            "limitations": "Manifest truth candidates; offline reference responses are not LLM accuracy. No OCR. Duplicate relevance is unannotated; no duplicate accuracy claim.",
        },
        "definitions": {
            "outcome_mapping": OUTCOMES,
            "quality_metrics": "Known normalized truth only; failures remain in denominators. Unknown truth coverage is explicit.",
            "automatic": "All outputs before EDIT/APPROVE; no products saved.",
            "calls": "Service calls; SDK transport retries are not counted separately.",
            "confidence": "Null scores / observed non-null normalized AI attributes. Unproduced attributes are outside this score-only denominator; quality metrics still penalize missing known truth. No calibrated probability claim.",
        },
        "truth_coverage": {
            "normalized_truth_groups": len(metric_samples),
            "unknown_normalized_truth_groups": len(samples) - len(metric_samples),
            "independently_human_reviewed": False,
        },
        "call_count": len(calls),
        "limits": {
            "max_calls": max_calls,
            "time_limit_seconds": time_limit_seconds,
            "semantics": "Checked before each service call; in-flight SDK calls retain configured timeout/retries.",
        },
        "limited_cases": [
            s["ground_truth"]["case_id"]
            for s in samples
            if s["observed_outcome"] == "limit_reached"
        ],
        "calls": calls,
        "failures": [
            s["ground_truth"]["case_id"]
            for s in samples
            if s["observed_outcome"] == "execution_error" or not s["outcome_matches"]
        ],
        "suites": [
            {
                "label": "OFFLINE REFERENCE EVALUATION"
                if mode == "offline_reference"
                else "LIVE MODEL EVALUATION",
                "input_mode": mode,
                "agents": metadata,
                "metrics": metrics,
                "samples": samples,
            }
        ],
    }
    (output / "evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2),
        encoding="utf-8",
    )
    (output / "evaluation.md").write_text(markdown_report(report), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Offline synthetic reference evaluation; no API calls"
    )
    parser.add_argument("--dataset", type=Path, default=Path("inputdata"))
    parser.add_argument("--output", type=Path, default=Path("eval/document_reports"))
    parser.add_argument("--cases", nargs="+")
    parser.add_argument("--format", choices=["txt", "pdf", "xlsx"])
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actual model calls; obtain user approval before running",
    )
    parser.add_argument("--max-calls", type=int, default=8)
    parser.add_argument("--time-limit-seconds", type=float, default=600)
    args = parser.parse_args()
    services = None
    if args.live:
        import os

        from ontoproduct.services.llm_service import create_llm_services
        from ontoproduct.services.settings import Settings

        settings = Settings.from_environment({**os.environ, "AGENT_MODE": "real"})
        services = create_llm_services(settings)
    report = run_document_evaluation(
        args.dataset,
        args.output,
        case_ids=args.cases,
        file_format=args.format,
        mode="live" if args.live else "offline_reference",
        llm_services=services,
        max_calls=args.max_calls if args.live else None,
        time_limit_seconds=args.time_limit_seconds if args.live else None,
    )
    print(report["report_directory"])
    print(report["suites"][0]["metrics"]["Expected Outcome Accuracy"])


if __name__ == "__main__":
    main()
