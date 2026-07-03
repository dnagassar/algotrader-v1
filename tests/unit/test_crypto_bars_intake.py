from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.crypto_bars_intake import (
    CRYPTO_BARS_INTAKE_CANONICAL_COLUMNS,
    CRYPTO_BARS_INTAKE_REQUIRED_BARS,
    CryptoBarsIntakeConfig,
    build_crypto_bars_intake,
    render_crypto_bars_intake_json,
    run_crypto_bars_intake,
    write_crypto_bars_intake_jsonl,
)
from algotrader.execution.crypto_paper_supervisor import (
    CryptoPaperSupervisorConfig,
    run_crypto_paper_supervisor,
)

GENERATED_AT = datetime(2026, 7, 3, 2, tzinfo=UTC)
MODULE_PATH = Path("src/algotrader/execution/crypto_bars_intake.py")

SAFETY_FALSE_FIELDS = (
    "submit_authorized",
    "paper_submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "paper_submit_performed",
    "broker_mutation_performed",
    "live_mutation_performed",
    "live_authorized",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "requests",
    "socket",
    "urllib",
)


def test_accepts_fresh_btcusd_payload_writes_canonical_and_feeds_supervisor(
    tmp_path: Path,
) -> None:
    raw_path = _write_json(tmp_path, _alpaca_payload())
    canonical_csv = tmp_path / "crypto_paper_bars.csv"
    run_log = tmp_path / "manifest.jsonl"

    payload = run_crypto_bars_intake(
        CryptoBarsIntakeConfig(
            input_path=raw_path,
            canonical_csv=canonical_csv,
            run_log=run_log,
            observed_at=GENERATED_AT,
            market_data_read_performed=True,
            network_access_attempted=True,
        )
    )

    assert payload["intake_state"] == "accepted_fresh_crypto_bars"
    assert payload["symbol"] == "BTCUSD"
    assert payload["asset_class"] == "crypto"
    assert payload["basis"] == "alpaca_crypto_bars_v1beta3_ohlcv"
    assert payload["source"] == "alpaca_market_data_crypto_bars_v1beta3_us"
    assert payload["accepted_bar_count"] == 60
    assert payload["usable_bar_count"] == 60
    assert payload["required_bars"] == CRYPTO_BARS_INTAKE_REQUIRED_BARS
    assert payload["latest_bar_at"] == "2026-07-03T01:30:00+00:00"
    assert payload["data_freshness_status"] == "current_for_24_7_crypto_lab"
    assert payload["market_data_read_performed"] is True
    assert payload["network_access_attempted"] is True
    assert payload["credential_values_stored"] is False
    assert json.loads(run_log.read_text(encoding="utf-8")) == payload
    _assert_safety_false(payload)

    rows = canonical_csv.read_text(encoding="utf-8").splitlines()
    assert rows[0] == ",".join(CRYPTO_BARS_INTAKE_CANONICAL_COLUMNS)
    assert rows[-1].startswith("2026-07-03T01:30:00+00:00,BTCUSD,crypto,")

    record = run_crypto_paper_supervisor(
        CryptoPaperSupervisorConfig(
            output_root=tmp_path / "out",
            bars_csv=canonical_csv,
        ),
        assets=(
            {
                "symbol": "BTC/USD",
                "asset_class": "crypto",
                "tradable": True,
                "marginable": False,
                "fractionable": True,
                "status": "active",
                "min_notional": "10.00",
            },
        ),
        timestamp=GENERATED_AT,
        write_artifacts=False,
    )

    assert record["selected_symbol"] == "BTCUSD"
    assert record["min_notional"] == "10.00"
    assert record["data_freshness_status"] == "current_for_24_7_crypto_lab"
    assert record["strategy_posture"] == "risk_on"
    assert record["action_decision"] == "preview_buy/no_submit"
    assert record["readiness_status"] == "readiness_blocked_crypto_preview_only_no_submit"
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert record["live_mutation_performed"] is False


def test_normalizes_timezone_offsets_to_utc(tmp_path: Path) -> None:
    latest_at = datetime(2026, 7, 3, 1, 30, tzinfo=UTC)
    offset = timezone(timedelta(hours=-4))
    raw_path = _write_json(
        tmp_path,
        _alpaca_payload(latest_at=latest_at.astimezone(offset), timezone_mode="offset"),
    )
    canonical_csv = tmp_path / "canonical.csv"

    payload = build_crypto_bars_intake(
        CryptoBarsIntakeConfig(
            input_path=raw_path,
            canonical_csv=canonical_csv,
            run_log=tmp_path / "manifest.jsonl",
            observed_at=GENERATED_AT,
        )
    )

    assert payload["intake_state"] == "accepted_fresh_crypto_bars"
    assert payload["latest_bar_at"] == "2026-07-03T01:30:00+00:00"
    assert canonical_csv.read_text(encoding="utf-8").splitlines()[-1].startswith(
        "2026-07-03T01:30:00+00:00,BTCUSD,crypto,"
    )


def test_duplicate_timestamps_are_rejected(tmp_path: Path) -> None:
    payload = _alpaca_payload()
    bars = payload["bars"]["BTC/USD"]
    bars[-1]["t"] = bars[-2]["t"]
    raw_path = _write_json(tmp_path, payload)
    canonical_csv = tmp_path / "canonical.csv"

    result = build_crypto_bars_intake(
        CryptoBarsIntakeConfig(
            input_path=raw_path,
            canonical_csv=canonical_csv,
            run_log=tmp_path / "manifest.jsonl",
            observed_at=GENERATED_AT,
        )
    )

    assert result["intake_state"] == "blocked_invalid_crypto_bars"
    assert "duplicate_timestamps" in result["blockers"]
    assert not canonical_csv.exists()
    _assert_safety_false(result)


def test_stale_latest_crypto_bar_blocks_without_writing_canonical(tmp_path: Path) -> None:
    raw_path = _write_json(
        tmp_path,
        _alpaca_payload(latest_at=GENERATED_AT - timedelta(hours=6)),
    )
    canonical_csv = tmp_path / "canonical.csv"

    result = build_crypto_bars_intake(
        CryptoBarsIntakeConfig(
            input_path=raw_path,
            canonical_csv=canonical_csv,
            run_log=tmp_path / "manifest.jsonl",
            observed_at=GENERATED_AT,
        )
    )

    assert result["intake_state"] == "blocked_stale_crypto_bars"
    assert result["data_freshness_status"] == "stale_crypto_data_preview_only"
    assert "crypto_bar_age_exceeds_threshold" in result["blockers"]
    assert not canonical_csv.exists()
    _assert_safety_false(result)


def test_insufficient_history_blocks_without_writing_canonical(tmp_path: Path) -> None:
    raw_path = _write_json(tmp_path, _alpaca_payload(count=49))
    canonical_csv = tmp_path / "canonical.csv"

    result = build_crypto_bars_intake(
        CryptoBarsIntakeConfig(
            input_path=raw_path,
            canonical_csv=canonical_csv,
            run_log=tmp_path / "manifest.jsonl",
            observed_at=GENERATED_AT,
        )
    )

    assert result["intake_state"] == "blocked_insufficient_crypto_history"
    assert result["usable_bar_count"] == 49
    assert "insufficient_history" in result["blockers"]
    assert not canonical_csv.exists()


def test_non_btcusd_symbol_is_not_treated_as_tradable_input(tmp_path: Path) -> None:
    raw_path = _write_json(tmp_path, _alpaca_payload(symbol="ETH/USD"))

    result = build_crypto_bars_intake(
        CryptoBarsIntakeConfig(
            input_path=raw_path,
            canonical_csv=tmp_path / "canonical.csv",
            run_log=tmp_path / "manifest.jsonl",
            observed_at=GENERATED_AT,
        )
    )

    assert result["intake_state"] == "blocked_invalid_crypto_bars"
    assert "selected_symbol_missing_from_payload:BTCUSD" in result["blockers"]

    with pytest.raises(ValidationError, match="BTCUSD only"):
        CryptoBarsIntakeConfig(
            input_path=raw_path,
            canonical_csv=tmp_path / "canonical.csv",
            run_log=tmp_path / "manifest.jsonl",
            observed_at=GENERATED_AT,
            symbol="ETHUSD",
        )


def test_csv_asset_class_and_timezone_are_validated(tmp_path: Path) -> None:
    bad_asset = tmp_path / "bad_asset.csv"
    bad_asset.write_text(
        "\n".join(
            (
                "timestamp,symbol,asset_class,open,high,low,close,volume",
                "2026-07-03T01:30:00Z,BTCUSD,equity,1,2,1,2,1",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    asset_result = build_crypto_bars_intake(
        CryptoBarsIntakeConfig(
            input_path=bad_asset,
            canonical_csv=tmp_path / "asset.csv",
            run_log=tmp_path / "manifest.jsonl",
            observed_at=GENERATED_AT,
        )
    )
    assert "asset_class_must_be_crypto" in asset_result["blockers"]

    naive = tmp_path / "naive.csv"
    naive.write_text(
        "\n".join(
            (
                "timestamp,symbol,asset_class,open,high,low,close,volume",
                "2026-07-03T01:30:00,BTCUSD,crypto,1,2,1,2,1",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    timezone_result = build_crypto_bars_intake(
        CryptoBarsIntakeConfig(
            input_path=naive,
            canonical_csv=tmp_path / "timezone.csv",
            run_log=tmp_path / "manifest.jsonl",
            observed_at=GENERATED_AT,
        )
    )
    assert "timestamp_timezone_required" in timezone_result["blockers"]


def test_missing_input_writes_blocked_manifest(tmp_path: Path) -> None:
    run_log = tmp_path / "manifest.jsonl"

    payload = run_crypto_bars_intake(
        CryptoBarsIntakeConfig(
            input_path=tmp_path / "missing.json",
            canonical_csv=tmp_path / "canonical.csv",
            run_log=run_log,
            observed_at=GENERATED_AT,
        )
    )

    assert payload["intake_state"] == "blocked_missing_crypto_bars_input"
    assert "crypto_bars_input_missing" in payload["blockers"]
    assert json.loads(run_log.read_text(encoding="utf-8")) == payload


def test_render_json_is_deterministic(tmp_path: Path) -> None:
    raw_path = _write_json(tmp_path, _alpaca_payload())
    payload = build_crypto_bars_intake(
        CryptoBarsIntakeConfig(
            input_path=raw_path,
            canonical_csv=tmp_path / "canonical.csv",
            run_log=tmp_path / "manifest.jsonl",
            observed_at=GENERATED_AT,
        )
    )
    first = render_crypto_bars_intake_json(payload)
    second = render_crypto_bars_intake_json(payload)

    assert first == second
    assert json.loads(first) == payload


def test_module_imports_no_network_or_broker_packages() -> None:
    imports = _import_references(MODULE_PATH)
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def _write_json(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "raw.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _alpaca_payload(
    *,
    latest_at: datetime = GENERATED_AT - timedelta(minutes=30),
    count: int = 60,
    symbol: str = "BTC/USD",
    timezone_mode: str = "utc_z",
) -> dict[str, object]:
    first = latest_at - timedelta(hours=count - 1)
    bars: list[dict[str, object]] = []
    for index in range(count):
        close = Decimal("50000") + Decimal(index)
        timestamp = first + timedelta(hours=index)
        if timezone_mode == "offset":
            timestamp_text = timestamp.isoformat()
        else:
            timestamp_text = timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")
        bars.append(
            {
                "t": timestamp_text,
                "o": str(close - Decimal("1")),
                "h": str(close + Decimal("2")),
                "l": str(close - Decimal("2")),
                "c": str(close),
                "v": "1.25",
            }
        )
    return {"bars": {symbol: bars}}


def _assert_safety_false(payload: dict[str, object]) -> None:
    for field_name in SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False
    assert payload["no_submit_mode"] is True
    assert payload["profit_claim"] == "none"


def _import_references(path: Path) -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _matches_forbidden_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in prefixes)
