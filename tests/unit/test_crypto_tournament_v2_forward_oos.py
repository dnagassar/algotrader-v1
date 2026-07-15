from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shutil
from typing import Mapping, Sequence

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.crypto_history_refresh_adapter import (
    CryptoHistoryRefreshConfig,
)
from algotrader.orchestration.crypto_tournament_v2_forward_oos import (
    build_crypto_tournament_v2_refresh_readiness,
    run_crypto_tournament_v2_operating_cycle,
)
from algotrader.research.crypto_preregistered_tournament import (
    _completed_round_trips,
)
from algotrader.research.crypto_preregistered_tournament_v2 import (
    CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT,
    DISCOVERY_END_EXCLUSIVE,
    DISCOVERY_START,
    EMBARGO_START,
    OOS_END_EXCLUSIVE,
    OOS_START,
    TOURNAMENT_V2_SYMBOLS,
)
from algotrader.research.crypto_tournament_v2_forward_oos import (
    _completed_round_trips_with_initial,
    _eligible_and_selected,
    _simulate_window,
    _window_metrics,
    initialize_crypto_tournament_v2_forward_oos,
    run_crypto_tournament_v2_forward_oos,
)


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).astimezone(UTC)


def _write_history(
    path: Path,
    *,
    start: datetime,
    hours: int,
    missing: set[tuple[str, datetime]] | None = None,
    price_shift: Decimal = Decimal("0"),
) -> None:
    skipped = missing or set()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(
        "w", encoding="utf-8", newline=""
    ) as stream:
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
        for symbol_index, symbol in enumerate(
            TOURNAMENT_V2_SYMBOLS
        ):
            for index in range(hours):
                timestamp = start + timedelta(hours=index)
                if (symbol, timestamp) in skipped:
                    continue
                price = (
                    Decimal("100")
                    + price_shift
                    + Decimal(symbol_index * 10)
                    + (Decimal(index % 97) / Decimal("100"))
                )
                text = format(price, "f")
                writer.writerow(
                    {
                        "timestamp": timestamp.isoformat(),
                        "symbol": symbol,
                        "open": text,
                        "high": text,
                        "low": text,
                        "close": text,
                        "volume": "1",
                    }
                )


def _write_receipt(
    path: Path,
    *,
    output_path: Path,
    start: datetime,
    end: datetime,
    symbols: Sequence[str] = TOURNAMENT_V2_SYMBOLS,
    paper_submit_occurred: bool = False,
) -> dict[str, object]:
    packet: dict[str, object] = {
        "schema_version": (
            "v5_22_crypto_history_refresh_adapter_receipt_v2"
        ),
        "record_type": "crypto_history_refresh_adapter_packet",
        "classification": "market_data_refresh_ready",
        "coverage_gate_classification": (
            "not_evaluated_data_intake_only"
        ),
        "mode": "market_data_fetch",
        "authorization_status": "authorized",
        "endpoint_safety_status": (
            "passed_non_live_endpoint_check"
        ),
        "data_source": (
            "alpaca_market_data_crypto_bars_v1beta3"
        ),
        "timeframe": "1Hour",
        "loc": "us",
        "schema_validation_status": "passed",
        "requested_symbols": list(symbols),
        "fetched_symbols": list(symbols),
        "output_path": str(output_path),
        "packet_path": str(path),
        "data_intake_only": True,
        "strategy_evidence_evaluation_performed": False,
        "output_sha256": hashlib.sha256(
            output_path.read_bytes()
        ).hexdigest(),
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "as_of": (end + timedelta(hours=1)).isoformat(),
        "market_data_fetch_occurred": True,
        "network_access_attempted": True,
        "broker_read_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "paper_submit_authorized": False,
        "paper_submit_occurred": paper_submit_occurred,
        "paper_cancel_occurred": False,
        "paper_replace_occurred": False,
        "paper_close_occurred": False,
        "paper_liquidate_occurred": False,
        "live_authorized": False,
        "live_endpoint_indicator": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(packet, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return packet


@pytest.fixture(scope="module")
def frozen_state_root(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    base = tmp_path_factory.mktemp("crypto_tournament_v2")
    source = base / "source.csv"
    receipt = base / "source_receipt.json"
    root = base / "state"
    discovery_start = _utc(DISCOVERY_START)
    discovery_end = _utc(DISCOVERY_END_EXCLUSIVE)
    gap = discovery_start + timedelta(hours=100)
    missing = {
        (symbol, gap) for symbol in TOURNAMENT_V2_SYMBOLS
    }
    _write_history(
        source,
        start=discovery_start,
        hours=int(
            (discovery_end - discovery_start)
            / timedelta(hours=1)
        ),
        missing=missing,
    )
    _write_receipt(
        receipt,
        output_path=source,
        start=discovery_start,
        end=discovery_end - timedelta(hours=1),
        symbols=(*TOURNAMENT_V2_SYMBOLS, "ADAUSD"),
    )
    initialize_crypto_tournament_v2_forward_oos(
        discovery_source_path=source,
        discovery_receipt_path=receipt,
        output_root=root,
        as_of=DISCOVERY_END_EXCLUSIVE,
    )
    return root


def _copy_state(
    frozen_state_root: Path,
    tmp_path: Path,
) -> Path:
    destination = tmp_path / "state"
    shutil.copytree(frozen_state_root, destination)
    return destination


def _delta(
    tmp_path: Path,
    *,
    start: datetime,
    hours: int,
    missing: set[tuple[str, datetime]] | None = None,
    price_shift: Decimal = Decimal("100"),
) -> tuple[Path, Path]:
    history = tmp_path / "delta.csv"
    receipt = tmp_path / "delta_receipt.json"
    _write_history(
        history,
        start=start,
        hours=hours,
        missing=missing,
        price_shift=price_shift,
    )
    _write_receipt(
        receipt,
        output_path=history,
        start=start,
        end=start + timedelta(hours=hours - 1),
    )
    return history, receipt


def test_initialization_freezes_discovery_without_candidate_metrics(
    frozen_state_root: Path,
) -> None:
    packet = run_crypto_tournament_v2_forward_oos(
        output_root=frozen_state_root,
        as_of="2026-07-15T12:00:00+00:00",
    )

    assert (
        packet["classification"]
        == "research_ready_for_future_oos_accrual"
    )
    assert packet["preregistration_fingerprint"] == (
        CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT
    )
    assert packet["discovery"]["normalized_rows"] == 12_960
    assert packet["discovery"]["imputed_rows"] == 3
    assert packet["candidate_evaluations"] == []
    assert packet["ranking"] == []
    assert packet["selected_candidate"] == {}
    assert packet["terminal_scoring_performed"] is False
    assert packet["paper_or_broker_eligible"] is False
    assert packet["broker_mutation_occurred"] is False
    assert packet["paper_submit_occurred"] is False
    assert packet["network_access_attempted"] is False


def test_frozen_discovery_rewrite_is_rejected(
    frozen_state_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_state(frozen_state_root, tmp_path)
    discovery = root / "frozen_discovery_history.csv"
    discovery.write_text(
        discovery.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
        match="frozen artifact mismatch: discovery",
    ):
        run_crypto_tournament_v2_forward_oos(
            output_root=root,
            as_of="2026-07-15T12:00:00+00:00",
        )


def test_receipt_with_paper_mutation_is_rejected(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.csv"
    receipt = tmp_path / "receipt.json"
    start = _utc(DISCOVERY_START)
    end = _utc(DISCOVERY_END_EXCLUSIVE)
    _write_history(
        source,
        start=start,
        hours=4_320,
    )
    _write_receipt(
        receipt,
        output_path=source,
        start=start,
        end=end - timedelta(hours=1),
        paper_submit_occurred=True,
    )

    with pytest.raises(
        ValidationError,
        match="no-mutation safety field",
    ):
        initialize_crypto_tournament_v2_forward_oos(
            discovery_source_path=source,
            discovery_receipt_path=receipt,
            output_root=tmp_path / "state",
            as_of=end,
        )

def test_discovery_source_with_future_row_is_rejected_before_freeze(
    tmp_path: Path,
) -> None:
    source = tmp_path / "future_source.csv"
    receipt = tmp_path / "future_receipt.json"
    start = _utc(DISCOVERY_START)
    end = _utc(DISCOVERY_END_EXCLUSIVE)
    _write_history(
        source,
        start=start,
        hours=4_321,
    )
    _write_receipt(
        receipt,
        output_path=source,
        start=start,
        end=end - timedelta(hours=1),
    )

    with pytest.raises(
        ValidationError,
        match="after its guarded cutoff",
    ):
        initialize_crypto_tournament_v2_forward_oos(
            discovery_source_path=source,
            discovery_receipt_path=receipt,
            output_root=tmp_path / "state",
            as_of=end,
        )


def test_first_oos_return_uses_embargo_signal_and_charges_boundary_entry(
) -> None:
    point = _simulate_window(
        initial_exposure=Decimal("1"),
        timestamps=(_utc(OOS_START),),
        asset_returns=(Decimal("0.10"),),
        targets=(Decimal("1"),),
        fee_bps=Decimal("10"),
        slippage_bps=Decimal("0"),
    )[0]

    assert point.applied_exposure == Decimal("1")
    assert point.asset_return == Decimal("0.10")
    assert point.boundary_transition_delta == Decimal("1")
    assert point.signal_transition_delta == Decimal("0")
    assert point.net_return == Decimal("0.09890")
    assert _window_metrics((point,))["total_return"] == "0.0989"


def test_embargo_round_trips_are_excluded_by_calculation() -> None:
    discovery_targets = (Decimal("1"), Decimal("0"))
    embargo_targets = (
        Decimal("1"),
        Decimal("0"),
        Decimal("1"),
    )
    oos_targets = (Decimal("0"),)

    accepted = (
        _completed_round_trips(discovery_targets)
        + _completed_round_trips_with_initial(
            oos_targets,
            initial_exposure=embargo_targets[-1],
        )
    )
    naive_including_embargo = _completed_round_trips(
        discovery_targets + embargo_targets + oos_targets
    )

    assert accepted == 2
    assert naive_including_embargo == 3


def test_multiple_qualified_candidates_still_select_exactly_one() -> None:
    eligible, selected = _eligible_and_selected(
        (
            {
                "candidate_id": "first",
                "candidate_fingerprint": "a" * 64,
                "candidate_decision": (
                    "eligible_for_no_submit_shadow_evaluation"
                ),
            },
            {
                "candidate_id": "second",
                "candidate_fingerprint": "b" * 64,
                "candidate_decision": (
                    "eligible_for_no_submit_shadow_evaluation"
                ),
            },
        )
    )

    assert len(eligible) == 2
    assert selected["candidate_id"] == "first"
    assert selected["paper_or_broker_eligible"] is False


def test_partial_accrual_is_metric_free_and_exact_retry_is_idempotent(
    frozen_state_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_state(frozen_state_root, tmp_path)
    start = _utc(EMBARGO_START)
    history, receipt = _delta(
        tmp_path,
        start=start,
        hours=12,
    )
    first = run_crypto_tournament_v2_forward_oos(
        output_root=root,
        as_of=start + timedelta(hours=12),
        delta_history_path=history,
        delta_receipt_path=receipt,
        operation_network_access=True,
        operation_market_data_fetch=True,
    )
    second = run_crypto_tournament_v2_forward_oos(
        output_root=root,
        as_of=start + timedelta(hours=12),
        delta_history_path=history,
        delta_receipt_path=receipt,
        operation_network_access=True,
        operation_market_data_fetch=True,
    )

    assert first["candidate_evaluations"] == []
    assert first["terminal_scoring_performed"] is False
    assert first["receipt_count"] == 2
    assert second["receipt_count"] == 2
    assert second["frozen_state"]["embargo_raw_rows"] == 36
    assert second["frozen_state"]["oos_raw_rows"] == 0
    assert second["next_refresh"]["classification"] == (
        "waiting_for_calendar_hour"
    )
    assert second["market_data_fetch_occurred"] is True
    assert second["broker_mutation_occurred"] is False
    assert second["paper_submit_occurred"] is False


def test_conflicting_rewrite_fails_before_state_change(
    frozen_state_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_state(frozen_state_root, tmp_path)
    start = _utc(EMBARGO_START)
    history, receipt = _delta(
        tmp_path,
        start=start,
        hours=12,
    )
    run_crypto_tournament_v2_forward_oos(
        output_root=root,
        as_of=start + timedelta(hours=12),
        delta_history_path=history,
        delta_receipt_path=receipt,
    )
    state_path = root / "frozen_state.json"
    before = hashlib.sha256(state_path.read_bytes()).hexdigest()
    _write_history(
        history,
        start=start,
        hours=12,
        price_shift=Decimal("101"),
    )
    _write_receipt(
        receipt,
        output_path=history,
        start=start,
        end=start + timedelta(hours=11),
    )

    with pytest.raises(
        ValidationError,
        match="conflicting rewrite",
    ):
        run_crypto_tournament_v2_forward_oos(
            output_root=root,
            as_of=start + timedelta(hours=12),
            delta_history_path=history,
            delta_receipt_path=receipt,
        )
    assert hashlib.sha256(state_path.read_bytes()).hexdigest() == before


def test_preterminal_oos_never_emits_candidate_metrics(
    frozen_state_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_state(frozen_state_root, tmp_path)
    start = _utc(EMBARGO_START)
    history, receipt = _delta(
        tmp_path,
        start=start,
        hours=48,
    )
    packet = run_crypto_tournament_v2_forward_oos(
        output_root=root,
        as_of=start + timedelta(hours=48),
        delta_history_path=history,
        delta_receipt_path=receipt,
    )

    assert packet["classification"] == "collecting_untouched_oos"
    assert packet["candidate_evaluations"] == []
    assert packet["ranking"] == []
    assert packet["selected_candidate"] == {}
    assert packet["terminal_scoring_performed"] is False
    assert packet["oos_progress"]["observed_rows_per_symbol"] == {
        symbol: 24 for symbol in TOURNAMENT_V2_SYMBOLS
    }


def test_terminal_complete_window_scores_all_nine_candidates_once(
    frozen_state_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_state(frozen_state_root, tmp_path)
    start = _utc(EMBARGO_START)
    terminal = _utc(OOS_END_EXCLUSIVE)
    hours = int((terminal - start) / timedelta(hours=1))
    history, receipt = _delta(
        tmp_path,
        start=start,
        hours=hours,
    )
    packet = run_crypto_tournament_v2_forward_oos(
        output_root=root,
        as_of=terminal,
        delta_history_path=history,
        delta_receipt_path=receipt,
    )

    assert packet["classification"] in {
        "no_candidate_qualified",
        "eligible_for_no_submit_shadow_evaluation",
    }
    assert packet["terminal_scoring_performed"] is True
    assert len(packet["candidate_evaluations"]) == 9
    assert len(packet["ranking"]) == 9
    assert len(set(packet["ranking"])) == 9
    assert len(packet["terminal_evidence_fingerprint"]) == 64
    assert packet["paper_or_broker_eligible"] is False
    assert packet["paper_planning_eligibility"] == "not_eligible"
    assert packet["paper_or_live_execution_authorized"] is False
    assert all(
        item["paper_or_broker_eligible"] is False
        for item in packet["candidate_evaluations"]
    )
    assert all(
        item["embargo_round_trips_excluded"] is True
        for item in packet["candidate_evaluations"]
    )
    terminal_path = root / "terminal_packet.json"
    state_path = root / "frozen_state.json"
    canonical = json.loads(terminal_path.read_text(encoding="utf-8"))
    assert "frozen_state" not in canonical
    assert canonical["terminal_closure"] == {
        "terminal_outcome_closed": True,
        "terminal_classification": packet["classification"],
        "terminal_closed_at": terminal.isoformat(),
        "terminal_scoring_performed": True,
        "terminal_evidence_fingerprint": (
            packet["terminal_evidence_fingerprint"]
        ),
    }
    terminal_sha = hashlib.sha256(terminal_path.read_bytes()).hexdigest()
    state_sha = hashlib.sha256(state_path.read_bytes()).hexdigest()

    replay = run_crypto_tournament_v2_forward_oos(
        output_root=root,
        as_of=terminal + timedelta(days=1),
    )

    assert replay["classification"] == packet["classification"]
    assert replay["terminal_evidence_fingerprint"] == (
        packet["terminal_evidence_fingerprint"]
    )
    assert replay["candidate_evaluations"] == packet["candidate_evaluations"]
    assert replay["next_refresh"]["classification"] == (
        "terminal_window_closed"
    )
    assert hashlib.sha256(terminal_path.read_bytes()).hexdigest() == (
        terminal_sha
    )
    assert hashlib.sha256(state_path.read_bytes()).hexdigest() == state_sha

    with pytest.raises(
        ValidationError,
        match="terminal outcome rejects later deltas",
    ):
        run_crypto_tournament_v2_forward_oos(
            output_root=root,
            as_of=terminal + timedelta(days=1),
            delta_history_path=history,
            delta_receipt_path=receipt,
        )

    terminal_path.write_text(
        terminal_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        ValidationError,
        match="terminal packet hash mismatch",
    ):
        run_crypto_tournament_v2_forward_oos(
            output_root=root,
            as_of=terminal + timedelta(days=1),
        )


def test_isolated_oos_gap_holds_signal_on_one_and_four_hour_views(
    frozen_state_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_state(frozen_state_root, tmp_path)
    start = _utc(EMBARGO_START)
    terminal = _utc(OOS_END_EXCLUSIVE)
    missing_at = _utc(OOS_START) + timedelta(hours=5)
    history, receipt = _delta(
        tmp_path,
        start=start,
        hours=int((terminal - start) / timedelta(hours=1)),
        missing={("BTCUSD", missing_at)},
    )
    packet = run_crypto_tournament_v2_forward_oos(
        output_root=root,
        as_of=terminal,
        delta_history_path=history,
        delta_receipt_path=receipt,
    )

    btc = [
        item
        for item in packet["candidate_evaluations"]
        if item["symbol"] == "BTCUSD"
    ]
    assert len(btc) == 3
    assert all(item["primary"]["oos_imputed_bar_count"] == 1 for item in btc)
    assert all(item["robustness"]["oos_imputed_bar_count"] == 1 for item in btc)
    assert all(item["primary"]["imputed_signal_transition_count"] == 0 for item in btc)
    assert all(item["robustness"]["imputed_signal_transition_count"] == 0 for item in btc)




def test_missing_first_oos_hour_closes_terminal_without_scoring(
    frozen_state_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_state(frozen_state_root, tmp_path)
    start = _utc(EMBARGO_START)
    terminal = _utc(OOS_END_EXCLUSIVE)
    missing = {("BTCUSD", _utc(OOS_START))}
    history, receipt = _delta(
        tmp_path,
        start=start,
        hours=int((terminal - start) / timedelta(hours=1)),
        missing=missing,
    )
    packet = run_crypto_tournament_v2_forward_oos(
        output_root=root,
        as_of=terminal,
        delta_history_path=history,
        delta_receipt_path=receipt,
    )

    assert packet["classification"] == "terminal_input_quality_gate"
    assert packet["terminal_scoring_performed"] is False
    assert packet["candidate_evaluations"] == []
    assert any(
        "oos_BTCUSD_boundary_bar_missing" == item
        for item in packet["terminal_input_quality"]["errors"]
    )
    canonical = json.loads(
        (root / "terminal_packet.json").read_text(encoding="utf-8")
    )
    assert canonical["terminal_closure"][
        "terminal_outcome_closed"
    ] is True
    assert canonical["terminal_closure"][
        "terminal_scoring_performed"
    ] is False
    replay = run_crypto_tournament_v2_forward_oos(
        output_root=root,
        as_of=terminal + timedelta(days=1),
    )
    assert replay["classification"] == "terminal_input_quality_gate"
    assert replay["candidate_evaluations"] == []
    assert replay["frozen_state"]["terminal_outcome_closed"] is True
    assert replay["frozen_state"]["terminal_scoring_performed"] is False


def test_readiness_is_boolean_only_and_network_free(
    frozen_state_root: Path,
) -> None:
    packet = build_crypto_tournament_v2_refresh_readiness(
        output_root=frozen_state_root,
        as_of="2026-07-15T12:00:00+00:00",
        env={},
    )

    assert packet["classification"] == (
        "blocked_market_data_credentials_or_profile"
    )
    assert "paper_market_data_credentials_required" in (
        packet["blockers"]
    )
    assert packet["market_data_fetch_occurred"] is False
    assert packet["network_access_attempted"] is False
    assert packet["broker_mutation_occurred"] is False
    assert all(
        isinstance(value, bool)
        for value in packet["operator_preflight"].values()
    )


def test_operator_narrows_fetch_to_exact_three_symbol_window(
    frozen_state_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_state(frozen_state_root, tmp_path)
    as_of = _utc("2026-07-15T12:00:00+00:00")
    observed: list[CryptoHistoryRefreshConfig] = []

    def refresh_runner(
        config: CryptoHistoryRefreshConfig,
    ) -> Mapping[str, object]:
        observed.append(config)
        start = (
            config.start
            if isinstance(config.start, datetime)
            else _utc(str(config.start))
        )
        end = (
            config.end
            if isinstance(config.end, datetime)
            else _utc(str(config.end))
        )
        _write_history(
            Path(config.output_path),
            start=start,
            hours=int(
                (end - start) / timedelta(hours=1)
            )
            + 1,
        )
        return _write_receipt(
            Path(config.packet_path),
            output_path=Path(config.output_path),
            start=start,
            end=end,
            symbols=config.symbols,
        )

    packet = run_crypto_tournament_v2_operating_cycle(
        mode="market_data_fetch",
        output_root=root,
        as_of=as_of,
        refresh_config=CryptoHistoryRefreshConfig(
            mode="market_data_fetch",
            output_path=tmp_path / "ignored.csv",
            packet_path=tmp_path / "ignored.json",
            raw_response_path=tmp_path / "ignored_raw.json",
            market_data_fetch_authorized=True,
            allow_network=True,
        ),
        refresh_runner=refresh_runner,
    )

    assert len(observed) == 1
    assert observed[0].symbols == TOURNAMENT_V2_SYMBOLS
    assert _utc(str(observed[0].start)) == _utc(EMBARGO_START)
    assert _utc(str(observed[0].end)) == (
        as_of - timedelta(hours=1)
    )
    assert observed[0].timeframe == "1Hour"
    assert observed[0].data_intake_only is True
    assert packet["market_data_fetch_occurred"] is True
    assert packet["network_access_attempted"] is True
    assert packet["broker_mutation_occurred"] is False
    assert packet["paper_submit_occurred"] is False
    assert packet["candidate_evaluations"] == []


def test_refresh_exception_reports_network_attempt_conservatively(
    frozen_state_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_state(frozen_state_root, tmp_path)

    def refresh_runner(
        config: CryptoHistoryRefreshConfig,
    ) -> Mapping[str, object]:
        raise RuntimeError("redacted refresh failure")

    packet = run_crypto_tournament_v2_operating_cycle(
        mode="market_data_fetch",
        output_root=root,
        as_of="2026-07-15T12:00:00+00:00",
        refresh_config=CryptoHistoryRefreshConfig(
            mode="market_data_fetch",
            output_path=tmp_path / "ignored.csv",
            packet_path=tmp_path / "ignored.json",
            raw_response_path=tmp_path / "ignored_raw.json",
            market_data_fetch_authorized=True,
            allow_network=True,
        ),
        refresh_runner=refresh_runner,
    )

    assert packet["network_access_attempted"] is True
    assert packet["market_data_fetch_occurred"] is None
    assert packet["refresh"] == {
        "status": "failed_closed",
        "error_type": "RuntimeError",
        "market_data_fetch_occurred": None,
        "market_data_fetch_occurrence_known": False,
        "network_access_attempted": True,
    }


def test_returned_receipt_window_mismatch_fails_before_accrual(
    frozen_state_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_state(frozen_state_root, tmp_path)
    state_path = root / "frozen_state.json"
    before = hashlib.sha256(state_path.read_bytes()).hexdigest()

    def refresh_runner(
        config: CryptoHistoryRefreshConfig,
    ) -> Mapping[str, object]:
        start = _utc(str(config.start))
        end = _utc(str(config.end))
        _write_history(
            Path(config.output_path),
            start=start,
            hours=int((end - start) / timedelta(hours=1)) + 1,
        )
        returned = _write_receipt(
            Path(config.packet_path),
            output_path=Path(config.output_path),
            start=start,
            end=end,
            symbols=config.symbols,
        )
        returned["requested_end"] = start.isoformat()
        return returned

    packet = run_crypto_tournament_v2_operating_cycle(
        mode="market_data_fetch",
        output_root=root,
        as_of="2026-07-15T12:00:00+00:00",
        refresh_config=CryptoHistoryRefreshConfig(
            mode="market_data_fetch",
            output_path=tmp_path / "ignored.csv",
            packet_path=tmp_path / "ignored.json",
            raw_response_path=tmp_path / "ignored_raw.json",
            market_data_fetch_authorized=True,
            allow_network=True,
        ),
        refresh_runner=refresh_runner,
    )

    assert packet["network_access_attempted"] is True
    assert packet["market_data_fetch_occurred"] is True
    assert packet["refresh"]["status"] == (
        "failed_closed_receipt_mismatch"
    )
    assert packet["refresh"]["broker_mutation_occurred"] is False
    assert packet["refresh"]["paper_submit_occurred"] is False
    assert hashlib.sha256(state_path.read_bytes()).hexdigest() == before



def test_research_module_has_no_execution_or_network_import() -> None:
    source = Path(
        "src/algotrader/research/"
        "crypto_tournament_v2_forward_oos.py"
    ).read_text(encoding="utf-8")

    assert "algotrader.execution" not in source
    assert "algotrader.orchestration" not in source
    assert "http.client" not in source
    assert "urllib" not in source
