# 09. 평가·QA 담당자: 실제로 잘 되는지 확인하기

[공통 약속](00_COMMON.md) · [통합](08_INTEGRATION.md) · [분업표](../MOCK_REPLACEMENT_PLAN.md)

## 1. 내 역할

각 담당자의 “동작한다”는 말을 실제 문서와 사람이 검수한 정답으로 확인합니다. 어떤 값을 맞혔고 틀렸는지, 사람 수정 전과 후가 어떻게 다른지 재현 가능한 결과를 남깁니다.

합성 TXT 3개 Mock 평가는 Mock 제거와 함께 삭제했습니다. [document_runner.py](../../src/ontoproduct/evaluation/document_runner.py)가 inputdata의 80개 TXT/PDF/XLSX·75 업로드 조합을 격리 Real runtime으로 평가합니다. 기본 실행은 통신만 고정 참조 응답으로 대체한 `offline_reference`이며 실제 LLM 정확도가 아닙니다. 순차 실행 기록·정답 범위·실패 분모는 [04 실행 기록](04_EXECUTION_LOG.md)에 있습니다. 아래 초기 Real 평가 구현 계획은 현재 구현과 대조해 읽습니다.

```powershell
$env:ONTOPRODUCT_LIVE_LLM = "0"
.venv\Scripts\python.exe -m ontoproduct.evaluation.document_runner --dataset inputdata --output eval/document_reports
```

manifest의 기대값은 정답 후보이며 independent human review는 아직 false입니다. 파일은 verification의 SHA-256으로 확인하고 형식 대안은 각기 별도 작업, together 문서는 한 작업으로 처리합니다. 기존 보고서를 덮어쓰지 않고 실행 UUID 폴더에 JSON/Markdown을 남깁니다. 실제 모델은 별도 승인 후 `--live --cases ... --format ... --max-calls ... --time-limit-seconds ...`로 실행하며 현재 모델 설정을 재사용합니다. 호출·시간 한도는 service call 직전에 검사하고 진행 중 SDK 요청은 기존 timeout/retry를 유지합니다.

2026-10-09 사용자 요청으로 대표 TXT 4건을 gpt-5에서 Extraction 2.0.0/2.1.0으로 비교했습니다. [실모델 비교 보고서](../../eval/confidence_reports/20261009-0b4fe5df-6275-4095-aa12-3299b56c37d8/comparison.md)에 실제 16회 호출과 지표·실패를 기록했습니다. confidence 누락 감소 효과는 확인하지 못했으며 E008/E009의 상위 분류 선택으로 관계 오류를 놓쳤습니다. 전체 inputdata 실모델 평가 완료를 뜻하지 않습니다.

## 2. 파일 위치

| 위치 | 현재 기능 | 앞으로 할 일 |
| --- | --- | --- |
| [evaluation/document_runner.py](../../src/ontoproduct/evaluation/document_runner.py) | inputdata 오프라인·승인 후 실모델 평가 경로, 대표 TXT 4건 비교 실행 | 전체 실모델 평가·정답 독립 검수·분류 실패 보완 |
| [evaluation/metrics.py](../../src/ontoproduct/evaluation/metrics.py) | 지표 계산 | 기본 계산 재사용, 새 요구는 정의부터 합의 |
| [evaluation/report.py](../../src/ontoproduct/evaluation/report.py) | Markdown 보고서 | provider/model/prompt 정보 추가 |
| [views/evaluation.py](../../src/ontoproduct/views/evaluation.py) | inputdata 오프라인 참조 평가 실행/조회/다운로드 | 실모델 평가 결과 조회 |
| [inputdata/manifest.json](../../inputdata/manifest.json) | 사례별 파일·기대 결과·정규화 정답 후보 | 정답 독립 검수 |
| eval/document_reports/ | 실행 ID별 평가 JSON/Markdown | 실모델 결과 누적 |
| tests/test_evaluation.py | 지표 계산 검사 | 새 지표 정의 시 테스트 추가 |
| tests/test_real_workflow.py | 실제 문서·평가·충돌·복원·저장 통합 회귀 | 승인 범위의 실제 모델 확인 |

## 3. Ground Truth가 무엇인가요?

사람이 원문을 읽고 적은 정답입니다. 모델 답을 그대로 정답으로 복사하면 정확도를 측정할 수 없습니다.

현재 정답은 [inputdata/manifest.json](../../inputdata/manifest.json)에 있습니다. 사례마다 업로드할 파일 목록, `expected_outcome`(valid, missing_required, unsupported_unit, document_conflict 등), `expected_normalized_attributes`(canonical 단위 기준 값)를 적습니다. 파일 무결성은 `verification.json`의 SHA-256으로 확인합니다.

정답 power는 원문 0.6 kW를 canonical 600 W로 적습니다. 다른 단위처럼 보여도 같은 실제 사양을 평가하기 위한 것입니다.

manifest의 기대값은 정답 후보이며 사람의 독립 검수는 아직 하지 않았습니다. 중복 관련성 정답은 없으므로 중복 정확도는 주장하지 않습니다.

## 4. 실제 평가 실행 경로 만들기

현재 document_runner가 아래 순서로 구현되어 있습니다.

1. inputdata 사례를 읽고 파일 SHA-256을 확인합니다.
2. 격리된 평가 workspace/DB/checkpoint를 만듭니다.
3. 원본 PDF/XLSX/TXT를 DocumentService로 저장하여 FileReference를 얻습니다.
4. 실제 registry_factory를 WorkflowRuntime에 주입합니다.
5. runtime.start로 실제 Parser부터 Reviewer까지 실행합니다.
6. 사람이 고치기 전에 extracted/normalized/mapping/validation/candidate 출력을 저장합니다.
7. 정답과 이 출력으로 지표를 계산합니다.
8. EDIT/APPROVE와 DB/JSON은 별도 통합 테스트(test_real_workflow.py)에서 확인합니다.

사람이 정답을 보고 수정한 결과를 “자동 추출 정확도”에 넣으면 안 됩니다. 사람이 수정한 결과는 별도 최종 제품 품질/통합 결과로 기록합니다.

실제 Parser에는 원본 경로가 있는 FileReference를 넣습니다.

## 5. 통합용 DB와 중복 평가용 DB

기존 사용자의 runtime DB를 평가 대상으로 수정하지 않습니다. 평가 작업은 격리된 폴더에서 실행합니다.

중복 검출 성능만 보고 싶으면 canonical 정답 query를 실제 DuplicateAgent에 넣습니다. 전체 파이프라인의 효과를 보려면 실제 추출/정규화 결과를 query로 씁니다. 이 두 결과는 입력이 다르므로 보고서에서 구분합니다.

현재 factory는 문서 5개 슬롯만 등록하고 Runtime이 Duplicate/Registration을 실제로 연결합니다. factory만 build_workflow에 넣으면 두 슬롯이 비어 오류가 나므로 WorkflowRuntime을 사용하세요.

## 6. 현재 지표를 쉽게 읽기

| 지표 | 질문 | 현재 계산 기준 |
| --- | --- | --- |
| Attribute Detection Precision | 뽑은 속성 중 정답에 있는 것은? | 속성 이름 TP/(TP+FP) |
| Attribute Detection Recall | 정답 속성을 얼마나 찾았나? | TP/(TP+FN) |
| Attribute Detection F1 | precision/recall 균형은? | 2TP/(2TP+FP+FN) |
| Attribute Value Accuracy | 실제 값이 맞나? | canonical 값 정답 수 / 전체 non-null 정답 속성 |
| Unit Normalization Accuracy | 표준 단위가 맞나? | 정답 표준 단위 수 / 단위가 있는 정답 속성 |
| Ontology Classification Accuracy | 클래스가 맞나? | 일치 사례 / 전체 사례 |
| Required Field Detection Accuracy | 필수 속성의 누락을 올바르게 보고했나? | 정답 클래스의 필수 슬롯별 누락 판정 일치 |
| Duplicate Precision@K | 상위 K칸에 관련 후보가 얼마나 있나? | hits/(K×쿼리 수), 빈 칸도 포함 |
| Duplicate Recall@K | 관련 기존 제품을 얼마나 찾았나? | hits/전체 관련 정답 수 |

TP는 맞게 찾은 속성, FP는 정답 밖 속성, FN은 놓친 정답 속성입니다. 분모가 0이면 N/A이며 100%로 처리하지 않습니다. 중복 정답이 없는 문서는 별도 Negative Query Accuracy로 확인합니다.

현재 Attribute Value는 전체 정답 속성 기준으로 누락도 오답입니다. 문자열 “24”와 숫자 24는 같은 정답으로 처리하지 않습니다.

## 7. 어떤 평가 자료를 준비하나요?

- 모터와 베어링처럼 서로 다른 클래스.
- 값/단위가 다른 여러 제품.
- TXT, 텍스트 PDF, 표 PDF, XLSX.
- 여러 파일에 사양이 나뉜 제품.
- 누락 필수값·지원하지 않는 단위.
- 문서끼리 충돌하는 사양.
- 중복 정답이 있는 제품과 없는 제품.
- 스캔 PDF는 OCR 지원을 선언한 경우 별도 사례.

새 자료는 train/prompt 튜닝에 쓴 자료인지 독립 평가 자료인지 구분합니다. 이 작은 교육용 자료에서 높은 점수가 나왔다고 운영 정확도를 보장하지 않습니다.

## 8. 테스트 두 종류를 분리합니다

**자동 회귀/단위 테스트**는 외부 API 없이 재현되게 만듭니다. 파서 실제 파일 읽기, 고정된 모델 통신 응답에 대한 실제 Agent 처리, schema, 오류, lock, 저장을 확인합니다.

**실제 모델 확인**은 선택한 실제 provider/model로 실행합니다. 문서 정답 대비 실제 출력과 오류를 기록합니다. 모델 통신을 대체한 테스트 결과를 Real 정확도로 표시하지 않습니다.

test_phase2_workflow의 가짜 PDF/XLSX bytes는 `tests/doubles.py` 고정 Agent로 checkpoint 동작만 보는 테스트용입니다. 실제 Parser 통합 테스트는 정상 형식 파일을 씁니다.

## 9. 통합 테스트 시나리오

1. 실제 DM-600 문서를 업로드.
2. Parser text와 source/page 확인.
3. Extraction이 실제 DM-600 사양 추출.
4. Ontology가 0.6 kW를 600 W로 정규화.
5. Validation과 Duplicate가 완료된 다음 Reviewer 실행.
6. 누락값이 있으면 추가 시도 후 사람 검토에서 멈춤.
7. 사람이 속도를 수정하면 HUMAN/null과 locked 유지.
8. 분류 변경으로 부적합 수정값은 orphan에 보관/복원.
9. 승인 전 제품 DB가 늘지 않음.
10. 승인 후 DB 1개와 JSON 일치.
11. 반복 승인/Export 오류 retry에도 제품 수 유지.
12. 서버 재시작 후 검토/완료 작업 복원.
13. 모니터 metadata와 로그가 실제 Agent를 표시.
14. 평가 JSON/Markdown에 실제 입력·출력·hash·모드가 기록됨.

## 10. 테스트 명령과 보고서

신규 테스트 작성 후:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_real_workflow.py tests\test_evaluation.py -q
.venv\Scripts\python.exe -m pytest -q -W error::pytest.PytestCacheWarning
```

평가 CLI는 `python -m ontoproduct.evaluation.document_runner`이며 실모델은 `--live`와 호출·시간 제한을 함께 지정합니다([eval/README.md](../../eval/README.md)).

보고서에 남길 것:

- 실행 ID·시각·원문/정답 hash.
- provider/model과 prompt/Agent 버전.
- 실행 모드(offline_reference / live).
- 실제 Parser/Agent 출력과 오류.
- 지표 정의, 분자/분모, 실패 사례.
- 사람 수정 전/후 구분.
- 지원 범위와 미지원/OCR 여부.

완료 기준은 “전체 테스트 통과”와 “실제 문서·모델 평가가 별도로 재현된다”를 모두 충족하는 것입니다.
