from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .fact_key import FactKey
from .fetch_request import FetchRequest


@dataclass(frozen=True)
class FactDemand:
    key: FactKey
    family: str


@dataclass
class FetchPlan:
    requests: list[FetchRequest]
    covered_demands: Mapping[FetchRequest, set[FactDemand]]


class FetchPlanner:
    def build_fetch_plan(self, demands: list[FactDemand]) -> FetchPlan:
        grouped: dict[tuple[object, ...], list[FactDemand]] = {}

        for demand in demands:
            key = (
                demand.family,
                demand.key.scope.slice,
                demand.key.scope.resolution_grain,
                demand.key.scope.execution_context,
            )
            grouped.setdefault(key, []).append(demand)

        requests: list[FetchRequest] = []
        covered_demands: dict[FetchRequest, set[FactDemand]] = {}

        for (family, slice_, grain, execution_context), group_demands in grouped.items():
            metrics = tuple(sorted({d.key.metric for d in group_demands}))
            request = FetchRequest(
                family=family,
                slice=slice_,
                resolution_grain=grain,
                execution_context=execution_context,
                metrics=metrics,
            )
            requests.append(request)
            covered_demands[request] = set(group_demands)

        return FetchPlan(requests=requests, covered_demands=covered_demands)
