# 04. Validation 담당자: 값이 등록 가능한지 규칙으로 검사하기

[공통 약속](00_COMMON.md) · [Ontology](03_ONTOLOGY.md) · [분업표](../MOCK_REPLACEMENT_PLAN.md)

**현재 상태 (2026-10-08):** ValidationAgent와 규칙 검증 함수가 구현되어 있으며, UI Real 모드의 Registry에도 연결되어 있습니다. 기본 Mock 모드는 ValidationMock을 사용하고 두 adapter는 같은 `validate_product`를 호출합니다. LLM 검증과 SHACL 자동 연결은 포함되지 않습니다. 이번 점검 결과와 남은 작업은 [§9](#9-점검-결과와-남은-작업)에 정리했습니다.

## 1. 내가 맡는 일

필수 항목이 있는지, 숫자인지, 단위가 맞는지, 범위를 벗어났는지 검사합니다. 이 기능은 기존 validation_service.py에 실제로 구현되어 있습니다. ValidationMock이라는 이름 때문에 검사도 고정 결과라고 생각하면 안 됩니다.

담당자는 기존 검증 함수를 실제 Agent에 연결하고 실제 문서에서 나오는 경계 사례를 테스트합니다. 검증 함수의 정상 동작을 유지하는 것이 먼저입니다.

## 2. 위치

| 구분 | 위치 | 할 일 |
| --- | --- | --- |
| 기본 Mock adapter | [mocks/agents.py의 ValidationMock](../../src/ontoproduct/mocks/agents.py) | 실제 validate_product 호출 |
| 기존 실제 함수 | [services/validation_service.py](../../src/ontoproduct/services/validation_service.py) | 필수값·타입·단위·범위 검사 |
| schema | [schemas/validation.py](../../src/ontoproduct/schemas/validation.py) | ValidationResult, ValidationIssue |
| Real adapter | [agents/validation_agent.py](../../src/ontoproduct/agents/validation_agent.py) | 구현된 BaseAgent adapter |
| Real 연결 | [agents/real_registry.py](../../src/ontoproduct/agents/real_registry.py) | ValidationAgent를 replace=True로 등록 |
| 실제 Agent 테스트 | [tests/test_real_validation_agent.py](../../tests/test_real_validation_agent.py) | adapter 계약·타입·범위·실제 Duplicate와 병렬 합류 |
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

필수 속성의 문서 충돌은 `value=null`과 후보 근거를 보존한 채 `MISSING_REQUIRED`, `severity=error`, `valid=false`로 반환합니다. 실제 누락과의 차이는 message입니다.

| 상황 | field | code / severity | message |
| --- | --- | --- | --- |
| 필수 전압 실제 누락 | attributes.rated_voltage | MISSING_REQUIRED / error | Required property rated_voltage is missing |
| 필수 전압 문서 충돌 | attributes.rated_voltage | MISSING_REQUIRED / error | Required property rated_voltage has conflicting document values |
| 문자열 전압 | attributes.rated_voltage | TYPE / error | Expected number |
| 선택 중량 누락 | attributes.weight | MISSING_OPTIONAL / warning | Optional property weight is missing |

Reviewer는 code·field·severity와 제품의 충돌 근거를 함께 읽어야 합니다. 충돌을 구분하려고 새 오류 code를 추가하지 않습니다. 후보 원문은 [등록 화면](../../src/ontoproduct/views/registration.py)에 표시하며, Validation은 후보를 선택하거나 값을 고치지 않습니다.

정의된 속성의 issue는 mapping 순서를 따르고, 클래스 밖 속성의 `UNKNOWN_PROPERTY` 경고는 속성 이름 오름차순으로 반환합니다. 같은 제품의 경고 표시 순서가 실행마다 바뀌지 않도록 합니다.

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

이 예시는 현재 구현으로 실행할 수 있습니다. UI Real 모드에서는 `build_document_registry()`가 같은 방식으로 연결합니다. 다른 Agent의 결과나 case_status를 직접 수정하지 않습니다. Duplicate와 병렬로 실행되므로 자기 출력만 작성해야 합니다.

## 7. 테스트

| 경우 | 기대 |
| --- | --- |
| 필수 속도 누락/null | MISSING_REQUIRED, valid=false |
| 선택 weight 누락 | warning, 필수값이 맞으면 valid=true |
| voltage value="24" 문자열 | TYPE |
| 숫자 자리에 True | TYPE |
| integer에 1 / 1.0 / True | 1만 허용, 나머지는 TYPE |
| boolean에 False / 0 / "false" | False만 허용, 나머지는 TYPE |
| string에 공백만 입력 | TYPE; 실제 누락/null의 MISSING_REQUIRED와 구분 |
| power unit=kW인 최종 제품 | 표준 W가 아니므로 UNIT |
| speed=-1 | minimum=0보다 작으므로 RANGE |
| maximum과 같은 값 / 초과한 값 | 상한 포함, 초과하면 RANGE |
| product_class와 mapping 클래스 불일치 | CLASS |
| 정의되지 않은 속성 여러 개 | UNKNOWN_PROPERTY warning, 속성 이름 오름차순; valid=true 유지 |
| 사람이 속도를 보완한 normalized_product | 누락 오류 해소 |
| 여러 오류 | 관련 issue 보존, valid=false |
| 정상 adapter | 기존 함수 결과와 동일, 계약 통과 |
| 실제 Validation·Duplicate 병렬 Graph | Barrier로 동시 실행 확인, 각 결과 보존, 합류 1회 후 Reviewer 실행, 승인 전 DB 저장 없음 |

현재 검증 명령:

```powershell
$env:ONTOPRODUCT_LIVE_LLM = "0"
.venv\Scripts\python.exe -m pytest tests\test_real_validation_agent.py tests\test_validation.py tests\test_parallel_workflow.py tests\test_review_01_05.py -q
.venv\Scripts\python.exe -m pytest -q
```

## 8. 완료 기준

기존 검증을 실제 Agent로 분리하고, 오류/경고의 의미를 유지해야 합니다. Reviewer 담당자에게 issue.code/field/severity 예시를 전달하세요. LLM 호출 없이도 완료할 수 있는 역할입니다.

## 9. 점검 결과와 남은 작업

### 이번 점검

- 기본 규칙·Real 연결·필수 충돌 메시지·사람 수정 후 재검증은 구현되어 있습니다. [REVIEW_01_05](REVIEW_01_05.md)의 #1~#5는 이미 반영되어 있으며 회귀 파일의 9개 테스트가 통과합니다.
- 클래스 밖 속성 경고가 set 순서를 따라 표시되는 문제를 실패하는 테스트로 재현하고, 이름순 정렬 한 줄로 수정했습니다. 오류 code·severity·등록 가능 여부는 바꾸지 않았습니다.
- integer/boolean/string 타입, 상한 포함 여부, 직접 호출의 입력 불변성, 실제 ValidationAgent와 SQLite DuplicateAgent의 병렬 합류를 테스트로 보강했습니다. Parser·Extraction·Ontology·Reviewer는 이 병렬 테스트에서 Mock이므로 실모델 품질 검증으로 해석하지 않습니다.
- 검사 함수는 원문 사실의 정확성이나 AI confidence를 판정하지 않습니다. confidence와 재시도 정책은 Reviewer의 책임입니다. NaN/Infinity·잘못된 구조는 기존 schema/Wrapper가 처리 오류로 거부하며, 정상 검증 결과로 숨기지 않습니다.

검증 기록 (2026-10-08):

| 확인 | 명령 / 방법 | 결과 |
| --- | --- | --- |
| 시작 관련 테스트 | `.venv\Scripts\python.exe -m pytest tests\test_real_validation_agent.py tests\test_validation.py tests\test_review_01_05.py -q` | 33 passed |
| 시작 전체 | `.venv\Scripts\python.exe -m pytest -q` | 469 passed / 2 skipped |
| 경고 순서 재현 | `.venv\Scripts\python.exe -m pytest tests\test_real_validation_agent.py::test_unknown_property_warnings_have_stable_order -q` | 수정 전 1 failed, 수정 후 관련 테스트에서 통과 |
| 개선 후 관련 테스트 | §7의 첫 pytest 명령 | 50 passed (기존 병렬 테스트 포함, 신규 회귀 12개 추가) |
| 개선 후 전체 | `.venv\Scripts\python.exe -m pytest -q` | 481 passed / 2 skipped / 0 xfailed |
| 정적 검사 | `.venv\Scripts\python.exe -m ruff check src\ontoproduct\services\validation_service.py tests\test_real_validation_agent.py` | 통과 |
| SHACL 연결 한계 확인 | 내경 32 mm·외경 12 mm 제품을 `validate_product`와 `OntologyService.validate_semantics`에 각각 전달 | 기본 규칙 valid=true / SHACL valid=false 확인 |

pytest 실행 시 `ONTOPRODUCT_LIVE_LLM=0`을 사용했습니다. skip은 기존 live LLM 테스트 2개이며, 전체 실행의 기존 rdflib DeprecationWarning 1개는 유지됩니다. 화면 수동 확인과 실제 모델 호출은 미실시입니다. 새 패키지를 추가하지 않았으며 기존 staged 작업을 보존하고 스테이징·커밋하지 않았습니다.

### 남은 작업과 완료 조건

아래는 문서와 현재 코드를 대조한 후속 목록입니다. 04번의 기본 규칙 검증 완료와 구분하며, 우선순위는 이번 점검의 제안입니다.

| 우선순위 | 작업 / 담당 | 현재 차이와 완료 조건 | 근거 |
| --- | --- | --- | --- |
| 높음 | SHACL을 등록 검증에 연결 / 03·04·08 | 현재 각 속성의 타입·단위·범위만 검사하므로 내경 32 mm·외경 12 mm도 기본 규칙은 통과할 수 있습니다. `validate_semantics`는 이 조합을 거부합니다. issue의 code·field·severity 매핑, 중복 issue 처리와 실행 실패 정책을 먼저 합의하고, Graph 검증과 승인 시 RegistrationService 재검증에 같은 정책을 적용해야 합니다. 정상 베어링 통과, 내경≥외경 등록 차단, 사람이 수정한 뒤 해소, DB 저장 없음으로 확인합니다. | [제품 온톨로지의 운영 연결](03_PRODUCT_ONTOLOGY.md#운영-연결과-검증-한계), [08 통합](08_INTEGRATION.md) |
| 높음 | ReviewerAgent와 충돌·중복 판단 / 06 | Reviewer는 아직 Mock입니다. 필수 문서 충돌을 반복 재추출하지 않고 사람 수정으로 안내하는 정책, duplicate verdict/evidence를 reason에 설명하는 동작을 구현·연결해야 합니다. HUMAN/locked 보호·상한·최종 승인 검사를 유지하는 테스트가 필요합니다. Validation은 충돌을 MISSING_REQUIRED로 계속 전달합니다. | [06 Reviewer](06_REVIEWER.md), [검토 #6](REVIEW_01_05.md#6-06-인계-reviewer가-duplicate충돌-정보를-판단에-쓰지-않음) |
| 높음 | 실제 문서·모델 평가 / 09·02·03·04 | 현재 평가 runner는 합성 TXT의 Mock 평가와 별도 규칙 중복 평가입니다. PDF/XLSX/TXT와 사람이 검수한 정답, 격리 DB, Real runtime 실행, 원문/정답 hash·모델·프롬프트 버전과 실패 사례를 남겨야 합니다. 자동 추출 결과와 사람 수정 후 결과를 분리하고 04의 누락·타입·단위·범위·충돌 검출을 측정합니다. | [09 평가](09_EVALUATION.md) |
| 중간 | 결정적 오류의 수동 해결 경로 / 02·03·08 | 선택 속성·제품명 충돌은 오류 화면의 RETRY/STOP만 제공합니다. 같은 입력으로 반복되는 오류의 recoverable 정책과 자료 교체·분류/속성 수정 경로를 합의해야 합니다. 충돌 보존과 잠금 보호를 유지한 채 해결 또는 종료할 수 있어야 합니다. | [명세 §10](02_03_IMPLEMENTATION_SPEC.md#10-기존-graph와-오류-처리의-한계) |
| 중간 | confidence 프롬프트·기준 평가 / 02·03·06 | Extraction 프롬프트는 confidence를 optional로 안내합니다. 근거 있는 값의 점수 반환 지시 변경은 평가 후 결정하고, 변경하면 프롬프트 버전을 올립니다. null 정책·사람 확인 경로·점수가 보정 확률이 아니라는 의미는 유지합니다. | [검토 #1](REVIEW_01_05.md#1-ai-confidence가-없거나-낮은-필수-속성은-사람이-확인할-수-없음), [06 Reviewer](06_REVIEWER.md) |
| 필요 시 | OCR·대규모 중복 조회·RDF DB / 01·05·03·08 | 스캔 PDF OCR은 미지원이고, 중복 조회는 같은 분류 전체를 Python에서 비교하며, RDF는 필요할 때 생성합니다. 지원할 입력·데이터량·저장 요구가 정해지면 별도 작업으로 진행합니다. 기본 ValidationAgent 연결의 미완료 항목은 아닙니다. | [01 Parser](01_PARSER.md), [05 Duplicate](05_DUPLICATE.md), [제품 온톨로지](03_PRODUCT_ONTOLOGY.md) |

과거 인계 문서의 “운영 목업 교체 미완료”와 테스트 개수는 작성 당시 이력입니다. 현재 Parser·Extraction·Ontology·Validation의 Real 연결과 SQLite Duplicate·Registration 구현을 남은 작업으로 다시 집계하지 않습니다.
