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
from algotrader.research.nexustrade_high_volatility_attribution import (
    NexusTradeHighVolatilityAttributionConfig,
    build_nexustrade_high_volatility_attribution_preregistration,
    run_nexustrade_high_volatility_attribution,
)
from algotrader.research.nexustrade_monthly_high_volatility_defense import (
    NexusTradeMonthlyHighVolatilityDefenseConfig,
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
    / "nexustrade_high_volatility_attribution.py"
)
DEFENSE_ENGINE_PATH = (
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
    PROJECT_ROOT / "scripts" / "run_nexustrade_high_volatility_attribution.ps1"
)
PREREGISTRATION_PATH = (
    PROJECT_ROOT
    / "docs"
    / "design"
    / "v5_66_nexustrade_high_volatility_attribution.md"
)
PARENT_PREREGISTRATION_PATH = (
    PROJECT_ROOT
    / "docs"
    / "design"
    / "v5_64_nexustrade_monthly_independent_replication.md"
)
EXPECTED_PREREGISTRATION_SHA256 = (
    "2a2d03030b2ec74ca3a0682ca94163ea5b28218c1b452b4f10664fc182733227"
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


def test_tracked_protocol_and_frozen_dependencies_are_fixed() -> None:
    assert _sha256(PREREGISTRATION_PATH) == EXPECTED_PREREGISTRATION_SHA256
    assert (
        _sha256(PARENT_PREREGISTRATION_PATH)
        == EXPECTED_PARENT_PREREGISTRATION_SHA256
    )
    assert _sha256(PARENT_ENGINE_PATH) == EXPECTED_PARENT_ENGINE_SHA256

    config = NexusTradeHighVolatilityAttributionConfig()

    assert config.expected_preregistration_sha256 == (
        EXPECTED_PREREGISTRATION_SHA256
    )
    assert config.initial_equity == Decimal("10000")
    assert config.required_oos_session_count == 254
    with pytest.raises(ValidationError, match="preregistered value 10000"):
        NexusTradeHighVolatilityAttributionConfig(initial_equity="9999")


def test_preregistration_hashes_every_dependency_without_writing(
    tmp_path: Path,
) -> None:
    config = _fixture_config(tmp_path)

    payload = build_nexustrade_high_volatility_attribution_preregistration(
        config
    )

    assert payload["protocol_id"] == (
        "v5_66_nexustrade_high_volatility_attribution_v1"
    )
    assert payload["diagnostic_only"] is True
    assert payload["candidate_created"] is False
    assert payload["route_created"] is False
    assert payload["path_definitions"] == {
        "P": NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID,
        "A": (
            "nexustrade_monthly_independent_spy_sma_50_200_"
            "high_volatility_defense"
        ),
        "D": "diagnostic_high_volatility_defense_delayed_parent_state",
        "I": "diagnostic_high_volatility_defense_immediate_parent_state",
        "diagnostic_counterfactuals_are_candidates": False,
    }
    assert payload["return_decomposition"]["reconciliation_tolerance"] == (
        "0.000000000000000000000001"
    )
    assert payload["parameter_search_performed"] is False
    assert not config.output_root.exists()


def test_full_attribution_is_deterministic_reconciled_and_diagnostic_only(
    tmp_path: Path,
) -> None:
    config = _fixture_config(tmp_path)

    first = run_nexustrade_high_volatility_attribution(config)
    first_hashes = _output_hashes(config.output_root)
    second = run_nexustrade_high_volatility_attribution(config)
    second_hashes = _output_hashes(config.output_root)

    assert first_hashes == second_hashes
    assert first["artifact_manifest"] == second["artifact_manifest"]
    assert first["diagnostic_only"] is True
    assert first["candidate_created"] is False
    assert first["route_created"] is False
    assert first["preview_review_created"] is False
    assert first["shadow_created"] is False
    assert first["frozen_reproduction"]["passed"] is True
    assert first["frozen_reproduction"]["full_target_hash_comparisons"] == 8
    assert first["frozen_reproduction"]["oos_target_hash_comparisons"] == 8
    assert first["diagnostic_classification"]["classification"] in {
        "no_material_harm",
        "classification_primary",
        "execution_delay_primary",
        "stateful_carry_primary",
        "mixed_harm",
    }
    assert first["diagnostic_classification"]["creates_route"] is False
    for cost in first["attribution"]["cost_results"]:
        for window in cost["windows"]:
            assert window["return_effects"]["passed"] is True
            assert window["constituent_contribution_attribution"]["passed"] is (
                True
            )
            assert set(window["drawdown_paths"]) == {
                NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID,
                (
                    "nexustrade_monthly_independent_spy_sma_50_200_"
                    "high_volatility_defense"
                ),
                "diagnostic_high_volatility_defense_delayed_parent_state",
                "diagnostic_high_volatility_defense_immediate_parent_state",
            }
    assert first["safety"]["network_access_attempted"] is False
    assert first["safety"]["credential_access_attempted"] is False
    assert first["safety"]["broker_access_attempted"] is False
    assert first["safety"]["paper_mutation_performed"] is False
    assert first["safety"]["live_activity_performed"] is False
    assert first["safety"]["v5_64_frozen"] is True
    assert first["safety"]["v5_65_frozen"] is True
    assert first["safety"]["max_entry_order_notional_usd"] == "25"
    assert first["safety"]["max_aggregate_marked_spy_entry_exposure_usd"] == (
        "60"
    )
    for name in (
        "preregistration.json",
        "attribution_results.json",
        "attribution_summary.md",
        "manifest.json",
    ):
        assert (config.output_root / name).is_file()


def test_tampered_frozen_result_fails_before_preregistration_write(
    tmp_path: Path,
) -> None:
    config = _fixture_config(tmp_path)
    config.v565_result_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="v565_result_sha256"):
        run_nexustrade_high_volatility_attribution(config)

    assert not (config.output_root / "preregistration.json").exists()
    assert not (config.output_root / "attribution_results.json").exists()


def test_reproduction_mismatch_fails_after_preregistration_before_result(
    tmp_path: Path,
) -> None:
    config = _fixture_config(tmp_path)
    frozen = json.loads(config.v565_result_path.read_text(encoding="utf-8"))
    frozen["candidate"]["cost_results"][0]["window_metrics"][0][
        "total_return"
    ] = "999"
    config.v565_result_path.write_text(
        json.dumps(frozen, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    bad_config = NexusTradeHighVolatilityAttributionConfig(
        **{
            **_config_kwargs(config),
            "expected_v565_result_sha256": _sha256(config.v565_result_path),
        }
    )

    with pytest.raises(ValidationError, match="window metrics"):
        run_nexustrade_high_volatility_attribution(bad_config)

    assert (bad_config.output_root / "preregistration.json").is_file()
    assert not (bad_config.output_root / "attribution_results.json").exists()


def test_module_has_safe_imports_and_fixed_counterfactuals() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "classification_effect_I_minus_P" in source
    assert "execution_delay_effect_D_minus_I" in source
    assert "stateful_carry_effect_A_minus_D" in source
    assert "diagnostic_counterfactuals_are_candidates" in source
    assert "_simulate_dynamic_candidate" in source
    assert "parameter_search_performed" in source

    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    for module_name in imported:
        assert not module_name.startswith(FORBIDDEN_IMPORT_PREFIXES)


def test_wrapper_is_offline_fail_closed_and_blocks_loaded_credentials(
    tmp_path: Path,
) -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "APP_PROFILE" in script
    assert "TIINGO_API_KEY" in script
    assert "NEXUSTRADE_API_KEY" in script
    assert "blocked_unsafe_environment" in script
    assert "Credential values are never printed" in script
    assert "PYTHONPATH" in script
    assert "algotrader.research.nexustrade_high_volatility_attribution" in script
    assert "Invoke-RestMethod" not in script
    assert "Invoke-WebRequest" not in script

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


def _fixture_config(tmp_path: Path) -> NexusTradeHighVolatilityAttributionConfig:
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
    defense_protocol_path = tmp_path / "v565_protocol.md"
    defense_protocol_path.write_text(
        "fixed synthetic V5.65 protocol\n", encoding="utf-8"
    )
    windows = (
        ReplicationWindow("oos_walk_forward_1", dates[600], dates[632]),
        ReplicationWindow("oos_walk_forward_2", dates[633], dates[665]),
        ReplicationWindow("oos_walk_forward_3", dates[666], dates[699]),
    )
    defense_root = tmp_path / "v565"
    defense_config = NexusTradeMonthlyHighVolatilityDefenseConfig(
        output_root=defense_root,
        data_path=data_path,
        data_manifest_path=data_manifest_path,
        preregistration_path=defense_protocol_path,
        parent_preregistration_path=PARENT_PREREGISTRATION_PATH,
        parent_engine_path=PARENT_ENGINE_PATH,
        expected_preregistration_sha256=_sha256(defense_protocol_path),
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
        walk_forward_windows=windows,
        required_common_session_count=len(dates),
        required_oos_session_count=100,
        minimum_indicator_sessions=365,
    )
    run_nexustrade_monthly_high_volatility_defense(defense_config)
    protocol_path = tmp_path / "v566_protocol.md"
    protocol_path.write_text(
        "fixed synthetic V5.66 protocol\n", encoding="utf-8"
    )
    return NexusTradeHighVolatilityAttributionConfig(
        output_root=tmp_path / "v566",
        data_path=data_path,
        data_manifest_path=data_manifest_path,
        preregistration_path=protocol_path,
        v564_protocol_path=PARENT_PREREGISTRATION_PATH,
        v564_engine_path=PARENT_ENGINE_PATH,
        v565_protocol_path=defense_protocol_path,
        v565_engine_path=DEFENSE_ENGINE_PATH,
        v565_preregistration_path=defense_root / "preregistration.json",
        v565_result_path=defense_root / "defense_results.json",
        v565_summary_path=defense_root / "defense_summary.md",
        v565_manifest_path=defense_root / "manifest.json",
        expected_preregistration_sha256=_sha256(protocol_path),
        expected_data_sha256=data_hash,
        expected_data_manifest_sha256=_sha256(data_manifest_path),
        expected_v564_protocol_sha256=EXPECTED_PARENT_PREREGISTRATION_SHA256,
        expected_v564_engine_sha256=EXPECTED_PARENT_ENGINE_SHA256,
        expected_v565_protocol_sha256=_sha256(defense_protocol_path),
        expected_v565_engine_sha256=_sha256(DEFENSE_ENGINE_PATH),
        expected_v565_preregistration_sha256=_sha256(
            defense_root / "preregistration.json"
        ),
        expected_v565_result_sha256=_sha256(
            defense_root / "defense_results.json"
        ),
        expected_v565_summary_sha256=_sha256(
            defense_root / "defense_summary.md"
        ),
        expected_v565_manifest_sha256=_sha256(defense_root / "manifest.json"),
        data_start=dates[0],
        data_end=dates[-1],
        train_start=dates[500],
        train_end=dates[599],
        oos_start=dates[600],
        oos_end=dates[699],
        walk_forward_windows=windows,
        required_common_session_count=len(dates),
        required_oos_session_count=100,
        minimum_indicator_sessions=365,
    )


def _config_kwargs(
    config: NexusTradeHighVolatilityAttributionConfig,
) -> dict[str, object]:
    return {
        name: getattr(config, name)
        for name in NexusTradeHighVolatilityAttributionConfig.__dataclass_fields__
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
            "attribution_results.json",
            "attribution_summary.md",
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
    from shutil import which

    for candidate in ("pwsh", "powershell"):
        path = which(candidate)
        if path is not None:
            return path
    pytest.skip("PowerShell is unavailable")


_ONE = Decimal("1")
