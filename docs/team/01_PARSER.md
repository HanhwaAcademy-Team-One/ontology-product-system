# 01. Parser 담당자: 실제 파일을 문서 텍스트로 바꾸기

[공통 약속](00_COMMON.md) · [분업표](../MOCK_REPLACEMENT_PLAN.md)

## 1. 내가 맡는 일

파일을 열고 내용을 읽어 다음 Extraction 담당자에게 넘깁니다. 제품 사양을 판단하는 작업은 Extraction 담당자의 역할입니다.

PDF 파일을 업로드했다는 것과 PDF 내용을 읽었다는 것은 다릅니다. 현재 업로드 원본 저장은 구현되어 있지만 ParserMock은 원본을 열지 않습니다.

## 2. 먼저 볼 파일과 만들 파일

| 구분 | 위치 | 읽는 이유/할 일 |
| --- | --- | --- |
| 현재 Mock | [mocks/agents.py의 ParserMock](../../src/ontoproduct/mocks/agents.py) | 현재 source_documents에서 text 또는 MOCK document를 반환 |
| 기존 파일 저장 | [services/document_service.py](../../src/ontoproduct/services/document_service.py) | 원본 보관과 FileReference 생성이 이미 있음 |
| 기존 데이터 모양 | [schemas/product.py](../../src/ontoproduct/schemas/product.py) | FileReference, ParsedDocument 확인 |
| 신규 | src/ontoproduct/agents/parser_agent.py | ParserAgent 입구 |
| 신규 | src/ontoproduct/services/parser_service.py | 파일 형식별 실제 읽기 함수 |
| 신규 | tests/test_real_parser.py | 실제 문서 파싱 테스트 |
| 신규 자료 | tests/fixtures/documents/ | 작은 TXT/PDF/XLSX와 손상 파일 |

## 3. 어떤 입력을 받나요?

필수 입력: source_documents. 선택 입력: 없음.

```json
{
  "source_documents": [
    {
      "file_id": "22222222-2222-4222-8222-222222222222",
      "name": "motor_spec.txt",
      "path": "D:/ontology-product-system/runtime/uploads/11111111-1111-4111-8111-111111111111/22222222-2222-4222-8222-222222222222_motor_spec.txt",
      "mime_type": "text/plain",
      "size": 123
    }
  ]
}
```

- path: 실제로 열어야 할 원본 경로.
- name: 사용자가 업로드한 이름.
- mime_type: 파일 형식.
- file_id: 원본을 구별할 ID.
- size: 저장된 파일 크기.

이 JSON의 경로/크기/UUID는 설명용 예시입니다. 테스트에서는 DocumentService.save로 실제 파일을 저장하고 반환된 FileReference를 사용합니다.

## 4. 어떤 출력을 반환하나요?

```json
{
  "parsed_documents": [
    {
      "source_file": "motor_spec.txt",
      "text": "Product: DM-600\nClass: BLDCMotor\nManufacturer: XYZ Motors\nRated Voltage: 24 V\nRated Power: 0.6 kW\nRated Speed: 3200 rpm",
      "page": null
    }
  ]
}
```

여러 문서는 list에 여러 항목을 넣습니다. PDF는 페이지별 항목으로 나누면 Extraction이 어느 페이지에 근거가 있는지 알 수 있습니다.

신규 실제 Parser의 규칙은 TXT와 Excel의 `page: null`, PDF의 `page: 1, 2, ...`입니다. 위 출력도 이 규칙을 따릅니다. 기존 ParserMock은 TXT에도 `page: 1`을 반환하지만 Mock 구현을 변경하는 작업은 아닙니다. Schema상 둘 다 유효하므로 신규 실제 Parser 테스트에서는 여기서 정한 규칙을 명시적으로 검사합니다. Excel 시트명과 셀 위치는 현재 별도 schema 필드가 없으므로 text의 각 행 앞에 `[Sheet: Spec, Row: 3] A3=Manufacturer | B3=XYZ Motors`처럼 시트·행 번호와 셀 주소를 남깁니다. Extraction의 근거 검증도 이 `[Sheet: 이름, Row: n]` 형식을 기준으로 합니다. page에 시트 번호를 넣으면 PDF 페이지와 의미가 달라지므로 임의로 사용하지 않습니다.

원본 파일명이 같은 경우 source_file을 어떻게 유일하게 표시할지 통합/Extraction 담당자와 합의합니다. 원본 file_id를 포함한 표시 문자열을 사용할 수 있으며 schema 필드를 추가하려면 함께 변경합니다.

## 5. 구현 순서

1. parse(references) 함수부터 만듭니다.
2. 각 reference를 FileReference.model_validate로 검사합니다.
3. path가 존재하는지, 허용된 업로드 경로인지 확인합니다. 기존 DocumentService 검증을 재사용하거나 같은 정책을 적용합니다.
4. 확장자/파일 형식에 따라 TXT, PDF, XLSX 읽기 함수로 나눕니다.
5. 가장 쉬운 TXT부터 실제 내용을 읽습니다.
6. 텍스트 PDF의 페이지 내용을 읽습니다. 표의 값과 단위를 잃지 않도록 텍스트 구성 방식을 정합니다.
7. XLSX의 시트·행·셀을 읽습니다. `Manufacturer | XYZ Motors`처럼 값과 항목의 관계를 보존합니다.
8. ParsedDocument로 각 항목을 검사하고 dictionary list로 반환합니다.
9. 이미지 PDF를 지원할지 정합니다. OCR을 구현하지 않았다면 텍스트가 없다는 오류와 미지원 범위를 명확히 남깁니다.

parser_service.py의 함수명은 제안이며 팀이 합의해서 정하면 됩니다. Agent의 출력 키는 parsed_documents로 유지합니다.

## 6. Mock 대신 내 기능을 붙이는 방법

공통 문서의 ParserAgent 틀을 구현한 뒤 개발용 테스트에서 다음처럼 바꿉니다.

```python
from pathlib import Path
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.agents.parser_agent import ParserAgent
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.parser_service import ParserService

paths = ApplicationPaths(Path("<데이터 폴더>"))
registry = mock_registry()
registry.register(ParserAgent(ParserService(paths.uploads)), replace=True)
```

ParserService는 업로드 폴더(`ApplicationPaths.uploads`)를 생성자 인자로 받으며, 그 폴더 밖의 경로는 읽지 않습니다. 앱에서는 `AGENT_MODE=real`일 때 실제 Parser가 연결됩니다([통합 담당자 문서](08_INTEGRATION.md)).

다른 슬롯은 그대로이므로 Graph 전체를 실행해도 추출 결과는 아직 DM-500일 수 있습니다. **Parser 테스트는 parsed_documents에 실제 원문이 들어오는지 검사해야 합니다.** Extraction까지 고정 데이터를 쓰는 상태에서 최종 제품명을 Parser 성능의 기준으로 삼으면 안 됩니다.

UI 연결은 [통합 담당자 문서](08_INTEGRATION.md)를 따릅니다.

## 7. 무엇을 테스트하나요?

| 입력 | 확인할 결과 |
| --- | --- |
| 실제 TXT “Product: DM-600” | 출력 text에 DM-600이 있고 page=null |
| 두 페이지 PDF | 페이지별 text와 page=1/2가 맞음 |
| 표에 “Power / 0.6 / kW” | 항목·값·단위 관계가 text에 남음 |
| Excel 두 시트 | 두 시트의 값과 시트 위치가 보존되고 page=null |
| 한글·영문이 섞인 문서 | 글자가 깨지지 않음 |
| 여러 문서 | 모든 원본에 대한 출력이 있고 source_file이 구별됨 |
| 손상 PDF/XLSX | 예외가 나고 Wrapper가 오류 이벤트를 기록 |
| 없는 경로/허용 경로 밖 파일 | 읽기 거부 |
| 텍스트 없는 스캔 PDF | OCR 수행 또는 명시한 미지원 오류 |
| 모든 정상 출력 | ParsedDocument schema와 JSON 직렬화 통과 |

기존 테스트는 b"%PDF mock" 같은 가짜 bytes를 사용하는 경우가 있습니다. 실제 Parser 테스트에서는 정상 형식의 PDF/XLSX를 준비해야 합니다. Mock fixture는 기존 데모 테스트용으로 유지합니다.

신규 테스트 작성 후:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_real_parser.py tests\test_document_workspace.py -q
```

## 8. 완료 기준과 인계

TXT, 지원하는 PDF/XLSX에서 실제 내용을 읽고 위치를 보존해야 합니다. 읽기 실패가 기존 오류 경로에 들어가야 합니다.

Extraction 담당자에게 실제 파일 1개, parsed_documents JSON, Excel 위치 표기 규칙, OCR 지원 범위를 전달하세요.

### 인계 기록 (실제 Parser 기준)

- 지원 형식: TXT(UTF-8·UTF-8 BOM·CP949), 텍스트 PDF, XLSX. 그 밖의 확장자는 업로드 단계에서 거부합니다.
- page: TXT·XLSX는 `null`, PDF는 1부터 시작하는 실제 페이지 번호입니다. 텍스트가 없는 PDF 페이지는 건너뛰지만 번호는 원본을 따릅니다.
- PDF 표: 본문 텍스트 뒤에 `[Table n]`과 `항목 | 값 | 단위` 행을 덧붙입니다. 세로줄이 없는 표는 글자 간격으로 칸을 나눕니다.
- Excel: 시트마다 항목 하나이며, 각 행은 `[Sheet: 이름, Row: n] A1=값 | B1=값` 형식입니다. 수식 셀은 Excel이 저장한 계산값을 읽습니다.
- 같은 이름 파일: source_file을 `이름 (file_id 앞 8자리)`로 구분합니다.
- OCR 미지원: 텍스트가 없는 스캔 PDF는 "읽을 수 있는 텍스트가 없습니다 (스캔 PDF OCR 미지원)" 오류입니다.
- 읽기 실패는 파일명이 붙은 ValueError로 Wrapper의 parser 단계 오류 이벤트가 됩니다.
