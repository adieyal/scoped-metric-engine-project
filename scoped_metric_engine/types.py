from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Literal, TypeAlias

Completeness: TypeAlias = Literal["complete", "partial", "unavailable"]
MetricKind: TypeAlias = Literal["primitive", "derived"]
MetricValueType: TypeAlias = Literal["currency", "count", "ratio", "number", "other"]
PopulationMode: TypeAlias = Literal["observed", "eligible"]
AggregationOp: TypeAlias = Literal["sum", "mean", "min", "max", "weighted_recompute"]

ScalarMetricValue: TypeAlias = int | float | Decimal | str | None | Any
DimensionsMap: TypeAlias = Mapping[str, Any]
