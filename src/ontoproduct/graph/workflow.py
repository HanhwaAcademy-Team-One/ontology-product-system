from langgraph.graph import END, START, StateGraph
from ontoproduct.graph.checkpoint import memory_checkpointer
from ontoproduct.graph.nodes import WorkflowNodes
from ontoproduct.graph.routing import route_parallel, route_registration, route_review, route_stage
from ontoproduct.graph.state import ProductState
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.services.ontology_service import OntologyService


def build_workflow(registry=None, *, ontology=None, checkpointer=None):
    ontology = ontology or OntologyService()
    registry = registry if registry is not None else mock_registry(ontology)
    registry.validate_complete()
    nodes = WorkflowNodes(registry, ontology)
    graph = StateGraph(ProductState)
    for name in ("parser", "extraction", "ontology", "validation", "duplicate", "reviewer", "registration"):
        graph.add_node(name, nodes.agent_node(name))
    for name in ("apply_manual_overrides", "post_parallel_gate", "prepare_extraction_retry",
                 "prepare_ontology_retry", "mark_needs_fix", "prepare_human_review", "mark_rejected",
                 "human_review", "error_handler"):
        graph.add_node(name, getattr(nodes, name))
    graph.add_edge(START, "parser")
    for current, following in (("parser", "extraction"), ("extraction", "ontology"), ("ontology", "apply_manual_overrides")):
        graph.add_conditional_edges(current, lambda state, target=following: route_stage(state, target), [following, "error_handler"])
    graph.add_edge("apply_manual_overrides", "validation")
    graph.add_edge("apply_manual_overrides", "duplicate")
    graph.add_edge(["validation", "duplicate"], "post_parallel_gate")
    graph.add_conditional_edges("post_parallel_gate", route_parallel, ["reviewer", "error_handler"])
    graph.add_conditional_edges("reviewer", route_review, ["error_handler", "prepare_extraction_retry",
                                "prepare_ontology_retry", "mark_needs_fix", "mark_rejected", "prepare_human_review"])
    graph.add_edge("prepare_extraction_retry", "extraction")
    graph.add_edge("prepare_ontology_retry", "ontology")
    graph.add_edge("mark_needs_fix", "human_review")
    graph.add_edge("prepare_human_review", "human_review")
    graph.add_edge("mark_rejected", END)
    graph.add_conditional_edges("registration", route_registration, [END, "error_handler"])
    # Command nodes deliberately have no static outgoing edges.
    return graph.compile(checkpointer=checkpointer if checkpointer is not None else memory_checkpointer())
