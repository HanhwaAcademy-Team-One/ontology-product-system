from ontoproduct.agents.base import BaseAgent
from ontoproduct.agents.registry import CONTRACTS
from ontoproduct.schemas.product import ProductAttribute
from ontoproduct.schemas.review import ReviewResult
from ontoproduct.services.evidence_service import is_conflict


class ReviewerAgent(BaseAgent):
    name = "reviewer"
    provider = "python-review-rules"
    version = "0.1.0"
    is_mock = False

    def __init__(self):
        required, optional, writes = CONTRACTS[self.name]
        self.required_reads, self.optional_reads, self.writes = (
            set(required),
            set(optional),
            dict(writes),
        )

    def run(self, state):
        locked = set(state.get("locked_fields", []))
        attrs = state["normalized_product"]["attributes"]
        retry, conflicts, protected_missing = [], [], []
        for key in state["ontology_mapping"]["required_properties"]:
            attr = attrs.get(key)
            protected = f"attributes.{key}" in locked or (
                attr and attr.get("provenance") == "HUMAN"
            )
            if attr and is_conflict(ProductAttribute.model_validate(attr)):
                conflicts.append(key)
            elif not attr or attr.get("value") is None:
                (protected_missing if protected else retry).append(key)
            elif (
                not protected
                and attr.get("provenance") == "AI"
                and (attr.get("confidence") is None or attr["confidence"] < 0.70)
            ):
                retry.append(key)
        errors = [
            i for i in state["validation_result"]["issues"] if i["severity"] == "error"
        ]
        if (
            conflicts
            or protected_missing
            or any(i["code"] != "MISSING_REQUIRED" for i in errors)
        ):
            decision = "NEEDS_FIX"
            detail = "; ".join(
                [
                    *(f"Conflicting document values: {k}" for k in conflicts),
                    *(
                        f"Protected required value is missing: {k}"
                        for k in protected_missing
                    ),
                    *(f"{i['field']}: {i['message']}" for i in errors),
                ]
            )
            reason, retry = f"Human repair is required. {detail}", []
        elif retry:
            decision, reason = (
                "RE_EXTRACT",
                "Required properties are missing or have low AI confidence.",
            )
        elif (
            state["ontology_mapping"]["confidence"] < 0.70
            and "product_class" not in locked
        ):
            decision, reason = (
                "REMAP_ONTOLOGY",
                "Ontology mapping confidence is below 0.70.",
            )
        elif not state["validation_result"]["valid"]:
            decision, reason = (
                "NEEDS_FIX",
                "Deterministic validation requires human repair.",
            )
        else:
            decision, reason = (
                "READY_FOR_HUMAN",
                "Required properties are valid; human approval is required.",
            )
        for candidate in state["duplicate_candidates"]:
            evidence = ", ".join(
                f"{e['field']}={e['status']}" for e in candidate.get("evidence", [])
            )
            reason += f" Duplicate candidate {candidate['product_name']} ({candidate['product_id']}): {candidate.get('verdict') or 'UNCLASSIFIED'}; {candidate['reason']}; {evidence}."
        return {
            "review_result": ReviewResult(
                decision=decision,
                reason=reason,
                retry_fields=retry,
                can_register=decision == "READY_FOR_HUMAN",
            ).model_dump(mode="json")
        }
