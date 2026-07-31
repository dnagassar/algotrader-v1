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
from algotrader.research import nexustrade_monthly_high_volatility_defense as defense
from algotrader.research.nexustrade_monthly_high_volatility_defense import (
    NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID,
    NexusTradeMonthlyHighVolatilityDefenseConfig,
    build_nexustrade_monthly_high_volatility_defense_preregistration,
    run_nexustrade_monthly_high_volatility_defense,
)
from algotrader.research.nexustrade_monthly_independent_replication import (
    NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID,
    NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
    ReplicationWindow,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "research"
    / "nexustrade_monthly_high_volatility_defense.py"
)
PARENT_ENGINE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "research"
    / "nexustrade_monthly_independent_replication.py"
)
SCRIPT_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "run_nexustrade_monthly_high_volatility_defense.ps1"
)
PREREGISTRATION_PATH = (
    PROJECT_ROOT
    / "docs"
    / "design"
    / "v5_65_nexustrade_monthly_high_volatility_defense.md"
)
PARENT_PREREGISTRATION_PATH = (
    PROJECT_ROOT
    / "docs"
    / "design"
    / "v5_64_nexustrade_monthly_independent_replication.md"
)
EXPECTED_PREREGISTRATION_SHA256 = (
    "1b614cb9d9e310704a0f8adcda224a4c540054a70af2731bcd3ec9c9b44db0c5"
)
EXPECTED_PARENT_PREREGISTRATION_SHA256 = (
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


def test_tracked_protocol_and_frozen_parent_hashes_are_fixed() -> None:
    assert _sha256(PREREGISTRATION_PATH) == EXPECTED_PREREGISTRATION_SHA256
    assert (
        _sha256(PARENT_PREREGISTRATION_PATH)
        == EXPECTED_PARENT_PREREGISTRATION_SHA256
    )
    assert _sha256(PARENT_ENGINE_PATH) == EXPECTED_PARENT_ENGINE_SHA256

    config = NexusTradeMonthlyHighVolatilityDefenseConfig()

    assert config.expected_preregistration_sha256 == (
        EXPECTED_PREREGISTRATION_SHA256
    )
    assert config.expected_parent_engine_sha256 == EXPECTED_PARENT_ENGINE_SHA256
    assert config.volatility_lookback == 20
    assert config.quantile_min_history == 252
    assert config.low_quantile == Decimal("0.33")
    assert config.high_quantile == Decimal("0.67")
    assert config.initial_equity == Decimal("10000")
    with pytest.raises(ValidationError, match="preregistered value 20"):
        NexusTradeMonthlyHighVolatilityDefenseConfig(volatility_lookback=21)
    with pytest.raises(ValidationError, match="0.33/0.67"):
        NexusTradeMonthlyHighVolatilityDefenseConfig(high_quantile="0.75")


def test_preregistration_does_not_read_prices_or_outcomes(tmp_path: Path) -> None:
    protocol_path = tmp_path / "protocol.md"
    protocol_path.write_text("fixed protocol\n", encoding="utf-8")
    config = NexusTradeMonthlyHighVolatilityDefenseConfig(
        output_root=tmp_path / "out",
        data_path=tmp_path / "missing.csv",
        data_manifest_path=tmp_path / "missing.json",
        preregistration_path=protocol_path,
        parent_preregistration_path=PARENT_PREREGISTRATION_PATH,
        parent_engine_path=PARENT_ENGINE_PATH,
        expected_preregistration_sha256=_sha256(protocol_path),
        expected_parent_preregistration_sha256=(
            EXPECTED_PARENT_PREREGISTRATION_SHA256
        ),
        expected_parent_engine_sha256=EXPECTED_PARENT_ENGINE_SHA256,
        expected_data_sha256="a" * 64,
        expected_data_manifest_sha256="b" * 64,
    )

    payload = (
        build_nexustrade_monthly_high_volatility_defense_preregistration(
            config
        )
    )

    assert payload["protocol_id"] == (
        "v5_65_nexustrade_monthly_independent_high_volatility_defense_v1"
    )
    assert payload["frozen_parent"]["altered"] is False
    assert payload["parameter_search_performed"] is False
    assert payload["volatility_regime"]["threshold_history"] == (
        "expanding_prior_only"
    )
    assert payload["paper_promotion_allowed"] is False
    assert not config.output_root.exists()


def test_full_defense_replay_is_deterministic_and_genuine(
    tmp_path: Path,
) -> None:
    config = _fixture_config(tmp_path)

    first = run_nexustrade_monthly_high_volatility_defense(config)
    first_hashes = _output_hashes(config.output_root)
    second = run_nexustrade_monthly_high_volatility_defense(config)
    second_hashes = _output_hashes(config.output_root)

    assert first_hashes == second_hashes
    assert first["artifact_manifest"] == second["artifact_manifest"]
    assert first["claim"] == "independent_followup_not_authentic_source_replay"
    assert first["parameter_search_performed"] is False
    assert first["paper_promotion_allowed"] is False
    assert first["frozen_parent"]["altered"] is False
    assert first["overlay_integrity"]["passed"] is True
    assert (
        first["overlay_integrity"]["oos_target_difference_session_count"] > 0
    )
    candidate = first["candidate"]
    assert candidate["candidate_id"] == (
        NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID
    )
    assert candidate["parent_candidate_ids"] == [
        NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID
    ]
    assert candidate["role"] == "volatility_regime_filter"
    assert candidate["route"] in {
        "preview_review",
        "continue_local_research",
        "reject",
    }
    repair = candidate["gates"]["targeted_parent_repair_gate"]
    assert repair["forced_cash_session_count"] > 0
    assert repair["forced_cash_required"] is True
    assert first["safety"]["network_access_attempted"] is False
    assert first["safety"]["credential_access_attempted"] is False
    assert first["safety"]["broker_access_attempted"] is False
    assert first["safety"]["paper_mutation_performed"] is False
    assert first["safety"]["live_activity_performed"] is False
    assert first["safety"]["v5_64_frozen"] is True
    assert first["artifact_manifest"]["manifest_self_hash_embedded"] is False
    for name in (
        "preregistration.json",
        "defense_results.json",
        "defense_summary.md",
        "manifest.json",
    ):
        assert (config.output_root / name).is_file()


def test_tampered_parent_engine_fails_before_artifact_write(
    tmp_path: Path,
) -> None:
    config = _fixture_config(tmp_path)
    copied_parent = tmp_path / "parent.py"
    copied_parent.write_bytes(PARENT_ENGINE_PATH.read_bytes())
    copied_hash = _sha256(copied_parent)
    copied_parent.write_text("tampered\n", encoding="utf-8")
    bad_config = NexusTradeMonthlyHighVolatilityDefenseConfig(
        **{
            **_config_kwargs(config),
            "parent_engine_path": copied_parent,
            "expected_parent_engine_sha256": copied_hash,
        }
    )

    with pytest.raises(ValidationError, match="parent_engine_sha256"):
        run_nexustrade_monthly_high_volatility_defense(bad_config)

    assert not (bad_config.output_root / "preregistration.json").exists()
    assert not (bad_config.output_root / "defense_results.json").exists()


def test_module_reuses_fixed_prior_only_regime_and_has_safe_imports() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "compute_realized_volatility_series" in source
    assert "classify_realized_volatility_series" in source
    assert "quantile_min_history" in source
    assert "parameter_search_performed" in source
    assert "_simulate_dynamic_candidate" in source

    tree = ast.parse(source)
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
    assert (
        "algotrader.research.nexustrade_monthly_high_volatility_defense"
        in script
    )
    assert "Invoke-RestMethod" not in script
    assert "Invoke-WebRequest" not in script


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


def _fixture_config(
    tmp_path: Path,
) -> NexusTradeMonthlyHighVolatilityDefenseConfig:
    dates = _weekdays(date(2019, 1, 2), 700)
    data_path = tmp_path / "canonical.csv"
    _write_price_data(data_path, dates)
    data_hash = _sha256(data_path)
    data_manifest_path = tmp_path / "data_manifest.json"
    data_manifest = {
        "canonical_data_ready": True,
        "symbols": [*NEXUSTRADE_MONTHLY_STOCK_SYMBOLS, "SPY"],
        "provider_symbol_map": {
            symbol: symbol
            for symbol in (*NEXUSTRADE_MONTHLY_STOCK_SYMBOLS, "SPY")
        },
        "combined_output_sha256": data_hash,
        "session_reference_count": len(dates),
    }
    data_manifest_path.write_text(
        json.dumps(data_manifest, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    preregistration_path = tmp_path / "protocol.md"
    preregistration_path.write_text(
        "fixed test high-volatility defense protocol\n",
        encoding="utf-8",
    )
    return NexusTradeMonthlyHighVolatilityDefenseConfig(
        output_root=tmp_path / "out",
        data_path=data_path,
        data_manifest_path=data_manifest_path,
        preregistration_path=preregistration_path,
        parent_preregistration_path=PARENT_PREREGISTRATION_PATH,
        parent_engine_path=PARENT_ENGINE_PATH,
        expected_preregistration_sha256=_sha256(preregistration_path),
        expected_parent_preregistration_sha256=(
            EXPECTED_PARENT_PREREGISTRATION_SHA256
        ),
        expected_parent_engine_sha256=EXPECTED_PARENT_ENGINE_SHA256,
        expected_data_sha256=data_hash,
        expected_data_manifest_sha256=_sha256(data_manifest_path),
        data_start=dates[0],
        data_end=dates[-1],
        train_start=dates[500],
        train_end=dates[599],
        oos_start=dates[600],
        oos_end=dates[699],
        walk_forward_windows=(
            ReplicationWindow(
                "oos_walk_forward_1",
                dates[600],
                dates[632],
            ),
            ReplicationWindow(
                "oos_walk_forward_2",
                dates[633],
                dates[665],
            ),
            ReplicationWindow(
                "oos_walk_forward_3",
                dates[666],
                dates[699],
            ),
        ),
        required_common_session_count=len(dates),
        required_oos_session_count=100,
        minimum_indicator_sessions=365,
    )


def _config_kwargs(
    config: NexusTradeMonthlyHighVolatilityDefenseConfig,
) -> dict[str, object]:
    return {
        "output_root": config.output_root,
        "data_path": config.data_path,
        "data_manifest_path": config.data_manifest_path,
        "preregistration_path": config.preregistration_path,
        "parent_preregistration_path": config.parent_preregistration_path,
        "parent_engine_path": config.parent_engine_path,
        "expected_preregistration_sha256": (
            config.expected_preregistration_sha256
        ),
        "expected_parent_preregistration_sha256": (
            config.expected_parent_preregistration_sha256
        ),
        "expected_parent_engine_sha256": config.expected_parent_engine_sha256,
        "expected_data_sha256": config.expected_data_sha256,
        "expected_data_manifest_sha256": (
            config.expected_data_manifest_sha256
        ),
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
        "volatility_lookback": config.volatility_lookback,
        "quantile_min_history": config.quantile_min_history,
        "low_quantile": config.low_quantile,
        "high_quantile": config.high_quantile,
    }


def _write_price_data(path: Path, dates: tuple[date, ...]) -> None:
    rows = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    symbols = (*NEXUSTRADE_MONTHLY_STOCK_SYMBOLS, "SPY")
    for symbol_index, symbol in enumerate(symbols):
        price = Decimal("100") + Decimal(symbol_index)
        for index, on_date in enumerate(dates):
            if symbol == "SPY":
                if 610 <= index <= 640:
                    daily_return = (
                        Decimal("0.05")
                        if index % 2 == 0
                        else Decimal("-0.035")
                    )
                else:
                    daily_return = (
                        Decimal("0.0015")
                        if index % 3
                        else Decimal("0.0005")
                    )
                price *= _ONE + daily_return
            else:
                price *= Decimal("1.0008") + (
                    Decimal(symbol_index) * Decimal("0.00001")
                )
            price = price.quantize(Decimal("0.00000001"))
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
            "defense_results.json",
            "defense_summary.md",
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
        "ALPACA_API_SECRET",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_ENDPOINT",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "APCA_API_BASE_URL",
        "NEXUSTRADE_API_KEY",
        "NEXUSTRADE_ACCESS_TOKEN",
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


_ONE = Decimal("1")
