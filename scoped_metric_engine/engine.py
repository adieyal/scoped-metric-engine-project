from __future__ import annotations

from collections.abc import Mapping, Sequence

from .aggregation import (
    AggregationInputValue,
    AggregationPolicyRegistry,
    aggregate_values,
)
from .compute import compute_metrics_for_row
from .dependency_resolver import MetricEngineAdapter
from .exceptions import UnsupportedAggregationError
from .fact_key import FactKey
from .fact_store import FactStore
from .fetch_plan import FactDemand, FetchPlanner
from .fetchers import PrimitiveFactFetcher
from .group_key import GroupKey
from .issues import ResolutionIssue
from .metric_metadata import ScopedMetricRegistry
from .normalization import normalize_fetch_response_to_facts
from .population import PopulationResolver, PopulationRow
from .requests import AggregationRequest, ResolveMetricsRequest
from .results import AggregatedMetricResult, AggregatedMetricValue, ResolvedMetricTable
from .row_assembly import assemble_rows
from .scope import Scope
from .zero_fill import build_zero_filled_facts


class ScopedMetricEngine:
    def __init__(
        self,
        metric_registry: ScopedMetricRegistry,
        fact_store: FactStore,
        fetchers_by_family: Mapping[str, PrimitiveFactFetcher],
        population_resolver: PopulationResolver,
        metric_engine: MetricEngineAdapter,
        aggregation_policy_registry: AggregationPolicyRegistry,
    ) -> None:
        self._metric_registry = metric_registry
        self._fact_store = fact_store
        self._fetchers_by_family = dict(fetchers_by_family)
        self._population_resolver = population_resolver
        self._metric_engine = metric_engine
        self._aggregation_policy_registry = aggregation_policy_registry
        self._fetch_planner = FetchPlanner()

    def resolve_metrics(self, request: ResolveMetricsRequest) -> ResolvedMetricTable:
        scope = request.scope.canonicalized()
        scope.validate()

        issues: list[ResolutionIssue] = []
        population_rows = list(self._population_resolver.resolve_population(scope, request.population))
        population_by_key = {row.group_key: row for row in population_rows}

        primitive_metrics, valid_metrics, metric_issues = self._classify_and_validate_metrics(request.metrics)
        issues.extend(metric_issues)

        required_primitive_metrics = self._discover_required_primitive_metrics(valid_metrics, primitive_metrics)
        demands = self._build_demands(scope, required_primitive_metrics)
        fetch_plan = self._fetch_planner.build_fetch_plan(demands)

        inferred_row_dimensions: dict[GroupKey, dict[str, object]] = {}
        observed_group_keys: set[GroupKey] = set()

        for fetch_request in fetch_plan.requests:
            fetcher = self._fetchers_by_family.get(fetch_request.family)
            if fetcher is None:
                issues.append(
                    ResolutionIssue(
                        code="UNSUPPORTED_FETCH_FAMILY",
                        message=f"No fetcher registered for family '{fetch_request.family}'",
                    )
                )
                continue

            response = fetcher.fetch(fetch_request)
            issues.extend(response.issues)
            facts, row_dimensions = normalize_fetch_response_to_facts(
                scope,
                response,
                population_mode=request.population.mode,
            )
            self._fact_store.put_many(facts)
            inferred_row_dimensions.update(row_dimensions)
            observed_group_keys.update(row_dimensions.keys())

        if request.population.mode == "eligible":
            existing_fact_keys = {
                FactKey(metric=m, scope=scope, group_key=row.group_key)
                for row in population_rows
                for m in required_primitive_metrics
                if self._fact_store.has(FactKey(metric=m, scope=scope, group_key=row.group_key))
            }
            zero_filled = build_zero_filled_facts(
                scope=scope,
                primitive_metrics=required_primitive_metrics,
                population_rows=population_rows,
                existing_fact_keys=existing_fact_keys,
                metric_registry=self._metric_registry,
                population_mode=request.population.mode,
            )
            self._fact_store.put_many(zero_filled)

        group_keys = self._resolve_group_keys(
            scope=scope,
            population_mode=request.population.mode,
            population_rows=population_rows,
            observed_group_keys=observed_group_keys,
        )

        derived_metrics = sorted(m for m in valid_metrics if self._metric_registry.get(m).kind == "derived")
        context_metrics = sorted(set(valid_metrics) | set(required_primitive_metrics))
        for group_key in group_keys:
            derived_facts = compute_metrics_for_row(
                scope=scope,
                group_key=group_key,
                targets=derived_metrics,
                context_metrics=context_metrics,
                metric_engine=self._metric_engine,
                fact_store=self._fact_store,
                allow_partial=request.calculation_options.allow_partial,
                policy=request.calculation_options.policy,
                population_mode=request.population.mode,
            )
            self._fact_store.put_many(derived_facts)

        row_dimensions = self._merge_row_dimensions(
            group_keys=group_keys,
            population_by_key=population_by_key,
            inferred_row_dimensions=inferred_row_dimensions,
        )

        rows = assemble_rows(
            scope=scope,
            group_keys=group_keys,
            row_dimensions=row_dimensions,
            metrics=valid_metrics,
            fact_store=self._fact_store,
        )

        return ResolvedMetricTable(scope=scope, population=request.population, rows=rows, issues=issues)

    def aggregate_metrics(self, request: AggregationRequest) -> AggregatedMetricResult:
        issues: list[ResolutionIssue] = []
        resolved_tables: dict[str, ResolvedMetricTable] = {}

        for scope_ref in request.scopes:
            resolved_tables[scope_ref.label] = self.resolve_metrics(
                ResolveMetricsRequest(
                    scope=scope_ref.scope,
                    metrics=request.metrics,
                    population=request.population,
                    calculation_options=request.calculation_options,
                )
            )
            issues.extend(resolved_tables[scope_ref.label].issues)

        values: list[AggregatedMetricValue] = []
        for operator in request.aggregation_spec.operators:
            policy = self._aggregation_policy_registry.get(operator.metric)
            per_scope_values = [
                AggregationInputValue(
                    metric=operator.metric,
                    value=self._extract_scalar_value(resolved_tables[scope_ref.label], operator.metric),
                    completeness=self._extract_scalar_completeness(resolved_tables[scope_ref.label], operator.metric),
                )
                for scope_ref in request.scopes
            ]

            recompute_inputs = None
            if operator.op == "weighted_recompute" and policy is not None and policy.recompute_from:
                recompute_inputs = {
                    metric_name: [
                        AggregationInputValue(
                            metric=metric_name,
                            value=self._extract_scalar_value(resolved_tables[scope_ref.label], metric_name),
                            completeness=self._extract_scalar_completeness(
                                resolved_tables[scope_ref.label], metric_name
                            ),
                        )
                        for scope_ref in request.scopes
                    ]
                    for metric_name in policy.recompute_from
                }

            value, completeness, metric_issues = aggregate_values(
                operator=operator,
                values=per_scope_values,
                policy=policy,
                recompute_inputs=recompute_inputs,
                metric_engine=self._metric_engine,
                calculation_options=request.calculation_options,
            )
            issues.extend(metric_issues)
            values.append(
                AggregatedMetricValue(
                    metric=operator.metric,
                    value=value,
                    completeness=completeness,
                    issues=metric_issues,
                )
            )

        return AggregatedMetricResult(
            scopes=request.scopes,
            population=request.population,
            values=values,
            issues=issues,
        )

    def _classify_and_validate_metrics(
        self, metrics: Sequence[str]
    ) -> tuple[list[str], list[str], list[ResolutionIssue]]:
        primitive: list[str] = []
        all_valid: list[str] = []
        issues: list[ResolutionIssue] = []
        for metric in metrics:
            if not self._metric_registry.has(metric):
                issues.append(ResolutionIssue(code="UNSUPPORTED_METRIC", message=f"Unsupported metric '{metric}'"))
                continue
            all_valid.append(metric)
            metadata = self._metric_registry.get(metric)
            if metadata.kind == "primitive":
                primitive.append(metric)
        return primitive, all_valid, issues

    def _discover_required_primitive_metrics(
        self, valid_metrics: Sequence[str], primitive_metrics: Sequence[str]
    ) -> list[str]:
        needed = self._metric_engine.inputs_needed_for(set(valid_metrics))
        # Union with explicitly requested primitives so that direct primitive
        # requests are always fetched even if inputs_needed_for() omits them.
        needed = needed | set(primitive_metrics)
        primitives: list[str] = []
        for metric in sorted(needed):
            if self._metric_registry.has(metric):
                metadata = self._metric_registry.get(metric)
                if metadata.kind == "primitive":
                    primitives.append(metric)
        return primitives

    def _build_demands(self, scope: Scope, primitive_metrics: Sequence[str]) -> list[FactDemand]:
        demands: list[FactDemand] = []
        for metric in primitive_metrics:
            metadata = self._metric_registry.get(metric)
            if not metadata.family:
                continue
            demands.append(FactDemand(key=FactKey(metric=metric, scope=scope, group_key=None), family=metadata.family))
        return demands

    def _resolve_group_keys(
        self,
        scope: Scope,
        population_mode: str,
        population_rows: Sequence[PopulationRow],
        observed_group_keys: set[GroupKey],
    ) -> list[GroupKey | None]:
        if not scope.resolution_grain.dimensions:
            return [None]
        if population_mode == "eligible":
            return [row.group_key for row in population_rows]
        return sorted(observed_group_keys, key=lambda gk: gk.dimensions)

    def _merge_row_dimensions(
        self,
        group_keys: Sequence[GroupKey | None],
        population_by_key: Mapping[GroupKey, PopulationRow],
        inferred_row_dimensions: Mapping[GroupKey, dict[str, object]],
    ) -> dict[GroupKey | None, dict[str, object]]:
        merged: dict[GroupKey | None, dict[str, object]] = {}
        for group_key in group_keys:
            dimensions = {}
            if group_key in population_by_key:
                dimensions.update(population_by_key[group_key].dimensions)
            dimensions.update(inferred_row_dimensions.get(group_key, {}))
            merged[group_key] = dimensions
        return merged

    def _extract_scalar_value(self, table: ResolvedMetricTable, metric: str):
        if len(table.rows) != 1:
            raise UnsupportedAggregationError("Aggregation over grouped rows is not supported in v1")
        value = table.rows[0].metrics[metric]
        return _unwrap_numeric(value)

    def _extract_scalar_completeness(self, table: ResolvedMetricTable, metric: str):
        if len(table.rows) != 1:
            raise UnsupportedAggregationError("Aggregation over grouped rows is not supported in v1")
        raw_value = self._extract_scalar_value(table, metric)
        return "unavailable" if raw_value is None else table.rows[0].completeness


def _unwrap_numeric(value: object) -> object:
    """Extract a plain numeric from a FinancialValue-like object for aggregation."""
    if value is None:
        return None
    if hasattr(value, "is_none") and value.is_none():
        return None
    if hasattr(value, "as_decimal"):
        return value.as_decimal()
    if hasattr(value, "as_float"):
        return value.as_float()
    return value
