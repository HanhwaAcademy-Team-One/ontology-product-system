# 제3자 자료 고지

OntoProduct의 제품 온톨로지(`src/ontoproduct/ontology/`)는 아래 자료를 **설계 참고**로 사용했다. 2026-10-07 내재화 이후 운영 온톨로지·제품 RDF·SHACL은 이 자료들의 URI를 참조하거나 import하지 않는다. 모든 개념은 `urn:ontoproduct:ontology:` 아래 프로젝트가 직접 정의했다.

## 재사용 범위

- 외부 원문 설명, RDF/OWL 공리, 모듈을 복사하지 않았다.
- 개념의 구분 방식(제품 모델과 개별 제품, 사업 주체와 조직, 값·단위·물리량 종류를 묶는 값 노드)을 참고해 내부 클래스·관계·물리량·단위를 정의했다. 정의 문장은 프로젝트가 새로 작성했다.
- 단위 배율과 SI 차원 표기는 프로젝트가 작성한 자료다. QUDT의 SI 배율을 복사하지 않았다.
- 외부 개념과의 동치(`owl:equivalentClass`, `owl:equivalentProperty`, `owl:sameAs`)를 선언하지 않았다.

운영 RDF는 각 개념에 `dcterms:source`로 아래 로컬 출처 식별자를 기록한다. 대응 관계 전체는 [외부 개념 대응표](team/03_EXTERNAL_CONCORDANCE.md)에 있다.

## 자료별 고지

### IOF Core

- 로컬 출처 식별자: `op:source/iof-202603`
- 저작자: IOF Core Working Group / Industrial Ontologies Foundry / Open Applications Group
- 버전: 202603 (Core.rdf의 owl:versionIRI)
- 원출처: https://github.com/iofoundry/ontology
- 라이선스: MIT — https://github.com/iofoundry/ontology/blob/master/LICENSE
- 참고한 개념: MaterialArtifact, Organization
- 내부 대응: `op:PhysicalArtifact`, `op:Organization`

### GoodRelations

- 로컬 출처 식별자: `op:source/goodrelations-1.0`
- 저작자: Martin Hepp
- 버전: 1.0, release 2011-10-01
- 원출처: https://www.heppnetz.de/ontologies/goodrelations/v1.html
- 라이선스: Creative Commons Attribution 3.0 (CC BY 3.0) — https://creativecommons.org/licenses/by/3.0/
- 참고한 개념: ProductOrServiceModel, Individual, BusinessEntity, hasManufacturer, hasMakeAndModel
- 내부 대응: `op:ProductModel`, `op:ManufacturedItem`, `op:BusinessEntity`, `op:hasManufacturer`, `op:hasMakeAndModel`
- 변경 내용: 개념을 그대로 쓰지 않고 내부 정의로 다시 작성했다. 제조사는 이름 문자열이 아닌 레코드 범위의 개체로 표현하며 전역 동일성을 주장하지 않는다.

### QUDT

- 로컬 출처 식별자: `op:source/qudt-3.5.2`
- 저작자: QUDT.org
- 버전: 3.5.2
- 원출처: https://www.qudt.org/ , https://github.com/qudt/qudt-public-repo
- 라이선스: Creative Commons Attribution 4.0 (CC BY 4.0) — https://github.com/qudt/qudt-public-repo/blob/main/LICENSE.md
- 참고한 개념: QuantityValue, numericValue, hasUnit, hasQuantityKind, 물리량 종류 5개(Voltage, Power, RotationalFrequency, Mass, Length), 단위 7개(V, W, kW, kg, g, mm, rpm)
- 내부 대응: `op:QuantityValue`, `op:numericValue`, `op:hasUnit`, `op:hasQuantityKind`, `op:QuantityKind`, `op:Unit`, `op:quantitykind/*`, `op:unit/*`
- 변경 내용: rpm을 rad/s로 바꾸지 않고 회전 빈도의 표준 단위로 유지했다. mm를 길이의 표준 단위로 사용한다. 배율은 내부 표준 단위 기준이다.

## 앞으로 외부 자료를 가져올 때

원문·공리를 복사하거나 수정해서 배포하면, 그 시점의 라이선스·저작권 고지·변경 표시 조건을 다시 확인하고 이 파일에 기록한다. URI만 참조한다고 모든 라이선스 의무가 사라진다고 해석하지 않는다.
