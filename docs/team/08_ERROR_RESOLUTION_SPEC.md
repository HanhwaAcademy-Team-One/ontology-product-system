# 결정적 문서 충돌의 해결 경로

기준일: 2026-10-09. 작업 4는 기존 runtime의 STOP·새 등록 작업 경로를 사용한다. 새 Graph action이나 schema 필드를 추가하지 않는다.

## 결정

| 오류 | recoverable | 해결 |
| --- | --- | --- |
| DocumentConflictError: 선택 속성·제품명·클래스 밖 미해결 충돌 | false | 원본 두 후보를 확인하고 수정한 문서로 새 등록 작업을 시작한다. 기존 작업은 STOP으로 끝낸다. |
| timeout·연결·일시적 서버/파일 접근 오류 및 미분류 예외 | 기존 true | 기존 RETRY를 유지한다. 일시적인지 불명확한 예외를 일괄 차단하지 않는다. |
| OntologyClassificationError | 기존 true | LLM 선택은 실행마다 달라질 수 있으므로 유형만으로 결정적이라고 단정하지 않는다. |

execute_agent는 충돌 예외만 recoverable=false로 기록한다. error_handler는 모든 미해결 오류가 recoverable인 경우에만 RETRY를 제시한다. 이미 저장된 구형 checkpoint의 DocumentConflictError는 recoverable=true여도 같은 방식으로 RETRY를 거부한다. 이 판정은 예외 유형을 사용하며 영어 message를 분석하지 않는다.

충돌 UI는 “같은 문서 재시도로 해결되지 않습니다. 후보를 확인해 문서를 수정한 뒤 새 등록 작업으로 올리세요.”라고 안내한다. 같은 충돌에 반복 모델 비용을 쓰지 않도록 RETRY를 숨긴다. STOP과 사이드바의 기존 새 등록 작업 버튼을 유지한다. 새 작업은 DocumentService → runtime.start로 실행한다. UI에서 Agent를 직접 호출하거나 state를 수정하지 않는다.

## 전후와 보존

D004 두 TXT의 weight=750 g/900 g, D005 두 TXT의 제품명 불일치는 실제 Parser와 고정 응답 Extraction에서 DocumentConflictError다. 수정 전 RETRY는 같은 오류를 다시 생성한다. 새 정책에서는 RETRY 직접 명령도 거부하고 STOP은 오류 이력을 남긴다.

예: 기존 case A는 STOPPED, 원본 FileReference·로그·error_events·checkpoint·manual_overrides·locked_fields는 그대로 보존한다. 문서를 정정한 새 case B는 새 ID와 업로드 원본을 사용하며 A의 수동 수정/잠금을 자동 복사하거나 삭제하지 않는다. B의 값을 검토하고 승인한 뒤 DB 1개와 JSON이 일치한다. 자동 추출 결과와 사람 정정 이후 결과는 평가에서 분리한다.

기존 작업을 직접 편집하려면 추출 전 제품명·부분 추출 결과·오류 원인·수동 override를 새 계약으로 전달해야 한다. 현재는 그 계약을 확대하는 대신 자료 정정 후 새 작업 경로를 사용한다. 원본 case A가 이미 등록된 경우 새 작업은 재등록 위험이 있으므로 기존 제품·중복 후보를 검토하고, Export 일시 실패는 기존 case A의 RETRY로 복구한다. 기존 case별 저장 멱등성은 바꾸지 않는다.

## 수용 조건

- D004·D005 실제 원본의 충돌 보존, 추가 RETRY 거부, STOP·오류 이력 유지.
- 정정한 입력의 새 case가 승인 전 DB에 저장되지 않고 승인 후 JSON과 DB 일치.
- 과거 recoverable=true 충돌 checkpoint도 반복 재시도 차단.
- 네트워크 일시 실패·Export 오류는 기존 RETRY·저장 멱등성 유지.
- HUMAN/locked 값이나 기존 case ID를 새 작업으로 조용히 이관하지 않음.

현재는 UI 내부에서 원본 문서를 편집하거나 충돌 제품명을 직접 고치는 기능은 지원하지 않는다. 사용자 요구가 생기면 별도 명령·복원 호환성 설계 후 추가한다.
