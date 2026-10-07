from ontoproduct.schemas.ontology import OntologyMapping
from ontoproduct.schemas.product import NormalizedProduct
from ontoproduct.schemas.validation import ValidationIssue, ValidationResult


def validate_product(product, mapping):
    product = NormalizedProduct.model_validate(product)
    mapping = OntologyMapping.model_validate(mapping)
    issues = []

    def issue(field, code, message, severity="error"):
        issues.append(
            ValidationIssue(field=field, code=code, message=message, severity=severity)
        )

    if product.product_class != mapping.product_class:
        issue("product_class", "CLASS", "Product class differs from ontology mapping")
    props = {**mapping.required_properties, **mapping.optional_properties}
    for key, prop in props.items():
        field = f"attributes.{key}"
        attr = product.attributes.get(key)
        if attr is None or attr.value is None:
            if key in mapping.required_properties:
                issue(field, "MISSING_REQUIRED", f"Required property {key} is missing")
            else:
                issue(
                    field,
                    "MISSING_OPTIONAL",
                    f"Optional property {key} is missing",
                    "warning",
                )
            continue
        value = attr.value
        valid_type = {
            "string": isinstance(value, str) and bool(value.strip()),
            "number": type(value) in (int, float),
            "integer": type(value) is int,
            "boolean": type(value) is bool,
        }[prop.type]
        if not valid_type:
            issue(field, "TYPE", f"Expected {prop.type}")
            continue
        if attr.unit != prop.canonical_unit:
            issue(field, "UNIT", f"Expected canonical unit {prop.canonical_unit!r}")
        if prop.type in ("number", "integer"):
            if prop.minimum is not None and value < prop.minimum:
                issue(field, "RANGE", f"Value is below {prop.minimum}")
            if prop.maximum is not None and value > prop.maximum:
                issue(field, "RANGE", f"Value exceeds {prop.maximum}")
    for key in product.attributes.keys() - props.keys():
        issue(
            f"attributes.{key}",
            "UNKNOWN_PROPERTY",
            "Property is outside this ontology class",
            "warning",
        )
    return ValidationResult(
        valid=not any(i.severity == "error" for i in issues), issues=issues
    ).model_dump(mode="json")
