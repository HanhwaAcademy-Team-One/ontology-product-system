from langgraph.graph import END
from ontoproduct.schemas.error import unresolved_errors


def route_stage(state, next_node):
    return (
        "error_handler"
        if unresolved_errors(state.get("error_events", []))
        else next_node
    )


def route_parallel(state):
    return route_stage(state, "reviewer")


def route_review(state):
    if unresolved_errors(state.get("error_events", [])):
        return "error_handler"
    decision = state["review_result"]["decision"]
    if decision == "RE_EXTRACT":
        return (
            "prepare_extraction_retry"
            if state.get("extraction_retry_count", 0)
            < state.get("max_extraction_retries", 1)
            else "mark_needs_fix"
        )
    if decision == "REMAP_ONTOLOGY":
        return (
            "prepare_ontology_retry"
            if state.get("ontology_retry_count", 0)
            < state.get("max_ontology_retries", 1)
            else "mark_needs_fix"
        )
    if decision == "REJECT":
        return "mark_rejected"
    return "prepare_human_review"


def retry_target(error):
    return (
        "apply_manual_overrides"
        if error["stage"] in {"validation", "duplicate"}
        else error["stage"]
    )


def route_registration(state):
    return route_stage(state, END)
