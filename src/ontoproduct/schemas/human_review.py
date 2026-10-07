from enum import Enum
from typing import Literal
from pydantic import model_validator
from .common import DomainModel
from .product import ProductAttribute


class HumanAction(str, Enum):
    APPROVE = "APPROVE"
    EDIT = "EDIT"
    REJECT = "REJECT"


class HumanReviewCommand(DomainModel):
    action: HumanAction
    edits: dict[str, ProductAttribute | str] | None = None
    changed_class: str | None = None

    @model_validator(mode="after")
    def edits_only_on_edit(self):
        if self.action != HumanAction.EDIT and (
            self.edits is not None or self.changed_class is not None
        ):
            raise ValueError("edits and changed_class are only allowed with EDIT")
        return self


class ErrorRetryCommand(DomainModel):
    action: Literal["RETRY", "STOP"]
