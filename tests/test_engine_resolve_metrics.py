from scoped_metric_engine.population import PopulationSpec
from scoped_metric_engine.requests import ResolveMetricsRequest


def test_resolve_metrics_includes_zero_filled_eligible_rows(engine, grouped_scope):
    result = engine.resolve_metrics(
        ResolveMetricsRequest(
            scope=grouped_scope,
            metrics=["units_sold", "revenue", "cogs", "gross_profit", "gross_margin"],
            population=PopulationSpec("eligible"),
        )
    )
    assert len(result.rows) == 3
    gamma = [r for r in result.rows if r.dimensions["name"] == "Gamma"][0]
    assert gamma.metrics["units_sold"] == 0
    assert gamma.metrics["revenue"] == 0
    assert gamma.metrics["cogs"] == 0
    assert gamma.metrics["gross_margin"] is None


def test_resolve_metrics_observed_mode_only_returns_observed_rows(engine, grouped_scope):
    result = engine.resolve_metrics(
        ResolveMetricsRequest(
            scope=grouped_scope,
            metrics=["units_sold", "revenue"],
            population=PopulationSpec("observed"),
        )
    )
    assert len(result.rows) == 2
