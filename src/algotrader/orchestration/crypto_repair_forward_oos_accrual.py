"""Frozen-candidate forward-OOS accrual for the ADA repair diagnostic.

This is an operating wrapper around the research evidence battery.  It owns
runtime state under ``runs/`` and may invoke the existing guarded, read-only
crypto-history refresh adapter.  It never imports an execution or broker path
into research code, and it never authorizes paper submission or a broker
mutation.
"""

from __future__ import annotations

import argparse
import csv
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.crypto_history_refresh_adapter import (
    CRYPTO_HISTORY_REFRESH_DEFAULT_OUTPUT_PATH,
    CryptoHistoryRefreshConfig,
    run_crypto_history_refresh,
)
from algotrader.research.crypto_strategy_evidence_battery import (
    CRYPTO_REPAIR_FRESH_OOS_SCHEMA_VERSION,
    DEFAULT_CRYPTO_EVIDENCE_SYMBOLS,
    DEFAULT_FRESH_OOS_REPAIR_CANDIDATE,
    DEFAULT_REPAIR_DISCOVERY_CUTOFF,
    CryptoEvidenceAssumptions,
    build_crypto_repair_fresh_oos_validation_packet,
)


CRYPTO_REPAIR_FORWARD_OOS_ACCRUAL_SCHEMA_VERSION = (
    "v5_20_2_crypto_repair_forward_oos_accrual_v1"
)
CRYPTO_REPAIR_FORWARD_OOS_DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_repair_forward_oos_accrual/latest"
)
CRYPTO_REPAIR_FORWARD_OOS_DEFAULT_HISTORY_PATH = (
    CRYPTO_HISTORY_REFRESH_DEFAULT_OUTPUT_PATH
)
CRYPTO_REPAIR_FORWARD_OOS_TIMEFRAME = "1Hour"
CRYPTO_REPAIR_FORWARD_OOS_REQUIRED_MIN_ROWS = 26
CRYPTO_REPAIR_FORWARD_OOS_EVALUATION_POLICY_VERSION = (
    CRYPTO_REPAIR_FRESH_OOS_SCHEMA_VERSION
)

_REQUIRED_CSV_COLUMNS = ("timestamp", "symbol", "open", "high", "low", "close")
_FALSE_SAFETY_FIELDS = (
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "live_authorized",
    "broker_read_occurred",
    "broker_mutation_occurred",
    "paper_submit_occurred",
    "paper_cancel_occurred",
    "paper_replace_occurred",
    "paper_close_occurred",
    "paper_liquidate_occurred",
    "live_endpoint_touched",
    "credential_values_exposed",
)
_FIXTURE_SOURCE_MARKERS = ("fixture", "synthetic", "deterministic_unit_fixture")

__all__ = [
    "CRYPTO_REPAIR_FORWARD_OOS_ACCRUAL_SCHEMA_VERSION",
    "CRYPTO_REPAIR_FORWARD_OOS_DEFAULT_HISTORY_PATH",
    "CRYPTO_REPAIR_FORWARD_OOS_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_REPAIR_FORWARD_OOS_EVALUATION_POLICY_VERSION",
    "CRYPTO_REPAIR_FORWARD_OOS_REQUIRED_MIN_ROWS",
    "CRYPTO_REPAIR_FORWARD_OOS_TIMEFRAME",
    "build_frozen_candidate_descriptor",
    "main",
    "render_crypto_repair_forward_oos_markdown",
    "run_crypto_repair_forward_oos_accrual",
]


@dataclass(frozen=True, slots=True)
class _NormalizedRow:
    timestamp: datetime
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: str
    source: str

    def key(self) -> tuple[str, datetime]:
        return (self.symbol, self.timestamp)

    def canonical(self) -> dict[str, str]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "open": _decimal_text(self.open),
            "high": _decimal_text(self.high),
            "low": _decimal_text(self.low),
            "close": _decimal_text(self.close),
            "volume": self.volume,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class _RowsLoad:
    path: Path
    rows: tuple[_NormalizedRow, ...]
    errors: tuple[str, ...]
    duplicate_timestamp_rows: int
    out_of_order_rows: int
    fixture_source_detected: bool

    @property
    def valid(self) -> bool:
        return not self.errors and not self.duplicate_timestamp_rows and not self.out_of_order_rows


RefreshRunner = Callable[[CryptoHistoryRefreshConfig], Mapping[str, object]]


def run_crypto_repair_forward_oos_accrual(
    *,
    output_root: Path | str = CRYPTO_REPAIR_FORWARD_OOS_DEFAULT_OUTPUT_ROOT,
    discovery_history_path: Path | str = CRYPTO_REPAIR_FORWARD_OOS_DEFAULT_HISTORY_PATH,
    refresh_config: CryptoHistoryRefreshConfig | None = None,
    refresh_runner: RefreshRunner = run_crypto_history_refresh,
    as_of: datetime | str | None = None,
    discovery_cutoff: datetime | str = DEFAULT_REPAIR_DISCOVERY_CUTOFF,
    candidate_id: str = DEFAULT_FRESH_OOS_REPAIR_CANDIDATE,
    timeframe: str = CRYPTO_REPAIR_FORWARD_OOS_TIMEFRAME,
    assumptions: CryptoEvidenceAssumptions | None = None,
    required_min_oos_rows: int = CRYPTO_REPAIR_FORWARD_OOS_REQUIRED_MIN_ROWS,
    evaluation_policy_version: str = CRYPTO_REPAIR_FORWARD_OOS_EVALUATION_POLICY_VERSION,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Accrue strict future bars and run the existing frozen ADA OOS gate.

    ``discovery_history_path`` is the immutable discovery-period reference.
    When ``refresh_config`` is supplied, its adapter output is treated as a
    delta feed: every row must be strictly after the frozen cutoff.  With no
    refresh configuration, the discovery path is used as a local full-history
    replay and only its strictly post-cutoff rows are accrued.
    """

    root = Path(output_root)
    cutoff = _utc_datetime(discovery_cutoff, "discovery_cutoff")
    evaluated_at = _utc_datetime(as_of or datetime.now(UTC), "as_of")
    checked_assumptions = assumptions or CryptoEvidenceAssumptions()
    checked_timeframe = _timeframe(timeframe)
    required_rows = _required_rows(required_min_oos_rows, checked_assumptions)
    policy_version = _required_text(evaluation_policy_version, "evaluation_policy_version")
    discovery_path = Path(discovery_history_path)
    state_paths = _state_paths(root)

    discovery_load = _load_normalized_rows(discovery_path)
    discovery_rows = tuple(row for row in discovery_load.rows if row.timestamp <= cutoff)
    discovery_hash = _rows_hash(discovery_rows)
    descriptor = build_frozen_candidate_descriptor(
        discovery_cutoff=cutoff,
        candidate_id=candidate_id,
        timeframe=checked_timeframe,
        assumptions=checked_assumptions,
        required_min_oos_rows=required_rows,
        evaluation_policy_version=policy_version,
        relevant_discovery_evidence_input_hash=discovery_hash,
    )

    packet = _base_packet(
        descriptor=descriptor,
        cutoff=cutoff,
        evaluated_at=evaluated_at,
        output_root=root,
        discovery_path=discovery_path,
        refresh_config=refresh_config,
    )
    blockers: list[str] = []
    integrity = _integrity_checks(
        discovery_load=discovery_load,
        cutoff=cutoff,
        refresh_config=refresh_config,
    )
    packet["integrity_checks"] = integrity

    if candidate_id != DEFAULT_FRESH_OOS_REPAIR_CANDIDATE:
        blockers.append("unsupported_frozen_candidate")
    if checked_timeframe != CRYPTO_REPAIR_FORWARD_OOS_TIMEFRAME:
        blockers.append("unsupported_timeframe")
    if policy_version != CRYPTO_REPAIR_FORWARD_OOS_EVALUATION_POLICY_VERSION:
        blockers.append("unsupported_evaluation_policy_version")
    if discovery_load.errors:
        blockers.extend(discovery_load.errors)
    if discovery_load.duplicate_timestamp_rows:
        blockers.append("duplicate_discovery_timestamp")
    if discovery_load.out_of_order_rows:
        blockers.append("out_of_order_discovery_bars")
    if discovery_load.fixture_source_detected:
        blockers.append("fixture_or_synthetic_discovery_history")

    frozen_manifest = _read_json_mapping(state_paths["frozen_candidate"])
    if frozen_manifest:
        expected_hash = str(frozen_manifest.get("relevant_discovery_evidence_input_hash", ""))
        if expected_hash and expected_hash != discovery_hash:
            blockers.append("rewritten_discovery_period_data")
            integrity["discovery_period_hash"] = "failed"
        else:
            integrity["discovery_period_hash"] = "passed"
        expected_configuration = str(
            frozen_manifest.get("candidate_configuration_fingerprint", "")
        )
        if expected_configuration != descriptor["candidate_configuration_fingerprint"]:
            blockers.append("candidate_fingerprint_mismatch")
            integrity["candidate_fingerprint"] = "failed"
        else:
            integrity["candidate_fingerprint"] = "passed"
        packet["frozen_candidate"] = dict(frozen_manifest)
    else:
        integrity["discovery_period_hash"] = (
            "passed" if not discovery_load.errors else "failed"
        )
        integrity["candidate_fingerprint"] = "not_yet_persisted"
        if not blockers:
            if write_artifacts:
                root.mkdir(parents=True, exist_ok=True)
                _write_json(state_paths["frozen_candidate"], descriptor)
            packet["frozen_candidate"] = descriptor
            integrity["candidate_fingerprint"] = "passed"

    if blockers:
        return _finalize_packet(
            packet,
            blockers=blockers,
            classification="blocked_integrity",
            root=root,
            state_paths=state_paths,
            write_artifacts=write_artifacts,
        )

    refresh_packet: Mapping[str, object] = {}
    source_path = discovery_path
    delta_is_refresh_output = False
    if refresh_config is not None:
        if refresh_config.timeframe != checked_timeframe:
            return _finalize_packet(
                packet,
                blockers=["refresh_timeframe_mismatch"],
                classification="blocked_integrity",
                root=root,
                state_paths=state_paths,
                write_artifacts=write_artifacts,
            )
        try:
            refresh_packet = dict(refresh_runner(refresh_config))
        except Exception as exc:  # adapter failure must remain a safe block
            packet["refresh"] = {
                "status": "failed",
                "error_type": exc.__class__.__name__,
                "market_data_fetch_occurred": False,
                "network_access_attempted": False,
            }
            return _finalize_packet(
                packet,
                blockers=["refresh_failure"],
                classification="blocked_refresh_failure",
                root=root,
                state_paths=state_paths,
                write_artifacts=write_artifacts,
            )
        packet["refresh"] = _refresh_summary(refresh_packet)
        source_path = refresh_config.output_path
        delta_is_refresh_output = True
        if not Path(source_path).is_file():
            return _finalize_packet(
                packet,
                blockers=["refresh_incomplete_output"],
                classification="blocked_refresh_failure",
                root=root,
                state_paths=state_paths,
                write_artifacts=write_artifacts,
            )

    source_load = _load_normalized_rows(Path(source_path))
    integrity["source_normalization"] = "passed" if source_load.valid else "failed"
    integrity["duplicate_timestamp_check"] = (
        "failed" if source_load.duplicate_timestamp_rows else "passed"
    )
    integrity["timestamp_order_check"] = (
        "failed" if source_load.out_of_order_rows else "passed"
    )
    integrity["fixture_source_check"] = (
        "failed" if source_load.fixture_source_detected else "passed"
    )
    if source_load.errors:
        blockers.extend(source_load.errors)
    if source_load.duplicate_timestamp_rows:
        blockers.append("duplicate_or_rewritten_oos_bar")
    if source_load.out_of_order_rows:
        blockers.append("out_of_order_oos_bars")
    if source_load.fixture_source_detected:
        blockers.append("fixture_or_synthetic_oos_history")
    if delta_is_refresh_output and any(row.timestamp <= cutoff for row in source_load.rows):
        blockers.append("attempted_pre_cutoff_leakage")
        integrity["pre_cutoff_leakage_check"] = "failed"
    else:
        integrity["pre_cutoff_leakage_check"] = "passed"
    if blockers:
        return _finalize_packet(
            packet,
            blockers=blockers,
            classification="blocked_integrity",
            root=root,
            state_paths=state_paths,
            write_artifacts=write_artifacts,
        )

    accrued_load = _load_normalized_rows(state_paths["accrued_oos"])
    if state_paths["accrued_oos"].exists():
        if accrued_load.errors:
            blockers.extend(accrued_load.errors)
        if accrued_load.duplicate_timestamp_rows:
            blockers.append("duplicate_accrued_oos_bar")
        if accrued_load.out_of_order_rows:
            blockers.append("out_of_order_accrued_oos_bars")
        if any(row.timestamp <= cutoff for row in accrued_load.rows):
            blockers.append("attempted_pre_cutoff_leakage")
    integrity["accrued_state"] = "passed" if not blockers else "failed"
    if blockers:
        return _finalize_packet(
            packet,
            blockers=blockers,
            classification="blocked_integrity",
            root=root,
            state_paths=state_paths,
            write_artifacts=write_artifacts,
        )

    incoming_oos = tuple(row for row in source_load.rows if row.timestamp > cutoff)
    merged_rows, merge_errors = _merge_accrued_rows(accrued_load.rows, incoming_oos)
    if merge_errors:
        integrity["accrual_merge"] = "failed"
        return _finalize_packet(
            packet,
            blockers=merge_errors,
            classification="blocked_integrity",
            root=root,
            state_paths=state_paths,
            write_artifacts=write_artifacts,
        )
    integrity["accrual_merge"] = "passed"
    if write_artifacts:
        root.mkdir(parents=True, exist_ok=True)
        _write_rows_csv(state_paths["accrued_oos"], merged_rows)

    ada_rows = tuple(row for row in merged_rows if row.symbol == "ADAUSD")
    packet["latest_normalized_bar"] = _latest_bar_payload(merged_rows)
    packet["oos_row_count"] = len(ada_rows)
    packet["oos_normalized_row_count"] = len(merged_rows)
    packet["oos_range"] = _date_range(ada_rows)
    packet["rows_still_required"] = max(0, required_rows - len(ada_rows))
    packet["integrity_checks"] = integrity

    if len(ada_rows) < required_rows:
        return _finalize_packet(
            packet,
            blockers=["awaiting_fresh_oos_rows"],
            classification="awaiting_fresh_oos",
            root=root,
            state_paths=state_paths,
            write_artifacts=write_artifacts,
        )

    gate_path = state_paths["accrued_oos"]
    if not write_artifacts:
        _write_rows_csv(gate_path, merged_rows)
    evidence_packet = build_crypto_repair_fresh_oos_validation_packet(
        gate_path,
        as_of=evaluated_at,
        discovery_cutoff=cutoff,
        repair_candidate=DEFAULT_FRESH_OOS_REPAIR_CANDIDATE,
        oos_data_source="frozen_candidate_forward_oos_accrual",
        assumptions=checked_assumptions,
        required_min_oos_rows=required_rows,
    )
    packet["evidence_gate"] = evidence_packet
    if evidence_packet["classification"] == "fresh_oos_validated":
        return _finalize_packet(
            packet,
            blockers=[],
            classification="eligible_for_no_submit_paper_planning",
            root=root,
            state_paths=state_paths,
            write_artifacts=write_artifacts,
        )
    return _finalize_packet(
        packet,
        blockers=_string_sequence(evidence_packet.get("rejection_reasons")),
        classification="fresh_oos_rejected",
        root=root,
        state_paths=state_paths,
        write_artifacts=write_artifacts,
    )


def build_frozen_candidate_descriptor(
    *,
    discovery_cutoff: datetime | str = DEFAULT_REPAIR_DISCOVERY_CUTOFF,
    candidate_id: str = DEFAULT_FRESH_OOS_REPAIR_CANDIDATE,
    timeframe: str = CRYPTO_REPAIR_FORWARD_OOS_TIMEFRAME,
    assumptions: CryptoEvidenceAssumptions | None = None,
    required_min_oos_rows: int = CRYPTO_REPAIR_FORWARD_OOS_REQUIRED_MIN_ROWS,
    evaluation_policy_version: str = CRYPTO_REPAIR_FORWARD_OOS_EVALUATION_POLICY_VERSION,
    relevant_discovery_evidence_input_hash: str = "",
) -> dict[str, object]:
    """Return the fully specified, hashable frozen repair-candidate descriptor."""

    cutoff = _utc_datetime(discovery_cutoff, "discovery_cutoff")
    checked_assumptions = assumptions or CryptoEvidenceAssumptions()
    required_rows = _required_rows(required_min_oos_rows, checked_assumptions)
    candidate = {
        "candidate_id": _required_text(candidate_id, "candidate_id"),
        "symbol": "ADAUSD",
        "timeframe": _timeframe(timeframe),
        "strategy": {
            "strategy_id": "trend_momentum_24h_repair",
            "strategy_family": "trend_momentum",
            "parameters": {
                "lookback": 24,
                "fast_window": 0,
                "slow_window": 0,
                "volatility_threshold": "0",
            },
        },
        "discovery_cutoff": cutoff.isoformat(),
        "required_min_oos_rows": required_rows,
        "evaluation_policy_version": _required_text(
            evaluation_policy_version,
            "evaluation_policy_version",
        ),
        "assumptions": _assumptions_payload(checked_assumptions),
    }
    configuration_fingerprint = _stable_hash(candidate)
    descriptor = {
        "schema_version": CRYPTO_REPAIR_FORWARD_OOS_ACCRUAL_SCHEMA_VERSION,
        **candidate,
        "candidate_configuration_fingerprint": configuration_fingerprint,
        "relevant_discovery_evidence_input_hash": _required_hash(
            relevant_discovery_evidence_input_hash
        ),
    }
    descriptor["frozen_candidate_fingerprint"] = _stable_hash(descriptor)
    return descriptor


def render_crypto_repair_forward_oos_markdown(packet: Mapping[str, object]) -> str:
    """Render a concise, no-submit operator packet."""

    frozen = _mapping(packet.get("frozen_candidate"))
    oos_range = _mapping(packet.get("oos_range"))
    integrity = _mapping(packet.get("integrity_checks"))
    blockers = _string_sequence(packet.get("blocker_rejection_reasons"))
    return "\n".join(
        (
            "# Frozen candidate forward-OOS accrual",
            "",
            f"- Classification: `{packet.get('classification', '')}`",
            f"- Frozen fingerprint: `{frozen.get('frozen_candidate_fingerprint', '')}`",
            f"- Discovery cutoff: `{packet.get('discovery_cutoff', '')}`",
            f"- Latest normalized bar: `{_bar_text(_mapping(packet.get('latest_normalized_bar')))}`",
            f"- ADA OOS rows/range: `{packet.get('oos_row_count', 0)}` / `{oos_range.get('start', '')}` to `{oos_range.get('end', '')}`",
            f"- Rows still required: `{packet.get('rows_still_required', 0)}`",
            f"- Repair eligibility: `{packet.get('repair_eligibility', '')}`",
            f"- Paper-planning eligibility: `{packet.get('paper_planning_eligibility', '')}`",
            f"- Integrity: `{_compact_mapping(integrity)}`",
            f"- Blockers/rejections: `{','.join(blockers)}`",
            f"- Market-data fetch/network: `{_bool(packet.get('market_data_fetch_occurred'))}` / `{_bool(packet.get('network_access_attempted'))}`",
            f"- Broker read/mutation/paper submit: `{_bool(packet.get('broker_read_occurred'))}` / `{_bool(packet.get('broker_mutation_occurred'))}` / `{_bool(packet.get('paper_submit_occurred'))}`",
            "",
        )
    )


def _base_packet(
    *,
    descriptor: Mapping[str, object],
    cutoff: datetime,
    evaluated_at: datetime,
    output_root: Path,
    discovery_path: Path,
    refresh_config: CryptoHistoryRefreshConfig | None,
) -> dict[str, object]:
    return {
        "schema_version": CRYPTO_REPAIR_FORWARD_OOS_ACCRUAL_SCHEMA_VERSION,
        "record_type": "crypto_repair_frozen_candidate_forward_oos_accrual_packet",
        "as_of": evaluated_at.isoformat(),
        "classification": "",
        "frozen_candidate": dict(descriptor),
        "discovery_cutoff": cutoff.isoformat(),
        "discovery_history_path": str(discovery_path),
        "refresh_requested": refresh_config is not None,
        "refresh": {"status": "not_requested"},
        "latest_normalized_bar": {},
        "oos_row_count": 0,
        "oos_normalized_row_count": 0,
        "oos_range": {"start": "", "end": ""},
        "rows_still_required": int(descriptor["required_min_oos_rows"]),
        "integrity_checks": {},
        "evidence_gate": {"runnable": False},
        "repair_eligibility": "not_eligible",
        "paper_planning_eligibility": "not_eligible",
        "blocker_rejection_reasons": [],
        "artifact_paths": {
            "output_root": str(output_root),
            "frozen_candidate": str(output_root / "frozen_candidate.json"),
            "accrued_oos": str(output_root / "accrued_oos_bars.csv"),
            "operating_packet_json": str(output_root / "operating_packet.json"),
            "operating_packet_markdown": str(output_root / "operating_packet.md"),
        },
        "labels": [
            "crypto_repair_forward_oos_accrual",
            "research_only",
            "paper_lab_only",
            "no_submit",
            "no_broker_read",
            "no_broker_mutation",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "profit_claim": "none",
        "market_data_fetch_occurred": False,
        "network_access_attempted": False,
        **{field: False for field in _FALSE_SAFETY_FIELDS},
    }


def _finalize_packet(
    packet: dict[str, object],
    *,
    blockers: Sequence[str],
    classification: str,
    root: Path,
    state_paths: Mapping[str, Path],
    write_artifacts: bool,
) -> dict[str, object]:
    evidence = _mapping(packet.get("evidence_gate"))
    evidence_runnable = bool(evidence) and evidence.get("runnable", True) is not False
    packet["classification"] = classification
    packet["blocker_rejection_reasons"] = list(dict.fromkeys(str(item) for item in blockers if item))
    eligible = classification == "eligible_for_no_submit_paper_planning"
    packet["repair_eligibility"] = (
        "eligible_for_no_submit_plan" if eligible else "not_eligible"
    )
    packet["paper_planning_eligibility"] = (
        "eligible_for_no_submit_plan" if eligible else "not_eligible"
    )
    if not evidence_runnable:
        packet["evidence_gate"] = {"runnable": False}
    refresh = _mapping(packet.get("refresh"))
    packet["market_data_fetch_occurred"] = bool(refresh.get("market_data_fetch_occurred", False))
    packet["network_access_attempted"] = bool(refresh.get("network_access_attempted", False))
    packet["runs_tracked"] = False
    if write_artifacts:
        root.mkdir(parents=True, exist_ok=True)
        _write_json(state_paths["operating_packet_json"], packet)
        state_paths["operating_packet_markdown"].write_text(
            render_crypto_repair_forward_oos_markdown(packet),
            encoding="utf-8",
            newline="\n",
        )
    return packet


def _integrity_checks(
    *,
    discovery_load: _RowsLoad,
    cutoff: datetime,
    refresh_config: CryptoHistoryRefreshConfig | None,
) -> dict[str, object]:
    return {
        "candidate_fingerprint": "not_checked",
        "discovery_period_hash": "not_checked",
        "discovery_normalization": "passed" if discovery_load.valid else "failed",
        "source_normalization": "not_checked",
        "duplicate_timestamp_check": "not_checked",
        "timestamp_order_check": "not_checked",
        "fixture_source_check": "not_checked",
        "pre_cutoff_leakage_check": "not_checked",
        "accrued_state": "not_checked",
        "accrual_merge": "not_checked",
        "discovery_rows_at_or_before_cutoff": sum(
            row.timestamp <= cutoff for row in discovery_load.rows
        ),
        "refresh_mode": "not_requested" if refresh_config is None else refresh_config.mode,
    }


def _state_paths(root: Path) -> dict[str, Path]:
    return {
        "frozen_candidate": root / "frozen_candidate.json",
        "accrued_oos": root / "accrued_oos_bars.csv",
        "operating_packet_json": root / "operating_packet.json",
        "operating_packet_markdown": root / "operating_packet.md",
    }


def _load_normalized_rows(path: Path) -> _RowsLoad:
    if not path.is_file():
        return _RowsLoad(path, (), ("input_history_missing",), 0, 0, False)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return _RowsLoad(path, (), ("input_history_unreadable",), 0, 0, False)
    reader = csv.DictReader(text.splitlines())
    fieldnames = tuple(reader.fieldnames or ())
    missing = tuple(column for column in _REQUIRED_CSV_COLUMNS if column not in fieldnames)
    if missing:
        return _RowsLoad(path, (), ("incomplete_normalized_output",), 0, 0, False)

    rows: list[_NormalizedRow] = []
    errors: list[str] = []
    seen: set[tuple[str, datetime]] = set()
    previous_by_symbol: dict[str, datetime] = {}
    duplicate_count = 0
    out_of_order_count = 0
    fixture_source_detected = False
    for raw in reader:
        if None in raw:
            errors.append("malformed_csv_row")
            break
        try:
            row = _normalized_row(raw)
        except _RowError as exc:
            errors.append(exc.reason)
            break
        if row.key() in seen:
            duplicate_count += 1
        previous = previous_by_symbol.get(row.symbol)
        if previous is not None and row.timestamp < previous:
            out_of_order_count += 1
        seen.add(row.key())
        previous_by_symbol[row.symbol] = row.timestamp
        if any(marker in row.source.lower() for marker in _FIXTURE_SOURCE_MARKERS):
            fixture_source_detected = True
        rows.append(row)
    return _RowsLoad(
        path=path,
        rows=tuple(sorted(rows, key=lambda row: row.key())),
        errors=tuple(dict.fromkeys(errors)),
        duplicate_timestamp_rows=duplicate_count,
        out_of_order_rows=out_of_order_count,
        fixture_source_detected=fixture_source_detected,
    )


class _RowError(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason


def _normalized_row(raw: Mapping[str | None, str | None]) -> _NormalizedRow:
    timestamp_text = str(raw.get("timestamp") or "").strip()
    try:
        timestamp = _utc_datetime(timestamp_text, "timestamp")
    except ValidationError as exc:
        raise _RowError("malformed_timestamp") from exc
    symbol = "".join(ch for ch in str(raw.get("symbol") or "").upper() if ch.isalnum())
    if symbol not in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS:
        raise _RowError("inconsistent_normalization")
    try:
        open_price = _positive_decimal(raw.get("open"))
        high = _positive_decimal(raw.get("high"))
        low = _positive_decimal(raw.get("low"))
        close = _positive_decimal(raw.get("close"))
    except _RowError:
        raise
    if low > min(open_price, close) or high < max(open_price, close):
        raise _RowError("inconsistent_normalization")
    return _NormalizedRow(
        timestamp=timestamp,
        symbol=symbol,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=str(raw.get("volume") or "").strip(),
        source=str(raw.get("source") or "").strip(),
    )


def _positive_decimal(value: object) -> Decimal:
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise _RowError("inconsistent_normalization") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise _RowError("inconsistent_normalization")
    return parsed


def _merge_accrued_rows(
    accrued_rows: Sequence[_NormalizedRow],
    incoming_rows: Sequence[_NormalizedRow],
) -> tuple[tuple[_NormalizedRow, ...], list[str]]:
    selected = {row.key(): row for row in accrued_rows}
    for row in incoming_rows:
        prior = selected.get(row.key())
        if prior is not None and prior.canonical() != row.canonical():
            return (), ["rewritten_accrued_oos_data"]
        selected[row.key()] = row
    return tuple(sorted(selected.values(), key=lambda row: row.key())), []


def _rows_hash(rows: Sequence[_NormalizedRow]) -> str:
    return _stable_hash([row.canonical() for row in sorted(rows, key=lambda row: row.key())])


def _stable_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _required_hash(value: str) -> str:
    if not value:
        return _stable_hash([])
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValidationError("relevant_discovery_evidence_input_hash must be a SHA-256 hex digest.")
    return value


def _required_rows(value: int, assumptions: CryptoEvidenceAssumptions) -> int:
    if type(value) is not int or value != CRYPTO_REPAIR_FORWARD_OOS_REQUIRED_MIN_ROWS:
        raise ValidationError("required_min_oos_rows must remain frozen at 26.")
    required_by_evidence = max(assumptions.min_bars_per_symbol, 26)
    if required_by_evidence != CRYPTO_REPAIR_FORWARD_OOS_REQUIRED_MIN_ROWS:
        raise ValidationError("assumptions must preserve the frozen 26-row OOS minimum.")
    return value


def _assumptions_payload(assumptions: CryptoEvidenceAssumptions) -> dict[str, object]:
    return {
        "initial_equity": _decimal_text(assumptions.initial_equity),
        "fee_bps": _decimal_text(assumptions.fee_bps),
        "slippage_bps": _decimal_text(assumptions.slippage_bps),
        "min_bars_per_symbol": assumptions.min_bars_per_symbol,
        "min_history_rows_per_symbol": assumptions.min_history_rows_per_symbol,
        "min_history_span_hours": assumptions.min_history_span_hours,
        "train_fraction_numerator": assumptions.train_fraction_numerator,
        "train_fraction_denominator": assumptions.train_fraction_denominator,
        "max_test_drawdown": _decimal_text(assumptions.max_test_drawdown),
        "min_test_excess_return_vs_buy_hold": _decimal_text(
            assumptions.min_test_excess_return_vs_buy_hold
        ),
        "min_test_total_return": _decimal_text(assumptions.min_test_total_return),
        "paper_max_notional": _decimal_text(assumptions.paper_max_notional),
        "max_paper_allocation_fraction": _decimal_text(
            assumptions.max_paper_allocation_fraction
        ),
        "candidate_symbols": list(assumptions.candidate_symbols),
    }


def _refresh_summary(packet: Mapping[str, object]) -> dict[str, object]:
    return {
        "status": str(packet.get("classification", "unknown")),
        "mode": str(packet.get("mode", "")),
        "output_path": str(packet.get("output_path", "")),
        "market_data_fetch_occurred": bool(packet.get("market_data_fetch_occurred", False)),
        "network_access_attempted": bool(packet.get("network_access_attempted", False)),
        "broker_read_occurred": False,
        "broker_mutation_occurred": False,
        "paper_submit_occurred": False,
        "credential_values_exposed": False,
    }


def _write_rows_csv(path: Path, rows: Sequence[_NormalizedRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("timestamp", "symbol", "open", "high", "low", "close", "volume", "source"),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(row.canonical() for row in rows)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_json_mapping(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def _date_range(rows: Sequence[_NormalizedRow]) -> dict[str, str]:
    if not rows:
        return {"start": "", "end": ""}
    return {"start": rows[0].timestamp.isoformat(), "end": rows[-1].timestamp.isoformat()}


def _latest_bar_payload(rows: Sequence[_NormalizedRow]) -> dict[str, str]:
    if not rows:
        return {}
    row = max(rows, key=lambda item: (item.timestamp, item.symbol))
    return {"timestamp": row.timestamp.isoformat(), "symbol": row.symbol, "close": _decimal_text(row.close)}


def _utc_datetime(value: datetime | str, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be an ISO timestamp.") from exc
    else:
        raise ValidationError(f"{field_name} must be an ISO timestamp.")
    if parsed.tzinfo is None:
        raise ValidationError(f"{field_name} must include timezone information.")
    return parsed.astimezone(UTC)


def _timeframe(value: str) -> str:
    if value != CRYPTO_REPAIR_FORWARD_OOS_TIMEFRAME:
        raise ValidationError("timeframe must remain frozen at 1Hour.")
    return value


def _required_text(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be non-empty text.")
    return value.strip()


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item))
    return () if value in (None, "") else (str(value),)


def _bool(value: object) -> str:
    return "true" if value is True else "false"


def _bar_text(bar: Mapping[str, object]) -> str:
    if not bar:
        return ""
    return ":".join(str(bar.get(name, "")) for name in ("timestamp", "symbol", "close"))


def _compact_mapping(value: Mapping[str, object]) -> str:
    return ",".join(f"{key}={item}" for key, item in sorted(value.items()))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Accrue frozen ADA repair forward-OOS evidence without submitting orders."
    )
    parser.add_argument("--output-root", default=str(CRYPTO_REPAIR_FORWARD_OOS_DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--discovery-history-path", default=str(CRYPTO_REPAIR_FORWARD_OOS_DEFAULT_HISTORY_PATH))
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--refresh-mode", choices=("none", "dry_run", "offline_fixture", "market_data_fetch"), default="none")
    parser.add_argument("--refresh-output-path", default=str(CRYPTO_HISTORY_REFRESH_DEFAULT_OUTPUT_PATH))
    parser.add_argument("--refresh-packet-path", default="")
    parser.add_argument("--refresh-raw-response-path", default="")
    parser.add_argument("--refresh-hours", type=int, default=240)
    parser.add_argument("--refresh-start", default=None)
    parser.add_argument("--refresh-end", default=None)
    parser.add_argument("--market-data-fetch-authorized", action="store_true")
    parser.add_argument("--allow-network", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    refresh_config = None
    if args.refresh_mode != "none":
        refresh_config = CryptoHistoryRefreshConfig(
            mode=args.refresh_mode,
            output_path=args.refresh_output_path,
            packet_path=args.refresh_packet_path or None,
            raw_response_path=args.refresh_raw_response_path or None,
            as_of=args.as_of,
            start=args.refresh_start,
            end=args.refresh_end,
            hours=args.refresh_hours,
            timeframe=CRYPTO_REPAIR_FORWARD_OOS_TIMEFRAME,
            market_data_fetch_authorized=args.market_data_fetch_authorized,
            allow_network=args.allow_network,
        )
    packet = run_crypto_repair_forward_oos_accrual(
        output_root=args.output_root,
        discovery_history_path=args.discovery_history_path,
        refresh_config=refresh_config,
        as_of=args.as_of,
    )
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
