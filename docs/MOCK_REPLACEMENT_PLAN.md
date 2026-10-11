# 팀 협업 가이드: 실제 Agent 담당과 협업 방식

이 문서는 신입 개발자가 담당 기능을 맡아 개선·테스트할 수 있도록 정리한 것입니다.

**현재 상태 (2026-10-11):** 7개 슬롯이 모두 실제 Agent로 교체되어 Mock 모드와 `src/ontoproduct/mocks/`는 제거되었습니다. 앱·CLI·평가는 항상 실제 Agent로 실행하며 API Key는 이 PC의 `OPENAI_API_KEY`에서 읽습니다. 실제 모델 품질 평가 확장은 남은 범위입니다. 설치는 [Quick start](QUICK_START.md), 현재 연결은 [통합 가이드](team/08_INTEGRATION.md)를 따릅니다. 01~03 담당 문서의 최초 교체 절차는 구현 당시 참고 자료입니다.

저장소 루트는 `D:\ontology-product-system`입니다. 아래 문서의 `src/...`는 이 폴더를 기준으로 읽으세요.

## 처음 읽는 순서

전체 동작을 먼저 이해하려면 [시스템 동작과 온톨로지의 역할](SYSTEM_AND_ONTOLOGY.md)을 읽으세요. 현재 코드에서 실제로 동작하는 규칙과 앞으로 구현할 문서 분석을 구분해 설명합니다.

1. [공통 약속과 용어](team/00_COMMON.md)를 읽습니다. 입력/출력 이름을 바꾸면 다른 팀원 코드가 연결되지 않는 이유를 설명합니다.
2. 아래 표에서 자기 담당 문서를 읽습니다. 각 문서에 파일 위치, JSON 예시, 구현 순서, Registry 연결 코드, 테스트, 완료 기준이 있습니다.
3. 담당 Agent를 개선하고 단위 테스트와 전체 workflow 테스트로 확인합니다.
4. 통합 담당자는 [연결 방법](team/08_INTEGRATION.md)을 따라 UI runtime에 연결합니다.
5. [실제 문서 평가](team/09_EVALUATION.md)로 결과를 확인합니다.

## 분업표

“담당”은 역할 이름입니다. 사람이 적으면 여러 역할을 한 사람이 맡아도 됩니다.

| 담당 | 현재 상태 | 앞으로 맡을 일 | 자세한 설명 |
| --- | --- | --- | --- |
| 문서 처리 | 실제 ParserAgent | 텍스트 PDF/XLSX/TXT·근거 위치 회귀 검증; OCR은 미지원 | [01 Parser](team/01_PARSER.md) |
| 정보 추출 | 실제 ExtractionAgent (OpenAI) | 실제 문서 추출·근거·충돌·재추출 품질 검증 | [02 Extraction](team/02_EXTRACTION.md) |
| 분류·정규화 | 실제 OntologyAgent (규칙·OpenAI) | 자체 의미 모델·규칙·LLM 분류·단위 정규화 검증 | [03 Ontology](team/03_ONTOLOGY.md) |
| 검증 | 실제 ValidationAgent (Python 규칙·SHACL) | SHACL 업무 정책·등록 재검증 연결 합의(03·08 공동), 실제 문서 평가 | [04 Validation](team/04_VALIDATION.md) |
| 중복 조회 | 실제 SQLite Agent | 기존 기능 검증·개선; 의미 검색은 선택 확장 | [05 Duplicate](team/05_DUPLICATE.md) |
| 검토 판단 | 실제 ReviewerAgent (규칙) | 판단·재시도·사람 수정 보호 검증 | [06 Reviewer](team/06_REVIEWER.md) |
| 저장 | 실제 SQLite Agent | 승인·멱등 저장·Export 실패 복구 검증 | [07 Registration](team/07_REGISTRATION.md) |
| 통합·LLM 기반 설정 | OpenAI adapter·실제 registry·CLI 연결 | cache·오류·복원 회귀 검증 | [08 Integration](team/08_INTEGRATION.md) |
| 평가·QA | inputdata 실문서 평가(오프라인 참조·live) | 정답 독립 검수, 전체 실모델 평가 | [09 Evaluation](team/09_EVALUATION.md) |

## 팀원끼리 주고받는 데이터

각 Agent가 한 작업을 하고 다음 Agent에게 넘겨주는 결과라고 생각하세요.

| 슬롯 | 반드시 받는 입력 | 있으면 읽을 수 있는 입력 | 반드시 반환할 최상위 키 |
| --- | --- | --- | --- |
| parser | source_documents | 없음 | parsed_documents |
| extraction | parsed_documents | review_result, ontology_mapping, locked_fields | extracted_product |
| ontology | extracted_product | locked_fields, manual_overrides | ontology_mapping, base_normalized_product |
| validation | normalized_product, ontology_mapping | 없음 | validation_result |
| duplicate | normalized_product, ontology_mapping | 없음 | duplicate_candidates |
| reviewer | normalized_product, validation_result, duplicate_candidates, ontology_mapping | review_result, locked_fields | review_result |
| registration | normalized_product, human_review | duplicate_candidates, ontology_mapping | final_product |

이 표는 [현재 계약 파일](../src/ontoproduct/agents/registry.py)의 CONTRACTS와 같습니다. **기본 작업은 키 이름과 자료형을 유지하고, 그 안에 실제 문서에서 얻은 값과 실제 판단 결과를 채우는 것입니다.**

## 실제 처리 흐름

```mermaid
flowchart TD
    Upload[UI에서 파일 업로드·저장] --> Parser
    Parser --> Extraction
    Extraction --> Ontology
    Ontology --> Apply[기존 수동 수정 병합 노드]
    Apply --> Validation
    Apply --> Duplicate
    Validation --> Join[둘 다 완료되면 합류]
    Duplicate --> Join
    Join --> Reviewer
    Reviewer --> Human[기존 사람 검토 화면]
    Human -->|수정| Apply
    Human -->|승인| Registration
    Registration --> Saved[SQLite 제품·JSON]
```

이 그림은 역할 이해용입니다. 실제 오류·재시도·분류 변경 경로 전체는 [compiled graph](workflow.mmd)에 있습니다.

## 협업할 때 파일 소유권

각 기능 담당자는 자신의 `agents/*_agent.py`, 전용 service/prompt, 전용 테스트를 주로 수정합니다. 통합 담당자가 `workflow_runtime.py`, `views/resources.py`, 공통 LLM service/settings, dependency 파일을 모아서 수정합니다.

Agent를 바꿀 때는 `build_document_registry()`에 등록된 구현을 수정하거나 새 Agent를 만들어 그 자리에 등록합니다. 테스트 전용 고정 Agent(`tests/doubles.py`)는 Graph 라우팅 테스트에만 씁니다. Graph, ProductState, 계약은 기본적으로 재사용합니다. 추가 출력 필드가 필요하면 schema 담당자와 먼저 합의하고, 스키마·모든 소비자·테스트를 함께 변경합니다.

## 팀원에게 받을 완료 보고

각 담당자는 PR에 다음 내용을 적으면 됩니다.

- 만든/수정한 파일과 구현 기능.
- 실제 입력 1개와 출력 1개.
- 지원 범위: 예를 들어 텍스트 PDF 지원, 스캔 PDF는 OCR 미지원.
- 자신의 Agent를 Registry에 등록하는 코드.
- 실행한 테스트와 결과.
- 아직 처리하지 못하는 입력·오류.

테스트 개수는 구현 이력에 고정하지 않고 실행 결과로 보고합니다. 새 기능을 완료했다고 말하려면 자기 단위 테스트, 계약 검사, 전체 회귀 테스트, 해당 기능의 실제 문서 통합 확인까지 끝내야 합니다.
