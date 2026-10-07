from ontoproduct.agents.base import BaseAgent
from ontoproduct.agents.registry import CONTRACTS
from ontoproduct.graph.state import ProductState
from ontoproduct.services.parser_service import ParserService


class ParserAgent(BaseAgent):
    """source_documents의 원본 파일을 읽어 parsed_documents로 반환하는 실제 Parser 슬롯."""

    name = "parser"
    provider = "local-document-parser"
    version = "0.3.0"
    is_mock = False

    def __init__(self, service: ParserService) -> None:
        required, optional, writes = CONTRACTS[self.name]
        self.required_reads = set(required)
        self.optional_reads = set(optional)
        self.writes = dict(writes)
        self.service = service

    def run(self, state: ProductState) -> dict:
        """업로드 파일 참조 목록을 받아 파일·페이지별 원문 목록을 반환한다."""
        return {"parsed_documents": self.service.parse(state["source_documents"])}
