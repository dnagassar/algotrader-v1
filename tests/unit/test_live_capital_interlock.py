from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.live_capital_interlock import (
    ENDPOINT_LIVE,
    ENDPOINT_PAPER,
    ENDPOINT_UNKNOWN,
    LiveCapitalGateError,
    evaluate_live_capital_interlock,
    require_live_capital_interlock,
)


MODULE_PATH = Path("src/algotrader/execution/live_capital_interlock.py")

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "requests",
    "socket",
    "ssl",
    "urllib",
)
FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
    "liquidate",
    "replace_order",
    "submit_order",
    "submit_order_request",
    "urlopen",
}

PAPER_URL = "https://paper-api.alpaca.markets"
LIVE_URL = "https://api.alpaca.markets"


def _paper_env(**extra: str) -> dict[str, str]:
    env = {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": "paper-key",
        "ALPACA_SECRET_KEY": "paper-secret",
        "ALPACA_PAPER_BASE_URL": PAPER_URL,
    }
    env.update(extra)
    return env


# --------------------------------------------------------------------------- #
# Passing paper boundary
# --------------------------------------------------------------------------- #
def test_clean_paper_env_passes() -> None:
    verdict = evaluate_live_capital_interlock(_paper_env())
    assert verdict.paper_boundary_ok is True
    assert verdict.profile_is_paper is True
    assert verdict.endpoint_class == ENDPOINT_PAPER
    assert verdict.paper_endpoint_ok is True
    assert verdict.live_signals == ()
    assert verdict.blockers == ()
    assert verdict.live_authorized is False


def test_require_returns_verdict_when_paper() -> None:
    verdict = require_live_capital_interlock(_paper_env())
    assert verdict.paper_boundary_ok is True


def test_expected_paper_account_presence_is_recorded() -> None:
    without = evaluate_live_capital_interlock(_paper_env())
    assert without.expected_paper_account_present is False
    withid = evaluate_live_capital_interlock(
        _paper_env(EXPECTED_PAPER_ACCOUNT_ID="PA123")
    )
    assert withid.expected_paper_account_present is True
    assert withid.paper_boundary_ok is True


# --------------------------------------------------------------------------- #
# Refusals — fail closed
# --------------------------------------------------------------------------- #
def test_live_profile_is_refused() -> None:
    env = _paper_env(APP_PROFILE="live")
    verdict = evaluate_live_capital_interlock(env)
    assert verdict.paper_boundary_ok is False
    assert "app_profile_is_live" in verdict.blockers
    with pytest.raises(LiveCapitalGateError):
        require_live_capital_interlock(env)


def test_dev_or_unset_profile_is_refused() -> None:
    verdict = evaluate_live_capital_interlock({"ALPACA_PAPER_BASE_URL": PAPER_URL})
    assert verdict.paper_boundary_ok is False
    assert any(b.startswith("app_profile_not_paper") for b in verdict.blockers)


def test_live_base_url_is_refused() -> None:
    env = _paper_env(ALPACA_BASE_URL=LIVE_URL)
    verdict = evaluate_live_capital_interlock(env)
    assert verdict.paper_boundary_ok is False
    assert any(s.startswith("live_base_url:ALPACA_BASE_URL") for s in verdict.live_signals)


def test_live_enable_flag_is_refused() -> None:
    env = _paper_env(ALLOW_LIVE_TRADING="true")
    verdict = evaluate_live_capital_interlock(env)
    assert verdict.paper_boundary_ok is False
    assert any(s.startswith("live_enable_flag:ALLOW_LIVE_TRADING") for s in verdict.live_signals)


def test_live_enable_flag_falsey_is_ignored() -> None:
    env = _paper_env(LIVE_TRADING_ENABLED="0")
    verdict = evaluate_live_capital_interlock(env)
    assert verdict.paper_boundary_ok is True


def test_catch_all_live_host_in_arbitrary_env_var_is_refused() -> None:
    env = _paper_env(SOME_RANDOM_ENDPOINT="https://api.alpaca.markets/v2")
    verdict = evaluate_live_capital_interlock(env)
    assert verdict.paper_boundary_ok is False
    assert any(s.startswith("live_host_in_env:SOME_RANDOM_ENDPOINT") for s in verdict.live_signals)


def test_non_paper_endpoint_is_refused() -> None:
    env = _paper_env(ALPACA_PAPER_BASE_URL="https://example.test/broker")
    verdict = evaluate_live_capital_interlock(env)
    assert verdict.endpoint_class == ENDPOINT_UNKNOWN
    assert verdict.paper_boundary_ok is False
    assert any(b.startswith("endpoint_not_paper") for b in verdict.blockers)


def test_live_endpoint_classified_live() -> None:
    env = _paper_env(ALPACA_PAPER_BASE_URL=LIVE_URL)
    verdict = evaluate_live_capital_interlock(env)
    assert verdict.endpoint_class == ENDPOINT_LIVE
    assert verdict.paper_boundary_ok is False


# --------------------------------------------------------------------------- #
# Secret safety
# --------------------------------------------------------------------------- #
def test_no_credential_value_leaks_into_verdict() -> None:
    env = _paper_env(
        ALPACA_API_KEY="SUPERSECRETKEY", ALPACA_SECRET_KEY="SUPERSECRETSECRET"
    )
    verdict = evaluate_live_capital_interlock(env)
    blob = json.dumps(verdict.to_dict()) + " ".join(verdict.blockers) + " ".join(
        verdict.live_signals
    )
    assert "SUPERSECRETKEY" not in blob
    assert "SUPERSECRETSECRET" not in blob


def test_to_dict_fixes_safety_booleans_false() -> None:
    verdict = evaluate_live_capital_interlock(_paper_env())
    d = verdict.to_dict()
    for key in (
        "live_authorized",
        "submitted",
        "mutated",
        "broker_action_performed",
        "network_access_attempted",
        "credential_access_attempted",
    ):
        assert d[key] is False, key


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def test_env_must_be_mapping() -> None:
    with pytest.raises(ValidationError):
        evaluate_live_capital_interlock(["APP_PROFILE=paper"])  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Safety source-scan
# --------------------------------------------------------------------------- #
def test_module_has_no_forbidden_imports_or_calls() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _assert_import_allowed(alias.name)
        elif isinstance(node, ast.ImportFrom):
            _assert_import_allowed(node.module or "")
        elif isinstance(node, ast.Call):
            _assert_call_allowed(node.func)


def _assert_import_allowed(module_name: str) -> None:
    root = module_name.split(".")[0]
    assert root not in FORBIDDEN_IMPORT_PREFIXES, module_name


def _assert_call_allowed(func: ast.expr) -> None:
    if isinstance(func, ast.Name):
        assert func.id not in FORBIDDEN_CALL_NAMES, func.id
    elif isinstance(func, ast.Attribute):
        assert func.attr not in FORBIDDEN_CALL_NAMES, func.attr
