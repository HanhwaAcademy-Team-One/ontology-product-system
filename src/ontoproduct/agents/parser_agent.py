from ontoproduct.agents.base import BaseAgent
from ontoproduct.agents.registry import CONTRACTS


class ParserAgent(BaseAgent):
    name = "parser"
    provider = "local-document-parser"
    version = "0.3.0"
    is_mock = False

    def __init__(self, service):
        required, optional, writes = CONTRACTS[self.name]
        self.required_reads, self.optional_reads, self.writes = set(required), set(optional), dict(writes)
        self.service = service

    def run(self, state):
        return {"parsed_documents": self.service.parse(state["source_documents"])}
