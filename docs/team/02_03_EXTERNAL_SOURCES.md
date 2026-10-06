# 02·03 외부 온톨로지 참고 기록

확인일: 2026-10-07. 실행 참조는 [external_mappings.yaml](../../src/ontoproduct/ontology/external_mappings.yaml)에 있다. 프로그램 실행 중 웹을 요청하지 않으며 확인된 참조만 로드한다.

## 자료와 검증 범위

| 자료 | 확인한 버전 | 저자·출처와 라이선스 | 이번 사용 |
| --- | --- | --- | --- |
| IOF Core | 202603, Core.rdf의 owl:versionIRI | IOF Core Working Group / Industrial Ontologies Foundry / Open Applications Group, MIT | MaterialArtifact·Organization의 설계 참고 URI |
| GoodRelations | 1.0, Release 2011-10-01 | Martin Hepp, CC BY 3.0 | ProductOrServiceModel·BusinessEntity·hasManufacturer의 참고 URI |
| QUDT Units | 3.5.2, 각 단위 페이지의 rdfs:isDefinedBy | QUDT.org, CC BY 4.0 | V·W·kW·kg·g·mm·rpm의 단위 식별 URI |

IOF는 [공식 Core.rdf](https://raw.githubusercontent.com/iofoundry/ontology/master/core/Core.rdf)에서 namespace와 개념 정의·버전·모듈 maturity를 확인했다. Core 모듈은 Released다. 이것이 각 개념의 독립적인 성숙도나 내부 제품 모델과의 동치를 보장하지는 않는다. [IOF 라이선스](https://github.com/iofoundry/ontology/blob/master/LICENSE)

GoodRelations의 [공식 명세](https://www.heppnetz.de/ontologies/goodrelations/v1.html)에서 제품 모델·제조사·기업 관계와 라이선스를 확인했다. 내부 manufacturer는 문자열이므로 BusinessEntity를 가리키는 object property와 동일하다고 선언하지 않았다. [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)

QUDT의 공식 단위 페이지에서 실제 URI·기호·물리량·버전을 확인했다: [V](https://qudt.org/vocab/unit/V), [W](https://qudt.org/vocab/unit/W), [kW](https://qudt.org/vocab/unit/KiloW), [kg](https://qudt.org/vocab/unit/KiloGM), [g](https://qudt.org/vocab/unit/GM), [mm](https://qudt.org/vocab/unit/MilliM), [rpm](https://qudt.org/vocab/unit/REV-PER-MIN). 귀속 대상과 라이선스는 [공식 저장소 고지](https://github.com/qudt/qudt-public-repo/blob/main/LICENSE.md)에서 확인했다. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## 재사용·수정 내용

- 전체 RDF/OWL 정의, 공리, 원문 설명을 복사하거나 외부 모듈을 import하지 않았다. 참조 URI·버전·라이선스·출처를 기록하고 프로젝트용 설명과 매핑을 작성했다.
- equivalentClass/equivalentProperty나 외부 추론을 선언하지 않았다. BLDCMotor/Bearing 및 필수·선택 속성·범위는 내부 업무 정의다.
- 내부 단위 서비스는 기존 kW↔W, g↔kg 변환을 공통 데이터로 옮겼다. 숫자 비교와 물리량 검증을 추가했다.
- mm/rpm은 기존 내부 canonical unit으로 유지한다. QUDT의 SI 참조 단위 배율을 내부 mm/rpm에 그대로 복사하지 않았다.
- 향후 원문·공리를 복사하거나 수정·배포하면 해당 자료의 라이선스·저작권·변경 고지 조건을 다시 확인하고 적용해야 한다. 현재 URI 참조가 모든 라이선스 의무를 면제한다고 해석하지 않는다.

## 미확인 참조의 처리

이번 실행 파일의 12개 URI는 확인했다. 새로운 개념·외부 동치 관계는 자동으로 만들지 않았다. 추가 후보를 확인할 수 없으면 실행 파일에 넣지 않거나 status=unverified로 두고 문서에 이유를 남긴다. ExternalMappings.verified()는 unverified 항목을 제외한다. 버전이나 URI를 확인할 수 없다는 이유로 내부 단위·동의어·분류를 중단하지 않는다.
