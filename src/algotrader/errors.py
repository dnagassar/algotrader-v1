"""Project-specific exceptions."""


class AlgoTraderError(Exception):
    """Base class for project errors."""


class ValidationError(AlgoTraderError, ValueError):
    """Raised when a domain model fails deterministic validation."""


class ConfigError(AlgoTraderError):
    """Raised when runtime configuration is invalid."""


class ProfileError(ConfigError):
    """Raised when a requested runtime profile is unknown."""


class DataError(AlgoTraderError):
    """Raised when deterministic market data inputs are invalid."""


class TradingCoreError(AlgoTraderError):
    """Raised by deterministic trading-core components."""


class MissingQuoteError(TradingCoreError, KeyError):
    """Raised when valuation requires a quote that was not supplied."""
