# Fetching and Fact Assembly

Primitive values are fetched in batches per family using a
`PrimitiveFactFetcher` implementation.

## Fetch planner behavior

- Required primitives are discovered from requested metrics and adapter dependencies.
- Primitive demands are grouped by:
  - family
  - scope slice
  - resolution grain
  - execution context
- One `FetchRequest` is produced per unique group.

## Response normalization

Each `FetchResponse` row (`RawFetchRow`) is normalized into internal `Fact` objects
with provenance tags:

- `origin="fetched"`
- `fetch_family=<family>`
- `fetch_request_id=<stable hash>`
- `population_mode=<observed/eligible>`

If `ResolutionGrain` dimensions are set, `group_dimensions` produce `GroupKey`.
Otherwise the request is treated as an aggregate-only primitive context.

