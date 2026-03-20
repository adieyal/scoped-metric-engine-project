from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .dependency_resolver import MetricEngineAdapter
from .fact import Fact, ResolutionProvenance
from .fact_key import FactKey
from .fact_store import FactStore
from .group_key import GroupKey
from .scope import Scope


@dataclass(frozen=True)
class CalculationOutcome:
    value: Any
    completeness: str
    provenance: Any | None = None


def build_row_context(
    scope: Scope,
    group_key: GroupKey | None,
    metrics: Sequence[str],
    fact_store: FactStore,
) -> dict[str, Any]:
    context: dict[str, Any] = {}
    for metric in metrics:
        fact = fact_store.get(FactKey(metric=metric, scope=scope, group_key=group_key))
        context[metric] = None if fact is None else fact.value
    return context


def compute_metrics_for_row(
    scope: Scope,
    group_key: GroupKey | None,
    metrics: Sequence[str],
    metric_engine: MetricEngineAdapter,
    fact_store: FactStore,
    *,
    allow_partial: bool = True,
    policy: object | None = None,
    population_mode: str | None = None,
) -> list[Fact]:
    ctx = build_row_context(scope, group_key, metrics, fact_store)
    results = metric_engine.calculate_many(
        targets=set(metrics),
        ctx=ctx,
        allow_partial=allow_partial,
        policy=policy,
    )

    facts: list[Fact] = []
    for metric, value in results.items():
        completeness = _infer_completeness(value)
        provenance = _extract_provenance(value)
        facts.append(
            Fact(
                key=FactKey(metric=metric, scope=scope, group_key=group_key),
                value=_extract_value(value),
                completeness=completeness,
                source_type="derived",
                resolution_provenance=ResolutionProvenance(
                    origin="derived",
                    population_mode=population_mode,
                ),
                calculation_provenance=provenance,
            )
        )
    return facts


def _extract_provenance(value: Any) -> Any | None:
    if hasattr(value, "get_provenance"):
        return value.get_provenance()
    return getattr(value, "_prov", None)


def _extract_value(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "amount"):
        return value.amount
    return value


def _infer_completeness(value: Any) -> str:
    if hasattr(value, "is_none"):
        return "unavailable" if value.is_none() else "complete"
    raw_value = _extract_value(value)
    return "unavailable" if raw_value is None else "complete"
