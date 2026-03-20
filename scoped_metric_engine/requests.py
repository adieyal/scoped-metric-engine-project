from __future__ import annotations

from dataclasses import dataclass, field

from .aggregation import AggregationSpec
from .population import PopulationSpec
from .scope import Scope


@dataclass(frozen=True)
class CalculationOptions:
    allow_partial: bool = True
    policy: object | None = None


@dataclass(frozen=True)
class ScopeRef:
    label: str
    scope: Scope


@dataclass
class ResolveMetricsRequest:
    scope: Scope
    metrics: list[str]
    population: PopulationSpec = field(default_factory=lambda: PopulationSpec("observed"))
    calculation_options: CalculationOptions = field(default_factory=CalculationOptions)


@dataclass
class AggregationRequest:
    scopes: list[ScopeRef]
    metrics: list[str]
    aggregation_spec: AggregationSpec
    population: PopulationSpec = field(default_factory=lambda: PopulationSpec("observed"))
    calculation_options: CalculationOptions = field(default_factory=CalculationOptions)
