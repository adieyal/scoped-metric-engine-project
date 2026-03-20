from datetime import date

import pytest

from scoped_metric_engine.scope import ResolutionGrain, Scope
from scoped_metric_engine.slice import Slice


def test_slice_canonicalization_sorts_entities_and_filters():
    scope = Scope(
        slice=Slice(entity_ids=(3, 1, 2), start_date=date(2026, 1, 1), end_date=date(2026, 1, 31), filters=(("z", 1), ("a", 2))),
        resolution_grain=ResolutionGrain(("item",)),
    )
    canonical = scope.canonicalized()
    assert canonical.slice.entity_ids == (1, 2, 3)
    assert canonical.slice.filters == (("a", 2), ("z", 1))


def test_resolution_grain_validation_rejects_multi_dimension():
    with pytest.raises(ValueError):
        ResolutionGrain(("item", "month")).validate()
