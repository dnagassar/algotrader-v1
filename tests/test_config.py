from decimal import Decimal

import pytest

from algotrader.config import load_config
from algotrader.errors import ProfileError


def test_loads_dev_profile() -> None:
    config = load_config("dev", env={})

    assert config.profile == "dev"
    assert config.log_level == "DEBUG"
    assert config.starting_cash == Decimal("100000")
    assert config.paper_exchange == "simulated"
    assert config.deterministic is True
    assert config.live_trading_enabled is False


def test_loads_paper_profile() -> None:
    config = load_config("paper", env={})

    assert config.profile == "paper"
    assert config.log_level == "INFO"
    assert config.starting_cash == Decimal("100000")
    assert config.paper_exchange == "paper"
    assert config.deterministic is True
    assert config.live_trading_enabled is False


def test_invalid_profile_raises_profile_error() -> None:
    with pytest.raises(ProfileError):
        load_config("live", env={})
