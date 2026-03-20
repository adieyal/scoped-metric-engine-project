# Configure Population Mode

Use `PopulationSpec` to choose row inclusion behavior.

- `PopulationSpec("observed")` is the safest default for performance.
- `PopulationSpec("eligible")` should be used when you need a fixed row set.

## Observed mode

Only rows that fetchers returned for the scope are included.

## Eligible mode

Your `PopulationResolver` decides which groups are eligible for the scope.
The engine can combine this with zero-fill to produce stable row outputs for groups
that lack rows from specific fetchers.

```python
from scoped_metric_engine import GroupKey, PopulationRow, PopulationSpec

rows = [
    PopulationRow(GroupKey.from_mapping({"item_id": 1}), {"name": "Alpha"}),
    PopulationRow(GroupKey.from_mapping({"item_id": 2}), {"name": "Beta"}),
]

population = PopulationSpec("eligible")
```

