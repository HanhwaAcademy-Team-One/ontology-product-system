class DocumentConflictError(ValueError):
    """Conflicting document values cannot safely pass the current workflow."""


class OntologyClassificationError(ValueError):
    """No single supported product class could be selected."""
