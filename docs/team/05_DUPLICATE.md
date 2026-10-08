# 05. Duplicate 담당자: 기존 제품과 비교해 후보 보여주기

[공통 약속](00_COMMON.md) · [분업표](../MOCK_REPLACEMENT_PLAN.md)

## 1. 현재 상태부터 확인하세요

UI에서는 이미 실제 DuplicateAgent가 SQLite 제품을 조회합니다. DuplicateMock은 기본 CLI/Mock 평가에서 빈 후보를 반환합니다.

따라서 이 담당자는 기본 기능을 새로 만들기보다 기존 구현을 검증·개선하고 실제 데이터 품질을 확인합니다. 임베딩/벡터 검색은 추가 목표가 있을 때 구현하는 선택 확장입니다.

## 2. 위치

| 위치 | 역할 |
| --- | --- |
| [agents/duplicate_agent.py](../../src/ontoproduct/agents/duplicate_agent.py) | 이미 있는 실제 Agent |
| [services/duplicate_service.py](../../src/ontoproduct/services/duplicate_service.py) | 이름·분류·속성 비교와 ranking |
| [repositories/product_repository.py](../../src/ontoproduct/repositories/product_repository.py) | 기존 제품 조회 |
| [schemas/duplicate.py](../../src/ontoproduct/schemas/duplicate.py) | DuplicateCandidate |
| [services/seed_service.py](../../src/ontoproduct/services/seed_service.py) | 중복 데모용 제품 |
| [tests/test_real_duplicate_agent.py](../../tests/test_real_duplicate_agent.py) | 후보/순위/음성 사례/검증 단계 테스트 |
| 필요 시 신규 services/semantic_duplicate_service.py | 의미 검색 추가 구현 |

## 3. 입력

필수: normalized_product, ontology_mapping. 선택: 없음. 서비스는 ontology_mapping의 required/optional 속성으로 핵심 사양과 비교 방식을 정합니다.

```json
{
  "normalized_product": {
    "product_name": "DM-600",
    "product_class": "BLDCMotor",
    "attributes": {
      "manufacturer": {
        "value": "XYZ Motors",
        "unit": null,
        "confidence": 0.82,
        "evidence": "Manufacturer: XYZ Motors",
        "source_file": "motor_spec.txt",
        "page": null,
        "provenance": "AI"
      },
      "rated_voltage": {
        "value": 24,
        "unit": "V",
        "confidence": 0.82,
        "evidence": "Rated Voltage: 24 V",
        "source_file": "motor_spec.txt",
        "page": null,
        "provenance": "AI"
      },
      "rated_power": {
        "value": 600.0,
        "unit": "W",
        "confidence": 0.82,
        "evidence": "Rated Power: 0.6 kW",
        "source_file": "motor_spec.txt",
        "page": null,
        "provenance": "AI"
      },
      "rated_speed": {
        "value": 3200,
        "unit": "rpm",
        "confidence": 0.82,
        "evidence": "Rated Speed: 3200 rpm",
        "source_file": "motor_spec.txt",
        "page": null,
        "provenance": "AI"
      }
    }
  },
  "ontology_mapping": {
    "product_class": "BLDCMotor",
    "confidence": 0.82,
    "required_properties": {
      "manufacturer": {
        "type": "string",
        "canonical_unit": null,
        "units": [],
        "minimum": null,
        "maximum": null
      },
      "rated_voltage": {
        "type": "number",
        "canonical_unit": "V",
        "units": [
          "V"
        ],
        "minimum": 0.0,
        "maximum": null
      },
      "rated_power": {
        "type": "number",
        "canonical_unit": "W",
        "units": [
          "W",
          "kW"
        ],
        "minimum": 0.0,
        "maximum": null
      },
      "rated_speed": {
        "type": "number",
        "canonical_unit": "rpm",
        "units": [
          "rpm"
        ],
        "minimum": 0.0,
        "maximum": null
      }
    },
    "optional_properties": {
      "weight": {
        "type": "number",
        "canonical_unit": "kg",
        "units": [
          "g",
          "kg"
        ],
        "minimum": 0.0,
        "maximum": null
      }
    }
  }
}
```

DB Repository/service는 생성자에서 받습니다. DB Connection이나 전체 제품 목록을 state에 추가하지 않습니다. `DuplicateService(repository, ontology)`의 ontology는 단위 재정규화에 쓰며, 생략하면 기본 OntologyService를 사용합니다.

## 4. 출력

동일 제품이 기존 DB에 있을 때의 형식 예시:

```json
{
  "duplicate_candidates": [
    {
      "product_id": "33333333-3333-4333-8333-333333333333",
      "product_name": "DM-600",
      "score": 1.0,
      "reason": "중복 가능성 높음; 제품명 동일; 핵심 사양 4/4 일치",
      "verdict": "LIKELY_DUPLICATE",
      "evidence": [
        {"field": "product_name", "status": "MATCH", "query_value": "DM-600", "candidate_value": "DM-600", "unit": null},
        {"field": "rated_voltage", "status": "MATCH", "query_value": 24, "candidate_value": 24, "unit": "V"}
      ]
    }
  ]
}
```

후보가 없으면:

```json
{
  "duplicate_candidates": []
}
```

위 product_id는 설명용 ID입니다. Repository가 저장할 때 생성한 실제 ID로 바뀌므로 테스트에서 이 문자열을 그대로 비교하지 말고 저장 결과의 `record["product_id"]`와 비교하세요. evidence 예시는 일부만 표시했습니다. 실제로는 제품명과 핵심 사양 전체, 양쪽 중 한쪽에라도 값이 있는 선택 사양이 들어갑니다.

`verdict`와 `evidence`는 선택 필드입니다(기본값 `null`, `[]`). DuplicateMock 등 기존 생산자는 그대로 유효하며, 실제 규칙 엔진은 항상 채웁니다.

| 필드 | 의미 |
| --- | --- |
| verdict | `LIKELY_DUPLICATE`(중복 가능성 높음) 또는 `POSSIBLE_DUPLICATE`(중복 의심). 중복이 아니라고 판단한 제품은 반환하지 않습니다. |
| evidence[].status | `MATCH` 일치, `NEAR` 근사(상대 오차 2% 이내·제품명 변형·제조사명 포함 관계), `CONFLICT` 충돌, `MISSING` 한쪽 값 없음/비교 불가 |
| reason | 판정 · 제품명 비교 · 핵심 사양 일치 수 · 근사/충돌/비교 불가 항목을 사람이 읽는 문장으로 요약 |

product_id는 실제 기존 DB 레코드 ID여야 합니다. 모델이 임의 ID를 만들면 안 됩니다. score는 0~1 비교 점수이며 실제 중복일 확률을 뜻하지 않습니다.

Agent는 후보만 반환합니다. 승인·거절은 Reviewer와 사람 검토의 역할입니다.

## 5. 알고리즘 (9단계 파이프라인)

[services/duplicate_service.py](../../src/ontoproduct/services/duplicate_service.py)의 단계 주석 번호와 같습니다.

| 단계 | 함수 | 하는 일 |
| --- | --- | --- |
| [1] 구조화 | `structure` | dict를 NormalizedProduct로 검증 |
| [2] 정규화 | `normalize`, `tokens` | 제품명·문자열은 NFKC + 소문자 + 영숫자 토큰(`DM-500A` → `dm`,`500`,`a`), 숫자는 표준 단위로 재변환(0.6 kW → 600 W) |
| [3] 핵심 스펙 추출 | `mapping_properties`, `key_specs` | Ontology 필수 속성 = 핵심 사양(가중치 1.0), 선택 속성 = 보조 사양(0.3). mapping이 없으면 조회 제품의 속성 전체를 핵심으로 취급 |
| [4] 비교 방식 분류 | `classify` | number/integer → NUMERIC(허용 오차), string → TEXT(정규화 일치/포함), boolean 등 → EXACT |
| [5] 후보 검색 | `DuplicateService.retrieve` | 같은 product_class의 저장 제품 전체(개수 제한 없음) |
| [6] 상세 비교 | `compare_value`, `compare_names` | 속성별 MATCH/NEAR/CONFLICT/MISSING. 제품명은 시리즈(첫 영문 토큰)나 숫자 토큰이 다르면 CONFLICT, 유사도 상한 0.3 |
| [7] 중복 판단 | `judge` | 점수와 verdict 계산(아래) |
| [8] 판단 근거 | `explain` | reason 문장과 evidence 목록 생성 |
| [9] 결과 검증 | `DuplicateService.verify` | schema, top_k, product_id 중복·정렬, **DB에 실제 존재하고 같은 분류인지** 재조회. 위반 시 ValueError → execute_agent 오류 경로 |

점수:

```
spec  = Σ(가중치 × 상태점수) / Σ(핵심 사양 가중치 + 비교된 보조 사양 가중치)
        상태점수: MATCH 1, NEAR 0.5, CONFLICT 0, MISSING 0
score = 0.6 × spec + 0.4 × 제품명 유사도   (소수 4자리 반올림)
```

핵심 사양이 비어 있으면 분모에 그대로 남으므로, 공통 속성이 1개뿐인 제품이 높은 점수를 받던 문제가 사라졌습니다.

판정:

| verdict | 조건 |
| --- | --- |
| LIKELY_DUPLICATE | 핵심 사양 충돌 없음 그리고 (score ≥ 0.85이고 핵심 사양 모두 비교됨, 또는 제품명 동일이고 핵심 사양 절반 이상 비교됨) |
| POSSIBLE_DUPLICATE | 핵심 사양 충돌 없고 score ≥ 0.6, 또는 **제품명 동일**(사양이 충돌해도 사람이 확인하도록 노출) |
| 반환 안 함 | 그 외 |

정렬은 score 내림차순, 동률이면 product_id 오름차순이며 기본 top_k=3입니다.

Reviewer에게 전달할 해석 기준과 알려진 한계:

- score는 0~1 비교 점수이며 중복 확률이 아닙니다. 승인 판단은 verdict와 evidence를 함께 봅니다.
- 같은 제품명 + 사양 충돌은 score가 0.6 미만이어도 POSSIBLE_DUPLICATE로 나옵니다(데이터 입력 오류 또는 동명 제품).
- 이름이 완전히 달라도 핵심 사양이 모두 같으면 POSSIBLE_DUPLICATE가 됩니다. 사양 항목이 적은 분류(Bearing 내경/외경 등)에서는 우연 일치로 인한 오탐이 생길 수 있습니다.
- 시리즈·모델번호 판단은 토큰 규칙입니다. 숫자가 없는 이름이나 접두어 없는 이름은 문자열 유사도만 사용합니다.
- 다른 product_class는 비교하지 않습니다. 분류가 잘못된 제품은 중복을 놓칠 수 있습니다.
- 같은 분류 제품을 전부 읽어 Python에서 비교합니다. 대량 데이터에서는 Repository 인덱스/검색 방식 합의가 필요합니다.

## 6. 작업 순서

1. 현재 실제 Agent/service를 읽고 기존 DB/seed 테스트를 실행합니다.
2. 비교 대상과 threshold/top_k 정책을 정리합니다.
3. 누락이 많은 제품, 이름만 비슷한 제품, 다른 분류 제품을 테스트합니다.
4. 이유 문자열에 비교된 항목이나 후보 근거를 설명하도록 개선할 수 있습니다.
5. 대규모 조회가 필요하면 Repository 조회 범위와 인덱스/검색 방식을 통합 담당자와 합의합니다.
6. 의미 검색을 추가한다면 DB 실제 ID를 유지하고 기존 출력 스키마로 결과를 반환합니다.

단순히 모델이 제품명을 비슷하다고 답하는 것만으로 제품을 저장하거나 최종 중복 판정하지 않습니다.

## 7. 내 기능을 연결하는 방법

기본 실제 구현을 개발용 registry에 붙이는 예:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from ontoproduct.agents.duplicate_agent import DuplicateAgent
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.repositories.database import Database
from ontoproduct.repositories.product_repository import ProductRepository
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.duplicate_service import DuplicateService
from ontoproduct.services.ontology_service import OntologyService

with TemporaryDirectory(prefix="ontoproduct-duplicate-") as directory:
    paths = ApplicationPaths(Path(directory))
    ontology = OntologyService()
    repository = ProductRepository(Database(paths.product_db))
    registry = mock_registry(ontology)
    registry.register(
        DuplicateAgent(DuplicateService(repository)),
        replace=True,
    )
    registry.validate_complete()
    # 테스트 제품 저장과 execute_agent 호출도 이 with 블록 안에서 수행합니다.
```

위 예시는 현재 구현으로 실행할 수 있으며, 별도 임시 DB를 사용합니다. 빈 DB에서는 후보가 없습니다. 같은 제품을 저장한 뒤 비교하는 테스트를 이 with 블록 안에 추가하세요. 블록이 끝나면 임시 DB가 삭제됩니다.

주의: 현재 WorkflowRuntime.graph와 agent_metadata는 이 슬롯을 SQLite DuplicateAgent로 다시 교체합니다. **새 의미 검색 Agent를 factory에만 넣으면 UI runtime에서 덮어써질 수 있습니다.** 통합 담당자가 runtime의 두 생성 위치를 함께 수정하거나 공통 factory로 묶어야 합니다.

현재 기본 SQLite Agent 개선은 서비스 코드를 바꾸면 동일 adapter에서 사용합니다. 개발 서버 cached 객체 때문에 재시작이 필요할 수 있습니다.

## 8. 테스트

| 경우 | 확인 |
| --- | --- |
| 완전히 같은 제품 | 기존 실제 product_id 후보로 반환 |
| 이름만 비슷하고 전압/출력이 다름 | 모델번호·핵심 사양 충돌로 후보 제외; 같은 제품명이면 충돌 근거와 함께 POSSIBLE_DUPLICATE |
| 다른 분류 | 현재 정책에서 후보 제외 |
| 속성 누락 | 예외 없이 처리, 누락 핵심 사양은 점수에서 0으로 계산하고 reason에 "비교 불가"로 표시 |
| 빈 DB | 빈 list |
| 동률 | product_id 문자열 오름차순; 점수가 다르면 score 내림차순 |
| 후보가 많음 | top_k 제한, 높은 점수 우선 |
| 0.6 kW → 600 W 정규화 후 | 같은 표준 사양으로 비교 |
| 여러 작업 동시 실행 | state/candidate가 섞이지 않음 |
| 비교 실행 전후 | 제품이 새로 저장되지 않음 |
| Precision@K/Recall@K/Candidate Precision | 실제 관련 후보 정답으로 계산. Candidate Precision = 정답 후보 수 / 반환 후보 수 |
| 결과 검증 | DB에 없는 ID, 다른 분류, 중복 ID, top_k 초과, verdict 누락은 ValueError |

신규 테스트 작성 후:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_real_duplicate_agent.py tests\test_phase2_workflow.py tests\test_evaluation.py -q
```

## 9. 완료 기준

실제 DB 후보를 올바른 ID·순위·점수·이유로 반환하고, 실패 시 기존 병렬 stage 오류/재시도 경로를 따라야 합니다. Reviewer 담당자에게 점수의 의미와 threshold, 알려진 오탐 조건을 전달하세요.
