# 개발자 매뉴얼

[문서 목차](README.md) · [Quick start](QUICK_START.md) · [팀 협업 가이드](MOCK_REPLACEMENT_PLAN.md)

설치·UI 실행은 Quick start를 따릅니다. 이 문서의 명령은 Windows PowerShell, 저장소 루트 기준입니다. cmd·Linux·macOS 문법은 [터미널별 명령](QUICK_START.md#터미널별-명령)을 참고하세요.

## 구조와 계약

| 위치 | 역할 |
| --- | --- |
| `src/ontoproduct/schemas/` | JSON 직렬화 가능한 Pydantic 업무 스키마 |
| `src/ontoproduct/graph/` | Wrapper, Reducer, Router, 병렬 join, interrupt/resume |
| `src/ontoproduct/agents/` | 고정 read/write 계약, 실제 문서 Agent, SQLite 등록·중복 adapter |
| `src/ontoproduct/services/` | 파싱·LLM·정규화·검증·runtime·등록/Export·조회 |
| `src/ontoproduct/repositories/` | SQLite 제품 및 작업 persistence |
| `src/ontoproduct/ontology/` | 업무 YAML, 의미 모델, RDF/OWL·SHACL 자료 |
| `app.py`, `src/ontoproduct/app.py`, `src/ontoproduct/views/` | 진입점, st.navigation, 6개 화면 |
| `src/ontoproduct/evaluation/`, `eval/` | inputdata 실문서 평가 계산, CLI 및 보고서 |
| `tests/` | 계약·Graph·서비스·UI·통합 회귀 테스트. `tests/doubles.py`는 Graph 라우팅 테스트 전용 고정 Agent |

UI는 Agent나 LLM을 직접 호출하지 않습니다. `current_runtime()`이 설정을 읽고 cached runtime을 제공합니다. `build_document_registry()`가 Parser·Extraction·Ontology·Validation·Reviewer Agent를 등록하고, runtime이 Duplicate·Registration을 작업별 실제 DB Agent로 추가한 뒤 7개 슬롯이 모두 찼는지 확인합니다. [통합 가이드](team/08_INTEGRATION.md)에 연결 코드와 설정 우선순위가 있습니다.

UploadedFile, DB Connection, LLM Client는 ProductState에 넣지 않습니다. `apply_manual_overrides` 노드가 effective `normalized_product`를 작성합니다. 수동 속성은 HUMAN provenance와 null confidence이며, 적용할 수 없는 수정값은 `orphaned_overrides`에 보관합니다.

Agent read/write 계약은 [registry.py](../src/ontoproduct/agents/registry.py)에 있습니다. 필드 변경 시 스키마·소비자·테스트를 함께 변경합니다. 상세 처리 흐름은 [시스템 동작 설명](SYSTEM_AND_ONTOLOGY.md), 모델 정의·RDF·SHACL은 [제품 온톨로지 매뉴얼](team/03_PRODUCT_ONTOLOGY.md)을 참고하세요.

## 테스트와 CLI

기능 변경은 관련 테스트와 전체 회귀 테스트를 통과해야 완료로 보고합니다. 테스트가 없는 기능은 최소 테스트 1개를 먼저 작성합니다. 새 패키지는 이유를 설명하고 확인받습니다.

```powershell
uv run pytest -q
```

시스템 Python의 `pytest`를 그대로 실행하면 의존성(openai 등)이 없어 수집 오류가 납니다. `uv run` 또는 `.venv\Scripts\python.exe -m pytest -q`로 실행합니다.

pytest cache 경고도 오류로 확인하려면 아래 명령을 사용합니다.

```powershell
.venv\Scripts\python.exe -m pytest -q -W error::pytest.PytestCacheWarning
```

기본 테스트는 실제 모델을 호출하지 않습니다. 워크플로를 끝까지 통과시키는 테스트는 원문 줄에서만 값을 고르는 가짜 LLM(`tests/real_llm_helpers.py`)을 실제 Agent에 주입하고, Graph 라우팅·재시도 테스트는 `tests/doubles.py`의 고정 Agent를 씁니다. 둘 다 테스트 전용이며 제품 코드에는 들어가지 않습니다. `tests/test_live_llm.py`는 `ONTOPRODUCT_LIVE_LLM=1`일 때만 실행되며, API Key와 모델 설정이 필요합니다. 실제 호출 방법과 기존 검증 기록은 [통합 가이드](team/08_INTEGRATION.md#검증)를 참고하세요.

CLI로 한 제품의 문서를 UI와 같은 실제 runtime(SQLite 저장 포함)으로 처리할 수 있습니다. `OPENAI_API_KEY`가 필요합니다.

```powershell
.venv\Scripts\python.exe -m ontoproduct.cli inputdata\01_normal_motors\M001_bldcmotor.txt
.venv\Scripts\python.exe -m ontoproduct.cli --interactive inputdata\03_edge_cases\E002_bldcmotor.txt
.venv\Scripts\python.exe -m ontoproduct.cli --diagram docs\workflow.mmd
```

- 기본 모드: 등록 가능하면 자동 승인하고, 사람 수정이 필요하면 작업을 대기 상태로 남긴 채 끝납니다. 출력된 `Case` ID로 UI(`?case=...`)에서 이어서 처리할 수 있습니다. 오류 interrupt는 중단합니다.
- `--interactive`: interrupt마다 resume 명령을 JSON으로 입력합니다(예: `{"action": "APPROVE"}`).
- 저장 위치는 UI와 같이 `ONTOPRODUCT_DATA_DIR`(기본 `runtime/`)입니다.

## 평가

평가 자료는 `inputdata/`의 50개 사례(TXT·PDF·XLSX, 다중 문서 포함)와 `manifest.json` 기대값입니다. 각 사례를 격리된 임시 runtime에서 실제 Parser·Extraction·Ontology·Validation·Reviewer·Duplicate Agent로 처리합니다.

```powershell
# 오프라인 참조 평가: 모델 대신 manifest 원문 값을 돌려주는 참조 응답. API 비용 없음
.venv\Scripts\python.exe -m ontoproduct.evaluation.document_runner --output eval\document_reports

# 실제 모델 평가: 호출 수·시간 제한 필수, 비용 발생
.venv\Scripts\python.exe -m ontoproduct.evaluation.document_runner --live --cases M001 E002 --max-calls 8 --time-limit-seconds 600 --output eval\document_reports
```

오프라인 참조 평가는 LLM 품질이 아니라 파이프라인 동작을 측정합니다. 평가 화면도 이 경로를 사용하며 결과는 `runtime/evaluation/{run_id}/`에 저장합니다. 보고서에는 Expected Outcome Accuracy, Attribute Detection Precision/Recall/F1, Value·Unit Accuracy, Ontology Classification Accuracy, Required Field Detection Accuracy, 호출 기록과 원본·정답 SHA-256이 들어갑니다. 누락은 오답이며 빈 분모는 N/A입니다. 상세 설명은 [eval/README.md](../eval/README.md)와 [09 Evaluation](team/09_EVALUATION.md)에 있습니다.

## 패키징

```powershell
uv --cache-dir .uv-cache build --offline
```

오프라인 빌드는 build dependency가 로컬 cache에 준비되어 있어야 합니다. 배포 포함 범위의 기준은 [pyproject.toml](../pyproject.toml)입니다.

- **source distribution**: app/config, source, eval 보고서, 테스트·문서 등 프로젝트 실행 자료.
- **wheel**: 패키지 코드와 패키지 안의 온톨로지·설정 자료. 루트 UI 진입점과 inputdata 평가 자료를 함께 실행하려면 저장소나 source distribution을 사용합니다.
- runtime·cache·사용자 DB는 배포 파일에 포함하지 않습니다.

`dist/` 파일은 마지막 빌드 시점의 결과입니다. 현재 소스와 같은 버전의 내용인지 확인하려면 다시 빌드하고 결과를 검사합니다.

## 협업과 검증 기록

담당별 파일 위치·입출력·교체 절차는 [팀 협업 가이드](MOCK_REPLACEMENT_PLAN.md), 브랜치·PR·검토 방식은 [Git 협업 가이드](GIT_WORKFLOW.md)를 따릅니다.

[PHASE 1](PHASE1_REPORT.md), [PHASE 2](PHASE2_REPORT.md), [PHASE 3](PHASE3_REPORT.md), [02·03 인계 기록](team/02_03_IMPLEMENTATION_HANDOFF.md)의 테스트 개수와 미구현 항목은 각 기록 시점의 상태입니다. 현재 검증 결과는 직접 실행한 테스트 결과로 보고합니다.
