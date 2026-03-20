# Define Aggregation Policy

Create one `MetricAggregationPolicy` per metric you want to aggregate.

```python
from scoped_metric_engine import (
    AggregationPolicyRegistry,
    MetricAggregationPolicy,
)

aggregation_policies = AggregationPolicyRegistry(
    {
        "revenue": MetricAggregationPolicy("revenue", ("sum", "mean", "min", "max")),
        "gross_margin": MetricAggregationPolicy(
            "gross_margin",
            ("mean", "weighted_recompute"),
            ("revenue", "cogs"),
        ),
    }
)
```

If a metric is requested with an unsupported operator, the result is:
- `value=None`
- completeness=`"unavailable"`
- an issue entry with `code="UNSUPPORTED_AGGREGATION"`.

