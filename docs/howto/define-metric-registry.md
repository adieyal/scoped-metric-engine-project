# Define a Metric Registry

Declare every metric that the engine can resolve.

```python
from scoped_metric_engine import (
    PrimitiveMetricSemantics,
    ScopedMetricMetadata,
    ScopedMetricRegistry,
)

metric_registry = ScopedMetricRegistry(
    {
        "revenue": ScopedMetricMetadata(
            name="revenue",
            kind="primitive",
            family="sales",
            value_type="currency",
            semantics=PrimitiveMetricSemantics(zero_fill_if_eligible_but_absent=True),
        ),
        "gross_margin": ScopedMetricMetadata(
            name="gross_margin",
            kind="derived",
            value_type="ratio",
        ),
    }
)
```

## Primitive registration checklist

- set `kind="primitive"` and provide `family`
- set `value_type` for intent and validation clarity
- choose zero-fill semantics for metrics that should default to zero in eligible mode
- use unique metric names referenced by fetchers and adapters
