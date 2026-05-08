from __future__ import annotations

from dataclasses import dataclass

from evosql_platform.config import DEFAULT_ITERATIONS, DEFAULT_SAMPLE_SIZE, DEFAULT_TOP_K


@dataclass(slots=True)
class SchedulePlan:
    iterations: int = DEFAULT_ITERATIONS
    sample_size: int = DEFAULT_SAMPLE_SIZE
    top_k: int = DEFAULT_TOP_K


@dataclass(slots=True)
class RuntimeSignals:
    iteration: int
    schema_stable: bool
    best_sql_stable: bool
    cluster_stable: bool
    success_rate: float
    disagreement_rate: float
    empty_result_rate: float
    consecutive_failure_rounds: int = 0


class AdaptiveScheduler:
    def build_plan(self, question: str, schema_size: int) -> SchedulePlan:
        q = question.lower()
        complexity_bonus = self.question_complexity(question)
        if schema_size > 8 or complexity_bonus >= 3:
            return SchedulePlan(iterations=4, sample_size=8, top_k=3)
        if complexity_bonus >= 1:
            return SchedulePlan(iterations=3, sample_size=6, top_k=2)
        return SchedulePlan(iterations=2, sample_size=4, top_k=2)

    def next_sample_size(self, plan: SchedulePlan, signals: RuntimeSignals) -> int:
        if signals.success_rate < 0.34 or signals.disagreement_rate > 0.66:
            return min(plan.sample_size + 2, 10)
        if signals.schema_stable and signals.cluster_stable:
            return max(3, plan.sample_size - 1)
        return plan.sample_size

    def next_top_k(self, plan: SchedulePlan, signals: RuntimeSignals) -> int:
        if signals.disagreement_rate > 0.5:
            return min(plan.top_k + 1, 4)
        if signals.cluster_stable and signals.schema_stable:
            return max(1, plan.top_k - 1)
        return plan.top_k

    def should_stop(
        self,
        previous_tables: set[str],
        current_tables: set[str],
        stable_rounds: int,
        signals: RuntimeSignals | None = None,
    ) -> bool:
        if signals is None:
            return previous_tables == current_tables and stable_rounds >= 1
        if signals.consecutive_failure_rounds >= 2:
            return True
        convergence = (
            signals.schema_stable
            and signals.cluster_stable
            and signals.best_sql_stable
            and signals.success_rate >= 0.5
            and signals.empty_result_rate < 0.75
        )
        return convergence or stable_rounds >= 2

    def question_complexity(self, question: str) -> int:
        q = question.lower()
        return sum(
            keyword in q
            for keyword in ["trend", "排名", "top", "近", "按", "以及", "and", "group", "join", "趋势", "占比"]
        )
