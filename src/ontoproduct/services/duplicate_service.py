from difflib import SequenceMatcher

from ontoproduct.schemas.duplicate import DuplicateCandidate


class DuplicateService:
    def __init__(self, repository):
        self.repository = repository

    def find(self, product, *, top_k=3):
        candidates = []
        for record in self.repository.list():
            existing = record["product"]
            if existing["product_class"] != product["product_class"]:
                continue
            common = existing["attributes"].keys() & product["attributes"].keys()
            values = [(existing["attributes"][key], product["attributes"][key]) for key in common]
            values = [(a, b) for a, b in values if a["value"] is not None and b["value"] is not None]
            match = sum(a["value"] == b["value"] and a.get("unit") == b.get("unit") for a, b in values)
            attribute_score = match / len(values) if values else 0
            name_score = SequenceMatcher(None, existing.get("product_name") or "", product.get("product_name") or "").ratio()
            score = 0.2 + 0.4 * attribute_score + 0.4 * name_score
            if score >= 0.6:
                candidates.append(DuplicateCandidate(
                    product_id=record["product_id"], product_name=existing.get("product_name") or "(unnamed)",
                    score=score, reason="Rule similarity of class, name, and shared canonical attributes.").model_dump(mode="json"))
        return sorted(candidates, key=lambda c: (-c["score"], c["product_id"]))[:top_k]
