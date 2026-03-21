from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .dependency_resolver import MetricEngineAdapter
from .fact import Fact, ResolutionProvenance
from .fact_key import FactKey
from .fact_store import FactStore
from .group_key import GroupKey
from .scope import Scope
from .types import Completeness


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


def _has_partial_upstream(
    scope: Scope,
    group_key: GroupKey | None,
    metrics: Sequence[str],
    fact_store: FactStore,
) -> bool:
    """Return True if any upstream context fact has partial completeness."""
    for metric in metrics:
        fact = fact_store.get(FactKey(metric=metric, scope=scope, group_key=group_key))
        if fact is not None and fact.completeness == "partial":
            return True
    return False


def compute_metrics_for_row(
    scope: Scope,
    group_key: GroupKey | None,
    targets: Sequence[str],
    metric_engine: MetricEngineAdapter,
    fact_store: FactStore,
    *,
    context_metrics: Sequence[str] | None = None,
    allow_partial: bool = True,
    policy: object | None = None,
    population_mode: str | None = None,
) -> list[Fact]:
    ctx = build_row_context(scope, group_key, context_metrics or targets, fact_store)
    results = metric_engine.calculate_many(
        targets=set(targets),
        ctx=ctx,
        allow_partial=allow_partial,
        policy=policy,
    )

    upstream_partial = _has_partial_upstream(scope, group_key, context_metrics or targets, fact_store)

    facts: list[Fact] = []
    for metric, value in results.items():
        completeness: Completeness = _infer_completeness(value)
        # If the derived value itself is available but any upstream context
        # fact is partial, downgrade to partial.
        if completeness == "complete" and upstream_partial:
            completeness = "partial"
        facts.append(
            Fact(
                key=FactKey(metric=metric, scope=scope, group_key=group_key),
                value=value,
                completeness=completeness,
                source_type="derived",
                resolution_provenance=ResolutionProvenance(
                    origin="derived",
                    population_mode=population_mode,
                ),
                calculation_provenance=_extract_provenance(value),
            )
        )
    return facts


def _extract_provenance(value: Any) -> Any | None:
    if hasattr(value, "get_provenance"):
        return value.get_provenance()
    return getattr(value, "_prov", None)


def _infer_completeness(value: Any) -> Completeness:
    if hasattr(value, "is_none"):
        return "unavailable" if value.is_none() else "complete"
    return "unavailable" if value is None else "complete"
