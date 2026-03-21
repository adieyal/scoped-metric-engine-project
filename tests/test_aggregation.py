from scoped_metric_engine.aggregation import (
    AggregationInputValue,
    AggregationOperator,
    aggregate_values,
)
from scoped_metric_engine.requests import CalculationOptions
from tests.conftest import FakeMetricEngine


def test_additive_aggregation_sum(aggregation_policies):
    value, completeness, issues = aggregate_values(
        AggregationOperator("revenue", "sum"),
        [AggregationInputValue("revenue", 100, "complete"), AggregationInputValue("revenue", 50, "complete")],
        aggregation_policies.get("revenue"),
    )
    assert value == 150
    assert completeness == "complete"
    assert issues == []


def test_ratio_weighted_recompute(aggregation_policies):
    value, completeness, issues = aggregate_values(
        AggregationOperator("gross_margin", "weighted_recompute"),
        [],
        aggregation_policies.get("gross_margin"),
        recompute_inputs={
            "revenue": [
                AggregationInputValue("revenue", 100, "complete"),
                AggregationInputValue("revenue", 50, "complete"),
            ],
            "cogs": [AggregationInputValue("cogs", 60, "complete"), AggregationInputValue("cogs", 20, "complete")],
        },
        metric_engine=FakeMetricEngine(),
        calculation_options=CalculationOptions(),
    )
    # Delegates to metric_engine.calculate("gross_margin", ctx={"revenue": 150, "cogs": 80})
    # FakeMetricEngine computes (150 - 80) / 150
    assert round(value.value, 10) == round((150 - 80) / 150, 10)
    assert completeness == "complete"
    assert issues == []


def test_weighted_recompute_delegates_to_metric_engine(aggregation_policies):
    """Verify recompute uses metric_engine.calculate rather than hardcoded formulas."""
    engine = FakeMetricEngine()
    value, completeness, issues = aggregate_values(
        AggregationOperator("gross_margin", "weighted_recompute"),
        [],
        aggregation_policies.get("gross_margin"),
        recompute_inputs={
            "revenue": [AggregationInputValue("revenue", 200, "complete")],
            "cogs": [AggregationInputValue("cogs", 100, "complete")],
        },
        metric_engine=engine,
        calculation_options=CalculationOptions(),
    )
    # Result is a FakeFinancialValue from metric_engine.calculate
    assert hasattr(value, "is_none")
    assert not value.is_none()
    assert value.value == 0.5
