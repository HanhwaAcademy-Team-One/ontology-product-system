# 02 Extraction · 03 Ontology 구현 인계

최초 작성: 2026-10-07.

상세 정책과 완료 조건은 [구현 명세](02_03_IMPLEMENTATION_SPEC.md)를 따른다. **1~7단계 구현과 오프라인 검증을 완료했다. 운영 앱의 목업 교체는 미완료다.** 실제 Parser·LLM adapter·Registry/runtime 연결은 통합 담당자에게 남아 있다. 실제 모델 품질과 PDF/XLSX 파싱을 검증한 결과가 아니다.

추가 요청: IOF·GoodRelations·QUDT를 참고 URI 목록에 두는 수준에서 제품 의미 모델·RDF/OWL·SHACL 구축까지 확장했다. 5~7단계도 완료했다. 현재 제품군의 자체 온톨로지·RDF 변환·SHACL 실행은 완료했으며 산업 전체 모델링·외부 전체 공리 추론·RDF DB 연결까지 완료했다는 뜻은 아니다.

## 진행 상태

| 단계 | 상태 | 완료 증거 |
| --- | --- | --- |
| 명세 정리 | 완료 | 상세 명세와 인계 문서 생성 |
| 1. 공통 기반 | 완료 | 기반·기존 회귀 테스트 69 passed |
| 2. Extraction | 완료 | Extraction·기반·기존 회귀 테스트 98 passed |
| 3. Ontology | 완료 | Ontology·Extraction·기존 회귀 테스트 84 passed |
| 4. Graph·패키징·인계 검증 | 완료 | Graph 7 passed, 최종 전체 278 passed, sdist/wheel 및 독립 로드 확인 |
| 5. 의미 모델·업무 연결 | 완료 | 의미 모델·Ontology·단위·기존 회귀 90 passed |
| 6. RDF/OWL·제품 RDF·SHACL | 완료 | 의미 모델·RDF/SHACL·실제 Agent Graph·Extraction 81 passed; 사례 생성 성공 |
| 7. 확장 회귀·패키징·인계 | 완료 | 최종 전체 313 passed; wheel/sdist 5 YAML·4 TTL 포함 및 독립 SHACL 확인 |

## 재개 지시

1. 구현 명세와 이 문서를 읽는다.
2. 브랜치·변경 사항·적용되는 로컬 지침과 의존 파일을 다시 확인한다.
3. 추가 요청의 5~7단계 중 첫 미완료 단계부터 진행한다. 모두 완료되면 아래 통합 의존성과 품질 검증 항목을 확인한다.
4. 각 단계의 실제 변경·테스트·정책 결정·남은 작업을 이 문서에 갱신한다.

## 명세 작성 시 확인한 사실

- 현재 브랜치: `temp/test_merge_branch`. 작성 시작 시 작업 트리는 깨끗했다.
- 공통 LLM service, ExtractionAgent, OntologyAgent는 기준 시점에 없었다.
- 기존 재추출 병합은 속성만 지원한다.
- 현재 필수 `rated_speed` 정의는 BLDCMotor에 있고 Motor에는 없다.
- 현재 ReviewerMock은 필수 AI 속성의 null/낮은 confidence를 재추출 대상으로 본다.
- 기본 추가 Extraction 재시도는 1회다.
- 현재 오류 화면은 RETRY/STOP만 제공하고 예외는 recoverable=True로 기록된다.
- 값이 null인 선택 속성은 경고이며 클래스 밖 속성도 경고라서, 충돌을 별도 확인하지 않으면 등록을 막지 않는다.

## 구현 파일과 범위

- 실제 Agent: `agents/extraction_agent.py`, `agents/ontology_agent.py`.
- 버전 2.0.0 지침: `prompts/extraction.py`, `prompts/ontology.py`. 추가 의미 모델·물리 제품/제조사 구분·질량/회전수 의미를 전달한다.
- 공통 Protocol·오류: `services/llm_protocol.py`, `agent_errors.py`.
- 동의어·공유 단위·근거·분할·병합·외부 매핑: `mapping_service.py`, `evidence_service.py`, `document_chunks.py`, `attribute_merge.py`, `external_mapping_service.py`.
- `ontology_service.py`의 기존 normalize_unit 호출을 공유 UnitService에 위임했다. 기존 호출 형태와 회귀 동작을 유지했다.
- 데이터: `ontology/property_aliases.yaml`, `unit_mappings.yaml`, `external_mappings.yaml`.
- 테스트: `test_extraction_ontology_foundation.py`, `test_real_extraction.py`, `test_real_ontology_agent.py`, `test_real_document_graph.py`. 통신 대체 helper와 TXT·Parser 출력 JSON fixture를 추가했다.
- 기존 업무 domain 스키마·CONTRACTS·Graph·Validation·Reviewer·UI·운영 runtime과 eval 원문은 변경하지 않았다. 자체 의미 모델 스키마를 별도로 추가했고 RDFLib·pySHACL 의존성을 추가했다. provider SDK·API key 설정은 추가하지 않았다.
- commit·push·PR 생성은 수행하지 않았다. 현재 작업 브랜치의 미커밋 변경으로 남겼다.

## 다음 작업

08 담당자가 실제 LLM adapter와 Parser를 연결한 Registry/runtime을 구성한다. 06 담당자가 충돌·confidence의 Review 정책을 확인한다. Validation 담당자와 08 담당자는 새 SHACL 결과를 기존 업무 Validation 결과와 합칠 정책 및 호출 위치를 정한다. 현재 Validation 노드는 validate_semantics를 자동 호출하지 않으므로 내경<외경 제약이 운영 흐름에 자동 적용된 것은 아니다. 이후 실제 모델·문서 평가를 진행한다.

## 외부 기반 구축 진행 기록

- 5단계: product_model.yaml에 모델/물리 제품/제조사 계층, 관계 domain/range, 속성 의미·등록 제약·분류 규칙을 정의했다. 기본 OntologyService는 이 모델에서 업무 정의를 투영하고 기존 ontology.yaml과 일치 여부를 검사한다. 기본 OntologyAgent는 데이터로 정의한 분류 규칙을 사용하고 LLM에는 의미 모델도 전달한다.
- 공유 단위 카탈로그에 QUDT 물리량 종류와 SI 차원을 연결했다. 검증한 외부 참조는 12개에서 23개로 확장했다. 제조사 이름만으로 조직/전역 동일성을 선언하지 않고, weight의 실제 의미를 질량으로 명시했다.
- 5단계 검증: `.venv/Scripts/python.exe -m pytest tests/test_product_semantic_model.py tests/test_real_ontology_agent.py tests/test_extraction_ontology_foundation.py tests/test_ontology.py -q -W error::pytest.PytestCacheWarning` → **90 passed**.
- RDFLib 7.6.0·pySHACL 0.40.1 및 필요한 전이 의존성을 잠금 파일에 추가했다. 실제 LLM·운영 앱 연결 상태는 그대로 미완료다.
- 6단계: RdfOntologyService, OntologyService.to_rdf/validate_semantics, RDF/OWL·SHACL 산출물 및 모터·베어링 예제를 구현했다. 원문 값·근거/위치·충돌 후보는 evidence 노드에 보존한다. 물리 제품·제조 조직은 명시적인 사실을 전달할 때만 생성한다.
- QUDT 공식 확인에서 현재 hasUnit URI와 rpm에 적용 가능한 RotationalFrequency를 선택했다. angular_velocity라는 초기 로컬 수량명은 rotational_frequency로 명확히 바꿨다. 기존 rpm 표준값·업무 schema는 유지한다.
- 6단계 검증: `.venv/Scripts/python.exe -m pytest tests/test_product_semantic_model.py tests/test_rdf_product_ontology.py tests/test_real_document_graph.py tests/test_real_extraction.py -q -W error::pytest.PytestCacheWarning` → **81 passed**. JSON-LD 왕복 테스트에서 RDFLib 내부 ConjunctiveGraph 사용의 DeprecationWarning 1개가 있으나 테스트는 통과했다.
- `.venv/Scripts/python.exe scripts/build_product_ontology.py` → 모터 96 triples·베어링 40 triples, SHACL conforms. 자체 모델 설명·실행 계약은 [제품 온톨로지 문서](03_PRODUCT_ONTOLOGY.md)에 정리했다.
- 7단계 최종 전체: `.venv/Scripts/python.exe -m pytest -q -W error::pytest.PytestCacheWarning` → **313 passed**, 위 RDFLib JSON-LD DeprecationWarning 1개. 공유 단위 카탈로그 주입이 업무 정규화와 RDF 정규화에서 다르지 않은지도 검증했다.
- `uv --cache-dir .uv-cache sync --locked --offline` 성공. pyproject.toml·requirements.txt·uv.lock의 RDF 의존성을 맞췄다.
- `uv --cache-dir .uv-cache build --offline --out-dir .pytest_tmp/package-check-ontology-model` 성공. wheel/sdist에 YAML 5개와 TTL 4개 포함, runtime/cache 제외, 요구 의존성 확인. 별도로 푼 wheel을 `python -I`로 읽어 의미 모델·단위·OWL/SHACL 일치·모터와 베어링 SHACL을 실행했다.
- 자체 온톨로지의 모델/물리 제품 계층을 SPARQL로 질의하고, 관계·수치·출처·충돌 보존, 오류 제약, 외부 네트워크 차단 상태에서도 SHACL이 동작함을 확인했다. 실제 Agent Graph의 최종 사람 수정 제품도 새 SHACL API로 검증했다.

## 확정 인터페이스

```python
ExtractionAgent(llm_service, *, ontology=None, aliases=None,
                max_chars=12000, overlap_chars=128)
OntologyAgent(ontology, llm_service=None, *, aliases=None, external_mappings=None)
OntologyService(path=None, *, definition=None, unit_service=None, semantic_model=None)
```

Extraction의 ontology 생략 시 기본 정의를 로드한다. 통합에서는 두 Agent에 같은 OntologyService를 전달하여 단위 서비스와 정의를 공유한다. Ontology는 llm_service가 없으면 규칙 분류, 있으면 모델 분류를 사용한다. 수동 분류가 있으면 모델 호출 없이 우선한다.

```python
generate_structured(*, task: str, payload: dict, response_schema: type[T]) -> T
```

반환은 요청받은 response_schema의 검증된 Pydantic model이어야 한다. dictionary·문자열·다른 model 반환은 오류다. Agent가 model_dump 후 다시 검증한다. 실제 adapter가 이를 구현해야 하며 Protocol만으로 API 호출이 생기지 않는다.

- Extraction의 response_schema는 기존 ExtractedProduct와 동일한 필드의 `ExtractionResponse`다. 내부 속성 confidence만 엄격한 숫자로 제한하여 boolean·숫자 문자열을 거부한다. Graph 출력은 기존 ExtractedProduct다.
- Extraction payload: `instructions`, `prompt_version`, `documents`, `property_aliases`, `requested_fields`, `locked_fields`, `ontology_context`, `semantic_model`.
- documents는 청크 단위 source_file/text/page다. 긴 Excel 행을 나누면 `location_prefix`가 payload 메타데이터에만 추가된다. Agent 출력에 새 필드는 없다.
- requested_fields/locked_fields는 표준 속성 이름으로 정규화된다. retry가 아니면 requested_fields는 null이다. 잠금이 항상 우선하며 전부 잠기면 호출이 없다.
- Ontology response_schema는 `ClassSelection(product_class: str | None, confidence: float)`이며 점수는 엄격한 유한 숫자 0~1이다.
- Ontology payload: `instructions`, `prompt_version`, `extracted_product`, `allowed_classes`, `class_definitions`, `external_references`, `semantic_model`.
- semantic_model은 기본 모델에서 2.0.0 의미 context다. 임의의 별도 ontology에 연결된 의미 모델이 없으면 null이다. adapter는 이 context를 신뢰된 업무 정의로 전달한다. 근거 문자열은 계속 비신뢰 입력이다.
- 추가 API: `OntologyService.to_rdf(product, *, record_id, item_id=None, manufacturer_is_organization=False)` → RDFLib Graph. `OntologyService.validate_semantics(product, *, record_id="validation")` → `{valid: bool, issues: list, report: str}`. Agent 출력 state에 RDF 객체를 넣지 않는다.
- adapter는 instructions를 신뢰된 지침에, documents/evidence는 비신뢰 입력에 연결한다. 실제 모델·timeout·짧은 통신 retry와 공급자 메타데이터는 08 담당자가 설정한다.
- 현재 health_check는 계약 수준이며 외부 모델 연결·권한·잔액 확인이 아니다.

## 확정 정책

- 충돌 evidence 형식: `@@ONTOPRODUCT_CONFLICT_V1@@` + 줄바꿈 + 후보 ProductAttribute JSON 배열. 같은 값의 다중 근거는 `@@ONTOPRODUCT_EVIDENCE_V1@@`로 구분한다. 원문 CONFLICT 단어는 표기가 아니다. 후보에는 원래 값·단위·confidence·근거·출처·페이지가 포함된다.
- 단일 근거는 원문 인용이다. 여러 위치의 근거는 위 문자열 안에 후보별로 보존한다. 여러 출처/페이지면 상위 source_file/page는 null이다. Excel 셀 인용은 해당 원문 행 전체로 복원하며 여러 시트·행에서 같은 인용이 발견되면 위치를 요구한다.
- 근거 비교는 공백만 정규화한다. 원문 대소문자·문장부호·전각/반각은 유지한다. 추가로 값·단위의 인용 내 존재를 검사한다. Excel 위치 숫자·셀 주소는 숫자값 근거에서 제외한다.
- 숫자 인용은 소수점·쉼표 천 단위·과학 표기법을 지원한다. boolean은 true/false, yes/no, 예/아니오의 명시적 표현을 지원한다. 의미 분석 전체를 보장하는 검증은 아니며 지원하지 않는 표기는 응답 검증 오류가 될 수 있다.
- 알려진 명령형 문구를 사양 근거로 사용하는 응답을 거부하고, 프롬프트 지침과 원문을 분리했다. 이 검사와 transport 대체 테스트는 모든 prompt injection의 방어 또는 실모델 품질을 증명하지 않는다.
- max_chars는 청크의 문자 수 상한이다. PDF 페이지·Excel 행을 우선 유지하고 긴 단일 행은 overlap_chars만큼 겹쳐 나눈다. 본문을 잘라 버리지 않는다. 토큰 수 상한과 모델 context 관리는 실제 adapter에서 확인해야 한다.
- 공유 숫자 비교: rel_tol=1e-9, abs_tol=0.0. 같은 값은 원래 대표값·단위를 보존하고 모든 근거와 최저 점수를 유지한다. 점수 없는 후보가 있으면 null이다.
- Extraction은 mapping 또는 검증된 후보 클래스 기준으로 필수 충돌을 null로 기록한다. 선택·클래스 밖·판정 불가·제품명 충돌은 DocumentConflictError다.
- Ontology는 AI/수동 최종 클래스의 상속 속성으로 모든 unresolved 충돌을 다시 확인한다. 최종 클래스에서 선택·클래스 밖이면 오류다. 속성 제거로 회피하지 않는다. 유효한 수동 값은 적용 가능한 클래스 안에서만 해결로 인정하고 최종 Graph 병합에 맡긴다.
- 규칙 분류: 내경·외경이 있고 모터 신호가 없으면 Bearing. 제조사와 전압/출력/속도 중 두 항목 이상이 있고 베어링 신호가 없으면 모터. 이때 candidate_class가 BLDCMotor이면 BLDCMotor, 아니면 Motor다. 일반 null 누락은 신호가 아니며 근거 있는 충돌은 신호다. 혼합·부족한 신호는 분류 오류다. 이 규칙은 프로젝트의 초기 판정 정책이지 외부 온톨로지의 분류 공리가 아니다.
- LLM은 허용된 내부 클래스에서 선택하며 Product로 자동 fallback하지 않는다. 수동 Product 등 존재하는 클래스 선택은 사용자의 명시적 선택으로 처리한다.
- 수동/규칙 분류의 1.0은 선택·규칙 충족이다. 모델 점수는 자기평가이며 보정된 확률이 아니다. 누락된 모델 분류 점수는 오류다. 낮은 점수는 높이지 않는다.
- 현재 ReviewerMock의 0.70 기준은 06 담당자에게 인계하며 실제 Reviewer의 확정 정책으로 취급하지 않는다.
- retry_fields는 알려진 속성만 지원한다. product_name/candidate_class 등은 오류다. 재추출 metadata는 null이며 기존 병합이 제품 이름·후보를 보존한다.
- 미지원 단위는 Ontology에서 원래 값·단위를 보존하여 Validation으로 전달한다.

## 기존 1~4단계 검증 기록

단계별 수치는 해당 시점의 완료 증거이며 아래 최종 전체 실행에는 후속 검증 보강도 포함된다.

- 1단계 검증: `.venv/Scripts/python.exe -m pytest tests/test_extraction_ontology_foundation.py tests/test_ontology.py tests/test_manual_overrides.py tests/test_agent_contracts.py -q -W error::pytest.PytestCacheWarning` → **69 passed**.
- 2단계 검증: `.venv/Scripts/python.exe -m pytest tests/test_real_extraction.py tests/test_extraction_ontology_foundation.py tests/test_manual_overrides.py tests/test_human_interrupt.py tests/test_agent_contracts.py -q -W error::pytest.PytestCacheWarning` → **98 passed**.
- 3단계 검증: `.venv/Scripts/python.exe -m pytest tests/test_real_ontology_agent.py tests/test_real_extraction.py tests/test_ontology.py tests/test_manual_overrides.py -q -W error::pytest.PytestCacheWarning` → **84 passed**.
- 4단계 Graph: `.venv/Scripts/python.exe -m pytest tests/test_real_document_graph.py -q -W error::pytest.PytestCacheWarning` → **7 passed**.
- 당시 전체: `.venv/Scripts/python.exe -m pytest -q -W error::pytest.PytestCacheWarning` → **278 passed**. 추가 구축 이후의 최종 결과는 위 313 passed다.
- `uv --cache-dir .uv-cache build --offline --out-dir .pytest_tmp/package-check-02-03` → sdist/wheel 빌드 성공.
- wheel과 sdist에 ontology.yaml 및 신규 YAML 3개 포함 확인. wheel을 별도 폴더에 풀고 `python -I`로 해당 경로의 모듈을 가져와 동의어·600 W 변환·외부 참조 12개를 실제 로드했다.
- build가 cache 포함 가능성 경고를 냈지만 sdist 내부 검사에서 .uv-cache/.pytest_tmp가 포함되지 않았음을 확인했다.
- Graph에서 필수 충돌은 기본 추가 재추출 1회 뒤 NEEDS_FIX와 사람 검토로 이동했다. 두 문서인 fixture는 최초·추가 각 2회로 총 4회의 transport 호출이었다.
- 결정적 선택 충돌/분류 오류는 RETRY 후 다시 오류가 되었고 STOP으로 종료했다. 이 화면에서 수정·분류 변경은 지원하지 않는다. recoverable=True와 업무 retry 제한은 별개다.
- 사람의 BLDCMotor→Motor 및 필수→선택 클래스 변경으로 충돌이 숨겨지지 않음을 확인했다. 수동 수정·단위 변환·잠금 보호·승인 흐름도 검증했다.
- 외부 통신만 canned transport로 대체했다. Parser fixture 전달과 Mock Reviewer/Registration을 사용했으므로 이 Graph 검증은 운영 Parser·실모델·실제 저장의 완료 증거가 아니다.

## 외부 자료와 남은 통합 작업

출처·검증 범위는 [외부 참고 기록](02_03_EXTERNAL_SOURCES.md)에, 실행 참조와 버전은 external_mappings.yaml에 있다. 현재 확인한 URI는 23개이며 이를 사용하는 자체 하위 클래스·관계·수치 구조를 구성했다. 외부 분류·등록 규칙 또는 equivalence 공리를 복사하지 않았다.

- 06 담당자: confidence 의미·현재 0.70 기준·필수 충돌 재추출 비용·최종 클래스 변경의 충돌 정책을 확인한다.
- 08 담당자: 실제 Protocol adapter, Parser 결과, 실제 Registry/runtime 실행 모드를 연결한다. 오류 종류별 recoverable 정책과 수동 해결 UX 개선을 별도 검토한다.
- SDK timeout/통신 retry는 adapter에서 설정하고 Graph의 업무 retry와 구분한다.
- 실제 모델·프롬프트 품질과 문서 평가: 미실행. 실제 PDF/XLSX 바이너리 파싱: 미실행.
- 운영 목업 교체: 미완료. 기본 mock_registry와 UI runtime을 변경하지 않았다.
- 브랜치: `temp/test_merge_branch`. commit·push·PR 생성 없이 변경을 남겼다.
