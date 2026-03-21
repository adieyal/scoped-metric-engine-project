from __future__ import annotations

from typing import Protocol


class MetricEngineAdapter(Protocol):
    def get_dependencies(self, target: str) -> set[str]: ...

    def inputs_needed_for(self, targets: set[str] | list[str]) -> set[str]: ...

    def calculate_many(
        self,
        targets: set[str],
        ctx: dict[str, object] | None = None,
        *,
        policy: object | None = None,
        allow_partial: bool = True,
        **kwargs: object,
    ) -> dict[str, object]: ...

    def calculate(
        self,
        target: str,
        ctx: dict[str, object] | None = None,
        *,
        policy: object | None = None,
        allow_partial: bool = True,
        **kwargs: object,
    ) -> object: ...
