from scoped_metric_engine.population import PopulationSpec


def test_population_modes_supported(engine, grouped_scope):
    observed = engine._population_resolver.resolve_population(grouped_scope, PopulationSpec("observed"))
    eligible = engine._population_resolver.resolve_population(grouped_scope, PopulationSpec("eligible"))
    assert observed == []
    assert len(eligible) == 3
