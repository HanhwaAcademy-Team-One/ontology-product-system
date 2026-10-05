# 03. Ontology 담당자: 분류·속성·단위를 우리 기준에 맞추기

[공통 약속](00_COMMON.md) · [Extraction](02_EXTRACTION.md) · [분업표](../MOCK_REPLACEMENT_PLAN.md)

## 1. 내가 맡는 일

“이 제품은 BLDCMotor인가 Bearing인가”, “출력과 정격 출력은 어느 속성인가”, “0.6 kW를 표준 W로 어떻게 바꾸나”를 처리합니다.

OntologyMock은 candidate_class를 그대로 사용하고 confidence를 0.95로 고정합니다. 하지만 클래스 상속과 단위 변환 service는 이미 실제로 동작합니다. 분류/이름 매핑을 실제화하면서 기존 규칙을 재사용합니다.

## 2. 위치

| 구분 | 위치 | 책임 |
| --- | --- | --- |
| 현재 Mock | [mocks/agents.py의 OntologyMock](../../src/ontoproduct/mocks/agents.py) | 후보 분류/수동 분류 선택, 고정 confidence |
| 정의 | [ontology/ontology.yaml](../../src/ontoproduct/ontology/ontology.yaml) | 존재하는 클래스·속성·단위·범위 |
| 기존 service | [services/ontology_service.py](../../src/ontoproduct/services/ontology_service.py) | 부모/상속 속성/단위 변환 |
| 기존 정규화 | [services/normalization_service.py](../../src/ontoproduct/services/normalization_service.py) | normalize_attributes, apply_overrides |
| schema | [schemas/ontology.py](../../src/ontoproduct/schemas/ontology.py), [product.py](../../src/ontoproduct/schemas/product.py) | OntologyMapping, NormalizedProduct |
| 신규 | src/ontoproduct/agents/ontology_agent.py | 실제 분류와 매핑 adapter |
| 신규 | src/ontoproduct/prompts/ontology.py | 모델 사용 시 분류·속성 매핑 지시 |
| 신규 | tests/test_real_ontology_agent.py | 분류·상속·단위·수동 분류 검증 |

## 3. 입력

필수: extracted_product. 선택: locked_fields, manual_overrides.

```json
{
  "extracted_product": {
    "product_name": "DM-600",
    "candidate_class": "BLDCMotor",
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
        "value": 0.6,
        "unit": "kW",
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
  "locked_fields": [],
  "manual_overrides": {}
}
```

사람이 분류를 Bearing으로 바꾸면 다음처럼 추가 입력이 옵니다.

```json
{
  "manual_overrides": {
    "product_class": "Bearing"
  },
  "locked_fields": [
    "product_class"
  ]
}
```

두 번째 JSON은 선택 필드 설명입니다. 실제로는 필수 extracted_product도 있어야 합니다. 사람 분류를 우선 적용하고 원래 AI 후보 BLDCMotor로 되돌리지 않습니다.

## 4. 출력은 두 개입니다

아래 ontology_mapping은 `model_dump(mode="json")`처럼 기본값 필드도 모두 포함합니다. 예를 들어 string 속성도 canonical_unit=null, units=[], minimum=null, maximum=null이 들어갑니다. minimum=0.0은 float이며, 0.6 kW를 변환한 rated_power.value도 600.0입니다. 입력에서는 기본값 필드를 생략할 수 있지만, 출력 전체를 비교하는 테스트에는 직렬화된 모든 필드를 사용하세요.

```json
{
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
  },
  "base_normalized_product": {
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

- ontology_mapping: 클래스, 분류 신뢰도, 해당 클래스의 필수/선택 속성 정의.
- base_normalized_product: 표준 이름/단위로 정리한 제품의 기본값.
- 원문 출력 0.6 kW가 표준 출력 600 W로 바뀝니다.
- manufacturer는 Motor에서 상속된 필수 속성입니다.
- weight는 선택 속성이라 비어 있어도 필수 누락 오류가 아닙니다.

예시 confidence=0.82는 설명용입니다. 실제 판단 정책으로 계산하거나 명시적인 불확실 처리 정책을 사용하세요. OntologyMapping.confidence는 현재 schema에서 null을 허용하지 않습니다.

**normalized_product는 반환하지 않습니다.** 그 값은 Graph의 apply_manual_overrides가 base_normalized_product에 사람 수정값을 합쳐서 만듭니다.

## 5. 구현 순서

1. ontology.yaml의 클래스 목록과 속성을 읽습니다. 문자열 이름은 정확히 일치해야 합니다.
2. manual_overrides에 수동 product_class가 있으면 먼저 유효한 클래스인지 확인하고 사용합니다.
3. 수동 분류가 없으면 추출 후보와 속성을 보고 실제 분류를 선택합니다. 모델을 쓰면 허용 클래스 목록을 입력에 제공하고 응답을 검사합니다.
4. “정격 출력”, “Rated Power”, “출력” 등의 항목을 rated_power로 연결합니다. 동의어 사전은 별도 service/data로 두어도 됩니다.
5. resolve_required_properties와 resolve_optional_properties를 사용해 상속 속성을 얻습니다.
6. mapping 객체를 만듭니다. 필수/선택 목록을 직접 하드코딩하면 ontology 변경 시 불일치하므로 service를 사용합니다.
7. normalize_attributes로 지원 단위 변환을 합니다.
8. OntologyMapping, NormalizedProduct로 검사하고 두 출력만 반환합니다.

공통 LLM service를 쓰는 생성자 예: OntologyAgent(ontology, llm_service). 규칙 기반 분류로 시작한다면 client는 필요하지 않을 수 있습니다. “실제 구현”의 기준은 실제 입력에 따라 올바르게 분류·매핑하는 동작입니다.

지원하지 않는 단위를 임의 변환하지 않습니다. 현재 normalize_attributes는 변환 불가 값을 보존하여 Validation이 UNIT 오류로 사람에게 보여줍니다.

분류가 불확실할 때 무조건 Product로 내리고 승인 가능하게 만들지 않습니다. 재매핑/사람 검토에 연결할 신뢰도 정책을 Reviewer 담당자와 합의합니다.

## 6. 교체

```python
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.agents.ontology_agent import OntologyAgent

ontology = OntologyService()
registry = mock_registry(ontology)
registry.register(OntologyAgent(ontology, llm_service), replace=True)
```

생성자 형태는 신규 구현의 합의 예시입니다. 실제 코드와 테스트를 같은 형태로 맞춥니다.

## 7. 테스트

| 입력/상황 | 확인 |
| --- | --- |
| 모터 추출 정보 | 존재하는 적절한 Motor/BLDCMotor 분류 |
| 베어링 정보 | Bearing 분류와 내경/외경 정의 |
| BLDCMotor | Motor의 manufacturer가 필수 목록에 포함 |
| 0.6 kW | 600 W |
| 750 g | 0.75 kg |
| 지원하지 않는 단위 | 잘못 변환하지 않고 검증에 전달 |
| 정의되지 않은 클래스 | 오류 또는 명시한 불확실 처리 |
| 수동 Bearing + AI BLDCMotor | 수동 Bearing을 유지 |
| locked product_class | 재매핑이 수동 분류를 덮어쓰지 않음 |
| 분류 변경 시 속도 수동값 | 기존 Graph가 orphaned_overrides에 보관하고 복원 |
| 출력 키 | ontology_mapping/base_normalized_product만 반환 |

신규 테스트 작성 후:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_real_ontology_agent.py tests\test_ontology.py tests\test_manual_overrides.py -q
```

## 8. 완료 기준

분류와 속성 매핑이 실제 입력에 따라 달라지고, 상속·단위·수동 분류가 보존되어야 합니다. Validation 담당자에게 실제 두 출력 JSON과 불확실 분류 정책을 전달하세요.
