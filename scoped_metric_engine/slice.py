from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


def canonicalize_filters(
    filters: tuple[tuple[str, Any], ...] | None,
) -> tuple[tuple[str, Any], ...]:
    if not filters:
        return ()
    return tuple(sorted(filters, key=lambda item: item[0]))


@dataclass(frozen=True)
class Slice:
    entity_ids: tuple[int, ...]
    start_date: date
    end_date: date
    filters: tuple[tuple[str, Any], ...] = ()

    def canonicalized(self) -> "Slice":
        return Slice(
            entity_ids=tuple(sorted(self.entity_ids)),
            start_date=self.start_date,
            end_date=self.end_date,
            filters=canonicalize_filters(self.filters),
        )

    def validate(self) -> None:
        if not self.entity_ids:
            raise ValueError("Slice.entity_ids must not be empty")
        if self.start_date > self.end_date:
            raise ValueError("Slice.start_date must be <= end_date")
