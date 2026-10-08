# OntoProduct Evaluation

Run: 5510a732-83da-4761-844b-00067300e4f0
Generated (UTC): 2026-10-08T16:31:57.341814+00:00

Dataset: inputdata synthetic documents (4 cases)

Manifest truth candidates; offline reference responses are not LLM accuracy. No OCR. Duplicate relevance is unannotated; no duplicate accuracy claim.

Mode: live
Service calls: 8 (SDK retries excluded)
Normalized truth: 2 known / 2 unknown; independent human review: False
Provider/model: openai/gpt-5
Prompt versions: extraction=2.0.0, ontology=3.0.0
Failures/limits: ['E008-002', 'E009-003'] / []
Manifest SHA-256: 5811c2f9a9c2e493e7c6df621c135ee666fb441a92c022774b055ca88d7a68b7
Verification SHA-256: 6b677138c41406769630a899e9f40095183e61a02f2718144305b8337188e887

## LIVE MODEL EVALUATION

live

| Metric | Calculated value | Numerator / denominator |
| --- | ---: | ---: |
| Attribute Detection Precision | 1.0000 | 7 / 7 |
| Attribute Detection Recall | 1.0000 | 7 / 7 |
| Attribute Detection F1 | 1.0000 | 14 / 14 |
| Attribute Value Accuracy | 1.0000 | 7 / 7 |
| Unit Normalization Accuracy | 1.0000 | 6 / 6 |
| Ontology Classification Accuracy | 1.0000 | 2 / 2 |
| Required Field Detection Accuracy | 1.0000 | 6 / 6 |
| Expected Outcome Accuracy | 0.5000 | 2 / 4 |
| AI Confidence Null Rate | 0.0000 | 0 / 12 |
| Human Repair Case Rate | 0.5000 | 2 / 4 |

Agents: parser (local-document-parser, Real), extraction (structured-llm-adapter, Real), ontology (ontology-structured-llm-adapter, Real), validation (python-validation-rules, Real), duplicate (sqlite-rule-engine, Real), reviewer (python-review-rules, Real), registration (sqlite, Real)

- M001-000: source SHA-256 7d9473dc63624dcc463312f28633ba00020603cfe15f10656313e7552dad3527
  Expected: valid; observed: valid; status: READY_FOR_HUMAN; after-human result: None
- B001-001: source SHA-256 352d7a26dd18869c836991d813bebefb07697377d2174da4e384e17718afa7fc
  Expected: valid; observed: valid; status: READY_FOR_HUMAN; after-human result: None
- E008-002: source SHA-256 5af365f896134113149d20991bc883d68cf4a402f99fe43556f4f9a7ce04d5d1
  Expected: semantic_error; observed: valid; status: NEEDS_FIX; after-human result: None
  attributes.construction / UNKNOWN_PROPERTY: Property is outside this ontology class
  attributes.inner_diameter / UNKNOWN_PROPERTY: Property is outside this ontology class
  attributes.outer_diameter / UNKNOWN_PROPERTY: Property is outside this ontology class
- E009-003: source SHA-256 42e2f11f308c542c3aa26b4c713261ff5201fcdfefd9eda9a0616ecfb250354b
  Expected: semantic_error; observed: valid; status: NEEDS_FIX; after-human result: None
  attributes.inner_diameter / UNKNOWN_PROPERTY: Property is outside this ontology class
  attributes.outer_diameter / UNKNOWN_PROPERTY: Property is outside this ontology class
Agent versions: parser=0.3.0, extraction=2.0.0, ontology=3.0.0, validation=0.2.0, duplicate=0.3.0, reviewer=0.1.0, registration=0.2.0

## Metric definitions

- outcome_mapping: {'valid': 'valid', 'equivalent_values': 'valid', 'classification_error': 'classification_error', 'missing_required': 'missing_required', 'unsupported_unit': 'unsupported_unit', 'semantic_error': 'semantic_error', 'required_conflict': 'required_conflict', 'optional_conflict': 'document_conflict', 'identity_conflict': 'document_conflict'}
- quality_metrics: Known normalized truth only; failures remain in denominators. Unknown truth coverage is explicit.
- automatic: All outputs before EDIT/APPROVE; no products saved.
- calls: Service calls; SDK transport retries are not counted separately.
- confidence: Null scores / observed non-null normalized AI attributes. Unproduced attributes are outside this score-only denominator; quality metrics still penalize missing known truth. No calibrated probability claim.
