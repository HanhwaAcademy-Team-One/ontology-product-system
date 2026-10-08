from copy import deepcopy
from ontoproduct.agents.base import BaseAgent
from ontoproduct.agents.registry import AgentRegistry, CONTRACTS
from ontoproduct.schemas.product import ExtractedProduct
from ontoproduct.schemas.review import ReviewResult
from ontoproduct.services.normalization_service import normalize_attributes
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.services.validation_service import validate_product


class MockAgent(BaseAgent):
    provider = "mock"
    version = "0.1.0"
    is_mock = True

    def __init__(self):
        reads, optional, writes = CONTRACTS[self.name]
        self.required_reads, self.optional_reads, self.writes = (
            set(reads),
            set(optional),
            dict(writes),
        )


class ParserMock(MockAgent):
    name = "parser"

    def run(self, state):
        return {
            "parsed_documents": [
                {
                    "source_file": d.get("name", "mock.txt"),
                    "text": d.get("text", "MOCK document"),
                    "page": 1,
                }
                for d in state["source_documents"]
            ]
        }


class ExtractionMock(MockAgent):
    name = "extraction"

    def __init__(self, *, attributes=None):
        super().__init__()
        self.attributes = (
            attributes
            if attributes is not None
            else {
                "manufacturer": {
                    "value": "ABC Motors",
                    "confidence": 0.95,
                    "provenance": "AI",
                },
                "rated_voltage": {
                    "value": 24,
                    "unit": "V",
                    "confidence": 0.95,
                    "provenance": "AI",
                },
                "rated_power": {
                    "value": 0.5,
                    "unit": "kW",
                    "confidence": 0.95,
                    "provenance": "AI",
                },
            }
        )

    def run(self, state):
        attrs = deepcopy(self.attributes)
        feedback = state.get("review_result", {})
        if feedback.get("decision") == "RE_EXTRACT":
            requested = {
                f.removeprefix("attributes.") for f in feedback.get("retry_fields", [])
            }
            locked = set(state.get("locked_fields", []))
            attrs = {
                k: v
                for k, v in attrs.items()
                if k in requested and f"attributes.{k}" not in locked
            }
        # This mock deliberately leaves rated_speed absent on both attempts.
        return {
            "extracted_product": ExtractedProduct(
                product_name="DM-500", candidate_class="BLDCMotor", attributes=attrs
            ).model_dump(mode="json")
        }


class OntologyMock(MockAgent):
    name = "ontology"

    def __init__(self, ontology):
        super().__init__()
        self.ontology = ontology

    def run(self, state):
        extracted = state["extracted_product"]
        cls = (
            state.get("manual_overrides", {}).get(
                "product_class", extracted.get("candidate_class")
            )
            or "Product"
        )
        self.ontology.get_class(cls)
        required = self.ontology.resolve_required_properties(cls)
        optional = self.ontology.resolve_optional_properties(cls)
        return {
            "ontology_mapping": {
                "product_class": cls,
                "confidence": 0.95,
                "required_properties": {
                    k: p.model_dump(mode="json") for k, p in required.items()
                },
                "optional_properties": {
                    k: p.model_dump(mode="json") for k, p in optional.items()
                },
            },
            "base_normalized_product": {
                "product_name": extracted.get("product_name"),
                "product_class": cls,
                "attributes": normalize_attributes(
                    extracted["attributes"], {**required, **optional}, self.ontology
                ),
            },
        }


class ValidationMock(MockAgent):
    name = "validation"

    def run(self, state):
        return {
            "validation_result": validate_product(
                state["normalized_product"], state["ontology_mapping"]
            )
        }


class DuplicateMock(MockAgent):
    name = "duplicate"

    def run(self, state):
        return {"duplicate_candidates": []}


class ReviewerMock(MockAgent):
    name = "reviewer"

    def run(self, state):
        locked = set(state.get("locked_fields", []))
        product = state["normalized_product"]
        retry = []
        for key in state["ontology_mapping"]["required_properties"]:
            path = f"attributes.{key}"
            attr = product["attributes"].get(key)
            if path in locked or (attr and attr.get("provenance") == "HUMAN"):
                continue
            if not attr or attr.get("value") is None:
                retry.append(key)
            elif attr.get("provenance") == "AI" and (
                attr.get("confidence") is None or attr["confidence"] < 0.70
            ):
                retry.append(key)
        if retry:
            decision, reason = (
                "RE_EXTRACT",
                "Required properties are missing or have low AI confidence.",
            )
        elif (
            state["ontology_mapping"]["confidence"] < 0.70
            and "product_class" not in locked
        ):
            decision, reason = (
                "REMAP_ONTOLOGY",
                "Ontology mapping confidence is below 0.70.",
            )
        elif not state["validation_result"]["valid"]:
            decision, reason = (
                "NEEDS_FIX",
                "Deterministic validation requires human repair.",
            )
        else:
            decision, reason = (
                "READY_FOR_HUMAN",
                "Required properties are valid; human approval is required.",
            )
        return {
            "review_result": ReviewResult(
                decision=decision,
                reason=reason,
                retry_fields=retry,
                can_register=decision == "READY_FOR_HUMAN",
            ).model_dump(mode="json")
        }


class RegistrationMock(MockAgent):
    name = "registration"

    def run(self, state):
        if state["human_review"].get("action") != "APPROVE":
            raise ValueError("Registration requires human approval")
        return {"final_product": deepcopy(state["normalized_product"])}


def mock_registry(ontology=None):
    ontology = ontology or OntologyService()
    registry = AgentRegistry()
    for agent in [
        ParserMock(),
        ExtractionMock(),
        OntologyMock(ontology),
        ValidationMock(),
        DuplicateMock(),
        ReviewerMock(),
        RegistrationMock(),
    ]:
        registry.register(agent)
    return registry
