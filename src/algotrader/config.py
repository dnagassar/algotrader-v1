"""Configuration models for offline application setup.

This module intentionally does not import Alpaca SDKs, instantiate clients, or
perform network calls.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
import os
from pathlib import Path
from typing import Optional


DEFAULT_APP_PROFILE = "dev"
DEFAULT_DATA_DIR = Path("data")
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_PAPER_EXCHANGE = "local"
DEFAULT_STARTING_CASH = Decimal("100000")
PAPER_APP_PROFILE = "paper"
LIVE_APP_PROFILE = "live"
PROFILE_NAMES = (DEFAULT_APP_PROFILE, PAPER_APP_PROFILE, LIVE_APP_PROFILE)
DEFAULT_ALPACA_PAPER_BASE_URL = "https://paper-api.alpaca.markets"


__all__ = [
    "AlpacaPaperConfig",
    "ConfigValidationError",
    "DEFAULT_ALPACA_PAPER_BASE_URL",
    "DEFAULT_APP_PROFILE",
    "DEFAULT_DATA_DIR",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_PAPER_EXCHANGE",
    "DEFAULT_STARTING_CASH",
    "LIVE_APP_PROFILE",
    "PAPER_APP_PROFILE",
    "PROFILE_NAMES",
    "TradingConfig",
    "load_config",
]


class ConfigValidationError(ValueError):
    """Raised when explicitly requested configuration validation fails."""


def _clean_optional(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    value = value.strip()
    return value or None


def _clean_with_default(value: Optional[str], default: str) -> str:
    cleaned = _clean_optional(value)
    return cleaned if cleaned is not None else default


@dataclass(frozen=True)
class TradingConfig:
    """Top-level application config kept for backward compatibility."""

    app_profile: str = DEFAULT_APP_PROFILE
    profile: str = DEFAULT_APP_PROFILE
    log_level: str = DEFAULT_LOG_LEVEL
    data_dir: Path = DEFAULT_DATA_DIR
    starting_cash: Decimal = DEFAULT_STARTING_CASH
    paper_exchange: str = DEFAULT_PAPER_EXCHANGE
    alpaca_paper: "AlpacaPaperConfig" = field(
        default_factory=lambda: AlpacaPaperConfig()
    )

    def __post_init__(self) -> None:
        app_profile = self.app_profile
        profile = self.profile

        if app_profile == DEFAULT_APP_PROFILE and profile != DEFAULT_APP_PROFILE:
            app_profile = profile
        elif profile == DEFAULT_APP_PROFILE and app_profile != DEFAULT_APP_PROFILE:
            profile = app_profile

        object.__setattr__(self, "app_profile", app_profile)
        object.__setattr__(self, "profile", profile)
        object.__setattr__(self, "data_dir", Path(self.data_dir))
        object.__setattr__(self, "starting_cash", Decimal(str(self.starting_cash)))

        if self.alpaca_paper.app_profile != app_profile:
            object.__setattr__(
                self,
                "alpaca_paper",
                AlpacaPaperConfig(
                    app_profile=app_profile,
                    alpaca_api_key=self.alpaca_paper.alpaca_api_key,
                    alpaca_secret_key=self.alpaca_paper.alpaca_secret_key,
                    alpaca_paper_base_url=self.alpaca_paper.alpaca_paper_base_url,
                ),
            )

    @classmethod
    def from_env(
        cls,
        env: Optional[Mapping[str, str]] = None,
        profile: Optional[str] = None,
    ) -> "TradingConfig":
        source = os.environ if env is None else env
        alpaca_paper = AlpacaPaperConfig.from_env(env)
        app_profile = _clean_with_default(profile, alpaca_paper.app_profile)
        alpaca_paper = AlpacaPaperConfig(
            app_profile=app_profile,
            alpaca_api_key=alpaca_paper.alpaca_api_key,
            alpaca_secret_key=alpaca_paper.alpaca_secret_key,
            alpaca_paper_base_url=alpaca_paper.alpaca_paper_base_url,
        )
        return cls(
            app_profile=app_profile,
            profile=app_profile,
            log_level=_clean_with_default(
                source.get("LOG_LEVEL"), DEFAULT_LOG_LEVEL
            ),
            data_dir=Path(
                _clean_with_default(source.get("DATA_DIR"), str(DEFAULT_DATA_DIR))
            ),
            starting_cash=Decimal(
                _clean_with_default(
                    source.get("STARTING_CASH"), str(DEFAULT_STARTING_CASH)
                )
            ),
            paper_exchange=_clean_with_default(
                source.get("PAPER_EXCHANGE"), DEFAULT_PAPER_EXCHANGE
            ),
            alpaca_paper=alpaca_paper,
        )


@dataclass(frozen=True)
class AlpacaPaperConfig:
    """Offline configuration boundary for future Alpaca paper integration."""

    app_profile: str = DEFAULT_APP_PROFILE
    alpaca_api_key: Optional[str] = field(default=None, repr=False)
    alpaca_secret_key: Optional[str] = field(default=None, repr=False)
    alpaca_paper_base_url: str = DEFAULT_ALPACA_PAPER_BASE_URL

    @classmethod
    def from_env(
        cls, env: Optional[Mapping[str, str]] = None
    ) -> "AlpacaPaperConfig":
        source = os.environ if env is None else env

        return cls(
            app_profile=_clean_with_default(
                source.get("APP_PROFILE"), DEFAULT_APP_PROFILE
            ),
            alpaca_api_key=_clean_optional(source.get("ALPACA_API_KEY")),
            alpaca_secret_key=_clean_optional(source.get("ALPACA_SECRET_KEY")),
            alpaca_paper_base_url=_clean_with_default(
                source.get("ALPACA_PAPER_BASE_URL"),
                DEFAULT_ALPACA_PAPER_BASE_URL,
            ),
        )

    @property
    def is_paper_profile(self) -> bool:
        return self.app_profile.strip().lower() == PAPER_APP_PROFILE

    def validate_alpaca_paper_ready(self) -> None:
        """Validate settings only when Alpaca paper readiness is requested."""

        missing_or_invalid = []

        if not self.is_paper_profile:
            missing_or_invalid.append("APP_PROFILE=paper")

        if not _clean_optional(self.alpaca_api_key):
            missing_or_invalid.append("ALPACA_API_KEY")

        if not _clean_optional(self.alpaca_secret_key):
            missing_or_invalid.append("ALPACA_SECRET_KEY")

        if not _clean_optional(self.alpaca_paper_base_url):
            missing_or_invalid.append("ALPACA_PAPER_BASE_URL")

        if missing_or_invalid:
            joined = ", ".join(missing_or_invalid)
            raise ConfigValidationError(
                f"Alpaca paper configuration is not ready. Missing or invalid: {joined}."
            )

    def __repr__(self) -> str:
        return (
            "AlpacaPaperConfig("
            f"app_profile={self.app_profile!r}, "
            f"alpaca_api_key={self._secret_state(self.alpaca_api_key)}, "
            f"alpaca_secret_key={self._secret_state(self.alpaca_secret_key)}, "
            f"alpaca_paper_base_url={self.alpaca_paper_base_url!r}"
            ")"
        )

    __str__ = __repr__

    @staticmethod
    def _secret_state(value: Optional[str]) -> str:
        return "<set>" if _clean_optional(value) else "<unset>"


def load_config(
    profile: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
) -> TradingConfig:
    """Load normal application config without requiring Alpaca credentials."""

    if isinstance(profile, Mapping):
        env = profile
        profile = None

    app_profile = _clean_optional(profile)
    if app_profile is not None and app_profile not in PROFILE_NAMES:
        valid = ", ".join(PROFILE_NAMES)
        raise ConfigValidationError(
            f"Unknown profile {app_profile!r}. Expected one of: {valid}."
        )

    return TradingConfig.from_env(env, profile=app_profile)
