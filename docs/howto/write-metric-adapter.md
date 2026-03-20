# Write a Metric Adapter

`ScopedMetricEngine` relies on a `MetricEngineAdapter` to compute derived values.

```python
from scoped_metric_engine import MetricEngineAdapter


class MyMetricAdapter:
    def get_dependencies(self, metric_name: str) -> set[str]:
        if metric_name == "gross_margin":
            return {"revenue", "cogs"}
        if metric_name == "gross_profit":
            return {"revenue", "cogs"}
        return set()

    def calculate_many(self, targets, ctx=None, allow_partial=True, policy=None):
        ctx = ctx or {}
        out = {}
        for metric in targets:
            if metric == "gross_profit":
                rev = ctx.get("revenue")
                cogs = ctx.get("cogs")
                out[metric] = None if rev is None or cogs is None else rev - cogs
            elif metric == "gross_margin":
                rev = ctx.get("revenue")
                cogs = ctx.get("cogs")
                if rev in (None, 0) or cogs is None:
                    out[metric] = None
                else:
                    out[metric] = (rev - cogs) / rev
            else:
                out[metric] = ctx.get(metric)
        return out
```

For derived metrics, ensure dependencies are complete enough for your failure mode.
When values are missing you may return `None` to signal `unavailable` outputs.

