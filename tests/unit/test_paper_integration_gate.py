import pytest

from conftest import (
    PAPER_INTEGRATION_FLAG,
    _paper_integration_enabled,
)


VALID_PAPER_ENV = {
    PAPER_INTEGRATION_FLAG: "1",
    "APP_PROFILE": "paper",
    "ALPACA_API_KEY": "test-api-key",
    "ALPACA_SECRET_KEY": "test-secret-key",
    "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
}


def test_paper_integration_gate_is_disabled_without_flag() -> None:
    env = dict(VALID_PAPER_ENV)
    env.pop(PAPER_INTEGRATION_FLAG)

    assert _paper_integration_enabled(env) is False


def test_paper_integration_gate_is_disabled_with_wrong_flag() -> None:
    env = dict(VALID_PAPER_ENV, **{PAPER_INTEGRATION_FLAG: "0"})

    assert _paper_integration_enabled(env) is False


def test_paper_integration_gate_is_disabled_without_paper_profile() -> None:
    env = dict(VALID_PAPER_ENV, APP_PROFILE="dev")

    assert _paper_integration_enabled(env) is False


def test_paper_integration_gate_is_disabled_with_missing_alpaca_values() -> None:
    env = dict(VALID_PAPER_ENV, ALPACA_SECRET_KEY="")

    assert _paper_integration_enabled(env) is False


def test_paper_integration_gate_is_enabled_with_all_required_values() -> None:
    assert _paper_integration_enabled(VALID_PAPER_ENV) is True


@pytest.mark.paper_integration
def test_paper_integration_marker_is_skipped_by_default() -> None:
    assert True
