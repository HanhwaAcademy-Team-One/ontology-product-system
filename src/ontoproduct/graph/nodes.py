from typing import Literal
from copy import deepcopy
from langgraph.graph import END
from langgraph.types import Command, interrupt
from pydantic import ValidationError
from ontoproduct.graph.execution import execute_agent
from ontoproduct.graph.routing import retry_target
from ontoproduct.schemas.error import unresolved_errors
from ontoproduct.schemas.human_review import ErrorRetryCommand, HumanReviewCommand
from ontoproduct.services.normalization_service import apply_overrides, human_edits, merge_extraction_retry


class WorkflowNodes:
    def __init__(self, registry, ontology):
        self.registry, self.ontology = registry, ontology

    def agent_node(self, name):
        def node(state):
            result = execute_agent(self.registry, name, state)
            if name == "extraction" and "extracted_product" in result:
                result["extracted_product"] = merge_extraction_retry(state, result["extracted_product"])
            if name == "registration" and "final_product" in result:
                result["case_status"] = "REGISTERED"
            return result
        return node

    def apply_manual_overrides(self, state):
        return apply_overrides(state, self.ontology)

    @staticmethod
    def post_parallel_gate(state):
        return {"case_status": "ERROR" if unresolved_errors(state.get("error_events", [])) else "REVIEWING"}

    @staticmethod
    def prepare_extraction_retry(state):
        return {"extraction_retry_count": state.get("extraction_retry_count", 0)+1, "case_status": "RETRYING_EXTRACTION"}

    @staticmethod
    def prepare_ontology_retry(state):
        return {"ontology_retry_count": state.get("ontology_retry_count", 0)+1, "case_status": "RETRYING_ONTOLOGY"}

    @staticmethod
    def mark_needs_fix(state):
        review = deepcopy(state["review_result"])
        label = "Extraction" if review["decision"] == "RE_EXTRACT" else "Ontology"
        review.update(decision="NEEDS_FIX", can_register=False, reason=f"{label} retry limit reached.")
        return {"review_result": review, "case_status": "NEEDS_FIX"}

    @staticmethod
    def prepare_human_review(state):
        return {"case_status": state["review_result"]["decision"]}

    @staticmethod
    def mark_rejected(state):
        return {"case_status": "REJECTED"}

    def human_review(self, state) -> Command[Literal["registration", "apply_manual_overrides", "ontology", "human_review", "__end__"]]:
        payload = {"kind": "human_review", "product": state["normalized_product"], "review": state["review_result"],
                   "orphaned_overrides": state.get("orphaned_overrides", {}),
                   "feedback": state.get("human_review", {}).get("feedback"),
                   "actions": ["EDIT", "REJECT"] + (["APPROVE"] if state["review_result"]["can_register"] else [])}
        raw = interrupt(payload)
        try:
            command = HumanReviewCommand.model_validate(raw)
            if command.action == "APPROVE":
                if (not state["review_result"]["can_register"] or not state["validation_result"]["valid"]
                        or unresolved_errors(state.get("error_events", []))):
                    raise ValueError("Approval is blocked until validation and review permit registration")
                return Command(update={"human_review": command.model_dump(mode="json"), "case_status": "APPROVED"},
                               goto="registration")
            if command.action == "REJECT":
                return Command(update={"human_review": command.model_dump(mode="json"), "case_status": "REJECTED"}, goto=END)
            if not command.edits and not command.changed_class:
                raise ValueError("EDIT requires edits or changed_class")
            edits = {k: v.model_dump(mode="json") if hasattr(v, "model_dump") else v for k, v in (command.edits or {}).items()}
            updates = human_edits(state, edits, command.changed_class, self.ontology)
            updates.update(human_review=command.model_dump(mode="json"), case_status="EDITING")
            return Command(update=updates, goto="ontology" if command.changed_class else "apply_manual_overrides")
        except (ValueError, ValidationError) as exc:
            return Command(update={"human_review": {"feedback": str(exc)}}, goto="human_review")

    @staticmethod
    def error_handler(state) -> Command[Literal["parser", "extraction", "ontology", "apply_manual_overrides",
                                               "reviewer", "registration", "error_handler", "__end__"]]:
        errors = unresolved_errors(state.get("error_events", []))
        raw = interrupt({"kind": "error", "errors": errors, "actions": ["RETRY", "STOP"],
                         "feedback": state.get("human_review", {}).get("feedback")})
        try:
            command = ErrorRetryCommand.model_validate(raw)
            if command.action == "STOP":
                return Command(update={"case_status": "STOPPED"}, goto=END)
            if not errors or not all(e["recoverable"] for e in errors):
                raise ValueError("No recoverable error is available for retry")
            return Command(update={"case_status": "RETRYING_ERROR"}, goto=retry_target(errors[0]))
        except (ValueError, ValidationError) as exc:
            return Command(update={"human_review": {"feedback": str(exc)}}, goto="error_handler")
