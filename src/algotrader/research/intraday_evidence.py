"""Deterministic SPY intraday SMA evidence gate.

This module evaluates the accepted fixed SMA8/32 preview signal across local
calendar-valid SPY 15-minute sessions. It is research-only: no broker state,
paper submission, execution planning, or network access is represented.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from algotrader.errors import ValidationError
from algotrader.research.intraday_trend_probe import (
    INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL,
    IntradayBar,
    LocalIntradayBarsCsvResult,
    load_local_intraday_bars_csv,
    validate_regular_session_intraday_bars,
)

__all__ = [
    "INTRADAY_EVIDENCE_LABELS",
    "INTRADAY_EVIDENCE_STRATEGY",
    "IntradayEvidenceConfig",
    "build_intraday_evidence_from_csv",
    "render_intraday_evidence_summary_markdown",
    "write_intraday_evidence_artifacts",
]


INTRADAY_EVIDENCE_STRATEGY = "intraday_sma_8_32_evidence_gate"
INTRADAY_EVIDENCE_LABELS = (
    "research_only",
    "signal_evaluation_only",
    "preview_only",
    "offline_only",
    "not_live_authorized",
    "no_broker_access",
    "no_paper_submit",
    "profit_claim=none",
    "source_calendar_validated",
)

_RECORD_TYPE = "spy_intraday_evidence"
_MANIFEST_RECORD_TYPE = "spy_intraday_evidence_manifest"
_SCHEMA_VERSION = "1"
_SYMBOL = "SPY"
_TIMEFRAME = "15m"
_TIMEFRAME_MINUTES = 15
_REGULAR_SESSION_TIMEZONE = "America/New_York"
_NEW_YORK = ZoneInfo(_REGULAR_SESSION_TIMEZONE)
_FAST_WINDOW = 8
_SLOW_WINDOW = 32
_POSTURE_INSUFFICIENT = "insufficient_history"
_POSTURE_RISK_ON = "risk_on"
_POSTURE_RISK_OFF = "risk_off"
_POSTURES = (_POSTURE_RISK_ON, _POSTURE_RISK_OFF)
_SOURCE_KIND_LOCAL = "local_intraday_csv"
_CALENDAR_REPORT_FILENAME = "calendar_validation_report.json"
_PROBE_MANIFEST_FILENAME = "intraday_probe_manifest.json"
_EXECUTION_NOT_DEFINED = "not_defined"
_EVALUATION_COMPLETE = "complete_signal_evidence"
_EVALUATION_INSUFFICIENT = "insufficient_history"
_RECOMMEND_INSUFFICIENT = "insufficient_evidence"
_RECOMMEND_RETAIN = "retain_research_candidate"
_RECOMMEND_REJECT = "reject_research_candidate"
_HASH_CHUNK_SIZE = 1024 * 1024
_ZERO = Decimal("0")
_ONE = Decimal("1")


@dataclass(frozen=True, slots=True)
class IntradayEvidenceConfig:
    """Explicit local input for one intraday evidence packet."""

    run_id: str
    intraday_bars_csv: Path | str
    data_source_kind: str = _SOURCE_KIND_LOCAL
    source_timeframe_minutes: int = _TIMEFRAME_MINUTES

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "intraday_bars_csv",
            _path_value(self.intraday_bars_csv, "intraday_bars_csv"),
        )
        object.__setattr__(
            self,
            "data_source_kind",
            _required_string(self.data_source_kind, "data_source_kind"),
        )
        object.__setattr__(
            self,
            "source_timeframe_minutes",
            _evidence_timeframe_minutes(self.source_timeframe_minutes),
        )


def build_intraday_evidence_from_csv(
    config: IntradayEvidenceConfig,
) -> dict[str, object]:
    """Build deterministic signal and forward-return diagnostics from local CSV."""

    checked_config = _config(config)
    source_path = checked_config.intraday_bars_csv
    source_sha256 = _sha256_file(source_path)
    csv_result = load_local_intraday_bars_csv(
        source_path,
        symbol=_SYMBOL,
        source_timeframe_minutes=checked_config.source_timeframe_minutes,
    )
    if not csv_result.input_sorted_by_timestamp:
        raise ValidationError("intraday_bars_csv must be sorted by timestamp.")

    calendar_validation = validate_regular_session_intraday_bars(
        csv_result.bars,
        source_timeframe_minutes=checked_config.source_timeframe_minutes,
    )
    calendar_report = calendar_validation.to_report()
    if calendar_validation.rejected_sessions:
        raise ValidationError("intraday_bars_csv contains invalid calendar sessions.")
    if not calendar_validation.accepted_bars:
        raise ValidationError("intraday_bars_csv has no complete accepted sessions.")
    if len(calendar_validation.accepted_bars) != len(csv_result.bars):
        raise ValidationError("intraday_bars_csv must contain only accepted sessions.")

    source_validation = _source_validation_summary(
        source_path=source_path,
        source_sha256=source_sha256,
        csv_result=csv_result,
        computed_calendar_report=calendar_report,
    )
    accepted_bars = calendar_validation.accepted_bars
    sessions = _session_summaries(calendar_report)
    signal_history = _signal_history(accepted_bars)
    data_integrity = _data_integrity_summary(
        source_path=source_path,
        source_sha256=source_sha256,
        csv_result=csv_result,
        calendar_report=calendar_report,
        signal_history=signal_history,
    )
    signal_behavior = _signal_behavior_summary(signal_history, sessions)
    directional = _directional_diagnostics(
        accepted_bars,
        signal_history,
        sessions,
    )
    usable_bars = _int_value(data_integrity["usable_bars_after_sma_warmup"])
    recommendation = _non_authoritative_recommendation(
        session_count=_int_value(data_integrity["session_count"]),
        usable_bars=usable_bars,
    )
    evaluation_status = (
        _EVALUATION_COMPLETE if usable_bars > 0 else _EVALUATION_INSUFFICIENT
    )

    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "run_id": checked_config.run_id,
        "evaluation_status": evaluation_status,
        "execution_semantics_status": _EXECUTION_NOT_DEFINED,
        "classification_recommendation": (
            "intraday_signal_evidence_only_ready_for_gpt_classification"
            if usable_bars > 0
            else "intraday_signal_evidence_only_insufficient_history"
        ),
        "non_authoritative_recommendation": recommendation,
        "symbol": _SYMBOL,
        "timeframe": _TIMEFRAME,
        "timeframe_minutes": checked_config.source_timeframe_minutes,
        "strategy": INTRADAY_EVIDENCE_STRATEGY,
        "fast_window": _FAST_WINDOW,
        "slow_window": _SLOW_WINDOW,
        "data_source_kind": checked_config.data_source_kind,
        "source_path": str(source_path),
        "source_sha256": source_sha256,
        "calendar_validation_status": "passed",
        "source_calendar_label": INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL,
        "source_validation": source_validation,
        "data_integrity": data_integrity,
        "signal_behavior": signal_behavior,
        "directional_diagnostics": directional,
        "hypothetical_performance": {
            "execution_semantics_status": _EXECUTION_NOT_DEFINED,
            "reason": (
                "No compatible intraday research execution semantics with explicit "
                "session-boundary behavior are defined for this evidence gate."
            ),
            "metrics": None,
        },
        "signal_semantics": {
            "rule": "SMA8 > SMA32 => risk_on; otherwise risk_off",
            "warmup": "insufficient_history until 32 closes are available",
            "no_lookahead": (
                "A signal at timestamp t uses only closes available through t."
            ),
            "forward_returns": (
                "Forward returns are research diagnostics only and are excluded "
                "when the requested future bars are unavailable in the same session."
            ),
        },
        "assumptions": [
            "Local CSV input has already been calendar validated by v1.82 artifacts.",
            "SPY 15-minute regular-session bars use bar-start timestamps.",
            "SMA8 and SMA32 use close prices through the as-of bar only.",
            "Forward returns are diagnostic labels, not trading instructions.",
        ],
        "exclusions": directional["exclusions"],
        "limitations": [
            "No profitability claim is made.",
            "No paper-trading, broker, execution, or live-use readiness is implied.",
            "Execution semantics are not defined for this evidence gate.",
            "The non-authoritative recommendation is conservative and sample-size based.",
        ],
        "paper_submit_authorized": False,
        "broker_access": False,
        "broker_mutation": False,
        "live_trading": False,
        "network_access": False,
        "market_data_fetch": False,
        "tiingo_fetch": False,
        "profit_claim": "none",
        "labels": list(INTRADAY_EVIDENCE_LABELS),
        "signal_history": signal_history,
    }


def write_intraday_evidence_artifacts(
    evidence: Mapping[str, object],
    output_root: str | Path,
) -> dict[str, Path]:
    """Write the deterministic evidence packet artifacts."""

    payload = _mapping(evidence, "evidence")
    root = _output_dir(output_root)
    root.mkdir(parents=True, exist_ok=True)

    json_path = root / "intraday_evidence.json"
    _write_json(json_path, payload)

    summary_path = root / "intraday_evidence_summary.md"
    summary_path.write_text(
        render_intraday_evidence_summary_markdown(payload),
        encoding="utf-8",
        newline="\n",
    )

    manifest_path = root / "intraday_evidence_manifest.json"
    manifest = _manifest(payload, artifact_paths=(summary_path, json_path))
    _write_json(manifest_path, manifest)

    return {
        "summary": summary_path,
        "evidence": json_path,
        "manifest": manifest_path,
    }


def render_intraday_evidence_summary_markdown(
    evidence: Mapping[str, object],
) -> str:
    """Render a compact deterministic evidence summary."""

    payload = _mapping(evidence, "evidence")
    integrity = _mapping(payload.get("data_integrity"), "data_integrity")
    behavior = _mapping(payload.get("signal_behavior"), "signal_behavior")
    directional = _mapping(
        payload.get("directional_diagnostics"),
        "directional_diagnostics",
    )
    next_bar = _mapping(directional.get("next_bar"), "next_bar")
    next_four = _mapping(directional.get("next_four_bar"), "next_four_bar")
    lines = [
        "# SPY Intraday Evidence",
        "",
        f"- Run ID: {payload.get('run_id', '')}",
        f"- Evaluation status: {payload.get('evaluation_status', '')}",
        f"- Execution semantics status: {payload.get('execution_semantics_status', '')}",
        f"- Non-authoritative recommendation: {payload.get('non_authoritative_recommendation', '')}",
        f"- Symbol: {payload.get('symbol', '')}",
        f"- Timeframe: {payload.get('timeframe', '')}",
        f"- Strategy: {payload.get('strategy', '')}",
        f"- Source path: {payload.get('source_path', '')}",
        f"- Source SHA-256: {payload.get('source_sha256', '')}",
        f"- Calendar validation status: {payload.get('calendar_validation_status', '')}",
        f"- Earliest timestamp: {integrity.get('earliest_timestamp', '')}",
        f"- Latest timestamp: {integrity.get('latest_timestamp', '')}",
        f"- Earliest accepted session: {integrity.get('earliest_accepted_session', '')}",
        f"- Latest accepted session: {integrity.get('latest_accepted_session', '')}",
        f"- Session count: {integrity.get('session_count', 0)}",
        f"- Total bars: {integrity.get('total_bars', 0)}",
        f"- Usable bars after SMA warmup: {integrity.get('usable_bars_after_sma_warmup', 0)}",
        f"- Risk-on bars: {behavior.get('risk_on_bar_count', 0)}",
        f"- Risk-off bars: {behavior.get('risk_off_bar_count', 0)}",
        f"- Transition count: {behavior.get('transition_count', 0)}",
        f"- Next-bar samples: {_posture_sample_line(next_bar)}",
        f"- Next-four-bar samples: {_posture_sample_line(next_four)}",
        f"- Paper submit authorized: {_bool_text(payload.get('paper_submit_authorized'))}",
        f"- Broker access: {_bool_text(payload.get('broker_access'))}",
        f"- Broker mutation: {_bool_text(payload.get('broker_mutation'))}",
        f"- Live trading: {_bool_text(payload.get('live_trading'))}",
        f"- Tiingo/network fetch: {_bool_text(payload.get('tiingo_fetch'))}/{_bool_text(payload.get('network_access'))}",
        f"- Labels: {', '.join(_labels(payload.get('labels')))}",
        "",
    ]
    return "\n".join(lines)


def _source_validation_summary(
    *,
    source_path: Path,
    source_sha256: str,
    csv_result: LocalIntradayBarsCsvResult,
    computed_calendar_report: Mapping[str, object],
) -> dict[str, object]:
    report_path = source_path.parent / _CALENDAR_REPORT_FILENAME
    manifest_path = source_path.parent / _PROBE_MANIFEST_FILENAME
    if not report_path.is_file() or not manifest_path.is_file():
        raise ValidationError(
            "source calendar-validation evidence is missing or incomplete."
        )

    report = _json_mapping(report_path, "calendar_validation_report")
    manifest = _json_mapping(manifest_path, "intraday_probe_manifest")
    report_hash = _sha256_file(report_path)
    manifest_hash = _sha256_file(manifest_path)

    if report.get("source_calendar_label") != INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL:
        raise ValidationError("source calendar-validation label is not validated.")
    if _int_value(report.get("accepted_bar_count")) != csv_result.observed_bar_count:
        raise ValidationError("calendar-validation accepted bar count mismatch.")
    if _int_value(report.get("accepted_session_count")) != _int_value(
        computed_calendar_report.get("accepted_session_count")
    ):
        raise ValidationError("calendar-validation accepted session count mismatch.")
    if _session_signature(report.get("accepted_sessions")) != _session_signature(
        computed_calendar_report.get("accepted_sessions")
    ):
        raise ValidationError("calendar-validation accepted sessions mismatch.")
    if not _manifest_hash_matches(manifest, source_path, source_sha256):
        raise ValidationError("source CSV hash is not recorded in the probe manifest.")
    if INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL not in _labels(
        manifest.get("labels")
    ):
        raise ValidationError("probe manifest does not label the source validated.")
    if _int_value(manifest.get("bar_count")) != csv_result.observed_bar_count:
        raise ValidationError("probe manifest bar count mismatch.")

    return {
        "status": "passed",
        "calendar_validation_status": "passed",
        "source_calendar_label": INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL,
        "calendar_report_path": str(report_path),
        "calendar_report_sha256": report_hash,
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_hash,
        "source_artifact_hash_match": True,
        "calendar_report_matches_input": True,
        "manifest_labels": _labels(manifest.get("labels")),
        "manifest_source_path": manifest.get("source_path"),
        "manifest_data_source_kind": manifest.get("data_source_kind"),
    }


def _data_integrity_summary(
    *,
    source_path: Path,
    source_sha256: str,
    csv_result: LocalIntradayBarsCsvResult,
    calendar_report: Mapping[str, object],
    signal_history: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    sessions = _session_summaries(calendar_report)
    bars_per_session = [_int_value(session.get("bar_count")) for session in sessions]
    usable_bars = sum(
        1 for row in signal_history if row.get("posture") in _POSTURES
    )
    accepted_dates = [str(session.get("date", "")) for session in sessions]
    return {
        "source_path": str(source_path),
        "source_sha256": source_sha256,
        "earliest_timestamp": None
        if not csv_result.bars
        else csv_result.bars[0].timestamp_text,
        "latest_timestamp": None
        if not csv_result.bars
        else csv_result.bars[-1].timestamp_text,
        "earliest_accepted_session": accepted_dates[0] if accepted_dates else None,
        "latest_accepted_session": accepted_dates[-1] if accepted_dates else None,
        "session_count": len(sessions),
        "total_bars": csv_result.observed_bar_count,
        "usable_bars_after_sma_warmup": usable_bars,
        "bars_per_session_distribution": _distribution(bars_per_session),
        "duplicate_count": 0,
        "invalid_session_count": _int_value(
            calendar_report.get("rejected_session_count")
        ),
        "calendar_validation_status": "passed",
        "source_calendar_label": INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL,
        "input_sorted_by_timestamp": csv_result.input_sorted_by_timestamp,
    }


def _signal_behavior_summary(
    signal_history: Sequence[Mapping[str, object]],
    sessions: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    usable = [row for row in signal_history if row.get("posture") in _POSTURES]
    usable_count = len(usable)
    risk_on_count = sum(1 for row in usable if row.get("posture") == _POSTURE_RISK_ON)
    risk_off_count = sum(
        1 for row in usable if row.get("posture") == _POSTURE_RISK_OFF
    )
    transitions = [
        row
        for row in usable
        if type(row.get("transition")) is str and row.get("transition") != "unchanged"
    ]
    transition_counts = {str(session.get("date", "")): 0 for session in sessions}
    for row in transitions:
        session = str(row.get("session", ""))
        transition_counts[session] = transition_counts.get(session, 0) + 1

    session_endings = _session_endings(signal_history, sessions)
    unchanged_session_count = sum(
        1
        for session in session_endings
        if session["ending_posture"] in _POSTURES
        and transition_counts.get(str(session["session"]), 0) == 0
    )
    return {
        "risk_on_bar_count": risk_on_count,
        "risk_on_proportion": _ratio_text(risk_on_count, usable_count),
        "risk_off_bar_count": risk_off_count,
        "risk_off_proportion": _ratio_text(risk_off_count, usable_count),
        "transition_count": len(transitions),
        "transitions_per_session": [
            {
                "session": session,
                "transition_count": transition_counts.get(session, 0),
            }
            for session in transition_counts
        ],
        "risk_on_dwell_length_distribution": _distribution(
            _dwell_lengths(signal_history, _POSTURE_RISK_ON)
        ),
        "risk_off_dwell_length_distribution": _distribution(
            _dwell_lengths(signal_history, _POSTURE_RISK_OFF)
        ),
        "sessions_ending_risk_on": _session_ending_payload(
            session_endings,
            _POSTURE_RISK_ON,
        ),
        "sessions_ending_risk_off": _session_ending_payload(
            session_endings,
            _POSTURE_RISK_OFF,
        ),
        "sessions_ending_insufficient_history": _session_ending_payload(
            session_endings,
            _POSTURE_INSUFFICIENT,
        ),
        "unchanged_session_count": unchanged_session_count,
        "session_endings": session_endings,
    }


def _directional_diagnostics(
    bars: Sequence[IntradayBar],
    signal_history: Sequence[Mapping[str, object]],
    sessions: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    session_dates = [str(session.get("date", "")) for session in sessions]
    horizon_payloads = {
        "next_bar": _forward_return_payload(
            bars,
            signal_history,
            horizon_bars=1,
            label="next_bar",
        ),
        "next_four_bar": _forward_return_payload(
            bars,
            signal_history,
            horizon_bars=4,
            label="next_four_bar",
        ),
    }
    split_index = len(session_dates) // 2
    first_half_sessions = session_dates[:split_index]
    second_half_sessions = session_dates[split_index:]
    chronological_halves = {
        "partition_rule": (
            "chronological complete sessions; first half uses floor(session_count/2), "
            "second half uses the remaining sessions"
        ),
        "first_half": _half_payload(
            "first_half",
            first_half_sessions,
            signal_history,
            horizon_payloads,
        ),
        "second_half": _half_payload(
            "second_half",
            second_half_sessions,
            signal_history,
            horizon_payloads,
        ),
    }
    exclusions = {
        label: payload["exclusions"] for label, payload in horizon_payloads.items()
    }
    return {
        **horizon_payloads,
        "session_level_aggregation": (
            "Per-session posture metrics are computed first, then summarized across "
            "sessions so one session cannot silently dominate the diagnostic."
        ),
        "chronological_first_half_vs_second_half": chronological_halves,
        "exclusions": exclusions,
    }


def _forward_return_payload(
    bars: Sequence[IntradayBar],
    signal_history: Sequence[Mapping[str, object]],
    *,
    horizon_bars: int,
    label: str,
) -> dict[str, object]:
    samples: list[dict[str, object]] = []
    exclusions = {
        "total": 0,
        "future_bar_exclusion_count": 0,
        "by_reason": {
            "insufficient_history": 0,
            "dataset_boundary": 0,
            "session_boundary": 0,
        },
        "by_posture": {
            _POSTURE_RISK_ON: 0,
            _POSTURE_RISK_OFF: 0,
            _POSTURE_INSUFFICIENT: 0,
        },
    }
    for index, row in enumerate(signal_history):
        posture = str(row.get("posture", ""))
        if posture not in _POSTURES:
            _increment_exclusion(exclusions, posture, "insufficient_history")
            continue
        future_index = index + horizon_bars
        if future_index >= len(bars):
            _increment_exclusion(exclusions, posture, "dataset_boundary")
            continue
        future_row = signal_history[future_index]
        if future_row.get("session") != row.get("session"):
            _increment_exclusion(exclusions, posture, "session_boundary")
            continue
        forward_return = (bars[future_index].close / bars[index].close) - _ONE
        samples.append(
            {
                "session": row.get("session"),
                "timestamp": row.get("timestamp"),
                "posture": posture,
                "forward_return": forward_return,
            }
        )

    return {
        "label": label,
        "horizon_bars": horizon_bars,
        "horizon_minutes": horizon_bars * _TIMEFRAME_MINUTES,
        "global_by_posture": _metrics_by_posture(samples),
        "session_level_by_posture": _session_level_metrics(samples),
        "sample_count_by_posture": {
            posture: sum(1 for sample in samples if sample["posture"] == posture)
            for posture in _POSTURES
        },
        "exclusions": exclusions,
        "samples": [_sample_json(sample) for sample in samples],
    }


def _half_payload(
    label: str,
    sessions: Sequence[str],
    signal_history: Sequence[Mapping[str, object]],
    horizon_payloads: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    session_set = set(sessions)
    usable_rows = [
        row
        for row in signal_history
        if row.get("session") in session_set and row.get("posture") in _POSTURES
    ]
    return {
        "label": label,
        "session_count": len(sessions),
        "sessions": list(sessions),
        "risk_on_bar_count": sum(
            1 for row in usable_rows if row.get("posture") == _POSTURE_RISK_ON
        ),
        "risk_off_bar_count": sum(
            1 for row in usable_rows if row.get("posture") == _POSTURE_RISK_OFF
        ),
        "forward_returns": {
            horizon_label: _metrics_by_posture(
                [
                    sample
                    for sample in _sample_mappings(payload.get("samples"))
                    if sample.get("session") in session_set
                ]
            )
            for horizon_label, payload in horizon_payloads.items()
        },
    }


def _signal_history(bars: Sequence[IntradayBar]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    closes: list[Decimal] = []
    previous_usable_posture: str | None = None
    session_bar_indices: dict[str, int] = {}
    for index, bar in enumerate(bars):
        closes.append(_decimal_value(bar.close, "close"))
        session = _session_date_text(bar.timestamp)
        session_index = session_bar_indices.get(session, 0)
        session_bar_indices[session] = session_index + 1
        sma8 = _sma(tuple(closes), _FAST_WINDOW)
        sma32 = _sma(tuple(closes), _SLOW_WINDOW)
        posture = _posture(sma8, sma32)
        transition: str | None = None
        if posture in _POSTURES:
            if previous_usable_posture is not None:
                transition = (
                    "unchanged"
                    if previous_usable_posture == posture
                    else f"{previous_usable_posture}_to_{posture}"
                )
            previous_usable_posture = posture

        rows.append(
            {
                "index": index,
                "timestamp": bar.timestamp_text,
                "session": session,
                "session_bar_index": session_index,
                "SMA8": _optional_decimal_text(sma8),
                "SMA32": _optional_decimal_text(sma32),
                "posture": posture,
                "transition": transition,
            }
        )
    return rows


def _session_endings(
    signal_history: Sequence[Mapping[str, object]],
    sessions: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    endings: list[dict[str, object]] = []
    for session in sessions:
        session_date = str(session.get("date", ""))
        rows = [row for row in signal_history if row.get("session") == session_date]
        posture = rows[-1].get("posture") if rows else _POSTURE_INSUFFICIENT
        endings.append(
            {
                "session": session_date,
                "ending_posture": posture,
                "usable_bar_count": sum(1 for row in rows if row.get("posture") in _POSTURES),
            }
        )
    return endings


def _session_ending_payload(
    endings: Sequence[Mapping[str, object]],
    posture: str,
) -> dict[str, object]:
    sessions = [
        str(ending.get("session", ""))
        for ending in endings
        if ending.get("ending_posture") == posture
    ]
    return {"count": len(sessions), "sessions": sessions}


def _dwell_lengths(
    signal_history: Sequence[Mapping[str, object]],
    posture: str,
) -> list[int]:
    lengths: list[int] = []
    current_posture: str | None = None
    current_length = 0
    for row in signal_history:
        row_posture = row.get("posture")
        if row_posture not in _POSTURES:
            continue
        if row_posture == current_posture:
            current_length += 1
            continue
        if current_posture == posture and current_length:
            lengths.append(current_length)
        current_posture = str(row_posture)
        current_length = 1
    if current_posture == posture and current_length:
        lengths.append(current_length)
    return lengths


def _metrics_by_posture(samples: Sequence[Mapping[str, object]]) -> dict[str, object]:
    return {
        posture: _return_metrics(
            [
                _decimal_value(sample.get("forward_return"), "forward_return")
                for sample in samples
                if sample.get("posture") == posture
            ]
        )
        for posture in _POSTURES
    }


def _session_level_metrics(
    samples: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    sessions = sorted({str(sample.get("session", "")) for sample in samples})
    per_session: list[dict[str, object]] = []
    by_posture: dict[str, list[dict[str, object]]] = {
        _POSTURE_RISK_ON: [],
        _POSTURE_RISK_OFF: [],
    }
    for session in sessions:
        for posture in _POSTURES:
            values = [
                _decimal_value(sample.get("forward_return"), "forward_return")
                for sample in samples
                if sample.get("session") == session and sample.get("posture") == posture
            ]
            metrics = _return_metrics(values)
            if metrics["sample_count"]:
                item = {"session": session, "posture": posture, **metrics}
                per_session.append(item)
                by_posture[posture].append(item)

    return {
        "aggregation_method": "equal_weight_by_session_after_within_session_metrics",
        "by_posture": {
            posture: _aggregate_session_metrics(items)
            for posture, items in by_posture.items()
        },
        "per_session": per_session,
    }


def _aggregate_session_metrics(
    session_metrics: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    means = [
        _decimal_value(item.get("mean"), "session mean")
        for item in session_metrics
        if item.get("mean") is not None
    ]
    positive_frequencies = [
        _decimal_value(item.get("positive_return_frequency"), "positive frequency")
        for item in session_metrics
        if item.get("positive_return_frequency") is not None
    ]
    return {
        "session_count": len(session_metrics),
        "mean_of_session_means": _optional_decimal_text(_mean(means)),
        "median_of_session_means": _optional_decimal_text(_median(means)),
        "mean_positive_return_frequency": _optional_decimal_text(
            _mean(positive_frequencies)
        ),
    }


def _return_metrics(values: Sequence[Decimal]) -> dict[str, object]:
    count = len(values)
    positive_count = sum(1 for value in values if value > _ZERO)
    return {
        "sample_count": count,
        "mean": _optional_decimal_text(_mean(values)),
        "median": _optional_decimal_text(_median(values)),
        "positive_return_count": positive_count,
        "positive_return_frequency": _ratio_text(positive_count, count),
    }


def _increment_exclusion(
    exclusions: dict[str, object],
    posture: str,
    reason: str,
) -> None:
    exclusions["total"] = _int_value(exclusions["total"]) + 1
    by_reason = _mutable_mapping(exclusions["by_reason"])
    by_reason[reason] = _int_value(by_reason.get(reason)) + 1
    by_posture = _mutable_mapping(exclusions["by_posture"])
    by_posture[posture] = _int_value(by_posture.get(posture)) + 1
    if reason in {"dataset_boundary", "session_boundary"}:
        exclusions["future_bar_exclusion_count"] = (
            _int_value(exclusions["future_bar_exclusion_count"]) + 1
        )


def _distribution(values: Sequence[int]) -> dict[str, object]:
    checked_values = [int(value) for value in values]
    decimals = [Decimal(value) for value in checked_values]
    return {
        "count": len(checked_values),
        "values": checked_values,
        "min": min(checked_values) if checked_values else None,
        "max": max(checked_values) if checked_values else None,
        "mean": _optional_decimal_text(_mean(decimals)),
        "median": _optional_decimal_text(_median(decimals)),
    }


def _non_authoritative_recommendation(*, session_count: int, usable_bars: int) -> str:
    if session_count < 60 or usable_bars < 500:
        return _RECOMMEND_INSUFFICIENT
    return _RECOMMEND_RETAIN


def _manifest(
    payload: Mapping[str, object],
    *,
    artifact_paths: tuple[Path, ...],
) -> dict[str, object]:
    return {
        "record_type": _MANIFEST_RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "run_id": payload.get("run_id", ""),
        "evaluation_status": payload.get("evaluation_status", ""),
        "execution_semantics_status": payload.get("execution_semantics_status", ""),
        "non_authoritative_recommendation": payload.get(
            "non_authoritative_recommendation",
            "",
        ),
        "symbol": payload.get("symbol", ""),
        "timeframe": payload.get("timeframe", ""),
        "strategy": payload.get("strategy", ""),
        "source_path": payload.get("source_path", ""),
        "source_sha256": payload.get("source_sha256", ""),
        "labels": _labels(payload.get("labels")),
        "paper_submit_authorized": False,
        "broker_access": False,
        "broker_mutation": False,
        "live_trading": False,
        "network_access": False,
        "market_data_fetch": False,
        "tiingo_fetch": False,
        "profit_claim": "none",
        "artifact_hashes": [
            {"path": path.as_posix(), "sha256": _sha256_file(path)}
            for path in artifact_paths
        ],
    }


def _session_summaries(
    calendar_report: Mapping[str, object],
) -> tuple[Mapping[str, object], ...]:
    sessions = calendar_report.get("accepted_sessions")
    if not isinstance(sessions, list | tuple):
        raise ValidationError("calendar report accepted_sessions must be a sequence.")
    return tuple(_mapping(session, "accepted_session") for session in sessions)


def _session_signature(value: object) -> tuple[tuple[object, ...], ...]:
    if not isinstance(value, list | tuple):
        return ()
    signature: list[tuple[object, ...]] = []
    for item in value:
        if not isinstance(item, Mapping):
            return ()
        signature.append(
            (
                item.get("date"),
                item.get("bar_count"),
                item.get("start_timestamp"),
                item.get("end_timestamp"),
                item.get("expected_bar_count"),
            )
        )
    return tuple(signature)


def _manifest_hash_matches(
    manifest: Mapping[str, object],
    source_path: Path,
    source_sha256: str,
) -> bool:
    hashes = manifest.get("artifact_hashes")
    if not isinstance(hashes, list | tuple):
        return False
    for item in hashes:
        if not isinstance(item, Mapping):
            continue
        if item.get("sha256") != source_sha256:
            continue
        path_text = item.get("path")
        if type(path_text) is str and _same_path(Path(path_text), source_path):
            return True
    return False


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.as_posix().replace("\\", "/") == right.as_posix().replace("\\", "/")


def _sample_json(sample: Mapping[str, object]) -> dict[str, object]:
    return {
        "session": sample.get("session"),
        "timestamp": sample.get("timestamp"),
        "posture": sample.get("posture"),
        "forward_return": _decimal_text(sample.get("forward_return")),
    }


def _sample_mappings(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _posture_sample_line(horizon_payload: Mapping[str, object]) -> str:
    by_posture = _mapping(horizon_payload.get("global_by_posture"), "by_posture")
    parts: list[str] = []
    for posture in _POSTURES:
        metrics = _mapping(by_posture.get(posture), posture)
        parts.append(f"{posture}={metrics.get('sample_count', 0)}")
    return ", ".join(parts)


def _session_date_text(timestamp: datetime) -> str:
    return timestamp.astimezone(_NEW_YORK).date().isoformat()


def _sma(closes: tuple[Decimal, ...], window: int) -> Decimal | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:], _ZERO) / Decimal(window)


def _posture(sma8: Decimal | None, sma32: Decimal | None) -> str:
    if sma8 is None or sma32 is None:
        return _POSTURE_INSUFFICIENT
    return _POSTURE_RISK_ON if sma8 > sma32 else _POSTURE_RISK_OFF


def _mean(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, _ZERO) / Decimal(len(values))


def _median(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    sorted_values = sorted(values)
    middle = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return sorted_values[middle]
    return (sorted_values[middle - 1] + sorted_values[middle]) / Decimal("2")


def _json_mapping(path: Path, field_name: str) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{field_name} must be valid JSON.") from exc
    return _mapping(payload, field_name)


def _config(value: object) -> IntradayEvidenceConfig:
    if type(value) is not IntradayEvidenceConfig:
        raise ValidationError("config must be an IntradayEvidenceConfig.")
    return value


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _mutable_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValidationError("expected mutable mapping.")
    return value


def _labels(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return list(INTRADAY_EVIDENCE_LABELS)
    return [item for item in value if type(item) is str]


def _path_value(value: object, field_name: str) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a path.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _output_dir(value: str | Path) -> Path:
    path = _path_value(value, "output_root")
    if path.exists() and not path.is_dir():
        raise ValidationError("output_root must be a directory path.")
    return path


def _evidence_timeframe_minutes(value: object) -> int:
    parsed = _positive_int(value, "source_timeframe_minutes")
    if parsed != _TIMEFRAME_MINUTES:
        raise ValidationError("intraday evidence supports only 15-minute bars.")
    return parsed


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is int and not isinstance(value, bool):
        parsed = value
    elif type(value) is str:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be a positive integer.") from exc
        if str(parsed) != value:
            raise ValidationError(f"{field_name} must be a positive integer.")
    else:
        raise ValidationError(f"{field_name} must be a positive integer.")
    if parsed <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return parsed


def _int_value(value: object) -> int:
    if type(value) is int and not isinstance(value, bool):
        return value
    if type(value) is str:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValidationError("value must be an integer.") from exc
        if str(parsed) != value:
            raise ValidationError("value must be an integer.")
        return parsed
    if value is None:
        return 0
    raise ValidationError("value must be an integer.")


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _decimal_value(value: object, field_name: str) -> Decimal:
    if type(value) is Decimal:
        decimal_value = value
    elif type(value) is int and not isinstance(value, bool):
        decimal_value = Decimal(value)
    elif type(value) is str:
        try:
            decimal_value = Decimal(value)
        except InvalidOperation as exc:
            raise ValidationError(f"{field_name} must be a Decimal.") from exc
    else:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not decimal_value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return decimal_value


def _ratio_text(numerator: int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    return _decimal_text(Decimal(numerator) / Decimal(denominator))


def _optional_decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _decimal_text(value)


def _decimal_text(value: object) -> str:
    decimal_value = _decimal_value(value, "decimal")
    text = format(decimal_value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _json_safe(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(_HASH_CHUNK_SIZE):
            hasher.update(chunk)
    return hasher.hexdigest()


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"
