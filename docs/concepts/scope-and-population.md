# Scope and Population

The engine resolves metrics for a single `Scope` request, then optional aggregation
requests can combine multiple scopes.

## Scope

`Scope` is composed of:

- `Slice`: entity ids, date window, and optional filters.
- `ResolutionGrain`: which group dimensions should be emitted.

`Slice` validates:

- entity ids are not empty
- `start_date <= end_date`

`ResolutionGrain` currently supports at most one grouping dimension.

## Population modes

- `PopulationSpec("observed")`
  - groups only appear when the underlying fetchers return rows.
- `PopulationSpec("eligible")`
  - groups come from your `PopulationResolver`.
  - paired with zero-fill for configured primitives.

## Population resolver contract

Your resolver receives `(scope, population)` and returns rows with:

- `group_key`: deterministic key for row identity.
- `dimensions`: stable dimension labels for output rows.

For `observed`, returning `[]` is valid and common.

