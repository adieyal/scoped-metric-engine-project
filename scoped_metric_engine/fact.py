from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .fact_key import FactKey
from .types import Completeness


@dataclass(frozen=True)
class SourceProvenance:
    """Provenance from the data source that produced a primitive fact."""

    source_name: str | None = None
    source_query_id: str | None = None
    extra: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ResolutionProvenance:
    """Tracks how a fact was resolved within the scoped metric engine.

    Distinct from Metric Engine's own Provenance which tracks calculation
    lineage (stored in Fact.calculation_provenance).
    """

    origin: str  # fetched | zero_filled | derived
    fetch_family: str | None = None
    fetch_request_id: str | None = None
    population_mode: str | None = None


@dataclass
class Fact:
    """A resolved metric value.

    ``value`` may hold:
    - raw source values from primitive fetchers
    - Metric Engine ``FinancialValue`` objects for derived metrics
    - aggregated values produced by the aggregation layer

    Callers should not assume plain scalars.
    """

    key: FactKey
    value: Any
    completeness: Completeness = "complete"
    source_type: str = "primitive"
    provenance: SourceProvenance | None = None
    resolution_provenance: ResolutionProvenance | None = None
    calculation_provenance: Any | None = None
