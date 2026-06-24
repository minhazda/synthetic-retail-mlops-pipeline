"""Custom exception hierarchy for the retail forecasting pipeline.

A single base exception (:class:`RetailForecastingError`) lets callers catch
every domain error with one ``except`` while still allowing fine-grained
handling of specific failure modes.
"""

from __future__ import annotations


class RetailForecastingError(Exception):
    """Base class for all errors raised by this package."""


class ConfigError(RetailForecastingError):
    """Raised when configuration is missing, malformed, or invalid."""


class DataValidationError(RetailForecastingError):
    """Raised when input data fails schema or quality validation."""


class ModelNotFoundError(RetailForecastingError):
    """Raised when a serialized model artifact cannot be located or loaded."""


class FeatureMismatchError(RetailForecastingError):
    """Raised when inference features do not match the model's training schema."""
