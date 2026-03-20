# Contributing

This package is intentionally small and opinionated. To contribute:

1. Add or adjust tests in `tests/`.
2. Keep behavior changes backward-compatible unless a migration is documented.
3. Run `pytest` before opening a PR.
4. Preserve registry/fetcher contract shapes when updating interfaces.

## Useful commands

- `pytest`
- `python -m pip install -e .[dev]`
