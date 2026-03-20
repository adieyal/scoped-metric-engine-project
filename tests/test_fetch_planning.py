from datetime import date

from scoped_metric_engine.execution_context import ExecutionContext
from scoped_metric_engine.fact_key import FactKey
from scoped_metric_engine.fetch_plan import FactDemand, FetchPlanner
from scoped_metric_engine.scope import ResolutionGrain, Scope
from scoped_metric_engine.slice import Slice


def test_fetch_planner_batches_by_family_and_scope():
    scope = Scope(
        slice=Slice(entity_ids=(1,), start_date=date(2026, 2, 1), end_date=date(2026, 2, 28)),
        resolution_grain=ResolutionGrain(("item",)),
        execution_context=ExecutionContext(currency="USD"),
    )
    planner = FetchPlanner()
    demands = [
        FactDemand(FactKey("units_sold", scope), "sales"),
        FactDemand(FactKey("revenue", scope), "sales"),
        FactDemand(FactKey("cogs", scope), "costs"),
    ]
    plan = planner.build_fetch_plan(demands)
    assert len(plan.requests) == 2
    sales_request = [r for r in plan.requests if r.family == "sales"][0]
    assert sales_request.metrics == ("revenue", "units_sold")
