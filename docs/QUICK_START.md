# Quick start

[문서 목차](README.md) · [사용자 매뉴얼](USER_MANUAL.md)

목표는 앱을 실행하고 제품 한 개를 승인하여 JSON과 DB 저장 결과를 확인하는 것입니다. 명령은 **Windows PowerShell, 저장소 루트** 기준입니다.

## 1. 설치

필수 환경은 Python **3.12**입니다(`>=3.12,<3.13`). 저장소나 source distribution을 사용하세요. wheel만 설치하면 루트의 `app.py`와 기본 평가 자료가 함께 제공되지 않습니다.

### uv 사용

`uv`가 설치된 환경에서 잠금 파일 기준으로 설치합니다.

```powershell
cd D:\ontology-product-system
uv --cache-dir .uv-cache sync --locked
```

### pip 사용

Python 3.12로 가상 환경을 만들고 같은 의존성과 프로젝트 패키지를 설치합니다. uv 방식과 pip 방식 중 하나를 선택합니다.

```powershell
cd D:\ontology-product-system
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

가상 환경을 활성화하지 않아도 아래 명령을 그대로 사용할 수 있습니다.

## 2. Mock 모드 실행

API Key가 필요 없습니다. 이전에 Real 모드를 사용한 터미널에서도 명시적으로 Mock을 선택합니다.

```powershell
$env:AGENT_MODE = "mock"
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

[http://127.0.0.1:8502 앱 열기](http://127.0.0.1:8502). 종료하려면 실행한 터미널에서 `Ctrl+C`를 누릅니다. 포트를 바꾸면 접속 주소도 같은 번호로 바꿉니다.

## 3. 첫 등록 데모

1. 제품 등록 화면에서 **Mock 예제로 시작**을 누릅니다.
2. DM-500의 필수 정격 속도가 없어 검토에서 멈추는 것을 확인합니다.
3. 제품 정보 수정에서 정격 속도에 값 `3000`, 단위 `rpm`을 입력합니다.
4. **수정 후 재검증**을 누른 뒤 검증 통과와 승인 가능 상태를 확인합니다.
5. **등록 승인**을 누르고 JSON을 다운로드합니다.
6. **제품 데이터베이스**에서 DM-500 등록 결과를 확인합니다.

Mock 모드에서 파일을 업로드해도 원본만 보관하고 추출은 DM-500 fixture를 사용합니다. 업로드 문서의 제품명이나 사양을 확인하려면 다음 Real 모드를 사용합니다.

## 4. Real 모드로 실제 문서 분석

Mock 서버를 `Ctrl+C`로 종료한 뒤, API Key가 환경 변수에 설정된 터미널에서 재시작합니다.

```powershell
$env:AGENT_MODE = "real"
$env:OPENAI_API_KEY = "<발급한 키>"
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

Real 모드는 Parser·Extraction·Ontology를 실제 구현으로 교체합니다. Validation·Reviewer는 기존 Mock의 규칙 판단을 사용하고, 중복 조회·등록은 실제 SQLite Agent를 사용합니다. Mock 예제 버튼은 숨겨집니다.

- 텍스트 PDF, XLSX, TXT(UTF-8·CP949)를 업로드할 수 있습니다. 파일당 최대 **20 MB**입니다.
- 여러 문서는 **제품 하나의 자료**로 함께 처리합니다.
- 스캔 PDF는 OCR을 지원하지 않아 파싱 오류가 됩니다.
- **문서 원문은 OpenAI API로 전송됩니다.** API Key는 저장소·설정 YAML·로그에 남기지 않습니다.
- 팀 기본 모델은 `gpt-5`입니다. 공급자·모델·timeout·retry 설정은 [통합 가이드](team/08_INTEGRATION.md)를 참고하세요.
- `.env` 파일을 자동으로 읽지 않습니다. 환경 변수나 YAML 설정을 바꾸면 서버를 재시작합니다.

등록 화면에서 현재 모드와 모델을 확인한 뒤 문서를 업로드하고 시작합니다. 추출된 값과 근거를 검토하고 필요한 값을 수정·재검증한 뒤 승인합니다. 상세 절차와 오류 대응은 [사용자 매뉴얼](USER_MANUAL.md)에 있습니다.

## 5. 실행 확인

| 확인 항목 | 성공 기준 |
| --- | --- |
| 앱 접속 | 제품 등록 화면과 메뉴가 표시됨 |
| Mock 수정 | `3000 rpm` 입력 후 검증 통과 |
| 승인 | 등록 완료와 JSON 다운로드 표시 |
| 저장 | 제품 데이터베이스에서 제품 조회 가능 |
| 작업 복원 | 최근 작업에서 선택 후 기존 결과 표시 |

기본 저장 위치는 `runtime/`입니다. 테스트용 데이터를 분리하려면 서버 실행 전에 아래처럼 지정합니다. 상세 경로는 [저장과 작업 복원](USER_MANUAL.md#저장과-작업-복원)을 참고하세요.

```powershell
$env:ONTOPRODUCT_DATA_DIR = "D:\ontology-product-system\runtime-demo"
```
