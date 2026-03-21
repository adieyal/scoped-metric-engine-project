from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import mean
from typing import TYPE_CHECKING, Any

from .issues import ResolutionIssue
from .types import AggregationOp, Completeness

if TYPE_CHECKING:
    from .dependency_resolver import MetricEngineAdapter
    from .requests import CalculationOptions


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
    metric_engine: MetricEngineAdapter | None = None,
    calculation_options: CalculationOptions | None = None,
) -> tuple[Any, Completeness, list[ResolutionIssue]]:
    """Aggregate per-scope metric values using the given operator.

    ``sum``, ``mean``, ``min``, and ``max`` operate on unwrapped plain
    numerics — the orchestration layer is responsible for extracting raw
    numbers before passing them in.

    ``weighted_recompute`` delegates formula recomputation back to
    ``metric_engine.calculate()``, which returns domain value objects
    (e.g. FinancialValue).
    """
    issues: list[ResolutionIssue] = []

    if policy is None or operator.op not in policy.supported_ops:
        return (
            None,
            "unavailable",
            [
                ResolutionIssue(
                    code="UNSUPPORTED_AGGREGATION",
                    message=f"Aggregation '{operator.op}' not supported for metric '{operator.metric}'",
                )
            ],
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
        return _recompute_weighted_metric(
            operator.metric,
            policy,
            recompute_inputs,
            metric_engine=metric_engine,
            calculation_options=calculation_options,
        )

    return (
        None,
        "unavailable",
        [
            ResolutionIssue(
                code="UNSUPPORTED_AGGREGATION",
                message=f"Unknown aggregation op '{operator.op}'",
            )
        ],
    )


def _combine_aggregation_completeness(values: Sequence[AggregationInputValue]) -> Completeness:
    if any(v.completeness == "unavailable" for v in values):
        return "unavailable"
    if any(v.completeness == "partial" for v in values):
        return "partial"
    return "complete"


def _recompute_weighted_metric(
    metric: str,
    policy: MetricAggregationPolicy,
    recompute_inputs: Mapping[str, Sequence[AggregationInputValue]] | None,
    *,
    metric_engine: MetricEngineAdapter | None = None,
    calculation_options: CalculationOptions | None = None,
) -> tuple[Any, Completeness, list[ResolutionIssue]]:
    if not policy.recompute_from or recompute_inputs is None:
        return (
            None,
            "unavailable",
            [
                ResolutionIssue(
                    code="UNSUPPORTED_AGGREGATION",
                    message=f"Missing recompute inputs for metric '{metric}'",
                )
            ],
        )

    if metric_engine is None:
        return (
            None,
            "unavailable",
            [
                ResolutionIssue(
                    code="UNSUPPORTED_AGGREGATION",
                    message=f"No metric engine provided for recompute of '{metric}'",
                )
            ],
        )

    # Aggregate each input metric, then delegate formula to metric engine.
    aggregated_ctx: dict[str, Any] = {}
    all_input_values: list[AggregationInputValue] = []
    for input_metric in policy.recompute_from:
        input_values = recompute_inputs.get(input_metric, [])
        all_input_values.extend(input_values)
        usable = [v.value for v in input_values if v.completeness != "unavailable"]
        if not usable:
            return (
                None,
                "unavailable",
                [
                    ResolutionIssue(
                        code="UNSUPPORTED_AGGREGATION",
                        message=f"No usable values for recompute input '{input_metric}'",
                    )
                ],
            )
        aggregated_ctx[input_metric] = sum(usable)

    calc_policy = calculation_options.policy if calculation_options else None
    allow_partial = calculation_options.allow_partial if calculation_options else True

    value = metric_engine.calculate(
        metric,
        ctx=aggregated_ctx,
        policy=calc_policy,
        allow_partial=allow_partial,
    )

    completeness: Completeness
    if hasattr(value, "is_none") and value.is_none():
        completeness = "unavailable"
    else:
        completeness = _combine_aggregation_completeness(all_input_values)

    return value, completeness, []
