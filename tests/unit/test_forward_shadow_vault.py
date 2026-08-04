from __future__ import annotations

import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research import forward_shadow_vault as subject

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def fake_repo(tmp_path: Path) -> Path:
    runs = tmp_path / "runs" / "v9_99_example"
    acquisition = runs / "data_acquisition"
    canonical = runs / "canonical"
    acquisition.mkdir(parents=True)
    canonical.mkdir(parents=True)

    (acquisition / "spy_refresh_manifest.jsonl").write_text(
        json.dumps({"symbol": "SPY", "refresh_state": "accepted"}) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (acquisition / "qqq_raw_tiingo.json").write_text("{}", encoding="utf-8")
    (canonical / "iwm_daily_tiingo_adjusted_canonical.csv").write_text(
        "symbol,date\n", encoding="utf-8"
    )
    (runs / "canonical_data_manifest.json").write_text(
        json.dumps(
            {
                "symbols": ["TLT", "GLD"],
                "provider_symbol_map": {"EFA": "EFA"},
                "symbol_data": [{"symbol": "AGG", "provider_symbol": "AGG"}],
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    return tmp_path


def test_scan_finds_symbols_across_every_evidence_shape(fake_repo: Path) -> None:
    acquired = subject.scan_acquired_symbols(fake_repo)

    assert set(acquired) == {"SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "AGG"}
    kinds = {
        symbol: {item.evidence_kind for item in evidence}
        for symbol, evidence in acquired.items()
    }
    assert "refresh_receipt_symbol" in kinds["SPY"]
    assert "raw_provider_response_filename" in kinds["QQQ"]
    assert "canonical_artifact_filename" in kinds["IWM"]
    assert "data_manifest_symbols" in kinds["TLT"]
    assert "data_manifest_provider_symbol_map" in kinds["EFA"]
    assert "data_manifest_symbol_data" in kinds["AGG"]


def test_never_acquired_symbol_is_vault_eligible(fake_repo: Path) -> None:
    report = subject.build_vault_eligibility_report(
        ["EWZ", "THD"], repo_root=fake_repo
    )

    assert report["all_requested_symbols_eligible"] is True
    assert report["vault_eligible_symbols"] == ["EWZ", "THD"]
    assert report["ineligible_symbols"] == []
    assert report["safety"]["network_access_performed"] is False


def test_acquired_symbol_is_refused_with_evidence(fake_repo: Path) -> None:
    report = subject.build_vault_eligibility_report(
        ["EWZ", "SPY"], repo_root=fake_repo
    )

    assert report["all_requested_symbols_eligible"] is False
    assert report["ineligible_symbols"] == ["SPY"]
    row = next(
        item for item in report["symbol_reports"] if item["symbol"] == "SPY"
    )
    assert row["vault_eligible"] is False
    assert row["evidence_count"] >= 1
    assert row["evidence"][0]["evidence_path"].startswith("runs")


def test_assert_vault_eligible_fails_closed(fake_repo: Path) -> None:
    with pytest.raises(ValidationError, match="already acquired"):
        subject.assert_vault_eligible(["SPY"], repo_root=fake_repo)

    report = subject.assert_vault_eligible(["EWZ"], repo_root=fake_repo)
    assert report["all_requested_symbols_eligible"] is True


def test_case_and_duplicates_are_normalized(fake_repo: Path) -> None:
    report = subject.build_vault_eligibility_report(
        ["spy", "SPY", "ewz"], repo_root=fake_repo
    )

    assert report["requested_symbols"] == ["SPY", "EWZ"]
    assert report["ineligible_symbols"] == ["SPY"]


def test_invalid_symbols_are_rejected(fake_repo: Path) -> None:
    with pytest.raises(ValidationError, match="invalid symbol"):
        subject.build_vault_eligibility_report(["not a ticker"], repo_root=fake_repo)
    with pytest.raises(ValidationError, match="at least one symbol"):
        subject.build_vault_eligibility_report([], repo_root=fake_repo)


def test_missing_runs_directory_yields_no_evidence(tmp_path: Path) -> None:
    assert subject.scan_acquired_symbols(tmp_path) == {}


def test_report_states_what_it_cannot_prove(fake_repo: Path) -> None:
    report = subject.build_vault_eligibility_report(["EWZ"], repo_root=fake_repo)

    assert "no acquisition receipt" in report["proves"]
    assert "author" in report["does_not_prove"]


def test_real_repository_flags_its_own_heavily_used_symbols() -> None:
    """SPY has been acquired many times here; it must never look untouched."""

    report = subject.build_vault_eligibility_report(
        ["SPY", "QQQ"], repo_root=REPO_ROOT
    )

    assert report["all_requested_symbols_eligible"] is False
    assert set(report["ineligible_symbols"]) == {"SPY", "QQQ"}
    assert report["distinct_acquired_symbols_in_repository"] > 10


def test_cli_reports_and_signals_ineligibility(
    fake_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        subject.main(["--symbol", "EWZ", "--repo-root", str(fake_repo)]) == 0
    )
    assert "ELIGIBLE" in capsys.readouterr().out

    assert (
        subject.main(["--symbol", "SPY", "--repo-root", str(fake_repo)]) == 3
    )
    out = capsys.readouterr().out
    assert "ALREADY ACQUIRED" in out
    assert "refresh_receipt_symbol" in out
