from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from algotrader.research.multi_etf_adjusted_data_manifest import (
    APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS,
    MultiEtfAdjustedDataManifestConfig,
    build_multi_etf_adjusted_data_manifest,
    run_multi_etf_adjusted_data_manifest,
)


def test_multi_symbol_data_discovery_writes_manifest_and_combined_csv(
    tmp_path: Path,
) -> None:
    paths = _write_symbol_files(tmp_path, ("SPY", "QQQ", "IWM", "TLT", "GLD"))
    manifest_path = tmp_path / "multi_etf_adjusted_data_manifest.json"
    combined_path = tmp_path / "multi_etf_adjusted_daily_canonical.csv"

    payload = run_multi_etf_adjusted_data_manifest(
        MultiEtfAdjustedDataManifestConfig(
            output_manifest=manifest_path,
            combined_output_csv=combined_path,
            canonical_paths=paths,
            expected_latest_bar_date="2026-06-26",
        )
    )

    assert payload["symbols"] == list(APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS)
    assert payload["valid_symbols"] == list(APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS)
    assert payload["refresh_required_symbols"] == []
    assert payload["combined_row_count"] == 15
    assert payload["combined_output_sha256"]
    assert manifest_path.is_file()
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == payload

    rows = combined_path.read_text(encoding="utf-8").splitlines()
    assert rows[0] == "symbol,date,open,high,low,close,adjusted_close,volume"
    assert sum(1 for row in rows if row.startswith("QQQ,")) == 3
    assert sum(1 for row in rows if row.startswith("GLD,")) == 3

    qqq = _symbol_record(payload, "QQQ")
    assert qqq["data_path"] == str(paths["QQQ"])
    assert qqq["sha256"]
    assert qqq["row_count"] == 3
    assert qqq["earliest_date"] == "2026-06-24"
    assert qqq["latest_date"] == "2026-06-26"
    assert qqq["adjusted_close_basis"] == "adjusted_close_price_return"
    assert qqq["duplicate_date_status"] == "no_duplicate_dates"
    assert qqq["validation_status"] == "valid"
    assert qqq["freshness_status"] == "current"


def test_missing_symbol_emits_data_refresh_required_without_crashing(
    tmp_path: Path,
) -> None:
    paths = _write_symbol_files(tmp_path, ("SPY",))
    paths["QQQ"] = tmp_path / "missing_qqq.csv"
    combined_path = tmp_path / "combined.csv"

    payload = build_multi_etf_adjusted_data_manifest(
        MultiEtfAdjustedDataManifestConfig(
            combined_output_csv=combined_path,
            symbols=("SPY", "QQQ"),
            canonical_paths=paths,
            expected_latest_bar_date="2026-06-26",
        )
    )

    assert payload["valid_symbols"] == ["SPY"]
    assert payload["missing_symbols"] == ["QQQ"]
    assert payload["refresh_required_symbols"] == ["QQQ"]
    assert payload["combined_row_count"] == 3
    assert combined_path.is_file()

    missing = _symbol_record(payload, "QQQ")
    assert missing["validation_status"] == "missing_data"
    assert missing["data_refresh_status"] == "data_refresh_required"
    assert missing["sha256"] == ""
    assert missing["row_count"] == 0
    assert missing["freshness_status"] == "not_evaluated_missing_data"


def test_existing_spy_canonical_data_remains_supported(tmp_path: Path) -> None:
    paths = _write_symbol_files(tmp_path, ("SPY",))

    payload = build_multi_etf_adjusted_data_manifest(
        MultiEtfAdjustedDataManifestConfig(
            combined_output_csv=tmp_path / "combined.csv",
            symbols=("SPY",),
            canonical_paths=paths,
        )
    )

    assert payload["valid_symbols"] == ["SPY"]
    assert payload["refresh_required_symbols"] == []
    assert _symbol_record(payload, "SPY")["validation_status"] == "valid"


def _write_symbol_files(
    root: Path,
    symbols: tuple[str, ...],
) -> dict[str, Path]:
    return {symbol: _write_symbol_file(root, symbol) for symbol in symbols}


def _write_symbol_file(root: Path, symbol: str) -> Path:
    path = root / f"{symbol.lower()}_daily_tiingo_adjusted_canonical.csv"
    start = date(2026, 6, 24)
    base = Decimal("100") + Decimal(len(symbol))
    rows = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    for offset in range(3):
        price = base + Decimal(offset)
        on_date = start + timedelta(days=offset)
        rows.append(
            "{symbol},{date},{price},{price},{price},{price},{adjusted},1000".format(
                symbol=symbol,
                date=on_date.isoformat(),
                price=price,
                adjusted=price + Decimal("0.25"),
            )
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _symbol_record(payload: dict[str, object], symbol: str) -> dict[str, object]:
    for record in payload["symbol_data"]:
        if record["symbol"] == symbol:
            return record
    raise AssertionError(symbol)
