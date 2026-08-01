from __future__ import annotations

import ast
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research import (
    nexustrade_monthly_relative_momentum_confirmation as target_module,
)
from algotrader.research.nexustrade_monthly_independent_replication import (
    NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
)
from algotrader.research.nexustrade_monthly_relative_momentum_confirmation import (
    NEXUSTRADE_MONTHLY_RELATIVE_MOMENTUM_ID,
    NexusTradeMonthlyRelativeMomentumConfig,
    _relative_momentum_target,
    build_nexustrade_monthly_relative_momentum_preregistration,
    run_nexustrade_monthly_relative_momentum_confirmation,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "research"
    / "nexustrade_monthly_relative_momentum_confirmation.py"
)
SCRIPT_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "run_nexustrade_monthly_relative_momentum_confirmation.ps1"
)
PREREGISTRATION_PATH = (
    PROJECT_ROOT
    / "docs"
    / "design"
    / "v5_69_nexustrade_monthly_relative_momentum_confirmation.md"
)
PARENT_PROTOCOL_PATH = (
    PROJECT_ROOT
    / "docs"
    / "design"
    / "v5_64_nexustrade_monthly_independent_replication.md"
)
PARENT_ENGINE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "research"
    / "nexustrade_monthly_independent_replication.py"
)
EXPECTED_PREREGISTRATION_SHA256 = (
    "a83ade6896ec7b6703af3afc51f922d0e7f98376a230f71a8c7957bf138690e5"
)
EXPECTED_PARENT_PROTOCOL_SHA256 = (
    "f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0"
)
EXPECTED_PARENT_ENGINE_SHA256 = (
    "66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5"
)
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.orchestration",
    "algotrader.risk",
    "alpaca",
    "httpx",
    "requests",
    "socket",
    "urllib",
)


def test_tracked_protocol_parent_and_fixed_defaults() -> None:
    assert _sha256(PREREGISTRATION_PATH) == EXPECTED_PREREGISTRATION_SHA256
    assert _sha256(PARENT_PROTOCOL_PATH) == EXPECTED_PARENT_PROTOCOL_SHA256
    assert _sha256(PARENT_ENGINE_PATH) == EXPECTED_PARENT_ENGINE_SHA256

    config = NexusTradeMonthlyRelativeMomentumConfig()

    assert config.momentum_lookback == 126
    assert config.max_selected_count == 5
    assert config.required_oos_session_count == 254
    with pytest.raises(ValidationError, match="must equal 126"):
        NexusTradeMonthlyRelativeMomentumConfig(momentum_lookback=63)
    with pytest.raises(ValidationError, match="must equal 5"):
        NexusTradeMonthlyRelativeMomentumConfig(max_selected_count=4)


def test_preregistration_is_outcome_blind_and_does_not_write(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "not-created"
    config = NexusTradeMonthlyRelativeMomentumConfig(output_root=output_root)

    payload = build_nexustrade_monthly_relative_momentum_preregistration(config)

    assert payload["protocol_id"] == (
        "v5_69_nexustrade_monthly_relative_momentum_confirmation_v1"
    )
    assert payload["candidate_id"] == NEXUSTRADE_MONTHLY_RELATIVE_MOMENTUM_ID
    assert payload["claim"] == (
        "independent_candidate_not_authentic_source_replay"
    )
    assert payload["selection"] == {
        "method": "positive_absolute_and_spy_relative_momentum_confirmation",
        "lookback_observed_sessions": 126,
        "return_formula": "close_t/close_t_minus_126-1",
        "absolute_return_must_be_strictly_positive": True,
        "stock_return_must_strictly_exceed_spy": True,
        "rank": "descending_stock_minus_spy_return",
        "tie_break": "canonical_stock_symbol_order",
        "maximum_selected_count": 5,
        "allocation": "equal_weight_selected_to_full_exposure",
        "no_selection_target": "cash",
        "parameter_search_performed": False,
    }
    assert payload["excluded_closed_lanes"][
        "v565_through_v568_signal_or_outcome_reused"
    ] is False
    assert payload["paper_promotion_allowed"] is False
    assert not output_root.exists()


def test_relative_momentum_selection_is_strict_ranked_and_equal_weight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions = 127
    dates = tuple(date(2024, 1, 1) + timedelta(days=index) for index in range(sessions))
    final_prices = {
        "AAPL": "160",
        "MSFT": "150",
        "GOOGL": "140",
        "AMZN": "130",
        "META": "120",
        "NVDA": "120",
        "TSLA": "110",
        "GS": "109",
        "JPM": "90",
        "BRK-B": "100",
        "COST": "111",
        "SPY": "110",
    }
    prices = {}
    for symbol in (*NEXUSTRADE_MONTHLY_STOCK_SYMBOLS, "SPY"):
        values = [Decimal("100")] * sessions
        values[-1] = Decimal(final_prices[symbol])
        prices[symbol] = tuple(values)
    data = SimpleNamespace(dates=dates, prices=prices)
    eligible = {
        symbol: Decimal("1") / Decimal(len(NEXUSTRADE_MONTHLY_STOCK_SYMBOLS))
        for symbol in NEXUSTRADE_MONTHLY_STOCK_SYMBOLS
    }
    monkeypatch.setattr(target_module._base, "_eligible_target", lambda *_: eligible)

    first_target, first_decision = _relative_momentum_target(
        data, {}, 126
    )
    second_target, second_decision = _relative_momentum_target(
        data, {}, 126
    )

    assert first_target == second_target
    assert first_decision == second_decision
    assert first_decision["ranked_qualified_symbols"] == [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "META",
        "NVDA",
        "COST",
    ]
    assert first_decision["selected_symbols"] == [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "META",
    ]
    assert all(
        first_target[symbol] == Decimal("0.2")
        for symbol in first_decision["selected_symbols"]
    )
    assert first_target["TSLA"] == Decimal("0")
    assert first_target["COST"] == Decimal("0")
    assert sum(first_target.values(), Decimal("0")) == Decimal("1.0")


def test_relative_momentum_parameters_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = SimpleNamespace(
        dates=tuple(date(2024, 1, 1) + timedelta(days=index) for index in range(127)),
        prices={
            symbol: tuple(Decimal("100") for _ in range(127))
            for symbol in (*NEXUSTRADE_MONTHLY_STOCK_SYMBOLS, "SPY")
        },
    )
    monkeypatch.setattr(
        target_module._base,
        "_eligible_target",
        lambda *_: {symbol: Decimal("0") for symbol in NEXUSTRADE_MONTHLY_STOCK_SYMBOLS},
    )

    with pytest.raises(ValidationError, match="must remain 126"):
        _relative_momentum_target(data, {}, 126, momentum_lookback=63)
    with pytest.raises(ValidationError, match="must remain five"):
        _relative_momentum_target(data, {}, 126, max_selected_count=4)


def test_full_replay_is_deterministic_and_enforces_fixed_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(PROJECT_ROOT)
    config = NexusTradeMonthlyRelativeMomentumConfig(
        output_root=tmp_path / "output"
    )

    first = run_nexustrade_monthly_relative_momentum_confirmation(config)
    first_hashes = _output_hashes(config.output_root)
    second = run_nexustrade_monthly_relative_momentum_confirmation(config)
    second_hashes = _output_hashes(config.output_root)

    assert first_hashes == second_hashes
    assert first["artifact_manifest"] == second["artifact_manifest"]
    assert first["frozen_parent_reproduction"]["passed"] is True
    assert first["frozen_parent_reproduction"][
        "result_structured_equality"
    ] is True
    assert first["parameter_search_performed"] is False
    candidate = first["candidate"]
    assert candidate["candidate_id"] == NEXUSTRADE_MONTHLY_RELATIVE_MOMENTUM_ID
    assert candidate["route"] in {
        "preview_review",
        "continue_local_research",
        "reject",
    }
    assert candidate["paper_promotion_allowed"] is False
    integrity = first["selection_integrity"]
    assert integrity["passed"] is True
    assert integrity["oos_target_difference_session_count"] > 0
    assert integrity["max_observed_selected_count"] <= 5
    assert integrity["count_violation_dates"] == []
    assert integrity["nonpositive_momentum_violation_dates"] == []
    assert integrity["spy_relative_momentum_violation_dates"] == []
    assert integrity["ranking_violation_dates"] == []
    assert integrity["equal_weight_violation_dates"] == []
    assert first["safety"]["network_access_performed"] is False
    assert first["safety"]["broker_access_performed"] is False
    assert first["safety"]["paper_mutation_performed"] is False
    assert first["safety"]["live_activity_performed"] is False


def test_tampered_protocol_fails_before_output_write(tmp_path: Path) -> None:
    tampered = tmp_path / "protocol.md"
    tampered.write_text(
        PREREGISTRATION_PATH.read_text(encoding="utf-8") + "\ntampered\n",
        encoding="utf-8",
    )
    output_root = tmp_path / "output"
    config = NexusTradeMonthlyRelativeMomentumConfig(
        output_root=output_root,
        preregistration_path=tampered,
    )

    with pytest.raises(ValidationError, match="tracked_preregistration_sha256"):
        run_nexustrade_monthly_relative_momentum_confirmation(config)
    assert not output_root.exists()


def test_module_has_no_network_broker_execution_or_risk_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    assert not any(
        imported == prefix or imported.startswith(prefix + ".")
        for imported in imports
        for prefix in FORBIDDEN_IMPORT_PREFIXES
    )


def test_wrapper_is_offline_fail_closed_and_uses_repo_src() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "nexustrade_monthly_relative_momentum_confirmation" in text
    assert 'Join-Path $RepoRoot "src"' in text
    assert "preflight_sensitive_variables_loaded" in text
    assert "TIINGO_API_KEY" in text
    assert "TIINGO_API_TOKEN" in text
    assert "blocked_unsafe_environment" in text
    assert "Invoke-WebRequest" not in text
    assert "Invoke-RestMethod" not in text
    assert "submit_order" not in text.lower()
    assert "cancel_order" not in text.lower()


def test_wrapper_blocks_loaded_credential_without_invoking_python(
    tmp_path: Path,
) -> None:
    powershell = _powershell()
    if powershell is None:
        pytest.skip("PowerShell is unavailable")
    env = os.environ.copy()
    env["APCA_API_KEY_ID"] = "sentinel-not-a-real-secret"
    completed = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-File",
            str(SCRIPT_PATH),
            "-OutputRoot",
            str(tmp_path / "blocked"),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    combined = completed.stdout + completed.stderr
    assert completed.returncode == 2
    assert "preflight_sensitive_variables_loaded=true" in combined
    assert "blocked_unsafe_environment" in combined
    assert env["APCA_API_KEY_ID"] not in combined
    assert not (tmp_path / "blocked").exists()


def _output_hashes(root: Path) -> dict[str, str]:
    return {
        path.name: _sha256(path)
        for path in sorted(root.iterdir())
        if path.is_file()
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _powershell() -> str | None:
    return shutil.which("pwsh") or shutil.which("powershell")
