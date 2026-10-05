from ontoproduct.agents.base import BaseAgent
from ontoproduct.agents.registry import CONTRACTS


class RegistrationAgent(BaseAgent):
    name = "registration"
    provider = "sqlite"
    version = "0.2.0"
    is_mock = False

    def __init__(self, case_id, service):
        required, optional, writes = CONTRACTS[self.name]
        self.required_reads, self.optional_reads, self.writes = set(required), set(optional), dict(writes)
        # The case identity is bound outside ProductState, preserving the frozen agent contract.
        self.case_id, self.service = case_id, service

    def run(self, state):
        result = self.service.register(self.case_id, state["normalized_product"], state["human_review"])
        return {"final_product": result["record"]["product"]}
