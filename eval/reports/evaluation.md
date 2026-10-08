# OntoProduct Evaluation

Run: 5553e130-4d72-4604-8fb1-e9e8723b0fd5
Generated (UTC): 2026-10-07T07:30:43.945382+00:00

Dataset: OntoProduct synthetic teaching fixtures (3 cases)

Three authored fixtures; not real document extraction or production accuracy.

## MOCK EVALUATION

Unmodified Mock workflow, no manual edits, zero automatic retries.

| Metric | Calculated value | Numerator / denominator |
| --- | ---: | ---: |
| Attribute Detection Precision | 0.6667 | 6 / 9 |
| Attribute Detection Recall | 0.6000 | 6 / 10 |
| Attribute Detection F1 | 0.6316 | 12 / 19 |
| Attribute Value Accuracy | 0.5000 | 5 / 10 |
| Unit Normalization Accuracy | 0.5000 | 4 / 8 |
| Ontology Classification Accuracy | 0.6667 | 2 / 3 |
| Required Field Detection Accuracy | 0.8000 | 8 / 10 |
| Duplicate Precision@3 | 0.0000 | 0 / 9 |
| Duplicate Recall@3 | 0.0000 | 0 / 2 |
| Duplicate Candidate Precision | N/A | 0 / 0 |
| Negative Query Accuracy | 1.0000 | 1 / 1 |

Agents: parser (mock, Mock), extraction (mock, Mock), ontology (mock, Mock), validation (mock, Mock), duplicate (mock, Mock), reviewer (mock, Mock), registration (mock, Mock)

- product_001: source SHA-256 b3ade37b4d04282a7c4d34e575cc97569c8a5741cfd450a5931a99ca67d97356
- product_002: source SHA-256 f291d8e64d883c00152e077c7604b3fa98ddf4464bc0e80d0d15aaf60a9a7ccb
- product_003: source SHA-256 f4ca69e018954eefe2c96e10c2c06fb03854e90b1810432851132044365e5a41

## RULE ENGINE EVALUATION

Canonical ground-truth query directly to the real SQLite DuplicateAgent; isolated seed catalog.

| Metric | Calculated value | Numerator / denominator |
| --- | ---: | ---: |
| Duplicate Precision@3 | 0.2222 | 2 / 9 |
| Duplicate Recall@3 | 1.0000 | 2 / 2 |
| Duplicate Candidate Precision | 1.0000 | 2 / 2 |
| Negative Query Accuracy | 1.0000 | 1 / 1 |

Agents: duplicate (sqlite-rule-engine, Real)

- product_001: source SHA-256 b3ade37b4d04282a7c4d34e575cc97569c8a5741cfd450a5931a99ca67d97356
- product_002: source SHA-256 f291d8e64d883c00152e077c7604b3fa98ddf4464bc0e80d0d15aaf60a9a7ccb
- product_003: source SHA-256 f4ca69e018954eefe2c96e10c2c06fb03854e90b1810432851132044365e5a41

## Metric definitions

- detection: Micro precision/recall/F1 of non-null raw extracted attribute names.
- value: Correct canonical normalized values / all non-null truth attributes; missing is wrong.
- unit: Correct canonical units / unit-bearing truth attributes; missing is wrong.
- required: Per truth-class required property, compare missing normalized values with MISSING_REQUIRED issues.
- duplicate: Precision@K = hits/(K*query_count); Recall@K = hits/all relevant labels; Candidate Precision = hits/returned candidates. Empty denominators are null.
