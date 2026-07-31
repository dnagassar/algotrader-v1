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
from algotrader.research.nexustrade_risk_balanced_attribution import (
    NexusTradeRiskBalancedAttributionConfig,
    _select_pure_sizing_target,
    build_nexustrade_risk_balanced_attribution_preregistration,
    run_nexustrade_risk_balanced_attribution,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "research"
    / "nexustrade_risk_balanced_attribution.py"
)
SCRIPT_PATH = (
    PROJECT_ROOT / "scripts" / "run_nexustrade_risk_balanced_attribution.ps1"
)
PREREGISTRATION_PATH = (
    PROJECT_ROOT
    / "docs"
    / "design"
    / "v5_68_nexustrade_risk_balanced_attribution.md"
)
V567_ENGINE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "research"
    / "nexustrade_monthly_risk_balanced_allocation.py"
)
EXPECTED_PREREGISTRATION_SHA256 = (
    "d0d89a0807cf8db41cb7377a40b6af1342625b4ff32fc8e56f53b5f2d9ec5513"
)
EXPECTED_V567_ENGINE_SHA256 = (
    "2c669051c6c3fc877cd86d482579ffa711e7d68724e5dffb117d32080aef1188"
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


def test_tracked_protocol_and_frozen_engine_hashes_are_fixed() -> None:
    assert _sha256(PREREGISTRATION_PATH) == EXPECTED_PREREGISTRATION_SHA256
    assert _sha256(V567_ENGINE_PATH) == EXPECTED_V567_ENGINE_SHA256

    config = NexusTradeRiskBalancedAttributionConfig()

    assert config.expected_preregistration_sha256 == (
        EXPECTED_PREREGISTRATION_SHA256
    )
    assert config.required_oos_session_count == 254
    assert config.initial_equity == Decimal("10000")
    with pytest.raises(ValidationError, match="preregistered value 10000"):
        NexusTradeRiskBalancedAttributionConfig(initial_equity="9999")


def test_preregistration_is_diagnostic_only_and_does_not_write(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "not-created"
    config = NexusTradeRiskBalancedAttributionConfig(output_root=output_root)

    payload = build_nexustrade_risk_balanced_attribution_preregistration(config)

    assert payload["protocol_id"] == (
        "v5_68_nexustrade_risk_balanced_attribution_v1"
    )
    assert payload["diagnostic_only"] is True
    assert payload["candidate_created"] is False
    assert payload["route_created"] is False
    assert payload["path_definitions"] == {
        "P": "nexustrade_monthly_independent_spy_sma_50_200_regime_filter",
        "R": "diagnostic_inverse_volatility_sizing_parent_state",
        "C": "diagnostic_subfive_partial_cash_parent_state",
        "A": (
            "nexustrade_monthly_independent_spy_sma_50_200_"
            "inverse_volatility_capped"
        ),
        "diagnostic_counterfactuals_are_candidates": False,
    }
    assert payload["return_decomposition"]["identity"] == (
        "(R-P)+(C-R)+(A-C)=A-P"
    )
    assert payload["return_decomposition"][
        "reconciliation_tolerance"
    ] == "0.000000000000000000000001"
    assert payload["parameter_search_performed"] is False
    assert payload["paper_promotion_allowed"] is False
    assert not output_root.exists()


def test_pure_sizing_selector_excludes_subfive_cash_effect() -> None:
    symbols = NEXUSTRADE_MONTHLY_STOCK_SYMBOLS
    parent_four = {symbol: Decimal("0") for symbol in symbols}
    actual_four = dict(parent_four)
    for symbol in symbols[:4]:
        parent_four[symbol] = Decimal("0.25")
        actual_four[symbol] = Decimal("0.20")

    selected_four = _select_pure_sizing_target(parent_four, actual_four)

    assert selected_four == parent_four
    assert sum(selected_four.values(), Decimal("0")) == Decimal("1.00")

    parent_six = {symbol: Decimal("0") for symbol in symbols}
    actual_six = dict(parent_six)
    parent_weight = Decimal("1") / Decimal("6")
    for symbol in symbols[:6]:
        parent_six[symbol] = parent_weight
    actual_six.update(
        {
            symbols[0]: Decimal("0.20"),
            symbols[1]: Decimal("0.16"),
            symbols[2]: Decimal("0.16"),
            symbols[3]: Decimal("0.16"),
            symbols[4]: Decimal("0.16"),
            symbols[5]: Decimal("0.16"),
        }
    )

    selected_six = _select_pure_sizing_target(parent_six, actual_six)

    assert selected_six == actual_six
    assert sum(selected_six.values(), Decimal("0")) == Decimal("1.00")


def test_full_attribution_is_deterministic_reconciled_and_diagnostic_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(PROJECT_ROOT)
    config = NexusTradeRiskBalancedAttributionConfig(
        output_root=tmp_path / "output"
    )

    first = run_nexustrade_risk_balanced_attribution(config)
    first_hashes = _output_hashes(config.output_root)
    second = run_nexustrade_risk_balanced_attribution(config)
    second_hashes = _output_hashes(config.output_root)

    assert first_hashes == second_hashes
    assert first["artifact_manifest"] == second["artifact_manifest"]
    assert first["diagnostic_only"] is True
    assert first["candidate_created"] is False
    assert first["route_created"] is False
    assert first["preview_review_created"] is False
    assert first["shadow_created"] is False
    assert first["frozen_reproduction"]["passed"] is True
    assert first["frozen_reproduction"][
        "v567_result_structured_equality"
    ] is True
    assert first["frozen_reproduction"]["full_target_hash_comparisons"] == 8
    assert first["frozen_reproduction"]["oos_target_hash_comparisons"] == 8
    assert first["diagnostic_classification"]["classification"] in {
        "no_material_harm",
        "pure_sizing_primary",
        "subfive_partial_cash_primary",
        "state_carry_primary",
        "mixed_harm",
    }
    assert first["diagnostic_classification"]["creates_route"] is False
    for cost in first["attribution"]["cost_results"]:
        for window in cost["windows"]:
            assert window["return_effects"]["passed"] is True
            assert window["constituent_contribution_attribution"][
                "passed"
            ] is True
            assert Decimal(
                window["return_effects"]["reconciliation_residual"]
            ).copy_abs() <= Decimal("1e-24")
    assert {item["path_id"] for item in first["path_results"]} == {
        "nexustrade_monthly_independent_spy_sma_50_200_regime_filter",
        "diagnostic_inverse_volatility_sizing_parent_state",
        "diagnostic_subfive_partial_cash_parent_state",
        (
            "nexustrade_monthly_independent_spy_sma_50_200_"
            "inverse_volatility_capped"
        ),
    }
    assert all(item["candidate"] is False for item in first["path_results"])
    ledger = first["parent_state_signal_ledger"]
    partial = [
        item
        for item in ledger
        if item["partial_cash_source_target_changed"] is True
    ]
    assert partial
    assert all(item["eligible_count"] in {1, 2, 3, 4} for item in partial)
    assert first["parent_state_signal_ledger_summary"][
        "partial_cash_changes_only_for_one_to_four_eligible"
    ] is True
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
    config = NexusTradeRiskBalancedAttributionConfig(
        output_root=output_root,
        preregistration_path=tampered,
    )

    with pytest.raises(ValidationError, match="tracked_preregistration_sha256"):
        run_nexustrade_risk_balanced_attribution(config)
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

    assert "nexustrade_risk_balanced_attribution" in text
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
