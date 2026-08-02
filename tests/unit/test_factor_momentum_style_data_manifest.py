from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.factor_momentum_style_data_manifest import (
    ALL_SYMBOLS,
    RISK_SYMBOLS,
    FactorMomentumStyleDataManifestConfig,
    build_factor_momentum_style_data_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/refresh_v584_factor_momentum_data.ps1"


def test_manifest_verifies_receipts_and_writes_exact_common_snapshot(tmp_path: Path) -> None:
    config = _config(tmp_path)

    payload = build_factor_momentum_style_data_manifest(config)

    assert payload["symbols"] == list(ALL_SYMBOLS)
    assert payload["risk_symbols"] == list(RISK_SYMBOLS)
    assert payload["common_session_count"] == 3
    assert payload["combined_row_count"] == 27
    assert payload["common_first_session"] == "2026-07-29"
    assert payload["common_last_session"] == "2026-07-31"
    assert payload["provider_field"] == "adjClose"
    assert payload["canonical_field"] == "adjusted_close"
    assert payload["adjustment_semantics"] == "provider_split_and_dividend_adjusted_close"
    assert payload["safety"]["outcome_metrics_computed"] is False
    assert payload["safety"]["candidate_ranking_performed"] is False
    assert payload["safety"]["broker_access_performed"] is False
    assert payload["safety"]["live_authorized"] is False
    rows = config.combined_output_csv.read_text(encoding="utf-8").splitlines()
    assert rows[0] == "symbol,date,open,high,low,close,adjusted_close,volume"
    assert len(rows) == 28


def test_manifest_rejects_changed_protocol(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.protocol_path.write_text("changed\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="protocol SHA-256"):
        build_factor_momentum_style_data_manifest(config)


def test_manifest_rejects_receipt_endpoint_drift(tmp_path: Path) -> None:
    config = _config(tmp_path)
    path = config.acquisition_root / "iwf_refresh_manifest.jsonl"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["request_start_date"] = "2026-07-30"
    path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="IWF refresh receipt request_start_date mismatch"):
        build_factor_momentum_style_data_manifest(config)


def test_manifest_rejects_nonidentical_session_sequence(tmp_path: Path) -> None:
    config = _config(tmp_path)
    data_path = config.canonical_root / "splv_daily_tiingo_adjusted_canonical.csv"
    _write_csv(data_path, "SPLV", days=2)
    receipt_path = config.acquisition_root / "splv_refresh_manifest.jsonl"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["canonical_csv_sha256"] = _sha(data_path)
    receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="SPLV must cover"):
        build_factor_momentum_style_data_manifest(config)


def test_refresh_script_is_exact_get_only_research_wrapper() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert '[string]$Mode = "dry_run"' in text
    assert '"IWD", "IWF", "RSP", "VBR", "VIG", "SPLV", "SHY", "SPY", "IEF"' in text
    assert '"2011-05-05"' in text
    assert '"2026-07-31"' in text
    assert "TIINGO_API_KEY" in text
    assert "--live-market-data-fetch-authorized" in text
    assert "factor_momentum_style_data_manifest" in text
    assert "ALPACA_" not in text
    assert "submit" not in text.lower()


def _config(tmp_path: Path) -> FactorMomentumStyleDataManifestConfig:
    protocol = tmp_path / "protocol.md"
    protocol.write_text("frozen protocol\n", encoding="utf-8")
    canonical_root = tmp_path / "canonical"
    acquisition_root = tmp_path / "acquisition"
    start = date(2026, 7, 29)
    end = date(2026, 7, 31)
    for symbol in ALL_SYMBOLS:
        data_path = canonical_root / f"{symbol.lower()}_daily_tiingo_adjusted_canonical.csv"
        _write_csv(data_path, symbol)
        raw_path = acquisition_root / f"{symbol.lower()}_raw_tiingo.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text("[]\n", encoding="utf-8")
        receipt = {
            "provider": "tiingo",
            "symbol": symbol,
            "mode": "live_market_data_fetch",
            "refresh_state": "accepted_adjusted_spy_data_refresh",
            "request_start_date": start.isoformat(),
            "request_end_date": end.isoformat(),
            "date_range_start": start.isoformat(),
            "date_range_end": end.isoformat(),
            "canonical_csv_sha256": _sha(data_path),
            "http_outcome_category": "success",
            "market_data_token_env_var": "TIINGO_API_KEY",
            "network_method_allowlist": ["GET"],
            "network_destination_allowlist_enforced": True,
            "provider_column_mapping": {"adjusted_close": "adjClose"},
            "raw_provider_response_path": str(raw_path),
            "source_sha256": _sha(raw_path),
            "token_value_recorded": False,
            "market_data_token_value_printed": False,
            "market_data_token_value_written": False,
            "broker_credential_lookup_attempted": False,
            "broker_access_attempted": False,
            "broker_mutation_attempted": False,
            "paper_submit_attempted": False,
            "live_authorized": False,
        }
        (acquisition_root / f"{symbol.lower()}_refresh_manifest.jsonl").write_text(
            json.dumps(receipt) + "\n", encoding="utf-8"
        )
    return FactorMomentumStyleDataManifestConfig(
        output_manifest=tmp_path / "manifest.json",
        combined_output_csv=tmp_path / "combined.csv",
        canonical_root=canonical_root,
        acquisition_root=acquisition_root,
        protocol_path=protocol,
        expected_protocol_sha256=_sha(protocol),
        start=start,
        end=end,
    )


def _write_csv(path: Path, symbol: str, *, days: int = 3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    for offset in range(days):
        on_date = date(2026, 7, 29) + timedelta(days=offset)
        value = 100 + offset
        rows.append(
            f"{symbol},{on_date.isoformat()},{value},{value},{value},{value},{value},1000"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
