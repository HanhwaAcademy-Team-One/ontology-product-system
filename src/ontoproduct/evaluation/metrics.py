"""Metrics use annotated truth and recorded outputs; undefined ratios are None."""
from math import isclose


def ratio(correct, total):
    return {"value": correct / total if total else None, "correct": correct, "total": total}


def present(attributes):
    return {key for key, attr in attributes.items() if attr.get("value") is not None}


def equal_value(actual, expected):
    if type(actual) in (int, float) and type(expected) in (int, float):
        return isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)
    return type(actual) is type(expected) and actual == expected


def evaluate_extraction(samples):
    tp = fp = fn = values = value_total = units = unit_total = 0
    for sample in samples:
        truth = sample["ground_truth"]["product"]["attributes"]
        extracted = sample["outputs"]["extracted_product"]["attributes"]
        normalized = sample["outputs"]["normalized_product"]["attributes"]
        expected, predicted = present(truth), present(extracted)
        tp += len(expected & predicted)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
        for key in expected:
            value_total += 1
            attr = normalized.get(key, {})
            values += equal_value(attr.get("value"), truth[key]["value"])
            if truth[key].get("unit") is not None:
                unit_total += 1
                units += attr.get("value") is not None and attr.get("unit") == truth[key]["unit"]
    precision, recall = ratio(tp, tp + fp), ratio(tp, tp + fn)
    return {
        "Attribute Detection Precision": precision,
        "Attribute Detection Recall": recall,
        "Attribute Detection F1": ratio(2 * tp, 2 * tp + fp + fn),
        "Attribute Value Accuracy": ratio(values, value_total),
        "Unit Normalization Accuracy": ratio(units, unit_total),
        "detection_counts": {"tp": tp, "fp": fp, "fn": fn},
    }


def evaluate_ontology(samples, ontology):
    classes = required_correct = required_total = 0
    for sample in samples:
        expected_class = sample["ground_truth"]["product"]["product_class"]
        outputs = sample["outputs"]
        classes += outputs["ontology_mapping"]["product_class"] == expected_class
        attrs = outputs["normalized_product"]["attributes"]
        reported = {issue["field"].removeprefix("attributes.") for issue in
                    outputs["validation_result"]["issues"] if issue["code"] == "MISSING_REQUIRED"}
        for key in ontology.resolve_required_properties(expected_class):
            missing = key not in attrs or attrs[key].get("value") is None
            required_correct += missing == (key in reported)
            required_total += 1
    return {"Ontology Classification Accuracy": ratio(classes, len(samples)),
            "Required Field Detection Accuracy": ratio(required_correct, required_total)}


def evaluate_duplicate(samples, *, k=3):
    if type(k) is not int or k < 1:
        raise ValueError("K must be a positive integer")
    hits = relevant_total = retrieved_total = negative_correct = negative_total = 0
    per_query = []
    for sample in samples:
        relevant = set(sample["ground_truth"]["relevant_duplicates"])
        ranking = sample["outputs"]["duplicate_candidates"][:k]
        names = [candidate["product_name"] for candidate in ranking]
        matched = len(set(names) & relevant)
        hits += matched
        retrieved_total += len(names)
        relevant_total += len(relevant)
        if not relevant:
            negative_total += 1
            negative_correct += not names
        per_query.append({"case_id": sample["ground_truth"]["case_id"], "retrieved": names,
                          "relevant": sorted(relevant), "hits": matched})
    # Precision@K uses K slots per query, including empty slots; recall is micro over relevant labels.
    return {f"Duplicate Precision@{k}": ratio(hits, k * len(samples)),
            f"Duplicate Recall@{k}": ratio(hits, relevant_total),
            # Share of returned candidates that are real duplicates; exposes false positives Precision@K hides.
            "Duplicate Candidate Precision": ratio(hits, retrieved_total),
            "Negative Query Accuracy": ratio(negative_correct, negative_total),
            "retrieved_count": retrieved_total, "queries": per_query}
