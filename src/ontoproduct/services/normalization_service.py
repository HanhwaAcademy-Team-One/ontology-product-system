from copy import deepcopy
from ontoproduct.schemas.product import NormalizedProduct, ProductAttribute


def normalize_attributes(attributes, properties, ontology):
    result = deepcopy(attributes)
    for key, attr in result.items():
        if key not in properties or attr.get("value") is None:
            continue
        try:
            attr["value"], attr["unit"] = ontology.normalize_unit(
                properties[key], attr["value"], attr.get("unit")
            )
        except ValueError:
            # Keep invalid evidence for deterministic validation and human repair.
            pass
    return result


def merge_extraction_retry(state, incoming):
    existing = state.get("extracted_product")
    feedback = state.get("review_result", {})
    if not existing or feedback.get("decision") != "RE_EXTRACT":
        return deepcopy(incoming)
    merged = deepcopy(existing)
    locked = set(state.get("locked_fields", []))
    for field in feedback.get("retry_fields", []):
        key = field.removeprefix("attributes.")
        if f"attributes.{key}" not in locked and key in incoming.get("attributes", {}):
            merged["attributes"][key] = deepcopy(incoming["attributes"][key])
    return merged


def apply_overrides(state, ontology):
    product = deepcopy(state["base_normalized_product"])
    properties = ontology.resolve_properties(product["product_class"])
    overrides = {
        **deepcopy(state.get("orphaned_overrides", {})),
        **deepcopy(state.get("manual_overrides", {})),
    }
    active, orphaned = {}, {}
    for path, value in overrides.items():
        if path == "product_class":
            active[path] = value  # Applied by ontology mapping.
        elif path == "product_name":
            product["product_name"] = value
            active[path] = value
        elif (
            path.startswith("attributes.")
            and path.removeprefix("attributes.") in properties
        ):
            attr = ProductAttribute.model_validate(value).model_dump(mode="json")
            attr.update(provenance="HUMAN", confidence=None)
            key = path.removeprefix("attributes.")
            product["attributes"][key] = normalize_attributes(
                {key: attr}, properties, ontology
            )[key]
            active[path] = attr
        else:
            orphaned[path] = value
    product = NormalizedProduct.model_validate(product).model_dump(mode="json")
    return {
        "normalized_product": product,
        "manual_overrides": active,
        "orphaned_overrides": orphaned,
    }


def human_edits(state, edits, changed_class, ontology):
    active = deepcopy(state.get("manual_overrides", {}))
    locked = set(state.get("locked_fields", []))
    cls = changed_class or state["normalized_product"]["product_class"]
    properties = ontology.resolve_properties(cls)
    for path, value in edits.items():
        if path == "product_name" and isinstance(value, str) and value.strip():
            active[path] = value
        elif (
            path.startswith("attributes.")
            and path.removeprefix("attributes.") in properties
        ):
            attr = ProductAttribute.model_validate(value).model_dump(mode="json")
            attr.update(provenance="HUMAN", confidence=None)
            active[path] = attr
        else:
            raise ValueError(f"Invalid human edit path or value: {path}")
        locked.add(path)
    if changed_class:
        ontology.get_class(changed_class)
        active["product_class"] = changed_class
        locked.add("product_class")
    return {"manual_overrides": active, "locked_fields": sorted(locked)}
