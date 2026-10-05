# Evaluation fixtures

The three source TXT documents and their JSON ground truth are authored synthetic teaching data. They are not measurements of real PDF/Excel extraction. Canonical power labels convert kW to W according to the project's ontology.

Duplicate relevance labels identify the single seed product with matching canonical specifications; BR-6201 has no relevant seed duplicate. Other same-class products may be retrieved as false positives. Labels were defined from the source specifications, not from observed rankings.

Run from the repository root:

```powershell
.venv\Scripts\python.exe eval/report.py
```

Reports are computed from unmodified Agent outputs and saved in reports/evaluation.json and reports/evaluation.md. The JSON includes source/truth hashes, raw extracted and normalized attributes, ontology mapping, validation issues, candidate rankings, and execution logs.

MOCK EVALUATION uses the unchanged Mock workflow with zero automatic retries and no manual corrections. RULE ENGINE EVALUATION separately runs the real SQLite DuplicateAgent on canonical truth queries against an isolated seed database. There is no combined Mock/Real score.

Metric denominators and missing-value handling are documented in the report. N/A means an empty denominator; it is not a perfect score. Precision@3 includes empty ranking slots. Recall@3 is micro over positive relevance labels; negative queries are measured separately.
