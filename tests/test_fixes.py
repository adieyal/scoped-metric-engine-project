"""Tests covering the targeted fixes applied to scoped_metric_engine."""

from __future__ import annotations

from datetime import date

from scoped_metric_engine.aggregation import (
    AggregationOperator,
    AggregationSpec,
)
from scoped_metric_engine.compute import compute_metrics_for_row
from scoped_metric_engine.engine import ScopedMetricEngine
from scoped_metric_engine.fact import Fact
from scoped_metric_engine.fact_key import FactKey
from scoped_metric_engine.fact_store import InMemoryFactStore
from scoped_metric_engine.fetch_request import FetchRequest
from scoped_metric_engine.fetchers import FetchResponse, RawFetchRow
from scoped_metric_engine.normalization import normalize_fetch_response_to_facts
from scoped_metric_engine.population import PopulationSpec
from scoped_metric_engine.requests import AggregationRequest, ResolveMetricsRequest, ScopeRef
from scoped_metric_engine.scope import ResolutionGrain, Scope
from scoped_metric_engine.slice import Slice
from tests.conftest import FakeMetricEngine

# ---------------------------------------------------------------------------
# Fix 1: Unsupported metrics reported once and excluded from row assembly
# ---------------------------------------------------------------------------


def test_unsupported_metrics_reported_and_excluded_from_rows(engine, grouped_scope):
    result = engine.resolve_metrics(
        ResolveMetricsRequest(
            scope=grouped_scope,
            metrics=["revenue", "nonexistent_metric"],
            population=PopulationSpec("observed"),
        )
    )
    # Issue reported for the unsupported metric
    unsupported_issues = [i for i in result.issues if i.code == "UNSUPPORTED_METRIC"]
    assert len(unsupported_issues) == 1
    assert "nonexistent_metric" in unsupported_issues[0].message

    # Rows should NOT contain the unsupported metric key
    for row in result.rows:
        assert "nonexistent_metric" not in row.metrics
        # The valid metric should still be present
        assert "revenue" in row.metrics


# ---------------------------------------------------------------------------
# Fix 2: Direct primitive requests fetch correctly even if inputs_needed_for
#         would omit them
# ---------------------------------------------------------------------------


def test_direct_primitive_requests_still_fetch(engine, grouped_scope):
    """Requesting a primitive metric directly should fetch it even if
    inputs_needed_for() does not return it (it only returns leaf inputs for
    derived metrics it knows about)."""
    result = engine.resolve_metrics(
        ResolveMetricsRequest(
            scope=grouped_scope,
            metrics=["units_sold"],
            population=PopulationSpec("observed"),
        )
    )
    assert len(result.rows) > 0
    for row in result.rows:
        assert row.metrics["units_sold"] is not None


# ---------------------------------------------------------------------------
# Fix 3: Scalar scope row assembly works with group_key=None
# ---------------------------------------------------------------------------


class _ScalarPopResolver:
    def resolve_population(self, scope, population):
        return []


class _ScalarSalesFetcher:
    family = "sales"

    def fetch(self, request):
        return FetchResponse(
            request=request,
            rows=[RawFetchRow(group_dimensions={}, metrics={"revenue": 100, "units_sold": 10})],
        )


def test_scalar_scope_row_assembly_with_none_group_key(metric_registry, aggregation_policies):
    scope = Scope(
        Slice((1,), date(2026, 1, 1), date(2026, 1, 31)),
        ResolutionGrain(()),
    )
    engine = ScopedMetricEngine(
        metric_registry=metric_registry,
        fact_store=InMemoryFactStore(),
        fetchers_by_family={"sales": _ScalarSalesFetcher(), "costs": _ScalarSalesFetcher()},
        population_resolver=_ScalarPopResolver(),
        metric_engine=FakeMetricEngine(),
        aggregation_policy_registry=aggregation_policies,
    )
    result = engine.resolve_metrics(
        ResolveMetricsRequest(
            scope=scope,
            metrics=["revenue", "units_sold"],
            population=PopulationSpec("observed"),
        )
    )
    assert len(result.rows) == 1
    assert result.rows[0].group_key is None
    assert result.rows[0].metrics["revenue"] is not None


# ---------------------------------------------------------------------------
# Fix 4: Fetch request IDs are deterministic across calls
# ---------------------------------------------------------------------------


def test_fetch_request_id_is_deterministic(grouped_scope):
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
            RawFetchRow(
                group_dimensions={"item_id": 1},
                dimensions={"name": "Alpha"},
                metrics={"revenue": 100, "units_sold": 10},
            ),
        ],
    )
    facts1, _ = normalize_fetch_response_to_facts(grouped_scope, response, population_mode="observed")
    facts2, _ = normalize_fetch_response_to_facts(grouped_scope, response, population_mode="observed")

    id1 = facts1[0].resolution_provenance.fetch_request_id
    id2 = facts2[0].resolution_provenance.fetch_request_id
    assert id1 == id2
    # Should be a hex string, not empty
    assert len(id1) > 0


# ---------------------------------------------------------------------------
# Fix 5: Partial primitive inputs propagate partial completeness into derived
# ---------------------------------------------------------------------------


def test_partial_upstream_propagates_to_derived_facts(grouped_scope):
    store = InMemoryFactStore()
    scope = grouped_scope
    group_key = None

    # revenue is partial, cogs is complete
    store.put(Fact(FactKey("revenue", scope, group_key), 100, completeness="partial"))
    store.put(Fact(FactKey("cogs", scope, group_key), 60, completeness="complete"))

    facts = compute_metrics_for_row(
        scope=scope,
        group_key=group_key,
        targets=["gross_profit"],
        metric_engine=FakeMetricEngine(),
        fact_store=store,
        context_metrics=["revenue", "cogs"],
    )
    gp = {f.key.metric: f for f in facts}["gross_profit"]
    # The derived fact should be partial because an upstream input is partial
    assert gp.completeness == "partial"


def test_complete_upstream_gives_complete_derived(grouped_scope):
    store = InMemoryFactStore()
    scope = grouped_scope
    group_key = None

    store.put(Fact(FactKey("revenue", scope, group_key), 100, completeness="complete"))
    store.put(Fact(FactKey("cogs", scope, group_key), 60, completeness="complete"))

    facts = compute_metrics_for_row(
        scope=scope,
        group_key=group_key,
        targets=["gross_profit"],
        metric_engine=FakeMetricEngine(),
        fact_store=store,
        context_metrics=["revenue", "cogs"],
    )
    gp = {f.key.metric: f for f in facts}["gross_profit"]
    assert gp.completeness == "complete"


# ---------------------------------------------------------------------------
# Fix 7: Aggregation issues appear at both top-level and per-value
# ---------------------------------------------------------------------------


def test_aggregation_issues_at_top_level_and_per_value(metric_registry, aggregation_policies):
    scope1 = Scope(Slice((1,), date(2026, 1, 1), date(2026, 1, 31)), ResolutionGrain(()))
    scope2 = Scope(Slice((1,), date(2026, 2, 1), date(2026, 2, 28)), ResolutionGrain(()))

    engine = ScopedMetricEngine(
        metric_registry=metric_registry,
        fact_store=InMemoryFactStore(),
        fetchers_by_family={"sales": _ScalarSalesFetcher(), "costs": _ScalarSalesFetcher()},
        population_resolver=_ScalarPopResolver(),
        metric_engine=FakeMetricEngine(),
        aggregation_policy_registry=aggregation_policies,
    )

    # units_sold has no aggregation policy → should produce UNSUPPORTED_AGGREGATION
    result = engine.aggregate_metrics(
        AggregationRequest(
            scopes=[ScopeRef("s1", scope1), ScopeRef("s2", scope2)],
            metrics=["units_sold"],
            aggregation_spec=AggregationSpec((AggregationOperator("units_sold", "sum"),)),
            population=PopulationSpec("observed"),
        )
    )

    # Per-value issues
    units_value = [v for v in result.values if v.metric == "units_sold"][0]
    per_value_issues = [i for i in units_value.issues if i.code == "UNSUPPORTED_AGGREGATION"]
    assert len(per_value_issues) >= 1

    # Top-level issues should also contain the same aggregation issue
    top_level_agg_issues = [i for i in result.issues if i.code == "UNSUPPORTED_AGGREGATION"]
    assert len(top_level_agg_issues) >= 1
