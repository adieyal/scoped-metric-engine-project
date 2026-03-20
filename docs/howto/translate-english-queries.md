# Convert English Queries to Structured Requests

`ScopedMetricEngine` works with structured requests (`ResolveMetricsRequest` and `AggregationRequest`), so NL queries are first normalized to an intermediate intent object and then mapped to these types.

Common extracted fields are:

- `time_range` (start/end dates)
- `entity_scope` (entity ids or names resolved to ids)
- `requested_metrics` (including derived metrics)
- `grouping` (`ResolutionGrain`)
- `population_mode` (`observed` / `eligible`)

## Example 1: Single scalar request

English:

`What was revenue for region West in March 2026?`

Parsed structure:

```json
{
  "intent": "resolve_metric",
  "scope": {
    "entities": ["region:West"],
    "time_range": {"start": "2026-03-01", "end": "2026-03-31"},
    "metrics": ["revenue"],
    "grain": []
  },
  "population": "observed"
}
```

Engine request:

```python
from datetime import date

from scoped_metric_engine import PopulationSpec, ResolveMetricsRequest, ResolutionGrain, Scope, Slice

ResolveMetricsRequest(
    scope=Scope(
        slice=Slice(
            entity_ids=(21,),  # "region West" resolved by your entity resolver
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            filters=(("region_name", "West"),),
        ),
        resolution_grain=ResolutionGrain(()),
    ),
    metrics=["revenue"],
    population=PopulationSpec("observed"),
)
```

## Example 2: Derived metrics with calculation mode

English:

`Show gross margin and gross profit for district North for Q1 2026.`

Parsed structure:

```json
{
  "intent": "resolve_metric",
  "scope": {
    "entities": ["district:North"],
    "time_range": {"start": "2026-01-01", "end": "2026-03-31"},
    "metrics": ["gross_profit", "gross_margin"],
    "grain": []
  },
  "population": "observed",
  "calculation_options": {"allow_partial": true}
}
```

Engine request:

```python
from datetime import date

from scoped_metric_engine import CalculationOptions, PopulationSpec, ResolveMetricsRequest, ResolutionGrain, Scope, Slice

ResolveMetricsRequest(
    scope=Scope(
        slice=Slice(
            entity_ids=(101,),  # "district North" resolved by your entity resolver
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            filters=(("time_bucket", "Q1"),),
        ),
        resolution_grain=ResolutionGrain(()),
    ),
    metrics=["gross_profit", "gross_margin"],
    population=PopulationSpec("observed"),
    calculation_options=CalculationOptions(allow_partial=True),
)
```

## Example 3: Grouped eligible request

English:

`List monthly revenue and gross margin for active products in Feb 2026, grouped by product.`

Parsed structure:

```json
{
  "intent": "resolve_metric",
  "scope": {
    "entities": ["org:3"],
    "time_range": {"start": "2026-02-01", "end": "2026-02-28"},
    "metrics": ["revenue", "gross_margin"],
    "grain": ["product"]
  },
  "population": "eligible"
}
```

Engine request:

```python
from datetime import date

from scoped_metric_engine import PopulationSpec, ResolveMetricsRequest, ResolutionGrain, Scope, Slice

ResolveMetricsRequest(
    scope=Scope(
        slice=Slice(
            entity_ids=(3,),  # resolved from "org:3"
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
            filters=(("product_status", "active"),),
        ),
        resolution_grain=ResolutionGrain(("product",)),
    ),
    metrics=["revenue", "gross_margin"],
    population=PopulationSpec("eligible"),
)
```

## Example 4: Multi-scope comparison

English:

`Compare average gross margin and total revenue for Jan and Feb 2026.`

Parsed structure:

```json
{
  "intent": "compare_scopes",
  "scopes": [
    {"label": "jan", "time_range": {"start": "2026-01-01", "end": "2026-01-31"}},
    {"label": "feb", "time_range": {"start": "2026-02-01", "end": "2026-02-28"}}
  ],
  "metrics": ["revenue", "gross_margin"],
  "aggregation": {
    "revenue": "sum",
    "gross_margin": "mean"
  }
}
```

Engine request:

```python
from datetime import date

from scoped_metric_engine import (
    AggregationOperator,
    AggregationRequest,
    AggregationSpec,
    PopulationSpec,
    ResolutionGrain,
    Scope,
    ScopeRef,
    Slice,
)

AggregationRequest(
    scopes=[
        ScopeRef(
            "jan",
            Scope(
                slice=Slice((3,), date(2026, 1, 1), date(2026, 1, 31)),
                resolution_grain=ResolutionGrain(()),
            ),
        ),
        ScopeRef(
            "feb",
            Scope(
                slice=Slice((3,), date(2026, 2, 1), date(2026, 2, 28)),
                resolution_grain=ResolutionGrain(()),
            ),
        ),
    ],
    metrics=["revenue", "gross_margin"],
    aggregation_spec=AggregationSpec(
        (
            AggregationOperator("revenue", "sum"),
            AggregationOperator("gross_margin", "mean"),
        )
    ),
    population=PopulationSpec("observed"),
)
```

## Suggested NL-to-structured pipeline

1. Classify intent (`resolve_metric`, `compare_scopes`, etc.).
2. Resolve entities to canonical ids and emit `entity_ids` plus filters.
3. Parse dates from phrases (`March 2026`, `Q1`) into `Slice.start_date` / `Slice.end_date`.
4. Expand aliases (`gross margin` -> `gross_margin`, `revenue` -> `revenue`).
5. Set `ResolutionGrain` from grouping words (`by product`, `by team`, etc.).
6. Select population policy and calculation options.
7. Validate metric dependencies and dispatch `ResolveMetricsRequest` / `AggregationRequest`.
