from __future__ import annotations

import ast
from datetime import date
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research import diversified_etf_absolute_trend as subject

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "docs/design/v5_71_diversified_etf_absolute_trend_preregistration.md"
RECEIPT = ROOT / "docs/design/v5_71_diversified_etf_absolute_trend_data_receipt.md"
DATA = ROOT / "runs/v5_71_diversified_etf_absolute_trend/canonical_data.csv"
MODULE = ROOT / "src/algotrader/research/diversified_etf_absolute_trend.py"
SCRIPT = ROOT / "scripts/run_diversified_etf_absolute_trend.ps1"


def test_protocol_and_receipt_hashes_are_frozen() -> None:
    assert _hash(PROTOCOL) == "afa4254ceac06f643fd51fd2df63364ce14a38f01ba8392e664d8e478bc57d17"
    assert _hash(RECEIPT) == "ca782882cb499ea2e956fc36658df4f76f88fff06b4a69b293ced4a70c213525"


def test_preregistration_is_terminal_and_outcome_blind(tmp_path: Path) -> None:
    payload = subject.build_diversified_etf_absolute_trend_preregistration()

    assert payload["candidate_id"] == "diversified_etf_absolute_trend_10m"
    assert payload["lookback_months"] == 10
    assert payload["parameter_search_performed"] is False
    assert payload["source_metrics_used"] is False
    assert payload["terminal_routes"] == [
        "preview_review",
        "close_diversified_etf_absolute_trend",
    ]
    assert payload["paper_promotion_allowed"] is False
    assert list(tmp_path.iterdir()) == []


def test_action_is_lagged_and_weights_drift_between_monthly_actions() -> None:
    dates = (date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 6))
    prices = {
        symbol: (
            Decimal("100"),
            Decimal("100"),
            Decimal("200") if symbol == "SPY" else Decimal("100"),
        )
        for symbol in subject.SYMBOLS
    }
    data = subject._AlignedData(dates, prices, "data", "manifest")
    target = {symbol: Decimal("0.20") for symbol in subject.SYMBOLS}

    simulation = subject._simulate(data, {dates[1]: target}, Decimal("0"))

    assert simulation.records[0].strategy_return == Decimal("0")
    assert simulation.records[0].weights_after_close == target
    assert simulation.records[1].strategy_return == Decimal("0.20")
    assert simulation.records[1].weights_after_close["SPY"] == Decimal("1") / Decimal("3")
    assert simulation.records[1].weights_after_close["QQQ"] == Decimal("1") / Decimal("6")


def test_canonical_replay_is_deterministic_and_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not DATA.is_file():
        pytest.skip("ignored canonical V5.71 data are not present")
    monkeypatch.chdir(ROOT)
    output = tmp_path / "evaluation"

    first = subject.run_diversified_etf_absolute_trend(output)
    first_hashes = {path.name: _hash(path) for path in output.iterdir() if path.is_file()}
    second = subject.run_diversified_etf_absolute_trend(output)
    second_hashes = {path.name: _hash(path) for path in output.iterdir() if path.is_file()}

    assert first_hashes == second_hashes
    assert first["terminal_decision"]["route"] == "close_diversified_etf_absolute_trend"
    assert first["gates"]["oos_viability"]["passed"] is True
    assert first["gates"]["friction_stability"]["passed"] is True
    assert first["gates"]["diversification"]["passed"] is True
    assert first["gates"]["static_equal_weight_value"]["passed"] is False
    assert first["gates"]["spy_value"]["passed"] is False
    assert first["terminal_decision"]["paper_promotion_allowed"] is False
    assert first["safety"]["network_access"] is False
    assert first["safety"]["broker_access"] is False


def test_tampered_receipt_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tampered = tmp_path / "receipt.md"
    tampered.write_text(RECEIPT.read_text(encoding="utf-8") + "tamper\n", encoding="utf-8")
    monkeypatch.setattr(subject, "_RECEIPT", tampered)

    with pytest.raises(ValidationError, match="data receipt SHA-256 mismatch"):
        subject.build_diversified_etf_absolute_trend_preregistration()


def test_module_and_wrapper_are_offline_fail_closed(tmp_path: Path) -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    assert not any(
        name.startswith(
            ("requests", "httpx", "socket", "alpaca", "algotrader.execution", "algotrader.broker")
        )
        for name in imports
    )
    script = SCRIPT.read_text(encoding="utf-8")
    assert "preflight_sensitive_variables_loaded" in script
    assert "blocked_unsafe_environment" in script
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        return
    env = os.environ.copy()
    env["TIINGO_API_KEY"] = "sentinel-not-a-real-secret"
    completed = subprocess.run(
        [powershell, "-NoProfile", "-File", str(SCRIPT), "-OutputRoot", str(tmp_path / "blocked")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    combined = completed.stdout + completed.stderr
    assert completed.returncode == 2
    assert "preflight_sensitive_variables_loaded=true" in combined
    assert env["TIINGO_API_KEY"] not in combined


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
