# Quick start

[문서 목차](README.md) · [사용자 매뉴얼](USER_MANUAL.md)

목표는 앱을 실행하고 제품 한 개를 승인하여 JSON과 DB 저장 결과를 확인하는 것입니다. 명령은 **Windows PowerShell, 저장소 루트** 기준입니다. 명령 프롬프트(cmd)나 Linux·macOS를 쓴다면 먼저 [터미널별 명령](#터미널별-명령)을 확인하세요.

## 터미널별 명령

이 문서의 명령 블록은 모두 **PowerShell 문법**입니다. 환경 변수를 정하는 문법이 터미널마다 달라서, 다른 터미널에 그대로 붙여 넣으면 설정이 적용되지 않습니다.

프롬프트 모양으로 지금 터미널을 구분합니다.

| 터미널 | 프롬프트 예 |
| --- | --- |
| PowerShell | `PS D:\ontology-product-system>` |
| 명령 프롬프트(cmd) | `D:\ontology-product-system>` (앞에 `PS`가 없음) |
| Linux·macOS (bash, zsh) | `user@host:~/ontology-product-system$` |

cmd에 `$env:AGENT_MODE = "real"`을 입력하면 `파일 이름, 디렉터리 이름 또는 볼륨 레이블 구문이 잘못되었습니다.`가 나오고 값이 설정되지 않습니다. 이 상태로 서버를 켜면 **Mock 모드**로 실행됩니다. VS Code에서는 터미널 패널의 `+` 옆 드롭다운에서 PowerShell을 고를 수 있습니다.

| 작업 | PowerShell | cmd | Linux·macOS |
| --- | --- | --- | --- |
| 환경 변수 설정 (현재 창만) | `$env:AGENT_MODE = "real"` | `set AGENT_MODE=real` | `export AGENT_MODE=real` |
| 환경 변수 해제 | `Remove-Item Env:\AGENT_MODE` | `set AGENT_MODE=` | `unset AGENT_MODE` |
| 값 확인 | `$env:AGENT_MODE` | `echo %AGENT_MODE%` | `echo $AGENT_MODE` |
| 가상 환경 Python | `.venv\Scripts\python.exe` | `.venv\Scripts\python.exe` | `.venv/bin/python` |
| 가상 환경 생성 (pip 방식) | `py -3.12 -m venv .venv` | `py -3.12 -m venv .venv` | `python3.12 -m venv .venv` |

- cmd의 `set`은 `=` 앞뒤에 공백을 넣지 않습니다. 공백도 이름과 값에 들어갑니다.
- 위 방법으로 정한 값은 그 터미널 창에서만 유지됩니다. 새 창을 열면 다시 정합니다.
- Linux·macOS에서는 경로 구분자 `\`를 `/`로 바꿉니다. 이 프로젝트를 Linux·macOS에서 실행해 검증한 기록은 아직 없습니다.

예를 들어 Real 모드 실행은 터미널별로 다음과 같습니다.

```bat
:: 명령 프롬프트(cmd)
set AGENT_MODE=real
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

```bash
# Linux·macOS
export AGENT_MODE=real
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

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
$env:OPENAI_API_KEY = "<발급한 키>"   # Windows 사용자 환경 변수로 등록했다면 이 줄은 생략
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

API Key를 매번 입력하지 않으려면 Windows 사용자 환경 변수로 한 번 등록합니다. 앱은 실행한 터미널이 물려받은 `OPENAI_API_KEY`를 그대로 읽습니다.

1. Windows 검색에서 **계정의 환경 변수 편집**을 엽니다.
2. 사용자 변수에 이름 `OPENAI_API_KEY`, 값 `<발급한 키>`로 새로 만듭니다.
3. VS Code와 열려 있던 터미널을 **모두 닫고 다시 엽니다.** 이미 실행 중인 프로그램에는 새 값이 전달되지 않습니다.

명령으로 등록하면 키가 터미널 입력 기록에 남을 수 있으므로 위 화면에서 등록하는 방법을 권합니다. Linux·macOS에서는 `~/.bashrc`나 `~/.zshrc`에 `export OPENAI_API_KEY=...`를 넣습니다.

Real 모드는 Parser·Extraction·Ontology를 실제 구현으로 교체합니다. Validation은 실제 Python 규칙 Agent, Reviewer는 기존 Mock의 규칙 판단을 사용하고, 중복 조회·등록은 실제 SQLite Agent를 사용합니다. Mock 예제 버튼은 숨겨집니다.

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

기본 저장 위치는 `runtime/`입니다. 테스트용 데이터를 분리하려면 서버 실행 전에 아래처럼 지정합니다. 폴더는 git에 잡히지 않도록 `runtime\` 안에 만듭니다. 상세 경로는 [저장과 작업 복원](USER_MANUAL.md#저장과-작업-복원)을 참고하세요.

```powershell
$env:ONTOPRODUCT_DATA_DIR = "D:\ontology-product-system\runtime\demo"
```

빈 DB로 다시 테스트하는 방법, 기본 DB 초기화, inputdata 샘플로 확인하는 순서는 [새 DB로 테스트와 초기화](USER_MANUAL.md#새-db로-테스트와-초기화)에 있습니다.
