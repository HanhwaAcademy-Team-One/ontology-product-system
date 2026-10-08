# 04 후속 작업 순차 실행 기록

기준일: 2026-10-09. 사용자의 순차 실행 요청에 따라 기존 프롬프트 수정은 보존하고 한 단계씩 진행했다. 이후 사용자가 작업 5의 실모델 검증을 요청해 두 프롬프트에서 실제 모델을 비교했다. 스테이징·커밋·push, 새 패키지 설치는 하지 않았다. schema·CONTRACTS·새 Graph action도 추가하지 않았다.

## 단계별 상태

| 작업 | 상태 | 결과 / 남은 조건 |
| --- | --- | --- |
| 1A | 정책 작성·재현 완료 | [SHACL 정책](04_SHACL_INTEGRATION_SPEC.md). URI·빈 path 비교·중복·실패·공통 호출 경로를 정했다. |
| 1B | 구현·회귀 완료 | Real Validation과 직접 승인 등록이 공통 규칙·SHACL을 실행. E008/E009 차단, 수정 후 DB/JSON 1개, 엔진 예외 시 저장 없음. |
| 2 | 구현·회귀 완료 | Real ReviewerAgent. 필수 충돌/관계 오류는 confidence보다 먼저 NEEDS_FIX. D003 추가 추출 0회. 중복 근거는 사람 판단에 제공. Mock 유지. |
| 3a | 오프라인 구현·평가 완료 | TXT/PDF/XLSX 80파일의 75 업로드 조합. 기대 오류 유형 75/75 일치. 원문/정답 hash·버전·실패·분모·원문 근거 기록. |
| 3b | 작업 5 범위의 대표 실모델 실행 완료 | 사용자 요청으로 대표 TXT 4개를 두 버전에서 실제 gpt-5로 비교, 총 16 service call 성공. 전체 75개 실모델 평가는 미실시. |
| 4 | 정책·구현·회귀 완료 | [오류 해결 명세](08_ERROR_RESOLUTION_SPEC.md). 선택/제품명 충돌 RETRY 차단, STOP 후 정정 문서의 새 작업. 구형 checkpoint·UI·일시 실패·멱등성 확인. |
| 5 | 대표 실모델 비교 완료, 개선 효과 확인 못함 | 2.0.0 → 2.1.0 비교에서 confidence null 0/12 → 2/11, 정상 값·단위 정확도 동일. 두 버전 모두 오류 2건을 상위 분류로 선택해 SHACL 판정을 놓침. 후속 보완 필요. |
| 6 | 기존 지원 조사·질문 작성 완료 | OCR 대표 자료·언어·페이지·시간·전송 허용 요구 확인 대기. 설치/외부 전송 없음. |
| 7 | 예비 측정·질문 작성 완료 | 격리 합성 100/1,000/5,000개 단일 조회 측정. 목표 규모·동시 요청·SLA 확인 대기. 검색 알고리즘 변경 없음. |
| 8 | 기존 방식 조사·질문 작성 완료 | JSON에서 필요 시 RDF 생성하는 현재 방식 확인. 제품 간 지속 질의·갱신/삭제·운영 제약 확인 대기. 저장소/이관 없음. |

6~8의 질문과 예비 근거는 [요구 확인 기록](04_REQUIREMENTS_06_08.md)에 있다. 미정 답을 가정으로 확정하지 않았다.

## 재현과 보존

실제 Parser·고정 참조 응답·Ontology로 E007/E008/E009/D003을 다시 처리한 [원본 재현 JSON](../../eval/shacl_reproduction.json)을 남겼다. E007·D003은 규칙/SHACL 모두 false, E008·E009는 규칙 true / SHACL false였다. 공통 결합 결과와 원본 두 검사 결과를 구분해 보존했다.

- 기존 `test_bearing_dimensions_have_actual_cross_property_constraint`의 12/32 통과, 32/12·12/12 실패를 재사용했다. 직접 승인 우회는 새 테스트에서 수정 전 두 조합 모두 저장되는 FAIL로 재현했다.
- 실제 E008/E009 문서의 Parser → Extraction → Ontology → Validation → Reviewer → 수정 → 승인 → DB/JSON 흐름은 `test_shacl_registration.py`로 검증했다.
- E007은 현재 실행에서 `attributes.weight/RANGE` 하나로 안내한다. 과거 SHACL의 mass URI와 하위 numericalValue focus node를 모델·제품 RDF URI로 대응시키며, message 부분 문자열로 필드를 추측하지 않는다.
- D003은 `MISSING_REQUIRED`의 충돌 메시지와 두 원문 후보를 유지한다. 별도 SHACL 누락 중복을 제거한다. 같은 필드의 설명되지 않는 별도 위반은 CLASS로 유지하는 FAIL→PASS 회귀도 추가했다.
- `test_real_workflow.py`는 실제 D003 추가 추출 0회, HUMAN/null/locked 수정, runtime 재시작 복원, 승인 전 저장 없음과 반복 승인 저장 1회를 검증한다.
- D004/D005 실제 두 문서의 recoverable=True 문제를 FAIL로 재현했다. 수정 후 직접 RETRY 명령도 추가 추출을 하지 않으며 STOP 이력을 유지한다. 정정한 새 case는 별도 승인 후 저장된다.

SHACL 모델이 없는 사용자 정의 ontology는 기존 규칙 전용 동작을 유지한다. 기본 ontology에서 실행 실패/알 수 없는 위반은 등록을 허용하지 않는다. 기존 checkpoint에는 새 필드를 요구하지 않으며 승인 시 현재 정책으로 다시 검사한다.

## 검증 기록

모든 자동 테스트는 `ONTOPRODUCT_LIVE_LLM=0`으로 실행했다.

| 확인 | 결과 |
| --- | --- |
| 시작 전체 `python -m pytest -q` | 481 passed / 2 skipped |
| 1B 관련 SHACL/Validation/RDF/병렬/등록/Registry | 75 passed |
| 1B 전체 | 489 passed / 2 skipped |
| 2 관련 Reviewer/Validation/Graph/Human/수동/Registry/기존 검토/SHACL | 82 passed |
| 2 전체 | 500 passed / 2 skipped |
| 3a 관련 Real workflow/기존 evaluation/Registry/phase3 | 27 passed |
| 3a 전체 | 505 passed / 2 skipped |
| 호출 한도 포함 오류 해결 관련 | 35 passed |
| 4 전체 | 511 passed / 2 skipped |
| 같은 필드 독립 SHACL 보존 관련 | 38 passed |
| confidence 안내 변경 전 기존 회귀 | 82 passed |
| confidence 지표·안내 변경 후 관련 | 89 passed |

최종 전체 `.venv\Scripts\python.exe -m pytest -q`는 **513 passed / 2 skipped / 0 xfailed**, 53.57초였다. 수정·신규 Python 18개 파일의 `.venv\Scripts\python.exe -m ruff check <파일 목록>`과 `git diff --check`가 통과했다. 새 문서의 링크·코드 블록·공백도 확인했다. skip은 기존 live 테스트 2개이다. 기존 rdflib JSON-LD DeprecationWarning 1개는 유지한다. Streamlit AppTest는 실행했고, 실제 브라우저 수동 조작·외부 LLM·대표 스캔 OCR 확인은 하지 않았다.

## 오프라인 평가와 실제 모델의 구분

첫 오프라인 기록은 `eval/document_reports/468a534f-bd12-47f5-a0d1-b0ed02b22502/`에 있다. 프롬프트 2.0.0 기준 ReferenceLlm service call은 163회이며 실제 외부 요청은 0회다. 정규화 정답 후보가 있는 조합은 62개(244속성), 없는 오류 조합은 13개다. 정규화 지표는 후보 정답이 있는 조합만 대상으로 하고, 알려진 정답이 있는 실행 실패는 오답으로 분모에 남긴다. 오류 유형의 대응 지표는 75개 전체다.

`equivalent_values → valid`, `optional_conflict/identity_conflict → document_conflict`를 명시적인 대응표로 사용한다. 과거 verification의 issue message를 기대값으로 쓰지 않는다. 원문 SHA-256 불일치는 실행 전에 거부한다. 합성 자료의 lexical 근거 확인과 독립 사람 정답 검수는 구분하며, 사람이 검수했다거나 실제 추출 품질 100%라고 보고하지 않는다. 중복 relevance 정답은 없으므로 중복 Precision/Recall도 만들지 않는다.

JSON·Markdown에는 provider/model, prompt/Agent 버전, 호출 수, hash, 원문·출력·실패·분자/분모를 남긴다. 사람 수정 결과는 자동 추출 지표와 섞지 않고 회귀 통합 결과로 검증한다. 평가마다 임시 DB/upload/checkpoint/export를 생성하고 닫은 후 제거한다. 보고서는 새 실행 ID 폴더에 남겨 기존 실행을 덮어쓰지 않는다.

## confidence 비교의 한계와 후속 실행

최종 2.1.0 오프라인 실행도 기대 오류 유형 **75/75** 일치였다. [최신 JSON](../../eval/document_reports/0f93c903-f05b-4676-9afb-0a66af190558/evaluation.json) · [최신 Markdown](../../eval/document_reports/0f93c903-f05b-4676-9afb-0a66af190558/evaluation.md)에 confidence·사람 수정 필요 지표, 버전, 사례별 실패·오류를 함께 기록했다. 고정 응답이 지침을 읽고 점수를 바꾸는 모델은 아니므로 두 오프라인 실행의 일치를 프롬프트 효과로 해석하지 않는다.

새 지표 `AI Confidence Null Rate`는 실제 관측된 non-null normalized AI 속성 중 confidence=null인 비율이다. 미추출 속성은 이 점수 전용 분모에 없고 별도의 값 정확도에서 오답이다. `Human Repair Case Rate`, sample별 두 retry count, service call count도 기록한다. null 점수 15개를 입력한 회귀에서 15/15 null·NEEDS_FIX를 유지하고 값 정확도를 별도로 계산하는 것을 검증했다.

초기에는 실모델 비교를 승인 대기로 남겼다. 이후 사용자의 “5번 실모델 검증해주고” 요청에 따라 같은 TXT·정답 후보·model/settings·한도로 2.0.0과 2.1.0을 각각 실행했다. 결과와 한계는 아래에 기록한다.

## 작업 5 실모델 결과 — 2026-10-09

[비교 보고서](../../eval/confidence_reports/20261009-0b4fe5df-6275-4095-aa12-3299b56c37d8/comparison.md) · [비교 JSON](../../eval/confidence_reports/20261009-0b4fe5df-6275-4095-aa12-3299b56c37d8/comparison.json).

OpenAI gpt-5로 M001/B001/E008/E009 TXT를 각 버전 1회씩 비교했다. 각 실행 최대 8 service call·600초, 실제 호출 총 16/16 성공이다. 두 실행 모두 임시 DB의 저장 제품은 0개다. 기존 커밋의 이전 프롬프트를 AST로 읽고 평가 프로세스 메모리에서만 교체해 Agent 버전·호출 프롬프트 버전을 일치시켰다. 소스 프롬프트·모델 설정·0.70 기준은 바꾸지 않았다.

| 지표 | 2.0.0 | 2.1.0 |
| --- | ---: | ---: |
| 관측 AI confidence null | 0/12 | 2/11 |
| 공통 원문 11개 속성 confidence null | 0/11 | 2/11 |
| 정상 2건의 값·단위 | 7/7 · 6/6 | 7/7 · 6/6 |
| 전체 분류·기대 오류 유형 일치 | 2/4 · 2/4 | 2/4 · 2/4 |
| NEEDS_FIX | 2/4 | 2/4 |
| 자동 재시도 Extraction/Ontology | 0/0 | 0/0 |
| 실행 시간 | 115.50초 | 113.31초 |

confidence 누락 감소나 품질 개선 효과는 확인하지 못했다. 자동 재시도를 동일하게 껐으므로 재시도 감소 효과도 판단할 수 없다. 합성 4건·각 버전 1회라 일반적인 악화나 전체 업무 정확도를 확정하는 결과는 아니다. 정상 2건의 7속성만 정규화 정답 후보가 있으며 오류 2건은 값·단위 지표에서 제외된다. 분류·기대 오류 유형은 4건 전체로 비교했다. HTTP 내부 재시도·토큰·비용은 별도 수집하지 않았다.

**추가 발견:** 두 버전 모두 E008/E009의 candidate_class=Bearing을 Ontology에서 MechanicalPart로 바꿨다. 따라서 Bearing SHACL 관계 규칙이 적용되지 않아 Validation은 valid=true였고, 낮은 분류 confidence로 NEEDS_FIX·can_register=false에 멈췄다. 이를 올바른 오류 검출 성공으로 보고하지 않는다. 2.1.0은 E009의 두 치수 confidence를 null로 반환했다. 원문 전사 확신과 의미적 유효성·문서 간 충돌을 구분하는 안내 보완, 상위 분류로 검증을 놓치는 경로의 회귀 테스트·분류 일관성 보완이 남았다. 이는 6~8의 기능 확장보다 먼저 검토할 항목이다.

관련 confidence·근거·Ontology·Reviewer 회귀 테스트는 **94 passed**, `git diff --check`는 통과했다. 이번 검증은 기능 코드를 변경하지 않았으며 앞선 전체 513 passed / 2 skipped 결과와 구분한다.
