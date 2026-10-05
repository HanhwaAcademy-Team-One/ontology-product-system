# 04. Validation 담당자: 값이 등록 가능한지 규칙으로 검사하기

[공통 약속](00_COMMON.md) · [Ontology](03_ONTOLOGY.md) · [분업표](../MOCK_REPLACEMENT_PLAN.md)

## 1. 내가 맡는 일

필수 항목이 있는지, 숫자인지, 단위가 맞는지, 범위를 벗어났는지 검사합니다. 이 기능은 기존 validation_service.py에 실제로 구현되어 있습니다. ValidationMock이라는 이름 때문에 검사도 고정 결과라고 생각하면 안 됩니다.

담당자는 기존 검증 함수를 실제 Agent에 연결하고 실제 문서에서 나오는 경계 사례를 테스트합니다. 검증 함수의 정상 동작을 유지하는 것이 먼저입니다.

## 2. 위치

| 구분 | 위치 | 할 일 |
| --- | --- | --- |
| 현재 adapter | [mocks/agents.py의 ValidationMock](../../src/ontoproduct/mocks/agents.py) | 실제 validate_product 호출 |
| 기존 실제 함수 | [services/validation_service.py](../../src/ontoproduct/services/validation_service.py) | 필수값·타입·단위·범위 검사 |
| schema | [schemas/validation.py](../../src/ontoproduct/schemas/validation.py) | ValidationResult, ValidationIssue |
| 신규 | src/ontoproduct/agents/validation_agent.py | 실제 BaseAgent adapter |
| 신규 | tests/test_real_validation_agent.py | adapter 계약과 경계 사례 |
| 기존 테스트 | [tests/test_validation.py](../../tests/test_validation.py) | 이미 있는 검증 동작 확인 |

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

normalized_product는 사람 수정까지 반영된 최종 검사 대상입니다. Extraction 원문 값이나 base_normalized_product를 검사하면 사람 수정 후 재검증 결과가 틀릴 수 있습니다.

ontology_mapping에는 필수/선택 속성과 표준 단위/범위가 들어 있습니다. 이 정의를 기준으로 검사합니다.

## 4. 출력

정상 제품에 선택 중량만 없을 때:

```json
{
  "validation_result": {
    "valid": true,
    "issues": [
      {
        "field": "attributes.weight",
        "code": "MISSING_OPTIONAL",
        "message": "Optional property weight is missing",
        "severity": "warning"
      }
    ]
  }
}
```

§3 입력에서 `normalized_product.attributes.rated_speed` 항목만 제거했을 때입니다. 원래 없던 weight의 경고도 함께 나옵니다:

```json
{
  "validation_result": {
    "valid": false,
    "issues": [
      {
        "field": "attributes.rated_speed",
        "code": "MISSING_REQUIRED",
        "message": "Required property rated_speed is missing",
        "severity": "error"
      },
      {
        "field": "attributes.weight",
        "code": "MISSING_OPTIONAL",
        "message": "Optional property weight is missing",
        "severity": "warning"
      }
    ]
  }
}
```

현재 validate_product의 message는 영어 고정 문자열입니다. 위 JSON은 Agent 반환 형태라 `validation_result`로 감싸져 있습니다. 함수를 직접 호출하면 그 안의 `{"valid": ..., "issues": ...}`만 반환하므로, 함수 테스트에서는 `result == expected["validation_result"]`처럼 비교합니다.

valid는 error가 하나라도 있으면 false입니다. warning만 있으면 true입니다.

현재 허용 code는 MISSING_REQUIRED, MISSING_OPTIONAL, TYPE, UNIT, RANGE, UNKNOWN_PROPERTY, CLASS입니다. 새 code를 만들려면 schema와 화면/평가 소비자를 함께 변경해야 합니다.

## 5. 구현 순서

1. 기존 validate_product를 읽고 테스트를 실행합니다.
2. BaseAgent 형태로 ValidationAgent를 만듭니다. name은 validation, is_mock은 False, provider는 실제 규칙 엔진임을 표시합니다.
3. required/optional/writes는 CONTRACTS["validation"]에서 복사합니다.
4. run에서 기존 validate_product(normalized_product, ontology_mapping)를 호출합니다.
5. validation_result 한 키만 반환합니다.
6. 실제 문서에서 생기는 새 검증 요구가 있을 때 service와 테스트를 함께 확장합니다.

핵심 run 함수는 다음처럼 단순합니다.

```python
def run(self, state):
    return {
        "validation_result": validate_product(
            state["normalized_product"],
            state["ontology_mapping"]
        )
    }
```

LLM이 “괜찮다”고 답해도 숫자 타입이나 필수값 오류를 통과시키지 않습니다. 검증은 deterministic rule로 유지합니다.

## 6. 교체

```python
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.agents.validation_agent import ValidationAgent

ontology = OntologyService()
registry = mock_registry(ontology)
registry.register(ValidationAgent(), replace=True)
registry.validate_complete()
```

이 예시는 신규 `src/ontoproduct/agents/validation_agent.py`에 ValidationAgent를 구현한 뒤 실행합니다. 현재 저장소에는 이 신규 파일이 없습니다. 다른 Agent의 결과나 case_status를 직접 수정하지 않습니다. Duplicate와 병렬로 실행되므로 자기 출력만 작성해야 합니다.

## 7. 테스트

| 경우 | 기대 |
| --- | --- |
| 필수 속도 누락/null | MISSING_REQUIRED, valid=false |
| 선택 weight 누락 | warning, 필수값이 맞으면 valid=true |
| voltage value="24" 문자열 | TYPE |
| 숫자 자리에 True | TYPE |
| power unit=kW인 최종 제품 | 표준 W가 아니므로 UNIT |
| speed=-1 | minimum=0보다 작으므로 RANGE |
| product_class와 mapping 클래스 불일치 | CLASS |
| 정의되지 않은 속성 | UNKNOWN_PROPERTY warning |
| 사람이 속도를 보완한 normalized_product | 누락 오류 해소 |
| 여러 오류 | 관련 issue 보존, valid=false |
| 정상 adapter | 기존 함수 결과와 동일, 계약 통과 |
| 병렬 Graph | Duplicate 결과를 덮어쓰지 않고 둘 다 완료 후 Reviewer 실행 |

신규 테스트 작성 후:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_real_validation_agent.py tests\test_validation.py tests\test_parallel_workflow.py -q
```

## 8. 완료 기준

기존 검증을 실제 Agent로 분리하고, 오류/경고의 의미를 유지해야 합니다. Reviewer 담당자에게 issue.code/field/severity 예시를 전달하세요. LLM 호출 없이도 완료할 수 있는 역할입니다.
