# REVIEW_01_05 구현 프롬프트

[검토 문서](REVIEW_01_05.md)의 항목을 구현할 때 Claude Code 세션이나 팀원에게 그대로 전달하는 지시문입니다. 아래 코드 블록 전체를 붙여넣으세요.

```text
역할: D:\ontology-product-system 저장소에서 docs/team/REVIEW_01_05.md 의 항목 #1~#5를 구현한다.
규칙은 저장소의 CLAUDE.md/AGENTS.md를 따른다. (최소 변경, 기능을 바꾸면 테스트 통과 후 완료 보고, 새 패키지 금지)

## 먼저 읽을 것
- docs/team/REVIEW_01_05.md : 문제 재현, 원인, 해결 목업(코드·화면). 이것이 설계 근거다.
- tests/test_review_01_05.py : 이미 작성된 검증 테스트. 통과 3개, xfail(strict) 6개.
- docs/team/00_COMMON.md, 02_03_IMPLEMENTATION_SPEC.md §7~§9 : 변경하면 안 되는 계약.

## 작업 전 확인
- 저장소 루트에서 `git status --short`, `git diff`, `git diff --cached`를 확인한다.
  staged·unstaged·untracked 기존 작업을 보존하고, 관련 줄만 수정한다. 스테이징과 커밋은 하지 않는다.
- 수정 전에 회귀 파일과 전체 pytest를 실행해 실제 시작 결과를 기록한다. 아래 시작 수치는 참고값이다.
  기준과 다르면 차이를 확인하고 기록한다. 범위 밖의 기존 실패를 임의로 수정하지 않는다.
- 이 작업의 회귀 테스트에서는 실제 LLM을 호출하지 않는다. 테스트 실행 환경의
  ONTOPRODUCT_LIVE_LLM은 1이 아니어야 한다. API Key·모델 설정은 변경하지 않는다.

## 완료 기준 (필수. 하나라도 실패하거나 실행하지 못하면 완료로 보고하지 않는다)
1. `.venv\Scripts\python.exe -m pytest tests\test_review_01_05.py -q` 결과가 **9 passed, 0 xfailed** 이다.
   - 항목 수정 후 해당 테스트 하나를 선택해 실행하고 XPASS(strict)인지 확인한다.
     일반 FAIL이나 XFAIL은 해결 확인이 아니다. XPASS 확인 후 해당 @pytest.mark.xfail 표시만 제거한다.
   - 표시 제거 후 회귀 파일과 전체 pytest가 통과해야 다음 항목으로 진행한다.
   - tests/test_review_01_05.py 의 테스트 본문(assert, 픽스처, 문구)은 수정하지 않는다. 아직 수정하지 않은 항목의 xfail은 중간 단계에서만 허용한다.
2. `.venv\Scripts\python.exe -m pytest -q` 전체 통과. skip 은 기존 live 테스트 2개만 허용한다.
   시작 기준은 463 passed / 2 skipped / 6 xfailed 이고, 완료 시 xfailed 는 0 이어야 한다.
3. 전역 python 이 아니라 .venv 의 python 으로 실행한다.

## 선택 검증
- `AGENT_MODE=mock` 으로 앱을 실행해 #1·#3 체크박스와 #2A 충돌 표를 화면에서 확인하는 것은 선택이다.
- 하지 않았으면 보고에 "화면 수동 확인 미실시"라고 쓴다. 선택 검증을 하지 않아도 필수 기준을 만족하면 완료로 볼 수 있다.

## 작업 순서 (한 항목씩 끝내고 전체 테스트를 돌린 뒤 다음으로)
1. #4 agents/real_registry.py : ValidationAgent() 를 replace=True 로 등록.
   이 변경으로 기존 테스트 3곳의 기대값이 바뀐다. 아래만 수정한다. 이 파일의 다른 검증은 그대로 둔다.
   - tests/test_real_registry.py 의 test_document_registry_replaces_only_document_slots
     (`modes == {...}`): "validation": True → False.
   - tests/test_real_registry.py 의 test_runtime_runs_real_documents_to_human_review_without_saving
     (~line 147, 실제 Agent 목록): "ontology" 와 "duplicate" 사이에 "validation" 추가.
     결과는 ["parser", "extraction", "ontology", "validation", "duplicate", "registration"] 이다(registry 등록 순서).
   - tests/test_real_registry.py 의 test_real_mode_with_injected_llm_processes_uploads
     (~line 204, 모니터 모드 표): `(modes["validation"], modes["reviewer"]) == ("Mock", "Mock")`
     → ("Real", "Mock"). 또한 parser·extraction·ontology 만 비교하던 dict 는 그대로 둔다.
   상태 설명 갱신(아래 '상태 안내' 참고)도 이 단계에서 한다.
2. #5 services/workflow_runtime.py : Registration·Duplicate 등록을 하나의 메서드로 묶어
   graph() 와 agent_metadata() 가 같은 코드를 쓰게 한다. DuplicateService 에는 항상 self.ontology 를 넘긴다.
   공통 메서드는 기존 factory 호출과 두 Agent 등록만 담당한다. graph()의 캐시·잠금과
   agent_metadata(thread_id)의 기존 동작은 유지한다. 인자 없는 metadata 조회는 기존 "metadata"
   식별자를 사용하며 작업 생성·Graph 실행·제품 등록을 하지 않는다.
3. #2B services/validation_service.py : 충돌 속성(evidence_service.is_conflict)이면 MISSING_REQUIRED 의
   message 만 "...has conflicting document values" 로 바꾼다. code·severity·schema 는 그대로 둔다.
   실제 누락은 기존 "is missing" 메시지를 유지한다. 선택 속성 메시지와 검증 정책은 바꾸지 않는다.
4. #1 views/registration.py _edit_form : review_result.retry_fields 에 있는 항목에 label 에 "AI 값 확인"을
   포함한 체크박스를 추가하고, 체크된 항목은 값이 같아도 edits 에 포함한다.
   체크박스는 기존 값이 None이 아닌 항목에만 표시한다. 0과 False도 유효한 확인 대상이다.
   누락·충돌의 None 값을 체크만으로 확인·해결 처리하지 않고, 기존 입력·재검증 경로를 사용한다.
   체크하지 않은 항목은 기존 값 변경 비교를 유지한다. 체크 상태는 작업·revision별로 구분한다.
   NEEDS_FIX 에 "AI 신뢰도가 낮거나 없는 항목" 안내 문구를 함께 표시한다.
5. #3 views/registration.py _edit_form : product_class 가 locked_fields 에 없을 때 label 에 "AI 분류 확정"을
   포함한 체크박스를 추가하고, 체크되면 선택 분류가 현재와 같아도 changed_class 로 보낸다.
   체크하지 않았을 때의 기존 분류 변경·재검증 동작은 유지한다. ProductState·confidence를
   UI에서 직접 수정하지 않고 기존 EDIT payload와 runtime.resume 경로로 전달한다.
6. #2A views/registration.py _review : normalized_product 의 충돌 속성마다 후보(값·단위·출처·페이지·근거)를
   표로 보여주고 st.error 로 안내한다. evidence_candidates/is_conflict 를 재사용한다.
   표에는 후보의 evidence 원문("Rated Voltage: 24 V")이 그대로 들어가야 한다.
   후보를 자동 선택하거나 요약·단위 변환해 원문 근거를 바꾸지 않는다. 화면 표시는 state를 수정하지 않는다.

## 단계별 필수 검증
대상 테스트 이름은 모두 tests/test_review_01_05.py 안에 있다.

| 작업 단계 | XPASS 확인 후 표시를 제거할 테스트 | 회귀 파일의 예상 결과 |
| --- | --- | --- |
| 1 (#4) | test_real_registry_runs_real_validation_agent | 4 passed / 5 xfailed |
| 2 (#5) | test_every_duplicate_service_receives_the_runtime_ontology | 5 passed / 4 xfailed |
| 3 (#2B) | test_validation_message_tells_conflict_apart_from_missing | 6 passed / 3 xfailed |
| 4 (#1) | test_ui_confirming_ai_values_releases_needs_fix | 7 passed / 2 xfailed |
| 5 (#3) | test_ui_confirming_ai_class_releases_needs_fix | 8 passed / 1 xfailed |
| 6 (#2A) | test_ui_shows_conflicting_document_values | 9 passed / 0 xfailed |

각 단계에서 다음 순서로 실행한다.
1. `.venv\Scripts\python.exe -m pytest tests\test_review_01_05.py::<대상 테스트 이름> -q`
   로 해당 테스트의 XPASS(strict)를 확인한다. 위 이름으로 치환해 실행한다.
2. 해당 xfail 표시만 제거한 뒤
   `.venv\Scripts\python.exe -m pytest tests\test_review_01_05.py -q`를 실행한다.
3. `.venv\Scripts\python.exe -m pytest -q`를 실행한다.
   중간에는 표에 적힌 미수정 xfail과 기존 live 테스트 2개 skip만 허용한다.
   예상하지 못한 FAIL·XPASS·추가 skip이 있으면 다음 단계로 진행하지 않는다.

최종 단계 후에는 두 pytest 명령이 완료 기준을 만족하는지 확인하고 결과를 기록한다.

## 상태 안내 갱신 (#4 연결에 따른 문구 수정만 허용)
Real 모드에서 Validation 이 Mock 이 아니라 실제 Agent 로 바뀐 사실을 설명하는 문구만 고친다.
기본 Mock 모드는 ValidationMock을 유지한다. 실제 ValidationAgent는 기존 Python 규칙 검증이며
LLM 검증이나 SHACL 자동 연결이 추가되는 것은 아니다. 이 지원 범위를 바꾸어 설명하지 않는다.
로직·구조·다른 설명은 바꾸지 않는다. 그 외 문서 편집은 하지 않는다.
- src/ontoproduct/views/registration.py `_mode_caption` (~line 71): "이후 단계 Mock" →
  Validation 은 실제, Reviewer 는 Mock 임이 드러나게 수정. 단 test 가 찾는 "실제 문서 분석"
  문구는 유지한다(test_real_registry.py 가 caption 에서 이 문구를 검사한다).
- Validation 을 "Mock/기존 Mock 규칙"으로 설명하는 문장:
  docs/QUICK_START.md:112, docs/USER_MANUAL.md:27, docs/SYSTEM_AND_ONTOLOGY.md:7·77·152,
  docs/team/08_INTEGRATION.md:5·86, docs/MOCK_REPLACEMENT_PLAN.md:5·28·32, README.md:37·40.
  Reviewer 에 대한 설명은 그대로 둔다. (QUICK_START.md, USER_MANUAL.md 는 작업 전부터 변경되어 있다.
  git diff 와 git diff --cached 로 기존 변경을 확인하고, 관련 줄만 고쳐 기존 변경을 덮어쓰지 않는다.)
- 줄 번호는 참고용이다. Grep 도구나 `git grep` 으로 현재 위치를 확인한 뒤 수정한다.
- real_registry.py의 기존 "01~03만 교체" docstring도 Validation 연결에 맞춰 문구만 갱신한다.

## 바꾸면 안 되는 것
- graph/*, agents/registry.py(CONTRACTS), schemas/*, ProductState, mocks/agents.py 는 수정하지 않는다.
  (계약 변경이 필요해 보이면 구현하지 말고 이유와 예시를 적어 보고한다.)
- 위 항목 외의 리팩터링, 서식 정리, 기존 코드 개선, 이 범위 밖의 UI 개선은 하지 않는다.
  수정하는 줄만 주변 코드 스타일에 맞춘다.
- #6(ReviewerAgent)과 prompts/extraction.py 의 confidence 지시 변경은 이번 범위가 아니다. 구현하지 않는다.
- 새 패키지를 추가하지 않는다.

## 보고 형식
항목별로 (수정한 파일, 실행한 명령과 결과, 확인하지 못한 것)을 적는다.
각 단계의 XPASS 확인·표시 제거 후 회귀 파일·전체 pytest 결과를 구분해서 기록한다.
시작 결과와 최종 결과의 passed/skipped/xfailed 수, 실패·timeout·미실시 여부를 정확히 적는다.
필수 기준 중 실패하거나 실행하지 못한 것이 있으면 그대로 쓰고 완료라고 하지 않는다.
선택 검증(화면 수동 확인)을 하지 않았다면 미실시라고 쓴다. 커밋은 하지 않는다.
```

## 이 프롬프트의 전제

- 체크박스 label에는 "AI 값 확인", "AI 분류 확정" 문구를 각각 유지합니다. 테스트가 `in` 비교로 찾으므로 이번 작업에서는 테스트 본문이나 이 필수 문구를 바꾸지 않습니다.
- #6과 confidence 프롬프트 지시는 06·02 담당자와 합의가 필요해서 이번 범위에서 뺐습니다.
