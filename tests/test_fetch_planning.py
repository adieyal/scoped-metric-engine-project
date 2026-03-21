from datetime import date

from scoped_metric_engine.execution_context import ExecutionContext
from scoped_metric_engine.fact_key import FactKey
from scoped_metric_engine.fetch_plan import FactDemand, FetchPlanner
from scoped_metric_engine.scope import ResolutionGrain, Scope
from scoped_metric_engine.slice import Slice


def _scope(
    *,
    entity_ids=(1,),
    start_date=date(2025, 1, 1),
    end_date=date(2025, 1, 31),
    filters=(),
    dimensions=(),
    currency=None,
):
    return Scope(
        slice=Slice(
            entity_ids=entity_ids,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
        ).canonicalized(),
        resolution_grain=ResolutionGrain(dimensions=dimensions),
        execution_context=ExecutionContext(currency=currency),
    )


def test_build_fetch_plan_groups_metrics_by_fetch_shape():
    scope = _scope()
    planner = FetchPlanner()

    demands = [
        FactDemand(key=FactKey(metric="revenue", scope=scope), family="sales"),
        FactDemand(key=FactKey(metric="cogs", scope=scope), family="sales"),
    ]

    plan = planner.build_fetch_plan(demands)

    assert len(plan.requests) == 1
    request = plan.requests[0]
    assert request.family == "sales"
    assert request.metrics == ("cogs", "revenue")
    assert plan.covered_demands[request] == set(demands)


def test_build_fetch_plan_separates_different_families():
    scope = _scope()
    planner = FetchPlanner()

    demands = [
        FactDemand(key=FactKey(metric="revenue", scope=scope), family="sales"),
        FactDemand(key=FactKey(metric="on_hand_qty", scope=scope), family="inventory"),
    ]

    plan = planner.build_fetch_plan(demands)

    assert len(plan.requests) == 2
    assert {(r.family, r.metrics) for r in plan.requests} == {
        ("sales", ("revenue",)),
        ("inventory", ("on_hand_qty",)),
    }


def test_build_fetch_plan_separates_different_scopes():
    planner = FetchPlanner()
    scope_a = _scope(entity_ids=(1,))
    scope_b = _scope(entity_ids=(2,))

    demands = [
        FactDemand(key=FactKey(metric="revenue", scope=scope_a), family="sales"),
        FactDemand(key=FactKey(metric="cogs", scope=scope_b), family="sales"),
    ]

    plan = planner.build_fetch_plan(demands)

    assert len(plan.requests) == 2


def test_build_fetch_plan_separates_different_grains():
    planner = FetchPlanner()
    ungrouped = _scope(dimensions=())
    grouped = _scope(dimensions=("recipe_id",))

    demands = [
        FactDemand(key=FactKey(metric="revenue", scope=ungrouped), family="sales"),
        FactDemand(key=FactKey(metric="cogs", scope=grouped), family="sales"),
    ]

    plan = planner.build_fetch_plan(demands)

    assert len(plan.requests) == 2


def test_build_fetch_plan_separates_different_execution_contexts():
    planner = FetchPlanner()
    usd_scope = _scope(currency="USD")
    ils_scope = _scope(currency="ILS")

    demands = [
        FactDemand(key=FactKey(metric="revenue", scope=usd_scope), family="sales"),
        FactDemand(key=FactKey(metric="cogs", scope=ils_scope), family="sales"),
    ]

    plan = planner.build_fetch_plan(demands)

    assert len(plan.requests) == 2


def test_build_fetch_plan_deduplicates_duplicate_metric_demands_with_same_shape():
    planner = FetchPlanner()
    scope = _scope()

    demand_a = FactDemand(key=FactKey(metric="revenue", scope=scope), family="sales")
    demand_b = FactDemand(key=FactKey(metric="revenue", scope=scope), family="sales")

    plan = planner.build_fetch_plan([demand_a, demand_b])

    assert len(plan.requests) == 1
    request = plan.requests[0]
    assert request.metrics == ("revenue",)
    assert plan.covered_demands[request] == {demand_b} or plan.covered_demands[request] == {demand_a}


def test_build_fetch_plan_is_deterministic_regardless_of_input_order():
    planner = FetchPlanner()
    scope = _scope()

    demands_a = [
        FactDemand(key=FactKey(metric="cogs", scope=scope), family="sales"),
        FactDemand(key=FactKey(metric="revenue", scope=scope), family="sales"),
    ]
    demands_b = list(reversed(demands_a))

    plan_a = planner.build_fetch_plan(demands_a)
    plan_b = planner.build_fetch_plan(demands_b)

    assert plan_a.requests == plan_b.requests
    assert plan_a.requests[0].metrics == ("cogs", "revenue")
