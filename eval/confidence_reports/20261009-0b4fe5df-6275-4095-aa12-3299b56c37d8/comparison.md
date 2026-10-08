# 작업 5: confidence 실모델 비교

2026-10-09 사용자 요청으로 실제 OpenAI `gpt-5`를 호출했다. **confidence 누락 감소 효과를 확인하지 못했다.** 정상 사례의 값·단위는 두 버전 모두 맞혔지만, 오류 사례의 분류 문제가 함께 발견됐다.

| 지표 | 기존 2.0.0 | 변경 2.1.0 |
| --- | ---: | ---: |
| 실제 API service call 성공 | 8/8 | 8/8 |
| 관측된 non-null AI 속성의 confidence null | 0/12 (0%) | 2/11 (18.2%) |
| 동일한 원문 기재 11개 속성의 confidence null | 0/11 | 2/11 |
| 제공된 속성 confidence < 0.70 | 0 | 0 |
| 정상 2건의 값 정확도 | 7/7 | 7/7 |
| 정상 2건의 단위 정확도 | 6/6 | 6/6 |
| 전체 4건의 분류 일치 | 2/4 | 2/4 |
| 기대 오류 유형 일치 | 2/4 | 2/4 |
| NEEDS_FIX / READY_FOR_HUMAN | 2 / 2 | 2 / 2 |
| Extraction / Ontology 자동 재시도 | 0 / 0 | 0 / 0 |
| 저장된 제품 | 0 | 0 |
| 전체 실행 시간 | 115.50초 | 113.31초 |

기준 버전은 E008에서 원문에 있는 `construction`을 추가 추출해 관측 속성이 12개다. 두 버전의 공통 원문 속성 11개로 비교해도 null은 0개에서 2개로 늘었다. null을 보정하거나 0.70 기준을 변경하지 않았다. 점수는 정답 확률이 아니다.

## 조건과 재현 근거

- 같은 TXT `M001`, `B001`, `E008`, `E009`, 같은 manifest/verification SHA-256, 같은 모델과 현재 Agent 코드를 사용했다. 각 버전 1회씩 순차 실행했다.
- 기존 커밋의 extraction.py에서 AST로 VERSION/INSTRUCTIONS 문자열을 읽었다. 평가 프로세스 안의 ExtractionAgent 프롬프트·버전만 교체하고 실행 후 복원했다. 소스 프롬프트를 체크아웃하거나 수정하지 않았다. Ontology 프롬프트는 두 실행 모두 3.0.0이다.
- 각 실행은 기존 `run_document_evaluation(..., mode="live", case_ids=["M001", "B001", "E008", "E009"], file_format="txt", max_calls=8, time_limit_seconds=600)` 경로를 사용했다. 사용자 DB 대신 사례마다 새 임시 runtime을 사용했다.
- 기존 설정은 timeout 250초, SDK max_retries 2다. 한도는 service call 직전에 검사하며 진행 중 요청의 timeout은 유지한다. 호출 수는 SDK 내부 HTTP 재시도를 따로 세지 않는다. 사용 토큰·실제 청구 비용은 수집하지 않았다.
- 자동 Workflow 재시도를 두 버전 모두 끄고 프롬프트 비교를 격리했다. 따라서 재시도 감소 효과는 판단할 수 없다. READY_FOR_HUMAN인 정상 2건도 사람 승인이 필요하다. EDIT/APPROVE는 실행하지 않았다.
- 합성 문서 4건·각 버전 1회이며 독립 사람이 검수한 gold가 아니다. 정규화 정답 후보가 있는 M001/B001만 기존 값·단위 지표에 들어간다. E008/E009의 정규화 정답은 manifest에서 null이므로 전체 분류·오류 유형 지표를 별도로 봐야 한다. 이 결과를 전체 자료나 실제 업무 정확도로 일반화하지 않는다.

[비교 JSON](comparison.json)에는 두 프롬프트 원문·hash, 설정, 실행 ID, 지표, 사례 요약, 후속 항목이 있다. 실제 출력·원문 hash·Agent 버전·호출 시간·오류는 다음 보고서에 있다.

- [2.0.0 JSON](../../document_reports/5510a732-83da-4761-844b-00067300e4f0/evaluation.json) · [Markdown](../../document_reports/5510a732-83da-4761-844b-00067300e4f0/evaluation.md)
- [2.1.0 JSON](../../document_reports/dc6a8ae3-786e-4c45-b19e-ae26000d3c76/evaluation.json) · [Markdown](../../document_reports/dc6a8ae3-786e-4c45-b19e-ae26000d3c76/evaluation.md)

## 확인한 실패와 남은 보완

E008은 내경=외경=20 mm, E009는 내경 30 mm·외경 20 mm다. 두 버전 모두 원문 값을 옮겼고 Extraction의 candidate_class는 Bearing이었다. 그러나 Ontology는 두 사례를 MechanicalPart로 선택했다. 해당 분류에는 Bearing 비교 규칙이 없으므로 Validation.valid=true와 UNKNOWN_PROPERTY 경고가 나왔고, 기대한 semantic_error를 놓쳤다. 낮은 분류 confidence(0.60~0.62)로 Reviewer/Graph가 NEEDS_FIX·can_register=false에 멈췄다. 오류의 올바른 SHACL 판정과 낮은 confidence로 인한 중단은 다르다.

변경 버전은 E009의 두 치수 confidence만 null로 반환했다. 속성 관계 오류를 문서 후보 충돌과 혼동했을 가능성은 있으나, 모델의 판단 이유를 수집하지 않았으므로 원인을 확정하지 않는다.

다음 보완은 이번 결과를 보존한 뒤 별도 변경으로 수행한다.

1. confidence가 **원문 값을 정확히 옮겼다는 확신**이며 제품 사양의 의미적 유효성과 별개라는 점, 문서 후보 간 충돌의 의미를 더 명확히 한다. 새 안내의 효과는 다시 측정해야 한다.
2. 근거 없이 상위 분류를 선택해 하위 분류의 검증 규칙을 놓치는 경로를 보완한다. E008/E009 + MechanicalPart 선택을 고정 응답으로 재현하는 테스트를 먼저 만든다. ontology 프롬프트와 로컬 분류 일관성 검사 범위를 검토한다.
3. 반복 비교와 실제 재시도 정책을 포함한 다음 평가로 효과를 확인한다. 이번 16회 이후 추가 모델 호출은 하지 않았다.

confidence·근거·Reviewer 관련 회귀 테스트는 **94 passed**다. 이번 작업에서는 기능 코드를 바꾸지 않았다.
