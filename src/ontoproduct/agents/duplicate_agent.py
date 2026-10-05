from ontoproduct.agents.base import BaseAgent
from ontoproduct.agents.registry import CONTRACTS


class DuplicateAgent(BaseAgent):
    name = "duplicate"
    provider = "sqlite-rule-engine"
    version = "0.2.0"
    is_mock = False

    def __init__(self, service):
        required, optional, writes = CONTRACTS[self.name]
        self.required_reads, self.optional_reads, self.writes = set(required), set(optional), dict(writes)
        self.service = service

    def run(self, state):
        return {"duplicate_candidates": self.service.find(state["normalized_product"])}
