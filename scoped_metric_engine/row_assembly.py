from __future__ import annotations

from collections.abc import Mapping, Sequence

from .fact_key import FactKey
from .fact_store import FactStore
from .group_key import GroupKey
from .issues import ResolutionIssue
from .results import ResultRow
from .scope import Scope
from .types import Completeness


def combine_row_completeness(metric_completenesses: Sequence[Completeness]) -> Completeness:
    if any(c == "unavailable" for c in metric_completenesses):
        return "unavailable"
    if any(c == "partial" for c in metric_completenesses):
        return "partial"
    return "complete"


def assemble_rows(
    scope: Scope,
    group_keys: Sequence[GroupKey | None],
    row_dimensions: Mapping[GroupKey | None, Mapping[str, object]],
    metrics: Sequence[str],
    fact_store: FactStore,
) -> list[ResultRow]:
    rows: list[ResultRow] = []

    for group_key in group_keys:
        metric_values: dict[str, object] = {}
        metric_completenesses: list[Completeness] = []
        issues: list[ResolutionIssue] = []

        for metric in metrics:
            fact = fact_store.get(FactKey(metric=metric, scope=scope, group_key=group_key))
            if fact is None:
                metric_values[metric] = None
                metric_completenesses.append("unavailable")
                issues.append(
                    ResolutionIssue(
                        code="MISSING_FACT",
                        message=f"Missing fact for metric '{metric}'",
                        key=FactKey(metric=metric, scope=scope, group_key=group_key),
                    )
                )
            else:
                metric_values[metric] = fact.value
                metric_completenesses.append(fact.completeness)

        rows.append(
            ResultRow(
                group_key=group_key,
                dimensions=dict(row_dimensions.get(group_key, {})),
                metrics=metric_values,
                completeness=combine_row_completeness(metric_completenesses),
                issues=issues,
            )
        )

    return rows
