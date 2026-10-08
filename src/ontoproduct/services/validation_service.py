from urllib.parse import unquote

from ontoproduct.schemas.ontology import OntologyMapping
from ontoproduct.schemas.product import NormalizedProduct
from ontoproduct.schemas.validation import ValidationIssue, ValidationResult
from ontoproduct.services.evidence_service import is_conflict


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
                detail = (
                    "has conflicting document values"
                    if attr is not None and is_conflict(attr)
                    else "is missing"
                )
                issue(field, "MISSING_REQUIRED", f"Required property {key} {detail}")
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
    for key in sorted(product.attributes.keys() - props.keys()):
        issue(
            f"attributes.{key}",
            "UNKNOWN_PROPERTY",
            "Property is outside this ontology class",
            "warning",
        )
    return ValidationResult(
        valid=not any(i.severity == "error" for i in issues), issues=issues
    ).model_dump(mode="json")


def _out_of_class_comparisons(product, ontology):
    """Apply comparison rules of other classes when both properties are present.

    SHACL only checks comparisons of the product's own class, so choosing a parent
    class (e.g. MechanicalPart for a Bearing) must not hide inner >= outer diameter.
    """
    product = NormalizedProduct.model_validate(product)
    classes = {product.product_class, *ontology.get_ancestors(product.product_class)}
    issues = []
    for rule in ontology.semantic_model.model.comparisons:
        if rule.product_class in classes:
            continue  # Reported through SHACL in validate_registration_product.
        properties = ontology.resolve_properties(rule.product_class)
        values = []
        for key in (rule.left, rule.right):
            attr = product.attributes.get(key)
            if attr is None or attr.value is None:
                break
            try:
                values.append(
                    ontology.normalize_unit(properties[key], attr.value, attr.unit)[0]
                )
            except ValueError:
                break  # Uninterpretable values cannot prove a violation.
        if len(values) == 2 and values[0] >= values[1]:
            issues.append(
                ValidationIssue(
                    field=f"attributes.{rule.left}",
                    code="RANGE",
                    message=f"{rule.left} must be less than {rule.right}",
                ).model_dump(mode="json")
            )
    return issues


def validate_registration_product(product, mapping, ontology):
    """Combine operational rules and aligned SHACL without changing the JSON contract."""
    result = validate_product(product, mapping)
    if ontology.semantic_model is None:
        return result
    result["issues"] += _out_of_class_comparisons(product, ontology)
    result["valid"] = not any(i["severity"] == "error" for i in result["issues"])
    semantic = ontology.validate_semantics(product)
    if semantic["valid"]:
        return result
    product = NormalizedProduct.model_validate(product)
    model = ontology.semantic_model.model
    paths = {model.namespace + p.predicate: k for k, p in model.properties.items()}
    extra = []
    comparisons = []
    classes = {product.product_class, *ontology.get_ancestors(product.product_class)}
    for rule in model.comparisons:
        left, right = (
            product.attributes.get(rule.left),
            product.attributes.get(rule.right),
        )
        fields = {f"attributes.{rule.left}", f"attributes.{rule.right}"}
        if rule.product_class not in classes or any(
            i["severity"] == "error" and i["field"] in fields for i in result["issues"]
        ):
            continue
        if (
            left
            and right
            and rule.operator == "less_than"
            and left.value >= right.value
        ):
            comparisons.append(
                ValidationIssue(
                    field=f"attributes.{rule.left}",
                    code="RANGE",
                    message=f"{rule.left} must be less than {rule.right}",
                ).model_dump(mode="json")
            )
    mapped = []
    for issue in semantic["issues"]:
        key = paths.get(issue["path"])
        if key is None:
            candidate = unquote(issue.get("focus_node", "").partition(":value:")[2])
            if candidate in model.properties:
                key = candidate
        field = f"attributes.{key}" if key else "product_class"
        component = issue["constraint"].rsplit("#", 1)[-1]
        code = {
            "MinInclusiveConstraintComponent": "RANGE",
            "MaxInclusiveConstraintComponent": "RANGE",
            "DatatypeConstraintComponent": "TYPE",
            "OrConstraintComponent": "TYPE",
            "PatternConstraintComponent": "TYPE",
        }.get(component, "CLASS")
        if (
            component == "HasValueConstraintComponent"
            and issue["path"] == model.namespace + model.measurement.has_unit.name
        ):
            code = "UNIT"
        mapped.append((issue, field, component, code))
    for issue, field, component, code in mapped:
        existing = {
            i["code"]
            for i in result["issues"]
            if i["field"] == field and i["severity"] == "error"
        }
        if (
            component == "MinCountConstraintComponent"
            and "MISSING_REQUIRED" in existing
        ):
            continue
        if component == "NodeConstraintComponent" and any(
            f == field and c in existing & {"TYPE", "UNIT", "RANGE"}
            for _, f, _, c in mapped
        ):
            continue
        if code != "CLASS" and code in existing:
            continue
        if (
            component == "SPARQLConstraintComponent"
            and not issue["path"]
            and comparisons
        ):
            extra.extend(comparisons)
            continue
        extra.append(
            ValidationIssue(
                field=field,
                code=code,
                message=f"SHACL constraint {component} failed for {field}",
            ).model_dump(mode="json")
        )
    if not extra and not any(i["severity"] == "error" for i in result["issues"]):
        extra.append(
            ValidationIssue(
                field="product_class", code="CLASS", message="SHACL validation failed"
            ).model_dump(mode="json")
        )
    seen = {(i["field"], i["code"], i["message"]) for i in result["issues"]}
    for issue in sorted(extra, key=lambda i: (i["field"], i["code"], i["message"])):
        signature = (issue["field"], issue["code"], issue["message"])
        if signature not in seen:
            result["issues"].append(issue)
            seen.add(signature)
    result["valid"] = not any(i["severity"] == "error" for i in result["issues"])
    return result
