from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from scoped_metric_engine.aggregation import AggregationPolicyRegistry, MetricAggregationPolicy
from scoped_metric_engine.engine import ScopedMetricEngine
from scoped_metric_engine.fact_store import InMemoryFactStore
from scoped_metric_engine.fetchers import FetchResponse, PrimitiveFactFetcher, RawFetchRow
from scoped_metric_engine.group_key import GroupKey
from scoped_metric_engine.metric_metadata import (
    PrimitiveMetricSemantics,
    ScopedMetricMetadata,
    ScopedMetricRegistry,
)
from scoped_metric_engine.population import PopulationResolver, PopulationRow, PopulationSpec
from scoped_metric_engine.scope import ResolutionGrain, Scope
from scoped_metric_engine.slice import Slice


@dataclass
class FakeProv:
    op: str


class FakeFinancialValue:
    def __init__(self, value, prov=None):
        self.value = value
        self._prov = prov

    def is_none(self):
        return self.value is None

    def get_provenance(self):
        return self._prov


class FakeMetricEngine:
    def get_dependencies(self, metric_name: str) -> set[str]:
        mapping = {
            "gross_profit": {"revenue", "cogs"},
            "gross_margin": {"gross_profit", "revenue", "cogs"},
        }
        return mapping.get(metric_name, set())

    def calculate_many(self, targets: set[str], ctx=None, allow_partial=True, policy=None):
        ctx = ctx or {}
        out = {}
        for target in targets:
            if target == "units_sold":
                out[target] = FakeFinancialValue(ctx.get("units_sold"), FakeProv("input:units_sold"))
            elif target == "revenue":
                out[target] = FakeFinancialValue(ctx.get("revenue"), FakeProv("input:revenue"))
            elif target == "cogs":
                out[target] = FakeFinancialValue(ctx.get("cogs"), FakeProv("input:cogs"))
            elif target == "gross_profit":
                revenue = ctx.get("revenue")
                cogs = ctx.get("cogs")
                value = None if revenue is None or cogs is None else revenue - cogs
                out[target] = FakeFinancialValue(value, FakeProv("calc:gross_profit"))
            elif target == "gross_margin":
                revenue = ctx.get("revenue")
                cogs = ctx.get("cogs")
                if revenue in (None, 0) or cogs is None:
                    value = None
                else:
                    value = (revenue - cogs) / revenue
                out[target] = FakeFinancialValue(value, FakeProv("calc:gross_margin"))
            else:
                out[target] = FakeFinancialValue(None, FakeProv(f"calc:{target}"))
        return out


class FakePopulationResolver:
    def resolve_population(self, scope: Scope, population: PopulationSpec):
        if scope.resolution_grain.dimensions == ():
            return []
        if population.mode == "observed":
            return []
        return [
            PopulationRow(GroupKey.from_mapping({"item_id": 1}), {"name": "Alpha"}),
            PopulationRow(GroupKey.from_mapping({"item_id": 2}), {"name": "Beta"}),
            PopulationRow(GroupKey.from_mapping({"item_id": 3}), {"name": "Gamma"}),
        ]


class SalesFetcher:
    family = "sales"

    def fetch(self, request):
        return FetchResponse(
            request=request,
            rows=[
                RawFetchRow(
                    group_dimensions={"item_id": 1},
                    dimensions={"name": "Alpha"},
                    metrics={"units_sold": 10, "revenue": 100},
                ),
                RawFetchRow(
                    group_dimensions={"item_id": 2},
                    dimensions={"name": "Beta"},
                    metrics={"units_sold": 5, "revenue": 40},
                ),
            ],
        )


class CostsFetcher:
    family = "costs"

    def fetch(self, request):
        return FetchResponse(
            request=request,
            rows=[
                RawFetchRow(
                    group_dimensions={"item_id": 1},
                    dimensions={"name": "Alpha"},
                    metrics={"cogs": 60},
                ),
                RawFetchRow(
                    group_dimensions={"item_id": 2},
                    dimensions={"name": "Beta"},
                    metrics={"cogs": 25},
                ),
                RawFetchRow(
                    group_dimensions={"item_id": 3},
                    dimensions={"name": "Gamma"},
                    metrics={"cogs": 0},
                ),
            ],
        )


@pytest.fixture
def metric_registry():
    return ScopedMetricRegistry(
        {
            "units_sold": ScopedMetricMetadata(
                "units_sold",
                "primitive",
                family="sales",
                value_type="count",
                semantics=PrimitiveMetricSemantics(zero_fill_if_eligible_but_absent=True),
            ),
            "revenue": ScopedMetricMetadata(
                "revenue",
                "primitive",
                family="sales",
                value_type="currency",
                semantics=PrimitiveMetricSemantics(zero_fill_if_eligible_but_absent=True),
            ),
            "cogs": ScopedMetricMetadata(
                "cogs",
                "primitive",
                family="costs",
                value_type="currency",
                semantics=PrimitiveMetricSemantics(zero_fill_if_eligible_but_absent=False),
            ),
            "gross_profit": ScopedMetricMetadata("gross_profit", "derived", value_type="currency"),
            "gross_margin": ScopedMetricMetadata("gross_margin", "derived", value_type="ratio"),
        }
    )


@pytest.fixture
def aggregation_policies():
    return AggregationPolicyRegistry(
        {
            "revenue": MetricAggregationPolicy("revenue", supported_ops=("sum", "mean", "min", "max")),
            "gross_margin": MetricAggregationPolicy(
                "gross_margin",
                supported_ops=("mean", "weighted_recompute"),
                recompute_from=("revenue", "cogs"),
            ),
            "cogs": MetricAggregationPolicy("cogs", supported_ops=("sum", "mean", "min", "max")),
        }
    )


@pytest.fixture
def grouped_scope():
    return Scope(
        slice=Slice(entity_ids=(2, 1), start_date=date(2026, 2, 1), end_date=date(2026, 2, 28), filters=(("b", 2), ("a", 1))),
        resolution_grain=ResolutionGrain(("item",)),
    )


@pytest.fixture
def scalar_scope():
    return Scope(
        slice=Slice(entity_ids=(1,), start_date=date(2026, 2, 1), end_date=date(2026, 2, 28)),
        resolution_grain=ResolutionGrain(()),
    )


@pytest.fixture
def engine(metric_registry, aggregation_policies):
    return ScopedMetricEngine(
        metric_registry=metric_registry,
        fact_store=InMemoryFactStore(),
        fetchers_by_family={"sales": SalesFetcher(), "costs": CostsFetcher()},
        population_resolver=FakePopulationResolver(),
        metric_engine=FakeMetricEngine(),
        aggregation_policy_registry=aggregation_policies,
    )
