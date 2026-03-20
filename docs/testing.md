# Testing

Run the test suite:

```bash
pip install -e .[dev]
pytest
```

Target specific behavior:

- metric resolution: `tests/test_engine_resolve_metrics.py`
- aggregation behavior: `tests/test_engine_aggregate_metrics.py`
- zero-fill: `tests/test_zero_fill.py`

