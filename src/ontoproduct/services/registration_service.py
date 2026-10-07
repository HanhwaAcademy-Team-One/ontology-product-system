import json
from pathlib import Path
from uuid import UUID, uuid4

from ontoproduct.schemas.human_review import HumanReviewCommand
from ontoproduct.schemas.product import NormalizedProduct
from ontoproduct.services.validation_service import validate_product


class RegistrationService:
    def __init__(self, repository, ontology, export_directory):
        self.repository, self.ontology = repository, ontology
        self.export_directory = Path(export_directory)

    def register(self, case_id, product, human_review):
        command = HumanReviewCommand.model_validate(human_review)
        if command.action != "APPROVE":
            raise ValueError("Registration requires human approval")
        product = NormalizedProduct.model_validate(product).model_dump(mode="json")
        cls = product["product_class"]
        mapping = {
            "product_class": cls,
            "confidence": 1,
            "required_properties": {
                k: p.model_dump(mode="json")
                for k, p in self.ontology.resolve_required_properties(cls).items()
            },
            "optional_properties": {
                k: p.model_dump(mode="json")
                for k, p in self.ontology.resolve_optional_properties(cls).items()
            },
        }
        if not validate_product(product, mapping)["valid"]:
            raise ValueError("Product failed deterministic validation")
        result = self.repository.save(case_id, product)
        result["export_path"] = str(self.export(result["record"]))
        return result

    def export(self, record):
        product_id = str(UUID(record["product_id"]))
        self.export_directory.mkdir(parents=True, exist_ok=True)
        destination = self.export_directory / f"{product_id}.json"
        temporary = self.export_directory / f".{product_id}.{uuid4().hex}.tmp"
        payload = self.json_bytes(record)
        try:
            temporary.write_bytes(payload)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return destination

    @staticmethod
    def json_bytes(record):
        return json.dumps(
            record["product"], ensure_ascii=False, allow_nan=False, indent=2
        ).encode("utf-8")
