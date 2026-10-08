# 개발자 매뉴얼

[문서 목차](README.md) · [Quick start](QUICK_START.md) · [팀 협업 가이드](MOCK_REPLACEMENT_PLAN.md)

설치·UI 실행은 Quick start를 따릅니다. 이 문서의 명령은 Windows PowerShell, 저장소 루트 기준입니다. cmd·Linux·macOS 문법은 [터미널별 명령](QUICK_START.md#터미널별-명령)을 참고하세요.

## 구조와 계약

| 위치 | 역할 |
| --- | --- |
| `src/ontoproduct/schemas/` | JSON 직렬화 가능한 Pydantic 업무 스키마 |
| `src/ontoproduct/graph/` | Wrapper, Reducer, Router, 병렬 join, interrupt/resume |
| `src/ontoproduct/agents/` | 고정 read/write 계약, 실제 문서 Agent, SQLite 등록·중복 adapter |
| `src/ontoproduct/mocks/` | Parser·Extraction·Ontology·Validation·Reviewer Mock |
| `src/ontoproduct/services/` | 파싱·LLM·정규화·검증·runtime·등록/Export·조회 |
| `src/ontoproduct/repositories/` | SQLite 제품 및 작업 persistence |
| `src/ontoproduct/ontology/` | 업무 YAML, 의미 모델, RDF/OWL·SHACL 자료 |
| `app.py`, `src/ontoproduct/app.py`, `src/ontoproduct/views/` | 진입점, st.navigation, 6개 화면 |
| `src/ontoproduct/evaluation/`, `eval/` | 평가 계산, 합성 문서·정답, CLI 및 보고서 |
| `tests/` | 계약·Graph·서비스·UI·통합 회귀 테스트 |

UI는 Agent나 LLM을 직접 호출하지 않습니다. `current_runtime()`이 설정을 읽고 cached runtime을 제공하며, Real 모드의 Registry는 01~03 문서 Agent를 교체합니다. runtime은 Duplicate·Registration을 작업별 실제 DB Agent로 연결합니다. [통합 가이드](team/08_INTEGRATION.md)에 연결 코드와 설정 우선순위가 있습니다.

UploadedFile, DB Connection, LLM Client는 ProductState에 넣지 않습니다. `apply_manual_overrides` 노드가 effective `normalized_product`를 작성합니다. 수동 속성은 HUMAN provenance와 null confidence이며, 적용할 수 없는 수정값은 `orphaned_overrides`에 보관합니다.

Agent read/write 계약은 [registry.py](../src/ontoproduct/agents/registry.py)에 있습니다. 필드 변경 시 스키마·소비자·테스트를 함께 변경합니다. 상세 처리 흐름은 [시스템 동작 설명](SYSTEM_AND_ONTOLOGY.md), 모델 정의·RDF·SHACL은 [제품 온톨로지 매뉴얼](team/03_PRODUCT_ONTOLOGY.md)을 참고하세요.

## 테스트와 CLI

기능 변경은 관련 테스트와 전체 회귀 테스트를 통과해야 완료로 보고합니다. 테스트가 없는 기능은 최소 테스트 1개를 먼저 작성합니다. 새 패키지는 이유를 설명하고 확인받습니다.

```powershell
.venv\Scripts\python.exe -m pytest -q
```

pytest cache 경고도 오류로 확인하려면 아래 명령을 사용합니다.

```powershell
.venv\Scripts\python.exe -m pytest -q -W error::pytest.PytestCacheWarning
```

기본 테스트는 실제 모델을 호출하지 않습니다. `tests/test_live_llm.py`는 `ONTOPRODUCT_LIVE_LLM=1`일 때만 실행되며, API Key와 모델 설정이 필요합니다. 실제 호출 방법과 기존 검증 기록은 [통합 가이드](team/08_INTEGRATION.md#검증)를 참고하세요.

PHASE 1 Mock workflow를 CLI로 확인할 수 있습니다.

```powershell
.venv\Scripts\python.exe -m ontoproduct.cli
.venv\Scripts\python.exe -m ontoproduct.cli --interactive
```

CLI는 InMemory Checkpointer와 Mock 등록을 사용합니다. `AGENT_MODE=real`을 지정해도 UI의 Real runtime이나 SQLite 저장으로 전환되지 않습니다. interactive 모드는 interrupt에서 resume 명령을 JSON으로 입력합니다.

## 평가

정답은 `eval/documents/`의 합성 TXT와 `eval/ground_truth/`의 JSON 3개입니다. 실제 제조 문서 추출 정확도를 대표하지 않습니다.

```powershell
.venv\Scripts\python.exe eval/report.py
```

[Markdown 보고서](../eval/reports/evaluation.md)와 [원본 출력 JSON](../eval/reports/evaluation.json)을 생성합니다. UI 실행은 별도로 `runtime/evaluation/`에 저장합니다.

- **MOCK EVALUATION**: 수정하지 않은 Mock workflow 출력. 자동 추가 시도 0회, 사람 수정 없음.
- **RULE ENGINE EVALUATION**: 정답의 canonical query를 SQLite DuplicateAgent에 입력. 독립 seed DB를 사용하며 사용자 제품 DB를 변경하지 않습니다.

두 평가를 합산하지 않습니다. CLI와 평가 화면은 `AGENT_MODE`와 관계없이 이 평가 경로를 사용합니다. 실제 문서·모델 품질 평가를 확장하는 계획은 [09 Evaluation](team/09_EVALUATION.md)에 있습니다.

Attribute Detection Precision/Recall/F1, canonical Value Accuracy, Unit Normalization Accuracy, Ontology Classification Accuracy, Required Field Detection Accuracy, Duplicate Precision@3/Recall@3를 실제 출력에서 계산합니다. 누락은 오답이며 빈 분모는 N/A입니다. Precision@3의 분모는 쿼리 수 × 3으로 빈 후보 슬롯도 포함합니다. 지표 정의, 분자·분모, 입력/출력, 원본·정답 SHA-256은 보고서에 포함됩니다.

## 패키징

```powershell
uv --cache-dir .uv-cache build --offline
```

오프라인 빌드는 build dependency가 로컬 cache에 준비되어 있어야 합니다. 배포 포함 범위의 기준은 [pyproject.toml](../pyproject.toml)입니다.

- **source distribution**: app/config, source, eval 자료·보고서, 테스트·문서 등 프로젝트 실행 자료.
- **wheel**: 패키지 코드와 패키지 안의 온톨로지·설정 자료. 루트 UI 진입점과 기본 Ground Truth를 함께 실행하려면 저장소나 source distribution을 사용합니다.
- runtime·cache·사용자 DB는 배포 파일에 포함하지 않습니다.

`dist/` 파일은 마지막 빌드 시점의 결과입니다. 현재 소스와 같은 버전의 내용인지 확인하려면 다시 빌드하고 결과를 검사합니다.

## 협업과 검증 기록

담당별 파일 위치·입출력·교체 절차는 [팀 협업 가이드](MOCK_REPLACEMENT_PLAN.md), 브랜치·PR·검토 방식은 [Git 협업 가이드](GIT_WORKFLOW.md)를 따릅니다.

[PHASE 1](PHASE1_REPORT.md), [PHASE 2](PHASE2_REPORT.md), [PHASE 3](PHASE3_REPORT.md), [02·03 인계 기록](team/02_03_IMPLEMENTATION_HANDOFF.md)의 테스트 개수와 미구현 항목은 각 기록 시점의 상태입니다. 현재 검증 결과는 직접 실행한 테스트 결과로 보고합니다.
