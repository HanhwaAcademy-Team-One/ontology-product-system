from ontoproduct.agents.base import BaseAgent
from ontoproduct.agents.registry import CONTRACTS
from ontoproduct.graph.state import ProductState
from ontoproduct.services.validation_service import (
    validate_product,
    validate_registration_product,
)


class ValidationAgent(BaseAgent):
    # Registry에서 사용하는 슬롯 이름
    name = "validation"

    # LLM이 아닌 Python 규칙으로 검증
    provider = "python-validation-rules"
    version = "0.2.0"
    is_mock = False

    def __init__(self, ontology=None):
        self.ontology = ontology
        # 공통 계약에서 이 Agent가 읽고 쓸 수 있는 키를 가져옴
        required, optional, writes = CONTRACTS[self.name]
        self.required_reads = set(required)
        self.optional_reads = set(optional)
        self.writes = dict(writes)

    def run(self, state: ProductState) -> dict:
        # 사람이 수정한 제품 정보와 해당 분류의 온톨로지 기준으로 검증
        args = state["normalized_product"], state["ontology_mapping"]
        result = (
            validate_registration_product(*args, self.ontology)
            if self.ontology is not None
            else validate_product(*args)
        )

        # 이 Agent가 담당하는 결과만 반환
        return {"validation_result": result}
