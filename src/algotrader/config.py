"""Runtime configuration for deterministic dev and paper profiles."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from .errors import ConfigError, ProfileError

ProfileName = Literal["dev", "paper"]
PROFILE_NAMES: tuple[ProfileName, ...] = ("dev", "paper")


@dataclass(frozen=True, slots=True)
class TradingConfig:
    profile: ProfileName
    log_level: str
    data_dir: Path
    starting_cash: Decimal
    paper_exchange: str
    deterministic: bool = True
    live_trading_enabled: bool = False


_PROFILE_DEFAULTS: dict[ProfileName, dict[str, str]] = {
    "dev": {
        "log_level": "DEBUG",
        "data_dir": ".data/dev",
        "starting_cash": "100000",
        "paper_exchange": "simulated",
    },
    "paper": {
        "log_level": "INFO",
        "data_dir": ".data/paper",
        "starting_cash": "100000",
        "paper_exchange": "paper",
    },
}


def load_config(
    profile: str | None = None,
    env: Mapping[str, str] | None = None,
) -> TradingConfig:
    values = env if env is not None else os.environ
    selected = profile or values.get("ALGOTRADER_PROFILE", "dev")

    if selected not in PROFILE_NAMES:
        expected = ", ".join(PROFILE_NAMES)
        raise ProfileError(f"Unknown profile {selected!r}. Expected one of: {expected}.")

    profile_name = selected
    defaults = _PROFILE_DEFAULTS[profile_name]
    starting_cash_text = values.get(
        "ALGOTRADER_STARTING_CASH",
        defaults["starting_cash"],
    )

    try:
        starting_cash = Decimal(starting_cash_text)
    except InvalidOperation as exc:
        raise ConfigError("ALGOTRADER_STARTING_CASH must be a decimal number.") from exc

    if starting_cash <= 0:
        raise ConfigError("ALGOTRADER_STARTING_CASH must be greater than zero.")

    return TradingConfig(
        profile=profile_name,
        log_level=values.get("ALGOTRADER_LOG_LEVEL", defaults["log_level"]).upper(),
        data_dir=Path(values.get("ALGOTRADER_DATA_DIR", defaults["data_dir"])),
        starting_cash=starting_cash,
        paper_exchange=values.get(
            "ALGOTRADER_PAPER_EXCHANGE",
            defaults["paper_exchange"],
        ),
    )
