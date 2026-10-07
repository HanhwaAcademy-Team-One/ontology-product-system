"""Honest canned LlmService: answers only from lines that exist in the supplied chunk."""

import re

LABELS = {
    "manufacturer": "manufacturer",
    "rated voltage": "rated_voltage",
    "voltage": "rated_voltage",
    "정격 전압": "rated_voltage",
    "rated power": "rated_power",
    "power": "rated_power",
    "rated speed": "rated_speed",
    "speed": "rated_speed",
}
PATTERNS = [
    re.compile(
        r"^\[Sheet: [^\]]+, Row: \d+\] A\d+=(?P<label>[^|]+?) \| B\d+=(?P<value>[^|]+?)"
        r"(?: \| C\d+=(?P<unit>.+))?$"
    ),
    re.compile(r"^(?P<label>[^|:\[]+?) \| (?P<value>[^|]+?) \|\s?(?P<unit>.*)$"),
    re.compile(
        r"^(?P<label>[^:|]+): (?P<value>\S+(?: \S+)*?)(?: (?P<unit>V|kW|W|rpm|g|kg))?$"
    ),
]
MOTOR_FIELDS = {"rated_voltage", "rated_power", "rated_speed"}


def number(text):
    try:
        value = float(text)
    except ValueError:
        return text
    return int(value) if value.is_integer() else value


class HonestLlm:
    def __init__(self):
        self.calls = []

    def generate_structured(self, *, task, payload, response_schema):
        self.calls.append(task)
        if task == "ontology":
            return response_schema.model_validate(self._classify(payload))
        return response_schema.model_validate(self._extract(payload["documents"][0]))

    @staticmethod
    def _classify(payload):
        product = payload["extracted_product"]
        candidate = product.get("candidate_class")
        if candidate in payload["allowed_classes"]:
            return {"product_class": candidate, "confidence": 0.9}
        if MOTOR_FIELDS <= set(product["attributes"]):
            return {"product_class": "BLDCMotor", "confidence": 0.8}
        return {"product_class": None, "confidence": 0.0}

    @staticmethod
    def _extract(chunk):
        name = cls = None
        attributes = {}
        for line in chunk["text"].splitlines():
            for pattern in PATTERNS:
                match = pattern.match(line.strip())
                if not match:
                    continue
                label = match["label"].strip().lower()
                value = match["value"].strip()
                unit = (match["unit"] or "").strip() or None
                if label == "product":
                    name = value
                elif label == "class":
                    cls = value
                elif label in LABELS and LABELS[label] not in attributes:
                    attributes[LABELS[label]] = {
                        "value": number(value),
                        "unit": unit,
                        "evidence": line.strip(),
                        "source_file": chunk["source_file"],
                        "page": chunk["page"],
                        "confidence": 0.9,
                        "provenance": "AI",
                    }
                break
        return {"product_name": name, "candidate_class": cls, "attributes": attributes}
