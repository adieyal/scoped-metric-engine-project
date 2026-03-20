from __future__ import annotations

from typing import Protocol

from .fact import Fact
from .fact_key import FactKey


class FactStore(Protocol):
    def get(self, key: FactKey) -> Fact | None: ...
    def put(self, fact: Fact) -> None: ...
    def put_many(self, facts: list[Fact]) -> None: ...
    def has(self, key: FactKey) -> bool: ...


class InMemoryFactStore:
    def __init__(self) -> None:
        self._facts: dict[FactKey, Fact] = {}

    def get(self, key: FactKey) -> Fact | None:
        return self._facts.get(key)

    def put(self, fact: Fact) -> None:
        self._facts[fact.key] = fact

    def put_many(self, facts: list[Fact]) -> None:
        for fact in facts:
            self.put(fact)

    def has(self, key: FactKey) -> bool:
        return key in self._facts
