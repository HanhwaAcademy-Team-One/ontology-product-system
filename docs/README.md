# 문서 목차

[프로젝트 홈](../README.md)

## 처음 읽는 순서

1. [Quick start](QUICK_START.md): 설치 → Mock 데모 → Real 모드 실행.
2. [사용자 매뉴얼](USER_MANUAL.md): 화면 사용, 검토·승인, 복원과 오류 대응.
3. [시스템 동작과 온톨로지](SYSTEM_AND_ONTOLOGY.md): 처리 순서와 업무 규칙.
4. [개발자 매뉴얼](DEVELOPER_GUIDE.md): 구조, 테스트, 평가와 패키징.

## 사용자·개발자 매뉴얼

| 문서 | 내용 |
| --- | --- |
| [Quick start](QUICK_START.md) | Python 3.12 설치, uv/pip, 첫 등록 확인 |
| [사용자 매뉴얼](USER_MANUAL.md) | 6개 화면, 등록·수정·승인·거절, 작업 재개, 저장 경로 |
| [개발자 매뉴얼](DEVELOPER_GUIDE.md) | 실행 구조와 계약, 검증 명령, 평가, 배포 파일 |
| [시스템 동작과 온톨로지](SYSTEM_AND_ONTOLOGY.md) | 상속, 정규화, 검증, 사람 수정, 승인과 저장 |
| [제품 온톨로지 모델](team/03_PRODUCT_ONTOLOGY.md) | 자체 의미 모델, YAML/RDF/OWL/SHACL, 확장·시각화 |
| [평가 자료 안내](../eval/README.md) | 합성 문서·정답, 보고서 계산과 해석 |
| [계산된 평가 보고서](../eval/reports/evaluation.md) | 지표 정의·분자·분모와 저장된 계산 결과 |

## 팀 협업·담당별 가이드

[팀 협업 가이드](MOCK_REPLACEMENT_PLAN.md)에서 현재 구현 상태와 분업표를 먼저 확인하세요. 01~03의 최초 교체 절차는 구현 당시 참고 자료이며, 현재 연결은 08 통합 가이드를 따릅니다.

| 담당 | 문서 |
| --- | --- |
| 공통 데이터·계약 | [00 Common](team/00_COMMON.md) |
| 문서 파싱 | [01 Parser](team/01_PARSER.md) |
| 정보 추출 | [02 Extraction](team/02_EXTRACTION.md) |
| 분류·정규화 | [03 Ontology](team/03_ONTOLOGY.md) |
| 검증 | [04 Validation](team/04_VALIDATION.md) |
| 중복 조회 | [05 Duplicate](team/05_DUPLICATE.md) |
| 검토 판단 | [06 Reviewer](team/06_REVIEWER.md) |
| 저장·Export | [07 Registration](team/07_REGISTRATION.md) |
| 설정·Registry·UI 연결 | [08 Integration](team/08_INTEGRATION.md) |
| 실제 문서 평가·QA 계획 | [09 Evaluation](team/09_EVALUATION.md) |
| 브랜치·PR·검토 | [Git 협업 가이드](GIT_WORKFLOW.md) |

## 명세·출처·이력

아래 문서는 설계 조건과 당시 검증 결과를 보존합니다. 과거 테스트 개수나 당시 미구현 항목을 현재 상태로 해석하지 않습니다.

| 문서 | 용도 |
| --- | --- |
| [02·03 구현 명세](team/02_03_IMPLEMENTATION_SPEC.md) | 추출·분류·의미 모델의 구현 정책과 완료 조건 |
| [02·03 인계 기록](team/02_03_IMPLEMENTATION_HANDOFF.md) | 단계별 구현·검증 이력 |
| [외부 자료 참고 기록](team/02_03_EXTERNAL_SOURCES.md) | 온톨로지 설계 참고 자료와 확인 기록 |
| [외부 → 내부 개념 대응표](team/03_EXTERNAL_CONCORDANCE.md) | 온톨로지 내재화 이관 기록 |
| [제3자 고지](THIRD_PARTY_NOTICES.md) | 출처·라이선스 고지 |
| [PHASE 1 보고서](PHASE1_REPORT.md) | 초기 Mock workflow·CLI 구현 당시 기록 |
| [PHASE 2 보고서](PHASE2_REPORT.md) | persistence·UI 구현 당시 기록 |
| [PHASE 3 보고서](PHASE3_REPORT.md) | 화면·평가·통합 구현 당시 기록 |
| [Compiled graph](workflow.mmd) | 저장된 Mermaid 실행 그래프 |
