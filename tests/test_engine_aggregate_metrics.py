from datetime import date

from scoped_metric_engine.aggregation import AggregationOperator, AggregationSpec
from scoped_metric_engine.population import PopulationSpec
from scoped_metric_engine.requests import AggregationRequest, ScopeRef
from scoped_metric_engine.scope import ResolutionGrain, Scope
from scoped_metric_engine.slice import Slice


class ScalarPopulationResolver:
    def resolve_population(self, scope, population):
        return []


class ScalarFetcher:
    family = "sales"

    def __init__(self, value):
        self.value = value

    def fetch(self, request):
        from scoped_metric_engine.fetchers import FetchResponse, RawFetchRow
        return FetchResponse(request=request, rows=[RawFetchRow(group_dimensions={}, metrics={"revenue": self.value, "cogs": self.value / 2})])


class ScalarMetricEngine:
    def get_dependencies(self, metric_name: str):
        if metric_name == "gross_margin":
            return {"revenue", "cogs"}
        return set()

    def calculate_many(self, targets, ctx=None, allow_partial=True, policy=None):
        ctx = ctx or {}
        out = {}
        for t in targets:
            if t == "revenue":
                out[t] = type("FV", (), {"value": ctx.get("revenue"), "is_none": lambda self: self.value is None, "get_provenance": lambda self: None})()
            elif t == "cogs":
                out[t] = type("FV", (), {"value": ctx.get("cogs"), "is_none": lambda self: self.value is None, "get_provenance": lambda self: None})()
            elif t == "gross_margin":
                rev = ctx.get("revenue")
                cogs = ctx.get("cogs")
                value = None if rev in (None, 0) or cogs is None else (rev - cogs) / rev
                out[t] = type("FV", (), {"value": value, "is_none": lambda self: self.value is None, "get_provenance": lambda self: None})()
        return out


def test_aggregate_metrics_mean_and_weighted_recompute(metric_registry, aggregation_policies):
    from scoped_metric_engine.engine import ScopedMetricEngine
    from scoped_metric_engine.fact_store import InMemoryFactStore

    scope1 = Scope(Slice((1,), date(2026, 1, 1), date(2026, 1, 31)), ResolutionGrain(()))
    scope2 = Scope(Slice((1,), date(2026, 2, 1), date(2026, 2, 28)), ResolutionGrain(()))

    # same fetcher value is okay because scopes differ only for aggregation plumbing test
    engine = ScopedMetricEngine(
        metric_registry=metric_registry,
        fact_store=InMemoryFactStore(),
        fetchers_by_family={"sales": ScalarFetcher(100), "costs": ScalarFetcher(100)},
        population_resolver=ScalarPopulationResolver(),
        metric_engine=ScalarMetricEngine(),
        aggregation_policy_registry=aggregation_policies,
    )

    result = engine.aggregate_metrics(
        AggregationRequest(
            scopes=[ScopeRef("s1", scope1), ScopeRef("s2", scope2)],
            metrics=["revenue", "cogs", "gross_margin"],
            aggregation_spec=AggregationSpec((
                AggregationOperator("revenue", "mean"),
                AggregationOperator("gross_margin", "weighted_recompute"),
            )),
            population=PopulationSpec("observed"),
        )
    )
    values = {v.metric: v.value for v in result.values}
    assert values["revenue"] == 100
    assert values["gross_margin"] == 0.5
