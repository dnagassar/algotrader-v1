from __future__ import annotations

import ast
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research import nexustrade_monthly_independent_replication as rep
from algotrader.research.nexustrade_monthly_independent_replication import (
    NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID,
    NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID,
    NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
    NexusTradeMonthlyIndependentReplicationConfig,
    ReplicationWindow,
    build_nexustrade_monthly_independent_preregistration,
    run_nexustrade_monthly_independent_replication,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "research"
    / "nexustrade_monthly_independent_replication.py"
)
SCRIPT_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "run_nexustrade_monthly_independent_replication.ps1"
)
PREREGISTRATION_PATH = (
    PROJECT_ROOT
    / "docs"
    / "design"
    / "v5_64_nexustrade_monthly_independent_replication.md"
)
EXPECTED_PREREGISTRATION_SHA256 = (
    "f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0"
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


def test_tracked_preregistration_hash_and_fixed_defaults() -> None:
    assert _sha256(PREREGISTRATION_PATH) == EXPECTED_PREREGISTRATION_SHA256
    config = NexusTradeMonthlyIndependentReplicationConfig()

    assert config.expected_preregistration_sha256 == (
        EXPECTED_PREREGISTRATION_SHA256
    )
    assert config.train_start == date(2021, 12, 31)
    assert config.train_end == date(2024, 3, 24)
    assert config.oos_start == date(2024, 3, 24)
    assert config.oos_end == date(2025, 3, 28)
    assert config.required_common_session_count == 1569
    assert config.required_oos_session_count == 254
    assert tuple(
        (window.start, window.end) for window in config.walk_forward_windows
    ) == (
        (date(2024, 3, 25), date(2024, 7, 24)),
        (date(2024, 7, 25), date(2024, 11, 21)),
        (date(2024, 11, 22), date(2025, 3, 28)),
    )
    with pytest.raises(ValidationError, match="preregistered value 10000"):
        NexusTradeMonthlyIndependentReplicationConfig(initial_equity="9999")


def test_full_independent_replication_writes_deterministic_hashed_artifacts(
    tmp_path: Path,
) -> None:
    config = _fixture_config(tmp_path)

    first = run_nexustrade_monthly_independent_replication(config)
    first_hashes = _output_hashes(config.output_root)
    second = run_nexustrade_monthly_independent_replication(config)
    second_hashes = _output_hashes(config.output_root)

    assert first_hashes == second_hashes
    assert first["claim"] == "independent_replication_not_authentic_source_replay"
    assert first["source_metrics_used_for_ranking"] is False
    assert first["source_metrics_used_for_promotion"] is False
    assert first["paper_promotion_allowed"] is False
    assert first["safety"]["network_access_attempted"] is False
    assert first["safety"]["credential_access_attempted"] is False
    assert first["safety"]["broker_access_attempted"] is False
    assert first["safety"]["paper_mutation_performed"] is False
    assert first["safety"]["live_activity_performed"] is False
    assert first["artifact_manifest"] == second["artifact_manifest"]
    assert first["artifact_manifest"]["manifest_self_hash_embedded"] is False
    assert len(first["artifact_manifest"]["artifacts"]) == 3

    candidates = {
        candidate["candidate_id"]: candidate for candidate in first["candidates"]
    }
    assert set(candidates) == {
        NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID,
        NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID,
    }
    assert all(
        candidate["route"]
        in {"preview_review", "continue_local_research", "reject"}
        for candidate in candidates.values()
    )
    composite = candidates[NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID]
    assert composite["parent_strategy_ids"] == ["spy_sma_50_200_baseline"]
    assert composite["role"] == "risk_regime_filter"
    assert first["composite_integrity"]["passed"] is True
    assert (
        first["composite_integrity"]["oos_target_difference_session_count"] > 0
    )

    for name in (
        "preregistration.json",
        "replication_results.json",
        "replication_summary.md",
        "manifest.json",
    ):
        assert (config.output_root / name).is_file()


def test_preregistration_payload_does_not_read_data_or_outcomes(
    tmp_path: Path,
) -> None:
    preregistration = tmp_path / "protocol.md"
    preregistration.write_text("fixed protocol\n", encoding="utf-8")
    config = NexusTradeMonthlyIndependentReplicationConfig(
        output_root=tmp_path / "out",
        data_path=tmp_path / "missing.csv",
        data_manifest_path=tmp_path / "missing.json",
        preregistration_path=preregistration,
        expected_preregistration_sha256=_sha256(preregistration),
        expected_data_sha256="a" * 64,
        expected_data_manifest_sha256="b" * 64,
    )

    payload = build_nexustrade_monthly_independent_preregistration(config)

    assert payload["protocol_id"] == (
        "v5_64_nexustrade_monthly_independent_replication_v1"
    )
    assert payload["paper_promotion_allowed"] is False
    assert payload["source_metrics_used_for_ranking"] is False
    assert payload["fill_assumptions"]["same_close_fill_allowed"] is False
    assert not config.output_root.exists()


def test_tampered_preregistration_fails_before_result_write(tmp_path: Path) -> None:
    config = _fixture_config(tmp_path)
    config.preregistration_path.write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="preregistration SHA-256"):
        run_nexustrade_monthly_independent_replication(config)

    assert not (config.output_root / "preregistration.json").exists()
    assert not (config.output_root / "replication_results.json").exists()


def test_manifest_hash_or_symbol_mapping_mismatch_fails_closed(
    tmp_path: Path,
) -> None:
    config = _fixture_config(tmp_path)
    manifest = json.loads(config.data_manifest_path.read_text(encoding="utf-8"))
    manifest["provider_symbol_map"]["BRK-B"] = "BRK.B"
    config.data_manifest_path.write_text(
        json.dumps(manifest, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    bad_config = NexusTradeMonthlyIndependentReplicationConfig(
        **{
            **_config_kwargs(config),
            "expected_data_manifest_sha256": _sha256(
                config.data_manifest_path
            ),
        }
    )

    with pytest.raises(ValidationError, match="BRK-B mapping"):
        run_nexustrade_monthly_independent_replication(bad_config)

    assert (bad_config.output_root / "preregistration.json").is_file()
    assert not (bad_config.output_root / "replication_results.json").exists()


def test_stateful_calendar_day_rule_and_simple_rsi_semantics() -> None:
    assert rep._rebalance_ready(date(2025, 1, 2), None, None) is True
    assert (
        rep._rebalance_ready(
            date(2025, 1, 31),
            date(2025, 1, 2),
            date(2025, 1, 2),
        )
        is False
    )
    assert (
        rep._rebalance_ready(
            date(2025, 2, 1),
            date(2025, 1, 2),
            date(2025, 1, 2),
        )
        is True
    )
    rising = tuple(Decimal(index + 1) for index in range(15))
    flat = tuple(Decimal("10") for _ in range(15))
    assert rep._simple_rsi(rising, 14, 14) == Decimal("100")
    assert rep._simple_rsi(flat, 14, 14) == Decimal("50")

    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "_rebalance_ready" in source
    assert ".days >= _CALENDAR_REBALANCE_DAYS" in source
    assert "_is_rebalance_index" not in source
    assert "same_close_fill_allowed" in source


def test_module_has_no_network_broker_execution_or_risk_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    for module_name in imported:
        assert not module_name.startswith(FORBIDDEN_IMPORT_PREFIXES)


def test_wrapper_is_offline_fail_closed_and_pins_current_src() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "APP_PROFILE" in script
    assert "TIINGO_API_KEY" in script
    assert "NEXUSTRADE_API_KEY" in script
    assert "blocked_unsafe_environment" in script
    assert "Credential values are never printed" in script
    assert "PYTHONPATH" in script
    assert "algotrader.research.nexustrade_monthly_independent_replication" in script
    assert "Invoke-RestMethod" not in script
    assert "Invoke-WebRequest" not in script
    assert "paper" in script
    assert "live" in script


def test_wrapper_blocks_loaded_profile_without_invoking_python(
    tmp_path: Path,
) -> None:
    capture_path = tmp_path / "called.txt"
    env = _fake_python_env(tmp_path, capture_path)
    env["APP_PROFILE"] = "paper"
    env["TIINGO_API_KEY"] = "must-never-be-printed"

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-File",
            str(SCRIPT_PATH),
            "-OutputRoot",
            str(tmp_path / "out"),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "preflight_APP_PROFILE_is_paper=true" in result.stdout
    assert "preflight_sensitive_variables_loaded=true" in result.stdout
    assert "must-never-be-printed" not in result.stdout
    assert "blocked_unsafe_environment" in result.stderr
    assert not capture_path.exists()


def _fixture_config(tmp_path: Path) -> NexusTradeMonthlyIndependentReplicationConfig:
    dates = _weekdays(date(2020, 1, 2), 560)
    data_path = tmp_path / "canonical.csv"
    _write_price_data(data_path, dates)
    data_hash = _sha256(data_path)
    data_manifest_path = tmp_path / "data_manifest.json"
    data_manifest = {
        "canonical_data_ready": True,
        "symbols": [*NEXUSTRADE_MONTHLY_STOCK_SYMBOLS, "SPY"],
        "provider_symbol_map": {
            symbol: symbol for symbol in (*NEXUSTRADE_MONTHLY_STOCK_SYMBOLS, "SPY")
        },
        "combined_output_sha256": data_hash,
        "session_reference_count": len(dates),
    }
    data_manifest_path.write_text(
        json.dumps(data_manifest, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    preregistration_path = tmp_path / "protocol.md"
    preregistration_path.write_text("fixed test protocol\n", encoding="utf-8")
    train_start_index = 400
    train_end_index = 499
    oos_start_index = 500
    oos_end_index = 559
    return NexusTradeMonthlyIndependentReplicationConfig(
        output_root=tmp_path / "out",
        data_path=data_path,
        data_manifest_path=data_manifest_path,
        preregistration_path=preregistration_path,
        expected_preregistration_sha256=_sha256(preregistration_path),
        expected_data_sha256=data_hash,
        expected_data_manifest_sha256=_sha256(data_manifest_path),
        data_start=dates[0],
        data_end=dates[-1],
        train_start=dates[train_start_index],
        train_end=dates[train_end_index],
        oos_start=dates[oos_start_index],
        oos_end=dates[oos_end_index],
        walk_forward_windows=(
            ReplicationWindow(
                "oos_walk_forward_1",
                dates[500],
                dates[519],
            ),
            ReplicationWindow(
                "oos_walk_forward_2",
                dates[520],
                dates[539],
            ),
            ReplicationWindow(
                "oos_walk_forward_3",
                dates[540],
                dates[559],
            ),
        ),
        required_common_session_count=len(dates),
        required_oos_session_count=oos_end_index - oos_start_index + 1,
        minimum_indicator_sessions=365,
    )


def _config_kwargs(
    config: NexusTradeMonthlyIndependentReplicationConfig,
) -> dict[str, object]:
    return {
        "output_root": config.output_root,
        "data_path": config.data_path,
        "data_manifest_path": config.data_manifest_path,
        "preregistration_path": config.preregistration_path,
        "expected_preregistration_sha256": config.expected_preregistration_sha256,
        "expected_data_sha256": config.expected_data_sha256,
        "expected_data_manifest_sha256": config.expected_data_manifest_sha256,
        "initial_equity": config.initial_equity,
        "data_start": config.data_start,
        "data_end": config.data_end,
        "train_start": config.train_start,
        "train_end": config.train_end,
        "oos_start": config.oos_start,
        "oos_end": config.oos_end,
        "walk_forward_windows": config.walk_forward_windows,
        "required_common_session_count": config.required_common_session_count,
        "required_oos_session_count": config.required_oos_session_count,
        "minimum_indicator_sessions": config.minimum_indicator_sessions,
    }


def _write_price_data(path: Path, dates: tuple[date, ...]) -> None:
    rows = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    symbols = (*NEXUSTRADE_MONTHLY_STOCK_SYMBOLS, "SPY")
    for symbol_index, symbol in enumerate(symbols):
        for index, on_date in enumerate(dates):
            if symbol == "SPY":
                if index < 400:
                    price = Decimal("100")
                elif index < 500:
                    price = Decimal("100") + Decimal(index - 400) * Decimal("0.5")
                else:
                    price = Decimal("150") - Decimal(index - 500) * Decimal("1.5")
            else:
                price = (
                    Decimal("100")
                    + Decimal(symbol_index)
                    + Decimal(index) * Decimal("0.05")
                )
            rows.append(
                f"{symbol},{on_date.isoformat()},{price},{price},{price},"
                f"{price},{price},1000"
            )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _weekdays(start: date, count: int) -> tuple[date, ...]:
    dates = []
    current = start
    while len(dates) < count:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return tuple(dates)


def _output_hashes(root: Path) -> dict[str, str]:
    return {
        name: _sha256(root / name)
        for name in (
            "preregistration.json",
            "replication_results.json",
            "replication_summary.md",
            "manifest.json",
        )
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        f'echo called> "{capture_path}"\r\n'
        "exit /B 0\r\n",
        encoding="utf-8",
        newline="",
    )
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    for name in (
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_KEY_ID",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "NEXUSTRADE_API_KEY",
        "TIINGO_API_KEY",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    for candidate in ("pwsh", "powershell"):
        path = _which(candidate)
        if path is not None:
            return path
    pytest.skip("PowerShell is unavailable")


def _which(command: str) -> str | None:
    from shutil import which

    return which(command)
