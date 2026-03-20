from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .fact_key import FactKey
from .types import Completeness


@dataclass(frozen=True)
class Provenance:
    source_name: str | None = None
    source_query_id: str | None = None
    extra: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ResolutionProvenance:
    origin: str  # fetched | zero_filled | derived
    fetch_family: str | None = None
    fetch_request_id: str | None = None
    population_mode: str | None = None


@dataclass
class Fact:
    key: FactKey
    value: Any
    completeness: Completeness = "complete"
    source_type: str = "primitive"
    provenance: Provenance | None = None
    resolution_provenance: ResolutionProvenance | None = None
    calculation_provenance: Any | None = None
