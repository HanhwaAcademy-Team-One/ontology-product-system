from ontoproduct.agents.extraction_agent import ExtractionAgent
from ontoproduct.agents.ontology_agent import OntologyAgent
from ontoproduct.agents.parser_agent import ParserAgent
from ontoproduct.agents.validation_agent import ValidationAgent
from ontoproduct.mocks.agents import mock_registry


def build_document_registry(ontology, *, parser_service, llm_services):
    """Replace the 01-04 document/validation slots; the rest keep the mock agents.

    The UI runtime still swaps duplicate/registration for its per-case DB agents.
    """
    registry = mock_registry(ontology)
    registry.register(ParserAgent(parser_service), replace=True)
    registry.register(
        ExtractionAgent(llm_services["extraction"], ontology=ontology), replace=True
    )
    registry.register(OntologyAgent(ontology, llm_services["ontology"]), replace=True)
    registry.register(ValidationAgent(ontology), replace=True)
    registry.validate_complete()
    return registry
