# 08. 통합 가이드: 설정과 실제 앱 연결

[문서 목차](../README.md) · [공통 약속](00_COMMON.md) · [분업표](../MOCK_REPLACEMENT_PLAN.md)

현재 UI는 `AGENT_MODE=real`에서 Parser·Extraction·Ontology를 실제 구현으로 연결합니다. Validation·Reviewer는 기존 Mock 규칙을 사용하고, Duplicate·Registration은 두 모드 모두 runtime의 실제 SQLite Agent입니다. 설치와 실행 명령은 [Quick start](../QUICK_START.md)를 따릅니다.

## 현재 연결 위치

| 파일 | 현재 역할 |
| --- | --- |
| [services/settings.py](../../src/ontoproduct/services/settings.py) | 환경 변수와 YAML 기본값 검증 |
| [config/llm.yaml](../../src/ontoproduct/config/llm.yaml) | 공급자·모델·timeout·retry 팀 기본값 |
| [services/llm_protocol.py](../../src/ontoproduct/services/llm_protocol.py) | 공통 LlmService 인터페이스 |
| [services/llm_service.py](../../src/ontoproduct/services/llm_service.py) | OpenAI adapter, Agent별 서비스 생성 |
| [agents/real_registry.py](../../src/ontoproduct/agents/real_registry.py) | 01~03 실제 문서 Agent 교체 |
| [views/resources.py](../../src/ontoproduct/views/resources.py) | 설정에 따른 cached runtime 생성·조회 |
| [services/workflow_runtime.py](../../src/ontoproduct/services/workflow_runtime.py) | 작업별 Graph, checkpoint, 실제 SQLite Agent 연결 |
| [agents/registry.py](../../src/ontoproduct/agents/registry.py) | CONTRACTS 검사 |
| [graph/workflow.py](../../src/ontoproduct/graph/workflow.py) | Registry를 받아 compile |
| [cli.py](../../src/ontoproduct/cli.py) | PHASE 1 Mock CLI, InMemory Checkpointer |
| [evaluation/runner.py](../../src/ontoproduct/evaluation/runner.py) | Mock 평가와 SQLite 규칙 평가 별도 실행 |

## 실행 설정

`Settings.from_environment()`가 설정을 읽습니다. `AGENT_MODE`는 환경 변수로만 정하며, **`.env` 파일은 자동으로 읽지 않습니다.** API Key는 Settings나 YAML에 담지 않습니다.

| 환경 변수 | 의미 | 현재 기본값 |
| --- | --- | --- |
| `AGENT_MODE` | `mock` 또는 `real` | `mock` |
| `OPENAI_API_KEY` | OpenAI SDK가 사용하는 키 | 없음, Real 모드에 필요 |
| `LLM_PROVIDER` | 공급자, 현재 `openai` 지원 | YAML의 `openai` |
| `LLM_MODEL` | 공통 모델 | 환경 변수 기본값 없음; YAML models.default는 `gpt-5` |
| `LLM_MODEL_EXTRACTION` | Extraction 전용 모델 | 없음 |
| `LLM_MODEL_ONTOLOGY` | Ontology 전용 모델 | 없음 |
| `LLM_TIMEOUT_SECONDS` | 모델 요청 timeout(초), 0보다 커야 함 | YAML의 `250` |
| `LLM_MAX_RETRIES` | SDK 통신 retry 횟수, 0 이상 | YAML의 `2` |
| `ONTOPRODUCT_DATA_DIR` | 업로드·DB·Export 저장 루트 | 현재 작업 디렉터리의 `runtime/` |

Agent 모델 선택 순서는 다음과 같습니다.

1. 환경 변수 `LLM_MODEL_<AGENT>`
2. 환경 변수 `LLM_MODEL`
3. YAML `models.<agent>`
4. YAML `models.default`

환경 변수의 공급자·timeout·retry 값도 YAML보다 우선합니다. LLM을 쓰는 슬롯은 Extraction·Ontology이며 다른 이름의 `LLM_MODEL_*`는 설정 오류입니다. OntologyAgent는 직접 생성할 때 LLM 없이 규칙 분류를 사용할 수 있지만, UI Real Registry는 두 Agent 모두 LLM 서비스를 전달합니다.

Real 모드의 키·공급자·모델이 없거나 잘못되면 화면에 설정 오류를 표시하고 페이지를 멈춥니다. 설정이나 키를 변경하면 서버를 재시작합니다. API Key는 cache key에서 제외하며 client는 state에 넣지 않습니다.

## Registry와 runtime

기존 Graph·ProductState·read/write 계약을 재사용합니다. 현재 factory의 호출 형식은 다음과 같습니다.

```python
from ontoproduct.agents.real_registry import build_document_registry

def registry_factory(ontology):
    return build_document_registry(
        ontology,
        parser_service=parser_service,
        llm_services=llm_services,
    )
```

`parser_service`와 `llm_services`는 `views/resources.py`의 `get_runtime()`이 생성해 closure로 전달합니다. `ParserService`에는 해당 runtime의 `ApplicationPaths.uploads`를 전달합니다.

`build_document_registry()`는 parser·extraction·ontology만 교체합니다. 이를 `build_workflow()`에 직접 전달하면 Duplicate·Registration은 Mock으로 남습니다. UI처럼 실제 DB에 저장하려면 `WorkflowRuntime(paths, registry_factory=registry_factory)`을 사용해야 합니다. runtime이 case_id별 RegistrationAgent와 SQLite DuplicateAgent를 연결합니다.

모든 화면과 앱 진입점은 `current_runtime()`을 사용합니다. Real 설정은 `get_runtime` cache key에 포함됩니다(API Key 제외). Mock 모드는 기존 기본 runtime을 사용합니다. 테스트는 `get_runtime.clear()`로 cache를 정리합니다.

## LLM adapter

공통 인터페이스는 `generate_structured(task=..., payload=..., response_schema=...)`입니다. `OpenAiLlmService`는 Responses API의 `client.responses.create`에 strict JSON schema를 전달하고, 복원한 결과를 Pydantic 스키마로 검증하여 반환합니다.

- payload의 `instructions`는 신뢰된 지침으로, 나머지 문서 자료는 user 메시지 JSON으로 분리합니다.
- 자유 키 맵(`dict[str, X]`)은 요청에서 `[{key, value}]` 배열로 바꾸고 응답 후 원래 맵으로 복원합니다.
- 숫자 범위·기본값 등은 원래 Pydantic 스키마의 로컬 검증으로 확인합니다.
- 거부·미완료·빈 응답·JSON 오류·스키마 불일치는 원문을 담지 않는 `LlmResponseError`로 Graph 오류 경로에 전달합니다.
- SDK timeout·통신 retry는 Graph의 재추출·재분류 업무 retry와 별개입니다.
- `create_llm_services(settings)`가 하나의 SDK client를 공유하고 Agent별 모델 서비스를 만듭니다.

현재 Agent writes에 토큰 수나 원본 SDK 응답을 임의로 추가하지 않습니다. 별도 기록이 필요하면 서버 측 service 또는 정식 스키마·계약 변경으로 구현합니다.

## 추가 Agent 교체와 스키마 변경

Validation·Reviewer 교체는 남은 구현 범위입니다. 전용 Agent와 테스트를 만들고 Registry에 `replace=True`로 등록합니다. `mocks/agents.py`를 직접 바꿔 기존 데모·평가를 함께 변경하지 않습니다.

1. 새 Agent의 입력·출력과 기존 CONTRACTS 일치 여부를 확인합니다.
2. 관련 단위 테스트, `validate_contract`·`execute_agent` 검사, 부분 교체 Graph 테스트를 실행합니다.
3. runtime factory에 연결하고 최종 metadata를 확인합니다.
4. 수정·승인·거절·오류 retry·재시작 복원을 확인합니다.
5. 전체 회귀 테스트를 통과하고 지원 범위·남은 제한을 기록합니다.

스키마를 바꿀 때는 Parser/Extraction/Ontology/Review/UI/Checkpoint/Evaluation 중 소비자를 확인하고 자료형·누락 정책·호환성을 합의합니다. 스키마·계약·모든 소비자·테스트를 함께 반영합니다.

UI는 모드·모델·실제 근거를 표시하고 `EDIT / APPROVE / REJECT / RETRY / STOP`을 runtime.resume으로 전달합니다. UI에서 모델을 직접 호출하지 않습니다. SHACL 결과를 Graph Validation의 업무 정책에 합치는 작업은 별도 구현 범위입니다.

## 검증

기본 회귀 테스트는 실제 모델을 호출하지 않습니다.

```powershell
.venv\Scripts\python.exe -m pytest -q
```

실제 모델 호출을 검증하려면 API Key와 모델 설정이 준비된 터미널에서 실행합니다. 업로드 원문이 API로 전송되며 실제 호출 비용이 발생합니다.

```powershell
$env:ONTOPRODUCT_LIVE_LLM = "1"
.venv\Scripts\python.exe -m pytest -q tests/test_live_llm.py
Remove-Item Env:\ONTOPRODUCT_LIVE_LLM
```

[Live 테스트](../../tests/test_live_llm.py)는 motor_spec.txt와 two_page_spec.pdf를 처리합니다. 기존 기록은 OpenAI gpt-5에서 DM-600, BLDCMotor, 0.6 kW → 600 W, 원문 근거·페이지를 확인한 2 passed(약 78초, 당시 timeout 60초)입니다. 이것은 제한된 사례의 검증 기록입니다.

현재 Registry Health는 외부 모델 연결·권한·잔액을 보장하지 않습니다. 실제 추출 품질 평가는 [09 Evaluation](09_EVALUATION.md)에 따른 별도 데이터와 측정이 필요합니다.
