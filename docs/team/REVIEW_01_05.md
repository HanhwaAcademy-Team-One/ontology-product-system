# 01~05 구현 검토: 설계와 다르게 동작하는 부분

> **현재 상태 (2026-10-08):** #1~#5는 구현되어 `tests/test_review_01_05.py`의 9개 테스트가 통과합니다(xfail 없음). 아래 재현과 목업은 수정 전 검토 기록입니다. #6과 합의된 한계는 후속 항목이며, 현재 점검과 남은 작업은 [04 Validation §9](04_VALIDATION.md#9-점검-결과와-남은-작업)를 참고하세요.

기준: `temp/test_merge_branch` @ `8b128df` (origin/main #2·#3 머지 후). 비교 기준 문서는 [00](00_COMMON.md)~[05](05_DUPLICATE.md), [02·03 구현 명세](02_03_IMPLEMENTATION_SPEC.md)입니다.

- 전체 테스트(`.venv` 기준 `pytest -q`)는 460개 통과, 2개 skip입니다.
- 아래 항목은 **테스트는 통과하지만 설계 의도와 다르게 동작하는 부분**입니다. 재현 결과는 가짜 LLM 응답(`tests/extraction_ontology_helpers.py`)과 실제 Extraction·Ontology Agent·Graph로 직접 확인했습니다.
- 코드 블록은 해결 방향을 보여주는 **목업**입니다. 아직 적용하지 않았습니다.

## 요약

| # | 심각도 | 담당 | 현상 | 해결 위치 |
| --- | --- | --- | --- | --- |
| 1 | 높음 | 02 → UI(08) | 검증을 통과한 제품인데도 AI confidence가 없거나 낮으면 NEEDS_FIX에 갇힘 | `views/registration.py` |
| 2 | 높음 | 02·04 → UI | 문서 간 필수값 충돌이 "누락"으로만 보이고 후보값이 화면에 나오지 않음 | `views/registration.py`, `validation_service.py` |
| 3 | 중간 | 03 → UI(08) | LLM 분류 confidence가 0.70 미만이면 NEEDS_FIX에 갇히고, 현재 분류를 "확정"할 방법이 없음 | `views/registration.py` |
| 4 | 중간 | 04 → 08 | ValidationAgent를 구현했지만 Real 모드에 연결하지 않아 여전히 ValidationMock이 실행됨 | `agents/real_registry.py` |
| 5 | 낮음 | 05 → 08 | `agent_metadata()`의 DuplicateService에 ontology가 빠짐(머지 산물). 생성 위치가 두 곳으로 중복됨 | `services/workflow_runtime.py` |
| 6 | 낮음 | 05 → 06 | Reviewer가 duplicate verdict를 판단과 reason에 반영하지 않음 | 06 인계(ReviewerAgent) |

01 Parser는 설계와 다른 동작을 찾지 못했습니다. 확인한 범위는 페이지 규칙, Excel 위치 표기, 같은 이름 파일 구분, 경로 검증, 손상·스캔 PDF 오류입니다.

---

## 1. AI confidence가 없거나 낮은 필수 속성은 사람이 "확인"할 수 없음

**설계**
- 02 §4: confidence는 고정값으로 채우지 않습니다.
- 명세 §8: 점수가 없으면 null로 둡니다.
- 06 §5: 사람이 확인한 속성(HUMAN/locked)은 재추출 대상에서 제외합니다.
- 즉 "AI 값이 불확실하면 사람이 확인해서 등록한다"가 의도된 흐름입니다.

**실제 동작** (재현: 모든 속성 `confidence=None`, 문서 값은 모두 정상)

```
status=NEEDS_FIX  reason='Extraction retry limit reached.'
retry=['manufacturer','rated_voltage','rated_power','rated_speed']  valid=True
→ 다른 항목 수정 후에도 NEEDS_FIX 반복
```

1. ReviewerMock이 confidence=null을 RE_EXTRACT로 판단합니다.
2. 같은 문서를 다시 추출하므로 결과도 같은 null입니다. 상한에 도달하면 NEEDS_FIX가 됩니다.
3. 화면에는 "수정이 필요한 항목이 있습니다"가 뜨지만, 검증 표에는 오류가 없습니다. 사용자는 무엇을 고쳐야 하는지 알 수 없습니다.
4. 수정 폼은 **값이 바뀐 항목만** `edits`로 보냅니다([registration.py:188](../../src/ontoproduct/views/registration.py#L188)). 그래서 맞는 AI 값을 그대로 확인하는 방법이 없습니다.
5. 지금 빠져나가려면 각 값을 다른 값으로 바꿨다가 되돌리는 두 번의 수정이 필요합니다.

Graph는 이미 "같은 값 수정"을 받아서 HUMAN으로 바꾸고 READY_FOR_HUMAN까지 진행합니다(재현 확인). **막는 곳은 UI뿐입니다.**

**해결 목업**: `retry_fields`에 있는 항목을 "확인 필요"로 표시하고, 체크하면 같은 값도 edits로 보냅니다. `mark_needs_fix`는 retry_fields를 보존하므로 이 값을 그대로 쓸 수 있습니다.

```python
# views/registration.py — _edit_form
flagged = set(state["review_result"].get("retry_fields", []))
if flagged:
    st.warning("AI 신뢰도가 낮거나 없는 항목: "
               + ", ".join(LABELS.get(k, k) for k in sorted(flagged))
               + " — 원문과 비교해 값이 맞으면 'AI 값 확인'을 체크하세요.")
...
for key, prop in properties.items():
    ...
    confirm = (
        left.checkbox("AI 값 확인", key=f"confirm_{thread_id}_{revision}_{key}")
        if key in flagged and value is not None
        else False
    )
    inputs[key] = (text, unit, prop.type, confirm)
...
for key, (text, unit, property_type, confirm) in inputs.items():
    value = parse_value(text, property_type)
    old = product["attributes"].get(key, {})
    if confirm or value != old.get("value") or (value is not None and unit != old.get("unit")):
        edits[f"attributes.{key}"] = ProductAttribute(value=value, unit=unit).model_dump(mode="json")
```

화면 목업:

```
┌ 제품 정보 수정 ────────────────────────────────────────────┐
│ ⚠ AI 신뢰도가 낮거나 없는 항목: 정격 전압, 정격 속도        │
│   원문과 비교해 값이 맞으면 'AI 값 확인'을 체크하세요.      │
│ 정격 전압 *  [ 24        ]  단위 [V  ▾]   ☑ AI 값 확인      │
│ 정격 속도 *  [ 3200      ]  단위 [rpm▾]   ☐ AI 값 확인      │
│ 정격 출력 *  [ 600.0     ]  단위 [W  ▾]                     │
│                                   [ 수정 후 재검증 ]        │
└────────────────────────────────────────────────────────────┘
```

**함께 검토할 것 (02 담당)**: [prompts/extraction.py](../../src/ontoproduct/prompts/extraction.py)는 confidence를 "optional"이라고 안내합니다. 그래서 모델이 null을 자주 반환할 수 있습니다. 명세 §8의 "근거가 검증된 값의 유효 점수는 보존한다"와 충돌하지 않으므로, 근거가 있는 값에는 점수를 반드시 반환하도록 지시하고 VERSION을 올리는 방안을 제안합니다. null 정책 자체는 유지합니다.

**검증 테스트 목업**

```python
def test_confirming_unchanged_ai_value_releases_needs_fix(graph_with_null_confidence):
    graph, cfg = graph_with_null_confidence          # confidence=None 응답으로 NEEDS_FIX 도달
    state = graph.get_state(cfg).values
    product = state["normalized_product"]
    edits = {f"attributes.{k}": {"value": product["attributes"][k]["value"],
                                 "unit": product["attributes"][k]["unit"]}
             for k in state["review_result"]["retry_fields"]}
    graph.invoke(Command(resume={"action": "EDIT", "edits": edits}), cfg)
    assert graph.get_state(cfg).values["review_result"]["decision"] == "READY_FOR_HUMAN"
```

---

## 2. 필수 속성 충돌이 "누락"으로 숨겨짐

**설계**
- 02 §7: "서로 다른 전압 → 충돌을 숨기지 않고 합의한 정책으로 처리"
- 명세 §7: 충돌 후보 전체를 evidence에 보존합니다.

**실제 동작** (재현: a.txt `24 V`, b.txt `48 V`)

```
NEEDS_FIX  'Extraction retry limit reached.'
[('attributes.rated_voltage', 'Required property rated_voltage is missing')]
value=None, evidence='@@ONTOPRODUCT_CONFLICT_V1@@\n[{"value": 24 ...}, {"value": 48 ...}]'
```

- Extraction은 충돌을 정확히 보존합니다.
- 반면 Validation 메시지는 "missing"이고, 화면은 evidence를 해석하지 않습니다([registration.py](../../src/ontoproduct/views/registration.py)에는 `evidence`를 쓰는 부분이 없음).
- 그래서 사용자는 24 V와 48 V 중 하나를 골라야 한다는 사실을 볼 수 없고, 빈 입력칸만 보게 됩니다.
- 이 경우 같은 충돌을 다시 추출하느라 LLM 호출도 한 번 낭비됩니다. 명세 §10이 인정한 한계입니다.

**해결 목업 A — 화면에 충돌 후보 표시 (UI)**

```python
# views/registration.py
from ontoproduct.schemas.product import ProductAttribute
from ontoproduct.services.evidence_service import evidence_candidates, is_conflict

def _conflict_rows(product):
    rows = []
    for key, raw in product["attributes"].items():
        attr = ProductAttribute.model_validate(raw)
        if is_conflict(attr):
            rows += [{"항목": LABELS.get(key, key), "값": c.value, "단위": c.unit,
                      "출처": c.source_file, "페이지": c.page, "근거": c.evidence}
                     for c in evidence_candidates(attr)]
    return rows

# _review() 안, 검증 결과 표 위에
if rows := _conflict_rows(state["normalized_product"]):
    st.error("문서마다 값이 다른 항목이 있습니다. 원문을 확인해 올바른 값을 입력하세요.")
    st.dataframe(rows, hide_index=True, width="stretch")
```

```
┌ ⛔ 문서마다 값이 다른 항목이 있습니다 ─────────────────────┐
│ 항목      값   단위  출처    페이지  근거                   │
│ 정격 전압  24   V     a.txt   1       Rated Voltage: 24 V   │
│ 정격 전압  48   V     b.txt   1       Rated Voltage: 48 V   │
└────────────────────────────────────────────────────────────┘
```

**해결 목업 B — Validation 메시지 구분 (04 담당)**: code는 `MISSING_REQUIRED` 그대로 두고 message만 바꿉니다. schema와 소비자는 변경하지 않습니다.

```python
# services/validation_service.py
from ontoproduct.services.evidence_service import is_conflict
...
if attr is None or attr.value is None:
    if key in mapping.required_properties:
        detail = ("has conflicting document values"
                  if attr is not None and is_conflict(attr) else "is missing")
        issue(field, "MISSING_REQUIRED", f"Required property {key} {detail}")
```

**해결 목업 C — 06 인계**: 충돌 속성은 재추출해도 결과가 같습니다. Reviewer가 RE_EXTRACT 대신 바로 NEEDS_FIX로 보내면 LLM 호출을 아낄 수 있습니다(§6 목업에 포함).

---

## 3. 낮은 분류 confidence → REMAP 반복 → 현재 분류를 확정할 수 없음

**설계**
- 03 §5: 분류가 불확실하면 "재매핑/사람 검토에 연결"합니다.
- 명세 §9: 낮은 confidence도 정상 출력한 뒤 ReviewerMock의 재매핑 흐름을 사용합니다.

**실제 동작** (재현: Ontology LLM `confidence=0.5`, 속성은 모두 정상)

```
status=NEEDS_FIX  reason='Ontology retry limit reached.'  valid=True  ontology LLM 호출 2회
→ 다른 항목 수정 후에도 NEEDS_FIX 반복
```

- ontology 슬롯의 입력 계약에는 `review_result`가 없습니다. 그래서 REMAP 재시도는 **같은 입력으로 LLM을 다시 호출**합니다.
- 수정 폼은 선택한 분류가 현재 분류와 같으면 `changed_class=None`으로 보냅니다([registration.py:194](../../src/ontoproduct/views/registration.py#L194)). 그래서 "현재 분류가 맞다"고 확정할 수 없습니다.
- 다른 항목을 고치면 `apply_manual_overrides`로 돌아갑니다. Reviewer가 다시 REMAP을 판단하지만 이미 상한에 도달했으므로 NEEDS_FIX가 반복됩니다.
- 빠져나가려면 분류를 다른 값으로 바꿨다가 되돌려야 합니다.

같은 클래스로 `changed_class`를 보내면 수동 분류(confidence 1.0)가 되어 READY_FOR_HUMAN으로 진행합니다(재현 확인). **이것도 막는 곳은 UI뿐입니다.**

**해결 목업 (UI)**

```python
# views/registration.py — _edit_form, 분류 selectbox 아래
locked = set(state.get("locked_fields", []))
confirm_class = (
    "product_class" not in locked
    and st.checkbox("AI 분류 확정 (현재 분류가 맞습니다)",
                    key=f"confirm_class_{thread_id}_{revision}")
)
...
changed_class = (
    selected_class
    if selected_class != product["product_class"] or confirm_class
    else None
)
```

**선택 사항 (계약 변경, 합의 필요)**: REMAP 재시도를 의미 있게 하려면 ontology optional reads에 `review_result`를 추가해야 합니다. 그러면 "이전 선택의 confidence가 낮았다"는 사실을 LLM payload에 전달할 수 있습니다. 00 §10에 따라 통합 담당자와 합의해야 하므로 기본안에서는 제외합니다. 기본안은 UI의 확정 경로입니다.

---

## 4. ValidationAgent가 Real 모드에 연결되지 않음

**설계**
- 04 §8: 기존 검증을 실제 Agent로 분리합니다.
- 04 §7 마지막 행: 병렬 Graph에서 Duplicate와 함께 완료되는지 확인합니다.

**실제 동작**
- [validation_agent.py](../../src/ontoproduct/agents/validation_agent.py)와 단위 테스트는 있습니다.
- 하지만 [real_registry.py](../../src/ontoproduct/agents/real_registry.py)는 parser·extraction·ontology만 교체합니다. 그래서 Real 모드에서도 `ValidationMock`이 실행되고, Agent 모니터에 `is_mock=True`로 표시됩니다.
- `ValidationAgent`를 import하는 곳은 `tests/test_real_validation_agent.py`뿐입니다.
- 병렬 Graph 테스트도 없습니다.
- 검증 결과는 같은 함수를 쓰므로 동일합니다.

**해결 목업**

```python
# agents/real_registry.py
from ontoproduct.agents.validation_agent import ValidationAgent
...
    registry.register(OntologyAgent(ontology, llm_services["ontology"]), replace=True)
    registry.register(ValidationAgent(), replace=True)
    registry.validate_complete()
```

```python
# tests/test_real_registry.py
def test_real_registry_uses_real_validation(...):
    registry = build_document_registry(ontology, parser_service=..., llm_services=...)
    meta = {m["name"]: m for m in registry.metadata()}
    assert meta["validation"]["is_mock"] is False

# tests/test_real_validation_agent.py — 04 §7 '병렬 Graph'
def test_validation_and_duplicate_run_in_parallel(tmp_path):
    registry = mock_registry(ontology)
    registry.register(ValidationAgent(), replace=True)
    registry.register(DuplicateAgent(DuplicateService(repository, ontology)), replace=True)
    graph.invoke(initial_state(...), cfg)
    logs = graph.get_state(cfg).values["agent_logs"]
    assert {"validation", "duplicate"} <= {l["agent"] for l in logs if l["status"] == "success"}
    assert "duplicate_candidates" in state and "validation_result" in state
```

[MOCK_REPLACEMENT_PLAN](../MOCK_REPLACEMENT_PLAN.md)의 "Validation 연결은 남은 범위"라는 표기도 함께 갱신합니다.

---

## 5. Duplicate 슬롯 생성 위치 중복과 머지 회귀

**설계**: 05 §7은 "runtime의 두 생성 위치를 함께 수정하거나 공통 factory로 묶어야 한다"고 경고합니다.

**실제 동작**: 머지 충돌을 해결하면서 [workflow_runtime.py:152](../../src/ontoproduct/services/workflow_runtime.py#L152)만 `DuplicateService(self.products)`로 남았습니다. 59번째 줄은 `self.ontology`를 넘깁니다. 기능 영향은 메타데이터 조회 시 OntologyService를 하나 더 만드는 정도입니다. 다만 두 위치가 어긋나기 쉬운 구조라는 것을 이번 머지가 그대로 보여줍니다.

**해결 목업**

```python
# services/workflow_runtime.py
def _case_registry(self, case_id):
    registry = self.registry_factory(self.ontology)
    registry.register(RegistrationAgent(case_id, self.registration), replace=True)
    registry.register(
        DuplicateAgent(DuplicateService(self.products, self.ontology)), replace=True
    )
    return registry

# graph():          registry = self._case_registry(thread_id)
# agent_metadata(): return self._case_registry("metadata").metadata()
```

---

## 6. (06 인계) Reviewer가 Duplicate·충돌 정보를 판단에 쓰지 않음

05 §4는 "승인·거절은 Reviewer와 사람 검토의 역할"이라고 정합니다. 06 §5.7은 "중복 후보의 의미를 reason에 설명"하도록 정합니다. 하지만 ReviewerMock은 `duplicate_candidates`를 읽지 않습니다. LIKELY_DUPLICATE가 있어도 reason은 "Required properties are valid"뿐입니다. 화면의 후보 표에는 나오므로 사람이 볼 수는 있습니다.

06 담당자가 `reviewer_agent.py`를 만들 때 반영할 목업입니다. 00 지침에 따라 `mocks/agents.py`는 직접 수정하지 않습니다.

```python
# agents/reviewer_agent.py (발췌) — ReviewerMock 판단 순서에 두 가지 추가
conflicts = []
for key in mapping["required_properties"]:
    attr = product["attributes"].get(key)
    if attr and is_conflict(ProductAttribute.model_validate(attr)) \
            and f"attributes.{key}" not in locked:
        conflicts.append(key)          # 재추출해도 같은 충돌 → 재시도하지 않음
        continue
    ...  # 기존 누락/낮은 confidence → retry
if retry:
    decision = "RE_EXTRACT"
elif conflicts:
    decision, reason = "NEEDS_FIX", f"Documents disagree on: {', '.join(conflicts)}"
...
likely = [c["product_name"] for c in state["duplicate_candidates"]
          if c.get("verdict") == "LIKELY_DUPLICATE"]
if decision == "READY_FOR_HUMAN" and likely:
    reason += f" Likely duplicate of existing product(s): {', '.join(likely)}."
```

---

## 합의된 한계 (설계 위반 아님, 참고)

명세에 이미 적힌 정책입니다. 사용자 경험상 막히는 지점이라 다시 정리합니다.

- **선택 속성·제품명 충돌 → `DocumentConflictError`** (명세 §7·§10): 오류 화면은 RETRY/STOP만 제공합니다. 같은 입력이면 RETRY해도 다시 실패하므로 STOP 외에 출구가 없습니다. 오류 화면에서 수정하는 기능은 통합 제안으로 남아 있습니다.
- **SHACL `validate_semantics` 미연결** (handoff): 내경 < 외경 같은 의미 제약은 Validation 노드에서 자동으로 검사하지 않습니다.
- **OCR 미지원** (01 인계 기록).

## 적용 순서 제안

1. 4·5번: 코드 몇 줄과 테스트 1~2개로 끝나며 위험이 낮습니다.
2. 1·3번 UI 확인 경로: Graph를 바꾸지 않고 막힌 흐름을 풉니다.
3. 2번 A(UI 충돌 표시)와 B(메시지 구분).
4. 6번과 confidence 프롬프트: 06·02 담당자와 합의한 뒤 진행합니다.
