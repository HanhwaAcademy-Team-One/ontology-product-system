# OntoProduct

Ontology 기반 제조 제품 등록 교육 프로젝트입니다. Python 3.12, Pydantic, LangGraph, Streamlit, SQLite로 **PHASE 1~3 구현 및 통합 검증을 완료**했습니다.

## 실행

저장소 루트에서 실행합니다.

```powershell
uv --cache-dir .uv-cache sync --locked
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

uv 대신 pip를 사용하려면 Python 3.12 환경에서 `python -m pip install -r requirements.txt`를 실행하세요. 의존성과 이 프로젝트 패키지를 함께 설치합니다.

[앱 열기](http://127.0.0.1:8502). 이미 서버가 실행 중이면 링크로 접속하세요. 다른 포트를 쓰려면 실행 명령의 포트 번호를 바꾸세요.

| 화면 | 기능 | 주소 |
| --- | --- | --- |
| 제품 등록 | 업로드, 진행 상황, 검토·수정·승인·거절, 오류 retry | `/` |
| 대시보드 | 전체 DB 집계, 최근 작업 상태와 재시도·오류 이력 | `/dashboard` |
| 제품 데이터베이스 | 이름·분류·등록 구분 검색, 속성·근거·JSON | `/products` |
| 온톨로지 탐색 | 상속도, 속성 정의·단위·범위, 단위 변환 | `/ontology` |
| Agent 모니터 | Registry 메타데이터·계약·Health·실행 시간·오류·compiled graph | `/agents` |
| 평가 | Ground Truth, Mock/규칙 엔진 별도 계산 결과와 보고서 다운로드 | `/evaluation` |

## 등록 데모

1. **Mock 예제로 시작**을 누르거나 PDF/XLSX/TXT 문서를 업로드하고 시작합니다.
2. DM-500의 필수 속도 값이 비어 있어 검토에서 멈춥니다.
3. 제품 정보 수정에서 정격 속도를 `3000 rpm`으로 입력하고 **수정 후 재검증**을 누릅니다.
4. 검증 통과 후 **등록 승인**을 누르면 SQLite 저장과 JSON Export가 실행됩니다.
5. JSON 다운로드 및 제품 데이터베이스 화면에서 결과를 확인합니다.

파일당 최대 20 MB이며 여러 문서를 한 제품의 자료로 업로드할 수 있습니다. 원본 파일은 실제로 보관하지만 **Parser/Extraction은 문서 내용 대신 DM-500 Mock fixture를 사용합니다**. 실제 PDF/Excel 파싱이나 LLM 추출 기능은 구현되지 않았습니다. 화면에도 Mock 모드를 표시하며 API Key는 필요하지 않습니다.

중복 후보는 실제 SQLite 기존 제품의 분류·공통 속성·제품명으로 계산한 규칙 기반 결과입니다. LLM 의미 검색 결과가 아닙니다.

## 저장과 작업 복원

기본 데이터 폴더는 저장소의 `runtime/`입니다. `ONTOPRODUCT_DATA_DIR` 환경 변수로 변경할 수 있습니다.

| 경로 | 내용 |
| --- | --- |
| `runtime/uploads/{session_id}/` | UUID를 붙인 업로드 원본 |
| `runtime/data/checkpoints.db` | LangGraph SQLite Checkpointer |
| `runtime/data/ontoproduct.db` | 제품 및 등록 작업 catalog |
| `runtime/exports/{product_id}.json` | 등록 제품 JSON |
| `runtime/evaluation/` | UI에서 실행한 평가 JSON/Markdown |

Streamlit rerun이나 서버 재시작 후 **최근 작업 → 선택한 작업 불러오기** 또는 대시보드의 **등록 화면에서 열기**로 이어갑니다. 등록 화면의 `?case={thread_id}` 링크로도 복원합니다. 중간에 끊긴 실행은 **실행 이어가기**, 오류 interrupt에서는 **오류 재시도 / 작업 중단**을 사용합니다.

등록 작업 ID UNIQUE 제약으로 같은 작업의 반복 승인이나 재시도가 제품을 중복 생성하지 않습니다. DB 저장 뒤 Export가 실패해도 기존 error_handler에서 재시도하여 원본 제품의 JSON을 복구합니다.

중복 검토용 예제 제품 DM-500A, DM-510, MX-500은 화면의 예제 추가 버튼 또는 아래 명령으로 넣습니다. 반복 실행해도 중복 생성하지 않습니다.

```powershell
.venv\Scripts\python.exe scripts/seed_database.py
```

## 평가

정답은 `eval/documents/`의 합성 TXT 문서와 `eval/ground_truth/`의 JSON 3개입니다. 이 작은 교육용 데이터는 실제 제조 문서 추출 정확도를 대표하지 않습니다.

```powershell
.venv\Scripts\python.exe eval/report.py
```

[계산된 평가 보고서](eval/reports/evaluation.md)와 [원본 출력 JSON](eval/reports/evaluation.json)을 생성합니다. UI 실행은 별도로 runtime/evaluation에 저장합니다.

- **MOCK EVALUATION**: 수정하지 않은 Mock workflow 출력. 자동 추가 시도 0회, 사람 수정 없음.
- **RULE ENGINE EVALUATION**: 정답의 canonical query를 실제 SQLite DuplicateAgent에 입력. 독립 seed DB를 사용하며 사용자 제품 DB를 변경하지 않습니다.

두 평가를 합산하지 않습니다. Attribute Detection Precision/Recall/F1, canonical Value Accuracy, Unit Normalization Accuracy, Ontology Classification Accuracy, Required Field Detection Accuracy, Duplicate Precision@3/Recall@3를 실제 출력에서 계산합니다. 누락은 오답이며 빈 분모는 N/A입니다. Precision@3의 분모는 쿼리 수 × 3으로 빈 후보 슬롯도 포함합니다. 자세한 정의, 분자·분모, 입력/출력, 원본·정답 SHA-256은 보고서에 포함됩니다.

## 구조와 계약

- `schemas/`: JSON 직렬화 가능한 Pydantic 업무 스키마.
- `graph/`: 검증된 Wrapper, Reducer, Router, 병렬 barrier join, HITL interrupt/resume.
- `agents/`: 고정 read/write 계약 및 SQLite 등록·중복 adapter.
- `mocks/`: Parser, Extraction, Ontology, Validation, Reviewer Mock.
- `services/`: 정규화·검증·workspace·workflow runtime·등록/Export·조회 집계.
- `repositories/`: SQLite 제품 및 작업 persistence.
- `app.py`, `views/`: 명시적 st.navigation과 6개 화면.
- `evaluation/`, `eval/`: 평가 계산, 합성 문서/정답, CLI 진입점 및 보고서.

UI는 Agent나 LLM을 직접 호출하지 않습니다. UploadedFile, DB Connection, LLM Client는 ProductState에 넣지 않습니다. cached resource가 runtime/checkpointer를 재사용합니다. `apply_manual_overrides`만 effective normalized_product를 작성하며 수동 속성은 HUMAN provenance와 null confidence입니다. 분류 변경 시 적용할 수 없는 수정값은 orphaned_overrides로 보관하고 화면에 알립니다.

Agent 모니터는 Registry metadata를 사용하며 내부 코드를 분석하지 않습니다. 평균 실행 시간은 checkpoint의 execution_id별 완료 이벤트에서 계산합니다. Health는 health_check 응답으로 외부 모델 연결을 검증하는 지표가 아닙니다. 대시보드 전체 수치는 SQL 전체 집계이며 실행 이력 집계는 최근 최대 100개 작업입니다. 제품 검색은 최신 최대 500개를 표시합니다.

## 검증과 배포 파일

```powershell
.venv\Scripts\python.exe -m pytest -q -W error::pytest.PytestCacheWarning
.venv\Scripts\python.exe -m ontoproduct.cli
.venv\Scripts\python.exe -m ontoproduct.cli --interactive
uv --cache-dir .uv-cache build --offline
```

전체 테스트 **166 passed**. SQLite 재개, 오류 retry, 동시 작업 격리, 등록 멱등성, 평가 계산·원본 저장, Streamlit AppTest와 최종 통합 흐름을 검증했습니다. CLI는 PHASE 1의 InMemory Checkpointer와 Mock 등록을 유지합니다.

[source distribution](dist/ontology_product_system-0.1.0.tar.gz)에는 app/config, source, eval 데이터와 보고서, 테스트·문서를 포함합니다. wheel에는 패키지 코드와 ontology.yaml을 포함합니다. UI와 기본 Ground Truth를 함께 실행하려면 이 저장소 또는 source distribution을 사용하세요. runtime·cache·사용자 DB는 배포 파일에 포함하지 않습니다.

[실제 compiled graph](docs/workflow.mmd), [PHASE 1 보고서](docs/PHASE1_REPORT.md), [PHASE 2 보고서](docs/PHASE2_REPORT.md), [PHASE 3 완료 보고서](docs/PHASE3_REPORT.md)를 참고하세요. 앞 단계 보고서는 당시 상태를 기록한 문서입니다.

현재 앱은 로컬 교육용이며 인증 없이 최근 작업을 조회합니다. 실제 문서 파싱, 실제 LLM Agent, 운영 인증 및 대규모 DB 성능은 추가 구현 범위입니다.

팀원이 Mock을 실제 문서·LLM 기능으로 교체할 때는 [팀 협업 가이드](docs/MOCK_REPLACEMENT_PLAN.md)에서 담당별 파일 위치, 입력·출력 예시, 교체 절차와 테스트 기준을 확인하세요.

전체 처리 순서와 온톨로지의 상속·정규화·검증·승인·저장 역할은 [시스템 동작 설명](docs/SYSTEM_AND_ONTOLOGY.md)에 정리했습니다.

팀원의 작업 브랜치·PR 제출과 Isaac0424의 검토·병합 방식, main 보호 설정은 [Git 협업 가이드](docs/GIT_WORKFLOW.md)를 참고하세요.
