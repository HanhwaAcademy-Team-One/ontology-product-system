"""Canned transport responses; no production parser or model is replaced here."""

from copy import deepcopy
from pathlib import Path

from ontoproduct.schemas.product import ExtractedProduct

FIXTURES = Path(__file__).parent / "fixtures" / "extraction_ontology"


class RecordingTransport:
    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def generate_structured(self, *, task, payload, response_schema):
        self.calls.append({"task": task, "payload": deepcopy(payload), "response_schema": response_schema})
        result = self.handler(task, payload)
        return response_schema.model_validate(result) if isinstance(result, dict) else result


def document(name="motor.txt", *, source_file=None, page=None):
    return {"source_file": source_file or name, "page": page, "text": (FIXTURES / name).read_text(encoding="utf-8")}


def attribute(value, unit=None, *, evidence, source_file="motor.txt", page=None, confidence=0.9):
    return {"value": value, "unit": unit, "evidence": evidence,
            "source_file": source_file, "page": page, "confidence": confidence, "provenance": "AI"}


def motor_response(*, source_file="motor.txt", page=None):
    definitions = {
        "manufacturer": ("XYZ Motors", None, "Manufacturer: XYZ Motors"),
        "rated_voltage": (24, "V", "Rated Voltage: 24 V"),
        "rated_power": (0.6, "kW", "Rated Power: 0.6 kW"),
        "rated_speed": (3200, "rpm", "Rated Speed: 3200 rpm"),
        "weight": (750, "g", "Weight: 750 g"),
    }
    return {"product_name": "DM-600", "candidate_class": "BLDCMotor", "attributes": {
        key: attribute(v, u, evidence=e, source_file=source_file, page=page) for key, (v, u, e) in definitions.items()
    }}


def constant_transport(response):
    return RecordingTransport(lambda task, payload: deepcopy(response))
