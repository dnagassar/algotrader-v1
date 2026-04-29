from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.config import (
    AlpacaPaperConfig,
    ConfigValidationError,
    DEFAULT_DATA_DIR,
    DEFAULT_LOG_LEVEL,
    DEFAULT_PAPER_EXCHANGE,
    DEFAULT_STARTING_CASH,
    PROFILE_NAMES,
    TradingConfig,
    load_config,
    require_paper_profile,
)


def test_trading_config_public_api_is_available_for_conftest_imports():
    config = load_config({})

    assert isinstance(config, TradingConfig)
    assert config.app_profile == "dev"
    assert config.log_level == DEFAULT_LOG_LEVEL
    assert config.data_dir == DEFAULT_DATA_DIR
    assert config.starting_cash == DEFAULT_STARTING_CASH
    assert config.paper_exchange == DEFAULT_PAPER_EXCHANGE
    assert isinstance(config.alpaca_paper, AlpacaPaperConfig)
    assert config.alpaca_paper.alpaca_api_key is None
    assert config.alpaca_paper.alpaca_secret_key is None


def test_profile_names_public_api_is_available_for_cli_imports():
    assert "dev" in PROFILE_NAMES
    assert "paper" in PROFILE_NAMES


def test_load_config_accepts_profile_name_for_cli_compatibility():
    config = load_config("paper")

    assert isinstance(config, TradingConfig)
    assert config.profile == "paper"
    assert config.app_profile == "paper"
    assert config.log_level == DEFAULT_LOG_LEVEL
    assert config.alpaca_paper.app_profile == "paper"
    assert config.alpaca_paper.alpaca_api_key is None
    assert config.alpaca_paper.alpaca_secret_key is None


def test_load_config_preserves_cli_log_level_config():
    config = load_config({"LOG_LEVEL": "DEBUG"})

    assert config.log_level == "DEBUG"


def test_load_config_preserves_cli_display_config():
    config = load_config(
        {
            "DATA_DIR": "custom-data",
            "STARTING_CASH": "250000.50",
            "PAPER_EXCHANGE": "test-exchange",
        }
    )

    assert config.data_dir == Path("custom-data")
    assert config.starting_cash == Decimal("250000.50")
    assert config.paper_exchange == "test-exchange"


def test_alpaca_paper_config_can_be_constructed_with_paper_settings():
    config = AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key="test-api-key",
        alpaca_secret_key="test-secret-key",
        alpaca_paper_base_url="https://paper.example.test",
    )

    config.validate_alpaca_paper_ready()

    assert config.is_paper_profile is True
    assert config.alpaca_api_key == "test-api-key"
    assert config.alpaca_secret_key == "test-secret-key"
    assert config.alpaca_paper_base_url == "https://paper.example.test"


def test_require_paper_profile_rejects_non_paper_profile():
    config = AlpacaPaperConfig(
        app_profile="dev",
        alpaca_api_key="test-api-key",
        alpaca_secret_key="test-secret-key",
        alpaca_paper_base_url="https://paper.example.test",
    )

    with pytest.raises(ConfigValidationError, match="APP_PROFILE=paper"):
        require_paper_profile(config)


def test_require_paper_profile_passes_with_valid_paper_config():
    config = AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key="test-api-key",
        alpaca_secret_key="test-secret-key",
        alpaca_paper_base_url="https://paper.example.test",
    )

    assert require_paper_profile(config) is None


def test_require_paper_profile_delegates_paper_readiness_validation():
    config = AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key="test-api-key",
        alpaca_secret_key="",
        alpaca_paper_base_url="https://paper.example.test",
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        require_paper_profile(config)

    assert "ALPACA_SECRET_KEY" in str(exc_info.value)


def test_missing_alpaca_credentials_fail_only_when_readiness_is_validated():
    config = AlpacaPaperConfig(app_profile="paper")

    assert config.alpaca_api_key is None
    assert config.alpaca_secret_key is None

    with pytest.raises(ConfigValidationError) as exc_info:
        config.validate_alpaca_paper_ready()

    message = str(exc_info.value)
    assert "ALPACA_API_KEY" in message
    assert "ALPACA_SECRET_KEY" in message


def test_alpaca_config_repr_and_string_redact_secrets():
    config = AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key="sensitive-api-key",
        alpaca_secret_key="sensitive-secret-key",
    )

    rendered = f"{config!r} {config}"

    assert "sensitive-api-key" not in rendered
    assert "sensitive-secret-key" not in rendered
    assert "alpaca_api_key=<set>" in rendered
    assert "alpaca_secret_key=<set>" in rendered


def test_alpaca_config_validation_errors_do_not_expose_present_secrets():
    config = AlpacaPaperConfig(
        app_profile="dev",
        alpaca_api_key="sensitive-api-key",
        alpaca_secret_key="sensitive-secret-key",
        alpaca_paper_base_url="",
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        config.validate_alpaca_paper_ready()

    message = str(exc_info.value)
    assert "sensitive-api-key" not in message
    assert "sensitive-secret-key" not in message
    assert "APP_PROFILE=paper" in message
    assert "ALPACA_PAPER_BASE_URL" in message


def test_normal_dev_config_works_without_alpaca_credentials():
    config = AlpacaPaperConfig.from_env({})

    assert config.app_profile == "dev"
    assert config.is_paper_profile is False
    assert config.alpaca_api_key is None
    assert config.alpaca_secret_key is None


def test_from_env_is_credential_free_by_default(monkeypatch):
    monkeypatch.delenv("APP_PROFILE", raising=False)
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.delenv("ALPACA_PAPER_BASE_URL", raising=False)

    config = AlpacaPaperConfig.from_env()

    assert config.app_profile == "dev"
    assert config.alpaca_api_key is None
    assert config.alpaca_secret_key is None


def test_trading_config_repr_redacts_nested_alpaca_secrets():
    config = load_config(
        {
            "APP_PROFILE": "paper",
            "ALPACA_API_KEY": "sensitive-api-key",
            "ALPACA_SECRET_KEY": "sensitive-secret-key",
        }
    )

    rendered = repr(config)

    assert "sensitive-api-key" not in rendered
    assert "sensitive-secret-key" not in rendered
    assert "alpaca_api_key=<set>" in rendered
    assert "alpaca_secret_key=<set>" in rendered
