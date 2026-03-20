from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .types import MetricKind, MetricValueType


@dataclass(frozen=True)
class PrimitiveMetricSemantics:
    zero_fill_if_eligible_but_absent: bool = False


@dataclass(frozen=True)
class ScopedMetricMetadata:
    name: str
    kind: MetricKind
    family: str | None = None
    value_type: MetricValueType = "other"
    semantics: PrimitiveMetricSemantics | None = None


class ScopedMetricRegistry:
    def __init__(self, metrics: Mapping[str, ScopedMetricMetadata]) -> None:
        self._metrics = dict(metrics)

    def get(self, metric_name: str) -> ScopedMetricMetadata:
        try:
            return self._metrics[metric_name]
        except KeyError as exc:
            raise KeyError(f"Unknown metric: {metric_name}") from exc

    def has(self, metric_name: str) -> bool:
        return metric_name in self._metrics

    def all(self) -> dict[str, ScopedMetricMetadata]:
        return dict(self._metrics)
