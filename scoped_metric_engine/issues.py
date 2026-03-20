from __future__ import annotations

from dataclasses import dataclass

from .fact_key import FactKey


@dataclass(frozen=True)
class ResolutionIssue:
    code: str
    message: str
    key: FactKey | None = None
