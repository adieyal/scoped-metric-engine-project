# scoped-metric-engine

A domain-neutral library for resolving primitive and derived metrics over canonical scopes and populations.

## What it owns

- scope canonicalization
- population resolution contracts
- primitive fact fetch planning
- grouped fetch normalization into atomic facts
- derived metric orchestration against Metric Engine adapters
- row assembly
- scope-level aggregation

## What it does not own

- natural language interpretation
- business policies (ranking/classification/"worst")
- data-source-specific adapters
- domain-specific semantics such as restaurants, dishes, suppliers, etc.

## Running tests

```bash
pip install -e .[dev]
pytest
```

## Documentation

- Source docs: [docs/](docs/)
- API and usage docs are built with Sphinx for Read the Docs compatibility.
