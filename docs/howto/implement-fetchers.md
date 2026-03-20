# Implement Primitive Fetchers

Each family needs a class implementing `fetch(request: FetchRequest) -> FetchResponse`.

```python
from scoped_metric_engine import FetchResponse, FetchRequest, RawFetchRow


class SalesFetcher:
    family = "sales"

    def fetch(self, request: FetchRequest) -> FetchResponse:
        return FetchResponse(
            request=request,
            rows=[
                RawFetchRow(
                    group_dimensions={"item_id": 1},
                    dimensions={"name": "A"},
                    metrics={"revenue": 1000},
                )
            ],
        )
```

The engine passes a request containing:

- `family`
- `slice`
- `resolution_grain`
- `execution_context`
- `metrics` tuple requested for that family

Return only the requested metrics when possible to keep payloads smaller.

