# 08. 통합 담당자: 팀원 기능을 실제 앱에 연결하기

[공통 약속](00_COMMON.md) · [분업표](../MOCK_REPLACEMENT_PLAN.md)

## 1. 내 역할

각 담당자의 함수/Agent를 한 Registry에 모으고 UI runtime이 사용하도록 연결합니다. LLM client, 실행 모드, dependency, schema 변경도 이 담당자가 조율합니다.

팀원이 기능을 만들어도 실제 runtime에 등록하지 않으면 화면은 계속 Mock으로 동작합니다.

## 2. 현재 연결 위치

| 파일 | 현재 동작 | 담당 변경 |
| --- | --- | --- |
| [services/workflow_runtime.py](../../src/ontoproduct/services/workflow_runtime.py) | 기본 registry_factory=mock_registry. graph에서 Duplicate/Registration을 실제 Agent로 교체 | 실제 문서 Agent factory 주입 |
| [views/resources.py](../../src/ontoproduct/views/resources.py) | get_runtime이 cached WorkflowRuntime 생성 | 설정/client/factory 생성 |
| [app.py](../../src/ontoproduct/app.py)와 views 파일들 | get_runtime(storage_root) 호출 | 모드 설정을 일관되게 전달/표시 |
| [agents/registry.py](../../src/ontoproduct/agents/registry.py) | CONTRACTS 검사 | 기존 계약 유지. 새 정보가 필요하면 팀 합의 후 전체 변경 |
| [graph/workflow.py](../../src/ontoproduct/graph/workflow.py) | registry를 인자로 받아 compile | 그대로 재사용 |
| [cli.py](../../src/ontoproduct/cli.py) | 기본 Mock Graph | 실제 문서/registry를 쓰는 CLI가 필요하면 별도 옵션 |
| [evaluation/runner.py](../../src/ontoproduct/evaluation/runner.py) | Mock 평가 고정 | 별도 Real 평가 경로 추가 |
| 신규 agents/real_registry.py | 없음 | 문서 관련 실제 Agent factory |
| 신규 services/llm_service.py, settings.py | 없음 | 모델 호출 및 설정 |
| pyproject.toml / requirements.txt / uv.lock | 기존 dependency | 선택한 SDK/파서 추가·동기화 |

## 3. 팀원이 먼저 합의할 것

1. 파서 지원 범위: 텍스트 PDF, 표, XLSX, TXT, OCR 지원 여부.
2. Extraction/Ontology가 공통 LLM service를 호출하는 방법.
3. confidence의 의미와 산정/불확실 처리 정책.
4. 단위·속성 동의어, 문서 간 충돌 처리.
5. 모드: Mock 데모와 실제 실행을 어떻게 선택할지.
6. 실제 모델 호출 timeout/짧은 retry와 Graph 업무 retry의 구분.
7. dependency의 담당자와 버전.
8. schema를 확장할 때 어떤 소비자와 테스트를 함께 바꿀지.

선택할 SDK/파서 이름과 모델은 이 문서에서 정하지 않았습니다. 팀이 선택한 공식 API/현재 버전을 확인한 후 추가합니다.

## 4. LLM service는 하나의 공통 도구로 만듭니다

Extraction과 Ontology가 서로 다른 방식으로 API Key와 client를 만들면 설정과 오류 처리가 중복됩니다. 통합 담당자가 client를 만들고 생성자로 전달합니다.

공통 인터페이스 제안:

```python
class LlmService:
    def generate_structured(self, *, task, payload, response_schema):
        """모델을 호출하고 response_schema로 검사한 결과를 반환."""
        raise NotImplementedError
```

이 코드는 설계 틀이며 현재 실제 구현이 아닙니다. 반환을 Pydantic model로 할지 dictionary로 할지 팀이 먼저 정하고 두 Agent가 같은 약속을 사용합니다.

구현 항목:

- provider/model/key 설정 읽기.
- structured response를 모델 SDK로 요청하고 schema 검사.
- timeout, 제한된 통신 retry, 오류 메시지 정리.
- 문서 입력과 시스템 추출 규칙 구분.
- 모델/프롬프트 버전과 측정 가능한 호출 정보를 기록하는 정책.
- 로그와 state에 API Key나 client 객체를 넣지 않기.

현재 Agent writes에는 토큰 수나 원본 SDK 응답이 없습니다. 필요하면 서버 측 별도 기록 service에 보관하거나 정식 schema/계약 변경을 합의합니다. 임의로 Agent 반환 키를 추가하지 않습니다.

환경 변수 이름 제안은 AGENT_MODE, LLM_PROVIDER, LLM_MODEL, LLM_API_KEY입니다. 아직 이 프로젝트가 읽는 이름은 아니므로 settings.py에서 구현해야 합니다. .env 파일도 현재 자동으로 읽는 기능이 없습니다. settings에서 명시적으로 로드하거나 프로세스 환경 변수로 전달하는 방식을 정하세요.

## 5. 먼저 하나씩 교체하기

Parser만 완성된 때의 개발용 예시입니다. ParserService와 ParserAgent는 신규 구현 후 import합니다.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.agents.parser_agent import ParserAgent
from ontoproduct.services.parser_service import ParserService
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.workflow_runtime import WorkflowRuntime

with TemporaryDirectory(prefix="ontoproduct-parser-runtime-") as directory:
    paths = ApplicationPaths(Path(directory))
    parser_service = ParserService()

    def parser_registry(ontology):
        registry = mock_registry(ontology)
        registry.register(ParserAgent(parser_service), replace=True)
        registry.validate_complete()
        return registry

    runtime = WorkflowRuntime(paths, registry_factory=parser_registry)
    try:
        print(runtime.agent_metadata())
        # 업로드·Graph 실행 테스트도 이 블록 안에서 수행합니다.
    finally:
        runtime.close()
```

이 예시는 신규 ParserService/ParserAgent 구현 후 실행합니다. `ParserService()` 생성자는 §01의 제안과 같습니다. 생성자에 업로드 경로 설정을 추가했다면 이 호출도 맞추세요. 임시 데이터 폴더는 종료 시 삭제되며, UI 연결에서는 실제 storage_root로 ApplicationPaths를 만들고 cached runtime의 수명에 맞춰 관리합니다. 이렇게 하면 Parser만 실제 구현이고 나머지 문서 Agent는 기존 Mock입니다. UI runtime의 Duplicate/Registration은 기존처럼 실제 DB Agent입니다. 화면에 부분 교체 상태를 표시하세요.

이 과정을 Extraction, Ontology 순서로 진행하면 어느 단계에서 문제가 생겼는지 쉽게 찾습니다.

## 6. 다섯 문서 Agent가 완성되면

신규 agents/real_registry.py에 만들 factory 예시입니다. 생성자 형태는 각 담당자 문서와 합의한 예시이며 실제 구현과 일치시켜야 합니다.

```python
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.agents.parser_agent import ParserAgent
from ontoproduct.agents.extraction_agent import ExtractionAgent
from ontoproduct.agents.ontology_agent import OntologyAgent
from ontoproduct.agents.validation_agent import ValidationAgent
from ontoproduct.agents.reviewer_agent import ReviewerAgent

def build_document_registry(ontology, *, parser_service, llm_service):
    registry = mock_registry(ontology)
    registry.register(ParserAgent(parser_service), replace=True)
    registry.register(ExtractionAgent(llm_service), replace=True)
    registry.register(OntologyAgent(ontology, llm_service), replace=True)
    registry.register(ValidationAgent(), replace=True)
    registry.register(ReviewerAgent(), replace=True)
    registry.validate_complete()
    return registry
```

Reviewer가 LLM을 쓰면 생성자도 같은 방식으로 바꿉니다.

이 factory는 문서 관련 5개 슬롯을 교체합니다. 여기서 남은 Duplicate/Registration Mock은 **UI runtime이 작업별 실제 SQLite Agent로 교체**합니다. 이 factory만 build_workflow에 직접 전달하면 두 슬롯이 Mock으로 남으므로 실제 저장이 연결됐다고 생각하면 안 됩니다.

UI runtime 연결:

```python
def registry_factory(ontology):
    return build_document_registry(
        ontology,
        parser_service=parser_service,
        llm_service=llm_service,
    )

runtime = WorkflowRuntime(paths, registry_factory=registry_factory)
```

현재 factory의 호출 형식은 ontology 하나입니다. 다른 의존 객체는 위처럼 closure/생성자에 묶습니다. registration case_id는 runtime이 작업별로 묶으므로 state read 계약을 확장하지 않습니다.

## 7. cached runtime과 실행 모드

현재 get_runtime은 st.cache_resource로 재사용됩니다. 따라서 변경한 코드/설정이 오래된 객체에 바로 반영되지 않을 수 있습니다.

- 처음에는 실행 모드를 시작 설정으로 읽고, 변경 후 개발 서버를 재시작하는 방식이 단순합니다.
- UI에서 모드를 바꾸려면 mode/provider/model 같은 설정이 cache key의 함수 인자에 포함되도록 설계합니다.
- app.py와 모든 views가 같은 설정으로 같은 get_runtime을 호출해야 합니다.
- 모델 정보/실행 모드가 달라졌는데 이전 runtime을 재사용하지 않도록 확인합니다.
- 테스트에서 현재 get_runtime.clear()를 쓰므로 함수 인터페이스 변경 시 테스트 fixture도 함께 맞춥니다.

실제 모드를 선택했는데 키/설정이 없으면 명확한 설정 오류를 표시합니다. 조용히 Mock으로 되돌리고 실제 분석처럼 보여주면 안 됩니다.

현재 Registry health_check 응답은 외부 모델 연결/권한/잔액을 보장하지 않습니다. 모델 호출 확인은 별도 실제 요청으로 검증하고 metadata의 의미를 화면에 설명합니다.

## 8. UI에서 바꿀 위치

views/registration.py에는 “Mock 추출 모드”와 “Mock 예제로 시작”이 있습니다.

- 실제 모드에서는 실제 문서 분석임을 표시.
- Mock 예제는 별도 데모 모드로 구분.
- 원본 filename/page/evidence와 불확실 항목을 실제 결과로 표시.
- UI의 EDIT/APPROVE/REJECT/RETRY/STOP는 기존 runtime.resume과 Command 흐름 유지.
- Agent 모니터에 실제 factory의 Provider/Version/is_mock 표시가 맞는지 확인.

UI가 model 호출을 대신하는 코드를 넣지 않습니다.

## 9. schema 변경이 필요할 때

현재 schema는 extra=forbid로 모르는 필드를 거부합니다. Excel sheet/cell, 문서별 충돌 정보, token usage 등이 추가로 필요할 수 있습니다.

1. 필요한 정보와 실제 입력/출력 예시를 적습니다.
2. schema와 해당 Agent read/write 계약 변경 필요 여부를 확인합니다.
3. Parser/Extraction/Ontology/Review/UI/Checkpoint/Evaluation 중 소비자를 찾습니다.
4. 관련 담당자와 자료형/누락 처리/이름을 합의합니다.
5. 동시에 반영하고 이전 데이터 및 checkpoint 호환 여부를 확인합니다.
6. 테스트를 통과시킵니다.

기본 목표는 기존 계약으로 연결하는 것입니다. 업무 요구로 변경할 때도 팀원 한 명이 단독으로 키를 바꾸지 않습니다.

## 10. 통합 테스트 순서

1. 신규 parser 단위 테스트.
2. 신규 extraction/ontology의 통신 대체 테스트와 실제 원문 테스트.
3. validate_contract / execute_agent로 모든 슬롯의 metadata/입출력 검사.
4. 기존 전체 pytest 실행.
5. 별도 테스트 runtime 데이터 폴더에서 PDF/XLSX/TXT 업로드.
6. 제품 결과·근거·단위·분류 확인.
7. 재추출·재매핑·사람 수정·분류 변경·orphan 복원 확인.
8. validation/duplicate 병렬 join 및 오류 후 전체 stage retry 확인.
9. 승인 전에 DB 저장이 없는지 확인.
10. 승인 후 DB/JSON 생성, 반복 승인/Export 실패 retry의 중복 방지.
11. 서버 재시작 후 checkpoint 복원.
12. Real 평가 실행과 보고서 생성.
13. 각 UI 페이지에서 예외 없는지 확인.

외부 API 없이 돌아가는 단위/회귀 테스트와 실제 모델 호출 테스트를 분리합니다. 실제 모델 호출은 별도 테스트 자료로 실행하고 결과를 기록해야 합니다. Mock transport 통과만으로 Real 평가 성공을 주장하지 않습니다.

## 11. 인계 체크리스트

- 최종 `runtime.agent_metadata()`에 기대한 7개 실제 Agent가 보임. 특정 작업은 `runtime.agent_metadata(thread_id)`로 확인. `runtime.metadata`라는 메서드는 없음.
- 실제 모델/프롬프트/실행 모드가 보고서에 기록됨.
- Mock 데모/기존 회귀 테스트는 재현 가능.
- 모든 신규 및 기존 테스트 통과.
- 실제 문서에서 서로 다른 제품이 추출되고 근거가 확인됨.
- 재시도/사람 수정/저장/복원 흐름 유지.
- 지원하지 않는 문서/OCR 범위와 알려진 오류를 README에 기록.
