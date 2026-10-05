# PHASE 1 완료 보고서

작업일: 2026-10-05 (Asia/Seoul)

명세의 70·71·74번 범위를 구현했습니다. PHASE 2는 시작하지 않았습니다.

## 환경과 의존성

초기 저장소는 빈 README, 의존성 없는 pyproject.toml, Hello 출력 함수만 존재했습니다. 기존 Python 패키지 이름은 호환 진입점으로 유지하고, 구현은 src/ontoproduct에 배치했습니다.

| 항목 | 확인/고정 버전 |
|---|---|
| Python | 3.12.10, 프로젝트는 3.12 계열 |
| LangGraph | 1.2.12 |
| LangGraph checkpoint | 4.2.0 |
| LangChain | 1.4.3 |
| LangChain Core | 1.6.6 |
| Pydantic | 2.13.5 |
| PyYAML | 6.0.3 |
| pytest | 9.1.1 |
| uv | 0.12.17 |

호스트에는 Streamlit 1.64.0이 설치되어 있었지만 PHASE 1 프로젝트 의존성에는 추가하지 않았습니다. SQLite checkpointer도 PHASE 2에서 추가합니다. PyPI와 공식 LangGraph 문서를 확인하고 프로젝트 가상환경에서 고정 의존성을 설치했습니다. uv.lock은 전이 의존성까지 기록합니다.

## 생성·수정 파일과 책임

패키지 인식을 위한 각 디렉터리의 __init__.py도 포함합니다.

| 파일 | 책임 |
|---|---|
| src/ontoproduct/ontology/ontology.yaml | flat class registry, 필수/선택 속성과 canonical unit |
| src/ontoproduct/schemas/common.py | extra field와 비유한 수치 거부 |
| src/ontoproduct/schemas/product.py | 범용 ProductAttribute, Extracted/NormalizedProduct, ParsedDocument, FileReference |
| src/ontoproduct/schemas/ontology.py | 클래스·속성·상속 구조·매핑 계약 검증 |
| src/ontoproduct/schemas/validation.py | 업무 검증 이슈와 valid 일관성 |
| src/ontoproduct/schemas/duplicate.py | 중복 후보 계약 |
| src/ontoproduct/schemas/review.py | ReviewDecision, can_register 일관성 |
| src/ontoproduct/schemas/agent.py | AgentExecution 및 custom stream 이벤트 |
| src/ontoproduct/schemas/error.py | append-only 오류 이벤트와 최신 미해결 상태 조회 |
| src/ontoproduct/schemas/human_review.py | 수정·승인·거절 및 오류 retry/stop 입력 계약 |
| src/ontoproduct/services/ontology_service.py | 부모 상속, 자식 재정의, 단위 변환 |
| src/ontoproduct/services/normalization_service.py | 선택적 retry merge, 잠금 보호, 수동 병합과 orphan 보존/복원 |
| src/ontoproduct/services/validation_service.py | 필수값·타입·표준 단위·범위의 deterministic 검증 |
| src/ontoproduct/agents/base.py | BaseAgent 인터페이스와 계약 오류 |
| src/ontoproduct/agents/registry.py | 7개 고정 slot 계약, metadata, 교체/등록 검증 |
| src/ontoproduct/mocks/agents.py | Parser, Extraction, Ontology, Validation, Duplicate, Reviewer, Registration Mock |
| src/ontoproduct/graph/state.py | ProductState, operator.add Reducer, 초기 상태 |
| src/ontoproduct/graph/execution.py | read/write 계약 검증, 실행 격리, schema 검증, 시간·이력·stream·오류 처리 |
| src/ontoproduct/graph/routing.py | 상태를 변경하지 않는 조건부 Router와 오류 retry target |
| src/ontoproduct/graph/nodes.py | 정책 집행, HITL, retry 준비, 상태 전환 |
| src/ontoproduct/graph/workflow.py | compiled LangGraph 구성과 병렬 barrier join |
| src/ontoproduct/graph/checkpoint.py | PHASE 1 InMemorySaver factory |
| src/ontoproduct/cli.py | Mock 데모, 직접 입력 CLI, compiled Mermaid 생성 |
| src/ontology_product_system/__init__.py | 기존 CLI 진입점 호환 |
| tests/conftest.py | Registry/상태 fixture 및 오류 주입 도구 |
| tests/test_agent_contracts.py | required/optional reads, output/schema 위반, mutation 격리, Registry |
| tests/test_ontology.py | 상속·재정의·canonical 변환·잘못된 ontology |
| tests/test_manual_overrides.py | retry merge·수동값 보존·class 변경·orphan 복원 |
| tests/test_parallel_workflow.py | 실제 동시 실행, join, branch 오류와 전체 stage retry |
| tests/test_human_interrupt.py | 실제 interrupt, EDIT/APPROVE/REJECT, 잘못된 resume 처리 |
| tests/test_error_handler.py | 일반 stage 오류 interrupt, retry/stop, OPEN/RESOLVED 이력 |
| tests/test_workflow.py | retry 한도, 복구, 순수 Router, custom stream, thread 분리 |
| tests/test_validation.py | 타입·단위·범위·선택값 경고·confidence 정책 |
| tests/test_cli.py | CLI 데모/직접 입력, 잘못된 JSON, compiled 문서 일치 |
| tests/test_edge_cases.py | JSON 안전성, 수치 overflow, 승인 입력, 수동 편집 후 실제 graph retry |
| docs/workflow.mmd | 실제 compiled graph에서 생성한 Mermaid |
| README.md | PHASE 1 실행 방법, 구조, 범위 |
| pyproject.toml, requirements.txt, uv.lock | 의존성·패키징·pytest·CLI 설정 |
| .gitignore | 가상환경·cache·runtime·DB·빌드 산출물 제외 |

## Graph와 Agent Contract

Parser → Extraction → Ontology → apply_manual_overrides 이후 Validation과 Duplicate를 병렬 실행합니다. 두 branch가 완료되면 post_parallel_gate가 미해결 실행 오류를 판단합니다. 오류가 없으면 Reviewer가 재추출·재매핑·사람 검토·수정 필요·거절을 판단합니다.

Agent node는 공통 실행 Wrapper와 deterministic merge를 호출합니다. 업무 추출·판단은 Agent에, 규칙과 병합은 service/정책 node에 배치했습니다. 외부 client, Pydantic instance, 파일 handle은 업무 State에 저장하지 않습니다. Agent에는 선언한 reads의 복사본만 전달하며 입력 변경을 탐지합니다.

Registry는 명세의 required_reads/optional_reads/writes를 고정합니다. Agent 교체 시 metadata와 계약을 확인합니다. Wrapper는 필수 입력·정확한 출력 key·JSON 직렬화·Pydantic schema를 검사하며, 부분 output 실패 시 모든 업무 output을 폐기합니다. 실행 이력과 오류 이력만 append합니다. Validation과 Duplicate는 서로 다른 업무 key만 작성합니다.

## Ontology와 Retry

Product → ElectricalPart → Motor → BLDCMotor 및 Product → MechanicalPart → Bearing의 flat registry입니다. Motor의 manufacturer를 상속하고, 자식의 같은 속성 정의가 부모 정의를 대체합니다. 0.5 kW는 500 W, 1000 g은 1 kg으로 정규화됩니다.

Reviewer는 필수값 누락 또는 AI confidence < 0.70이면 RE_EXTRACT, 낮은 class confidence이면 REMAP_ONTOLOGY를 제안합니다. HUMAN 입력과 locked field는 confidence retry 후보에서 제외합니다. 선택 속성 누락은 경고입니다.

Router는 상태를 변경하지 않습니다. prepare_extraction_retry/prepare_ontology_retry만 해당 counter를 증가시킵니다. 기본 한도 1은 최초 실행 외 1회, 총 2회입니다. 한도에 도달하면 mark_needs_fix가 review_result와 case_status를 변경합니다. 사람의 오류 재시도는 이 자동 replanning counter와 별개이며 execution attempt에 기록합니다.

## Parallel, Human Override, Interrupt/Resume

테스트의 threading.Barrier로 두 branch가 동시에 실제 실행되는 것을 검증했습니다. branch에서 실행 예외가 발생해도 wrapper가 OPEN 이벤트를 반환하므로 두 branch가 join한 뒤 error_handler로 이동합니다. 병렬 오류 RETRY는 apply_manual_overrides로 이동해 두 Agent를 모두 다시 실행합니다.

effective product의 유일한 writer는 apply_manual_overrides입니다. human_review는 manual_overrides와 locked_fields를 갱신합니다. 사람 값은 HUMAN/null confidence로 저장합니다. 클래스 변경은 Ontology부터 다시 실행하며 기존 수정값과 잠금을 보존하고, 유효하지 않은 수정값은 orphaned_overrides로 이동합니다.

사람 검토 및 오류 처리는 실제 interrupt()로 중단합니다. caller는 같은 thread_id로 Command(resume=...)를 전달하고, node는 Command(goto=...)로 다음 경로를 선택합니다. interrupt 이전에 파일 생성이나 영속 DB 변경을 수행하지 않습니다. 잘못된 명령이나 승인 불가 상태의 APPROVE는 설명을 담아 다시 중단합니다.

## Error Retry

일반 Agent 실행 오류는 error_handler에서 RETRY/STOP을 기다립니다. RETRY는 실패 stage로, Validation/Duplicate 오류는 전체 병렬 stage의 입구로 이동합니다. 성공한 재실행은 동일 error_id의 RESOLVED 이벤트를 append합니다. 반복 실패한 OPEN 이벤트는 삭제하지 않으며 이후 성공 시 관련 미해결 이력을 모두 해결합니다. STOP도 기존 오류 이력을 보존합니다.

## 검증 결과

실행한 검증:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ontoproduct.cli
.venv\Scripts\python.exe -m ontoproduct.cli --diagram docs/workflow.mmd
uv --cache-dir .uv-cache build --offline
```

pytest 결과: **116 passed**. 실제 checkpoint/interrupt/resume을 사용했습니다. CLI는 NEEDS_FIX → 사람 수정 → READY_FOR_HUMAN → 승인 → REGISTERED를 완료했습니다. source distribution과 wheel 빌드가 성공했고 wheel에 ontology.yaml이 포함된 것을 확인했습니다.

## 알려진 제한사항과 PHASE 2 예정

Parser는 실제 PDF/Excel을 읽지 않으며 Extraction은 DM-500 Mock fixture를 사용합니다. Duplicate는 빈 후보 목록을 반환합니다. Reviewer는 deterministic Mock 정책입니다. 실제 LLM 품질이나 중복 검색 정확도를 평가한 결과가 아닙니다.

RegistrationMock은 final_product만 생성합니다. SQLite Product DB, Unique Constraint와 등록 멱등성, JSON 파일 Export, seed database는 PHASE 2 작업입니다. InMemorySaver는 프로세스 재시작 이후 상태를 보존하지 않으며 CLI를 다시 실행하면 새 workflow가 생성됩니다. thread_id는 같은 실행 중 checkpoint를 재개할 때 사용합니다.

다음 단계는 검증된 graph에 SQLite Checkpointer와 Streamlit Interaction adapter를 연결하고, 업로드 workspace, custom streaming UI, Human Review/Edit 및 오류 retry UI, Product DB와 export를 구현하는 것입니다. 평가·대시보드·최종 통합 문서는 PHASE 3에 진행합니다. PHASE 2는 명시적 진행 요청 전까지 시작하지 않습니다.

공식 확인 자료: [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts), [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api), [Streaming](https://docs.langchain.com/oss/python/langgraph/streaming), [LangGraph PyPI](https://pypi.org/project/langgraph/), [SQLite Checkpoint PyPI](https://pypi.org/project/langgraph-checkpoint-sqlite/).

## Windows 테스트 폴더 권한

2026-10-05에 기존 pytest Temp 폴더와 .pytest_cache가 다른 실행 계정의 전용 권한으로 생성되어 일반 사용자 실행에서 PermissionError가 발생한 것을 수정했습니다. tests/conftest.py는 기본 임시 경로를 .pytest_tmp/{실행별 UUID}로 지정하고, 새 캐시 폴더에는 프로젝트 폴더의 접근 권한을 상속하도록 미리 생성합니다. 사용자가 지정한 --basetemp와 cache_dir은 유지합니다.

이 작업에서는 기존 프로젝트 .pytest_cache에도 부모 폴더 권한 상속을 복구했습니다. 시스템 Temp의 기존 폴더는 변경하지 않았습니다. 샌드박스와 실제 사용자 계정 isaac\\eodud에서 모두 116개 테스트가 통과했고 캐시 경고도 발생하지 않았습니다.
