"""Project-specific exceptions."""


class AlgoTraderError(Exception):
    """Base class for project errors."""


class ConfigError(AlgoTraderError):
    """Raised when runtime configuration is invalid."""


class ProfileError(ConfigError):
    """Raised when a requested runtime profile is unknown."""


class DataError(AlgoTraderError):
    """Raised when deterministic market data inputs are invalid."""


class TradingCoreError(AlgoTraderError):
    """Raised by deterministic trading-core components."""
