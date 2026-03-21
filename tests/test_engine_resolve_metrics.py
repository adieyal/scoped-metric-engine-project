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
    # Primitive zero-filled values are raw scalars
    assert gamma.metrics["units_sold"] == 0
    assert gamma.metrics["revenue"] == 0
    # cogs is not zero-filled (zero_fill_if_eligible_but_absent=False), but
    # fetcher provides cogs=0 for Gamma, so it comes from the fetch
    assert gamma.metrics["cogs"] == 0
    # Derived metrics are FinancialValue objects; gross_margin with 0 revenue → None
    gm = gamma.metrics["gross_margin"]
    assert gm.is_none()


def test_resolve_metrics_observed_mode_only_returns_observed_rows(engine, grouped_scope):
    result = engine.resolve_metrics(
        ResolveMetricsRequest(
            scope=grouped_scope,
            metrics=["units_sold", "revenue"],
            population=PopulationSpec("observed"),
        )
    )
    assert len(result.rows) == 2


def test_resolve_metrics_transitive_dependency_discovery(engine, grouped_scope):
    """Verify that requesting a derived metric with transitive deps fetches all primitives."""
    result = engine.resolve_metrics(
        ResolveMetricsRequest(
            scope=grouped_scope,
            metrics=["gross_margin"],
            population=PopulationSpec("observed"),
        )
    )
    # 3 rows: Alpha and Beta from sales fetcher, Gamma from costs fetcher.
    # inputs_needed_for discovers both revenue and cogs as leaf dependencies.
    assert len(result.rows) == 3
    alpha = [r for r in result.rows if r.dimensions["name"] == "Alpha"][0]
    gm = alpha.metrics["gross_margin"]
    assert not gm.is_none()
