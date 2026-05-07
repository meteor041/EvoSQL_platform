from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from evosql_platform.models import ContextState


class LLMClient(ABC):
    @abstractmethod
    def generate_candidates(self, context: ContextState, sample_size: int) -> list[str]:
        raise NotImplementedError

    def select_schema(self, context: ContextState, max_tables: int = 6) -> dict[str, Any]:
        return {"tables": [], "reasoning": "Schema linking not implemented for this client."}
