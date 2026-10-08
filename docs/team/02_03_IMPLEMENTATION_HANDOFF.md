# 02 Extraction · 03 Ontology 구현 인계

> **현재 연결 상태:** Parser·Extraction·Ontology와 OpenAI adapter·UI Real Registry 연결은 이후 구현되어 있습니다. 아래 “운영 목업 교체 미완료” 등의 문구는 각 단계 당시의 인계 이력입니다. 현재 실행·연결은 [Quick start](../QUICK_START.md)와 [08 통합 가이드](08_INTEGRATION.md)를 따릅니다. Graph Validation의 SHACL 자동 연결과 RDF DB 저장은 여전히 남은 범위입니다.

최초 작성: 2026-10-07.

상세 정책과 완료 조건은 [구현 명세](02_03_IMPLEMENTATION_SPEC.md)를 따른다. **1~7단계 구현과 오프라인 검증을 완료했다. 운영 앱의 목업 교체는 미완료다.** 실제 Parser·LLM adapter·Registry/runtime 연결은 통합 담당자에게 남아 있다. 실제 모델 품질과 PDF/XLSX 파싱을 검증한 결과가 아니다.

추가 요청: IOF·GoodRelations·QUDT를 참고 URI 목록에 두는 수준에서 제품 의미 모델·RDF/OWL·SHACL 구축까지 확장했다. 5~7단계도 완료했다. 현재 제품군의 자체 온톨로지·RDF 변환·SHACL 실행은 완료했으며 산업 전체 모델링·외부 전체 공리 추론·RDF DB 연결까지 완료했다는 뜻은 아니다.

후속 요청으로 온톨로지 탐색 UI에 의미 관계·제품 RDF 시각화를 추가했다. 구현·검증 내용은 아래 시각화 기록을 따른다. 운영 Extraction/Ontology 목업 교체와 Graph Validation 노드의 SHACL 자동 연결은 여전히 미완료다.

**온톨로지 내재화 완료(I-1~I-4).** 운영 온톨로지·제품 RDF·SHACL·Agent context에서 IOF·GoodRelations·QUDT 업무 URI 연결을 제거하고 `urn:ontoproduct:ontology:` 아래 자체 정의로 바꿨다. 외부 → 내부 대응표는 [03_EXTERNAL_CONCORDANCE.md](03_EXTERNAL_CONCORDANCE.md), 라이선스 고지는 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)에 있다. 이 두 문서와 [외부 참고 기록](02_03_EXTERNAL_SOURCES.md)만 외부 URI를 담으며 운영 코드는 이들을 읽지 않는다. 운영 목업 교체 상태는 바뀌지 않았다.

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

### 온톨로지 내재화 (후속 요청)

IOF·GoodRelations·QUDT 업무 URI 연결을 운영 온톨로지·제품 RDF·SHACL·Agent context에서 제거하고 자체 정의로 바꾸는 작업이다. 시작 기준: `temp/test_merge_branch` 깨끗한 작업 트리, 전체 313 passed.

| 단계 | 상태 | 완료 증거 |
| --- | --- | --- |
| I-1. 의존성 조사·이관 설계 | 완료 | [대응표](03_EXTERNAL_CONCORDANCE.md)에 23개 참조 키의 내부 URI·의미·이관 위치·출처 정리. 단순 치환으로 부족한 7개 항목 식별 |
| I-2. 내부 정의·공통 서비스 전환 | 완료 | RDF 2개 파일 제외 297 passed. 외부 자료 없이 의미 모델·단위·분류 로드 |
| I-3. RDF/OWL·SHACL·Agent context 이관 | 완료 | RDF·의미 모델·Agent·Graph 81 passed, 내재화 테스트 10 passed. TTL 4개 재생성, 모터·베어링 SHACL conforms |
| I-4. 검증·패키징·인계 | 완료 | 전체 329 passed. wheel/sdist 확인, 압축 해제 wheel의 네트워크 차단 로드·SHACL 확인 |

I-1 조사 결과:
- 외부 URI는 `ProductOntology.reference_uri()`를 통해 온톨로지 RDF(상위 클래스·관계, range, 물리량), SHACL(값 노드 클래스·수치·단위·물리량), 제품 RDF(외부 타입·중복 관계 triple), Agent context(`external_uri`, `uri`, `external_references` payload)로 퍼진다. 프롬프트 문구(ontology 2.0.0)에도 external URI 언급이 있다.
- 테스트: `test_rdf_product_ontology.py`, `test_product_semantic_model.py`, `test_real_ontology_agent.py`가 외부 참조를 직접 확인한다. 빌드 스크립트는 서비스만 호출한다.
- 앱 데이터(`runtime/`)에는 외부 URI를 담은 저장 RDF가 없다. 제품은 JSON으로 저장되고 RDF는 필요할 때 생성된다. 이관 대상은 저장소의 생성 TTL 4개뿐이며 생성 스크립트로 다시 만든다.
- 결정: `external_mappings.yaml`과 `external_mapping_service.py`는 제거하고 내용은 대응표 문서로 옮긴다. 출처 메타데이터는 URL 없이 product_model.yaml `sources`에 둔다. 측정 구조(QuantityValue 등)는 product_model.yaml `measurement`, 물리량·단위 설명은 unit_mappings.yaml이 단일 원본이다.

I-2 내부 정의·공통 서비스:
- product_model.yaml(모델 버전 2.0.0 → 3.0.0): `sources`(로컬 출처 3개, URL 없음), `measurement`(QuantityValue·QuantityKind·Unit·numericValue·hasUnit·hasQuantityKind), 상위 개체 클래스 PhysicalArtifact·Organization·BusinessEntity를 추가했다. 개체 클래스의 `parent`/`external_parents`를 `parents` 목록(다중 상속)과 `sources`로, 관계의 `external_parent`를 `sources`로 바꿨다.
- unit_mappings.yaml: 물리량 종류의 외부 참조 키(`reference`)를 label·description·sources로, 단위에 label·sources를 추가했다. 배율·차원·변환 정책은 바꾸지 않았다.
- ProductOntology: 외부 참조 조회(`reference_uri`, `references`)를 제거했다. 다중 상속 DAG 순환, 알 수 없는 상위·출처, 측정 용어 이름 충돌, 사용 단위·물리량의 로컬 정의 누락, 정의 데이터 안의 외부 URL(`://`)을 로드 시 거부한다. `entity_ancestors()`, `used_units()`, `used_quantities()`를 추가했다.
- OntologyAgent: `external_mappings` 생성자 인자와 payload `external_references`를 제거했다. 프롬프트 ontology 2.0.0 → 3.0.0(외부 URI 문구 제거). extraction 프롬프트 문구는 바뀌지 않아 2.0.0을 유지했다.
- 검증: RDF 2개 파일을 제외한 `pytest` → **297 passed**.

I-3 RDF/OWL·SHACL·Agent context:
- RdfOntologyService: 외부 접두사(gr·qudt·unit·qk) 바인딩과 외부 subClassOf/subPropertyOf를 제거했다. 내부 IRI 규칙 `op:<이름>`, `op:quantitykind/<key>`, `op:unit/<기호>`, `op:source/<출처>-<버전>`을 적용했다. 측정 구조를 OWL 클래스·속성으로 정의하고 물리량 종류·단위 개체에 이름·설명·차원·기호·배율·표준 단위를 기록한다. 출처는 `op:SourceRecord`(제목·버전·SPDX 라이선스·귀속 문자열)로 기록한다.
- 제품 RDF: 외부 타입과 중복 관계 triple(`gr:hasManufacturer`, `gr:hasMakeAndModel`)을 제거했다. 개체 노드에는 상위 개체 타입을 명시적으로 기록한다(제조사 → BusinessEntity, 조직 → Organization, 물리 제품 → PhysicalArtifact). 카탈로그 밖 단위는 문자열로 남겨 SHACL이 보고한다.
- SHACL·베어링 SPARQL 제약은 내부 numericValue·hasUnit·hasQuantityKind를 사용한다. 필수·범위·유한성·표준 단위·물리량·모델/물리 제품 구분 제약은 그대로다.
- `scripts/build_product_ontology.py` → 모터 94 triples·베어링 39 triples, SHACL conforms. TTL 4개를 다시 만들었다. 외부 IRI는 RDF·RDFS·OWL·XSD·SHACL·Dublin Core Terms만 남았다.
- 새 테스트 `tests/test_ontology_internalization.py`(10개): src/ 패키지 파일·생성 그래프·저장 TTL의 외부 업무 URI 부재, 출처 기록, RDF 단위 정보와 UnitService 일치, 미지원 단위, 명시적 상위 타입, Agent payload, 네트워크 차단 로드, 대응표 누락 검사.

I-4 검증·패키징:
- 전체: `.venv/Scripts/python.exe -m pytest -q -W error::pytest.PytestCacheWarning` → **329 passed**, 기존 RDFLib JSON-LD DeprecationWarning 1개. 시작 기준 313 passed와 구분한다(내재화 테스트 10개와 변경 테스트가 늘었다).
- `uv --cache-dir .uv-cache build --offline --out-dir .pytest_tmp/package-check-internalization` 성공. wheel에 ontology.yaml·product_model.yaml·property_aliases.yaml·unit_mappings.yaml과 TTL 4개 포함, external_mappings 없음, 패키지 파일의 외부 업무 URI 0건. sdist에 대응표·고지 문서 포함, .uv-cache/.pytest_tmp 미포함.
- wheel을 별도 폴더에 풀고 `python -I`로 그 경로의 모듈만 가져와 소켓 연결을 막은 상태에서 정의 로드, 0.6 kW → 600 W, ontology 321 triples 생성, 베어링 SHACL 통과·내경≥외경 위반 판정을 확인했다.
- 실제 LLM 호출은 하지 않았다. Agent payload 검사는 canned transport 기준이다.

내재화 후 남은 사항:
- **시각화 병합 후 조정 완료:** 현재 `temp/test_merge_branch`의 시각화 코드에 남은 삭제 API·외부 URI 접두사·색상 분류를 내부 모델 계약으로 교체했다. 아래 “시각화 병합 후 내재화 조정”의 실제 검증 결과를 따른다. 운영 목업 교체와 SHACL 자동 연결은 별도 미완료 항목이다.
- 외부 표준 데이터와의 상호운용은 기본 제공되지 않는다. 필요하면 대응표로 운영 RDF와 분리된 정렬 그래프를 만든다.
- 이전 버전 RDF를 외부에 내보낸 적이 있다면 원본 제품 JSON에서 다시 생성한다. 앱 데이터에는 저장 RDF가 없어 이관 대상이 없다.

## 재개 지시

1. 구현 명세와 이 문서를 읽는다.
2. 브랜치·변경 사항·적용되는 로컬 지침과 의존 파일을 다시 확인한다.
3. 1~7단계와 내재화 I-1~I-4는 완료했다. 시각화 병합 후 내재화 조정도 완료했다. 다음은 운영 목업 교체(LLM adapter·Registry/runtime 연결)와 SHACL 자동 연결 정책 확정이다.
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
- 지침: `prompts/extraction.py` 2.0.0, `prompts/ontology.py` 3.0.0. 의미 모델·물리 제품/제조사 구분·질량/회전수 의미를 전달한다.
- 공통 Protocol·오류: `services/llm_protocol.py`, `agent_errors.py`.
- 동의어·공유 단위·근거·분할·병합: `mapping_service.py`, `evidence_service.py`, `document_chunks.py`, `attribute_merge.py`. 의미 모델·RDF: `product_ontology_service.py`, `rdf_ontology_service.py`. 외부 매핑 서비스는 내재화로 제거했다.
- `ontology_service.py`의 기존 normalize_unit 호출을 공유 UnitService에 위임했다. 기존 호출 형태와 회귀 동작을 유지했다.
- 데이터: `ontology/product_model.yaml`, `ontology.yaml`, `property_aliases.yaml`, `unit_mappings.yaml`, `rdf/*.ttl`. `external_mappings.yaml`은 내재화로 제거했다.
- 테스트: `test_extraction_ontology_foundation.py`, `test_real_extraction.py`, `test_real_ontology_agent.py`, `test_real_document_graph.py`, `test_product_semantic_model.py`, `test_rdf_product_ontology.py`, `test_ontology_internalization.py`. 통신 대체 helper와 TXT·Parser 출력 JSON fixture를 추가했다.
- 1~7단계에서 기존 업무 domain 스키마·CONTRACTS·Graph·Validation·Reviewer·UI·운영 runtime과 eval 원문은 변경하지 않았다. 후속 시각화 요청에서 온톨로지 탐색 UI를 확장했다. 자체 의미 모델 스키마를 별도로 추가했고 RDFLib·pySHACL 의존성을 추가했다. provider SDK·API key 설정은 추가하지 않았다.
- 1~7단계 변경은 사용자 요청으로 `temp/test_merge_branch`에 커밋·push되었다. 이후 내재화 변경(`606a269`, `d086f96`, `c27f4f3`)과 시각화 변경(`5998633`, `76a0220`)도 커밋되어 현재 브랜치에 병합되었다.

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

## 후속 시각화 구현 기록 (내재화 이전 이력)

- `services/ontology_visualization.py`: 실제 RDF에서 Mermaid 노드·관계, 전체 triple 표, 속성의 입력 값·표준값·근거 표를 생성한다. 문자열은 Mermaid 문법을 깨지 않도록 이스케이프하고 RDF graph는 변경하지 않는다.
- `views/ontology_graphs.py`, `views/ontology_explorer.py`: 선택 제품군/전체 의미 구조, 모터·베어링 예제와 저장된 제품 그래프, 근거 표시, RDF/JSON 다운로드, SHACL 검사 버튼을 제공한다. 기존 클래스 계층·속성 표·단위 미리보기는 유지한다.
- 시각화는 주요 관계를 보여 주는 투영이며, 전체 triple은 펼쳐진 표·Turtle 원문과 RDF 다운로드에서 확인한다. 저장된 제품은 실제 레코드에서 RDF를 생성해 읽기만 하고 예제를 DB에 넣지 않는다. 운영 LLM·Parser·Agent Registry 연결을 바꾸지 않았다.
- `tests/test_ontology_visualization.py`: 실제 RDF 관계와 단위·값, 클래스별 범위, 원문 위치, 표시 문자열 이스케이프, 샘플 전환·근거·다운로드·SHACL, 저장 제품 표시의 DB 불변성을 검증한다.
- 관련 테스트와 기존 탐색 UI 회귀: `.venv/Scripts/python.exe -m pytest tests/test_ontology_visualization.py tests/test_phase3_ui.py::test_ontology_hierarchy_inherited_fields_and_real_unit_conversion -q -W error::pytest.PytestCacheWarning` → **7 passed**.
- 시각화 추가 후 전체 회귀: `.venv/Scripts/python.exe -m pytest -q -W error::pytest.PytestCacheWarning` → **319 passed**, 기존 RDFLib JSON-LD DeprecationWarning 1개.
- 당시 시각화 브랜치에서는 실제 Chrome에서 Mermaid 제품 그래프·Excel 근거 표·베어링 SHACL 통과를 확인했다. 이 결과는 아래 병합 후 조정의 브라우저 검증을 대신하지 않는다. agent-browser CLI가 설치되어 있지 않아 연결된 브라우저로 검증했다. 미리보기는 `.pytest_tmp/ontology-preview-runtime`의 별도 DB를 사용한다.
- 실행 방법과 표시 범위는 [제품 온톨로지 문서](03_PRODUCT_ONTOLOGY.md)의 그래프로 보기 절에 정리했다. 기존 운영 데이터에서 보려면 정상 실행 환경의 `uv run streamlit run app.py`로 앱을 연다.

## 시각화 병합 후 내재화 조정 (2026-10-07)

작업 시작 브랜치는 `temp/test_merge_branch`, `git status --short`는 `?? AGENTS.md`였다. 기존 AGENTS.md를 보존했다. 최근 이력은 `cc56031`(Ruff 개발 의존성 고정), `3af4966`(Ruff indent 자동화), `1dc6f4c`(병합 후 문서의 legacy 정보 정리)이다. 과거 문서의 “시각화 브랜치 후속 수정”은 병합된 현재 코드의 조정 완료로 갱신했다.

수정 전 실제 관련 테스트 기준선:

```text
.venv/Scripts/python.exe -m pytest tests/test_ontology_visualization.py tests/test_ontology_internalization.py tests/test_phase3_ui.py::test_ontology_hierarchy_inherited_fields_and_real_unit_conversion -q
8 failed, 9 passed in 4.46s
```

실패 목록:

- `test_ontology_visualization.py::test_diagram_uses_actual_rdf_and_preserves_graph_with_distinct_literal_nodes`
- `test_ontology_visualization.py::test_ontology_diagram_focus_shows_inheritance_external_alignment_and_properties`
- `test_ontology_visualization.py::test_attributes_show_raw_and_normalized_values_with_original_evidence`
- `test_ontology_visualization.py::test_untrusted_labels_cannot_break_mermaid_diagram`
- `test_ontology_visualization.py::test_ui_sample_graph_switching_evidence_validation_and_downloads_are_read_only`
- `test_ontology_visualization.py::test_ui_saved_product_graph_uses_actual_record_without_modifying_it`
- `test_ontology_internalization.py::test_operational_package_files_contain_no_external_business_uris`
- `test_phase3_ui.py::test_ontology_hierarchy_inherited_fields_and_real_unit_conversion`

7건은 삭제된 `RdfOntologyService._reference()` 호출로 인한 AttributeError, 1건은 시각화 운영 코드의 외부 업무 URI 감시 실패다. 참고 전체 기준선 `8 failed, 327 passed, 1 warning`과 실패 수는 같지만, 이번 수정 전 실행은 위 관련 테스트만 실행했으므로 전체 기준선으로 간주하지 않는다.

변경 내용:

- `services/ontology_visualization.py`: `_reference()` 호출을 `quantity_value`, `numeric_value`, `has_unit`, `has_quantity_kind`, `unit_uri()`로 교체했다. 제조사·모델 연결은 product_model.yaml의 relations·properties에 정의된 실제 내부 관계를 사용한다. 삭제된 외부 API를 복원하거나 예외를 숨기지 않는다.
- `term_label()`: 하위 namespace인 opqk·opunit·opsrc를 op보다 먼저 판별한다. rdf·rdfs·owl·xsd·sh·dcterms 표준 접두사도 유지한다. opsrc:qudt-3.5.2·opsrc:iof-202603·opsrc:goodrelations-1.0은 정상 내부 출처 식별자다.
- 노드 그룹은 표시 라벨이 아닌 IRI·RDF 타입으로 판별하고 rdfs:label을 우선한다. opqk는 별도 `quantity_kind` 그룹(분홍색), opunit은 `unit`(초록색), XSD는 `datatype`(회색), opsrc 내부 출처는 보라색 `local` 그룹이다. 실제 diagram에 등장하는 내부 근거 노드도 local 그룹을 사용한다. dcterms:source를 시각화 관계 목록에 추가하지 않았다.
- `views/ontology_graphs.py`: 자체 개념·내부 출처 보라색, 물리량 종류 분홍색, 단위 초록색, XSD 데이터 타입 회색으로 관계 탭 범례를 갱신했다. 제품 탭에서는 제품 파란색·제조사 노란색·물리량 값 청록색·값 주황색·단위 초록색·물리량 종류 분홍색·자체 개념 및 내부 출처 보라색으로 Mermaid classDef·class 할당·caption을 맞췄다. 외부 온톨로지 안내 문구도 현재 의미 모델에 맞췄다.
- 물리량 값·단위·변환 데이터는 변경하지 않았다. 0.6 kW → 600 W, 750 g → 0.75 kg, 파일·페이지·원문 근거를 그대로 검증했다. 저장 제품은 기존 등록 경로로 임시 DB에 등록하고 저장된 정규화 값을 표시한다. 근거 문자열에서 파싱 전 숫자를 임의 복원하지 않는다.
- `tests/test_ontology_visualization.py`: 외부 URI 기대값을 내부 관계·개념으로 갱신하고 기존 검증을 보강했다. 직접 term_label 호출, rdfs:label 우선순위, 양쪽 diagram의 단위·물리량 종류·XSD·내부 출처 그룹, 색상·class 할당·caption, 실제 제조사·물리량 및 물리 제품→모델 관계, 상속·제품군 범위, 문자열 이스케이프를 검증한다. diagram·attribute_rows·RDF/JSON 데이터 생성·SHACL 실행 전후 트리플 집합, AppTest 다운로드 생성·검사·전환 전후 products와 registration_cases 및 checkpoint DB의 모든 테이블 행 내용을 비교했다.
- `tests/test_ontology_internalization.py`의 검사 대상·정규식·assert와 읽기 전용 모델·서비스·의존성 파일을 변경하지 않았다. 기존 `ontology_explorer.py`와 `test_phase3_ui.py`도 수정 없이 통과했다. 패키지 설치·네트워크 다운로드·실제 LLM 호출은 하지 않았다. 최초 조정 검증에서는 runtime/data/ 기존 DB에 쓰지 않았으며 pytest 밖에서 앱·스크립트를 실행하지 않아 별도 scratch 폴더를 만들지 않았다. 이후 실제 실행 요청은 아래 후속 기록을 따른다.

실제 검증 결과:

- 운영 코드 수정 전 보강한 시각화 테스트: `20 failed, 4 passed in 4.33s`. 신규 18개 회귀 사례 중 14개 실패·4개 통과를 확인했고, 수정 후 신규 사례와 기존 시각화 6개 모두 통과했다.
- 최종 관련 테스트(위 동일 명령): `35 passed in 7.45s`.
- 최종 전체: `.venv/Scripts/python.exe -m pytest -q -W error::pytest.PytestCacheWarning` → `353 passed, 1 warning in 41.44s`. `-p no:cacheprovider`는 사용하지 않았다. 경고는 범위 밖 `test_rdf_product_ontology.py`의 RDFLib JSON-LD ConjunctiveGraph DeprecationWarning 1개다.
- 수정한 운영 코드 2개에만 `.venv/Scripts/ruff.exe format src/ontoproduct/services/ontology_visualization.py src/ontoproduct/views/ontology_graphs.py` 적용: `1 file reformatted, 1 file left unchanged`.
- 같은 파일의 `.venv/Scripts/ruff.exe format --check src/ontoproduct/services/ontology_visualization.py src/ontoproduct/views/ontology_graphs.py` → `2 files already formatted`. 테스트 파일에는 Ruff format을 적용하지 않았다.
- `git diff --check`: 통과(출력 없음).

AppTest에서 /ontology 탐색 화면과 선택 제품군/전체 구조, 모터·베어링 샘플·저장 제품·근거 표시 전환 시 예외 없이 Mermaid 문자열이 생성됐다. 다운로드 데이터와 SHACL 결과도 검증했다. **최초 보고 당시 미확인:** 실제 Mermaid 브라우저 렌더링과 브라우저 다운로드는 확인하지 않았다. 이후 실제 실행 결과는 아래 후속 기록을 따른다. 위 AppTest·문자열·데이터 검증과 과거 Chrome 검증 기록을 구분한다. 읽기 전용 파일에서 별도 수정이 필요한 문제는 발견하지 않았다. 최종 상태에서 시작 시점에 없던 미추적 `skills-lock.json`을 확인했으며, 이번 작업의 수정 대상이 아니므로 변경하거나 삭제하지 않았다.

### 후속 실제 실행 확인 (2026-10-07)

사용자의 “실행해봐줘” 요청으로 로컬 Streamlit 앱을 실제 Chrome에서 실행했다. 앱 모듈 import 전에 ONTOPRODUCT_DATA_DIR을 저장소 내부의 고유 폴더 `.pytest_tmp/ontology-browser-check-34db67d2-5b7d-48c1-9d91-3129a4bc6721`로 지정했다. 기존 runtime/data/ DB는 사용하지 않았다. 확인 주소는 `http://127.0.0.1:18501/ontology`였으며 확인 후 임시 서버를 종료했다. scratch의 절대 경로와 .pytest_tmp 바로 아래 이번 작업 폴더인지 검사한 후 해당 scratch만 삭제했다.

- 실제 /ontology 화면과 전체 관계 그래프가 예외 없이 렌더링됐다. watt 단위의 초록색, Power 물리량 종류의 분홍색 등 분류와 라벨을 확인했다.
- 모터 DM-600·베어링 BR-6201 그래프 전환과 두 샘플의 SHACL 통과 메시지를 확인했다. 모터 속성 표의 0.6 kW → 600.0 W, 750 g → 0.75 kg 및 파일·페이지 근거를 확인했다.
- 근거 표시를 켜 실제 베어링 그래프를 렌더링하면서 괄호·구분자가 entity 코드로 보이는 기존 표시 문제를 발견했다. 설치된 Mermaid 번들에서 entity 문법을 확인하고 _safe_label을 조정했다. Mermaid 인용 라벨 안에서 허용되는 대괄호·구분자를 과도하게 이스케이프하지 않고, 따옴표·HTML 문자 및 입력에 포함된 entity 표기는 안전하게 인코딩한다. 근거 노드의 `[Sheet: Spec, Row: 3] A3=Inner Diameter | B3=12 mm`가 실제 정상 문자로 표시됨을 재확인했다.
- 새 회귀 테스트 `test_mermaid_label_entities_preserve_text_without_reinterpreting_source`의 수정 전 결과는 `1 failed in 1.17s`였고 수정 후 통과했다. 기존 문자열 주입 검증도 유지했다.
- 실제 RDF와 제품 그래프 JSON 다운로드 이벤트가 Chrome에서 정상 발생했다. **미확인:** Chrome 다운로드 목록은 브라우저 보안 정책으로 접근이 차단되어 디스크에 저장된 파일을 다시 열어 확인하지 않았다. 다운로드 데이터의 내용·읽기 전용 동작은 자동 테스트에서 검증했다. 저장 제품의 실제 Chrome 화면 전환은 이번 확인에서 재검증하지 않았으며 AppTest 결과를 따른다.
- 최종 관련 테스트: `36 passed in 7.38s`.
- 최종 전체 명령 `.venv/Scripts/python.exe -m pytest -q -W error::pytest.PytestCacheWarning`: `354 passed, 1 warning in 40.67s`. 경고는 앞서 기록한 기존 RDFLib ConjunctiveGraph 경고 1개다.
- `.venv/Scripts/ruff.exe format --check src/ontoproduct/services/ontology_visualization.py src/ontoproduct/views/ontology_graphs.py`: `2 files already formatted`.
- `git diff --check`: 통과(출력 없음).

## 확정 인터페이스

```python
ExtractionAgent(llm_service, *, ontology=None, aliases=None,
                max_chars=12000, overlap_chars=128)
OntologyAgent(ontology, llm_service=None, *, aliases=None)
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
- Ontology payload: `instructions`, `prompt_version`, `extracted_product`, `allowed_classes`, `class_definitions`, `semantic_model`. 내재화로 `external_references`를 제거했다.
- semantic_model은 기본 모델에서 3.0.0 의미 context다. 개체·관계·측정 구조·물리량 종류·단위·출처(제목·버전·라이선스)를 담으며 URI·URL이 없다. 임의의 별도 ontology에 연결된 의미 모델이 없으면 null이다. adapter는 이 context를 신뢰된 업무 정의로 전달한다. 근거 문자열은 계속 비신뢰 입력이다.
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

출처·검증 범위는 [외부 참고 기록](02_03_EXTERNAL_SOURCES.md), 외부 → 내부 대응은 [대응표](03_EXTERNAL_CONCORDANCE.md), 라이선스는 [제3자 고지](../THIRD_PARTY_NOTICES.md)에 있다. 운영 정의는 외부 URI 없이 자체 개념으로 구성했다. 외부 분류·등록 규칙 또는 equivalence 공리를 복사하지 않았다.

- 06 담당자: confidence 의미·현재 0.70 기준·필수 충돌 재추출 비용·최종 클래스 변경의 충돌 정책을 확인한다.
- 08 담당자: 실제 Protocol adapter, Parser 결과, 실제 Registry/runtime 실행 모드를 연결한다. 오류 종류별 recoverable 정책과 수동 해결 UX 개선을 별도 검토한다.
- SDK timeout/통신 retry는 adapter에서 설정하고 Graph의 업무 retry와 구분한다.
- 실제 모델·프롬프트 품질과 문서 평가: 미실행. 실제 PDF/XLSX 바이너리 파싱: 미실행.
- 운영 목업 교체: 미완료. 기본 mock_registry와 UI runtime을 변경하지 않았다.
- 브랜치: `temp/test_merge_branch`. 현재 Git 이력에는 내재화(`606a269`, `d086f96`, `c27f4f3`)와 시각화(`5998633`, `76a0220`)의 커밋 및 병합 기록이 있다. 이번 시각화 병합 후 조정은 commit·push·PR 생성 없이 작업 트리에 남겼다.
