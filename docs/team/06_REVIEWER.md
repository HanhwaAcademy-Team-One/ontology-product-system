# 06. Reviewer 담당자: 다음에 무엇을 할지 판단하기

[공통 약속](00_COMMON.md) · [Validation](04_VALIDATION.md) · [Duplicate](05_DUPLICATE.md)

## 1. 내가 맡는 일

제품을 살펴보고 “정보를 다시 뽑자”, “분류를 다시 하자”, “사람이 고쳐야 한다”, “사람에게 승인을 받자”를 결정합니다.

현재 ReviewerMock은 실제 규칙으로 판단합니다. 실제 ReviewerAgent로 분리할 수 있습니다. 문서 근거/중복 후보를 더 깊게 종합하는 LLM 판단은 팀 목표에 따라 추가합니다.

## 2. 위치

| 구분 | 위치 | 역할 |
| --- | --- | --- |
| 현재 규칙 | [mocks/agents.py의 ReviewerMock](../../src/ontoproduct/mocks/agents.py) | 누락·confidence·validation 기반 판단 |
| schema | [schemas/review.py](../../src/ontoproduct/schemas/review.py) | 허용 decision, can_register 관계 |
| 기존 흐름 | [graph/routing.py](../../src/ontoproduct/graph/routing.py), [graph/nodes.py](../../src/ontoproduct/graph/nodes.py) | 추가 시도 상한, 사람 검토, 승인 검사 |
| 신규 | src/ontoproduct/agents/reviewer_agent.py | 실제 adapter |
| 필요 시 신규 | src/ontoproduct/services/review_service.py, prompts/reviewer.py | 판단 규칙/LLM 검토 |
| 신규 | tests/test_real_reviewer.py | decision 및 보호 규칙 검증 |

## 3. 입력

필수: normalized_product, validation_result, duplicate_candidates, ontology_mapping.
선택: review_result, locked_fields.

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
  },
  "duplicate_candidates": [],
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
  "locked_fields": []
}
```

Reviewer가 받는 것은 이미 사람 수정과 정규화를 반영한 제품입니다. parsed_documents는 현재 입력 계약에 없습니다. 근거는 속성의 evidence/source_file/page를 볼 수 있습니다. 원문 전체가 꼭 필요하면 입력 계약 변경을 모든 소비자와 합의해야 합니다.

## 4. 출력

```json
{
  "review_result": {
    "decision": "READY_FOR_HUMAN",
    "reason": "필수 항목의 규칙 검증을 통과했습니다. 사람의 승인이 필요합니다.",
    "retry_fields": [],
    "can_register": true
  }
}
```

허용 decision은 다음 다섯 개입니다.

| decision | 의미 | can_register |
| --- | --- | --- |
| RE_EXTRACT | 요청한 속성을 다시 추출 | false |
| REMAP_ONTOLOGY | 분류·매핑 다시 시도 | false |
| NEEDS_FIX | 사람 수정 필요 | false |
| READY_FOR_HUMAN | 등록 가능한 상태이며 사람 승인 필요 | true |
| REJECT | 업무 판단상 거절 | false |

can_register=true는 저장을 실행하라는 뜻이 아닙니다. **사람에게 승인 버튼을 제공할 수 있다는 뜻**입니다.

재추출 예시:

```json
{
  "review_result": {
    "decision": "RE_EXTRACT",
    "reason": "정격 속도가 없어 원문을 다시 확인합니다.",
    "retry_fields": [
      "rated_speed"
    ],
    "can_register": false
  }
}
```

현재 Mock은 retry_fields에 속성 키 rated_speed를 넣습니다. 기존 병합 함수는 attributes.rated_speed 경로도 처리하지만 팀은 한 표기 규칙을 합의해 사용하세요.

## 5. 구현 순서

1. 기존 ReviewerMock을 읽고 판단 순서를 이해합니다.
2. 수동 보호 항목을 먼저 확인합니다. locked_fields이거나 provenance=HUMAN이면 AI confidence로 재추출을 요구하지 않습니다.
3. AI의 필수 속성이 누락됐거나 confidence가 낮으면 retry_fields를 만듭니다.
4. AI 분류가 불확실하고 product_class가 locked가 아니면 재매핑을 요청합니다.
5. 검증 실패가 남으면 NEEDS_FIX로 사람 수정에 연결합니다.
6. 정상 제품이면 READY_FOR_HUMAN으로 사람 승인에 연결합니다.
7. 중복 후보의 의미를 reason에 설명합니다. 후보 점수만 보고 저장·삭제하지 않습니다.
8. ReviewResult.model_validate로 검사하고 review_result만 반환합니다.

기존 confidence 기준은 0.70입니다. 실제 모델 점수는 보정된 확률이 아니므로 기준/정책은 Extraction·Ontology 담당자와 합의하고 평가로 확인합니다. 현재 AI 속성의 confidence=null도 불확실하게 취급합니다.

사람 속성은 confidence=null이어도 HUMAN/locked 보호에 의해 재추출 대상으로 삼지 않습니다.

## 6. Graph가 하는 일과 내 역할을 구분하세요

Reviewer는 retry_count를 직접 수정하지 않습니다. 입력 계약에도 retry_count는 없습니다.

Reviewer가 RE_EXTRACT를 반환하면 Graph가 추가 시도 가능 여부를 확인합니다. 기본 max_extraction_retries=1이면 최초 실행과 추가 1회, 총 2회입니다. 상한에 도달하면 Graph가 NEEDS_FIX로 바꾸고 사람 검토로 이동합니다.

오류 이벤트의 unresolved 검사와 오류 stage 이동도 Graph가 관리합니다. Reviewer가 error_events를 임의로 읽거나 삭제하지 않습니다.

LLM을 쓰더라도 validation=false인 결과를 READY_FOR_HUMAN으로 허용하지 않는 최종 규칙 검사를 두세요. 기존 Graph는 사람 승인 시에도 validation과 미해결 오류를 다시 검사합니다.

## 7. 교체

```python
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.agents.reviewer_agent import ReviewerAgent

ontology = OntologyService()
registry = mock_registry(ontology)
registry.register(ReviewerAgent(), replace=True)
registry.validate_complete()
```

이 예시는 신규 `src/ontoproduct/agents/reviewer_agent.py`에 ReviewerAgent를 구현한 뒤 실행합니다. 현재 저장소에는 이 신규 파일이 없습니다.

LLM을 사용하는 구현이면 생성자에 llm_service를 넣는 형태로 합의합니다. 기존 Graph의 routing/human_review를 새로 만들지 않습니다.

## 8. 테스트

| 상황 | 기대 |
| --- | --- |
| 필수 AI 속성 누락 | RE_EXTRACT, 정확한 retry_fields |
| 낮은 AI 신뢰도 | 합의한 재추출 정책 |
| HUMAN 속성 confidence=null | 재추출 대상 제외 |
| locked 필드 | 수정·재추출 대상 제외 |
| 낮은 분류 신뢰도 | REMAP_ONTOLOGY |
| locked product_class | 수동 분류 유지 |
| validation 오류 | 등록 불가, 적절한 수정/재시도 결정 |
| 모두 정상 | READY_FOR_HUMAN, can_register=true |
| 중복 후보 | reason에 검토 정보, 최종 사람 승인 유지 |
| 자동 시도 상한 | Graph가 NEEDS_FIX로 전환, 무한 반복 없음 |
| 잘못된 decision 또는 NEEDS_FIX+true | schema 거부 |
| 실제 Graph 승인 전 | DB 제품 추가 없음 |

신규 테스트 작성 후:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_real_reviewer.py tests\test_workflow.py tests\test_human_interrupt.py tests\test_manual_overrides.py -q
```

## 9. 완료 기준

판단 이유와 다음 동작이 맞고, 사람 수정·retry 상한·최종 승인 흐름을 보존해야 합니다. Extraction 담당자에게 retry_fields, Ontology 담당자에게 재매핑 정책, UI 담당자에게 사용자에게 보여줄 reason 예시를 전달합니다.
