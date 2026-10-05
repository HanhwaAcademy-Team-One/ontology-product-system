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
| 신규 tests/test_real_duplicate_agent.py | 후보/순위/음성 사례 테스트 |
| 필요 시 신규 services/semantic_duplicate_service.py | 의미 검색 추가 구현 |

## 3. 입력

필수: normalized_product, ontology_mapping. 선택: 없음.

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

DB Repository/service는 생성자에서 받습니다. DB Connection이나 전체 제품 목록을 state에 추가하지 않습니다. 현재 Agent는 입력 계약에 ontology_mapping을 받지만 service 비교에는 normalized_product를 사용합니다.

## 4. 출력

동일 제품이 기존 DB에 있을 때의 형식 예시:

```json
{
  "duplicate_candidates": [
    {
      "product_id": "33333333-3333-4333-8333-333333333333",
      "product_name": "DM-600",
      "score": 1.0,
      "reason": "Rule similarity of class, name, and shared canonical attributes."
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

위 product_id는 설명용 ID입니다. Repository가 저장할 때 생성한 실제 ID로 바뀌므로 테스트에서 이 문자열을 그대로 비교하지 말고 저장 결과의 `record["product_id"]`와 비교하세요. 현재 reason은 위의 영어 고정 문자열이며, 후보별 설명은 아직 구현되어 있지 않습니다.

product_id는 실제 기존 DB 레코드 ID여야 합니다. 모델이 임의 ID를 만들면 안 됩니다. score는 0~1 비교 점수이며 실제 중복일 확률을 뜻하지 않습니다.

Agent는 후보만 반환합니다. 승인·거절은 Reviewer와 사람 검토의 역할입니다.

## 5. 기존 알고리즘 이해하기

현재 service는 다음과 같습니다.

1. 최신 최대 500개 기존 제품을 조회합니다.
2. 동일 product_class만 비교합니다.
3. 공통의 non-null 속성 값과 단위가 같은 비율을 구합니다.
4. 제품명은 SequenceMatcher로 비교합니다.
5. 점수 = 0.2 + 0.4 × 속성 일치 비율 + 0.4 × 이름 유사도.
6. 점수가 0.6 이상인 후보를 score 내림차순으로 정렬합니다. 점수가 같으면 product_id 문자열 오름차순입니다. 이 순서대로 기본 top_k=3개를 반환합니다.

속성은 표준 단위로 정규화된 입력이어야 합니다. 0.6 kW와 600 W가 서로 다른 값으로 비교되지 않도록 Ontology 단계가 먼저 처리합니다.

반드시 확인할 한계는 “공통 속성이 아주 적어도 일치율이 높게 나올 수 있음”과 “최신 500개 밖 제품은 검색하지 않음”입니다. 개선하면 score/reason 정책과 평가를 함께 변경합니다.

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
| 이름만 비슷하고 전압/출력이 다름 | 차이가 점수에 반영; 현재 reason은 고정 문자열 |
| 다른 분류 | 현재 정책에서 후보 제외 |
| 속성 누락 | 예외 없이 처리하고 근거 과대 해석을 평가 |
| 빈 DB | 빈 list |
| 동률 | product_id 문자열 오름차순; 점수가 다르면 score 내림차순 |
| 후보가 많음 | top_k 제한, 높은 점수 우선 |
| 0.6 kW → 600 W 정규화 후 | 같은 표준 사양으로 비교 |
| 여러 작업 동시 실행 | state/candidate가 섞이지 않음 |
| 비교 실행 전후 | 제품이 새로 저장되지 않음 |
| Precision@K/Recall@K | 실제 관련 후보 정답으로 계산 |

신규 테스트 작성 후:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_real_duplicate_agent.py tests\test_phase2_workflow.py tests\test_evaluation.py -q
```

## 9. 완료 기준

실제 DB 후보를 올바른 ID·순위·점수·이유로 반환하고, 실패 시 기존 병렬 stage 오류/재시도 경로를 따라야 합니다. Reviewer 담당자에게 점수의 의미와 threshold, 알려진 오탐 조건을 전달하세요.
