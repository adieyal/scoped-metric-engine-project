from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from .fact import Provenance
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
    provenance: Provenance | None = None
    issues: list[ResolutionIssue] = field(default_factory=list)


class PrimitiveFactFetcher(Protocol):
    family: str

    def fetch(self, request: FetchRequest) -> FetchResponse:
        ...
