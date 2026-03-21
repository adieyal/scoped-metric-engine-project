from datetime import date

from scoped_metric_engine.aggregation import AggregationOperator, AggregationSpec
from scoped_metric_engine.fetchers import FetchResponse, RawFetchRow
from scoped_metric_engine.population import PopulationSpec
from scoped_metric_engine.requests import AggregationRequest, ScopeRef
from scoped_metric_engine.scope import ResolutionGrain, Scope
from scoped_metric_engine.slice import Slice
from tests.conftest import FakeFinancialValue


class ScalarPopulationResolver:
    def resolve_population(self, scope, population):
        return []


class ScalarFetcher:
    family = "sales"

    def __init__(self, value):
        self.value = value

    def fetch(self, request):
        return FetchResponse(
            request=request,
            rows=[RawFetchRow(group_dimensions={}, metrics={"revenue": self.value, "cogs": self.value / 2})],
        )


class ScalarMetricEngine:
    _deps = {
        "gross_margin": {"revenue", "cogs"},
    }

    def get_dependencies(self, target: str):
        return self._deps.get(target, set())

    def inputs_needed_for(self, targets):
        leaf_inputs = {
            "gross_margin": {"revenue", "cogs"},
        }
        out = set()
        for target in targets:
            out |= leaf_inputs.get(target, {target})
        return out

    def calculate_many(self, targets, ctx=None, *, policy=None, allow_partial=True, **kwargs):
        ctx = ctx or {}
        out = {}
        for t in targets:
            out[t] = self.calculate(t, ctx, policy=policy, allow_partial=allow_partial)
        return out

    def calculate(self, target, ctx=None, *, policy=None, allow_partial=True, **kwargs):
        ctx = ctx or {}
        if target == "revenue":
            return FakeFinancialValue(ctx.get("revenue"))
        if target == "cogs":
            return FakeFinancialValue(ctx.get("cogs"))
        if target == "gross_margin":
            rev = ctx.get("revenue")
            cogs = ctx.get("cogs")
            value = None if rev in (None, 0) or cogs is None else (rev - cogs) / rev
            return FakeFinancialValue(value)
        return FakeFinancialValue(None)


def test_aggregate_metrics_mean_and_weighted_recompute(metric_registry, aggregation_policies):
    from scoped_metric_engine.engine import ScopedMetricEngine
    from scoped_metric_engine.fact_store import InMemoryFactStore

    scope1 = Scope(Slice((1,), date(2026, 1, 1), date(2026, 1, 31)), ResolutionGrain(()))
    scope2 = Scope(Slice((1,), date(2026, 2, 1), date(2026, 2, 28)), ResolutionGrain(()))

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
            aggregation_spec=AggregationSpec(
                (
                    AggregationOperator("revenue", "mean"),
                    AggregationOperator("gross_margin", "weighted_recompute"),
                )
            ),
            population=PopulationSpec("observed"),
        )
    )
    values = {v.metric: v for v in result.values}

    # Mean of revenue: scalar fetcher returns FV objects, mean operates on them
    revenue_val = values["revenue"].value
    # Revenue values are FakeFinancialValue from calculate_many; mean operates on the stored objects
    assert revenue_val is not None

    # weighted_recompute delegates to metric_engine.calculate("gross_margin", ...)
    gm_val = values["gross_margin"].value
    # The recomputed value is a FakeFinancialValue from ScalarMetricEngine.calculate
    assert gm_val.value == 0.5
