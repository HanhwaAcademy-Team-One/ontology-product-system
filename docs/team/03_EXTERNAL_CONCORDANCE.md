# 03 외부 개념 → 내부 개념 대응표

작성: 2026-10-07. 제품 온톨로지 내재화의 이관 기록이다.

이 문서는 **운영에서 읽지 않는 기록**이다. 운영 코드·설정·패키지 데이터·RDF 생성·Agent context는 이 문서를 읽지 않는다. 나중에 외부 표준과 다시 연결할 때 참고한다. 이 문서와 [외부 자료 기록](02_03_EXTERNAL_SOURCES.md), [제3자 고지](../THIRD_PARTY_NOTICES.md)만 외부 업무 URI를 담는다.

## 내부 URI 규칙

내부 namespace는 기존 `urn:ontoproduct:ontology:`(아래 `op:`)를 그대로 사용한다. 새 namespace는 만들지 않았다.

| 대상 | 내부 URI 형식 | 예 |
| --- | --- | --- |
| 클래스·관계·속성 | `op:<LocalName>` | `op:ProductModel`, `op:hasUnit` |
| 물리량 종류 | `op:quantitykind/<key>` | `urn:ontoproduct:ontology:quantitykind/power` |
| 단위 | `op:unit/<기호>` | `urn:ontoproduct:ontology:unit/kW` |
| 출처 | `op:source/<출처>-<버전>` | `urn:ontoproduct:ontology:source/qudt-3.5.2` |

Turtle 파일에서는 `opqk:`, `opunit:`, `opsrc:` 접두사로 내부 하위 namespace를 표시한다. 외부 접두사(`gr:`, `qudt:`, `unit:`, `qk:`, `iof:`)는 사용하지 않는다.

## 대응표

이전 실행 파일 `external_mappings.yaml`의 23개 참조 키 전체를 옮겼다. 내부 정의 문장은 프로젝트가 작성한 것이며 외부 원문을 복사하지 않았다. 외부 개념과의 `equivalentClass`·`equivalentProperty`·`sameAs`는 선언하지 않는다. 아래 "대응"은 설계 출처일 뿐 동치가 아니다.

### 개체 클래스와 관계

| 이전 키 | 외부 URI | 내부 URI | 타입 | 의미(내부 정의) | 이관 위치 | 출처 |
| --- | --- | --- | --- | --- | --- | --- |
| physical_artifact | `https://spec.industrialontologies.org/ontology/construct/MaterialArtifact` | `op:PhysicalArtifact` | owl:Class (상위) | 물질로 이루어진 인공 물체. `op:ManufacturedItem`의 상위 | product_model.yaml `entity_classes` | `op:source/iof-202603` |
| organization | `https://spec.industrialontologies.org/ontology/construct/Organization` | `op:Organization` | owl:Class (상위) | 조직으로 별도 확인된 개체. `op:ManufacturerOrganization`의 상위 | product_model.yaml `entity_classes` | `op:source/iof-202603` |
| manufacturer_entity | `http://purl.org/goodrelations/v1#BusinessEntity` | `op:BusinessEntity` | owl:Class (상위) | 제품·서비스 제공에 관여하는 사업 주체. `op:Manufacturer`의 상위 | product_model.yaml `entity_classes` | `op:source/goodrelations-1.0` |
| product_model | `http://purl.org/goodrelations/v1#ProductOrServiceModel` | `op:ProductModel` (흡수) | owl:Class | 카탈로그 사양으로서의 제품 모델. 개별 물리 제품이 아님 | product_model.yaml `entity_classes.ProductModel` | `op:source/goodrelations-1.0` |
| individual_product | `http://purl.org/goodrelations/v1#Individual` | `op:ManufacturedItem` (흡수) | owl:Class | 명시적으로 식별된 개별 물리 제품 | product_model.yaml `entity_classes.ManufacturedItem` | `op:source/goodrelations-1.0` |
| manufacturer | `http://purl.org/goodrelations/v1#hasManufacturer` | `op:hasManufacturer` | owl:ObjectProperty | 제품 모델 → 범위가 한정된 제조사 개체 | product_model.yaml `relations` | `op:source/goodrelations-1.0` |
| make_and_model | `http://purl.org/goodrelations/v1#hasMakeAndModel` | `op:hasMakeAndModel` | owl:ObjectProperty | 식별된 개별 제품 → 그 제품 모델 | product_model.yaml `relations` | `op:source/goodrelations-1.0` |

### 물리량 표현 구조

| 이전 키 | 외부 URI | 내부 URI | 타입 | 의미(내부 정의) | 이관 위치 | 출처 |
| --- | --- | --- | --- | --- | --- | --- |
| quantity_value | `http://qudt.org/schema/qudt/QuantityValue` | `op:QuantityValue` | owl:Class | 수치 하나와 단위·물리량 종류를 묶는 값 노드 | product_model.yaml `measurement` | `op:source/qudt-3.5.2` |
| numeric_value | `http://qudt.org/schema/qudt/numericValue` | `op:numericValue` | owl:DatatypeProperty | 값 노드의 수치 크기 | product_model.yaml `measurement` | `op:source/qudt-3.5.2` |
| quantity_unit | `http://qudt.org/schema/qudt/hasUnit` | `op:hasUnit` | owl:ObjectProperty | 값 노드 → 단위 | product_model.yaml `measurement` | `op:source/qudt-3.5.2` |
| quantity_kind | `http://qudt.org/schema/qudt/hasQuantityKind` | `op:hasQuantityKind` | owl:ObjectProperty | 값 노드 → 물리량 종류 | product_model.yaml `measurement` | `op:source/qudt-3.5.2` |
| (없음, 새로 정의) | — | `op:QuantityKind`, `op:Unit` | owl:Class | 물리량 종류·단위 개체의 클래스. 이전에는 외부 개체를 가리키기만 해서 로컬 클래스가 없었다 | product_model.yaml `measurement` | `op:source/qudt-3.5.2` |

### 물리량 종류

| 이전 키 | 외부 URI | 내부 URI | 내부 key | SI 차원 | 이관 위치 |
| --- | --- | --- | --- | --- | --- |
| voltage_quantity | `http://qudt.org/vocab/quantitykind/Voltage` | `op:quantitykind/electric_potential` | electric_potential | M·L²·T⁻³·I⁻¹ | unit_mappings.yaml `quantity_definitions` |
| power_quantity | `http://qudt.org/vocab/quantitykind/Power` | `op:quantitykind/power` | power | M·L²·T⁻³ | unit_mappings.yaml |
| speed_quantity | `http://qudt.org/vocab/quantitykind/RotationalFrequency` | `op:quantitykind/rotational_frequency` | rotational_frequency | T⁻¹ | unit_mappings.yaml |
| mass_quantity | `http://qudt.org/vocab/quantitykind/Mass` | `op:quantitykind/mass` | mass | M | unit_mappings.yaml |
| length_quantity | `http://qudt.org/vocab/quantitykind/Length` | `op:quantitykind/length` | length | L | unit_mappings.yaml |

출처는 모두 `op:source/qudt-3.5.2`다. 차원 표기는 프로젝트가 작성한 SI 기본 차원 이름이다.

### 단위

| 이전 키 | 외부 URI | 내부 URI | 물리량 | 표준 단위로의 배율 | 이관 위치 |
| --- | --- | --- | --- | --- | --- |
| V | `http://qudt.org/vocab/unit/V` | `op:unit/V` | electric_potential | 1 (표준) | unit_mappings.yaml `units` |
| W | `http://qudt.org/vocab/unit/W` | `op:unit/W` | power | 1 (표준) | unit_mappings.yaml |
| kW | `http://qudt.org/vocab/unit/KiloW` | `op:unit/kW` | power | 1000 → W | unit_mappings.yaml |
| kg | `http://qudt.org/vocab/unit/KiloGM` | `op:unit/kg` | mass | 1 (표준) | unit_mappings.yaml |
| g | `http://qudt.org/vocab/unit/GM` | `op:unit/g` | mass | 0.001 → kg | unit_mappings.yaml |
| mm | `http://qudt.org/vocab/unit/MilliM` | `op:unit/mm` | length | 1 (표준) | unit_mappings.yaml |
| rpm | `http://qudt.org/vocab/unit/REV-PER-MIN` | `op:unit/rpm` | rotational_frequency | 1 (표준). rad/s로 바꾸지 않음 | unit_mappings.yaml |

출처는 모두 `op:source/qudt-3.5.2`다. 배율은 기존 내부 변환 계수이며 QUDT의 SI 배율을 복사한 것이 아니다.

## 단순 URI 치환으로 부족했던 부분

1. **다중 상속.** 이전 `ManufacturedItem`은 외부 상위 개념 2개(MaterialArtifact, Individual)를, `ManufacturerOrganization`은 내부 상위 1개와 외부 상위 1개를 가졌다. 개체 클래스의 단일 `parent`를 `parents` 목록으로 바꾸고 순환 검사를 그래프(DAG) 검사로 바꿨다.
2. **흡수한 개념.** 내부 하위 클래스가 하나뿐이고 의미가 같은 범위인 상위 개념(ProductOrServiceModel → ProductModel, Individual → ManufacturedItem)은 별도 상위 클래스를 만들지 않고 내부 클래스 정의와 출처 기록에 흡수했다. 둘 이상의 의미를 구분해야 하는 개념(PhysicalArtifact, Organization, BusinessEntity)만 상위 클래스로 만들었다.
3. **중복 관계 triple.** 제품 RDF는 `op:hasManufacturer`와 `gr:hasManufacturer`, `op:hasMakeAndModel`과 `gr:hasMakeAndModel`을 둘 다 기록했다. 외부 쪽을 제거했다. 내부 관계가 도메인·범위·설명을 모두 가진다.
4. **외부에만 있던 정의.** 단위와 물리량 종류는 외부 개체를 가리키기만 했고 로컬 RDF에 이름·기호·차원·배율이 없었다. `op:QuantityKind`·`op:Unit` 개체로 이 정보를 로컬 RDF에 직접 기록한다. 단위 변환은 계속 공유 단위 서비스가 수행하며, RDF의 배율은 설명용이다.
5. **수치 속성.** SHACL과 베어링 SPARQL 제약이 외부 `numericValue`를 직접 가리켰다. `op:numericValue`를 DatatypeProperty로 정의하고 제약을 옮겼다.
6. **출처 기록.** 온톨로지 RDF가 출처 URL과 라이선스 URL을 `dcterms:source`/`dcterms:license`로 기록했다. 운영 RDF는 `op:source/<출처>-<버전>` 개체와 SPDX 라이선스 이름 문자열만 기록한다. URL은 문서에서만 관리한다.
7. **Agent context.** LLM payload의 `external_references`와 의미 context의 `external_uri`·물리량 `uri`를 제거하고 내부 이름·정의·차원으로 바꿨다.

## external_mappings.yaml 처리

**제거했다.** 내용은 이 문서로 옮겼다. `external_mapping_service.py`와 OntologyAgent의 `external_mappings` 생성자 인자도 제거했다. 운영 패키지에 외부 업무 URI를 담은 파일을 남기지 않기 위해서다. 출처 메타데이터(제목·버전·라이선스·귀속)는 URL 없이 product_model.yaml의 `sources`에 남겼다.

## 외부 표준과 다시 연결하려면

1. 이 표의 외부 URI를 기준으로 연결할 개념을 고른다.
2. 운영 RDF에 직접 넣지 말고 별도 정렬(alignment) 그래프로 만든다. 예: `op:ProductModel rdfs:subClassOf gr:ProductOrServiceModel`.
3. 그 시점의 공식 자료에서 URI·버전·라이선스를 다시 확인한다.
4. 동치 공리는 의미가 같다는 근거가 있을 때만 선언한다.
