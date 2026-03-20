from __future__ import annotations

from typing import Protocol


class MetricEngineAdapter(Protocol):
    def get_dependencies(self, metric_name: str) -> set[str]:
        ...

    def calculate_many(
        self,
        targets: set[str],
        ctx: dict[str, object] | None = None,
        allow_partial: bool = True,
        policy: object | None = None,
    ) -> dict[str, object]:
        ...
