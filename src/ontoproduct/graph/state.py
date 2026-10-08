import json
import operator
from typing import Annotated, TypedDict
from uuid import uuid4


class ProductState(TypedDict, total=False):
    session_id: str
    registration_case_id: str
    source_documents: list[dict]
    parsed_documents: list[dict]
    extracted_product: dict
    ontology_mapping: dict
    base_normalized_product: dict
    manual_overrides: dict
    locked_fields: list[str]
    orphaned_overrides: dict
    normalized_product: dict
    validation_result: dict
    duplicate_candidates: list[dict]
    review_result: dict
    human_review: dict
    final_product: dict
    extraction_retry_count: int
    ontology_retry_count: int
    max_extraction_retries: int
    max_ontology_retries: int
    case_status: str
    agent_logs: Annotated[list[dict], operator.add]
    error_events: Annotated[list[dict], operator.add]


def initial_state(
    source_documents: list[dict] | None = None,
    *,
    case_id: str | None = None,
    max_extraction_retries: int = 1,
    max_ontology_retries: int = 1,
) -> ProductState:
    for value in (max_extraction_retries, max_ontology_retries):
        if type(value) is not int or value < 0:
            raise ValueError("Retry limits must be non-negative integers")
    json.dumps(source_documents, allow_nan=False)
    return ProductState(
        session_id=str(uuid4()),
        registration_case_id=case_id or str(uuid4()),
        source_documents=source_documents
        if source_documents is not None
        else [
            {"name": "motor_spec.pdf", "text": "MOCK DM-500 BLDC Motor specification"}
        ],
        manual_overrides={},
        locked_fields=[],
        orphaned_overrides={},
        extraction_retry_count=0,
        ontology_retry_count=0,
        max_extraction_retries=max_extraction_retries,
        max_ontology_retries=max_ontology_retries,
        case_status="NEW",
        agent_logs=[],
        error_events=[],
    )
