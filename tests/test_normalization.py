from scoped_metric_engine.fetch_request import FetchRequest
from scoped_metric_engine.fetchers import FetchResponse, RawFetchRow
from scoped_metric_engine.normalization import normalize_fetch_response_to_facts


def test_normalization_creates_atomic_facts_and_dimensions(grouped_scope):
    request = FetchRequest(
        family="sales",
        slice=grouped_scope.slice,
        resolution_grain=grouped_scope.resolution_grain,
        execution_context=grouped_scope.execution_context,
        metrics=("revenue", "units_sold"),
    )
    response = FetchResponse(
        request=request,
        rows=[
            RawFetchRow(group_dimensions={"item_id": 1}, dimensions={"name": "Alpha"}, metrics={"revenue": 100, "units_sold": 10})
        ],
    )
    facts, row_dimensions = normalize_fetch_response_to_facts(grouped_scope, response, population_mode="observed")
    assert len(facts) == 2
    assert facts[0].resolution_provenance.origin == "fetched"
    assert list(row_dimensions.values())[0]["name"] == "Alpha"
