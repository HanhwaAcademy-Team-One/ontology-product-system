# OntoProduct

Ontology 기반 제조 제품 등록 교육 프로젝트입니다. 문서에서 제품 정보를 추출하고, 분류·속성·단위를 정규화한 뒤 검증과 사람의 승인을 거쳐 SQLite에 저장합니다.

Python **3.12**와 OpenAI API Key가 필요합니다. 앱은 PC에 등록된 `OPENAI_API_KEY` 환경 변수를 읽습니다.

## Quick start

Windows PowerShell에서 저장소 루트를 열고 실행합니다. `uv`가 설치되어 있어야 합니다. 명령 프롬프트(cmd)나 Linux·macOS에서는 환경 변수 문법이 다르므로 [터미널별 명령](docs/QUICK_START.md#터미널별-명령)을 먼저 확인하세요.

```powershell
cd D:\ontology-product-system
uv --cache-dir .uv-cache sync --locked
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

`OPENAI_API_KEY`를 아직 등록하지 않았다면 [API Key 등록](docs/QUICK_START.md#2-api-key-등록)을 먼저 따르세요. [앱 열기](http://127.0.0.1:8502) → `inputdata/01_normal_motors/M001_bldcmotor.txt` 업로드 → **업로드 문서로 시작** → 추출 값과 근거 확인 → **등록 승인** 순서로 진행합니다. JSON 다운로드와 제품 데이터베이스에서 등록 결과를 확인하면 첫 실행이 끝납니다.

## 매뉴얼

| 목적 | 문서 |
| --- | --- |
| 설치, pip 대안, API Key 등록, 첫 등록 | [Quick start](docs/QUICK_START.md) |
| 화면별 사용법, 등록·수정·승인, 작업 복원, 오류 대응 | [사용자 매뉴얼](docs/USER_MANUAL.md) |
| 코드 구조, 테스트, 평가, 패키징 | [개발자 매뉴얼](docs/DEVELOPER_GUIDE.md) |
| 전체 매뉴얼·팀별 가이드·이력 찾아보기 | [문서 목차](docs/README.md) |

## 현재 구현 범위

| 단계 | 동작 |
| --- | --- |
| Parser | 텍스트 PDF·XLSX·TXT 실제 파싱 |
| Extraction · Ontology | OpenAI 모델 기반 추출·분류, 공통 규칙으로 정규화 |
| Validation · Reviewer | Python 규칙 검증과 규칙 기반 검토 판단 |
| Duplicate · Registration | SQLite 비교·저장, JSON Export |

Mock 모드는 없습니다. 모든 Agent가 실제 구현으로 동작합니다. 팀 기본 설정은 [llm.yaml](src/ontoproduct/config/llm.yaml)의 `openai / gpt-5`입니다. 업로드 문서 원문은 OpenAI API로 전송됩니다. 스캔 PDF의 OCR, 운영 인증, 대규모 DB 성능 개선은 추가 구현 범위입니다. 등록 흐름의 Validation과 승인 직전 재검증은 Python 규칙과 SHACL 정책(예: 베어링 내경 < 외경)을 함께 적용합니다.

현재 앱은 인증 없이 사용하는 로컬 교육용입니다. 단계별 완료 보고서는 당시 상태를 기록한 이력이며, 현재 실행 방법은 위 매뉴얼을 기준으로 확인하세요.
