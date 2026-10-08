# SHACL 등록 검증 정책

기준일: 2026-10-09. 순차 실행 요청의 1A 산출물이다. 아래 정책으로 1B를 구현한다. schema·CONTRACTS·Graph의 데이터 모양은 유지한다.

## 적용 경로와 결정

`validate_registration_product(product, mapping, ontology)`가 기존 `validate_product` 결과와 `ontology.validate_semantics` 결과를 결합한다. Real ValidationAgent와 RegistrationService가 같은 함수를 사용한다. 기본 `validate_product`와 ValidationMock은 기존 규칙 계약을 유지한다. runtime의 실제 RegistrationService는 Mock 화면에서도 승인 직전에 의미 검증을 한다.

기본 온톨로지와 명시적으로 정렬된 semantic_model에는 SHACL을 적용한다. semantic_model 없는 사용자 정의 OntologyService는 기존 규칙 검증만 지원하며, 기본 모델을 대신 주입하지 않는다. 기본 모델에서 의미 검증 실행 예외·알 수 없는 위반은 성공이나 warning으로 숨기지 않는다. 예외는 Wrapper 오류 경로 또는 직접 등록 호출자에게 전달한다. 실행 실패 시 저장하지 않는다.

## 출력 대응표

현재 RDF 출력은 `{valid, issues, report}`이며 issue는 `{focus_node, path, message, constraint}`이다. 비교 위반의 path는 빈 문자열이고 constraint는 `SPARQLConstraintComponent`여서 규칙을 식별할 수 없다. 일반 위반의 message에는 실행마다 다른 blank node 식별자가 들어갈 수 있다.

| 원본 | 업무 field / code | 정책 |
| --- | --- | --- |
| 속성 predicate URI | `attributes.<key>` | semantic_model.properties의 namespace + predicate로 대응. mass는 weight에 대응한다. |
| 필수값 MinCount | 대응 속성 / MISSING_REQUIRED | 기존 동일 code·field 오류가 있으면 기존 메시지와 충돌 근거를 유지한다. |
| 생성 제품의 NodeConstraint | 대응 속성 / 기존 TYPE·UNIT·RANGE | 동일 필드의 하위 SHACL 제약과 기존 오류가 함께 설명하는 경우만 중복 제거한다. 하위 근거 없이 NodeConstraint만 남으면 독립 CLASS 오류로 보존한다. |
| 빈 path SPARQL 비교 | left 속성 / RANGE | 모델 comparisons의 클래스·left·right·operator와 제품 값을 사용한다. less_than 위반은 `inner_diameter must be less than outer_diameter`로 안내한다. message 부분 문자열로 비교를 식별하지 않는다. |
| 설명되지 않는 일반/비교 위반 | 대응 속성 또는 product_class / CLASS | SHACL 위반이라는 안정적인 안내로 차단한다. 기존 CLASS는 온톨로지 적합성 실패의 호환 코드로 재사용한다. |

비교 후보는 제품 클래스 및 조상에 적용되는 정의에서 얻는다. 규칙 TYPE·UNIT·RANGE 오류가 있는 비교 피연산자로 추가 관계 오류를 추측하지 않는다. 매핑할 수 없는 비교는 일반 SHACL 오류로 보존한다. Reviewer는 null/충돌 및 단일 속성·관계 오류를 구분하되 관계 오류를 낮은 confidence 재추출로 보내지 않는다.

반환 순서는 기존 규칙 issue 순서를 먼저 보존하고 추가 의미 issue를 field·code·message 순으로 정렬한다. 같은 field라는 이유로 전체 오류를 제거하지 않는다. 동일 업무 code·field·안내만 중복 제거한다. 원문 보고서 전체를 state/schema에 추가하지 않으며 원문 evidence와 HUMAN/locked는 제품에 그대로 남긴다.

## 재현 입력과 검증

`tests/test_rdf_product_ontology.py::test_bearing_dimensions_have_actual_cross_property_constraint`가 12/32 통과, 32/12·12/12 실패를 이미 검증한다. 새 중복 테스트를 만들지 않는다. 기본 규칙은 세 조합 모두 통과하며 SHACL 비교 위반은 빈 path의 SPARQLConstraintComponent다.

inputdata E008(20/20)·E009(30/20)는 실제 Parser 입력으로 같은 차이를 확인한다. E007의 음수 weight는 규칙 `attributes.weight/RANGE`와 SHACL `urn:ontoproduct:ontology:mass/NodeConstraintComponent`가 같은 범위 실패를 설명하므로 기존 RANGE 하나로 안내한다.

D003 두 문서의 필수 rated_power 충돌은 후보를 유지한 null이다. 규칙 MISSING_REQUIRED 메시지 `has conflicting document values`를 유지하고 같은 필수값 SHACL MinCount 중복을 제거한다. 기존 `test_missing_required_conflict_preserves_candidates_but_fails_shacl`도 같은 정책의 근거다. 필수 충돌과 다른 필드 관계 위반이 함께 있으면 둘 다 남긴다. verification.json은 과거 기록이며 현재 실행 결과로 갱신 여부를 판단한다.

1B 수용 조건: 정상 Bearing 등록, 역전·동일 치수의 Graph 및 직접 승인 차단, 수정 후 승인 DB 1개와 JSON 일치, 예외 시 저장 없음, 입력 불변성, 충돌·선택 warning·멱등성 유지. 새 code나 checkpoint 필드가 없어 복원 마이그레이션은 필요 없다. 과거 checkpoint도 승인 시 현재 정책으로 재검증된다.

실행 결과와 운영 연결 완료 여부는 [순차 작업 기록](04_EXECUTION_LOG.md)에 단계별로 기록한다. 정책 문서 작성 자체는 운영 연결 완료가 아니다. OCR·규모·RDF 지속 저장은 이 정책의 결정 범위가 아니다.
