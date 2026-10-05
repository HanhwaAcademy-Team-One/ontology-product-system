# PHASE 2 완료 보고서

2026-10-05 · D:\ontology-product-system · Python 3.12.10

## 완료 범위

PHASE 1의 검증된 Graph에 Streamlit Interaction adapter와 SQLite Checkpointer를 연결했습니다. 기존 HITL, retry, validation/duplicate 병렬 join, error_handler 경로를 재사용합니다. PHASE 3은 시작하지 않았습니다.

| 기능 | 구현 |
| --- | --- |
| 명시적 페이지 구성 | st.navigation / st.Page |
| 업로드와 workspace | PDF/XLSX/TXT 원본 저장, 20 MB 제한, UUID 파일명, FileReference |
| 실행 진행 | 실제 custom agent_started/finished 이벤트로 RUNNING/SUCCESS/ERROR 표시 |
| checkpoint | SqliteSaver, thread_id별 workflow, cached resource |
| 사람 검토 | 검증 결과, 중복 후보, 승인/거절 |
| 사람 수정 | ontology 속성 기반 입력, 타입/단위, 분류 변경, orphan 경고 |
| 오류 처리 | 기존 error interrupt의 RETRY/STOP |
| 제품 등록 | SQLite UNIQUE registration_case_id, 반복 등록 시 원본 유지 |
| Export | 제품별 UTF-8 JSON, 임시 파일 후 atomic replace |
| 예제 데이터 | DM-500A, DM-510, MX-500 반복 가능한 seed |
| 저장 확인 | 간단한 제품 검색·상세·JSON 다운로드 화면 |

## 주요 파일

- `app.py`, `src/ontoproduct/app.py`: 실행 진입점, navigation, session/thread 관리, 최근 작업 복원.
- `views/registration.py`: 업로드, 검토·수정, 승인·거절, 오류 재시도·중단, JSON 다운로드.
- `views/streaming.py`: 실제 graph stream 소비 및 Agent 상태 표시.
- `views/product_database.py`: 저장 결과 조회, seed, 검색 및 다운로드.
- `views/resources.py`: st.cache_resource로 runtime 수명 관리.
- `services/workflow_runtime.py`: SQLite checkpointer, graph 재사용, Command resume, 실행 lock.
- `services/document_service.py`: 파일 보관과 FileReference 검증.
- `services/registration_service.py`: 승인·제품 검증, 멱등 저장, JSON Export.
- `repositories/`: 제품 및 작업 catalog persistence.
- `agents/registration_agent.py`, `agents/duplicate_agent.py`: 기존 계약을 따르는 실제 SQLite adapter.
- `services/seed_service.py`, `scripts/seed_database.py`: 중복 검토용 예제 데이터.

새 dependency는 `streamlit==1.64.0`, `langgraph-checkpoint-sqlite==3.1.1`이며 requirements, pyproject, uv.lock을 갱신했습니다.

## Graph 및 계약 유지

workflow.py, routing.py, nodes.py, state.py와 Agent base.py, registry.py의 SHA-256이 PHASE 2 시작 전과 같습니다. 기본 CLI는 기존 Mock Registry와 InMemory Checkpointer를 계속 사용합니다. UI runtime만 SQLite Registration/Duplicate Agent 및 SqliteSaver를 주입합니다.

RegistrationAgent의 고정 required_reads를 확장하지 않았습니다. case_id와 persistence service는 runtime이 생성하는 adapter에 바인딩하며 ProductState에 Connection을 저장하지 않습니다.

UploadedFile을 bytes로 받아 workspace에 저장한 뒤 FileReference만 initial_state에 전달합니다. UI 수정은 HumanCommand를 Command(resume=...)로 전달하여 기존 human_review 경로를 따릅니다. 수동 속성의 HUMAN provenance와 confidence=null, 분류 변경의 orphan 보관을 유지합니다.

## 재개와 멱등성

SQLite checkpoint와 별도 case catalog로 rerun 및 서버 재시작 후 작업을 복원합니다. 같은 runtime에서는 thread별 lock이 동시 실행을 막고, 서로 다른 작업은 독립 state를 사용합니다. 중간에 stream이 끊겨 완료 task의 pending write만 남은 경우도 continue_run으로 이어갑니다.

제품 DB는 registration_case_id UNIQUE 제약을 사용합니다. Export 실패가 DB commit 뒤에 발생하면 graph의 기존 error_handler에서 중단합니다. RETRY는 등록 Agent를 다시 실행하며 기존 제품을 재사용하여 JSON만 복구합니다. 등록 완료 후 반복 승인 요청은 ALREADY_REGISTERED를 반환합니다.

## 검증 결과

실제 Windows 계정 `isaac\eodud`에서 다음 명령을 실행했습니다.

```powershell
.venv\Scripts\python.exe -m pytest -q -W error::pytest.PytestCacheWarning
```

**148 passed in 15.37s**. 기존 PHASE 1 테스트 116개와 PHASE 2 테스트 32개를 포함합니다. 캐시 권한 경고도 발생하지 않았습니다.

검증 범위:

- SQLite connection을 닫고 새 runtime으로 검토·수정·승인 재개.
- 병렬 Validation/Duplicate 오류와 전체 병렬 stage 재시도.
- 반복 승인, 동시 DB 저장, Export 실패 뒤 재시도 시 제품 중복 방지.
- 두 작업 동시 실행의 state와 등록 레코드 격리 및 같은 thread 실행 차단.
- 업로드 workspace/파일명/크기 제한과 ProductState의 JSON 직렬화.
- Streamlit AppTest 7개: 실제 페이지 navigation, 두 파일 업로드, 수정·승인·rerun, 잘못된 숫자, 오류 retry, 최근 작업 복원, 분류 변경과 seed·검색·download.

브라우저에서도 Mock 시작 → 회전수 3000 rpm 수정 → 재검증 → 등록 승인 → SQLite 저장 완료 → DB 상세의 HUMAN provenance와 JSON 다운로드 버튼을 확인했습니다. 로컬 runtime에는 검증용 Mock 제품 1개가 저장되어 있습니다.

compileall과 source distribution / wheel 빌드가 성공했습니다. wheel에 ontology.yaml과 Streamlit app/views가 포함됩니다. source distribution에 runtime이나 .uv-cache 데이터가 포함되지 않는 것을 확인했습니다.

## 실행과 제한

저장소 루트에서:

```powershell
uv --cache-dir .uv-cache sync --locked
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

현재 실행 주소: [http://127.0.0.1:8502](http://127.0.0.1:8502). 기본 저장 경로는 runtime/data, runtime/uploads/{session_id}, runtime/exports입니다.

Parser/Extraction/Ontology/Reviewer는 PHASE 1 Mock입니다. 업로드 원본은 저장하지만 실제 문서 내용 추출이나 LLM 호출은 수행하지 않습니다. UI에 DM-500 예제 추출 모드를 명시했습니다. Duplicate는 SQLite 기존 제품 대상 규칙 엔진이며 의미 검색 정확도를 주장하지 않습니다.

현재 앱은 로컬 교육용으로 인증 없이 최근 작업을 조회합니다. Dashboard, Ontology Explorer, Agent Monitor, Ground Truth, Evaluation Report 및 최종 통합은 PHASE 3의 별도 범위로 남겨 두었습니다.

공식 API 확인 자료: [Streamlit navigation](https://docs.streamlit.io/develop/api-reference/navigation/st.navigation), [cache_resource](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource), [AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest), [SqliteSaver](https://reference.langchain.com/python/langgraph.checkpoint.sqlite/SqliteSaver).
