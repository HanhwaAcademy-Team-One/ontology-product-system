# Quick start

[문서 목차](README.md) · [사용자 매뉴얼](USER_MANUAL.md)

앱을 설치·실행하고 제품 한 개를 등록하는 데까지 안내합니다. 명령은 **Windows PowerShell, 저장소 루트(`D:\ontology-product-system`)** 기준입니다. cmd나 Linux·macOS를 쓰면 [터미널별 명령](#터미널별-명령)을 함께 보세요.

| 순서 | 할 일 | 한 번만? |
| --- | --- | --- |
| 1 | [설치](#1-설치) | 예 |
| 2 | [API Key 등록](#2-api-key-등록) | 예 |
| 3 | [앱 실행](#3-앱-실행) | 매번 |
| 4 | [첫 등록](#4-첫-등록) | 확인용 |

## 1. 설치

Python **3.12**가 필요합니다(`>=3.12,<3.13`). wheel만 설치하면 `app.py`와 평가 자료가 빠지므로 저장소나 source distribution을 사용하세요. 아래 두 방법 중 하나를 고릅니다.

### uv 사용 (권장)

```powershell
cd D:\ontology-product-system
uv --cache-dir .uv-cache sync --locked
```

### pip 사용

```powershell
cd D:\ontology-product-system
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

어느 방법이든 `.venv` 가상 환경이 만들어집니다. 활성화하지 않아도 아래 명령을 그대로 쓸 수 있습니다.

## 2. API Key 등록

> **API Key는 Windows 사용자 환경 변수 `OPENAI_API_KEY`에 등록합니다.**
> [llm.yaml](../src/ontoproduct/config/llm.yaml)이나 다른 저장소 파일에는 적지 않습니다. git에 올라가면 키가 노출됩니다. `.env` 파일도 읽지 않습니다.

1. Windows 검색에서 **계정의 환경 변수 편집**을 엽니다.
2. **사용자 변수**에서 **새로 만들기**를 누르고 이름 `OPENAI_API_KEY`, 값 `<발급한 키>`를 입력합니다.
3. VS Code와 열려 있던 터미널을 **모두 닫고 다시 엽니다.** 이미 실행 중인 프로그램은 새 값을 받지 못합니다.
4. 새 PowerShell에서 확인합니다. `True`가 나오면 됩니다.

   ```powershell
   [bool]$env:OPENAI_API_KEY
   ```

지금 창에서만 잠깐 쓰려면 `$env:OPENAI_API_KEY = "<발급한 키>"`를 입력합니다. 다만 키가 터미널 입력 기록에 남을 수 있습니다. Linux·macOS는 `~/.bashrc`나 `~/.zshrc`에 `export OPENAI_API_KEY=...`를 넣습니다.

모델·timeout·retry 같은 **키 이외의 설정**은 [llm.yaml](../src/ontoproduct/config/llm.yaml)에 있습니다. 기본 모델은 `openai/gpt-5`입니다. 바꾸는 방법은 [통합 가이드](team/08_INTEGRATION.md#실행-설정)에 있습니다.

## 3. 앱 실행

```powershell
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

[http://127.0.0.1:8502](http://127.0.0.1:8502)를 엽니다. 종료는 실행한 터미널에서 `Ctrl+C`입니다. 포트를 바꾸면 접속 주소의 번호도 같이 바꿉니다.

API Key가 없거나 설정이 잘못되면 **모든 화면**에 "실행 설정 오류"가 표시되고 멈춥니다. 2단계를 다시 확인한 뒤 서버를 재시작하세요. 환경 변수나 YAML을 바꿨을 때도 재시작해야 적용됩니다.

## 4. 첫 등록

1. 제품 등록 화면 상단에 표시된 모델(`openai/gpt-5`)을 확인합니다.
2. `inputdata\01_normal_motors\M001_bldcmotor.txt`를 업로드하고 **업로드 문서로 시작**을 누릅니다. 분석에 30초~1분 정도 걸립니다.
3. 추출된 제조사·정격 전압·정격 출력·정격 속도와 원문 근거를 확인합니다. `0.6 kW`는 `600 W`로 정규화됩니다.
4. 값이 비거나 틀렸으면 제품 정보 수정에서 고치고 **수정 후 재검증**을 누릅니다.
5. **등록 승인**을 누르고 JSON을 다운로드합니다.
6. **제품 데이터베이스** 화면에서 등록된 제품을 확인합니다.

아래가 모두 되면 정상입니다.

| 확인 항목 | 성공 기준 |
| --- | --- |
| 앱 접속 | 제품 등록 화면과 메뉴가 표시됨 |
| 분석 | 추출 값·근거가 표시되고 승인 가능 상태 |
| 승인 | 등록 완료와 JSON 다운로드 표시 |
| 저장 | 제품 데이터베이스에서 제품 조회 가능 |
| 작업 복원 | 사이드바 최근 작업에서 선택하면 기존 결과 표시 |

업로드할 때 알아둘 점:

- 텍스트 PDF, XLSX, TXT(UTF-8·CP949)를 지원합니다. 파일당 최대 **20 MB**입니다.
- 여러 파일을 올리면 **제품 하나의 자료**로 함께 처리합니다. 서로 다른 제품은 별도 작업으로 올립니다.
- 스캔 PDF는 OCR을 지원하지 않아 파싱 오류가 납니다.
- **문서 원문은 OpenAI API로 전송되고**, 분석할 때마다 호출 비용이 듭니다.

다른 샘플로 확인하는 순서와 화면별 사용법은 [사용자 매뉴얼](USER_MANUAL.md)에 있습니다.

## 데이터 저장 위치

업로드 원본·DB·JSON은 기본으로 `runtime\`에 저장됩니다. 기존 데이터와 분리해 테스트하려면 서버를 켜기 전에 다른 폴더를 지정합니다. git에 잡히지 않도록 `runtime\` 안에 만드세요.

```powershell
$env:ONTOPRODUCT_DATA_DIR = "D:\ontology-product-system\runtime\demo"
```

빈 DB로 다시 시작하기, 기본 DB 초기화는 [새 DB로 테스트와 초기화](USER_MANUAL.md#새-db로-테스트와-초기화)를 참고하세요.

## 터미널별 명령

이 문서의 명령은 **PowerShell 문법**입니다. 환경 변수 문법이 터미널마다 달라서 다른 터미널에 그대로 붙여 넣으면 적용되지 않습니다. 프롬프트 모양으로 지금 터미널을 구분합니다.

| 터미널 | 프롬프트 예 |
| --- | --- |
| PowerShell | `PS D:\ontology-product-system>` |
| 명령 프롬프트(cmd) | `D:\ontology-product-system>` (앞에 `PS`가 없음) |
| Linux·macOS (bash, zsh) | `user@host:~/ontology-product-system$` |

cmd에서 `$env:...`를 입력하면 `파일 이름, 디렉터리 이름 또는 볼륨 레이블 구문이 잘못되었습니다.`가 나오고 값이 설정되지 않습니다. VS Code에서는 터미널 패널의 `+` 옆 드롭다운에서 PowerShell을 고를 수 있습니다.

| 작업 | PowerShell | cmd | Linux·macOS |
| --- | --- | --- | --- |
| 환경 변수 설정 (현재 창만) | `$env:ONTOPRODUCT_DATA_DIR = "..."` | `set ONTOPRODUCT_DATA_DIR=...` | `export ONTOPRODUCT_DATA_DIR=...` |
| 환경 변수 해제 | `Remove-Item Env:\ONTOPRODUCT_DATA_DIR` | `set ONTOPRODUCT_DATA_DIR=` | `unset ONTOPRODUCT_DATA_DIR` |
| 값 확인 | `$env:ONTOPRODUCT_DATA_DIR` | `echo %ONTOPRODUCT_DATA_DIR%` | `echo $ONTOPRODUCT_DATA_DIR` |
| 가상 환경 Python | `.venv\Scripts\python.exe` | `.venv\Scripts\python.exe` | `.venv/bin/python` |
| 가상 환경 생성 (pip 방식) | `py -3.12 -m venv .venv` | `py -3.12 -m venv .venv` | `python3.12 -m venv .venv` |

- cmd의 `set`은 `=` 앞뒤에 공백을 넣지 않습니다. 공백도 이름과 값에 들어갑니다.
- 이렇게 정한 값은 그 터미널 창에서만 유지됩니다.
- Linux·macOS에서는 경로 구분자 `\`를 `/`로 바꿉니다. 이 프로젝트를 Linux·macOS에서 실행해 검증한 기록은 아직 없습니다.

서버 실행 명령:

```bat
:: 명령 프롬프트(cmd)
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

```bash
# Linux·macOS
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```
