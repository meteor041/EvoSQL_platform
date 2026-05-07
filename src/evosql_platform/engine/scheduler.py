from __future__ import annotations

from dataclasses import dataclass

from evosql_platform.config import DEFAULT_ITERATIONS, DEFAULT_SAMPLE_SIZE, DEFAULT_TOP_K


@dataclass(slots=True)
class SchedulePlan:
    iterations: int = DEFAULT_ITERATIONS
    sample_size: int = DEFAULT_SAMPLE_SIZE
    top_k: int = DEFAULT_TOP_K


class AdaptiveScheduler:
    def build_plan(self, question: str, schema_size: int) -> SchedulePlan:
        q = question.lower()
        complexity_bonus = sum(
            keyword in q for keyword in ["trend", "排名", "top", "近", "按", "以及", "and", "group", "join"]
        )
        if schema_size > 8 or complexity_bonus >= 3:
            return SchedulePlan(iterations=3, sample_size=8, top_k=3)
        if complexity_bonus >= 1:
            return SchedulePlan(iterations=3, sample_size=6, top_k=2)
        return SchedulePlan(iterations=2, sample_size=4, top_k=2)

    def should_stop(self, previous_tables: set[str], current_tables: set[str], stable_rounds: int) -> bool:
        return previous_tables == current_tables and stable_rounds >= 1
