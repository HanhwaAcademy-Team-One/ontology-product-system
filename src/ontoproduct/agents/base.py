from abc import ABC, abstractmethod
from typing import Any
from ontoproduct.graph.state import ProductState


class AgentContractError(ValueError):
    pass


class BaseAgent(ABC):
    name: str
    provider: str
    version: str
    is_mock: bool
    required_reads: set[str]
    optional_reads: set[str]
    writes: dict[str, Any]

    @abstractmethod
    def run(self, state: ProductState) -> dict:
        """Return only business outputs without mutating input state."""
        ...

    def health_check(self) -> bool:
        return True
