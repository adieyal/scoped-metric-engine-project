from __future__ import annotations

from dataclasses import dataclass

from .execution_context import ExecutionContext
from .scope import ResolutionGrain
from .slice import Slice


@dataclass(frozen=True)
class FetchRequest:
    family: str
    slice: Slice
    resolution_grain: ResolutionGrain
    execution_context: ExecutionContext
    metrics: tuple[str, ...]
