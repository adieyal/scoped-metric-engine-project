from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from .fact import SourceProvenance
from .fetch_request import FetchRequest
from .issues import ResolutionIssue


@dataclass(frozen=True)
class RawFetchRow:
    group_dimensions: Mapping[str, Any]
    metrics: Mapping[str, Any]
    dimensions: Mapping[str, Any] | None = None


@dataclass
class FetchResponse:
    request: FetchRequest
    rows: list[RawFetchRow]
    provenance: SourceProvenance | None = None
    issues: list[ResolutionIssue] = field(default_factory=list)


class PrimitiveFactFetcher(Protocol):
    family: str

    def fetch(self, request: FetchRequest) -> FetchResponse: ...
