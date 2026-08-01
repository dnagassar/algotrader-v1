from __future__ import annotations

from datetime import date, timedelta
import hashlib
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.primary_source_alpha_data_manifest import (
    ALL_SYMBOLS,
    CORE_SYMBOLS,
    SECTOR_SYMBOLS,
    PrimarySourceAlphaDataManifestConfig,
    build_primary_source_alpha_data_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/refresh_v572_primary_source_alpha_data.ps1"


def test_manifest_pins_inputs_and_writes_exact_common_snapshot(tmp_path: Path) -> None:
    config = _config(tmp_path)

    payload = build_primary_source_alpha_data_manifest(config)

    assert payload["symbols"] == list(ALL_SYMBOLS)
    assert payload["core_symbols"] == list(CORE_SYMBOLS)
    assert payload["sector_symbols"] == list(SECTOR_SYMBOLS)
    assert payload["common_session_count"] == 3
    assert payload["combined_row_count"] == 42
    assert payload["common_first_session"] == "2026-07-29"
    assert payload["common_last_session"] == "2026-07-31"
    assert payload["provider_field"] == "adjClose"
    assert payload["canonical_field"] == "adjusted_close"
    assert payload["safety"]["outcome_metrics_computed"] is False
    assert payload["safety"]["candidate_ranking_performed"] is False
    assert payload["safety"]["broker_access_performed"] is False
    assert payload["safety"]["live_authorized"] is False
    assert config.output_manifest.is_file()
    assert config.combined_output_csv.is_file()
    rows = config.combined_output_csv.read_text(encoding="utf-8").splitlines()
    assert rows[0] == "symbol,date,open,high,low,close,adjusted_close,volume"
    assert len(rows) == 43


def test_manifest_rejects_changed_frozen_input(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.protocol_path.write_text("changed\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="protocol SHA-256"):
        build_primary_source_alpha_data_manifest(config)


def test_manifest_rejects_nonidentical_session_sequence(tmp_path: Path) -> None:
    config = _config(tmp_path)
    path = config.sector_root / "xlk_daily_tiingo_adjusted_canonical.csv"
    path.write_text(
        "symbol,date,open,high,low,close,adjusted_close,volume\n"
        "XLK,2026-07-29,100,100,100,100,100,1000\n"
        "XLK,2026-07-31,101,101,101,101,101,1000\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="XLK common-session sequence differs"):
        build_primary_source_alpha_data_manifest(config)


def test_refresh_script_is_exact_get_only_research_wrapper() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert '[string]$Mode = "dry_run"' in text
    assert '"XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"' in text
    assert '"2004-11-18"' in text
    assert '"2026-07-31"' in text
    assert "TIINGO_API_KEY" in text
    assert "--live-market-data-fetch-authorized" in text
    assert "primary_source_alpha_data_manifest" in text
    assert "ALPACA_" not in text
    assert "submit" not in text.lower()


def _config(tmp_path: Path) -> PrimarySourceAlphaDataManifestConfig:
    protocol = tmp_path / "protocol.md"
    protocol.write_text("frozen protocol\n", encoding="utf-8")
    prior_manifest = tmp_path / "prior_manifest.json"
    prior_manifest.write_text("{}\n", encoding="utf-8")
    prior_data = tmp_path / "prior.csv"
    _write_csv(prior_data, CORE_SYMBOLS)
    sector_root = tmp_path / "sectors"
    for symbol in SECTOR_SYMBOLS:
        _write_csv(
            sector_root / f"{symbol.lower()}_daily_tiingo_adjusted_canonical.csv",
            (symbol,),
        )
    return PrimarySourceAlphaDataManifestConfig(
        output_manifest=tmp_path / "manifest.json",
        combined_output_csv=tmp_path / "combined.csv",
        prior_data=prior_data,
        prior_manifest=prior_manifest,
        sector_root=sector_root,
        protocol_path=protocol,
        expected_protocol_sha256=_sha(protocol),
        expected_prior_data_sha256=_sha(prior_data),
        expected_prior_manifest_sha256=_sha(prior_manifest),
        start=date(2026, 7, 29),
        end=date(2026, 7, 31),
    )


def _write_csv(
    path: Path,
    symbols: tuple[str, ...],
    *,
    start: date = date(2026, 7, 29),
    days: int = 3,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    for symbol_index, symbol in enumerate(symbols):
        for offset in range(days):
            on_date = start + timedelta(days=offset)
            value = 100 + symbol_index + offset
            rows.append(
                f"{symbol},{on_date.isoformat()},{value},{value},{value},{value},{value},1000"
            )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
