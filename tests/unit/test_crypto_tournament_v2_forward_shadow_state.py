from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Sequence

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.crypto_history_refresh_adapter import (
    CryptoHistoryRefreshConfig,
)
from algotrader.orchestration import (
    crypto_tournament_v2_bounded_paper_probe_review as probe_review,
    crypto_tournament_v2_forward_shadow as shadow_operating,
)
from algotrader.research.crypto_preregistered_tournament_v2 import (
    CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT,
    OOS_END_EXCLUSIVE,
    build_crypto_tournament_v2_preregistration,
)
from algotrader.research.crypto_tournament_v2_forward_oos import _Bar, _rows_hash
from algotrader.research.crypto_tournament_v2_forward_shadow import (
    build_crypto_tournament_v2_forward_shadow_activation,
)
from algotrader.research import crypto_tournament_v2_forward_shadow_state as shadow_state


ONE_HOUR = timedelta(hours=1)


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _terminal_packet(
    *, terminal_sha256: str, closed_at: str
) -> dict[str, object]:
    candidate = build_crypto_tournament_v2_preregistration()["candidates"][0]
    classification = "eligible_for_no_submit_shadow_evaluation"
    evidence_fingerprint = "b" * 64
    return {
        "classification": classification,
        "preregistration_fingerprint": (
            CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT
        ),
        "frozen_state": {
            "terminal_outcome_closed": True,
            "terminal_classification": classification,
            "terminal_closed_at": closed_at,
            "terminal_packet_sha256": terminal_sha256,
            "terminal_scoring_performed": True,
            "terminal_evidence_fingerprint": evidence_fingerprint,
            "state_fingerprint": "d" * 64,
        },
        "terminal_scoring_performed": True,
        "terminal_evidence_fingerprint": evidence_fingerprint,
        "terminal_closure": {
            "terminal_outcome_closed": True,
            "terminal_classification": classification,
            "terminal_closed_at": closed_at,
            "terminal_scoring_performed": True,
            "terminal_evidence_fingerprint": evidence_fingerprint,
        },
        "selected_candidate": {
            "candidate_id": candidate["candidate_id"],
            "candidate_fingerprint": candidate["candidate_fingerprint"],
            "candidate_decision": classification,
            "selection_scope": classification,
            "paper_or_broker_eligible": False,
        },
        "broker_read_occurred": False,
        "paper_or_broker_eligible": False,
        "paper_planning_eligibility": "not_eligible",
        "paper_or_live_execution_authorized": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "paper_cancel_occurred": False,
        "paper_replace_occurred": False,
        "paper_close_occurred": False,
        "paper_liquidate_occurred": False,
        "live_authorized": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "profit_claim": "none",
    }


def _context_packet(
    *, activation: dict[str, object], terminal_path: Path
) -> dict[str, object]:
    source = activation["source_binding"]
    assert isinstance(source, dict)
    candidate = activation["selected_candidate"]
    assert isinstance(candidate, dict)
    end = _utc(OOS_END_EXCLUSIVE)
    start = end - (169 * ONE_HOUR)
    context_bars: list[_Bar] = []
    for index in range(169):
        timestamp = start + (index * ONE_HOUR)
        context_bars.append(
            _Bar(
                timestamp=timestamp,
                symbol=str(candidate["symbol"]),
                open=Decimal("100"),
                high=Decimal("100"),
                low=Decimal("100"),
                close=Decimal("100"),
                volume=Decimal("1"),
                imputed=False,
            )
        )
    frozen_context = tuple(context_bars)
    return {
        "candidate": candidate,
        "context_rows": [bar.canonical() for bar in frozen_context],
        "context_row_count": len(frozen_context),
        "context_sha256": _rows_hash(frozen_context),
        "source_binding": {
            "terminal_packet_path": str(terminal_path),
            "terminal_packet_sha256": source["terminal_packet_sha256"],
            "terminal_evidence_fingerprint": source[
                "terminal_evidence_fingerprint"
            ],
            "state_fingerprint": source["state_fingerprint"],
            "terminal_closed_at": source["terminal_closed_at"],
        },
        "network_access_attempted": False,
        "broker_read_occurred": False,
        "broker_mutation_occurred": False,
        "paper_or_live_execution_authorized": False,
        "live_authorized": False,
        "profit_claim": "none",
    }


def _initialize(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    closed_at: str = "2026-08-13T00:00:00+00:00",
) -> tuple[Path, dict[str, object]]:
    terminal_path = tmp_path / "tournament_terminal.json"
    terminal_path.write_text("{}\n", encoding="utf-8")
    terminal_sha = hashlib.sha256(terminal_path.read_bytes()).hexdigest()
    activation = build_crypto_tournament_v2_forward_shadow_activation(
        _terminal_packet(
            terminal_sha256=terminal_sha,
            closed_at=closed_at,
        ),
        as_of=closed_at,
    )
    context = _context_packet(
        activation=activation,
        terminal_path=terminal_path,
    )
    monkeypatch.setattr(
        shadow_state,
        "run_crypto_tournament_v2_forward_shadow_readiness",
        lambda **_: activation,
    )
    monkeypatch.setattr(
        shadow_state,
        "export_crypto_tournament_v2_selected_shadow_context",
        lambda **_: context,
    )
    root = tmp_path / "shadow"
    packet = shadow_state.initialize_crypto_tournament_v2_forward_shadow_state(
        tournament_root=tmp_path / "tournament",
        output_root=root,
        as_of=closed_at,
    )
    return root, packet


def _write_history(
    path: Path,
    *,
    symbol: str,
    start: datetime,
    hours: int,
    missing_indexes: set[int] | None = None,
    price: Decimal = Decimal("100"),
    prices: tuple[Decimal, ...] | None = None,
) -> None:
    if prices is not None and len(prices) != hours:
        raise AssertionError("prices must contain exactly one value per hour")
    missing = missing_indexes or set()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "timestamp",
                "symbol",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        for index in range(hours):
            if index in missing:
                continue
            value = format(
                price if prices is None else prices[index],
                "f",
            )
            writer.writerow(
                {
                    "timestamp": (start + (index * ONE_HOUR)).isoformat(),
                    "symbol": symbol,
                    "open": value,
                    "high": value,
                    "low": value,
                    "close": value,
                    "volume": "1",
                }
            )


def _write_receipt(
    path: Path,
    *,
    history_path: Path,
    symbol: str,
    start: datetime,
    end: datetime,
) -> dict[str, object]:
    packet = {
        "schema_version": "v5_22_crypto_history_refresh_adapter_receipt_v2",
        "record_type": "crypto_history_refresh_adapter_packet",
        "classification": "market_data_refresh_ready",
        "coverage_gate_classification": "not_evaluated_data_intake_only",
        "mode": "market_data_fetch",
        "authorization_status": "authorized",
        "endpoint_safety_status": "passed_non_live_endpoint_check",
        "data_source": "alpaca_market_data_crypto_bars_v1beta3",
        "timeframe": "1Hour",
        "loc": "us",
        "schema_validation_status": "passed",
        "duplicate_timestamp_status": "passed",
        "duplicate_timestamp_status_after_normalization": "passed",
        "requested_symbols": [symbol],
        "fetched_symbols": [symbol],
        "missing_symbols": [],
        "output_path": str(history_path),
        "packet_path": str(path),
        "output_sha256": hashlib.sha256(history_path.read_bytes()).hexdigest(),
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "as_of": (end + ONE_HOUR).isoformat(),
        "rows_per_symbol_after_normalization": {symbol: 1},
        "data_intake_only": True,
        "strategy_evidence_evaluation_performed": False,
        "paper_planning_promotion_allowed": False,
        "market_data_fetch_occurred": True,
        "network_access_attempted": True,
        "broker_read_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "paper_cancel_occurred": False,
        "paper_replace_occurred": False,
        "paper_close_occurred": False,
        "paper_liquidate_occurred": False,
        "live_authorized": False,
        "live_endpoint_indicator": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "profit_claim": "none",
    }
    path.write_text(json.dumps(packet, sort_keys=True) + "\n", encoding="utf-8")
    return packet


def _delta(
    tmp_path: Path,
    *,
    root: Path,
    start: datetime,
    hours: int,
    name: str,
    missing_indexes: set[int] | None = None,
    price: Decimal = Decimal("100"),
    prices: tuple[Decimal, ...] | None = None,
) -> tuple[Path, Path]:
    state = json.loads((root / "frozen_state.json").read_text(encoding="utf-8"))
    symbol = state["selected_symbol"]
    history = tmp_path / f"{name}.csv"
    receipt = tmp_path / f"{name}_receipt.json"
    _write_history(
        history,
        symbol=symbol,
        start=start,
        hours=hours,
        missing_indexes=missing_indexes,
        price=price,
        prices=prices,
    )
    _write_receipt(
        receipt,
        history_path=history,
        symbol=symbol,
        start=start,
        end=start + ((hours - 1) * ONE_HOUR),
    )
    return history, receipt


def _run_delta(
    *, root: Path, as_of: datetime, delta: tuple[Path, Path]
) -> dict[str, object]:
    return shadow_state.run_crypto_tournament_v2_forward_shadow_state(
        output_root=root,
        as_of=as_of,
        delta_history_path=delta[0],
        delta_receipt_path=delta[1],
        operation_network_access=True,
        operation_market_data_fetch=True,
    )


def test_nonterminal_readiness_remains_dormant_and_writes_no_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        shadow_state,
        "run_crypto_tournament_v2_forward_shadow_readiness",
        lambda **_: {
            "classification": "waiting_for_tournament_terminal",
            "principal_blocker": "untouched_oos_not_terminal",
            "next_action": "continue_oos_accrual",
        },
    )

    packet = shadow_state.initialize_crypto_tournament_v2_forward_shadow_state(
        tournament_root=tmp_path / "tournament",
        output_root=tmp_path / "shadow",
        as_of="2026-08-12T00:00:00+00:00",
    )

    assert packet["phase"] == "dormant_before_terminal_winner"
    assert packet["shadow_state_initialized"] is False
    assert packet["network_access_attempted"] is False
    assert not (tmp_path / "shadow" / "frozen_state.json").exists()


def test_initialization_freezes_activation_and_169_context_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)

    assert packet["classification"] == "collecting_no_submit_forward_shadow"
    assert packet["progress"]["shadow_raw_rows"] == 0
    state = json.loads((root / "frozen_state.json").read_text(encoding="utf-8"))
    assert state["context_row_count"] == 169
    assert state["expected_shadow_hourly_bars"] == 168
    assert state["terminal_outcome_closed"] is False
    assert (root / "signal_context.csv").read_text(encoding="utf-8").count("\n") == 170
    assert packet["paper_or_live_execution_authorized"] is False


def test_initialization_rejects_nonpersisted_state_identity(
    tmp_path: Path,
) -> None:
    root = tmp_path / "shadow"

    with pytest.raises(ValidationError, match="must persist its frozen state"):
        shadow_state.initialize_crypto_tournament_v2_forward_shadow_state(
            tournament_root=tmp_path / "tournament",
            output_root=root,
            as_of="2026-08-13T00:00:00+00:00",
            write_artifacts=False,
        )

    assert not root.exists()


def test_status_is_read_only_and_reports_persisted_state_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)
    state_path = root / "frozen_state.json"
    before = state_path.read_bytes()
    persisted = json.loads(before)
    later = _utc(packet["as_of"]) + ONE_HOUR

    dry = shadow_state.run_crypto_tournament_v2_forward_shadow_state(
        output_root=root,
        as_of=later,
        write_artifacts=False,
    )
    written_status = shadow_state.run_crypto_tournament_v2_forward_shadow_state(
        output_root=root,
        as_of=later,
    )

    assert dry["frozen_state"]["state_fingerprint"] == persisted[
        "state_fingerprint"
    ]
    assert written_status["frozen_state"]["state_fingerprint"] == persisted[
        "state_fingerprint"
    ]
    assert state_path.read_bytes() == before


def test_overlapping_state_cycle_is_rejected_by_process_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)

    with shadow_state._exclusive_state_lock(root):
        with pytest.raises(ValidationError, match="exclusive lock"):
            shadow_state.run_crypto_tournament_v2_forward_shadow_state(
                output_root=root,
                as_of=packet["as_of"],
            )


def test_interrupted_generation_commit_recovers_before_next_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)
    start = _utc(packet["shadow_window"]["start"])
    delta = _delta(
        tmp_path,
        root=root,
        start=start,
        hours=1,
        name="interrupted_generation",
    )
    original_replace = shadow_state._replace_staged_file
    calls = 0

    def interrupted_replace(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls >= 2:
            raise OSError("simulated process interruption")
        original_replace(source, target)

    monkeypatch.setattr(
        shadow_state,
        "_replace_staged_file",
        interrupted_replace,
    )
    with pytest.raises(OSError, match="simulated process interruption"):
        _run_delta(root=root, as_of=start + ONE_HOUR, delta=delta)
    assert (root / "pending_transaction.json").is_file()
    monkeypatch.setattr(
        shadow_state,
        "_replace_staged_file",
        original_replace,
    )

    recovered = shadow_state.run_crypto_tournament_v2_forward_shadow_state(
        output_root=root,
        as_of=start + ONE_HOUR,
    )

    assert not (root / "pending_transaction.json").exists()
    assert recovered["progress"]["shadow_raw_rows"] == 1
    assert recovered["progress"]["shadow_normalized_rows"] == 1
    assert recovered["progress"]["decision_log_rows"] == 1
    assert not tuple(root.glob("*.pending"))


def test_delayed_activation_warmup_is_required_but_never_scored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(
        tmp_path,
        monkeypatch,
        closed_at="2026-08-13T00:07:00+00:00",
    )
    start = _utc(packet["shadow_window"]["start"])
    assert start == _utc("2026-08-13T01:00:00+00:00")
    warmup = _delta(
        tmp_path,
        root=root,
        start=start - ONE_HOUR,
        hours=1,
        name="warmup",
    )

    accrued = _run_delta(root=root, as_of=start, delta=warmup)

    assert accrued["progress"]["activation_warmup_raw_rows"] == 1
    assert accrued["progress"]["shadow_raw_rows"] == 0
    assert accrued["progress"]["decision_log_rows"] == 0
    assert accrued["activation_warmup_quality"]["status"] == "passed"


def test_delayed_activation_status_before_start_does_not_form_negative_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(
        tmp_path,
        monkeypatch,
        closed_at="2026-08-13T00:07:00+00:00",
    )

    status = shadow_state.run_crypto_tournament_v2_forward_shadow_state(
        output_root=root,
        as_of="2026-08-13T00:30:00+00:00",
    )

    assert status["classification"] == "shadow_initialized_waiting_for_start"
    assert status["progress"]["shadow_normalized_rows"] == 0
    assert status["progress"]["decision_log_rows"] == 0
    assert status["next_refresh"]["classification"] == "waiting_for_calendar_hour"


def test_checkpoints_accrue_without_promotion_and_duplicate_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)
    start = _utc(packet["shadow_window"]["start"])
    delta = _delta(
        tmp_path,
        root=root,
        start=start,
        hours=24,
        name="first_day",
    )

    first = _run_delta(root=root, as_of=start + (24 * ONE_HOUR), delta=delta)
    replay = _run_delta(root=root, as_of=start + (24 * ONE_HOUR), delta=delta)

    assert first["progress"]["decision_log_rows"] == 24
    assert first["progress"]["completed_checkpoint_hours"] == [24]
    assert first["bounded_paper_probe_review_permitted"] is False
    assert replay["progress"] == first["progress"]
    assert replay["receipt_count"] == 1
    assert not tuple(root.glob("*.pending"))


def test_conflicting_rewrite_of_accrued_bar_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)
    start = _utc(packet["shadow_window"]["start"])
    first = _delta(
        tmp_path,
        root=root,
        start=start,
        hours=1,
        name="first",
    )
    _run_delta(root=root, as_of=start + ONE_HOUR, delta=first)
    changed = _delta(
        tmp_path,
        root=root,
        start=start,
        hours=1,
        name="changed",
        price=Decimal("101"),
    )

    with pytest.raises(ValidationError, match="conflicting rewrite"):
        _run_delta(root=root, as_of=start + ONE_HOUR, delta=changed)


def test_missing_tail_status_preserves_prior_decisions_and_checkpoints(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)
    start = _utc(packet["shadow_window"]["start"])
    delta = _delta(
        tmp_path,
        root=root,
        start=start,
        hours=24,
        name="valid_prefix",
    )
    _run_delta(root=root, as_of=start + (24 * ONE_HOUR), delta=delta)
    decisions_before = (root / "hourly_decision_log.jsonl").read_bytes()
    checkpoints_before = (root / "checkpoint_ledger.json").read_bytes()

    status = shadow_state.run_crypto_tournament_v2_forward_shadow_state(
        output_root=root,
        as_of=start + (26 * ONE_HOUR),
    )

    assert status["progress"]["decision_log_rows"] == 24
    assert status["progress"]["completed_checkpoint_hours"] == [24]
    assert (root / "hourly_decision_log.jsonl").read_bytes() == decisions_before
    assert (root / "checkpoint_ledger.json").read_bytes() == checkpoints_before


def test_single_interior_gap_is_frozen_once_and_cannot_be_backfilled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)
    start = _utc(packet["shadow_window"]["start"])
    gapped = _delta(
        tmp_path,
        root=root,
        start=start,
        hours=3,
        name="isolated_gap",
        missing_indexes={1},
    )
    accrued = _run_delta(root=root, as_of=start + (3 * ONE_HOUR), delta=gapped)
    decisions = [
        json.loads(line)
        for line in (root / "hourly_decision_log.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert accrued["progress"]["decision_log_rows"] == 3
    assert decisions[1]["imputed"] is True
    backfill = _delta(
        tmp_path,
        root=root,
        start=start + ONE_HOUR,
        hours=1,
        name="forbidden_backfill",
    )

    with pytest.raises(ValidationError, match="retroactively replace"):
        _run_delta(root=root, as_of=start + (3 * ONE_HOUR), delta=backfill)


def test_excessive_gap_does_not_create_decisions_past_raw_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)
    start = _utc(packet["shadow_window"]["start"])
    gapped = _delta(
        tmp_path,
        root=root,
        start=start,
        hours=4,
        name="double_gap",
        missing_indexes={1, 2},
    )

    accrued = _run_delta(root=root, as_of=start + (4 * ONE_HOUR), delta=gapped)

    assert accrued["progress"]["shadow_raw_rows"] == 2
    assert accrued["progress"]["shadow_normalized_rows"] == 1
    assert accrued["progress"]["decision_log_rows"] == 1
    assert accrued["progress"]["completed_checkpoint_hours"] == []


def test_complete_168_hour_shadow_seals_terminal_evidence_and_replays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)
    start = _utc(packet["shadow_window"]["start"])
    end = _utc(packet["shadow_window"]["end_exclusive"])
    prices = tuple(
        [Decimal("100") + (Decimal(index + 1) / Decimal("2")) for index in range(40)]
        + [
            Decimal("120")
            - (Decimal(index + 1) * Decimal("20") / Decimal("70"))
            for index in range(70)
        ]
        + [Decimal("90") for _ in range(58)]
    )
    delta = _delta(
        tmp_path,
        root=root,
        start=start,
        hours=168,
        name="complete",
        prices=prices,
    )

    terminal = _run_delta(root=root, as_of=end, delta=delta)
    operating_before_export = (root / "operating_packet.json").read_bytes()
    exported = (
        shadow_state.export_crypto_tournament_v2_forward_shadow_terminal_evidence(
            output_root=root,
            as_of=end,
        )
    )
    assert (root / "operating_packet.json").read_bytes() == (
        operating_before_export
    )
    exported_later = (
        shadow_state.export_crypto_tournament_v2_forward_shadow_terminal_evidence(
            output_root=root,
            as_of=end + ONE_HOUR,
        )
    )
    replay = shadow_state.run_crypto_tournament_v2_forward_shadow_state(
        output_root=root,
        as_of=end + ONE_HOUR,
    )
    downstream_review = (
        probe_review.build_crypto_tournament_v2_bounded_paper_probe_review(
            exported,
            as_of=end,
        )
    )

    assert terminal["classification"] == (
        "evidence_complete_for_bounded_paper_probe_review"
    )
    assert terminal["terminal_scoring_performed"] is True
    assert terminal["terminal_metrics"]["decision_log_complete"] is True
    assert terminal["progress"]["decision_log_rows"] == 168
    assert terminal["progress"]["completed_checkpoint_hours"] == [24, 72, 168]
    assert terminal["bounded_paper_probe_review_permitted"] is False
    assert terminal["capital_allocation_authorized"] is False
    assert exported["classification"] == terminal["classification"]
    assert exported["review_eligible_source"] is True
    assert exported["terminal_scoring_performed"] is True
    assert exported["terminal_metrics"] == terminal["terminal_metrics"]
    assert exported["source_binding"]["terminal_evidence_fingerprint"] == (
        terminal["terminal_evidence_fingerprint"]
    )
    assert exported_later["evidence_export_fingerprint"] == (
        exported["evidence_export_fingerprint"]
    )
    assert exported_later["as_of"] != exported["as_of"]
    assert downstream_review["classification"] == (
        "blocked_by_operational_evidence"
    )
    assert all(
        item["passed"] for item in downstream_review["strategy_gate_results"]
    )
    assert (root / "operating_packet.json").read_bytes() != b""
    assert operating_before_export == json.dumps(
        terminal,
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    assert replay["terminal_evidence_fingerprint"] == (
        terminal["terminal_evidence_fingerprint"]
    )
    assert replay["classification"] == terminal["classification"]
    with pytest.raises(ValidationError, match="rejects later deltas"):
        _run_delta(root=root, as_of=end + ONE_HOUR, delta=delta)


def test_one_missing_hour_fails_locked_point_995_terminal_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)
    start = _utc(packet["shadow_window"]["start"])
    end = _utc(packet["shadow_window"]["end_exclusive"])
    delta = _delta(
        tmp_path,
        root=root,
        start=start,
        hours=168,
        name="one_gap",
        missing_indexes={80},
    )

    terminal = _run_delta(root=root, as_of=end, delta=delta)

    assert terminal["classification"] == "terminal_shadow_input_quality_gate"
    assert terminal["terminal_scoring_performed"] is False
    assert terminal["shadow_quality"]["raw_coverage"] == "0.99404762"
    assert "shadow_raw_coverage_below_threshold" in (
        terminal["terminal_input_quality"]["errors"]
    )
    assert terminal["capital_allocation_authorized"] is False
    exported = (
        shadow_state.export_crypto_tournament_v2_forward_shadow_terminal_evidence(
            output_root=root,
            as_of=end,
        )
    )
    assert exported["classification"] == "terminal_shadow_input_quality_gate"
    assert exported["review_eligible_source"] is False
    assert exported["terminal_metrics"] == {}


def test_terminal_quality_export_accepts_incomplete_checkpoint_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)
    start = _utc(packet["shadow_window"]["start"])
    end = _utc(packet["shadow_window"]["end_exclusive"])
    delta = _delta(
        tmp_path,
        root=root,
        start=start,
        hours=168,
        name="double_gap",
        missing_indexes={25, 26},
    )

    terminal = _run_delta(root=root, as_of=end, delta=delta)
    exported = (
        shadow_state.export_crypto_tournament_v2_forward_shadow_terminal_evidence(
            output_root=root,
            as_of=end,
        )
    )

    assert terminal["classification"] == "terminal_shadow_input_quality_gate"
    assert terminal["progress"]["completed_checkpoint_hours"] == [24]
    assert exported["progress"]["completed_checkpoint_hours"] == [24]
    assert exported["terminal_scoring_performed"] is False


def test_terminal_export_rejects_unsealed_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)

    with pytest.raises(ValidationError, match="terminal evidence is not sealed"):
        shadow_state.export_crypto_tournament_v2_forward_shadow_terminal_evidence(
            output_root=root,
            as_of=packet["as_of"],
        )


def test_tampered_frozen_context_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, packet = _initialize(tmp_path, monkeypatch)
    context = root / "signal_context.csv"
    context.write_text(
        context.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="frozen artifact mismatch: context"):
        shadow_state.run_crypto_tournament_v2_forward_shadow_state(
            output_root=root,
            as_of=packet["as_of"],
        )


def _bars(
    *, start: datetime, closes: Sequence[Decimal], symbol: str = "BTCUSD"
) -> tuple[_Bar, ...]:
    return tuple(
        _Bar(
            timestamp=start + (index * ONE_HOUR),
            symbol=symbol,
            open=close,
            high=close,
            low=close,
            close=close,
            volume=Decimal("1"),
            imputed=False,
        )
        for index, close in enumerate(closes)
    )


def test_first_shadow_hour_uses_prior_target_and_charges_boundary_cost() -> None:
    candidate = build_crypto_tournament_v2_preregistration()["candidates"][0]
    start = _utc(OOS_END_EXCLUSIVE)
    context = _bars(
        start=start - (169 * ONE_HOUR),
        closes=tuple(Decimal(index + 1) for index in range(169)),
    )
    shadow = _bars(
        start=start,
        closes=(context[-1].close * Decimal("1.10"),),
    )

    decisions, _ = shadow_state._build_decision_evidence(
        context=context,
        activation_warmup=(),
        shadow_rows=shadow,
        candidate=candidate,
    )

    assert decisions[0]["applied_exposure"] == "1"
    assert decisions[0]["target_exposure"] == "1"
    assert decisions[0]["boundary_transition_delta"] == "1"
    assert decisions[0]["base_net_return"] == "0.0956"
    assert decisions[0]["stress_net_return"] == "0.0912"


def test_first_shadow_signal_change_is_applied_one_bar_later() -> None:
    candidate = build_crypto_tournament_v2_preregistration()["candidates"][0]
    start = _utc(OOS_END_EXCLUSIVE)
    context = _bars(
        start=start - (169 * ONE_HOUR),
        closes=(Decimal("100"),) * 169,
    )
    shadow = _bars(start=start, closes=(Decimal("110"),))

    decisions, _ = shadow_state._build_decision_evidence(
        context=context,
        activation_warmup=(),
        shadow_rows=shadow,
        candidate=candidate,
    )

    assert decisions[0]["applied_exposure"] == "0"
    assert decisions[0]["target_exposure"] == "1"
    assert decisions[0]["signal_transition_delta"] == "1"
    assert decisions[0]["base_net_return"] == "-0.004"
    assert decisions[0]["stress_net_return"] == "-0.008"


def _authorized_refresh_config(tmp_path: Path) -> CryptoHistoryRefreshConfig:
    return CryptoHistoryRefreshConfig(
        mode="market_data_fetch",
        symbols=("ETHUSD", "SOLUSD"),
        output_path=tmp_path / "ignored.csv",
        packet_path=tmp_path / "ignored.json",
        raw_response_path=tmp_path / "ignored_raw.json",
        market_data_fetch_authorized=True,
        allow_network=True,
        data_intake_only=True,
    )


def test_operating_bridge_derives_one_symbol_and_exact_inclusive_hour(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, initialized = _initialize(tmp_path, monkeypatch)
    start = _utc(initialized["shadow_window"]["start"])
    selected = initialized["selected_candidate"]["symbol"]
    observed: list[CryptoHistoryRefreshConfig] = []

    def runner(config: CryptoHistoryRefreshConfig) -> dict[str, object]:
        observed.append(config)
        request_start = _utc(str(config.start))
        request_end = _utc(str(config.end))
        _write_history(
            Path(config.output_path),
            symbol=config.symbols[0],
            start=request_start,
            hours=1,
        )
        return _write_receipt(
            Path(config.packet_path),
            history_path=Path(config.output_path),
            symbol=config.symbols[0],
            start=request_start,
            end=request_end,
        )

    packet = (
        shadow_operating.run_crypto_tournament_v2_forward_shadow_operating_cycle(
            mode="market_data_fetch",
            tournament_root=tmp_path / "tournament",
            output_root=root,
            as_of=start + ONE_HOUR,
            refresh_config=_authorized_refresh_config(tmp_path),
            refresh_runner=runner,
        )
    )

    assert len(observed) == 1
    assert observed[0].symbols == (selected,)
    assert _utc(str(observed[0].start)) == start
    assert _utc(str(observed[0].end)) == start
    assert observed[0].data_intake_only is True
    assert Path(observed[0].output_path) == (
        root / "refresh" / "selected_symbol_delta.csv"
    )
    assert packet["progress"]["shadow_raw_rows"] == 1
    assert packet["refresh"]["state_accrual_status"] == "accepted"
    assert packet["network_access_attempted"] is True
    assert packet["broker_read_occurred"] is False


def test_operating_bridge_mismatched_receipt_fails_before_state_accrual(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, initialized = _initialize(tmp_path, monkeypatch)
    start = _utc(initialized["shadow_window"]["start"])
    state_path = root / "frozen_state.json"
    before = hashlib.sha256(state_path.read_bytes()).hexdigest()

    def runner(config: CryptoHistoryRefreshConfig) -> dict[str, object]:
        request_start = _utc(str(config.start))
        _write_history(
            Path(config.output_path),
            symbol=config.symbols[0],
            start=request_start,
            hours=1,
        )
        receipt = _write_receipt(
            Path(config.packet_path),
            history_path=Path(config.output_path),
            symbol=config.symbols[0],
            start=request_start,
            end=request_start,
        )
        receipt["requested_symbols"] = [config.symbols[0], "ETHUSD"]
        return receipt

    packet = (
        shadow_operating.run_crypto_tournament_v2_forward_shadow_operating_cycle(
            mode="market_data_fetch",
            tournament_root=tmp_path / "tournament",
            output_root=root,
            as_of=start + ONE_HOUR,
            refresh_config=_authorized_refresh_config(tmp_path),
            refresh_runner=runner,
        )
    )

    assert packet["refresh"]["status"] == "failed_closed_receipt_mismatch"
    assert packet["refresh"]["state_unchanged"] is True
    assert hashlib.sha256(state_path.read_bytes()).hexdigest() == before
    assert packet["progress"]["shadow_raw_rows"] == 0


def test_operating_bridge_exception_is_redacted_and_conservative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, initialized = _initialize(tmp_path, monkeypatch)
    start = _utc(initialized["shadow_window"]["start"])

    def runner(config: CryptoHistoryRefreshConfig) -> dict[str, object]:
        raise RuntimeError("do not expose this detail")

    packet = (
        shadow_operating.run_crypto_tournament_v2_forward_shadow_operating_cycle(
            mode="market_data_fetch",
            tournament_root=tmp_path / "tournament",
            output_root=root,
            as_of=start + ONE_HOUR,
            refresh_config=_authorized_refresh_config(tmp_path),
            refresh_runner=runner,
        )
    )

    assert packet["refresh"]["status"] == "failed_closed"
    assert packet["refresh"]["error_type"] == "RuntimeError"
    assert packet["refresh"]["market_data_fetch_occurred"] is None
    assert packet["refresh"]["network_access_attempted"] is True
    assert "detail" not in json.dumps(packet)


def test_operating_readiness_checks_environment_only_for_actionable_fetch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, initialized = _initialize(tmp_path, monkeypatch)
    start = _utc(initialized["shadow_window"]["start"])

    waiting = (
        shadow_operating.build_crypto_tournament_v2_forward_shadow_refresh_readiness(
            tournament_root=tmp_path / "tournament",
            output_root=root,
            as_of=start,
            env={},
        )
    )
    actionable = (
        shadow_operating.build_crypto_tournament_v2_forward_shadow_refresh_readiness(
            tournament_root=tmp_path / "tournament",
            output_root=root,
            as_of=start + ONE_HOUR,
            env={},
        )
    )

    assert waiting["classification"] == "waiting_for_calendar_hour"
    assert waiting["operator_preflight"] == {}
    assert actionable["classification"] == (
        "blocked_market_data_credentials_or_profile"
    )
    assert "paper_market_data_credentials_required" in actionable["blockers"]
    assert all(
        isinstance(value, bool)
        for value in actionable["operator_preflight"].values()
    )
    assert actionable["network_access_attempted"] is False


def test_operating_fetch_requires_both_explicit_authorization_flags(
    tmp_path: Path,
) -> None:
    config = CryptoHistoryRefreshConfig(
        mode="market_data_fetch",
        output_path=tmp_path / "ignored.csv",
        packet_path=tmp_path / "ignored.json",
        market_data_fetch_authorized=True,
        allow_network=False,
        data_intake_only=True,
    )

    with pytest.raises(ValidationError, match="both explicit"):
        shadow_operating.run_crypto_tournament_v2_forward_shadow_operating_cycle(
            mode="market_data_fetch",
            tournament_root=tmp_path / "tournament",
            output_root=tmp_path / "shadow",
            as_of="2026-08-13T00:00:00+00:00",
            refresh_config=config,
        )


def test_operating_fetch_rejects_overlapping_full_cycle(
    tmp_path: Path,
) -> None:
    root = tmp_path / "shadow"
    calls: list[CryptoHistoryRefreshConfig] = []

    with shadow_operating._exclusive_operating_cycle_lock(root):
        with pytest.raises(ValidationError, match="operating cycle"):
            shadow_operating.run_crypto_tournament_v2_forward_shadow_operating_cycle(
                mode="market_data_fetch",
                tournament_root=tmp_path / "tournament",
                output_root=root,
                as_of="2026-08-13T01:00:00+00:00",
                refresh_config=_authorized_refresh_config(tmp_path),
                refresh_runner=lambda config: calls.append(config) or {},
            )

    assert calls == []


def test_operating_fetch_rejects_unc_root_before_lock_or_adapter(
    tmp_path: Path,
) -> None:
    calls: list[CryptoHistoryRefreshConfig] = []

    with pytest.raises(ValidationError, match="output_root must be a local path"):
        shadow_operating.run_crypto_tournament_v2_forward_shadow_operating_cycle(
            mode="market_data_fetch",
            tournament_root=tmp_path / "tournament",
            output_root=r"\\server\share\shadow",
            as_of="2026-08-13T01:00:00+00:00",
            refresh_config=_authorized_refresh_config(tmp_path),
            refresh_runner=lambda config: calls.append(config) or {},
        )

    assert calls == []


def test_operating_fetch_stays_dormant_without_terminal_winner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[CryptoHistoryRefreshConfig] = []
    monkeypatch.setattr(
        shadow_operating,
        "initialize_crypto_tournament_v2_forward_shadow_state",
        lambda **_: {
            "classification": "waiting_for_tournament_terminal",
            "network_access_attempted": False,
            "market_data_fetch_occurred": False,
        },
    )

    packet = (
        shadow_operating.run_crypto_tournament_v2_forward_shadow_operating_cycle(
            mode="market_data_fetch",
            tournament_root=tmp_path / "tournament",
            output_root=tmp_path / "shadow",
            as_of="2026-08-12T00:00:00+00:00",
            refresh_config=_authorized_refresh_config(tmp_path),
            refresh_runner=lambda config: calls.append(config) or {},
        )
    )

    assert calls == []
    assert packet["refresh"]["status"] == "not_run"
    assert packet["refresh"]["network_access_attempted"] is False


def test_operating_cli_enforces_dual_authorization(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as missing_network:
        shadow_operating.main(
            ["--mode", "market_data_fetch", "--market-data-fetch-authorized"]
        )
    assert missing_network.value.code == 2
    monkeypatch.setattr(
        shadow_operating,
        "run_crypto_tournament_v2_forward_shadow_operating_cycle",
        lambda **_: {"classification": "test_only"},
    )

    assert (
        shadow_operating.main(
            [
                "--mode",
                "market_data_fetch",
                "--market-data-fetch-authorized",
                "--allow-network",
            ]
        )
        == 0
    )
    assert "test_only" in capsys.readouterr().out


def test_shadow_research_state_has_no_execution_or_network_import() -> None:
    source = Path(
        "src/algotrader/research/crypto_tournament_v2_forward_shadow_state.py"
    ).read_text(encoding="utf-8")

    assert "algotrader.execution" not in source
    assert "algotrader.orchestration" not in source
    assert "http.client" not in source
    assert "urllib" not in source
