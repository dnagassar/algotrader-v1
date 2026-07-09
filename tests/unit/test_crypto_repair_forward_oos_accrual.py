from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.execution.crypto_history_refresh_adapter import CryptoHistoryRefreshConfig
from algotrader.orchestration.crypto_repair_forward_oos_accrual import (
    CRYPTO_REPAIR_FORWARD_OOS_REQUIRED_MIN_ROWS,
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


def test_rewritten_discovery_period_data_blocks_accrual(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    initial_rows = (*_discovery_rows(), *_future_rows("ADAUSD", 3))
    _write_rows(history, initial_rows)
    _run(tmp_path, history)

    rewritten = list(initial_rows)
    rewritten[0] = {**rewritten[0], "close": "999", "high": "999"}
    _write_rows(history, tuple(rewritten))
    packet = _run(tmp_path, history)

    assert packet["classification"] == "blocked_integrity"
    assert "rewritten_discovery_period_data" in packet["blocker_rejection_reasons"]
    assert packet["integrity_checks"]["discovery_period_hash"] == "failed"


@pytest.mark.parametrize(
    ("rows", "reason"),
    (
        (
            lambda: (*_discovery_rows(), *_future_rows("ADAUSD", 1), _future_rows("ADAUSD", 1)[0]),
            "duplicate_discovery_timestamp",
        ),
        (
            lambda: (
                *_discovery_rows(),
                _row("ADAUSD", CUTOFF + timedelta(hours=2), "102"),
                _row("ADAUSD", CUTOFF + timedelta(hours=1), "101"),
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
