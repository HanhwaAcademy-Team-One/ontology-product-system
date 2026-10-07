"""Source checks and lossless multi-source evidence inside the existing string field."""

import json
import re
from math import isclose, isfinite

from pydantic import TypeAdapter

from ontoproduct.schemas.product import ParsedDocument, ProductAttribute

MERGED_PREFIX = "@@ONTOPRODUCT_EVIDENCE_V1@@\n"
CONFLICT_PREFIX = "@@ONTOPRODUCT_CONFLICT_V1@@\n"
EXCEL_PREFIX = re.compile(r"^\[Sheet: [^\]\r\n]+, Row: \d+\]")
COMMAND_PATTERN = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions|rules)|"
    r"(?:기존|이전)\s*지시[^\r\n]*무시|"
    r"(?:전압|voltage)[^\r\n]*999[^\r\n]*(?:답하|출력하|answer)",
    re.IGNORECASE,
)
NUMBER_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_.])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\d.])"
)


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def validate_quoted_value(attr: ProductAttribute):
    """A lexical anchor, not a claim of complete semantic validation."""
    if attr.value is None:
        return
    quote = EXCEL_PREFIX.sub("", attr.evidence or "")
    quote = re.sub(r"\b[A-Za-z]{1,3}\d+(?==)", "", quote)
    value = attr.value
    if type(value) in (int, float):
        supported = False
        for match in NUMBER_PATTERN.finditer(quote):
            number = float(match.group().replace(",", ""))
            try:
                supported |= isfinite(number) and isclose(
                    value, number, rel_tol=1e-9, abs_tol=0.0
                )
            except OverflowError:
                supported |= str(value) == match.group()
    elif isinstance(value, str):
        supported = bool(value.strip()) and normalize_whitespace(
            value
        ) in normalize_whitespace(quote)
    else:
        words = ("true", "yes", "예") if value else ("false", "no", "아니오")
        supported = any(
            re.search(r"(?<!\w)" + word + r"(?!\w)", quote, re.IGNORECASE)
            for word in words
        )
    if not supported:
        raise ValueError("Extracted value is not supported by its quoted evidence")
    if attr.unit is not None and (
        not attr.unit.strip()
        or not re.search(
            r"(?<![A-Za-z])" + re.escape(attr.unit) + r"(?![A-Za-z])", quote
        )
    ):
        raise ValueError("Extracted unit is not present in its quoted evidence")


def is_conflict(attr: ProductAttribute) -> bool:
    return bool(attr.evidence and attr.evidence.startswith(CONFLICT_PREFIX))


def evidence_candidates(attr: ProductAttribute) -> list[ProductAttribute]:
    prefix = next(
        (
            p
            for p in (CONFLICT_PREFIX, MERGED_PREFIX)
            if (attr.evidence or "").startswith(p)
        ),
        None,
    )
    if prefix is None:
        return [attr.model_copy(deep=True)]
    candidates = TypeAdapter(list[ProductAttribute]).validate_json(
        attr.evidence[len(prefix) :]
    )
    if len(candidates) < 2 or any(
        (c.evidence or "").startswith((CONFLICT_PREFIX, MERGED_PREFIX))
        for c in candidates
    ):
        raise ValueError("Invalid or nested aggregate evidence")
    return candidates


def pack_evidence(
    candidates: list[ProductAttribute], *, conflict=False
) -> ProductAttribute:
    flattened = [
        item for candidate in candidates for item in evidence_candidates(candidate)
    ]
    unique = {
        json.dumps(
            a.model_dump(mode="json"),
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        ): a
        for a in flattened
    }
    items = list(unique.values())
    if len(items) == 1 and not conflict:
        return items[0].model_copy(deep=True)
    first = items[0].model_copy(deep=True)
    scores = [a.confidence for a in items]
    first.confidence = min(scores) if all(s is not None for s in scores) else None
    if len({(a.source_file, a.page) for a in items}) > 1:
        first.source_file = first.page = None
    prefix = CONFLICT_PREFIX if conflict else MERGED_PREFIX
    first.evidence = prefix + json.dumps(
        [a.model_dump(mode="json") for a in items], ensure_ascii=False, allow_nan=False
    )
    if conflict:
        first.value = first.unit = first.confidence = None
    return first


def validate_evidence(
    attr: ProductAttribute, documents: list[ParsedDocument]
) -> ProductAttribute:
    result = attr.model_copy(deep=True)
    if (attr.evidence or "").startswith((CONFLICT_PREFIX, MERGED_PREFIX)):
        raise ValueError(
            "LLM must return raw evidence, not a reserved aggregate marker"
        )
    if not attr.evidence or not normalize_whitespace(attr.evidence):
        if attr.value is not None:
            raise ValueError("Non-null attribute requires source evidence")
        result.confidence = result.unit = None
        result.provenance = "AI"
        return result
    if attr.source_file is None:
        raise ValueError("Evidence requires an exact source_file")
    expression = re.compile(
        r"\s+".join(re.escape(part) for part in attr.evidence.split())
    )
    matches = []
    for doc in documents:
        if doc.source_file != attr.source_file or doc.page != attr.page:
            continue
        for match in expression.finditer(doc.text):
            begin = doc.text.rfind("\n", 0, match.start()) + 1
            end = doc.text.find("\n", match.end())
            line = doc.text[begin : end if end >= 0 else len(doc.text)]
            if COMMAND_PATTERN.search(line):
                raise ValueError(
                    "Document instruction cannot serve as specification evidence"
                )
            # Recover the actual row, including its location, from a cell-only quote.
            quote = line.rstrip("\r") if EXCEL_PREFIX.match(line) else match.group()
            matches.append(quote)
    if not matches:
        raise ValueError(
            f"Evidence not found in {attr.source_file!r}, page {attr.page!r}"
        )
    excel_matches = {m for m in matches if EXCEL_PREFIX.match(m)}
    if len(excel_matches) > 1:
        raise ValueError("Ambiguous Excel evidence; quote the row location")
    result.evidence = matches[0]
    validate_quoted_value(result)
    result.provenance = "AI"
    if result.value is None:
        result.confidence = result.unit = None
    return result
