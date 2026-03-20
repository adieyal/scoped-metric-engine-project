from __future__ import annotations

from dataclasses import dataclass

from .group_key import GroupKey
from .scope import Scope


@dataclass(frozen=True)
class FactKey:
    metric: str
    scope: Scope
    group_key: GroupKey | None = None
