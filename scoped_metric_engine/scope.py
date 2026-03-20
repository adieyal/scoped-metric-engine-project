from __future__ import annotations

from dataclasses import dataclass, field

from .execution_context import ExecutionContext
from .slice import Slice


@dataclass(frozen=True)
class ResolutionGrain:
    dimensions: tuple[str, ...]

    def validate(self) -> None:
        if len(self.dimensions) > 1:
            raise ValueError("V1 supports at most one grouping dimension")


@dataclass(frozen=True)
class Scope:
    slice: Slice
    resolution_grain: ResolutionGrain
    execution_context: ExecutionContext = field(default_factory=ExecutionContext)

    def canonicalized(self) -> "Scope":
        return Scope(
            slice=self.slice.canonicalized(),
            resolution_grain=ResolutionGrain(tuple(self.resolution_grain.dimensions)),
            execution_context=self.execution_context,
        )

    def validate(self) -> None:
        self.slice.validate()
        self.resolution_grain.validate()
