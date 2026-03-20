from scoped_metric_engine.compute import compute_metrics_for_row
from scoped_metric_engine.fact import Fact
from scoped_metric_engine.fact_key import FactKey
from scoped_metric_engine.fact_store import InMemoryFactStore


def test_compute_metrics_for_row_uses_batch_metric_engine(grouped_scope):
    store = InMemoryFactStore()
    gk = grouped_scope.canonicalized().resolution_grain and None
    from tests.conftest import FakeMetricEngine, FakeFinancialValue, FakeProv
    # scalar row for simpler context
    scope = grouped_scope
    group_key = None
    store.put(Fact(FactKey("revenue", scope, group_key), 100))
    store.put(Fact(FactKey("cogs", scope, group_key), 60))
    facts = compute_metrics_for_row(
        scope=scope,
        group_key=group_key,
        metrics=["revenue", "cogs", "gross_profit", "gross_margin"],
        metric_engine=FakeMetricEngine(),
        fact_store=store,
    )
    result = {f.key.metric: f for f in facts}
    assert result["gross_profit"].value == 40
    assert result["gross_margin"].value == 0.4
    assert result["gross_margin"].calculation_provenance.op == "calc:gross_margin"
