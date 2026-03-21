from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


def canonicalize_group_dimensions(
    dimensions: Mapping[str, Any],
) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted(dimensions.items(), key=lambda item: item[0]))


@dataclass(frozen=True)
class GroupKey:
    dimensions: tuple[tuple[str, Any], ...]

    @classmethod
    def from_mapping(cls, dimensions: Mapping[str, Any]) -> GroupKey:
        return cls(dimensions=canonicalize_group_dimensions(dimensions))
