from ontoproduct.agents.extraction_agent import ExtractionAgent
from ontoproduct.agents.ontology_agent import OntologyAgent
from ontoproduct.agents.parser_agent import ParserAgent
from ontoproduct.agents.registry import AgentRegistry
from ontoproduct.agents.reviewer_agent import ReviewerAgent
from ontoproduct.agents.validation_agent import ValidationAgent


def build_document_registry(ontology, *, parser_service, llm_services):
    """Register the document, validation and reviewer agents.

    Duplicate and registration need a case-specific database, so WorkflowRuntime
    adds them per case before the workflow checks that every slot is filled.
    """
    registry = AgentRegistry()
    registry.register(ParserAgent(parser_service))
    registry.register(ExtractionAgent(llm_services["extraction"], ontology=ontology))
    registry.register(OntologyAgent(ontology, llm_services["ontology"]))
    registry.register(ValidationAgent(ontology))
    registry.register(ReviewerAgent())
    return registry
