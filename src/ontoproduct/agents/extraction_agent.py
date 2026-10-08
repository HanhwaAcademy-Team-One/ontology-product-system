from pydantic import Field, TypeAdapter

from ontoproduct.agents.base import BaseAgent
from ontoproduct.agents.registry import CONTRACTS
from ontoproduct.prompts.extraction import INSTRUCTIONS, VERSION
from ontoproduct.schemas.ontology import OntologyMapping
from ontoproduct.schemas.product import (
    ExtractedProduct,
    ParsedDocument,
    ProductAttribute,
)
from ontoproduct.services.agent_errors import DocumentConflictError
from ontoproduct.services.attribute_merge import enforce_conflicts, merge_attributes
from ontoproduct.services.document_chunks import document_chunks
from ontoproduct.services.evidence_service import (
    normalize_whitespace,
    validate_evidence,
)
from ontoproduct.services.llm_protocol import LlmService, validated_response
from ontoproduct.services.mapping_service import PropertyAliases
from ontoproduct.services.ontology_service import OntologyService


class EvidenceAttribute(ProductAttribute):
    confidence: float | None = Field(default=None, ge=0, le=1, strict=True)


class ExtractionResponse(ExtractedProduct):
    """Same fields, stricter LLM score type; the public state schema is unchanged."""

    attributes: dict[str, EvidenceAttribute] = Field(default_factory=dict)


class ExtractionAgent(BaseAgent):
    name = "extraction"
    provider = "structured-llm-adapter"
    version = VERSION
    is_mock = False

    def __init__(
        self,
        llm_service: LlmService,
        *,
        ontology=None,
        aliases=None,
        max_chars=12000,
        overlap_chars=128,
    ):
        required, optional, writes = CONTRACTS[self.name]
        self.required_reads, self.optional_reads, self.writes = (
            set(required),
            set(optional),
            dict(writes),
        )
        self.llm_service = llm_service
        self.ontology = ontology if ontology is not None else OntologyService()
        self.aliases = aliases if aliases is not None else PropertyAliases()
        # Validate limits without requiring a document or a model call.
        list(document_chunks([], max_chars=max_chars, overlap_chars=overlap_chars))
        self.max_chars, self.overlap_chars = max_chars, overlap_chars

    def _field(self, path):
        if not isinstance(path, str):
            raise ValueError("Field paths must be strings")
        key = path.removeprefix("attributes.")
        if key in {"product_name", "candidate_class", "product_class"}:
            return key
        return self.aliases.resolve(key)

    def run(self, state):
        documents = TypeAdapter(list[ParsedDocument]).validate_python(
            state["parsed_documents"]
        )
        if not documents or not any(d.text.strip() for d in documents):
            raise ValueError("parsed_documents contain no readable text")
        mapping = (
            OntologyMapping.model_validate(state["ontology_mapping"])
            if state.get("ontology_mapping")
            else None
        )
        known = {
            key
            for cls in self.ontology.definition.classes
            for key in self.ontology.resolve_properties(cls)
        }
        if mapping:
            known.update(mapping.required_properties)
            known.update(mapping.optional_properties)
        locked = {self._field(p) for p in state.get("locked_fields", [])}
        retry = state.get("review_result", {}).get("decision") == "RE_EXTRACT"
        requested = None
        if retry:
            requested = {
                self._field(p)
                for p in state.get("review_result", {}).get("retry_fields", [])
            }
            if requested - known:
                raise ValueError(
                    f"Unsupported retry_fields: {sorted(requested - known)}; only known attributes are supported"
                )
            requested -= locked
            if not requested:
                return {"extracted_product": ExtractedProduct().model_dump(mode="json")}
        names, classes, batches = set(), set(), []
        for chunk in document_chunks(
            documents, max_chars=self.max_chars, overlap_chars=self.overlap_chars
        ):
            payload = {
                "instructions": INSTRUCTIONS,
                "prompt_version": VERSION,
                "documents": [chunk],
                "property_aliases": self.aliases.as_payload(),
                "requested_fields": sorted(requested)
                if requested is not None
                else None,
                "locked_fields": sorted(locked),
                "ontology_context": mapping.model_dump(mode="json")
                if mapping
                else None,
                "semantic_model": (
                    self.ontology.semantic_model.as_context()
                    if self.ontology.semantic_model is not None
                    else None
                ),
            }
            response = validated_response(
                self.llm_service,
                task="extraction",
                payload=payload,
                schema=ExtractionResponse,
            )
            if not retry:
                if response.product_name and "product_name" not in locked:
                    name = response.product_name.strip()
                    if not name or normalize_whitespace(
                        name
                    ) not in normalize_whitespace(chunk["text"]):
                        raise ValueError(
                            "product_name is not present in the supplied document chunk"
                        )
                    names.add(name)
                if response.candidate_class and "candidate_class" not in locked:
                    classes.add(response.candidate_class)
            attrs = {}
            chunk_doc = ParsedDocument.model_validate(
                {k: chunk[k] for k in ("source_file", "page", "text")}
            )
            for key, attr in response.attributes.items():
                canonical = self.aliases.resolve(key)
                if canonical in locked or (
                    requested is not None and canonical not in requested
                ):
                    continue
                validate_evidence(attr, [chunk_doc])
                validated = validate_evidence(attr, documents)
                # Keep aliases distinct until merge so two spellings cannot overwrite.
                attrs[key] = validated
            batches.append(attrs)
        if len(names) > 1:
            raise DocumentConflictError(f"Conflicting product names: {sorted(names)}")
        candidate = next(iter(classes)) if len(classes) == 1 else None
        required, optional = {}, {}
        if mapping:
            required, optional = (
                mapping.required_properties,
                mapping.optional_properties,
            )
        elif candidate in self.ontology.definition.classes:
            required = self.ontology.resolve_required_properties(candidate)
            optional = self.ontology.resolve_optional_properties(candidate)
        attrs = merge_attributes(
            batches, self.aliases, self.ontology.unit_service, {**required, **optional}
        )
        enforce_conflicts(attrs, required, optional)
        result = ExtractedProduct(
            product_name=next(iter(names)) if names else None,
            candidate_class=None if retry else candidate,
            attributes=attrs,
        )
        return {"extracted_product": result.model_dump(mode="json")}
