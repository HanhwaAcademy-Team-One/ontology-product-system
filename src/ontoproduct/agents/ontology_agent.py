from pydantic import Field

from ontoproduct.agents.base import BaseAgent
from ontoproduct.agents.registry import CONTRACTS
from ontoproduct.prompts.ontology import INSTRUCTIONS, VERSION
from ontoproduct.schemas.common import DomainModel
from ontoproduct.schemas.ontology import OntologyMapping
from ontoproduct.schemas.product import ExtractedProduct, NormalizedProduct
from ontoproduct.services.agent_errors import OntologyClassificationError
from ontoproduct.services.attribute_merge import enforce_conflicts, merge_attributes
from ontoproduct.services.evidence_service import is_conflict
from ontoproduct.services.external_mapping_service import ExternalMappings
from ontoproduct.services.llm_protocol import validated_response
from ontoproduct.services.mapping_service import PropertyAliases
from ontoproduct.services.normalization_service import normalize_attributes


class ClassSelection(DomainModel):
    product_class: str | None
    confidence: float = Field(ge=0, le=1, strict=True)


class OntologyAgent(BaseAgent):
    name = "ontology"
    provider = "ontology-rules"
    version = VERSION
    is_mock = False

    def __init__(self, ontology, llm_service=None, *, aliases=None, external_mappings=None):
        required, optional, writes = CONTRACTS[self.name]
        self.required_reads, self.optional_reads, self.writes = set(required), set(optional), dict(writes)
        self.ontology, self.llm_service = ontology, llm_service
        self.aliases = aliases if aliases is not None else PropertyAliases()
        self.external_mappings = (external_mappings if external_mappings is not None
                                  else ontology.semantic_model.references if ontology.semantic_model is not None else ExternalMappings())
        if llm_service is not None:
            self.provider = "ontology-structured-llm-adapter"

    def _rule_class(self, candidate, attributes):
        present = {k for k, a in attributes.items() if a.value is not None or is_conflict(a)}
        if self.ontology.semantic_model is not None:
            return self.ontology.semantic_model.classify(candidate, present)
        bearing = {"inner_diameter", "outer_diameter"} <= present
        motor_fields = {"rated_voltage", "rated_power", "rated_speed"} & present
        motor = "manufacturer" in present and len(motor_fields) >= 2
        if bearing and not motor_fields:
            return "Bearing"
        if motor and not ({"inner_diameter", "outer_diameter"} & present):
            return "BLDCMotor" if candidate == "BLDCMotor" else "Motor"
        raise OntologyClassificationError("No unambiguous rule classification; supply a supported manual class or LLM adapter")

    def run(self, state):
        extracted = ExtractedProduct.model_validate(state["extracted_product"])
        attrs = merge_attributes([extracted.attributes], self.aliases, self.ontology.unit_service)
        overrides = state.get("manual_overrides", {})
        if "product_class" in state.get("locked_fields", []) and "product_class" not in overrides:
            raise ValueError("Locked product_class requires manual_overrides.product_class")
        if "product_class" in overrides:
            cls, confidence = overrides["product_class"], 1.0
            if not isinstance(cls, str):
                raise ValueError("Manual product_class must be a string")
            self.ontology.get_class(cls)
        elif self.llm_service is not None:
            allowed = [c for c in self.ontology.definition.classes if c != "Product"]
            selection = validated_response(self.llm_service, task="ontology", payload={
                "instructions": INSTRUCTIONS, "prompt_version": VERSION,
                "extracted_product": extracted.model_dump(mode="json"),
                "allowed_classes": allowed,
                "class_definitions": {c: self.ontology.get_class(c).model_dump(mode="json") for c in allowed},
                "external_references": self.external_mappings.verified(),
                "semantic_model": (self.ontology.semantic_model.as_context(allowed)
                                   if self.ontology.semantic_model is not None else None),
            }, schema=ClassSelection)
            cls, confidence = selection.product_class, selection.confidence
            if cls not in allowed:
                raise OntologyClassificationError(f"Model did not select a supported class: {cls!r}")
        else:
            cls, confidence = self._rule_class(extracted.candidate_class, attrs), 1.0
            if cls not in self.ontology.definition.classes:
                raise OntologyClassificationError(f"Rule class is absent from supplied ontology: {cls}")
        required = self.ontology.resolve_required_properties(cls)
        optional = self.ontology.resolve_optional_properties(cls)
        properties = {**required, **optional}
        # Inspect every conflict against FINAL definitions before normalization.
        attrs = merge_attributes([extracted.attributes], self.aliases, self.ontology.unit_service, properties)
        enforce_conflicts(attrs, required, optional, overrides=overrides, units=self.ontology.unit_service)
        normalized = normalize_attributes({k: a.model_dump(mode="json") for k, a in attrs.items()}, properties, self.ontology)
        mapping = OntologyMapping(product_class=cls, confidence=confidence,
                                  required_properties=required, optional_properties=optional)
        product = NormalizedProduct(product_name=extracted.product_name, product_class=cls, attributes=normalized)
        return {"ontology_mapping": mapping.model_dump(mode="json"),
                "base_normalized_product": product.model_dump(mode="json")}
