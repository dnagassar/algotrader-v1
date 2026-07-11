from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.crypto_history_refresh_adapter import CryptoHistoryRefreshConfig
from algotrader.orchestration.crypto_repair_forward_oos_accrual import (
    CRYPTO_REPAIR_FORWARD_OOS_REQUIRED_MIN_ROWS,
    invalidate_crypto_repair_frozen_candidate_state,
    run_crypto_repair_forward_oos_accrual,
)
from algotrader.research.crypto_strategy_evidence_battery import (
    DEFAULT_CRYPTO_EVIDENCE_SYMBOLS,
)


CUTOFF = datetime(2026, 7, 9, 16, 0, tzinfo=UTC)
AS_OF = datetime(2026, 7, 11, 0, 0, tzinfo=UTC)


def test_zero_oos_rows_freezes_candidate_and_awaits_fresh_data(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    _write_rows(history, _discovery_rows())

    packet = _run(tmp_path, history)

    assert packet["classification"] == "awaiting_fresh_oos"
    assert packet["oos_row_count"] == 0
    assert packet["rows_still_required"] == CRYPTO_REPAIR_FORWARD_OOS_REQUIRED_MIN_ROWS
    assert packet["repair_eligibility"] == "not_eligible"
    assert packet["paper_planning_eligibility"] == "not_eligible"
    assert packet["evidence_gate"] == {"runnable": False}
    assert Path(packet["artifact_paths"]["frozen_candidate"]).is_file()
    assert packet["broker_read_occurred"] is False
    assert packet["broker_mutation_occurred"] is False
    assert packet["paper_submit_occurred"] is False


def test_partial_accumulation_remains_ineligible(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    _write_rows(history, (*_discovery_rows(), *_future_rows("ADAUSD", 25)))

    packet = _run(tmp_path, history)

    assert packet["classification"] == "awaiting_fresh_oos"
    assert packet["oos_row_count"] == 25
    assert packet["rows_still_required"] == 1
    assert packet["repair_eligibility"] == "not_eligible"
    assert packet["paper_planning_eligibility"] == "not_eligible"


def test_cutoff_boundary_row_is_not_accrued_as_oos(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    boundary = _row("ADAUSD", CUTOFF, "100")
    _write_rows(history, (*_discovery_rows(), boundary, *_future_rows("ADAUSD", 25)))

    packet = _run(tmp_path, history)

    assert packet["oos_row_count"] == 25
    assert packet["rows_still_required"] == 1
    assert packet["oos_range"]["start"] == (CUTOFF + timedelta(hours=1)).isoformat()


def test_exactly_26_rows_runs_existing_evidence_gate(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    _write_rows(history, (*_discovery_rows(), *_future_rows("ADAUSD", 26)))

    packet = _run(tmp_path, history)

    assert packet["oos_row_count"] == 26
    assert packet["rows_still_required"] == 0
    assert packet["evidence_gate"]["classification"] == "fresh_oos_rejected"
    assert packet["classification"] == "fresh_oos_rejected"
    assert packet["repair_eligibility"] == "not_eligible"


def test_more_than_26_rows_are_accrued_and_evaluated(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    _write_rows(history, (*_discovery_rows(), *_future_rows("ADAUSD", 27)))

    packet = _run(tmp_path, history)

    assert packet["oos_row_count"] == 27
    assert packet["rows_still_required"] == 0
    assert packet["evidence_gate"]["classification"] == "fresh_oos_rejected"
    assert packet["classification"] == "fresh_oos_rejected"


def test_candidate_drift_cannot_inherit_accrued_evidence(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    _write_rows(history, (*_discovery_rows(), *_future_rows("ADAUSD", 25)))
    _run(tmp_path, history)

    packet = _run(
        tmp_path,
        history,
        candidate_id="crypto:ADAUSD:changed_parameter_set",
    )

    assert packet["classification"] == "blocked_integrity"
    assert "candidate_fingerprint_mismatch" in packet["blocker_rejection_reasons"]
    assert packet["oos_row_count"] == 0
    assert packet["paper_planning_eligibility"] == "not_eligible"


def test_future_runs_use_frozen_snapshot_when_mutable_history_changes(
    tmp_path: Path,
) -> None:
    history = tmp_path / "history.csv"
    initial_rows = (*_discovery_rows(), *_future_rows("ADAUSD", 3))
    _write_rows(history, initial_rows)
    _run(tmp_path, history)

    rewritten = list(initial_rows)
    rewritten[0] = {**rewritten[0], "close": "999", "high": "999"}
    _write_rows(history, tuple(rewritten))
    packet = _run(tmp_path, history)

    assert packet["classification"] == "awaiting_fresh_oos"
    assert packet["oos_row_count"] == 3
    assert "rewritten_discovery_period_data" not in packet["blocker_rejection_reasons"]
    assert packet["integrity_checks"]["discovery_period_hash"] == "passed"


@pytest.mark.parametrize(
    ("rows", "reason"),
        (
            (
                lambda: (*_discovery_rows(), _discovery_rows()[0]),
                "duplicate_discovery_timestamp",
            ),
            (
                lambda: (
                    *_discovery_rows(),
                    _row("ADAUSD", CUTOFF - timedelta(minutes=15), "102"),
                    _row("ADAUSD", CUTOFF - timedelta(minutes=30), "101"),
                ),
                "out_of_order_discovery_bars",
            ),
    ),
)
def test_duplicate_and_out_of_order_input_are_safely_blocked(
    tmp_path: Path,
    rows: object,
    reason: str,
) -> None:
    history = tmp_path / "history.csv"
    _write_rows(history, rows())

    packet = _run(tmp_path, history)

    assert packet["classification"] == "blocked_integrity"
    assert reason in packet["blocker_rejection_reasons"]
    assert packet["paper_planning_eligibility"] == "not_eligible"


def test_malformed_timestamp_and_inconsistent_normalization_are_blocked(
    tmp_path: Path,
) -> None:
    history = tmp_path / "history.csv"
    rows = list(_discovery_rows())
    rows.append(
        {
            "timestamp": "not-a-timestamp",
            "symbol": "ADAUSD",
            "open": "1",
            "high": "1",
            "low": "1",
            "close": "1",
            "volume": "1",
            "source": "recorded_local_history",
        }
    )
    _write_rows(history, tuple(rows))

    packet = _run(tmp_path, history)

    assert packet["classification"] == "blocked_integrity"
    assert "malformed_timestamp" in packet["blocker_rejection_reasons"]


def test_inconsistent_normalization_is_safely_blocked(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    inconsistent = _row("ADAUSD", CUTOFF + timedelta(hours=1), "100")
    inconsistent["high"] = "99"
    _write_rows(history, (*_discovery_rows(), inconsistent))

    packet = _run(tmp_path, history)

    assert packet["classification"] == "blocked_integrity"
    assert "inconsistent_normalization" in packet["blocker_rejection_reasons"]


def test_refresh_failure_is_a_safe_block(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    _write_rows(history, _discovery_rows())
    config = CryptoHistoryRefreshConfig(
        mode="dry_run",
        output_path=tmp_path / "unwritten_refresh.csv",
        packet_path=None,
        as_of=AS_OF,
    )

    def _failed_refresh(_: CryptoHistoryRefreshConfig) -> dict[str, object]:
        raise RuntimeError("offline test refresh failed")

    packet = _run(tmp_path, history, refresh_config=config, refresh_runner=_failed_refresh)

    assert packet["classification"] == "blocked_refresh_failure"
    assert packet["blocker_rejection_reasons"] == ["refresh_failure"]
    assert packet["network_access_attempted"] is False
    assert packet["paper_planning_eligibility"] == "not_eligible"


def test_refresh_output_with_pre_cutoff_rows_is_not_accepted_as_delta(tmp_path: Path) -> None:
    discovery = tmp_path / "discovery.csv"
    refresh_output = tmp_path / "refresh.csv"
    _write_rows(discovery, _discovery_rows())
    _write_rows(refresh_output, (*_discovery_rows(), *_future_rows("ADAUSD", 1)))
    config = CryptoHistoryRefreshConfig(
        mode="offline_fixture",
        output_path=refresh_output,
        packet_path=None,
        as_of=AS_OF,
    )

    packet = _run(
        tmp_path,
        discovery,
        refresh_config=config,
        refresh_runner=lambda _: {"classification": "offline_fixture_ready"},
    )

    assert packet["classification"] == "blocked_integrity"
    assert "attempted_pre_cutoff_leakage" in packet["blocker_rejection_reasons"]


@pytest.mark.parametrize(
    "aliased_field",
    ("output_path", "packet_path", "raw_response_path"),
)
def test_discovery_refresh_alias_blocks_before_runner_and_preserves_snapshot(
    tmp_path: Path,
    aliased_field: str,
) -> None:
    history = tmp_path / "history.csv"
    _write_rows(history, _discovery_rows())
    first = _run(tmp_path, history)
    snapshot = Path(first["artifact_paths"]["frozen_discovery_history"])
    before = snapshot.read_bytes()
    calls = 0
    config_values: dict[str, object] = {
        "mode": "market_data_fetch",
        "output_path": tmp_path / "refresh.csv",
        "packet_path": tmp_path / "refresh_packet.json",
        "raw_response_path": tmp_path / "raw_crypto_bars.json",
        "as_of": AS_OF,
        "start": CUTOFF + timedelta(hours=1),
        "end": AS_OF,
        "market_data_fetch_authorized": True,
        "allow_network": True,
    }
    config_values[aliased_field] = snapshot
    config = CryptoHistoryRefreshConfig(
        **config_values,
    )

    def _runner(_: CryptoHistoryRefreshConfig) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {}

    packet = _run(
        tmp_path,
        history,
        refresh_config=config,
        refresh_runner=_runner,
    )

    assert packet["classification"] == "blocked_integrity"
    assert packet["blocker_rejection_reasons"] == ["discovery_refresh_path_alias"]
    assert packet["network_access_attempted"] is False
    assert calls == 0
    assert snapshot.read_bytes() == before


def test_market_data_refresh_requires_strictly_post_cutoff_start(
    tmp_path: Path,
) -> None:
    history = tmp_path / "history.csv"
    refresh_output = tmp_path / "refresh.csv"
    _write_rows(history, _discovery_rows())
    _run(tmp_path, history)
    calls = 0
    config = CryptoHistoryRefreshConfig(
        mode="market_data_fetch",
        output_path=refresh_output,
        packet_path=None,
        raw_response_path=None,
        as_of=AS_OF,
        start=CUTOFF,
        end=AS_OF,
        market_data_fetch_authorized=True,
        allow_network=True,
    )

    def _runner(_: CryptoHistoryRefreshConfig) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {}

    packet = _run(
        tmp_path,
        history,
        refresh_config=config,
        refresh_runner=_runner,
    )

    assert packet["classification"] == "blocked_integrity"
    assert (
        "refresh_start_not_strictly_post_cutoff"
        in packet["blocker_rejection_reasons"]
    )
    assert packet["network_access_attempted"] is False
    assert calls == 0


def test_eight_post_cutoff_delta_rows_are_accrued_and_remain_ineligible(
    tmp_path: Path,
) -> None:
    history = tmp_path / "history.csv"
    refresh_output = tmp_path / "refresh.csv"
    _write_rows(history, _discovery_rows())
    _run(tmp_path, history)
    _write_rows(refresh_output, _future_rows("ADAUSD", 8))
    config = CryptoHistoryRefreshConfig(
        mode="market_data_fetch",
        output_path=refresh_output,
        packet_path=None,
        raw_response_path=None,
        as_of=AS_OF,
        market_data_fetch_authorized=True,
        allow_network=True,
    )
    captured: list[CryptoHistoryRefreshConfig] = []

    def _runner(value: CryptoHistoryRefreshConfig) -> dict[str, object]:
        captured.append(value)
        return {
            "classification": "insufficient_real_crypto_history",
            "mode": "market_data_fetch",
            "output_path": str(refresh_output),
            "market_data_fetch_occurred": True,
            "network_access_attempted": True,
        }

    packet = _run(
        tmp_path,
        history,
        refresh_config=config,
        refresh_runner=_runner,
    )

    assert packet["classification"] == "awaiting_fresh_oos"
    assert packet["oos_row_count"] == 8
    assert packet["rows_still_required"] == 18
    assert packet["paper_planning_eligibility"] == "not_eligible"
    assert packet["refresh"]["mode"] == "market_data_fetch"
    assert packet["market_data_fetch_occurred"] is True
    assert captured[0].start == CUTOFF + timedelta(hours=1)
    assert captured[0].end == AS_OF


def test_existing_manifest_snapshot_recovery_requires_exact_hash(
    tmp_path: Path,
) -> None:
    history = tmp_path / "history.csv"
    _write_rows(history, _discovery_rows())
    first = _run(tmp_path, history)
    manifest_path = Path(first["artifact_paths"]["frozen_candidate"])
    snapshot_path = Path(first["artifact_paths"]["frozen_discovery_history"])
    expected_hash = json.loads(manifest_path.read_text(encoding="utf-8"))[
        "relevant_discovery_evidence_input_hash"
    ]
    snapshot_path.unlink()

    recovered = _run(tmp_path, history)

    assert recovered["classification"] == "awaiting_fresh_oos"
    assert recovered["discovery_snapshot"]["status"] == "recovered"
    assert recovered["discovery_snapshot"]["fingerprint"] == expected_hash
    assert snapshot_path.is_file()


def test_mismatched_recovery_source_cannot_rewrite_manifest_or_snapshot(
    tmp_path: Path,
) -> None:
    history = tmp_path / "history.csv"
    _write_rows(history, _discovery_rows())
    first = _run(tmp_path, history)
    manifest_path = Path(first["artifact_paths"]["frozen_candidate"])
    snapshot_path = Path(first["artifact_paths"]["frozen_discovery_history"])
    manifest_before = manifest_path.read_bytes()
    snapshot_path.unlink()
    rows = list(_discovery_rows())
    rows[0] = {**rows[0], "close": "999", "high": "999"}
    _write_rows(history, tuple(rows))

    packet = _run(tmp_path, history)

    assert packet["classification"] == "blocked_discovery_snapshot_unrecoverable"
    assert "discovery_snapshot_hash_mismatch" in packet["blocker_rejection_reasons"]
    assert manifest_path.read_bytes() == manifest_before
    assert not snapshot_path.exists()


def test_write_artifacts_false_is_side_effect_free_with_26_rows(
    tmp_path: Path,
) -> None:
    history = tmp_path / "history.csv"
    output_root = tmp_path / "state"
    _write_rows(history, (*_discovery_rows(), *_future_rows("ADAUSD", 26)))

    packet = run_crypto_repair_forward_oos_accrual(
        output_root=output_root,
        discovery_history_path=history,
        as_of=AS_OF,
        write_artifacts=False,
    )

    assert packet["oos_row_count"] == 26
    assert packet["classification"] == "fresh_oos_rejected"
    assert not output_root.exists()


def test_explicit_invalidation_archives_prior_state_and_reinitializes(
    tmp_path: Path,
) -> None:
    state = tmp_path / "latest"
    original_history = tmp_path / "original.csv"
    replacement_history = tmp_path / "replacement.csv"
    archive = tmp_path / "invalidated_original"
    _write_rows(original_history, _discovery_rows())
    original = run_crypto_repair_forward_oos_accrual(
        output_root=state,
        discovery_history_path=original_history,
        as_of=AS_OF,
    )
    original_manifest = (state / "frozen_candidate.json").read_bytes()
    rewritten = list(_discovery_rows())
    rewritten[0] = {**rewritten[0], "close": "999", "high": "999"}
    _write_rows(
        replacement_history,
        (*rewritten, *_future_rows("ADAUSD", 8)),
    )

    packet = invalidate_crypto_repair_frozen_candidate_state(
        output_root=state,
        discovery_history_path=replacement_history,
        archive_path=archive,
        invalidation_reason="operator accepted rewritten discovery baseline",
        invalidated_at=AS_OF,
    )

    assert (archive / "frozen_candidate.json").read_bytes() == original_manifest
    assert (state / "frozen_candidate.json").is_file()
    assert packet["classification"] == "awaiting_fresh_oos"
    assert packet["oos_row_count"] == 8
    reset = packet["state_invalidation"]
    assert (
        reset["prior_discovery_hash"]
        == original["discovery_snapshot"]["fingerprint"]
    )
    assert reset["replacement_discovery_hash"] != reset["prior_discovery_hash"]
    assert reset["archive_preserved"] is True
    assert reset["deleted_prior_state"] is False
    assert reset["network_access_attempted"] is False
    assert reset["broker_mutation_occurred"] is False
    assert json.loads(
        (archive / "frozen_candidate_invalidation.json").read_text(encoding="utf-8")
    ) == reset
    assert json.loads(
        (state / "frozen_candidate_invalidation.json").read_text(encoding="utf-8")
    ) == reset


def test_invalidation_preflight_failure_preserves_current_state(
    tmp_path: Path,
) -> None:
    state = tmp_path / "latest"
    original_history = tmp_path / "original.csv"
    invalid_history = tmp_path / "invalid.csv"
    archive = tmp_path / "invalidated_original"
    _write_rows(original_history, _discovery_rows())
    run_crypto_repair_forward_oos_accrual(
        output_root=state,
        discovery_history_path=original_history,
        as_of=AS_OF,
    )
    manifest_before = (state / "frozen_candidate.json").read_bytes()
    _write_rows(invalid_history, (*_discovery_rows(), _discovery_rows()[0]))

    with pytest.raises(ValidationError, match="replacement discovery preflight failed"):
        invalidate_crypto_repair_frozen_candidate_state(
            output_root=state,
            discovery_history_path=invalid_history,
            archive_path=archive,
            invalidation_reason="operator reset",
            invalidated_at=AS_OF,
        )

    assert (state / "frozen_candidate.json").read_bytes() == manifest_before
    assert not archive.exists()


def test_invalidation_rejects_unchanged_hash_and_archive_collision(
    tmp_path: Path,
) -> None:
    state = tmp_path / "latest"
    history = tmp_path / "history.csv"
    archive = tmp_path / "invalidated_original"
    _write_rows(history, _discovery_rows())
    run_crypto_repair_forward_oos_accrual(
        output_root=state,
        discovery_history_path=history,
        as_of=AS_OF,
    )

    with pytest.raises(ValidationError, match="matches the existing candidate"):
        invalidate_crypto_repair_frozen_candidate_state(
            output_root=state,
            discovery_history_path=history,
            archive_path=archive,
            invalidation_reason="unnecessary reset",
            invalidated_at=AS_OF,
        )

    archive.mkdir()
    with pytest.raises(ValidationError, match="archive path already exists"):
        invalidate_crypto_repair_frozen_candidate_state(
            output_root=state,
            discovery_history_path=history,
            archive_path=archive,
            invalidation_reason="collision",
            invalidated_at=AS_OF,
        )


def test_invalidation_rejects_recovery_source_inside_state(tmp_path: Path) -> None:
    state = tmp_path / "latest"
    history = tmp_path / "history.csv"
    archive = tmp_path / "invalidated_original"
    _write_rows(history, _discovery_rows())
    run_crypto_repair_forward_oos_accrual(
        output_root=state,
        discovery_history_path=history,
        as_of=AS_OF,
    )

    with pytest.raises(ValidationError, match="must be outside output_root"):
        invalidate_crypto_repair_frozen_candidate_state(
            output_root=state,
            discovery_history_path=state / "frozen_discovery_history.csv",
            archive_path=archive,
            invalidation_reason="unsafe source",
            invalidated_at=AS_OF,
        )

    assert state.is_dir()
    assert not archive.exists()


def test_powershell_runner_exposes_isolated_paths_and_refresh_window() -> None:
    script = Path("scripts/run_crypto_repair_forward_oos_accrual.ps1").read_text(
        encoding="utf-8"
    )

    assert "DiscoveryRecoverySourcePath" in script
    assert "RefreshStart" in script
    assert "RefreshEnd" in script
    assert "refresh\\forward_oos_delta.csv" in script
    assert "refresh\\refresh_packet.json" in script
    assert "refresh\\raw_crypto_bars.json" in script
    assert '[string]$RefreshOutputPath = "runs\\operator_input' not in script
    assert "InvalidateFrozenCandidateState" in script
    assert "InvalidationReason" in script
    assert "InvalidationArchivePath" in script
    assert '"--invalidate-frozen-candidate-state"' in script


def test_identical_rerun_is_idempotent(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    _write_rows(history, (*_discovery_rows(), *_future_rows("ADAUSD", 25)))

    first = _run(tmp_path, history)
    second = _run(tmp_path, history)

    assert _decision_fields(second) == _decision_fields(first)
    accrued = Path(first["artifact_paths"]["accrued_oos"])
    assert _csv_data_row_count(accrued) == 25


def test_eligible_and_rejected_evidence_outcomes_are_preserved(tmp_path: Path) -> None:
    eligible_history = tmp_path / "eligible.csv"
    eligible_rows = [*_discovery_rows(), *_passing_oos_rows()]
    _write_rows(eligible_history, tuple(eligible_rows))

    eligible = _run(tmp_path / "eligible", eligible_history)

    assert eligible["classification"] == "eligible_for_no_submit_paper_planning"
    assert eligible["repair_eligibility"] == "eligible_for_no_submit_plan"
    assert eligible["paper_planning_eligibility"] == "eligible_for_no_submit_plan"
    assert eligible["evidence_gate"]["rejection_reasons"] == []

    rejected_history = tmp_path / "rejected.csv"
    rejected_prices = (*("100" for _ in range(24)), "101", "102", "103", "104", "105", "106")
    rejected_rows = [*_discovery_rows(), *_future_rows("ADAUSD", 30, rejected_prices)]
    _write_rows(rejected_history, tuple(rejected_rows))

    rejected = _run(tmp_path / "rejected", rejected_history)

    assert rejected["classification"] == "fresh_oos_rejected"
    assert "buy_and_hold_underperformance" in rejected["blocker_rejection_reasons"]
    assert rejected["repair_eligibility"] == "not_eligible"
    assert rejected["paper_planning_eligibility"] == "not_eligible"


def _run(
    output_root: Path,
    history: Path,
    **kwargs: object,
) -> dict[str, object]:
    return run_crypto_repair_forward_oos_accrual(
        output_root=output_root / "runs",
        discovery_history_path=history,
        as_of=AS_OF,
        **kwargs,
    )


def _discovery_rows() -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for symbol_index, symbol in enumerate(DEFAULT_CRYPTO_EVIDENCE_SYMBOLS):
        for row_index in range(3):
            rows.append(
                _row(
                    symbol,
                    CUTOFF - timedelta(hours=3 - row_index),
                    str(Decimal("100") + Decimal(symbol_index) + Decimal(row_index)),
                )
            )
    return tuple(rows)


def _future_rows(
    symbol: str,
    count: int,
    prices: tuple[str, ...] | None = None,
) -> tuple[dict[str, str], ...]:
    values = prices or tuple(str(Decimal("100") + Decimal(index)) for index in range(count))
    return tuple(
        _row(symbol, CUTOFF + timedelta(hours=index + 1), price)
        for index, price in enumerate(values)
    )


def _passing_oos_rows() -> tuple[dict[str, str], ...]:
    ada_prices = ("200", *("60" for _ in range(24)), "61", "90", "100", "100", "100")
    rows = [*_future_rows("ADAUSD", len(ada_prices), ada_prices)]
    for symbol in ("BTCUSD", "ETHUSD", "SOLUSD"):
        rows.extend(_future_rows(symbol, 30, tuple("100" for _ in range(30))))
    return tuple(rows)


def _row(symbol: str, timestamp: datetime, close: str) -> dict[str, str]:
    return {
        "timestamp": timestamp.isoformat(),
        "symbol": symbol,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": "1",
        "source": "recorded_local_history",
    }


def _write_rows(path: Path, rows: tuple[dict[str, str], ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("timestamp", "symbol", "open", "high", "low", "close", "volume", "source"),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _decision_fields(packet: dict[str, object]) -> dict[str, object]:
    return {
        field: packet[field]
        for field in (
            "classification",
            "oos_row_count",
            "oos_normalized_row_count",
            "oos_range",
            "rows_still_required",
            "repair_eligibility",
            "paper_planning_eligibility",
            "blocker_rejection_reasons",
            "integrity_checks",
        )
    }


def _csv_data_row_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines()) - 1
