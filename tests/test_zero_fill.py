from scoped_metric_engine.fact_key import FactKey
from scoped_metric_engine.population import PopulationSpec
from scoped_metric_engine.zero_fill import build_zero_filled_facts


def test_zero_fill_only_applies_to_configured_metrics(metric_registry, grouped_scope):
    population_rows = [
        row for row in [
            *([]),
        ]
    ]
    # use resolver fixture behavior indirectly
    from tests.conftest import FakePopulationResolver

    rows = FakePopulationResolver().resolve_population(grouped_scope, PopulationSpec("eligible"))
    existing = {FactKey("units_sold", grouped_scope, rows[0].group_key)}
    facts = build_zero_filled_facts(
        scope=grouped_scope,
        primitive_metrics=["units_sold", "revenue", "cogs"],
        population_rows=rows,
        existing_fact_keys=existing,
        metric_registry=metric_registry,
        population_mode="eligible",
    )
    zero_metrics = {(f.key.metric, f.key.group_key) for f in facts}
    assert ("cogs", rows[1].group_key) not in zero_metrics
    assert ("revenue", rows[1].group_key) in zero_metrics
