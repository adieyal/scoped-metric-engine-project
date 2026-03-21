from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .fact_key import FactKey
from .fetch_request import FetchRequest


@dataclass(frozen=True)
class FactDemand:
    key: FactKey
    family: str


@dataclass(frozen=True)
class _FetchShape:
    family: str
    scope_slice: object
    resolution_grain: object
    execution_context: object


@dataclass
class FetchPlan:
    requests: list[FetchRequest]
    covered_demands: Mapping[FetchRequest, set[FactDemand]]


class FetchPlanner:
    def build_fetch_plan(self, demands: list[FactDemand]) -> FetchPlan:
        grouped: dict[_FetchShape, dict[str, FactDemand]] = {}

        for demand in demands:
            shape = _FetchShape(
                family=demand.family,
                scope_slice=demand.key.scope.slice,
                resolution_grain=demand.key.scope.resolution_grain,
                execution_context=demand.key.scope.execution_context,
            )
            metric_demands = grouped.setdefault(shape, {})
            metric_demands[demand.key.metric] = demand

        planned_groups = sorted(grouped.items(), key=self._sort_key_for_shape)

        requests: list[FetchRequest] = []
        covered_demands: dict[FetchRequest, set[FactDemand]] = {}

        for shape, metric_demands in planned_groups:
            metrics = tuple(sorted(metric_demands))
            request = FetchRequest(
                family=shape.family,
                slice=shape.scope_slice,
                resolution_grain=shape.resolution_grain,
                execution_context=shape.execution_context,
                metrics=metrics,
            )
            requests.append(request)
            covered_demands[request] = set(metric_demands.values())

        return FetchPlan(requests=requests, covered_demands=covered_demands)

    @staticmethod
    def _sort_key_for_shape(item: tuple[_FetchShape, dict[str, FactDemand]]) -> tuple[object, ...]:
        shape, metric_demands = item
        return (
            shape.family,
            repr(shape.scope_slice),
            repr(shape.resolution_grain),
            repr(shape.execution_context),
            tuple(sorted(metric_demands)),
        )
