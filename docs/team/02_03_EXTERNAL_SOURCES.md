# 02·03 외부 온톨로지 참고 기록

확인일: 2026-10-07. 실행 참조는 [external_mappings.yaml](../../src/ontoproduct/ontology/external_mappings.yaml)에 있다. 사용자 추가 요청으로 URI 참고 목록에서 [제품 의미 모델](03_PRODUCT_ONTOLOGY.md)·자체 RDF/OWL·SHACL 구축까지 확장했다. 프로그램 실행 중 웹을 요청하지 않으며 확인된 참조만 로드한다.

## 자료와 검증 범위

| 자료 | 확인한 버전 | 저자·출처와 라이선스 | 이번 사용 |
| --- | --- | --- | --- |
| IOF Core | 202603, Core.rdf의 owl:versionIRI | IOF Core Working Group / Industrial Ontologies Foundry / Open Applications Group, MIT | 물리 제조물·명시적으로 확인한 제조 조직의 자체 하위 클래스 |
| GoodRelations | 1.0, Release 2011-10-01 | Martin Hepp, CC BY 3.0 | 제품 모델/제조사/물리 제품 개념과 제조사·모델 관계 |
| QUDT | 3.5.2, 공식 schema·quantitykind·unit 페이지의 rdfs:isDefinedBy | QUDT.org, CC BY 4.0 | QuantityValue·수치/단위/물리량 관계·5개 물리량 종류·7개 단위 |

IOF는 [공식 Core.rdf](https://raw.githubusercontent.com/iofoundry/ontology/master/core/Core.rdf)에서 namespace와 개념 정의·버전·모듈 maturity를 확인했다. Core 모듈은 Released다. 이것이 각 개념의 독립적인 성숙도나 내부 제품 모델과의 동치를 보장하지는 않는다. [IOF 라이선스](https://github.com/iofoundry/ontology/blob/master/LICENSE)

GoodRelations의 [공식 명세](https://www.heppnetz.de/ontologies/goodrelations/v1.html)에서 제품 모델·제조사·기업 관계와 Individual·hasMakeAndModel을 확인했다. 내부 manufacturer는 문자열이므로 BusinessEntity를 가리키는 object property와 동일하다고 선언하지 않았다. RDF 변환에서는 별도 제조사 개체와 hasManufacturer 관계를 생성한다. 이름에 기반한 전역 동일성·법적 정식 명칭을 주장하지 않는다. [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)

QUDT의 공식 단위 페이지에서 실제 URI·기호·물리량·버전을 확인했다: [V](https://qudt.org/vocab/unit/V), [W](https://qudt.org/vocab/unit/W), [kW](https://qudt.org/vocab/unit/KiloW), [kg](https://qudt.org/vocab/unit/KiloGM), [g](https://qudt.org/vocab/unit/GM), [mm](https://qudt.org/vocab/unit/MilliM), [rpm](https://qudt.org/vocab/unit/REV-PER-MIN). 귀속 대상과 라이선스는 [공식 저장소 고지](https://github.com/qudt/qudt-public-repo/blob/main/LICENSE.md)에서 확인했다. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

추가로 [QuantityValue](https://qudt.org/schema/qudt/QuantityValue), [numericValue](https://qudt.org/schema/qudt/numericValue), [hasUnit](https://qudt.org/schema/qudt/hasUnit), [hasQuantityKind](https://qudt.org/schema/qudt/hasQuantityKind), [공식 개요](https://www.qudt.org/pages/QUDToverviewPage.html)에서 수치·단위·물리량 구조를 확인했다. 예전 자료의 qudt:unit을 현재 schema URI로 가정하지 않고, 현재 문서에서 확인한 qudt:hasUnit을 사용한다.

물리량은 [Voltage](https://qudt.org/vocab/quantitykind/Voltage), [Power](https://qudt.org/vocab/quantitykind/Power), [RotationalFrequency](https://qudt.org/vocab/quantitykind/RotationalFrequency), [Mass](https://qudt.org/vocab/quantitykind/Mass), [Length](https://qudt.org/vocab/quantitykind/Length)를 확인했다. rpm은 공식 적용 단위에 REV-PER-MIN이 있는 RotationalFrequency로 연결했다. QUDT 차원 벡터 문자열의 I/E 기호를 SI 기본 차원 이름과 혼동하지 않고, 프로젝트의 mass/length/time/current 등 이름으로 차원을 명시했다. 이 차원 표기와 내부 변환 계수는 프로젝트가 작성한 자료다.

SHACL 표현·제약은 [W3C 표준](https://www.w3.org/TR/shacl/), 실행은 [pySHACL 공식 문서](https://github.com/RDFLib/pySHACL)를 참고했다. 전압/치수 등의 필수 여부와 범위·내경<외경 제약은 프로젝트의 등록 정책이며 외부 기관이 정의한 업무 규칙이라고 주장하지 않는다.

## 재사용·수정 내용

- 전체 RDF/OWL 정의, 외부 공리, 원문 설명을 복사하거나 외부 모듈을 import하지 않았다. 확인한 외부 개념을 상위 개념/상위 관계로 사용하고 자체 클래스·설명·타입 제한·SHACL을 작성했다.
- equivalentClass/equivalentProperty와 외부 전체 공리 추론은 적용하지 않았다. 자체 rdfs:subClassOf/subPropertyOf·domain/range·OWL 값 타입 제한·disjointness를 구성하고 로컬 RDFS 추론을 사용하는 SHACL을 실행한다.
- 내부 단위 서비스는 기존 kW↔W, g↔kg 변환을 공통 데이터로 옮겼다. 숫자 비교와 물리량 검증을 추가했다.
- mm/rpm은 기존 내부 canonical unit으로 유지한다. QUDT의 SI 참조 단위 배율을 내부 mm/rpm에 그대로 복사하지 않았다.
- 향후 원문·공리를 복사하거나 수정·배포하면 해당 자료의 라이선스·저작권·변경 고지 조건을 다시 확인하고 적용해야 한다. 현재 URI 참조가 모든 라이선스 의무를 면제한다고 해석하지 않는다.

## 미확인 참조의 처리

이번 실행 파일의 23개 URI는 확인했다. 외부 동치 관계는 자동으로 만들지 않았다. 추가 후보를 확인할 수 없으면 실행 파일에 넣지 않거나 status=unverified로 두고 문서에 이유를 남긴다. ExternalMappings.verified()는 unverified 항목을 제외한다. 새 자체 의미 모델이 요구하는 상위 개념·물리량·단위 참조가 미확인 상태라면 로드 오류로 처리한다. 임의의 사용자 정의 ontology에는 이 외부 연결을 강제하지 않는다.
