from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.butler_source_family_data_manifest import (
    ALL_SYMBOLS,
    CANDIDATE_SYMBOLS,
    DEFAULT_SOURCES,
    ButlerSourceFamilyDataManifestConfig,
    SymbolSourceSpec,
    build_butler_source_family_data_manifest,
)


def test_default_contract_is_exact_author_universe_and_mixed_provenance() -> None:
    assert CANDIDATE_SYMBOLS == (
        "DBC", "EEM", "EWJ", "GLD", "ICF", "IEF", "RWX", "TLT", "VGK", "VTI",
    )
    assert ALL_SYMBOLS == (*CANDIDATE_SYMBOLS, "SPY")
    assert tuple(source.symbol for source in DEFAULT_SOURCES) == ALL_SYMBOLS
    assert {
        source.symbol
        for source in DEFAULT_SOURCES
        if source.provenance_kind == "new_refresh"
    } == {"EEM", "EWJ", "ICF", "RWX", "VGK"}
    assert all(source.source_sha256 for source in DEFAULT_SOURCES)
    assert all(source.evidence_sha256 for source in DEFAULT_SOURCES)
    assert all(
        source.raw_response_sha256 is not None
        for source in DEFAULT_SOURCES
        if source.provenance_kind == "new_refresh"
    )


def test_manifest_validates_mixed_receipts_and_writes_common_panel(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)

    first = build_butler_source_family_data_manifest(config)
    first_bytes = config.combined_output_csv.read_bytes()
    second = build_butler_source_family_data_manifest(config)

    assert first == second
    assert first_bytes == config.combined_output_csv.read_bytes()
    assert first["symbols"] == list(ALL_SYMBOLS)
    assert first["candidate_symbols"] == list(CANDIDATE_SYMBOLS)
    assert first["common_session_count"] == 3
    assert first["combined_row_count"] == 33
    assert first["common_first_session"] == "2026-07-29"
    assert first["common_last_session"] == "2026-07-31"
    assert first["provider_field"] == "adjClose"
    assert first["canonical_field"] == "adjusted_close"
    assert (
        first["adjustment_semantics"]
        == "provider_split_and_dividend_adjusted_close"
    )
    assert first["safety"]["outcome_metrics_computed"] is False
    assert first["safety"]["candidate_ranking_performed"] is False
    assert first["safety"]["broker_access_performed"] is False
    assert first["safety"]["live_authorized"] is False
    kinds = [record["source_kind"] for record in first["symbol_data"]]
    assert kinds.count("candidate_specific_authenticated_acquisition") == 5
    assert kinds.count("reused_prior_canonical_evidence") == 6
    rows = config.combined_output_csv.read_text(encoding="utf-8").splitlines()
    assert rows[0] == "symbol,date,open,high,low,close,adjusted_close,volume"
    assert len(rows) == 34


def test_manifest_rejects_protocol_drift(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.protocol_path.write_text("changed\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="protocol SHA-256"):
        build_butler_source_family_data_manifest(config)


def test_manifest_rejects_prior_receipt_drift(tmp_path: Path) -> None:
    config = _config(tmp_path)
    prior = config.sources[0]
    prior.evidence_path.write_text("changed\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="DBC provenance receipt SHA-256"):
        build_butler_source_family_data_manifest(config)


def test_manifest_rejects_refresh_semantic_drift(tmp_path: Path) -> None:
    config = _config(tmp_path)
    position = next(
        index
        for index, source in enumerate(config.sources)
        if source.provenance_kind == "new_refresh"
    )
    source = config.sources[position]
    receipt = json.loads(source.evidence_path.read_text(encoding="utf-8"))
    receipt["provider_request"]["method"] = "POST"
    source.evidence_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    sources = list(config.sources)
    sources[position] = replace(source, evidence_sha256=_sha(source.evidence_path))
    config = replace(config, sources=tuple(sources))

    with pytest.raises(ValidationError, match="provider request method mismatch"):
        build_butler_source_family_data_manifest(config)


def test_manifest_rejects_raw_response_drift(tmp_path: Path) -> None:
    config = _config(tmp_path)
    source = next(
        source
        for source in config.sources
        if source.provenance_kind == "new_refresh"
    )
    receipt = json.loads(source.evidence_path.read_text(encoding="utf-8"))
    raw_path = Path(receipt["raw_provider_response_path"])
    raw_path.write_text("[1]\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="raw response SHA-256 mismatch"):
        build_butler_source_family_data_manifest(config)


def test_manifest_rejects_nonidentical_coverage(tmp_path: Path) -> None:
    config = _config(tmp_path)
    source = config.sources[-1]
    _write_csv(source.source_path, source.symbol, days=2)
    sources = list(config.sources)
    sources[-1] = replace(source, source_sha256=_sha(source.source_path))
    config = replace(config, sources=tuple(sources))

    with pytest.raises(ValidationError, match="SPY must cover"):
        build_butler_source_family_data_manifest(config)


def test_source_spec_requires_exact_provenance_contract(tmp_path: Path) -> None:
    path = tmp_path / "x"
    path.write_text("x", encoding="utf-8")
    digest = _sha(path)

    with pytest.raises(ValidationError, match="only a new refresh"):
        SymbolSourceSpec("SPY", path, digest, "new_refresh", path, digest)


def _config(tmp_path: Path) -> ButlerSourceFamilyDataManifestConfig:
    protocol = tmp_path / "protocol.md"
    protocol.write_text("frozen protocol\n", encoding="utf-8")
    start = date(2026, 7, 29)
    end = date(2026, 7, 31)
    sources: list[SymbolSourceSpec] = []
    new_symbols = {"EEM", "EWJ", "ICF", "RWX", "VGK"}
    for symbol in ALL_SYMBOLS:
        source_path = tmp_path / "canonical" / f"{symbol.lower()}.csv"
        _write_csv(source_path, symbol)
        if symbol in new_symbols:
            raw_path = tmp_path / "raw" / f"{symbol.lower()}.json"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text("[]\n", encoding="utf-8")
            evidence_path = tmp_path / "refresh" / f"{symbol.lower()}.jsonl"
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            receipt = {
                "provider": "tiingo",
                "symbol": symbol,
                "mode": "live_market_data_fetch",
                "refresh_state": "accepted_adjusted_spy_data_refresh",
                "request_start_date": start.isoformat(),
                "request_end_date": end.isoformat(),
                "date_range_start": start.isoformat(),
                "date_range_end": end.isoformat(),
                "canonical_csv_sha256": _sha(source_path),
                "http_outcome_category": "success",
                "market_data_token_env_var": "TIINGO_API_KEY",
                "source_sha256": _sha(raw_path),
                "network_method_allowlist": ["GET"],
                "network_destination_allowlist_enforced": True,
                "provider_column_mapping": {"adjusted_close": "adjClose"},
                "provider_request": {
                    "method": "GET",
                    "scheme": "https",
                    "destination_host": "api.tiingo.com",
                    "provider_symbol": symbol,
                    "provider_symbol_mapping": f"{symbol}->{symbol}",
                    "request_start_date": start.isoformat(),
                    "request_end_date": end.isoformat(),
                    "destination_allowlist_match": True,
                },
                "raw_provider_response_path": str(raw_path),
                "token_value_recorded": False,
                "market_data_token_value_printed": False,
                "market_data_token_value_written": False,
                "broker_credential_lookup_attempted": False,
                "broker_access_attempted": False,
                "broker_mutation_attempted": False,
                "paper_submit_attempted": False,
                "live_authorized": False,
                "live_trading_performed": False,
            }
            evidence_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
            sources.append(
                SymbolSourceSpec(
                    symbol,
                    source_path,
                    _sha(source_path),
                    "new_refresh",
                    evidence_path,
                    _sha(evidence_path),
                    _sha(raw_path),
                )
            )
        else:
            evidence_path = tmp_path / "receipts" / f"{symbol.lower()}.md"
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_path.write_text(f"{symbol} admitted\n", encoding="utf-8")
            sources.append(
                SymbolSourceSpec(
                    symbol,
                    source_path,
                    _sha(source_path),
                    "prior_receipt",
                    evidence_path,
                    _sha(evidence_path),
                )
            )
    return ButlerSourceFamilyDataManifestConfig(
        output_manifest=tmp_path / "manifest.json",
        combined_output_csv=tmp_path / "combined.csv",
        protocol_path=protocol,
        expected_protocol_sha256=_sha(protocol),
        sources=tuple(sources),
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
            f"{symbol},{on_date.isoformat()},{value},{value},{value},"
            f"{value},{value},1000"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()