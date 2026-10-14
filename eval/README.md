# Evaluation

## Inputdata document evaluation

```powershell
.venv\Scripts\python.exe -m ontoproduct.evaluation.document_runner --dataset inputdata --output eval/document_reports
```

The default is offline_reference: actual TXT/PDF/XLSX Parser, Agents, SHACL and an isolated temporary WorkflowRuntime, with manifest raw values supplied through a quoted-reference transport. It does not measure LLM quality. The manifest normalized values are truth candidates, not independently human-reviewed gold. Unknown normalized truth coverage is explicit; failed known-truth cases remain in quality denominators. Expected outcome accuracy includes every selected group. Missing, required conflicts, optional conflicts and identity conflicts remain distinguishable in the report.

Reports use a fresh run ID and retain source/truth hashes, provider/model, prompt/Agent versions, calls, retry counts, errors and metrics. No EDIT/APPROVE is sent, so automatic quality excludes human repair and DB registration. Temporary uploads/DB/checkpoints/exports are removed after each group; report files remain. Human repair/restore/approval is covered separately by test_real_workflow.py.

Actual calls require user approval, an existing SDK key and model settings. Example prepared scope, **do not run before approval**:

```powershell
.venv\Scripts\python.exe -m ontoproduct.evaluation.document_runner --live --cases M001 B001 E008 E009 --format txt --max-calls 8 --time-limit-seconds 600 --output eval/document_reports
```

Limits apply before each service call. SDK transport retries are separate and an in-flight request retains its existing timeout/retries. All selected groups, including failures and limit-blocked groups, stay in the report. See [execution record](../docs/team/04_EXECUTION_LOG.md) for results and [requirements](../docs/team/04_REQUIREMENTS_06_08.md) for OCR/scale/storage questions.

On 2026-10-09 the user requested task 5 live validation. Two extraction prompt versions were evaluated on the four representative TXT cases with the same gpt-5 settings: 16 successful service calls in total. The [comparison](confidence_reports/20261009-0b4fe5df-6275-4095-aa12-3299b56c37d8/comparison.md) records prompt hashes, settings, both raw reports, denominators and limitations. Confidence nulls were 0/12 versus 2/11; known-truth value/unit accuracy was unchanged. Both versions selected MechanicalPart for invalid Bearings E008/E009 and missed the expected relation errors, while low classification confidence kept registration eligibility false. This is neither evidence of improvement nor a full-dataset live evaluation. Workflow retries were disabled equally in both runs.
