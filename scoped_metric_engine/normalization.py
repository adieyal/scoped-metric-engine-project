from __future__ import annotations

import hashlib

from .fact import Fact, ResolutionProvenance
from .fact_key import FactKey
from .fetch_request import FetchRequest
from .fetchers import FetchResponse
from .group_key import GroupKey
from .scope import Scope


def normalize_fetch_response_to_facts(
    scope: Scope,
    response: FetchResponse,
    *,
    population_mode: str | None = None,
) -> tuple[list[Fact], dict[GroupKey, dict[str, object]]]:
    facts: list[Fact] = []
    row_dimensions: dict[GroupKey, dict[str, object]] = {}

    for row in response.rows:
        if response.request.resolution_grain.dimensions:
            group_key = GroupKey.from_mapping(row.group_dimensions)
            row_dimensions[group_key] = dict(row.dimensions or {})
        else:
            group_key = None

        for metric_name, value in row.metrics.items():
            fact = Fact(
                key=FactKey(metric=metric_name, scope=scope, group_key=group_key),
                value=value,
                completeness="complete",
                source_type="primitive",
                provenance=response.provenance,
                resolution_provenance=ResolutionProvenance(
                    origin="fetched",
                    fetch_family=response.request.family,
                    fetch_request_id=_fetch_request_id(response.request),
                    population_mode=population_mode,
                ),
            )
            facts.append(fact)

    return facts, row_dimensions


def _fetch_request_id(request: FetchRequest) -> str:
    """Produce a deterministic ID for a FetchRequest using SHA-256.

    Python's built-in hash() is randomised across processes (PYTHONHASHSEED),
    so we derive the ID from stable, explicit fields instead.
    """
    parts = (
        request.family,
        repr(request.slice),
        repr(request.resolution_grain),
        repr(request.execution_context),
        repr(request.metrics),
    )
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return digest[:16]
