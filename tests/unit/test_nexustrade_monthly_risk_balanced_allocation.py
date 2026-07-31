from __future__ import annotations

import ast
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research.nexustrade_monthly_independent_replication import (
    NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
)
from algotrader.research.nexustrade_monthly_risk_balanced_allocation import (
    NEXUSTRADE_MONTHLY_RISK_BALANCED_ID,
    NexusTradeMonthlyRiskBalancedConfig,
    _capped_water_fill,
    _sample_volatility,
    build_nexustrade_monthly_risk_balanced_preregistration,
    run_nexustrade_monthly_risk_balanced_allocation,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "research"
    / "nexustrade_monthly_risk_balanced_allocation.py"
)
SCRIPT_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "run_nexustrade_monthly_risk_balanced_allocation.ps1"
)
PREREGISTRATION_PATH = (
    PROJECT_ROOT
    / "docs"
    / "design"
    / "v5_67_nexustrade_monthly_risk_balanced_allocation.md"
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
    "17f86b8eafd7e67e6816603cb1bf06fa96a734c7b7d9094d30e68ec85690505e"
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

    config = NexusTradeMonthlyRiskBalancedConfig()

    assert config.volatility_lookback == 60
    assert config.max_target_weight == Decimal("0.20")
    assert config.required_oos_session_count == 254
    with pytest.raises(ValidationError, match="preregistered value 60"):
        NexusTradeMonthlyRiskBalancedConfig(volatility_lookback=20)
    with pytest.raises(ValidationError, match="preregistered value 0.20"):
        NexusTradeMonthlyRiskBalancedConfig(max_target_weight="0.25")


def test_preregistration_is_outcome_blind_and_does_not_write(tmp_path: Path) -> None:
    output_root = tmp_path / "not-created"
    config = NexusTradeMonthlyRiskBalancedConfig(output_root=output_root)

    payload = build_nexustrade_monthly_risk_balanced_preregistration(config)

    assert payload["protocol_id"] == (
        "v5_67_nexustrade_monthly_risk_balanced_allocation_v1"
    )
    assert payload["candidate_id"] == NEXUSTRADE_MONTHLY_RISK_BALANCED_ID
    assert payload["claim"] == (
        "independent_candidate_not_authentic_source_replay"
    )
    assert payload["allocation"] == {
        "method": "inverse_sample_volatility_capped_water_fill",
        "return_type": "simple_adjusted_close_return",
        "volatility_lookback_returns": 60,
        "required_adjusted_close_count": 61,
        "sample_variance_denominator": 59,
        "annualized_for_weighting": False,
        "volatility_floor": None,
        "max_target_weight": "0.20",
        "maximum_stock_exposure": "min(1,0.20*eligible_count)",
        "residual_held_as_cash": True,
        "canonical_symbol_order_tie_break": True,
    }
    assert payload["parameter_search_performed"] is False
    assert payload["paper_promotion_allowed"] is False
    assert not output_root.exists()


def test_sample_volatility_and_capped_water_fill_are_deterministic() -> None:
    prices = [Decimal("100")]
    for index in range(60):
        daily_return = Decimal("0.01") if index % 2 == 0 else Decimal("-0.005")
        prices.append(prices[-1] * (Decimal("1") + daily_return))

    first = _sample_volatility(tuple(prices), 60, 60)
    second = _sample_volatility(tuple(prices), 60, 60)

    assert first == second
    assert first > Decimal("0")

    symbols = NEXUSTRADE_MONTHLY_STOCK_SYMBOLS[:6]
    scores = {symbol: Decimal("1") for symbol in symbols}
    scores[symbols[-1]] = Decimal("2")
    weights = _capped_water_fill(symbols, scores)

    assert weights[symbols[-1]] == Decimal("0.20")
    assert all(weights[symbol] == Decimal("0.16") for symbol in symbols[:-1])
    assert sum(weights.values(), Decimal("0")) == Decimal("1.00")
    assert tuple(weights) == symbols


def test_volatility_and_allocation_fail_closed() -> None:
    with pytest.raises(ValidationError, match="finite and positive"):
        _sample_volatility(tuple(Decimal("100") for _ in range(61)), 60, 60)
    with pytest.raises(ValidationError, match="finite and positive"):
        _capped_water_fill(
            NEXUSTRADE_MONTHLY_STOCK_SYMBOLS[:2],
            {
                NEXUSTRADE_MONTHLY_STOCK_SYMBOLS[0]: Decimal("1"),
                NEXUSTRADE_MONTHLY_STOCK_SYMBOLS[1]: Decimal("0"),
            },
        )


def test_full_replay_is_deterministic_and_enforces_fixed_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(PROJECT_ROOT)
    config = NexusTradeMonthlyRiskBalancedConfig(output_root=tmp_path / "output")

    first = run_nexustrade_monthly_risk_balanced_allocation(config)
    first_hashes = _output_hashes(config.output_root)
    second = run_nexustrade_monthly_risk_balanced_allocation(config)
    second_hashes = _output_hashes(config.output_root)

    assert first_hashes == second_hashes
    assert first["artifact_manifest"] == second["artifact_manifest"]
    assert first["frozen_parent_reproduction"]["passed"] is True
    assert first["frozen_parent_reproduction"][
        "result_structured_equality"
    ] is True
    assert first["parameter_search_performed"] is False
    candidate = first["candidate"]
    assert candidate["candidate_id"] == NEXUSTRADE_MONTHLY_RISK_BALANCED_ID
    assert candidate["route"] in {
        "preview_review",
        "continue_local_research",
        "reject",
    }
    assert candidate["paper_promotion_allowed"] is False
    integrity = first["allocation_integrity"]
    assert integrity["passed"] is True
    assert integrity["oos_target_difference_session_count"] > 0
    assert integrity["cap_violation_session_count"] == 0
    assert integrity["exposure_violation_session_count"] == 0
    assert Decimal(integrity["max_observed_oos_target_weight"]) <= Decimal(
        "0.20"
    )
    assert first["safety"]["network_access_performed"] is False
    assert first["safety"]["broker_access_performed"] is False
    assert first["safety"]["paper_mutation_performed"] is False
    assert first["safety"]["live_activity_performed"] is False


def test_tampered_protocol_fails_before_output_write(
    tmp_path: Path,
) -> None:
    tampered = tmp_path / "protocol.md"
    tampered.write_text(
        PREREGISTRATION_PATH.read_text(encoding="utf-8") + "\ntampered\n",
        encoding="utf-8",
    )
    output_root = tmp_path / "output"
    config = NexusTradeMonthlyRiskBalancedConfig(
        output_root=output_root,
        preregistration_path=tampered,
    )

    with pytest.raises(ValidationError, match="tracked_preregistration_sha256"):
        run_nexustrade_monthly_risk_balanced_allocation(config)
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

    assert "nexustrade_monthly_risk_balanced_allocation" in text
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
