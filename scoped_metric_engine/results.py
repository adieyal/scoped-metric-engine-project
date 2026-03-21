from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .group_key import GroupKey
from .issues import ResolutionIssue
from .population import PopulationSpec
from .requests import ScopeRef
from .scope import Scope
from .types import Completeness


@dataclass
class ResultRow:
    group_key: GroupKey | None
    dimensions: Mapping[str, Any]
    metrics: Mapping[str, Any]
    completeness: Completeness
    issues: list[ResolutionIssue] = field(default_factory=list)


@dataclass
class ResolvedMetricTable:
    scope: Scope
    population: PopulationSpec
    rows: list[ResultRow]
    issues: list[ResolutionIssue] = field(default_factory=list)


@dataclass
class AggregatedMetricValue:
    metric: str
    value: Any
    completeness: Completeness
    issues: list[ResolutionIssue] = field(default_factory=list)


@dataclass
class AggregatedMetricResult:
    scopes: list[ScopeRef]
    population: PopulationSpec
    values: list[AggregatedMetricValue]
    issues: list[ResolutionIssue] = field(default_factory=list)
