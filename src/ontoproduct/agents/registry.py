from pydantic import TypeAdapter
from ontoproduct.agents.base import AgentContractError, BaseAgent
from ontoproduct.schemas.duplicate import DuplicateCandidate
from ontoproduct.schemas.ontology import OntologyMapping
from ontoproduct.schemas.product import (
    ExtractedProduct,
    NormalizedProduct,
    ParsedDocument,
)
from ontoproduct.schemas.review import ReviewResult
from ontoproduct.schemas.validation import ValidationResult

CONTRACTS = {
    "parser": ({"source_documents"}, set(), {"parsed_documents": list[ParsedDocument]}),
    "extraction": (
        {"parsed_documents"},
        {"review_result", "ontology_mapping", "locked_fields"},
        {"extracted_product": ExtractedProduct},
    ),
    "ontology": (
        {"extracted_product"},
        {"locked_fields", "manual_overrides"},
        {
            "ontology_mapping": OntologyMapping,
            "base_normalized_product": NormalizedProduct,
        },
    ),
    "validation": (
        {"normalized_product", "ontology_mapping"},
        set(),
        {"validation_result": ValidationResult},
    ),
    "duplicate": (
        {"normalized_product", "ontology_mapping"},
        set(),
        {"duplicate_candidates": list[DuplicateCandidate]},
    ),
    "reviewer": (
        {
            "normalized_product",
            "validation_result",
            "duplicate_candidates",
            "ontology_mapping",
        },
        {"review_result", "locked_fields"},
        {"review_result": ReviewResult},
    ),
    "registration": (
        {"normalized_product", "human_review"},
        {"duplicate_candidates", "ontology_mapping"},
        {"final_product": NormalizedProduct},
    ),
}


def validate_contract(agent: BaseAgent) -> None:
    if not isinstance(agent, BaseAgent) or agent.name not in CONTRACTS:
        raise AgentContractError(
            "Agent must implement BaseAgent and a known registry slot"
        )
    if not isinstance(agent.provider, str) or not agent.provider.strip():
        raise AgentContractError("provider must be a non-empty string")
    if (
        not isinstance(agent.version, str)
        or not agent.version.strip()
        or type(agent.is_mock) is not bool
    ):
        raise AgentContractError("Invalid version/is_mock metadata")
    required, optional, writes = CONTRACTS[agent.name]
    if (
        agent.required_reads != required
        or agent.optional_reads != optional
        or agent.writes != writes
    ):
        raise AgentContractError(f"{agent.name}: read/write contract mismatch")
    if type(agent.health_check()) is not bool:
        raise AgentContractError("health_check must return bool")
    for schema in writes.values():
        TypeAdapter(schema)


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent, *, replace: bool = False) -> None:
        validate_contract(agent)
        if agent.name in self._agents and not replace:
            raise AgentContractError(f"Duplicate agent slot: {agent.name}")
        self._agents[agent.name] = agent

    def get(self, name: str) -> BaseAgent:
        return self._agents[name]

    def validate_complete(self) -> None:
        if self._agents.keys() != CONTRACTS.keys():
            raise AgentContractError("All seven agent slots must be registered")
        for agent in self._agents.values():
            validate_contract(agent)

    def metadata(self) -> list[dict]:
        return [
            {
                "name": a.name,
                "provider": a.provider,
                "version": a.version,
                "is_mock": a.is_mock,
                "required_reads": sorted(a.required_reads),
                "optional_reads": sorted(a.optional_reads),
                "writes": sorted(a.writes),
                "health": a.health_check(),
            }
            for a in self._agents.values()
        ]
