from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from datetime import date, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research.nexustrade_strategy_intake import (
    NEXUSTRADE_INTAKE_LABELS,
    NexusTradeStrategyIntakeConfig,
    build_nexustrade_strategy_intake_payload,
    load_nexustrade_strategy_batch,
    run_nexustrade_strategy_intake,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "research"
    / "nexustrade_strategy_intake.py"
)
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_nexustrade_strategy_intake.ps1"

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


def test_valid_intake_runs_existing_local_challenger_replay(tmp_path: Path) -> None:
    input_path = tmp_path / "nexustrade.json"
    data_path = tmp_path / "spy.csv"
    output_root = tmp_path / "out"
    _write_json(input_path, _batch())
    _write_price_csv(data_path, _trend_then_drawdown_prices())

    result = run_nexustrade_strategy_intake(
        NexusTradeStrategyIntakeConfig(
            input_path=input_path,
            output_root=output_root,
            data_path=data_path,
            as_of="2026-07-29",
            fee_bps="1",
            slippage_bps="2",
        )
    )

    assert result["record_type"] == "nexustrade_strategy_intake"
    assert result["labels"] == list(NEXUSTRADE_INTAKE_LABELS)
    assert result["eligible_candidate_count"] == 1
    assert result["source_metrics_used_for_ranking"] is False
    assert result["source_metrics_used_for_promotion"] is False
    assert result["paper_promotion_allowed"] is False
    assert result["broker_access_attempted"] is False
    assert result["network_access_attempted"] is False
    candidate = result["candidates"][0]
    assert candidate["intake_status"] == "ready_for_local_replay"
    assert candidate["local_replay_eligible"] is True
    assert candidate["local_candidate"]["fast_window"] == 30
    assert candidate["local_candidate"]["slow_window"] == 150
    replay = result["local_replay"]
    assert replay["status"] == "completed"
    assert replay["eligible_candidate_ids"] == ["nexus_spy_sma_30_150"]
    assert replay["source_metrics_used_for_ranking"] is False
    assert replay["paper_promotion_allowed"] is False
    assert replay["results"]
    assert {
        item["candidate_id"] for item in replay["results"]
    } == {"nexus_spy_sma_30_150"}
    assert result["candidate_routes"][0]["route"] in {
        "preview_review",
        "continue_local_research",
        "reject",
    }
    assert (output_root / "local_replay" / "challenger_results.json").is_file()
    report = json.loads(
        (output_root / "nexustrade_intake_report.json").read_text(encoding="utf-8")
    )
    assert report == result


def test_exact_existing_local_strategy_is_rejected_as_duplicate() -> None:
    candidate = _candidate(
        candidate_id="nexus_spy_sma_50_200",
        parameters={"fast_window": 50, "slow_window": 200},
    )

    payload, replay_candidates = build_nexustrade_strategy_intake_payload(
        _batch(candidates=[candidate]),
        input_sha256="a" * 64,
    )

    assert replay_candidates == ()
    assert payload["eligible_candidate_count"] == 0
    assert payload["classification_counts"]["rejected_duplicate"] == 1
    assert payload["candidates"][0]["intake_status"] == "rejected_duplicate"
    assert payload["candidates"][0]["blockers"] == [
        "duplicate_existing_local_candidate"
    ]


def test_reserved_operating_strategy_id_cannot_enter_replay() -> None:
    candidate = _candidate(candidate_id="spy_rsi_14_mean_reversion_paper")

    payload, replay_candidates = build_nexustrade_strategy_intake_payload(
        _batch(candidates=[candidate]),
        input_sha256="a" * 64,
    )

    assert replay_candidates == ()
    assert payload["candidates"][0]["intake_status"] == "rejected_duplicate"
    assert "reserved_operating_strategy_id" in payload["candidates"][0]["blockers"]


def test_incomplete_source_evidence_is_retained_but_not_replayed() -> None:
    candidate = _candidate(
        source_backtest={
            "start_date": None,
            "end_date": None,
            "data_mode": None,
            "validation_method": "none",
            "fee_bps": None,
            "slippage_bps": None,
            "trade_count": 0,
            "metrics": {
                "total_return": None,
                "max_drawdown": None,
                "sharpe_ratio": None,
            },
        }
    )

    payload, replay_candidates = build_nexustrade_strategy_intake_payload(
        _batch(candidates=[candidate]),
        input_sha256="b" * 64,
    )

    record = payload["candidates"][0]
    assert replay_candidates == ()
    assert record["intake_status"] == "needs_source_evidence"
    assert set(record["blockers"]) == {
        "source_backtest_dates_missing",
        "source_data_mode_missing",
        "source_out_of_sample_validation_missing",
        "source_cost_assumptions_missing",
        "source_trade_count_missing",
        "source_summary_metrics_missing",
    }


def test_unsupported_family_is_routed_to_adapter_without_false_replay() -> None:
    candidate = _candidate(
        family="rsi_trend_filter_long_only",
        parameters={
            "rsi_window": 14,
            "entry_threshold": "30",
            "exit_threshold": "70",
            "trend_window": 200,
        },
    )

    payload, replay_candidates = build_nexustrade_strategy_intake_payload(
        _batch(candidates=[candidate]),
        input_sha256="c" * 64,
    )

    record = payload["candidates"][0]
    assert replay_candidates == ()
    assert record["intake_status"] == "needs_local_adapter"
    assert record["blockers"] == ["local_strategy_family_adapter_required"]
    assert record["local_candidate"] is None


def test_supported_family_parameter_not_yet_modeled_needs_adapter() -> None:
    candidate = _candidate(
        family="drawdown_filter_long_only",
        parameters={"lookback_days": 252, "max_drawdown_percent": "15"},
    )

    payload, replay_candidates = build_nexustrade_strategy_intake_payload(
        _batch(candidates=[candidate]),
        input_sha256="d" * 64,
    )

    assert replay_candidates == ()
    assert payload["candidates"][0]["intake_status"] == "needs_local_adapter"
    assert payload["candidates"][0]["blockers"] == [
        "local_parameter_adapter_required"
    ]


def test_lineage_and_pairing_role_are_preserved_but_not_authority() -> None:
    candidate = _candidate(
        parent_strategy_ids=["spy_sma_50_200_training_wheel"],
        pairing_role="confirmation_filter",
    )

    payload, replay_candidates = build_nexustrade_strategy_intake_payload(
        _batch(candidates=[candidate]),
        input_sha256="e" * 64,
    )

    record = payload["candidates"][0]
    assert len(replay_candidates) == 1
    assert record["parent_strategy_ids"] == ["spy_sma_50_200_training_wheel"]
    assert record["pairing_role"] == "confirmation_filter"
    assert record["source_metrics_trust"] == "untrusted_external_evidence"
    assert record["source_metrics_used_for_promotion"] is False
    assert payload["paper_promotion_allowed"] is False


def test_duplicate_candidate_ids_fail_closed() -> None:
    candidate = _candidate()

    with pytest.raises(ValidationError, match="duplicate candidate_id"):
        build_nexustrade_strategy_intake_payload(
            _batch(candidates=[candidate, dict(candidate)]),
            input_sha256="f" * 64,
        )


def test_candidate_cannot_name_itself_as_parent() -> None:
    candidate = _candidate(parent_strategy_ids=["nexus_spy_sma_30_150"])

    with pytest.raises(ValidationError, match="cannot name itself"):
        build_nexustrade_strategy_intake_payload(
            _batch(candidates=[candidate]),
            input_sha256="0" * 64,
        )


@pytest.mark.parametrize(
    "source_url",
    (
        "http://nexustrade.io/library",
        "https://example.com/strategy",
        "https://nexustrade.io/library?token=value",
        "https://user@nexustrade.io/library",
    ),
)
def test_noncanonical_or_sensitive_source_url_is_rejected(source_url: str) -> None:
    with pytest.raises(ValidationError, match="source_url"):
        build_nexustrade_strategy_intake_payload(
            _batch(source_url=source_url),
            input_sha256="1" * 64,
        )


def test_input_loader_rejects_sensitive_fields_without_echoing_values(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "sensitive.json"
    payload = _batch()
    payload["api_key"] = "must-never-be-echoed"
    _write_json(input_path, payload)

    with pytest.raises(ValidationError) as exc_info:
        load_nexustrade_strategy_batch(input_path)

    assert "forbidden sensitive field" in str(exc_info.value)
    assert "must-never-be-echoed" not in str(exc_info.value)


def test_input_loader_rejects_sensitive_text_without_echoing_value(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "sensitive_text.json"
    payload = _batch()
    payload["candidates"][0]["hypothesis"] = "Bearer must-never-be-echoed"
    _write_json(input_path, payload)

    with pytest.raises(ValidationError) as exc_info:
        load_nexustrade_strategy_batch(input_path)

    assert "forbidden sensitive text" in str(exc_info.value)
    assert "must-never-be-echoed" not in str(exc_info.value)


def test_config_is_frozen_slotted_and_validates_finite_costs(tmp_path: Path) -> None:
    config = NexusTradeStrategyIntakeConfig(
        input_path=tmp_path / "input.json",
        output_root=tmp_path / "out",
    )

    assert hasattr(config, "__slots__")
    assert not hasattr(config, "__dict__")
    with pytest.raises(FrozenInstanceError):
        config.fee_bps = Decimal("1")
    with pytest.raises(ValidationError, match="finite"):
        NexusTradeStrategyIntakeConfig(
            input_path=tmp_path / "input.json",
            output_root=tmp_path / "out",
            fee_bps="NaN",
        )


def test_module_imports_no_network_broker_or_execution_modules() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    violations = [
        module
        for module in imports
        if any(
            module == prefix or module.startswith(f"{prefix}.")
            for prefix in FORBIDDEN_IMPORT_PREFIXES
        )
    ]
    assert violations == []


def test_wrapper_is_offline_and_forwards_paths_without_secret_arguments(
    tmp_path: Path,
) -> None:
    capture_path = tmp_path / "args.txt"
    env = _fake_python_env(tmp_path, capture_path)

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-File",
            str(SCRIPT_PATH),
            "-InputPath",
            str(tmp_path / "input.json"),
            "-OutputRoot",
            str(tmp_path / "out"),
            "-BarsCsv",
            str(tmp_path / "bars.csv"),
            "-AsOfDate",
            "2026-07-29",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "preflight_APP_PROFILE_is_paper=false" in result.stdout
    assert "preflight_APP_PROFILE_is_live=false" in result.stdout
    assert "preflight_sensitive_variables_loaded=false" in result.stdout
    assert "Credential values are never printed" in result.stdout
    arguments = capture_path.read_text(encoding="utf-8")
    assert "algotrader.research.nexustrade_strategy_intake" in arguments
    assert "--input-path" in arguments
    assert "--data-path" in arguments
    assert "--as-of-date 2026-07-29" in arguments
    assert "NEXUSTRADE_API_KEY" not in arguments
    script_text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "Invoke-RestMethod" not in script_text
    assert "Invoke-WebRequest" not in script_text


def test_wrapper_blocks_loaded_profile_and_credentials_without_leaking_values(
    tmp_path: Path,
) -> None:
    capture_path = tmp_path / "args.txt"
    env = _fake_python_env(tmp_path, capture_path)
    env["APP_PROFILE"] = "paper"
    env["APCA_API_KEY_ID"] = "must-never-be-printed"
    env["NEXUSTRADE_API_KEY"] = "also-must-never-be-printed"

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-File",
            str(SCRIPT_PATH),
            "-InputPath",
            str(tmp_path / "input.json"),
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
    assert "blocked_unsafe_environment" in result.stdout
    assert "must-never-be-printed" not in result.stdout
    assert not capture_path.exists()


def _batch(
    *,
    candidates: list[dict[str, object]] | None = None,
    source_url: str = "https://nexustrade.io/library",
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "provider": "nexustrade",
        "captured_at": "2026-07-29",
        "source_url": source_url,
        "candidates": candidates or [_candidate()],
    }


def _candidate(**overrides: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "candidate_id": "nexus_spy_sma_30_150",
        "strategy_name": "Nexus SPY SMA 30/150",
        "hypothesis": "A slower trend pair may reduce whipsaw while retaining exposure.",
        "source_url": "https://nexustrade.io/library",
        "family": "sma_crossover_long_only",
        "symbol": "SPY",
        "timeframe": "1d",
        "parameters": {"fast_window": 30, "slow_window": 150},
        "source_rules": {
            "entry": "Enter long when SMA 30 is above SMA 150.",
            "exit": "Move to cash when SMA 30 is not above SMA 150.",
            "evaluation": "Evaluate after the daily close.",
            "allocation": "Long or cash.",
        },
        "source_backtest": {
            "start_date": "2018-01-02",
            "end_date": "2025-12-31",
            "data_mode": "daily_ohlc",
            "validation_method": "walk_forward",
            "fee_bps": "1",
            "slippage_bps": "2",
            "trade_count": 24,
            "metrics": {
                "total_return": "0.42",
                "max_drawdown": "0.18",
                "sharpe_ratio": "0.91",
            },
        },
        "parent_strategy_ids": [],
        "pairing_role": "standalone",
    }
    candidate.update(overrides)
    return candidate


def _trend_then_drawdown_prices() -> tuple[Decimal, ...]:
    prices: list[Decimal] = []
    price = Decimal("100")
    for _ in range(220):
        prices.append(price)
        price += Decimal("0.15")
    for _ in range(55):
        prices.append(price)
        price -= Decimal("0.95")
    for _ in range(180):
        prices.append(price)
        price += Decimal("0.30")
    return tuple(prices)


def _write_price_csv(path: Path, prices: tuple[Decimal, ...]) -> None:
    rows = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    start = date(2020, 1, 2)
    for index, price in enumerate(prices):
        on_date = start + timedelta(days=index)
        rows.append(
            f"SPY,{on_date.isoformat()},{price},{price},{price},{price},{price},1000"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo nexustrade_strategy_intake_status=completed\r\n"
        "echo broker_mutation_performed=false\r\n"
        "echo live_mutation_performed=false\r\n"
        "exit /B 0\r\n",
        encoding="utf-8",
        newline="",
    )
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture_path)
    for name in (
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_KEY_ID",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "NEXUSTRADE_API_KEY",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify the intake wrapper.")
    return powershell
