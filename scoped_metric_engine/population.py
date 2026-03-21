from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from .group_key import GroupKey
from .scope import Scope
from .types import PopulationMode


@dataclass(frozen=True)
class PopulationSpec:
    mode: PopulationMode


@dataclass(frozen=True)
class PopulationRow:
    group_key: GroupKey
    dimensions: Mapping[str, object]


class PopulationResolver(Protocol):
    def resolve_population(
        self,
        scope: Scope,
        population: PopulationSpec,
    ) -> Sequence[PopulationRow]: ...
