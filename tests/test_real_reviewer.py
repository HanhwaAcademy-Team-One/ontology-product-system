from copy import deepcopy

import pytest

from ontoproduct.mocks.agents import ReviewerMock
from ontoproduct.services.validation_service import validate_product


def inputs(paused_state):
    return deepcopy(
        {
            k: paused_state[k]
            for k in [
                "normalized_product",
                "ontology_mapping",
                "validation_result",
                "duplicate_candidates",
                "locked_fields",
            ]
        }
    )


def reviewer():
    from ontoproduct.agents.reviewer_agent import ReviewerAgent

    return ReviewerAgent()


def test_conflict_does_not_retry_and_preserves_input(paused_state):
    from ontoproduct.schemas.product import ProductAttribute
    from ontoproduct.services.evidence_service import pack_evidence

    state = inputs(paused_state)
    state["normalized_product"]["attributes"]["rated_power"] = pack_evidence(
        [
            ProductAttribute(value=600, unit="W", source_file="a.txt"),
            ProductAttribute(value=800, unit="W", source_file="b.txt"),
        ],
        conflict=True,
    ).model_dump(mode="json")
    state["normalized_product"]["attributes"].pop("rated_speed")
    state["validation_result"] = validate_product(
        state["normalized_product"], state["ontology_mapping"]
    )
    before = deepcopy(state)
    result = reviewer().run(state)["review_result"]
    assert state == before
    assert result["decision"] == "NEEDS_FIX"
    assert result["retry_fields"] == []
    assert "rated_power" in result["reason"]


@pytest.mark.parametrize(
    "class_score,attr_score", [(0.9, 0.9), (0.1, 0.9), (0.9, 0.1), (0.1, None)]
)
def test_relation_error_beats_confidence_retry(paused_state, class_score, attr_score):
    state = inputs(paused_state)
    state["ontology_mapping"]["confidence"] = class_score
    state["normalized_product"]["attributes"]["rated_power"]["confidence"] = attr_score
    state["validation_result"] = {
        "valid": False,
        "issues": [
            {
                "field": "attributes.inner_diameter",
                "code": "RANGE",
                "message": "inner_diameter must be less than outer_diameter",
                "severity": "error",
            }
        ],
    }
    result = reviewer().run(state)["review_result"]
    assert result["decision"] == "NEEDS_FIX"
    assert result["retry_fields"] == []
    assert not result["can_register"]


@pytest.mark.parametrize("protected", ["HUMAN", "locked"])
def test_protected_null_is_not_approved(paused_state, protected):
    state = inputs(paused_state)
    attr = state["normalized_product"]["attributes"]["rated_power"]
    attr["value"] = None
    if protected == "HUMAN":
        attr["provenance"] = "HUMAN"
    else:
        state["locked_fields"] = ["attributes.rated_power"]
    state["validation_result"] = validate_product(
        state["normalized_product"], state["ontology_mapping"]
    )
    result = reviewer().run(state)["review_result"]
    assert result["decision"] == "NEEDS_FIX" and not result["can_register"]


def test_missing_and_low_confidence_keep_existing_retry(paused_state):
    state = inputs(paused_state)
    state["normalized_product"]["attributes"].pop("rated_speed")
    state["validation_result"] = validate_product(
        state["normalized_product"], state["ontology_mapping"]
    )
    result = reviewer().run(state)["review_result"]
    assert result["decision"] == "RE_EXTRACT"
    assert result["retry_fields"] == ["rated_speed"]
    state = inputs(paused_state)
    state["ontology_mapping"]["confidence"] = 0.1
    assert reviewer().run(state)["review_result"]["decision"] == "REMAP_ONTOLOGY"
    state["locked_fields"] = ["product_class"]
    assert reviewer().run(state)["review_result"]["decision"] == "READY_FOR_HUMAN"


@pytest.mark.parametrize("verdict", ["LIKELY_DUPLICATE", "POSSIBLE_DUPLICATE"])
def test_duplicate_reason_keeps_human_approval(paused_state, verdict):
    state = inputs(paused_state)
    state["duplicate_candidates"] = [
        {
            "product_id": "actual-db-id",
            "product_name": "Existing",
            "verdict": verdict,
            "score": 0.9,
            "reason": "same specs",
            "evidence": [{"field": "rated_power", "status": "MATCH"}],
        }
    ]
    result = reviewer().run(state)["review_result"]
    assert result["decision"] == "READY_FOR_HUMAN"
    assert all(
        s in result["reason"]
        for s in ["Existing", verdict, "rated_power", "MATCH", "actual-db-id"]
    )


def test_mock_remains_mock():
    assert ReviewerMock().is_mock
