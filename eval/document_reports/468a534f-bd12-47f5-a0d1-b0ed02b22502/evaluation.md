# OntoProduct Evaluation

Run: 468a534f-bd12-47f5-a0d1-b0ed02b22502
Generated (UTC): 2026-10-08T15:57:21.363737+00:00

Dataset: inputdata synthetic documents (75 cases)

Manifest truth candidates; offline reference responses are not LLM accuracy. No OCR. Duplicate relevance is unannotated; no duplicate accuracy claim.

## OFFLINE REFERENCE EVALUATION

offline_reference

| Metric | Calculated value | Numerator / denominator |
| --- | ---: | ---: |
| Attribute Detection Precision | 1.0000 | 244 / 244 |
| Attribute Detection Recall | 1.0000 | 244 / 244 |
| Attribute Detection F1 | 1.0000 | 488 / 488 |
| Attribute Value Accuracy | 1.0000 | 244 / 244 |
| Unit Normalization Accuracy | 1.0000 | 203 / 203 |
| Ontology Classification Accuracy | 1.0000 | 62 / 62 |
| Required Field Detection Accuracy | 1.0000 | 206 / 206 |
| Expected Outcome Accuracy | 1.0000 | 75 / 75 |

Agents: parser (local-document-parser, Real), extraction (structured-llm-adapter, Real), ontology (ontology-structured-llm-adapter, Real), validation (python-validation-rules, Real), duplicate (sqlite-rule-engine, Real), reviewer (python-review-rules, Real), registration (sqlite, Real)

- M001-000: source SHA-256 7d9473dc63624dcc463312f28633ba00020603cfe15f10656313e7552dad3527
- M001-001: source SHA-256 5c9b562b3a8b744771362e8d5382a7af4f773b37fdf16317e8b468687d6cc07e
- M001-002: source SHA-256 72ae4bd8eb5edd3814878cf3ee6d99b0881e5f24916a6f5eedd3683bd96fb4c9
- M002-003: source SHA-256 1784a560285133c466f402bd57de79f55bc10facb43601d28781caaaffbbd1de
- M002-004: source SHA-256 0a7de4d0ce407056062d3c0041d113cff7e550b6d776585a96453fdc87373b6d
- M002-005: source SHA-256 01469214c5c758fc6f2f279ba19fa8ba35c5322da0fd96f63febcfb979d7c4df
- M003-006: source SHA-256 6ab32e0e0dbf8713c65cddf008ef85130616d517469aa3cd955c6b279773470a
- M003-007: source SHA-256 089ad254ee201a117fb4c898ea8dcd7f990bf5d87f42598cb2e5fadf9b69f4b6
- M003-008: source SHA-256 77b587a6d390b42cb804474e72c0057247cb0663d69c0cd74bc888785efeca30
- M004-009: source SHA-256 0e0ff76125004be3fe959548a05c51f20c9859823a9cb8104484aa1129733957
- M004-010: source SHA-256 558ddd30890056c2ff1f9aa056bdaaec0b6c6d84c564941aaaf104047215e10e
- M004-011: source SHA-256 6f41aa95d4b99e3e2f7c6cc9b750d240ca6dc5018bb2181e73be8df7b9f2c847
- M005-012: source SHA-256 6943e448080b54b2b0cceda87ab9e799d5718ba7a2fd2a21014f3d514d078a8f
- M005-013: source SHA-256 cd2b336aa9769ef5bb7cffc0175d765837620105c11bdb126e32b2cea7e999d4
- M005-014: source SHA-256 96d322db3f8f9d9eedbc0a4f04d871d5c8e3db44155f66d93832b60745da040d
- M006-015: source SHA-256 6ec15508f1f2393cc9e8deaefcd63424db10d04d8042fa426caf71a3a75d1cce
- M006-016: source SHA-256 95c7599d26e2ddd43e76dafdcdc0e2e30fa5c35b8b3216d87ceecc8f8618b7ec
- M006-017: source SHA-256 7dae77a9e8f4e334229ece651ddb3194e741e18a1992c49260799f1dc6d4744d
- M007-018: source SHA-256 a10c1f93608492ec8645b79064ad7c8d77e8846c7576d502a34549d137b973a9
- M007-019: source SHA-256 a6e68690904cbb1b991aacc2d6459758447eda3b4caa1729d13cc5032ef1c6c9
- M008-020: source SHA-256 93046387a838c0e9b2faef715dbc6324464d041c89a68a84c5ac95ce2120edda
- M008-021: source SHA-256 8bd4f7af3908634559eb473b1039dcdc4f272de47763e6e67a6f88f70544d00d
- M009-022: source SHA-256 70829047655dcd7784b83fc4421202ee62d013209ca797a44166847e4179aabd
- M009-023: source SHA-256 b7a2c480f9b1848e061460ce98178b1c20124a313aae101cd07c24c99cdfbfed
- M010-024: source SHA-256 d69c1444a8a401ce5ca77b0e9b556633a8d6342e6d694d7cec2d82b29a076c0f
- M010-025: source SHA-256 56bef8d58ade0ad5cf17861c99a79807345eaac69734bbc26b8b687f32bbb32d
- M011-026: source SHA-256 7f42d6ab50557911f75036ca027b2773897e2e634c556903438d318219589ef9
- M012-027: source SHA-256 541dcd2d8b9431d522dbb9e3ee897f1368048befa938b404dd4633c913de8bed
- M013-028: source SHA-256 966389787ce6ae4c35a815190b591dfd8ec403ddf9bb0eb1776968080c079de4
- M014-029: source SHA-256 74817d3e78639a8b7193f91698dca8ab69caa9d80ed045a03f28234295533000
- M015-030: source SHA-256 98c8425fb8c521b97ee70eeabd3a48d266cf56aa0557cb1fd6b4d56202498fac
- M016-031: source SHA-256 2b60fe5d982d3124778b7e9fe7fcd2f96be9487c16b51cdf6067ab29cb676001
- M017-032: source SHA-256 6481c3fa94cb5d3e7d780fa735ebf078bb88598a5dfbe5910d6ab77ef598a3e2
- M018-033: source SHA-256 c55d126c9b6f8754915ec25c2c5ec5e2037e6dfa2b708aaad0bca1839a249737
- M019-034: source SHA-256 32eec8443743816df3aa0eecdd8ff76db78394a911205de210cb9d6bde72baa9
- M020-035: source SHA-256 214225bc4729a7ff3f24111df3b20cf1e145fdecf268875fc316037d09ba1d50
- B001-036: source SHA-256 352d7a26dd18869c836991d813bebefb07697377d2174da4e384e17718afa7fc
- B001-037: source SHA-256 931eecb058075ebefec1bdd83770d2e791a50e42bfec624feeb330a1f5d8bff7
- B001-038: source SHA-256 41278cefdac58f9726b88f33086b3b6193c16d82496cf415c6dfff472f1a6553
- B002-039: source SHA-256 11bb57cd7f87ffa93512fd67b1b741b7a0ed4de12f5172cd110cc6ea4fec3bf8
- B002-040: source SHA-256 06c34dfc150daf3332b277fd29a7860c7bf9fea263a4f20d56f4d322441cd0bd
- B002-041: source SHA-256 379104dcbefd5ba25317332d0262cb1ce80570c1ef946ef931f9c952db3e7b49
- B003-042: source SHA-256 7f0743167a38ceb5301aba2768ab597b94910d8bf7c7dc854854ba0ec83b1c02
- B003-043: source SHA-256 d18750b36315a4574f2d3aee7be8768222a37b2535cdea9bb441d0aaff891d02
- B003-044: source SHA-256 92af1121ec875f3d7c3c67e9a65f16b19ee6d3154ccc377445939933484c530c
- B004-045: source SHA-256 7289fd6272e1b5433b99c557a8eb3bb9cc343daad061b3ef08e4d462dc62a951
- B004-046: source SHA-256 d357156df72ad918a0296b407c475dddf22b6a7f30035c17f8271aab3390d1e7
- B004-047: source SHA-256 9dd4ca254ded5f00446d49ed28fbd0dd1148dc04a817c6498c2e6bcc5c3991ea
- B005-048: source SHA-256 02a28b13e13bcaee99b79aac27585bfb77a7fab1c725a731a5e183c1d066e3d3
- B005-049: source SHA-256 508ddfa83fdbc0a12bb79ee8f86b82bc23c58bdf21c2eec5de07ad9412b734fa
- B006-050: source SHA-256 9ac16b7835f8bdcf78e9503a78b53d197e8fa3c7dff6968f0fc1ef5dc4ee4610
- B007-051: source SHA-256 04f31f2c5a58c7132354374c5892d6f90946fa71b07dcf36ca6a6c13fec076ff
- B008-052: source SHA-256 24babe33d2652f257664ef9859bb3037613e8525b68bf5772e55be09062a56d8
- B009-053: source SHA-256 5b2e4e9ab44a1ce335910763060b780b06aa27b793dba0ae4581e66ab90085a3
- B010-054: source SHA-256 00ef7a112502c2227f0bf7061e14d87a52f788fd2f82e970835e337236289ce2
- E001-055: source SHA-256 b8f4553d001a594d869d201408590621dffb36e2e7eb4a1e2e1bac63d9be889c
- E002-056: source SHA-256 d3eae3a003f125aa89a3f566639a44e7453b9d4f15a7288bb2cbed1a5462cb67
- E003-057: source SHA-256 288373acd3d2d11d2e4142929e417dce16ce68a080e10f2bb57697c9456e2b2b
- E004-058: source SHA-256 85271a3583b4c94e9e475cfd211deae78a57e50725ea325cdaab341c9e653dce
- E005-059: source SHA-256 bcefcc887e6672d1a0d20e7f9cf2272be61c1196adcb5fff317c0ae086ff8231
- E006-060: source SHA-256 cadf6215a871164f2b947ed72d773578a2082b2f578e3baa101a6454f08d1605
- E007-061: source SHA-256 28dd22b5acc4f54a44ab1df8e535d3cc25070cc4beecf5c1a4687e11fecdbdd3
- E008-062: source SHA-256 5af365f896134113149d20991bc883d68cf4a402f99fe43556f4f9a7ce04d5d1
- E009-063: source SHA-256 42e2f11f308c542c3aa26b4c713261ff5201fcdfefd9eda9a0616ecfb250354b
- E010-064: source SHA-256 70e80acb067f63e116b32b958b5b6dd23d66d3665f6b9c0d2e2e9b654fdb4d40
- E011-065: source SHA-256 a863e3cf51eddeaec19b5ef8862d1236f8fe85f3c92b69b4730dd6e2449ae951
- E012-066: source SHA-256 62c8500fbce50d331633d530496e16260d4ed4dbc1aaef9b4d06f5f81c7ea4b7
- E013-067: source SHA-256 d2c4c917952694e0c3ba5e12cfd7993cfcbe4dbda25b6e36f4d64c354b290c72
- E014-068: source SHA-256 3fdab4c3d8d97d34c265533b9eecda445e6fb317a7e937694a813242142eba03
- E015-069: source SHA-256 07eb49e47c19496610b8c5ee1b4c0b5916567d092c637612ca660eb0cf6ea8d8
- D001-070: source SHA-256 16912e7dca080018829a81e038d3acb5435683a31f128fd3d8f8f11b7f12b002
- D002-071: source SHA-256 5bd3174a48312f3aca42293ac8b1ab41686848efce58f7cb72f21d758ce46235
- D003-072: source SHA-256 3d5b40749aa1807a2e2bbb9391fabf39af275ccd26f3a2223db85f268a9c678c
- D004-073: source SHA-256 450480a5e30648d508529138e31b3111f4e5ed11f0f289984fffc848701e1877
- D005-074: source SHA-256 663227f9c0c34c256c5e4d64a215e8e22de25c6768d50e5ee74e36097dab2a76

## Metric definitions

- outcome_mapping: {'valid': 'valid', 'equivalent_values': 'valid', 'classification_error': 'classification_error', 'missing_required': 'missing_required', 'unsupported_unit': 'unsupported_unit', 'semantic_error': 'semantic_error', 'required_conflict': 'required_conflict', 'optional_conflict': 'document_conflict', 'identity_conflict': 'document_conflict'}
- quality_metrics: Known normalized truth only; failures remain in denominators. Unknown truth coverage is explicit.
- automatic: All outputs before EDIT/APPROVE; no products saved.
- calls: Service calls; SDK transport retries are not counted separately.
