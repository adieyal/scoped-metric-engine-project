from scoped_metric_engine.compute import compute_metrics_for_row
from scoped_metric_engine.fact import Fact
from scoped_metric_engine.fact_key import FactKey
from scoped_metric_engine.fact_store import InMemoryFactStore
from tests.conftest import FakeMetricEngine


def test_compute_metrics_for_row_uses_batch_metric_engine(grouped_scope):
    store = InMemoryFactStore()
    scope = grouped_scope
    group_key = None
    store.put(Fact(FactKey("revenue", scope, group_key), 100))
    store.put(Fact(FactKey("cogs", scope, group_key), 60))
    facts = compute_metrics_for_row(
        scope=scope,
        group_key=group_key,
        targets=["gross_profit", "gross_margin"],
        metric_engine=FakeMetricEngine(),
        fact_store=store,
        context_metrics=["revenue", "cogs", "gross_profit", "gross_margin"],
    )
    result = {f.key.metric: f for f in facts}
    # Derived facts preserve FinancialValue objects (not unwrapped scalars)
    assert result["gross_profit"].value.value == 40
    assert result["gross_margin"].value.value == 0.4
    assert result["gross_margin"].calculation_provenance.op == "calc:gross_margin"


def test_compute_preserves_financial_value_objects(grouped_scope):
    store = InMemoryFactStore()
    scope = grouped_scope
    group_key = None
    store.put(Fact(FactKey("revenue", scope, group_key), 100))
    store.put(Fact(FactKey("cogs", scope, group_key), 60))
    facts = compute_metrics_for_row(
        scope=scope,
        group_key=group_key,
        targets=["gross_profit"],
        metric_engine=FakeMetricEngine(),
        fact_store=store,
        context_metrics=["revenue", "cogs"],
    )
    gp = facts[0]
    assert hasattr(gp.value, "is_none")
    assert hasattr(gp.value, "get_provenance")
    assert not gp.value.is_none()
