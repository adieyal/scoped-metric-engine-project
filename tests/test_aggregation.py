from scoped_metric_engine.aggregation import (
    AggregationInputValue,
    AggregationOperator,
    aggregate_values,
)


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
            "revenue": [AggregationInputValue("revenue", 100, "complete"), AggregationInputValue("revenue", 50, "complete")],
            "cogs": [AggregationInputValue("cogs", 60, "complete"), AggregationInputValue("cogs", 20, "complete")],
        },
    )
    assert round(value, 4) == round((150 - 80) / 150, 4)
    assert completeness == "complete"
    assert issues == []
