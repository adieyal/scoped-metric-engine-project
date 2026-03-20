# scoped-metric-engine Getting Started

This library is a small orchestration layer that resolves **primitive** and **derived** metrics for a requested scope and optional population.

It does **not** know your domain — you supply:

- which metrics exist (and whether they are primitive/derived)
- fetchers for primitive metric families
- a population resolver (observed vs eligible rows)
- an adapter for your Metric Engine

---

## Install

```bash
pip install -e .[dev]
pytest  # optional: run the library test suite as examples
```

---

## Core object model (quick)

- **`ScopedMetricEngine`**: main entry point.
- **`ResolveMetricsRequest`**: asks for values at one scope.
- **`AggregationRequest`**: combines multiple resolved scopes.
- **`ScopedMetricRegistry`**: tells the engine what each metric is.
- **`InMemoryFactStore`**: cache used during a resolve/aggregate call.

---

## 1) Define your metric registry

```python
from scoped_metric_engine import (
    ScopedMetricMetadata,
    ScopedMetricRegistry,
    PrimitiveMetricSemantics,
)

metric_registry = ScopedMetricRegistry(
    {
        "units_sold": ScopedMetricMetadata(
            "units_sold",
            kind="primitive",
            family="sales",
            value_type="count",
            semantics=PrimitiveMetricSemantics(zero_fill_if_eligible_but_absent=True),
        ),
        "revenue": ScopedMetricMetadata(
            "revenue",
            kind="primitive",
            family="sales",
            value_type="currency",
            semantics=PrimitiveMetricSemantics(zero_fill_if_eligible_but_absent=True),
        ),
        "cogs": ScopedMetricMetadata(
            "cogs",
            kind="primitive",
            family="costs",
            value_type="currency",
            semantics=PrimitiveMetricSemantics(zero_fill_if_eligible_but_absent=False),
        ),
        "gross_profit": ScopedMetricMetadata("gross_profit", kind="derived", value_type="currency"),
        "gross_margin": ScopedMetricMetadata("gross_margin", kind="derived", value_type="ratio"),
    }
)
```

`family` is used to route each primitive metric to one registered fetcher.

---

## 2) Implement primitive fetchers

A fetcher returns a `FetchResponse` for its `family`.
The engine may call one fetcher multiple times with different metrics (batched by family).

```python
from scoped_metric_engine import FetchResponse, RawFetchRow, FetchRequest


class SalesFetcher:
    family = "sales"

    def fetch(self, request: FetchRequest) -> FetchResponse:
        # `request.metrics` contains only metrics needed from this family
        return FetchResponse(
            request=request,
            rows=[
                RawFetchRow(
                    group_dimensions={"item_id": 1},
                    dimensions={"name": "Alpha"},
                    metrics={"units_sold": 10, "revenue": 100},
                ),
                RawFetchRow(
                    group_dimensions={"item_id": 2},
                    dimensions={"name": "Beta"},
                    metrics={"units_sold": 5, "revenue": 40},
                ),
            ],
        )


class CostsFetcher:
    family = "costs"

    def fetch(self, request: FetchRequest) -> FetchResponse:
        return FetchResponse(
            request=request,
            rows=[
                RawFetchRow(
                    group_dimensions={"item_id": 1},
                    dimensions={"name": "Alpha"},
                    metrics={"cogs": 60},
                ),
                RawFetchRow(
                    group_dimensions={"item_id": 2},
                    dimensions={"name": "Beta"},
                    metrics={"cogs": 25},
                ),
            ],
        )
```

---

## 3) Population resolver

Returned rows differ by population mode:

- `PopulationSpec("observed")`: only groups present in fetch results.
- `PopulationSpec("eligible")`: all eligible groups from resolver, plus zero-fill (if configured on metric metadata).

```python
from scoped_metric_engine import GroupKey, PopulationRow, PopulationSpec
from scoped_metric_engine.scope import Scope


class MyPopulationResolver:
    def resolve_population(self, scope: Scope, population: PopulationSpec):
        # Keep it empty for observed mode if you only want fetched rows
        if population.mode == "observed":
            return []

        # For eligible mode, explicitly list all possible groups
        return [
            PopulationRow(GroupKey.from_mapping({"item_id": 1}), {"name": "Alpha"}),
            PopulationRow(GroupKey.from_mapping({"item_id": 2}), {"name": "Beta"}),
            PopulationRow(GroupKey.from_mapping({"item_id": 3}), {"name": "Gamma"}),
        ]
```

---

## 4) Provide a Metric Engine adapter

`ScopedMetricEngine` expects an adapter exposing:

- `get_dependencies(metric_name) -> set[str]`
- `calculate_many(targets, ctx=None, allow_partial=True, policy=None) -> mapping[str, value_obj]`

Each returned value object should provide:

- `.value`
- `.is_none()`
- optional `.get_provenance()`

```python
class FinancialValue:
    def __init__(self, value, provenance=None):
        self.value = value
        self._provenance = provenance

    def is_none(self):
        return self.value is None

    def get_provenance(self):
        return self._provenance


class MetricEngineAdapter:
    def get_dependencies(self, metric_name):
        if metric_name == "gross_profit":
            return {"revenue", "cogs"}
        if metric_name == "gross_margin":
            return {"gross_profit", "revenue", "cogs"}
        return set()

    def calculate_many(self, targets, ctx=None, allow_partial=True, policy=None):
        ctx = ctx or {}
        out = {}
        for metric in targets:
            if metric == "gross_profit":
                revenue = ctx.get("revenue")
                cogs = ctx.get("cogs")
                value = None if revenue is None or cogs is None else revenue - cogs
                out[metric] = FinancialValue(value, "calc:gross_profit")
            elif metric == "gross_margin":
                revenue = ctx.get("revenue")
                cogs = ctx.get("cogs")
                if revenue in (None, 0) or cogs is None:
                    value = None
                else:
                    value = (revenue - cogs) / revenue
                out[metric] = FinancialValue(value, "calc:gross_margin")
            else:
                # primitives are read from context
                out[metric] = FinancialValue(ctx.get(metric), f"input:{metric}")
        return out
```

---

## 5) Wire the scoped engine

```python
from datetime import date
from scoped_metric_engine import (
    ScopedMetricEngine,
    InMemoryFactStore,
    AggregationPolicyRegistry,
    MetricAggregationPolicy,
    ResolutionGrain,
    Scope,
    Slice,
    ResolveMetricsRequest,
    PopulationSpec,
)

aggregation_policies = AggregationPolicyRegistry(
    {
        "revenue": MetricAggregationPolicy("revenue", supported_ops=("sum", "mean", "min", "max")),
        "cogs": MetricAggregationPolicy("cogs", supported_ops=("sum", "mean", "min", "max")),
        "gross_margin": MetricAggregationPolicy(
            "gross_margin",
            supported_ops=("mean", "weighted_recompute"),
            recompute_from=("revenue", "cogs"),
        ),
    }
)

engine = ScopedMetricEngine(
    metric_registry=metric_registry,
    fact_store=InMemoryFactStore(),
    fetchers_by_family={"sales": SalesFetcher(), "costs": CostsFetcher()},
    population_resolver=MyPopulationResolver(),
    metric_engine=MetricEngineAdapter(),
    aggregation_policy_registry=aggregation_policies,
)

scope = Scope(
    slice=Slice(
        entity_ids=(2, 1),
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        filters=(("category", "example"),),
    ),
    resolution_grain=ResolutionGrain(("item",)),
)

result = engine.resolve_metrics(
    ResolveMetricsRequest(
        scope=scope,
        metrics=["units_sold", "revenue", "cogs", "gross_profit", "gross_margin"],
        population=PopulationSpec("eligible"),
    )
)

for row in result.rows:
    print("---")
    print("group:", row.group_key)
    print("dimensions:", row.dimensions)
    print("metrics:", row.metrics)
    print("completeness:", row.completeness)

# result.rows values for item 3 are zero-filled for units_sold/revenue,
# and cogs is missing there unless your costs fetcher returns it
# (zero_fill_if_eligible_but_absent=False for cogs)
```

---

## 6) Aggregate across scopes

Use this when you already have several scalar scopes (e.g., months/quarters).

```python
from scoped_metric_engine import (
    AggregationRequest,
    AggregationOperator,
    AggregationSpec,
    ScopeRef,
)

jan = Scope(Slice((1,), date(2026, 1, 1), date(2026, 1, 31),), ResolutionGrain(()))
feb = Scope(Slice((1,), date(2026, 2, 1), date(2026, 2, 28),), ResolutionGrain(()))

agg = engine.aggregate_metrics(
    AggregationRequest(
        scopes=[ScopeRef("jan", jan), ScopeRef("feb", feb)],
        metrics=["revenue", "gross_margin"],
        aggregation_spec=AggregationSpec((
            AggregationOperator("revenue", "mean"),
            AggregationOperator("gross_margin", "weighted_recompute"),
        )),
        population=PopulationSpec("observed"),
    )
)

for value in agg.values:
    print(value.metric, value.value, value.completeness)
```

---

## 7) Common gotchas

- `Scope.slice.entity_ids` must not be empty.
- `start_date <= end_date`.
- `ResolutionGrain` currently supports **at most one** dimension.
- If population mode is `observed`, groups come only from fetchers.
- If you request derived metrics, `metric_engine.get_dependencies` must include primitive dependencies.
- Check `result.issues` / `value.issues` for warnings and unsupported metrics/aggregations.

---

## 8) Single-file runnable example

Copy this into `example.py` and run it.

```python
from datetime import date

from scoped_metric_engine import (
    AggregationOperator,
    AggregationPolicyRegistry,
    AggregationRequest,
    AggregationSpec,
    FetchRequest,
    FetchResponse,
    GroupKey,
    InMemoryFactStore,
    MetricAggregationPolicy,
    PopulationRow,
    PopulationSpec,
    PrimitiveMetricSemantics,
    RawFetchRow,
    ResolveMetricsRequest,
    ResolutionGrain,
    ScopedMetricEngine,
    ScopedMetricMetadata,
    ScopedMetricRegistry,
    Scope,
    ScopeRef,
    Slice,
)


class SalesFetcher:
    family = "sales"

    def fetch(self, request: FetchRequest) -> FetchResponse:
        if request.resolution_grain.dimensions:
            return FetchResponse(
                request=request,
                rows=[
                    RawFetchRow({"item_id": 1}, {"name": "Alpha"}, {"units_sold": 10, "revenue": 100}),
                    RawFetchRow({"item_id": 2}, {"name": "Beta"}, {"units_sold": 5, "revenue": 40}),
                ],
            )
        return FetchResponse(
            request=request,
            rows=[RawFetchRow({}, {}, {"revenue": 100})],
        )


class CostsFetcher:
    family = "costs"

    def fetch(self, request: FetchRequest) -> FetchResponse:
        if request.resolution_grain.dimensions:
            return FetchResponse(
                request=request,
                rows=[
                    RawFetchRow({"item_id": 1}, {"name": "Alpha"}, {"cogs": 60}),
                    RawFetchRow({"item_id": 2}, {"name": "Beta"}, {"cogs": 25}),
                    RawFetchRow({"item_id": 3}, {"name": "Gamma"}, {"cogs": 0}),
                ],
            )
        return FetchResponse(
            request=request,
            rows=[RawFetchRow({}, {}, {"cogs": 50})],
        )


class MyPopulationResolver:
    def resolve_population(self, scope: Scope, population: PopulationSpec):
        if population.mode == "observed":
            return []
        return [
            PopulationRow(GroupKey.from_mapping({"item_id": 1}), {"name": "Alpha"}),
            PopulationRow(GroupKey.from_mapping({"item_id": 2}), {"name": "Beta"}),
            PopulationRow(GroupKey.from_mapping({"item_id": 3}), {"name": "Gamma"}),
        ]


class FinancialValue:
    def __init__(self, value, provenance=None):
        self.value = value
        self._prov = provenance

    def is_none(self):
        return self.value is None

    def get_provenance(self):
        return self._prov


class MetricEngine:
    def get_dependencies(self, metric_name):
        if metric_name == "gross_profit":
            return {"revenue", "cogs"}
        if metric_name == "gross_margin":
            return {"gross_profit", "revenue", "cogs"}
        return set()

    def calculate_many(self, targets, ctx=None, allow_partial=True, policy=None):
        ctx = ctx or {}
        out = {}
        for metric in targets:
            if metric == "gross_profit":
                rev, cogs = ctx.get("revenue"), ctx.get("cogs")
                out[metric] = FinancialValue(None if rev is None or cogs is None else rev - cogs, "calc:gross_profit")
            elif metric == "gross_margin":
                rev, cogs = ctx.get("revenue"), ctx.get("cogs")
                out[metric] = FinancialValue(
                    None if rev in (None, 0) or cogs is None else (rev - cogs) / rev,
                    "calc:gross_margin",
                )
            else:
                out[metric] = FinancialValue(ctx.get(metric), f"input:{metric}")
        return out


def main():
    metric_registry = ScopedMetricRegistry(
        {
            "units_sold": ScopedMetricMetadata(
                "units_sold",
                kind="primitive",
                family="sales",
                value_type="count",
                semantics=PrimitiveMetricSemantics(zero_fill_if_eligible_but_absent=True),
            ),
            "revenue": ScopedMetricMetadata(
                "revenue",
                kind="primitive",
                family="sales",
                value_type="currency",
                semantics=PrimitiveMetricSemantics(zero_fill_if_eligible_but_absent=True),
            ),
            "cogs": ScopedMetricMetadata(
                "cogs",
                kind="primitive",
                family="costs",
                value_type="currency",
                semantics=PrimitiveMetricSemantics(zero_fill_if_eligible_but_absent=False),
            ),
            "gross_profit": ScopedMetricMetadata("gross_profit", "derived", value_type="currency"),
            "gross_margin": ScopedMetricMetadata("gross_margin", "derived", value_type="ratio"),
        }
    )

    aggregation_policies = AggregationPolicyRegistry(
        {
            "revenue": MetricAggregationPolicy("revenue", supported_ops=("sum", "mean", "min", "max")),
            "cogs": MetricAggregationPolicy("cogs", supported_ops=("sum", "mean", "min", "max")),
            "gross_margin": MetricAggregationPolicy(
                "gross_margin",
                supported_ops=("mean", "weighted_recompute"),
                recompute_from=("revenue", "cogs"),
            ),
        }
    )

    engine = ScopedMetricEngine(
        metric_registry=metric_registry,
        fact_store=InMemoryFactStore(),
        fetchers_by_family={"sales": SalesFetcher(), "costs": CostsFetcher()},
        population_resolver=MyPopulationResolver(),
        metric_engine=MetricEngine(),
        aggregation_policy_registry=aggregation_policies,
    )

    grouped_scope = Scope(
        slice=Slice((2, 1), date(2026, 2, 1), date(2026, 2, 28), filters=(("category", "demo"),)),
        resolution_grain=ResolutionGrain(("item",)),
    )

    resolved = engine.resolve_metrics(
        ResolveMetricsRequest(
            scope=grouped_scope,
            metrics=["units_sold", "revenue", "cogs", "gross_profit", "gross_margin"],
            population=PopulationSpec("eligible"),
        )
    )

    print("Resolved grouped rows:")
    for row in resolved.rows:
        print(row.group_key.dimensions, row.metrics)

    jan = Scope(Slice((1,), date(2026, 1, 1), date(2026, 1, 31)), ResolutionGrain(()))
    feb = Scope(Slice((1,), date(2026, 2, 1), date(2026, 2, 28)), ResolutionGrain(()))

    aggregated = engine.aggregate_metrics(
        AggregationRequest(
            scopes=[ScopeRef("jan", jan), ScopeRef("feb", feb)],
            metrics=["revenue", "gross_margin"],
            aggregation_spec=AggregationSpec((
                AggregationOperator("revenue", "mean"),
                AggregationOperator("gross_margin", "weighted_recompute"),
            )),
            population=PopulationSpec("observed"),
        )
    )

    print("Aggregated values:", {v.metric: v.value for v in aggregated.values})


if __name__ == "__main__":
    main()
```

---

## Best next step

The unit tests are the living spec for edge cases and expected behavior. Start with:

- `tests/test_engine_resolve_metrics.py`
- `tests/test_engine_aggregate_metrics.py`
- `tests/test_zero_fill.py`
