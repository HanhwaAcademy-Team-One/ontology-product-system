"""Rule-based duplicate candidate search.

Stages follow docs/team/05_DUPLICATE.md:
[1] structure -> [2] normalize -> [3] key specs -> [4] comparison method -> [5] retrieve
-> [6] compare -> [7] verdict -> [8] evidence -> [9] verify.
The service only proposes candidates; approval stays with the Reviewer and the human review.
"""
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from math import isclose

from ontoproduct.schemas.duplicate import DuplicateCandidate
from ontoproduct.schemas.ontology import OntologyMapping
from ontoproduct.schemas.product import NormalizedProduct
from ontoproduct.services.ontology_service import OntologyService

NEAR_TOLERANCE = 0.02  # Relative gap still treated as rounding/notation noise (500 W vs 505 W).
KEY_WEIGHT, AUXILIARY_WEIGHT = 1.0, 0.3
SPEC_WEIGHT, NAME_WEIGHT = 0.6, 0.4
DIFFERENT_MODEL_NAME_CAP = 0.3  # DM-500 vs DM-510 look alike as strings but name different models.
CANDIDATE_THRESHOLD, LIKELY_THRESHOLD = 0.6, 0.85
STATUS_SCORE = {"MATCH": 1.0, "NEAR": 0.5, "CONFLICT": 0.0, "MISSING": 0.0}
VERDICT_LABELS = {"LIKELY_DUPLICATE": "중복 가능성 높음", "POSSIBLE_DUPLICATE": "중복 의심"}


@dataclass(frozen=True)
class Value:
    compare: object  # Normalized value used for comparison.
    display: object  # Canonical value reported as evidence.
    unit: str | None


@dataclass(frozen=True)
class Profile:
    product_id: str | None
    name: str | None
    name_tokens: tuple[str, ...]
    product_class: str
    attributes: dict[str, Value]

    @property
    def name_key(self):
        return "".join(self.name_tokens)


@dataclass(frozen=True)
class Spec:
    key: str
    is_key: bool
    type: str | None
    method: str = ""  # NUMERIC | TEXT | EXACT, filled in stage 4.

    @property
    def weight(self):
        return KEY_WEIGHT if self.is_key else AUXILIARY_WEIGHT


@dataclass(frozen=True)
class Comparison:
    spec: Spec | None  # None for the product name.
    field: str
    status: str
    query: Value | None
    candidate: Value | None
    similarity: float = 0.0


@dataclass(frozen=True)
class Judgement:
    verdict: str | None
    score: float
    matched: list[str]
    near: list[str]
    conflicts: list[str]
    missing: list[str]
    key_total: int


# [1] Structure: validate the dict into the shared NormalizedProduct shape.
def structure(product):
    return NormalizedProduct.model_validate(product)


# [2] Normalize: Unicode/case-insensitive names and text, canonical units for numbers.
def tokens(text):
    return tuple(re.findall(r"[^\W\d_]+|\d+", unicodedata.normalize("NFKC", text or "").casefold()))


def normalize(product, properties, ontology, *, product_id=None):
    attributes = {}
    for key, attr in product.attributes.items():
        value, unit = attr.value, attr.unit
        if value is None:
            continue
        prop = properties.get(key, (None, False))[0]
        if prop is not None and prop.canonical_unit and unit != prop.canonical_unit:
            try:
                value, unit = ontology.normalize_unit(prop, value, unit)
            except ValueError:
                pass  # Left as is; stage 6 reports it as not comparable instead of guessing.
        compare = "".join(tokens(value)) if isinstance(value, str) else value
        attributes[key] = Value(compare, value, unit)
    return Profile(product_id, product.product_name, tokens(product.product_name), product.product_class, attributes)


# [3] Key specs: ontology required properties identify a product; optional ones only support.
def mapping_properties(mapping):
    if mapping is None:
        return {}
    mapping = OntologyMapping.model_validate(mapping)
    return {**{k: (p, False) for k, p in mapping.optional_properties.items()},
            **{k: (p, True) for k, p in mapping.required_properties.items()}}


def key_specs(properties, query):
    if not properties:  # No mapping: every known query attribute is treated as identifying.
        return [Spec(key, True, None) for key in sorted(query.attributes)]
    specs = [Spec(key, is_key, prop.type) for key, (prop, is_key) in properties.items()]
    return sorted(specs, key=lambda s: (not s.is_key, s.key))


# [4] Comparison method per spec type.
def classify(specs, query):
    def method(spec):
        kind = spec.type
        if kind is None and spec.key in query.attributes:
            sample = query.attributes[spec.key].display
            kind = "boolean" if isinstance(sample, bool) else "number" if isinstance(sample, (int, float)) else "string"
        return {"number": "NUMERIC", "integer": "NUMERIC", "string": "TEXT"}.get(kind, "EXACT")
    return [Spec(s.key, s.is_key, s.type, method(s)) for s in specs]


# [6] Detailed comparison.
def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def compare_value(spec, query, candidate):
    q, c = query.attributes.get(spec.key), candidate.attributes.get(spec.key)
    if q is None or c is None:
        return Comparison(spec, spec.key, "MISSING", q, c)
    if spec.method == "NUMERIC" and is_number(q.compare) and is_number(c.compare):
        if q.unit != c.unit:
            status = "MISSING"  # Units that could not be normalized are not comparable.
        elif isclose(q.compare, c.compare, rel_tol=1e-9, abs_tol=1e-9):
            status = "MATCH"
        elif abs(q.compare - c.compare) <= NEAR_TOLERANCE * max(abs(q.compare), abs(c.compare)):
            status = "NEAR"
        else:
            status = "CONFLICT"
    elif spec.method == "TEXT" and isinstance(q.compare, str) and isinstance(c.compare, str):
        if q.compare == c.compare:
            status = "MATCH"
        elif q.compare and c.compare and (q.compare in c.compare or c.compare in q.compare):
            status = "NEAR"  # "ABC Motors" vs "ABC Motors Co".
        else:
            status = "CONFLICT"
    else:
        status = "MATCH" if q.compare == c.compare and q.unit == c.unit else "CONFLICT"
    return Comparison(spec, spec.key, status, q, c)


def compare_names(query, candidate):
    q, c = Value(query.name_key, query.name, None), Value(candidate.name_key, candidate.name, None)
    if not query.name_key or not candidate.name_key:
        return Comparison(None, "product_name", "MISSING", q, c)
    if query.name_key == candidate.name_key:
        return Comparison(None, "product_name", "MATCH", q, c, 1.0)
    ratio = SequenceMatcher(None, query.name_key, candidate.name_key).ratio()
    numbers = [[t for t in p.name_tokens if t.isdigit()] for p in (query, candidate)]
    series = [p.name_tokens[0] for p in (query, candidate) if not p.name_tokens[0].isdigit()]
    if numbers[0] != numbers[1] or (len(series) == 2 and series[0] != series[1]):
        return Comparison(None, "product_name", "CONFLICT", q, c, min(ratio, DIFFERENT_MODEL_NAME_CAP))
    return Comparison(None, "product_name", "NEAR", q, c, ratio)  # Same series and number, e.g. DM-500/DM-500A.


# [7] Verdict. Missing key specs count against the score so sparse records cannot look certain.
def judge(name, comparisons):
    weighted = [c for c in comparisons if c.spec.is_key or c.status != "MISSING"]
    total = sum(c.spec.weight for c in weighted)
    spec_score = sum(c.spec.weight * STATUS_SCORE[c.status] for c in weighted) / total if total else 0.0
    score = round(min(1.0, SPEC_WEIGHT * spec_score + NAME_WEIGHT * name.similarity), 4)
    key = [c for c in comparisons if c.spec.is_key]
    by_status = {s: [c.field for c in key if c.status == s] for s in STATUS_SCORE}
    key_conflict = bool(by_status["CONFLICT"])
    coverage = (len(key) - len(by_status["MISSING"])) / len(key) if key else 0.0
    name_exact = name.status == "MATCH"
    if not key_conflict and ((score >= LIKELY_THRESHOLD and coverage == 1) or (name_exact and coverage >= 0.5)):
        verdict = "LIKELY_DUPLICATE"
    elif (not key_conflict and score >= CANDIDATE_THRESHOLD) or name_exact:
        verdict = "POSSIBLE_DUPLICATE"  # The same model name with conflicting specs still needs a human look.
    else:
        verdict = None
    return Judgement(verdict, score, by_status["MATCH"], by_status["NEAR"], by_status["CONFLICT"],
                     by_status["MISSING"], len(key))


# [8] Evidence: a readable reason plus field-level evidence for the reviewer.
def explain(candidate, name, comparisons, judgement):
    name_text = {"MATCH": "제품명 동일", "NEAR": f"제품명 유사({name.similarity:.0%})",
                 "CONFLICT": "제품명의 시리즈/모델번호 상이", "MISSING": "제품명 비교 불가"}[name.status]
    parts = [VERDICT_LABELS[judgement.verdict], name_text,
             f"핵심 사양 {len(judgement.matched)}/{judgement.key_total} 일치"]
    for label, fields in [("근사", judgement.near), ("충돌", judgement.conflicts), ("비교 불가", judgement.missing)]:
        if fields:
            parts.append(f"{label}: {', '.join(fields)}")
    evidence = [name] + [c for c in comparisons if c.query or c.candidate]
    return DuplicateCandidate(
        product_id=candidate.product_id, product_name=candidate.name or "(unnamed)", score=judgement.score,
        reason="; ".join(parts), verdict=judgement.verdict,
        evidence=[{"field": c.field, "status": c.status,
                   "query_value": c.query.display if c.query else None,
                   "candidate_value": c.candidate.display if c.candidate else None,
                   "unit": (c.query or c.candidate).unit} for c in evidence],
    ).model_dump(mode="json")


class DuplicateService:
    def __init__(self, repository, ontology=None):
        self.repository = repository
        self.ontology = ontology or OntologyService()

    # [5] Candidate retrieval: every stored product of the same class, not only the latest page.
    def retrieve(self, product_class):
        return self.repository.list(product_class=product_class, limit=None)

    def find(self, product, mapping=None, *, top_k=3):
        properties = mapping_properties(mapping)
        query = normalize(structure(product), properties, self.ontology)
        specs = classify(key_specs(properties, query), query)
        results = []
        for record in self.retrieve(query.product_class):
            candidate = normalize(structure(record["product"]), properties, self.ontology,
                                  product_id=record["product_id"])
            name = compare_names(query, candidate)
            comparisons = [compare_value(spec, query, candidate) for spec in specs]
            judgement = judge(name, comparisons)
            if judgement.verdict:
                results.append(explain(candidate, name, comparisons, judgement))
        ranked = sorted(results, key=lambda c: (-c["score"], c["product_id"]))[:top_k]
        return self.verify(ranked, query.product_class, top_k=top_k)

    # [9] Verification: fail loudly instead of passing fabricated or inconsistent candidates on.
    def verify(self, candidates, product_class, *, top_k):
        problems = []
        candidates = [DuplicateCandidate.model_validate(c).model_dump(mode="json") for c in candidates]
        if len(candidates) > top_k:
            problems.append(f"{len(candidates)} candidates exceed top_k={top_k}")
        ids = [c["product_id"] for c in candidates]
        if len(set(ids)) != len(ids):
            problems.append("candidate product_id values are not unique")
        if candidates != sorted(candidates, key=lambda c: (-c["score"], c["product_id"])):
            problems.append("candidates are not ordered by score desc, product_id asc")
        for candidate in candidates:
            record = self.repository.get(candidate["product_id"])
            if record is None:
                problems.append(f"{candidate['product_id']} does not exist in the product database")
            elif record["product"]["product_class"] != product_class:
                problems.append(f"{candidate['product_id']} belongs to another product class")
            if candidate["verdict"] is None:
                problems.append(f"{candidate['product_id']} has no verdict")
        if problems:
            raise ValueError("Duplicate result verification failed: " + "; ".join(problems))
        return candidates
