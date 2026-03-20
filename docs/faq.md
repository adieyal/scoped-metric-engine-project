# FAQ

## Why isn't aggregation supported for grouped results?

Current implementation supports scalar scope aggregation. Grouped result sets should be
aggregated per calling context via external logic or future extension.

## Why do I see `UNSUPPORTED_FETCH_FAMILY`?

No fetcher was registered for a required metric family. Add a fetcher for the
missing family in `fetchers_by_family`.

## When should I use `PopulationSpec("eligible")`?

Use it when you need consistent row completeness independent of missing fact returns
for known groups, often for dashboard tables.

