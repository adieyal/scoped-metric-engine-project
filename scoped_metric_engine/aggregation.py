from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Mapping, Sequence

from .issues import ResolutionIssue
from .types import AggregationOp, Completeness


@dataclass(frozen=True)
class AggregationOperator:
    metric: str
    op: AggregationOp


@dataclass(frozen=True)
class AggregationSpec:
    operators: tuple[AggregationOperator, ...]


@dataclass(frozen=True)
class MetricAggregationPolicy:
    metric: str
    supported_ops: tuple[str, ...]
    recompute_from: tuple[str, ...] = ()


class AggregationPolicyRegistry:
    def __init__(self, policies: Mapping[str, MetricAggregationPolicy]) -> None:
        self._policies = dict(policies)

    def get(self, metric: str) -> MetricAggregationPolicy | None:
        return self._policies.get(metric)


@dataclass
class AggregationInputValue:
    metric: str
    value: Any
    completeness: Completeness


def aggregate_values(
    operator: AggregationOperator,
    values: Sequence[AggregationInputValue],
    policy: MetricAggregationPolicy | None,
    recompute_inputs: Mapping[str, Sequence[AggregationInputValue]] | None = None,
) -> tuple[Any, Completeness, list[ResolutionIssue]]:
    issues: list[ResolutionIssue] = []

    if policy is None or operator.op not in policy.supported_ops:
        return (
            None,
            "unavailable",
            [ResolutionIssue(
                code="UNSUPPORTED_AGGREGATION",
                message=f"Aggregation '{operator.op}' not supported for metric '{operator.metric}'",
            )],
        )

    usable = [v.value for v in values if v.completeness != "unavailable"]
    if operator.op != "weighted_recompute" and not usable:
        return None, "unavailable", issues

    completeness = _combine_aggregation_completeness(values)

    if operator.op == "sum":
        return sum(usable), completeness, issues
    if operator.op == "mean":
        return mean(usable), completeness, issues
    if operator.op == "min":
        return min(usable), completeness, issues
    if operator.op == "max":
        return max(usable), completeness, issues
    if operator.op == "weighted_recompute":
        if not policy.recompute_from or recompute_inputs is None:
            return (
                None,
                "unavailable",
                [ResolutionIssue(
                    code="UNSUPPORTED_AGGREGATION",
                    message=f"Missing recompute inputs for metric '{operator.metric}'",
                )],
            )
        return _recompute_weighted_metric(operator.metric, recompute_inputs)

    return (
        None,
        "unavailable",
        [ResolutionIssue(
            code="UNSUPPORTED_AGGREGATION",
            message=f"Unknown aggregation op '{operator.op}'",
        )],
    )


def _combine_aggregation_completeness(values: Sequence[AggregationInputValue]) -> Completeness:
    if any(v.completeness == "unavailable" for v in values):
        return "unavailable"
    if any(v.completeness == "partial" for v in values):
        return "partial"
    return "complete"


def _recompute_weighted_metric(
    metric: str,
    recompute_inputs: Mapping[str, Sequence[AggregationInputValue]],
) -> tuple[Any, Completeness, list[ResolutionIssue]]:
    issues: list[ResolutionIssue] = []

    if metric != "gross_margin":
        return (
            None,
            "unavailable",
            [ResolutionIssue(
                code="UNSUPPORTED_AGGREGATION",
                message=f"weighted_recompute not implemented for '{metric}'",
            )],
        )

    revenue_values = recompute_inputs.get("revenue", [])
    cogs_values = recompute_inputs.get("cogs", [])
    if not revenue_values or not cogs_values:
        return (
            None,
            "unavailable",
            [ResolutionIssue(
                code="UNSUPPORTED_AGGREGATION",
                message="Missing revenue/cogs inputs for gross_margin recompute",
            )],
        )

    revenue_total = sum(v.value for v in revenue_values if v.completeness != "unavailable")
    cogs_total = sum(v.value for v in cogs_values if v.completeness != "unavailable")
    if revenue_total == 0:
        return None, "unavailable", issues

    completeness = _combine_aggregation_completeness([*revenue_values, *cogs_values])
    gross_profit = revenue_total - cogs_total
    return gross_profit / revenue_total, completeness, issues
