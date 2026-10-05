# PHASE 3 완료 보고서

2026-10-05 · D:\ontology-product-system · Python 3.12.10

## 구현 완료

| 요구 항목 | 결과 |
| --- | --- |
| Dashboard | SQL 전체 제품/작업 집계, 상태·분류 차트, 최근 작업 복원, 재시도·미해결 오류 |
| Product Database | 이름·분류·등록 구분 필터, 속성·출처·근거·신뢰도, 상세 JSON 및 다운로드 |
| Ontology Explorer | 실제 ontology의 상속도, 상속 속성/정의 클래스, 필수·선택·범위·단위, 변환 미리보기 |
| Agent Monitor | Registry metadata, Provider/Version/Mock·Real/reads/writes/Health, 측정 평균 시간, 실행·오류 이력 |
| Evaluation | 합성 원문 3개와 Ground Truth, 계산 지표, 출력/정답 hash, JSON/Markdown 보고서 |
| Compiled Graph | 실제 build_workflow().get_graph().draw_mermaid() 결과 화면 표시 및 다운로드 |
| README / 통합 검증 | 실행·데모·저장/복원·평가·한계 문서, AppTest 및 최종 persistence 통합 테스트 |

기존 등록 페이지를 기본 화면으로 유지하고 6개 페이지를 명시적 st.navigation에 연결했습니다. dashboard, ontology, agents, evaluation URL을 추가했습니다.

## 주요 구현 파일

- `views/dashboard.py`, `ontology_explorer.py`, `agent_monitor.py`, `evaluation.py`: 새 화면.
- `views/product_database.py`: 필터와 속성/근거 표시.
- `services/analytics_service.py`: 저장된 state 및 Registry 메타데이터 조회/집계.
- `services/workflow_runtime.py`: case별 Registry 보관과 metadata/compiled diagram 인터페이스.
- `repositories/`: 전체 SQL 집계와 제품 분류/등록 구분 필터.
- `evaluation/metrics.py`: 9개 필수 평가 지표와 음성 중복 쿼리 지표.
- `evaluation/runner.py`, `report.py`: Agent 실제 실행, 평가 분리, 검증 가능한 보고서 저장.
- `eval/documents/`, `ground_truth/`: 합성 TXT 원문 및 canonical 정답 JSON 3개.
- `eval/evaluate_extraction.py`, `evaluate_ontology.py`, `evaluate_duplicate.py`, `report.py`: 명세의 평가 진입점.
- `tests/test_evaluation.py`, `test_phase3_integration.py`, `test_phase3_ui.py`: PHASE 3 검증.

PHASE 1 workflow.py/routing.py/nodes.py/state.py 및 Agent base.py/registry.py의 SHA-256은 기존과 같습니다. HITL, Router, Reducer, Agent 계약은 재설계하지 않았습니다. 추가 dependency 없이 기존 pinned 환경을 사용합니다.

## 평가 방식과 결과

평가 원문과 정답은 교육용으로 작성한 합성 fixture입니다. 모터 2개와 베어링 1개로 구성합니다. 정답은 원문 사양과 ontology의 canonical 단위에 맞추며, 후보 relevance는 동일 사양 seed 제품으로 주석 처리했습니다.

**MOCK EVALUATION**은 기존 Mock workflow를 변경하지 않고 실행합니다. 추가 retry는 0, 수동 수정은 없습니다. Parser/Extraction/분류/검증/중복의 실제 반환값으로 계산하며 Mock이 모든 문서에 DM-500을 반환하는 한계도 그대로 반영합니다.

**RULE ENGINE EVALUATION**은 실제 SQLite DuplicateAgent를 별도로 실행합니다. 정답의 canonical query를 사용하여 추출 오류를 분리하고, 독립 임시 DB의 seed catalog를 대상으로 평가합니다. 사용자 DB를 변경하지 않습니다. Mock과 Real 결과를 합산하지 않습니다.

계산 결과는 [evaluation.md](../eval/reports/evaluation.md), 원본 출력/로그/정답/원문 hash는 [evaluation.json](../eval/reports/evaluation.json)에 있습니다. 모든 지표에 분자·분모를 기록했습니다. Attribute Value는 전체 정답 속성 기준이며 누락도 오답입니다. 필수 항목 탐지는 정답 클래스의 필수 속성별 누락 여부를 validation의 MISSING_REQUIRED issue와 비교합니다. Precision@3은 쿼리 수 × 3 기준이며 빈 슬롯도 분모에 포함하고, Recall@3은 relevant label 전체 기준입니다. 빈 분모는 N/A입니다.

이 결과를 실제 PDF/Excel 추출이나 LLM 정확도로 해석할 수 없습니다. 표본 3개의 교육용 평가입니다.

## 검증

실제 Windows 사용자 `isaac\eodud`에서:

```powershell
.venv\Scripts\python.exe -m pytest -q -W error::pytest.PytestCacheWarning
```

**166 passed in 17.85s**. PHASE 2의 148개에 PHASE 3의 18개를 추가했으며 캐시 권한 경고가 없었습니다.

- 평가의 TP/FP/FN, canonical 값·단위, 필수 필드·분류, 빈 분모, 음성 쿼리, K 슬롯, 타입 구분 검증.
- 기록된 출력의 값·단위를 바꾸면 지표도 바뀌는지 확인.
- Ground Truth 경로 탈출/중복 ID 거부, 보고서와 원본 JSON 저장 일치.
- 업로드 → 사람 수정 → SQLite 연결 종료 → 새 runtime 재개 → 승인/반복 승인 → 제품/JSON → dashboard/monitor → 평가의 최종 통합.
- UI의 빈 대시보드, 등록 후 집계·복원, 단위 변환, metadata/로그/graph, 실제 평가 실행·다운로드, DB 필터 검증.
- Streamlit AppTest의 명시적 page hash는 st.switch_page 후 다음 요청 전에 동기화했습니다. 실제 브라우저 화면 전환도 별도로 검증했습니다.

브라우저에서 서버를 재시작하고 기존 SQLite 제품 1개와 완료 작업 1개가 복원되는 것을 확인했습니다. 대시보드 차트, ontology 상속 Mermaid, Agent monitor의 compiled Mermaid, 평가 버튼과 계산 결과/보고서 다운로드를 확인했습니다.

compileall, source distribution/wheel 빌드 및 uv lock 확인을 완료했습니다. sdist에는 앱 진입점·설정·eval 원문/정답/보고서·문서·테스트를 포함하도록 설정했으며 runtime, 사용자 DB, cache는 제외합니다.

## 실행 및 남은 제한

[앱](http://127.0.0.1:8502) · [대시보드](http://127.0.0.1:8502/dashboard) · [평가](http://127.0.0.1:8502/evaluation)

```powershell
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
.venv\Scripts\python.exe eval/report.py
```

PHASE 1~3 교육용 범위는 완료했습니다. Parser/Extraction/Ontology/Reviewer는 Mock이며 실제 PDF/Excel 파싱이나 LLM 연결은 추가 구현 범위입니다. 앱은 로컬 인증 없는 교육용입니다. 이력 집계는 최근 최대 100개, 제품 검색/중복 catalog는 최신 최대 500개입니다. Health는 BaseAgent.health_check 응답이며 외부 provider 연결 확인이 아닙니다.

공식 API 확인: [Streamlit Mermaid](https://docs.streamlit.io/develop/api-reference/charts/st.mermaid_chart), [Navigation](https://docs.streamlit.io/develop/api-reference/navigation/st.page), [uv build backend inclusion](https://docs.astral.sh/uv/configuration/build-backend/).
