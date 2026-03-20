from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionContext:
    currency: str | None = None
    snapshot_version: str | None = None
    metric_definition_version: str | None = None
