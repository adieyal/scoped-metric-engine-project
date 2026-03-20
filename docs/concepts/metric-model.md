# Metric Model

The package is built around four core domain objects:

- `Scope` and `Slice`: what and when to evaluate.
- `ScopedMetricMetadata` and `ScopedMetricRegistry`: what metrics are known.
- `FetchRequest` / `FetchResponse`: how primitive facts are gathered.
- `ResolvedMetricTable` / `AggregatedMetricResult`: what comes back from the engine.

## Primitive vs derived metrics

Every metric is explicitly registered in the `ScopedMetricRegistry`.

- Primitive metrics have a `family` and are resolved from fetchers.
- Derived metrics have dependencies declared by your Metric Engine adapter.

The engine always computes derived values from the context produced by primitive
facts and previously resolved values for the same group.

## Canonical metadata fields

- `name`: canonical metric identifier.
- `kind`: `"primitive"` or `"derived"`.
- `family`: fetcher family for primitive metrics (`None` for derived).
- `value_type`: optional domain hint (`currency`, `ratio`, `count`, etc.).
- `semantics`: optional primitive semantics, including zero-fill behavior.

## Zero-fill semantics

Zero-fill applies only when `PopulationSpec("eligible")` is used.
If a primitive metric has `zero_fill_if_eligible_but_absent=True`, missing
group/mode combinations are emitted as zero-valued facts instead of being absent.

