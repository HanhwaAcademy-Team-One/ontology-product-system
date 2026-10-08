# 04 점검 후 남은 작업 구현 프롬프트

[현재 점검·남은 작업](04_VALIDATION.md#9-점검-결과와-남은-작업) · [공통 계약](00_COMMON.md)

기준일: 2026-10-09. Claude Code나 Codex 세션에 **공통 지시문과 선택한 작업의 코드 블록 하나**를 함께 붙여넣습니다. 아래는 후속 작업 지시문이며, 해당 기능이 구현됐다는 보고가 아닙니다.

권장 순서는 1A(정책 정리) → 1B(SHACL 연결) → 2(Reviewer) → 3a(오프라인 평가 경로)입니다. 3b(실모델 실행)는 3a 완료 후 사용자의 실행 승인을 받아 별도로 수행합니다. 5(confidence 개선)는 3a의 평가 기반에 의존하며, 실제 효과 비교에는 3b의 실행 승인 범위가 필요합니다. 4(오류 해결)는 별도 계약 검토가 필요합니다. 6~8은 질문 목록을 작성해 사용자에게 요구를 확인받는 작업이며 한 번에 모두 구현하지 않습니다.

## 공통 지시문

```text
작업 저장소: D:\ontology-product-system
역할: 아래에 선택해 붙인 작업 한 개만 수행한다.

먼저 AGENTS.md, CLAUDE.md, docs/team/00_COMMON.md,
docs/team/04_VALIDATION.md §9와 선택 작업의 근거 문서를 읽는다.
문서의 과거 구현 기록과 현재 코드를 대조한다. 이미 구현된 기능을 다시 만들지 않는다.

작업 시작:
1. git status --short, git diff, git diff --cached를 확인한다.
   기존 staged/unstaged/untracked 작업을 보존하고 스테이징·커밋·push하지 않는다.
2. 최소 변경 계획과 검증할 동작을 짧게 적는다.
3. 구현 작업이면 수정 전에 .venv\Scripts\python.exe -m pytest -q를 실행한다.
   직전 기준은 481 passed / 2 skipped / 0 xfailed이다.
   실제 시작 결과가 다르면 차이를 기록한다. 범위 밖 실패를 임의로 고치지 않는다.
   정책·요구 정리만 하는 작업이면 테스트 미실시와 그 이유를 보고한다.

구현 규칙:
- 최소 변경. 관련 호출자·Registry·UI·저장·평가 소비자를 찾아 영향 범위를 확인한다.
- 기존 서비스·schema·런타임을 재사용한다. 새 프레임워크·범용 엔진을 만들지 않는다.
- 기능 변경은 회귀 테스트를 먼저 작성한다. 버그 수정은 정상 FAIL로 재현한 뒤 고친다.
  테스트를 약화하거나 xfail/skip으로 미구현 기능을 숨기지 않는다.
- 기본 Mock 모드와 mocks/agents.py는 유지한다. Real 동작은 실제 Agent/서비스와 연결 경로에서 바꾼다.
- Agent는 자기 출력만 반환하며 입력 state를 수정하지 않는다.
  로그·오류·case_status·retry_count는 기존 Wrapper/Graph가 관리한다.
- UI는 기존 runtime 경로를 사용한다. Agent/LLM 직접 호출과 state/confidence 직접 수정은 금지한다.
- 사람 수정, HUMAN/locked, orphaned 수정값, 승인 전 저장 없음, 저장 멱등성을 유지한다.
- schema·CONTRACTS·Graph 구조 변경이 필요하면 구체적인 입력/출력 예시,
  기존 작업 복원 영향과 소비자를 정리한다. 미합의 계약을 임의로 확대하지 않는다.
- 새 패키지는 추가하지 않는 방식부터 찾는다. 불가피하면 이유·대안·영향을 제시하고 확인받는다.
- API Key와 모델 설정은 변경하지 않고 키를 읽어 출력하거나 파일에 저장하지 않는다.
- 자동 회귀 테스트의 ONTOPRODUCT_LIVE_LLM은 0으로 설정한다.
  실제 모델 평가가 필요한 작업은 별도 실행으로 구분한다. 문서만 보고 자동 호출하지 않는다.
  사용자의 명시적 실행 요청과 기존 비용·자료 전송 허용 범위 안에서 실행한다.

필수 검증(구현 작업):
$env:ONTOPRODUCT_LIVE_LLM = "0"
.venv\Scripts\python.exe -m pytest <관련 테스트 파일> -q
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check <수정한 Python 파일>
git diff --check

새 테스트 수만큼 passed가 늘어날 수 있다. 예상하지 못한 FAIL/XPASS/skip을 확인한다.
기본 회귀의 live LLM 테스트 2개 skip과 실제 모델 평가의 미실시를 구분한다.
문서에는 현재 구현·테스트 명령·지원 범위·남은 제한을 갱신한다.

보고:
- 변경 파일과 실제 동작의 전후 차이.
- 재현·관련 테스트·전체 테스트·정적 검사의 명령과 결과를 각각 기록.
- 정책 결정, 계약 변경과 복원 호환성, 남은 작업.
- 실제 LLM/화면 확인의 실시 여부, 실패·timeout·미실시 여부.
필수 검증이 실패하거나 실행되지 않았으면 구현 완료라고 보고하지 않는다.
```

## 1A. SHACL 업무 정책 정리 — 03·04·08

```text
목표: SHACL을 등록 검증에 연결하기 위한 구체적인 정책안을 문서로 작성한다.
이 작업에서는 운영 검증·schema·Graph를 변경하지 않는다.

읽을 것:
- docs/team/03_PRODUCT_ONTOLOGY.md의 운영 연결과 검증 한계
- docs/team/04_VALIDATION.md §4·§9, docs/team/08_INTEGRATION.md
- src/ontoproduct/services/rdf_ontology_service.py의 validate_graph/validate_product
- services/ontology_service.py의 validate_semantics
- services/validation_service.py, services/registration_service.py
- agents/validation_agent.py, schemas/validation.py, schemas/ontology.py
- src/ontoproduct/ontology/product_model.yaml의 comparisons 정의
- tests/test_rdf_product_ontology.py, tests/test_registration_idempotency.py
- inputdata/manifest.json·verification.json의 E007·E008·E009·D003 사례

재현: 내경 32 mm·외경 12 mm인 정상 구조의 Bearing 제품을 같은 입력으로 검사한다.
기본 validate_product는 valid=true, validate_semantics는 valid=false인 차이를 기록한다.
정상 12/32, 역전 32/12, 동일 치수 12/12의 SHACL 판정은
기존 test_bearing_dimensions_have_actual_cross_property_constraint를 실행하고 인용한다.
이 테스트를 새로운 재현으로 다시 작성하지 않는다. 사용자 DB를 변경하지 않는다.
inputdata의 실제 문서 사례도 재현 입력으로 쓴다. 새 fixture는 부족할 때만 만든다.
- E008(내경=외경)·E009(내경>외경): 규칙 검증 통과, SHACL 비교 위반(path 빈 값).
- E007(음수 질량): 규칙 검증 attributes.weight RANGE 오류와 SHACL 위반이 함께 발생.
  SHACL path는 업무 field가 아닌 urn:ontoproduct:ontology:mass이고
  message는 "Value does not conform to Shape [...]"인 일반 문구이다.
- D003(필수 출력 충돌): 두 문서를 함께 올리는 필수 충돌 사례.
verification.json의 issue는 작성 당시 기록이다. 현재 코드로 다시 실행한 결과를 근거로 쓴다.

산출물: docs/team/04_SHACL_INTEGRATION_SPEC.md에 아래 결정표와 예시를 적는다.
1. 현재 SHACL 출력은 {valid, issues, report}이고 issue는
   focus_node/path/message/constraint이다. 업무 code/field/severity는 없다.
2. 실제 발생하는 constraint·경로별 기존 ValidationIssue 매핑 후보와 근거.
   베어링 비교처럼 path가 비어 있는 결과의 field 표현도 명시한다.
   E007처럼 path가 있어도 업무 field와 다른 온톨로지 URI(mass ↔ attributes.weight)인
   경우의 대응 기준을 명시한다. 이 대응은 온톨로지 정의에서 얻고 message에서 추측하지 않는다.
   비교 위반의 constraint는 SPARQLConstraintComponent라 비교 규칙을 구분할 수 없다.
   현재 결과에 비교 규칙 식별자가 없어 영어 message가 사실상 구분 수단이라는 한계를 기록한다.
   product_model.yaml의 comparisons(left/right/operator) 정의와 제품 값을 이용해
   비교 위반·업무 field를 대응시키는 안을 매핑 후보로 명시한다.
   일반 SHACL 제약과 비교 제약을 구분하고 영어 message 부분 문자열에만 의존하지 않는다.
3. 기존 규칙 검증과 SHACL 호출 순서, 중복 issue 제거 기준, 안정적인 반환 순서.
   기존 필수 충돌 message와 선택 속성 누락 warning이 어떻게 유지되는지 예시로 확인한다.
   필수 문서 충돌이 MISSING_REQUIRED와 SHACL 필수값 위반으로 두 번 보고되는 경우를
   구체적인 중복 제거 예시로 넣는다. 기존
   test_missing_required_conflict_preserves_candidates_but_fails_shacl과 D003을 근거로 사용한다.
   E007의 RANGE와 SHACL 위반처럼 같은 값을 두 검사가 다른 field 표현으로 보고하는 경우도
   중복 제거 예시로 넣는다.
   같은 필드의 다른 위반까지 지우지 않고 충돌 후보 근거를 보존하는 기준을 정한다.
4. 위반(valid=false)과 검증 엔진 실행 실패(예외)를 구분한다.
   실패를 valid=true 또는 warning으로 숨기지 않는다.
5. Graph의 Real Validation과 RegistrationService의 승인 시 재검증이
   같은 정책을 쓰는 호출 경로·ontology 주입 방식. Mock 지원 범위도 명시한다.
6. 현재 schema/CONTRACTS 안에서 가능한 안을 먼저 제시한다.
   새 code나 출력 필드가 꼭 필요하면 모든 소비자·복원 영향을 별도 표에 적는다.
7. 정상/위반/사람 수정/직접 등록 우회/예외/멱등 저장의 검증 목록.

확정된 계약, 권장안, 아직 선택이 필요한 결정을 구분한다.
공동 정책 판단에 필요한 질문만 정리하며, 모든 구현 선택을 승인 질문으로 만들지 않는다.
완료 기준: 실행 가능한 입력·실제 두 검사 결과·정책표·완료 테스트 조건이 문서에 있다.
SHACL 운영 연결이 완료됐다고 보고하지 않는다.
```

## 1B. SHACL 등록 검증 연결 — 03·04·08

```text
목표: 확정된 SHACL 업무 정책으로 베어링 내경≥외경의 등록을 차단한다.
선행 입력: docs/team/04_SHACL_INTEGRATION_SPEC.md의 확정된 정책.
정책 문서가 없거나 핵심 결정이 미정이면 구현하지 않고 중단·보고한다.
부족한 정책과 필요한 선행 작업 1A를 명시한다. 선택하지 않은 1A를 자동 수행하거나
미정 정책으로 운영 경로를 변경하지 않는다.

읽을 것: 1A의 파일 목록, agents/real_registry.py,
services/workflow_runtime.py, tests/test_real_validation_agent.py,
tests/test_parallel_workflow.py, tests/test_real_registry.py.

작업:
1. 규칙·의미 검증 결과를 결합하는 최소한의 공통 경로를 만든다.
   Graph의 Real ValidationAgent와 RegistrationService가 이를 함께 사용한다.
   한쪽에서만 SHACL을 적용하거나 UI에서만 차단하지 않는다.
2. 기존 ontology와 RDF/SHACL API를 재사용한다. 매 호출마다 불필요한 새 서비스나
   파일을 만들지 않는다. 온톨로지 엔진·Graph 실행 구조는 새로 만들지 않는다.
3. 확정된 issue 매핑·중복 제거·예외 정책을 적용한다.
   원문 근거·충돌 후보·HUMAN/locked 값을 보존한다.
4. 기본 validate_product의 기존 호출 계약과 Mock 지원 범위를 보존한다.
   Real 연결·caption·사용자 문서에는 새 의미 검증의 실제 지원 범위를 반영한다.

먼저 작성할 테스트:
- 정상 Bearing 내경 12 / 외경 32 통과.
- 내경 32 / 외경 12와 내경 12 / 외경 12의 등록 불가.
- inputdata의 E008·E009를 실제 Parser 입력으로 처리해도 같은 위반으로 등록 불가.
- E007의 RANGE와 SHACL 위반은 확정된 정책대로 하나의 업무 field로 보고된다.
- Graph에서 NEEDS_FIX/사람 검토로 이동하며 승인 전 DB·Export 추가 없음.
- 사람이 32/12를 12/32로 수정한 뒤 재검증·승인·DB 1개·JSON 일치.
- RegistrationService에 APPROVE로 직접 전달해도 위반 제품 저장 거부.
- SHACL 예외 시 성공으로 처리되지 않고 기존 오류 경로 사용.
- 필수 충돌의 MISSING_REQUIRED와 같은 SHACL 누락 위반은 확정된 정책대로 중복 제거하고
  충돌 후보를 유지한다. 같은 필드의 독립적인 다른 위반은 보존한다.
- 누락/충돌/선택 warning/단위/수동 수정/병렬 합류/저장 멱등성 유지.

검증: 새 SHACL 연결 테스트, test_real_validation_agent.py,
test_rdf_product_ontology.py, test_parallel_workflow.py,
test_registration_idempotency.py, test_real_registry.py 및 전체 pytest.
완료 기준: UI 경로와 직접 등록 경로가 같은 위반을 차단하고 정상 수정 후 저장된다.
```

## 2. ReviewerAgent와 충돌·중복 판단 — 06

```text
목표: Real 모드의 ReviewerMock을 실제 규칙 기반 ReviewerAgent로 교체한다.
LLM Reviewer는 이번 작업에 추가하지 않는다.

읽을 것: docs/team/06_REVIEWER.md, REVIEW_01_05.md #6,
04_VALIDATION.md §4·§9, 05_DUPLICATE.md, 02_03_IMPLEMENTATION_SPEC.md §7~§10.
코드: mocks/agents.py의 ReviewerMock(읽기만), schemas/review.py,
agents/registry.py의 CONTRACTS, services/evidence_service.py,
agents/real_registry.py, graph/nodes.py와 routing.py.

작업:
1. ReviewerAgent를 BaseAgent/현재 review 계약에 맞춰 구현한다.
   review_result만 반환하며 runtime/Registry의 Real 연결을 갱신한다.
   기본 Mock 모드는 유지한다.
2. 현재 타입·단위·범위 오류, confidence, 재매핑·수동 보호 정책을 유지한다.
3. 필수 속성의 충돌은 evidence_service.is_conflict로 판별한다.
   충돌만 남았으면 같은 문서를 다시 추출하지 않고 NEEDS_FIX와 구체적인 reason을 반환한다.
   일반 누락/낮은 confidence와 충돌이 함께 있을 때의 우선순위·retry_fields를 먼저 명시한다.
   충돌을 retry_fields에 넣지 않고 실제로 유효하게 수정된 값을 다시 충돌로 취급하지 않는다.
4. locked/HUMAN 보호는 재추출 제외이지 null·충돌을 유효하다고 승인하는 규칙이 아니다.
   validation=false면 can_register=true가 되지 않게 한다.
5. LIKELY_DUPLICATE/POSSIBLE_DUPLICATE의 제품명·판정·근거를 reason에 반영한다.
   score는 확률이 아니며 자동 저장·삭제·거절의 근거로 단독 사용하지 않는다.
6. Graph의 retry_count·상한·최종 승인 검사는 그대로 사용한다.
   입력 계약에 없는 원문 전체·retry_count·error_events를 읽지 않는다.
7. 1B가 적용된 상태에서는 값이 모두 있어도 내경≥외경 같은 관계 검증 오류가 발생한다.
   이 오류가 RE_EXTRACT나 REMAP으로 새지 않고 NEEDS_FIX가 되는 우선순위를 명시한다.
   관계 오류와 일반 누락/낮은 confidence가 함께 있을 때도 승인 차단과 처리 순서를 정한다.

테스트: 충돌만 있는 제품의 불필요한 추가 추출 0회, 충돌+일반 누락,
수동 충돌 해결, HUMAN/locked/null 보호, 낮은 분류 confidence,
중복 두 verdict의 reason, validation 오류의 승인 차단, 계약/입력 불변성,
Real metadata, Mock 유지, 승인 전 DB 저장 없음.
SHACL 관계 오류가 있는 완전한 제품 및 낮은 속성/분류 confidence를 동반한 제품은
NEEDS_FIX로 이동하고 불필요한 재추출·재매핑이 실행되지 않는지 확인한다.
아직 1B가 적용되지 않았다면 04_SHACL_INTEGRATION_SPEC.md에 정한 관계 검증 issue의
code·field 형태를 고정 입력으로 단위 테스트하고, 1B와의 통합 검증 미실시를 따로 보고한다.
1A 정책 문서도 없으면 가정한 code·field를 테스트와 보고서에 명시하고
1A 확정 후 다시 맞춰야 하는 항목으로 남긴다.

검증: 새 tests/test_real_reviewer.py 작성 후 실행하고
test_validation.py, test_workflow.py, test_human_interrupt.py,
test_manual_overrides.py, test_real_registry.py, test_review_01_05.py 및 전체 pytest.
완료 기준: 충돌은 사람 수정으로 이동하고 중복 근거가 설명되며 기존 승인 보호가 유지된다.
```

## 3a. 오프라인 평가 경로 — 09·02·03·04

```text
목표: 기존 Mock 평가와 inputdata 자료를 재사용해 오프라인 평가 경로를 구축한다.
실제 LLM은 호출하지 않는다. 실모델 실행은 별도 작업 3b이다.

읽을 것: docs/team/09_EVALUATION.md, docs/DEVELOPER_GUIDE.md의 평가,
eval/README.md, inputdata/README.md·manifest.json·verification.json,
evaluation/runner.py·metrics.py·report.py,
services/document_service.py·workflow_runtime.py·settings.py,
tests/test_evaluation.py·test_real_registry.py·test_live_llm.py.

작업:
1. inputdata에는 합성 50개 사례·80개 TXT/PDF/XLSX 파일과 기존 검증 기록이 있다.
   manifest.json의 product_class, expected_normalized_attributes, expected_outcome을
   평가 정답 후보로 사용하고 원문과 대조해 검수가 안 됐거나 부족한 항목만 보완한다.
   자료를 처음부터 새로 만들거나 기존 파일·기대값을 평가 결과에 맞춰 덮어쓰지 않는다.
   원문 검수 여부·근거를 기록하고, verification.json은 파일 hash와 오프라인 검사 이력으로
   활용한다. 이 기록을 실모델 정확도나 독립적인 정답 검수의 증거로 취급하지 않는다.
   verification.json을 만든 스크립트는 저장소에 없어 다시 실행할 수 없는 기록이다.
   3a의 runner가 첫 재현 도구이며 기존 기록과 차이가 나면 차이를 보고한다.
   기록의 issue message는 작성 당시 코드 기준이다. 예: D003은 "is missing"으로 기록됐지만
   현재 코드는 "has conflicting document values"를 반환한다. message를 기대값으로 쓰지 않는다.
   manifest expected_outcome과 관측 결과의 대응표를 산출물로 먼저 정한다.
   기존 기록은 equivalent_values→valid, optional_conflict·identity_conflict→document_conflict로
   관측하면서 75개 조합이 모두 일치했다고 적었지만 이 대응 규칙은 문서화되지 않았다.
   manifest의 upload_mode에 따라 형식별 대안과 함께 올리는 다중 문서를 구분한다.
   80개 파일이나 서로 다른 제품을 한 등록 작업에 모두 넣지 않는다.
   합성 자료임을 보고서에 표시하고, 필요한 평가 정답 형식으로 최소 변환해 사용한다.
2. 현재 UTF-8 source_text loader로 바이너리를 읽지 않는다.
   DocumentService → FileReference → 실제 registry_factory → WorkflowRuntime을 사용한다.
3. 평가마다 격리된 DB/upload/checkpoint/export와 실행 ID를 사용한다.
   사용자의 runtime DB나 기존 평가 보고서를 덮어쓰지 않는다.
4. 사람 수정 전의 추출·정규화·분류·검증·중복 결과와 오류를 기록한다.
   EDIT/APPROVE 후 결과는 별도 통합 결과이며 자동 추출 정확도에 섞지 않는다.
5. 현재 metric을 재사용한다. 검증의 실제 누락과 충돌은 같은 MISSING_REQUIRED일 수 있으므로
   평가 정답·evidence로 구분하고 정책에 맞는 측정 기준을 문서화한다.
6. 실행 ID·시각·원문/정답 hash·provider/model·프롬프트/Agent 버전·metadata·호출 수·
   오류·지표 분자/분모·실패 사례를 JSON/Markdown에 남긴다. 실패 사례를 분모에서 몰래 빼지 않는다.
7. 기존 adapter/settings를 재사용하고 통신만 고정 응답으로 대체한다.
   고정 응답을 실제 추출 품질의 증거로 삼거나 자격 증명을 새로 저장하지 않는다.

오프라인 테스트:
실제 TXT/PDF/XLSX 파싱 + 통신만 고정 응답으로 대체한 실제 Agent/runtime,
누락·단위·충돌·오류·보고서 모드/해시·격리 DB·사람 수정 전후 구분,
승인 후 DB/JSON·재시도·복원·metadata를 확인한다.
tests/test_real_workflow.py 등 필요한 회귀 파일을 먼저 작성하고
test_evaluation.py, test_real_registry.py, test_phase3_integration.py 및 전체 pytest를 실행한다.
manifest의 형식 선택/다중 문서 그룹화, 기존 기대값 변환, expected_outcome 대응표,
verification의 hash 불일치,
필수·선택·제품명 충돌과 일반 누락의 구분도 테스트한다.

완료 기준: 기존 자료와 검수 기록을 재사용한 격리 평가·보고서 경로가
실제 Parser/Agent/runtime과 고정 통신 응답으로 재현되고 회귀 테스트가 통과한다.
오프라인 평가 경로 완료와 실제 모델 평가 미실시를 구분해 보고한다.
```

## 3b. 실모델 평가 실행 — 09·02·03·04

```text
목표: 3a의 평가 경로로 승인된 자료·모델 범위의 실제 출력을 측정한다.
선행: 3a 구현·오프라인 검증 완료, 사용자의 실제 모델 실행 승인.
선행이 충족되지 않으면 실제 호출하지 않고 부족한 조건을 보고한다.

읽을 것: 작업 3a의 자료·검수 기록·실행 도구와 보고서,
docs/team/09_EVALUATION.md, inputdata/README.md·manifest.json·verification.json,
기존 adapter/settings와 tests/test_live_llm.py.

작업:
1. 사용할 사례·파일·모델, 자료 전송 허용 범위, 비용/호출 수/시간 한도를 정리해
   사용자에게 실행 승인을 받는다. 이미 명시적으로 승인된 동일 범위는 다시 묻지 않는다.
   답을 받기 전에는 실행 준비·오프라인 점검만 진행한다.
2. 3a에서 검수한 정답과 업로드 그룹을 사용하고 기존 adapter로 실제 호출한다.
   사용자 DB와 기존 보고서를 보존하며 별도 실행 ID·격리 runtime을 사용한다.
3. 실제 출력·hash·provider/model·버전·호출 수·시간·실패와 지표 분자/분모를 남긴다.
   입력 합성 자료라는 사실과 고정 응답 회귀 결과를 실제 모델 결과와 구분한다.
4. 한도에 도달하면 추가 호출을 중단하고 완료/실패/미실행 사례를 각각 기록한다.
   실패나 승인되지 않은 사례를 몰래 제외해 정확도를 높이지 않는다.

완료 기준: 승인 범위의 실제 출력·지표·실패 사례가 별도 보고서로 재현 가능하다.
일부 실행·timeout·한도 중단·승인 미확보는 그대로 보고하며 전체 평가 완료라고 하지 않는다.
```

## 4. 결정적 오류의 수동 해결 경로 — 02·03·08

```text
목표: 동일 입력의 선택 속성/제품명 충돌을 RETRY/STOP만 반복하지 않고 해결할 수 있게 한다.
이 항목은 Graph/명령/업로드 변경에 대한 계약 설계를 먼저 수행한다.

읽을 것: docs/team/02_03_IMPLEMENTATION_SPEC.md §7·§10,
04_VALIDATION.md §9, 08_INTEGRATION.md, schemas/error.py·human_review.py,
graph/execution.py·nodes.py, services/workflow_runtime.py·document_service.py,
views/registration.py, tests/test_error_handler.py·test_real_document_graph.py.

먼저 재현: inputdata의 D004(선택 질량 충돌)와 D005(제품명 충돌)를 재현 입력으로 쓴다.
두 사례는 verification.json에 document_conflict로 기록되어 있다. 부족할 때만 새 fixture를 만든다.
RETRY 후 같은 오류, STOP 종료를 확인한다. 네트워크 일시 실패와 구분한다.

설계 산출물: docs/team/08_ERROR_RESOLUTION_SPEC.md.
- 오류별 재시도 가능성 판정과 기존 오류 이력 보존.
- 수정된 문서로 새 작업을 시작하는 최소한의 경로와 기존 작업을 직접 수정하는 경로 비교.
- 원본·case ID·수동 수정·잠금·checkpoint·DB·Export에 대한 전후 예시.
- 새 명령/Graph 경로가 필요한 경우 모든 소비자와 이전 checkpoint 복원 영향.
  최소 요구를 만족하는 기존 runtime 경로가 있으면 그것을 우선한다.
- 확정된 정책과 미정 결정을 구분한다. 계약 확정 전 새 action을 임의로 추가하지 않는다.

확정된 설계의 구현 단계:
원문 후보를 보존한 채 자료 교체 또는 합의된 수동 수정으로 해결한다.
HUMAN/locked를 조용히 삭제하지 않고, 미해결 충돌을 단순 잠금으로 통과시키지 않는다.
원본 작업에서 저장이 이뤄졌을 가능성이 있으면 등록 멱등성을 보존한다.

테스트: 선택/제품명 충돌 해결, 변하지 않은 입력의 반복 실패,
일시 실패의 기존 RETRY, STOP, 사용자 작업 복원, 경로 검증,
승인 전 저장 없음, HUMAN/locked 보호, Export 재시도 중복 없음.
계약 검토만 끝났으면 설계 완료로 보고하고 기능 구현 완료와 구분한다.
```

## 5. confidence 프롬프트·기준 평가 — 02·03·06

```text
목표: 점수를 임의로 올리지 않고 confidence 안내 개선의 효과를 평가한다.
선행: 3a의 오프라인 평가 기반 또는 같은 수준의 재현 가능한 비교 도구.
실제 효과 비교는 3b의 승인된 실행 범위에서 수행한다.

읽을 것: docs/team/02_03_IMPLEMENTATION_SPEC.md §8·§9,
02_EXTRACTION.md, 06_REVIEWER.md, REVIEW_01_05.md #1,
prompts/extraction.py·ontology.py, services/evidence_service.py,
tests/test_real_extraction.py·test_real_ontology_agent.py·test_review_01_05.py.

작업:
1. 현재 optional confidence 안내와 null/낮은 점수의 발생·재시도·사람 확인을 기준으로 기록한다.
2. 근거가 검증된 비-null 값에 모델의 유효한 자기평가 점수를 요청하는 최소 변경안을 만든다.
   값 누락/충돌은 null, 제공되지 않은 점수도 null로 유지한다.
   고정 점수나 범위를 벗어난 점수의 보정으로 불확실성을 숨기지 않는다.
3. 프롬프트를 변경하면 VERSION을 올리고 평가 보고서에 이전/새 버전을 기록한다.
4. 같은 문서·정답·모델·설정·허용 호출 범위로 비교한다.
   null 비율·추출 정확도·재시도 수·호출 수·사람 확인 대상을 함께 비교한다.
   null이 줄었다는 사실만으로 정확도가 개선됐다고 결론 내리지 않는다.
5. 현재 0.70 기준은 별도 평가 근거 없이 변경하지 않는다.
   점수는 보정된 정답 확률이 아니고 높은 점수로 근거 검증 실패를 통과시키지 않는다.

테스트: 점수 누락/null 유지, 누락값·충돌의 null, 잘못된 점수 거부,
동일 후보 병합의 최솟값/점수 누락 정책, 잠긴 값 재추출 제외,
같은 값/분류를 사람이 확인하는 기존 UI 경로 유지.
관련 실제 Extraction/Ontology 테스트와 test_review_01_05.py, 전체 pytest 실행.
실제 모델 비교가 미실시이면 프롬프트 효과는 미검증이라고 보고한다.
```

## 6. OCR 요구 확인 — 01

```text
작업 성격: 질문 목록을 만들어 사용자에게 확인받는 작업이다.
목표: 스캔 PDF OCR이 필요한지 확인하고 최소 지원 명세를 작성한다.
현재 OCR은 미지원이다. 요구 확인 단계에서는 패키지 설치나 외부 OCR 전송을 하지 않는다.
01_PARSER.md와 parser_service.py, test_real_parser.py를 읽는다.
대표 스캔·혼합 PDF, 한글/영문, 해상도, 페이지 수, 처리 시간, 자료 전송 허용 범위를 확인한다.
이미 제공된 답은 재사용하고, 없는 답을 가정으로 채우지 않는다.
답변 전에는 기존 지원·도구 조사를 진행하고 미정 요구를 남긴다. 명세는 확인된 요구만 확정한다.
확인된 대표 자료가 없으면 그 제약을 기록하고 정확도 수치를 만들지 않는다.
기존 설치된 도구의 가능 범위를 먼저 확인하고 새 의존성·라이선스·비용이 필요하면 대안을 제시한다.
page/source_file/evidence 보존, 텍스트 PDF의 기존 출력 유지,
OCR 실패·낮은 인식 품질을 숨기지 않는 정책과 수용 테스트를 명세에 적는다.
명세와 의존성·자료 처리 범위가 확정된 뒤 구현·실제 자료 검증 작업을 별도로 수행한다.
```

## 7. 대규모 중복 조회 요구·성능 확인 — 05·08

```text
작업 성격: 질문 목록을 만들어 사용자에게 확인받는 작업이다.
목표: 실제 데이터 규모에서 병목을 측정하고 최소한의 검색 개선안을 작성한다.
05_DUPLICATE.md, duplicate_service.py, product_repository.py,
test_real_duplicate_agent.py를 읽는다.
목표 제품 수·동시 요청·응답 시간·메모리 한도를 확인한다.
이미 제공된 답은 재사용하고, 없는 목표를 가정으로 확정하지 않는다.
답변 전의 측정은 예비 조사로 표시하고 합성 DB의 크기·측정 환경을 명시한다.
격리된 합성 DB에서 현재 같은 분류 전체 조회와 비교의 시간·메모리를 측정한다.
측정 전 벡터 DB·임베딩·새 검색 엔진을 추가하지 않는다.
기존 SQLite 인덱스/조회 개선으로 가능한 안부터 비교한다.
현재 verdict·핵심 사양 충돌·누락·top_k·동률 product_id 순서·DB 실제 ID 검증을 유지한다.
후보를 제한하는 안이면 누락되는 정답과 Precision/Recall 변화를 측정한다.
목표가 현재 구현으로 충족되면 추가 구현 불필요로 보고한다.
개선 구현은 확정된 규모/기준과 회귀·성능 테스트를 바탕으로 수행한다.
```

## 8. RDF 저장 필요성·일관성 정책 확인 — 03·07·08

```text
작업 성격: 질문 목록을 만들어 사용자에게 확인받는 작업이다.
목표: 필요할 때 제품 JSON에서 생성하는 현재 RDF 방식으로 요구가 충족되는지 검토한다.
03_PRODUCT_ONTOLOGY.md, 07_REGISTRATION.md, rdf_ontology_service.py,
registration_service.py, tests/test_rdf_product_ontology.py를 읽는다.
저장 요구가 다운로드/단일 제품 시각화인지, 지속적인 제품 간 RDF 질의인지 확인한다.
이미 제공된 답은 재사용하고, 없는 요구를 가정으로 채우지 않는다.
답변 전에는 기존 방식과 대안을 조사하고 미정 요구를 기록한다. 새 저장소를 구축하지 않는다.
현재 방식으로 충족되면 새 DB를 추가하지 않는다.
지속 저장이 필요하면 JSON의 기준 데이터 역할, product/case ID,
RDF 생성 버전·갱신·삭제·재생성, 기존 데이터 이관을 명세에 적는다.
SQLite 저장 성공 후 RDF 실패와 그 역순의 일관성·재시도·복구 정책을 구체적인 사례로 작성한다.
사용자 DB를 직접 이관하거나 외부 저장소에 제품 자료를 전송하지 않는다.
목표·저장 기술·의존성·운영 범위가 확정된 뒤 격리 DB에서 구현을 검증한다.
기존 승인·멱등성·Export 복구·원문 근거 보존을 수용 테스트에 포함한다.
```
