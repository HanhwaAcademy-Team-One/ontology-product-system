"""Shared alias merge and conflict checks, independent of LLM transport."""

from ontoproduct.schemas.product import ProductAttribute
from ontoproduct.services.agent_errors import DocumentConflictError
from ontoproduct.services.evidence_service import (
    evidence_candidates,
    is_conflict,
    pack_evidence,
)


def merge_attributes(batches, aliases, units, properties=None):
    grouped = {}
    for attributes in batches:
        for key, value in attributes.items():
            attr = (
                ProductAttribute.model_validate(value)
                if isinstance(value, dict)
                else value.model_copy(deep=True)
            )
            grouped.setdefault(aliases.resolve(key), []).extend(
                evidence_candidates(attr)
            )
    merged = {}
    for key, candidates in grouped.items():
        present = [a for a in candidates if a.value is not None]
        if not present:
            attr = candidates[0].model_copy(deep=True)
            attr.confidence = attr.unit = None
            merged[key] = attr
            continue
        prop = (properties or {}).get(key)
        conflict = any(not units.equal(key, present[0], a, prop) for a in present[1:])
        merged[key] = pack_evidence(present, conflict=conflict)
    return merged


def valid_human_resolution(key, overrides, properties, units):
    if key not in properties or f"attributes.{key}" not in overrides:
        return False
    attr = ProductAttribute.model_validate(overrides[f"attributes.{key}"])
    prop = properties[key]
    value = attr.value
    valid = {
        "string": isinstance(value, str) and bool(value.strip()),
        "number": type(value) in (int, float),
        "integer": type(value) is int,
        "boolean": type(value) is bool,
    }[prop.type]
    if not valid:
        return False
    try:
        value, _ = units.normalize(prop, value, attr.unit, property_name=key)
    except ValueError:
        return False
    if prop.type == "integer" and type(value) is not int:
        return False
    if prop.type in ("number", "integer"):
        if prop.minimum is not None and value < prop.minimum:
            return False
        if prop.maximum is not None and value > prop.maximum:
            return False
    return True


def enforce_conflicts(attributes, required, optional, *, overrides=None, units=None):
    properties = {**required, **optional}
    for key, attr in attributes.items():
        if not is_conflict(attr):
            continue
        if overrides is not None and valid_human_resolution(
            key, overrides, properties, units
        ):
            continue
        if key not in required:
            raise DocumentConflictError(
                f"Unresolved CONFLICT for optional or outside-class property {key}: {attr.evidence}"
            )
