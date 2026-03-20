# Aggregation

`aggregate_metrics` repeatedly resolves multiple scalar scopes and then applies
per-metric aggregation policies.

## Supported operators

- `sum`
- `mean`
- `min`
- `max`
- `weighted_recompute`

`weighted_recompute` is policy-driven and currently implemented for
`gross_margin`-style recomputation from dependent primitives.

## Aggregation policy

Register `MetricAggregationPolicy` per metric:

- `supported_ops`
- optional `recompute_from` dependencies

Policy controls what operators are legal and how completeness is combined.

## Completeness

Result completeness follows this precedence:

1. `unavailable` if any input is unavailable
2. `partial` if any input is partial
3. `complete` only when all inputs are complete

