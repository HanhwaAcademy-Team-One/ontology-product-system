from typing import Literal

from pydantic import Field, model_validator

from .common import DomainModel


class ValidationIssue(DomainModel):
    field: str
    code: Literal[
        "MISSING_REQUIRED",
        "MISSING_OPTIONAL",
        "TYPE",
        "UNIT",
        "RANGE",
        "UNKNOWN_PROPERTY",
        "CLASS",
    ]
    message: str
    severity: Literal["error", "warning"] = "error"


class ValidationResult(DomainModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def coherent(self):
        if self.valid == any(i.severity == "error" for i in self.issues):
            raise ValueError("valid must agree with error issues")
        return self
