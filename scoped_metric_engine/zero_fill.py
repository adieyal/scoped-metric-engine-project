from __future__ import annotations

from typing import Sequence

from .fact import Fact, ResolutionProvenance
from .fact_key import FactKey
from .metric_metadata import ScopedMetricRegistry
from .population import PopulationRow
from .scope import Scope


def build_zero_filled_facts(
    scope: Scope,
    primitive_metrics: Sequence[str],
    population_rows: Sequence[PopulationRow],
    existing_fact_keys: set[FactKey],
    metric_registry: ScopedMetricRegistry,
    *,
    population_mode: str | None = None,
) -> list[Fact]:
    facts: list[Fact] = []

    for row in population_rows:
        for metric in primitive_metrics:
            metadata = metric_registry.get(metric)
            if not metadata.semantics or not metadata.semantics.zero_fill_if_eligible_but_absent:
                continue

            key = FactKey(metric=metric, scope=scope, group_key=row.group_key)
            if key in existing_fact_keys:
                continue

            facts.append(
                Fact(
                    key=key,
                    value=0,
                    completeness="complete",
                    source_type="primitive",
                    resolution_provenance=ResolutionProvenance(
                        origin="zero_filled",
                        population_mode=population_mode,
                    ),
                )
            )

    return facts
