# 00. 모두가 먼저 읽을 공통 약속

[전체 분업표](../MOCK_REPLACEMENT_PLAN.md)

## 1. 폴더를 어떻게 읽나요?

루트: `D:\ontology-product-system`

| 폴더 | 쉽게 설명하면 |
| --- | --- |
| src/ontoproduct/agents | “이 기능은 무엇을 받고 무엇을 돌려준다”를 구현하는 입구 |
| src/ontoproduct/services | 문서 읽기, 모델 호출, 검증, 저장 같은 실제 작업 함수 |
| src/ontoproduct/schemas | 팀원끼리 주고받는 데이터 모양 검사 |
| src/ontoproduct/mocks | 기존 데모를 위한 고정/규칙 Agent |
| src/ontoproduct/graph | 실행 순서, 병렬 처리, 재시도, 사람 검토 연결 |
| src/ontoproduct/views | 사용자가 보는 화면 |
| tests | 자동으로 실행하는 확인 코드 |
| eval | 평가용 원문, 정답, 보고서 |
| runtime | 업로드·DB·Export 등 실제 실행 데이터 |

Agent는 입구, Service는 작업 도구라고 생각하면 됩니다. 화면은 Graph에 실행을 요청하고, Graph가 Agent를 실행합니다.

## 2. 입력과 출력은 무엇인가요?

Agent의 `run(state)`에서 `state`는 Python dictionary입니다. 다른 단계가 만든 자료가 들어 있습니다.

Parser는 `state["source_documents"]`를 읽습니다. 작업이 끝나면 다음 형태를 반환합니다.

```json
{
  "parsed_documents": [
    {
      "source_file": "motor_spec.txt",
      "text": "Product: DM-600\nClass: BLDCMotor\nManufacturer: XYZ Motors\nRated Voltage: 24 V\nRated Power: 0.6 kW\nRated Speed: 3200 rpm",
      "page": null
    }
  ]
}
```

이 가이드의 신규 실제 Parser는 TXT·XLSX의 `page`를 `null`, PDF의 `page`를 1부터 시작하는 실제 페이지 번호로 통일합니다. Extraction 이후에도 이 위치 값을 유지합니다. 기존 ParserMock은 TXT에도 `page: 1`을 반환하며, schema는 두 값을 모두 허용합니다. 위 JSON은 신규 실제 Parser의 목표 출력입니다.

`parsed_documents`라는 이름은 다음 Extraction 담당자가 읽기로 약속한 이름입니다. 이를 `documents`로 바꾸면 연결이 끊깁니다.

“입출력을 수정한다”는 말은 우선 **같은 봉투 이름 안에 들어가는 내용을 실제 값으로 바꾼다**는 뜻입니다. 봉투 이름과 자료형은 현재 계약을 유지합니다.

## 3. 반드시 읽을 기존 파일

- [BaseAgent](../../src/ontoproduct/agents/base.py): 모든 Agent가 갖춰야 할 기본 인터페이스.
- [Registry / CONTRACTS](../../src/ontoproduct/agents/registry.py): 슬롯별 필수 입력, 선택 입력, 출력 검사.
- [execute_agent](../../src/ontoproduct/graph/execution.py): Agent 실행, 결과 검사, 시간·오류 기록.
- [ProductState](../../src/ontoproduct/graph/state.py): 전체 작업 state의 키 목록.
- [product schema](../../src/ontoproduct/schemas/product.py): 파일·문서·제품·속성의 자료형.

필수 입력은 없으면 실행 실패입니다. 선택 입력은 첫 실행 때 없을 수 있으므로 `state.get("locked_fields", [])`처럼 읽습니다.

Wrapper는 허용된 입력만 골라 Agent에 전달합니다. Extraction이 임의로 `state["source_documents"]`를 읽으면 안 됩니다. Extraction에 전달되는 필수 입력은 이미 읽은 `parsed_documents`입니다.

## 4. 새 Agent의 기본 모양

아래는 Parser 담당자가 구현할 틀입니다. ParserAgent 파일과 service는 아직 만들지 않은 신규 제안입니다.

```python
from ontoproduct.agents.base import BaseAgent
from ontoproduct.agents.registry import CONTRACTS

class ParserAgent(BaseAgent):
    name = "parser"
    provider = "local-document-parser"
    version = "0.3.0"
    is_mock = False

    def __init__(self, service):
        required, optional, writes = CONTRACTS[self.name]
        self.required_reads = set(required)
        self.optional_reads = set(optional)
        self.writes = dict(writes)
        self.service = service

    def run(self, state):
        documents = self.service.parse(state["source_documents"])
        return {"parsed_documents": documents}
```

- name: 교체할 슬롯 이름. UI에서 쓰는 이름과 같습니다.
- provider: 실제 처리 도구/모델 제공자 이름.
- version: 구현 버전. 예시 버전 번호는 팀에서 정하면 됩니다.
- is_mock: 실제 구현은 False.
- required_reads / optional_reads / writes: CONTRACTS에서 복사하므로 오타를 줄입니다.
- service: 실제 작업 함수가 있는 객체. 생성자에서 받습니다.

실제 기능을 만들지 않고 `is_mock=False`만 바꾸면 완료가 아닙니다.

## 5. Pydantic은 왜 쓰나요?

데이터 모양을 검사하는 도구입니다. 제품 속성의 value는 문자열·숫자·boolean·null 중 하나여야 합니다. 속성 안에 임의 dictionary나 list를 넣으면 현재 스키마에 맞지 않습니다.

```python
from ontoproduct.schemas.product import ExtractedProduct

def convert_response(model_response):
    product = ExtractedProduct.model_validate(model_response)
    return {"extracted_product": product.model_dump(mode="json")}
```

`model_response`는 모델 응답을 읽어 만든 dictionary라고 가정한 예시입니다. `model_validate`로 검사하고, `model_dump(mode="json")`으로 저장 가능한 dictionary를 만듭니다.

현재 schema는 정의하지 않은 필드를 거부합니다. `notes`, `sheet`, `provider_response` 같은 키를 마음대로 추가하면 오류입니다. Excel 위치는 기존 text/evidence에 넣거나 schema 담당자와 확장을 합의합니다.

## 6. 공통 금지 사항과 이유

| 잘못하기 쉬운 일 | 올바른 구현 |
| --- | --- |
| 받은 state의 dictionary를 직접 고침 | 새 dictionary를 만들어 반환 |
| 전체 state를 반환 | 자신의 writes에 있는 키만 반환 |
| Agent에서 agent_logs/error_events/case_status를 반환 | execute_agent와 Graph가 관리 |
| UI에서 agent.run 또는 LLM을 직접 호출 | UI → runtime → Graph → Agent |
| UploadedFile, DB Connection, LLM Client를 state에 넣음 | 파일은 FileReference, client/service는 Agent 생성자 |
| OntologyAgent가 normalized_product를 반환 | base_normalized_product 반환; 기존 수동 수정 병합 노드가 최종값 작성 |
| 사람이 입력한 속성을 재추출로 덮어씀 | locked_fields를 존중하고 기존 병합 로직 재사용 |
| 미확인 숫자를 confidence=0.95로 채움 | 근거와 점수 정책 정의; 모르면 명시적인 불확실 처리 |

숫자는 value에 `24`, 단위는 unit에 `"V"`를 넣습니다. `"24 V"` 전체를 숫자 value에 넣지 않습니다. NaN/Infinity도 허용하지 않습니다.

## 7. 오류를 어떻게 전달하나요?

문서를 읽지 못하거나 모델 호출이 실패하면 알아볼 수 있는 예외를 발생시킵니다.

```python
raise ValueError("motor_spec.pdf: 읽을 수 있는 텍스트가 없습니다")
```

execute_agent가 예외를 받아 오류 이벤트와 실행 실패를 기록하고 Graph가 기존 오류 화면으로 이동합니다. 실패했는데 `{"parsed_documents": []}`처럼 성공 결과로 숨기지 않습니다.

“문서에 정격 속도가 없다”는 추출 결과의 누락입니다. “PDF가 손상되어 아예 읽을 수 없다”는 처리 오류입니다. 이 둘을 구분하세요.

모델 SDK의 짧은 호출 재시도와 Graph의 업무 재추출은 별개입니다. Graph는 Reviewer feedback으로 추가 시도합니다. SDK 내부 retry를 무한하게 두면 Graph가 기다리므로 호출 timeout과 횟수는 통합 담당자와 정합니다.

## 8. 테스트는 세 단계로 합니다

1. **기능 테스트**: 실제 TXT/PDF/XLSX, 규칙 또는 모델 응답을 자신의 기능에 넣고 결과 확인.
2. **계약 테스트**: 입력 변경 여부, 반환 키, schema, JSON 직렬화, metadata 확인.
3. **Graph 테스트**: 실제 Agent를 한 슬롯에 등록하고 재시도·오류·사람 수정 흐름 확인.

단위 테스트에서 외부 모델 통신만 가짜 응답으로 바꿀 수 있습니다. 실제 Agent의 결과 정리·스키마 검사 코드는 실행해야 합니다. 이 테스트만으로 실제 모델 품질을 검증했다고 말하지 않고, 별도 실제 호출·문서 평가도 진행합니다.

## 9. 새 Agent를 계약과 함께 확인하는 공통 예시

Agent 파일을 구현한 뒤 테스트 코드에서 사용할 틀입니다.

```python
import json
from copy import deepcopy
from ontoproduct.graph.execution import execute_agent
from ontoproduct.mocks.agents import mock_registry

registry = mock_registry()
registry.register(agent, replace=True)  # agent는 내가 만든 실제 Agent
before = deepcopy(inputs)              # inputs는 해당 기능의 입력 dictionary
events = []
result = execute_agent(
    registry, agent.name, inputs, writer=events.append
)

assert inputs == before  # 호출자가 가진 원본 입력이 보존됐는지 확인
assert result["agent_logs"][-1]["status"] == "success"  # Agent 내부 입력 변경도 실패로 탐지
assert not result["error_events"]
assert set(result) == set(agent.writes) | {"agent_logs", "error_events"}
json.dumps(result, allow_nan=False)
```

execute_agent는 허용된 입력을 deepcopy해서 Agent에 넘깁니다. 따라서 Agent가 받은 복사본을 수정해도 `assert inputs == before`는 통과합니다. Wrapper는 Agent에게 넘긴 복사본의 실행 전후를 따로 비교하고, 변경됐다면 AgentContractError와 `status="error"`를 기록합니다. 이 계약 위반을 잡는 검사는 위의 `status == "success"`입니다. Agent 자체의 입력 불변성만 직접 검사하려면 별도 단위 테스트에서 복사한 입력을 `agent.run`에 전달하고 실행 전후를 비교하세요.

직접 `agent.run(inputs)`를 호출하면 업무 출력만 나옵니다. execute_agent의 결과에는 Wrapper가 추가한 로그와 오류 이벤트도 있습니다. 두 결과의 키를 혼동하지 마세요.

## 10. 완료와 인계

담당자 혼자 schema나 Graph를 바꾸지 않습니다. 입력/출력에 추가 정보가 필요하면 이유와 예시를 적어 통합 담당자와 합의합니다.

현재 제품명은 문자열만 저장하므로 product_name 자체에는 속성처럼 provenance가 없습니다. 제공된 필드의 의미를 확인한 뒤 확장해야 합니다.

테스트 명령은 저장소 루트에서 실행합니다.

```powershell
.venv\Scripts\python.exe -m pytest tests\test_agent_contracts.py -q
.venv\Scripts\python.exe -m pytest -q -W error::pytest.PytestCacheWarning
```

각 기능 문서의 신규 테스트 명령은 그 테스트 파일을 작성한 이후 사용합니다.
