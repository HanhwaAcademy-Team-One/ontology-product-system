# 07. Registration 담당자: 승인된 제품을 실제로 저장하기

[공통 약속](00_COMMON.md) · [Reviewer](06_REVIEWER.md) · [분업표](../MOCK_REPLACEMENT_PLAN.md)

## 1. 현재 실제 구현이 있습니다

UI는 RegistrationAgent와 RegistrationService를 사용하여 SQLite 저장과 JSON Export를 합니다. 기본 CLI/Mock 평가의 RegistrationMock은 메모리의 final_product만 반환합니다.

이 담당자는 기존 실제 저장 흐름을 이해하고 실제 Agent들이 만든 제품에서도 승인·멱등성·오류 복구가 유지되는지 검증합니다.

멱등성은 “같은 작업을 두 번 실행해도 같은 제품이 두 번 생성되지 않는다”는 뜻입니다.

## 2. 위치

| 위치 | 역할 |
| --- | --- |
| [agents/registration_agent.py](../../src/ontoproduct/agents/registration_agent.py) | 현재 실제 Agent |
| [services/registration_service.py](../../src/ontoproduct/services/registration_service.py) | 승인/제품 검증, DB 저장, JSON Export |
| [repositories/product_repository.py](../../src/ontoproduct/repositories/product_repository.py) | registration_case_id UNIQUE 저장 |
| [repositories/database.py](../../src/ontoproduct/repositories/database.py) | 테이블 정의와 Connection |
| [schemas/human_review.py](../../src/ontoproduct/schemas/human_review.py) | APPROVE/EDIT/REJECT |
| [tests/test_registration_idempotency.py](../../tests/test_registration_idempotency.py) | 반복/동시 저장 검증 |
| [tests/test_phase2_workflow.py](../../tests/test_phase2_workflow.py) | 실제 Graph Export 오류 retry |
| 필요 시 신규 tests/test_real_registration_flow.py | 실제 추출 결과 통합 저장 확인 |

## 3. 입력

필수: normalized_product, human_review.
선택: duplicate_candidates, ontology_mapping.

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
  "human_review": {
    "action": "APPROVE"
  }
}
```

case_id는 Agent 생성자에서 받습니다. 전체 ProductState에는 registration_case_id가 있지만 Wrapper는 계약에 없는 키를 Agent에 전달하지 않습니다. 따라서 Agent 안에서 state["registration_case_id"]를 읽도록 변경하면 안 됩니다.

UI runtime이 작업별로 RegistrationAgent(thread_id, service)를 만들기 때문에 각 작업 ID가 바르게 연결됩니다.

## 4. 출력

```json
{
  "final_product": {
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
  }
}
```

final_product는 DB에 저장한 원본 제품입니다. product_id, export_path, ALREADY_REGISTERED 상태를 최상위에 추가하면 계약 위반입니다. 그 값은 Service/Repository의 내부 결과이고 UI가 Repository로 조회합니다.

## 5. 현재 저장 순서

1. human_review를 검사하고 APPROVE인지 확인합니다.
2. NormalizedProduct schema를 검사합니다.
3. 실제 ontology 정의로 제품을 다시 검증합니다.
4. case_id UNIQUE 제약으로 저장합니다.
5. 이미 같은 case_id가 있으면 기존 레코드를 돌려줍니다.
6. 기존/신규 레코드의 제품을 JSON으로 Export합니다.
7. 저장된 제품을 final_product로 반환합니다.
8. Graph가 case_status를 REGISTERED로 바꿉니다.

승인 전 저장하거나 Agent에서 case_status를 직접 반환하지 않습니다.

## 6. DB 저장 뒤 Export가 실패하면?

DB commit이 먼저 끝나고 JSON 파일 쓰기가 실패할 수 있습니다. 이때 DB 제품은 1개가 존재하지만 Graph는 registration 오류 화면에서 멈춥니다.

사용자가 RETRY를 누르면 같은 case_id로 다시 실행합니다. Repository는 기존 제품을 반환하고 Service는 JSON을 다시 만듭니다. 이 동작을 유지해야 합니다.

“파일 저장이 실패했으니 다른 UUID로 새 제품을 만들자”라고 구현하면 중복 제품이 생깁니다.

현재 Export는 임시 파일을 쓴 다음 목적 파일로 replace합니다. 완성되지 않은 JSON이 사용자에게 보이는 것을 줄이기 위한 처리입니다.

## 7. 개발/교체 방법

현재 Agent를 단독 registry에 연결하는 예:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from ontoproduct.agents.registration_agent import RegistrationAgent
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.repositories.database import Database
from ontoproduct.repositories.product_repository import ProductRepository
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.services.registration_service import RegistrationService

with TemporaryDirectory(prefix="ontoproduct-registration-") as directory:
    paths = ApplicationPaths(Path(directory))
    ontology = OntologyService()
    repository = ProductRepository(Database(paths.product_db))
    registration_service = RegistrationService(repository, ontology, paths.exports)
    case_id = str(uuid4())
    registry = mock_registry(ontology)
    registry.register(
        RegistrationAgent(case_id, registration_service),
        replace=True,
    )
    registry.validate_complete()
    # execute_agent 호출과 DB/Export 확인도 이 with 블록 안에서 수행합니다.
```

위 예시는 현재 구현으로 실행할 수 있습니다. 임시 DB/Export 폴더는 블록 종료 시 삭제되므로 저장 테스트도 블록 안에서 실행하세요. 같은 작업의 재시도를 테스트할 때는 같은 case_id를 재사용합니다.

UI runtime은 작업별 case_id로 다시 연결합니다. 새 Agent가 동일 계약을 유지하더라도 통합 담당자와 runtime의 실제 생성 위치를 확인해야 합니다. 전체 팀이 공유하는 하나의 RegistrationAgent에 특정 작업 ID를 고정하면 안 됩니다.

## 8. 테스트

| 상황 | 확인 |
| --- | --- |
| APPROVE + 정상 제품 | DB 1개, JSON 생성, final_product 일치 |
| EDIT/REJECT 또는 승인 없음 | 저장 거부 |
| 필수값 누락 제품 | 승인 데이터가 있어도 검증 실패, 저장 없음 |
| 같은 case_id 두 번 | DB 제품 1개, 기존 제품 보존 |
| 같은 case_id 다른 payload | 기존 저장 제품이 몰래 덮어써지지 않음 |
| 같은 case_id 동시 실행 | UNIQUE 제약으로 1개 |
| 서로 다른 case_id | 독립 레코드 |
| DB commit 후 Export 실패 | 오류 interrupt, DB는 1개 |
| 위 오류에서 RETRY | 기존 제품 재사용, JSON 복구, 오류 RESOLVED 기록 |
| Streamlit rerun/서버 재시작 | 제품 추가 중복 없음, 완료 작업 복원 |
| HUMAN 속성 | provenance=HUMAN, confidence=null 보존 |
| 원본 근거 | evidence/source_file/page가 DB와 JSON에 보존 |

```powershell
.venv\Scripts\python.exe -m pytest tests\test_registration_idempotency.py tests\test_phase2_workflow.py tests\test_phase3_integration.py -q
```

신규 실제 문서 통합 테스트를 만들었다면 해당 파일도 실행합니다.

## 9. 완료 기준

실제 Agent가 만든 제품을 승인 후 저장하고 반복/동시 실행/Export 실패 뒤에도 중복이 없어야 합니다. 평가/QA 담당자에게 DB 레코드와 JSON 예시, 오류 retry 테스트 결과를 전달하세요.
