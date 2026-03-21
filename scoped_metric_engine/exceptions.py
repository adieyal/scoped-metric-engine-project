"""Domain exceptions for scoped-metric-engine."""


class ScopedMetricEngineError(Exception):
    """Base exception for all scoped metric engine errors."""


class InvalidScopeError(ScopedMetricEngineError):
    """Raised when a Scope or ResolutionGrain is invalid."""


class InvalidSliceError(ScopedMetricEngineError):
    """Raised when a Slice has invalid parameters."""


class UnsupportedAggregationError(ScopedMetricEngineError):
    """Raised when an aggregation operation is not supported."""
