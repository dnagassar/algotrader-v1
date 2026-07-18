"""Unattended evidence ledger for the authoritative adjusted-market-data lane.

The refresh manifest is intentionally a one-record latest-state artifact.  This
module preserves one compact receipt per live refresh attempt and derives a
rolling consecutive-session readiness report without broker or network access.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.exchange_session import NyseExchangeSessionCalendar

__all__ = [
    "build_adjusted_market_data_soak_receipt",
    "build_adjusted_market_data_soak_report",
    "record_adjusted_market_data_soak",
]

_RECEIPT_RECORD_TYPE = "adjusted_market_data_soak_receipt"
_REPORT_RECORD_TYPE = "adjusted_market_data_soak_report"
_MILESTONE = "v1.79"
_ACCEPTED_REFRESH_STATE = "accepted_adjusted_spy_data_refresh"
_LIVE_MODE = "live_market_data_fetch"
_MAX_REQUIRED_SESSIONS = 20


def record_adjusted_market_data_soak(
    refresh_payload: Mapping[str, object],
    *,
    ledger_path: Path | str,
    report_path: Path | str,
    required_sessions: int = 5,
    observed_at: datetime | None = None,
) -> dict[str, object]:
    """Append one attempt receipt atomically and regenerate the latest report."""
    ledger = _runtime_output_path(ledger_path, "ledger_path")
    report_output = _runtime_output_path(report_path, "report_path")
    required = _required_session_count(required_sessions)
    receipts = _load_receipts(ledger)
    receipts.append(
        build_adjusted_market_data_soak_receipt(
            refresh_payload,
            observed_at=observed_at,
        )
    )
    ledger_bytes = _jsonl_bytes(receipts)
    _write_bytes_atomic(ledger, ledger_bytes)

    report = build_adjusted_market_data_soak_report(
        receipts,
        required_sessions=required,
    )
    report["ledger_path"] = str(ledger)
    report["ledger_sha256"] = hashlib.sha256(ledger_bytes).hexdigest()
    report["report_path"] = str(report_output)
    _write_bytes_atomic(report_output, _json_bytes(report))
    return report


def build_adjusted_market_data_soak_receipt(
    refresh_payload: Mapping[str, object],
    *,
    observed_at: datetime | None = None,
) -> dict[str, object]:
    """Reduce one refresh manifest to a secret-free operational receipt."""
    if not isinstance(refresh_payload, Mapping):
        raise ValidationError("refresh_payload must be a mapping.")
    observed = _observed_at(observed_at)
    expected = _date_text(
        refresh_payload.get("expected_latest_bar_date"),
        "expected_latest_bar_date",
    )
    provider_latest = _optional_date_text(
        refresh_payload.get("latest_provider_bar_date"),
        "latest_provider_bar_date",
    )
    blockers = _qualification_blockers(
        refresh_payload,
        expected_session_date=expected,
        provider_latest_bar_date=provider_latest,
    )
    core = {
        "observed_at_utc": observed,
        "expected_session_date": expected,
        "provider_latest_bar_date": provider_latest,
        "refresh_state": str(refresh_payload.get("refresh_state", "")),
        "revision_outcome": str(refresh_payload.get("revision_outcome", "")),
        "canonical_csv_sha256": str(
            refresh_payload.get("canonical_csv_sha256", "")
        ),
        "source_sha256": str(refresh_payload.get("source_sha256", "")),
    }
    receipt_id = hashlib.sha256(_json_bytes(core, newline=False)).hexdigest()
    return {
        "milestone": _MILESTONE,
        "record_type": _RECEIPT_RECORD_TYPE,
        "schema_version": 1,
        "receipt_id": receipt_id,
        **core,
        "qualifying": not blockers,
        "qualification_blockers": blockers,
        "http_outcome_category": str(
            refresh_payload.get("http_outcome_category", "")
        ),
        "canonical_changed": bool(refresh_payload.get("canonical_changed", False)),
        "network_access_attempted": bool(
            refresh_payload.get("network_access_attempted", False)
        ),
        "network_destination_allowlist_enforced": bool(
            refresh_payload.get("network_destination_allowlist_enforced", False)
        ),
        "market_data_token_value_printed": bool(
            refresh_payload.get("market_data_token_value_printed", False)
        ),
        "market_data_token_value_written": bool(
            refresh_payload.get("market_data_token_value_written", False)
        ),
        "broker_access_attempted": bool(
            refresh_payload.get("broker_access_attempted", False)
        ),
        "broker_mutation_performed": bool(
            refresh_payload.get("broker_mutation_performed", False)
        ),
        "paper_submit_performed": bool(
            refresh_payload.get("paper_submit_performed", False)
        ),
        "live_trading_performed": bool(
            refresh_payload.get("live_trading_performed", False)
        ),
        "refresh_blockers": _strings(refresh_payload.get("refresh_blockers")),
        "refresh_warnings": _strings(refresh_payload.get("refresh_warnings")),
        "profit_claim": "none",
    }


def build_adjusted_market_data_soak_report(
    receipts: Sequence[Mapping[str, object]],
    *,
    required_sessions: int = 5,
) -> dict[str, object]:
    """Evaluate a rolling streak of distinct successful expected sessions."""
    required = _required_session_count(required_sessions)
    if isinstance(receipts, (str, bytes)) or not isinstance(receipts, Sequence):
        raise ValidationError("receipts must be a sequence of mappings.")

    by_session: dict[date, list[Mapping[str, object]]] = {}
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            raise ValidationError("every soak receipt must be a mapping.")
        if receipt.get("record_type") != _RECEIPT_RECORD_TYPE:
            raise ValidationError("unexpected soak receipt record_type.")
        session = date.fromisoformat(
            _date_text(receipt.get("expected_session_date"), "expected_session_date")
        )
        by_session.setdefault(session, []).append(receipt)

    attempted_dates = sorted(by_session)
    qualifying_dates = sorted(
        session
        for session, attempts in by_session.items()
        if any(bool(attempt.get("qualifying", False)) for attempt in attempts)
    )
    failed_dates = sorted(set(attempted_dates) - set(qualifying_dates))
    latest_attempted = attempted_dates[-1] if attempted_dates else None
    current_streak = _current_qualifying_streak(
        qualifying_dates,
        latest_attempted=latest_attempted,
    )
    ready = len(current_streak) >= required
    latest_qualified = bool(
        latest_attempted is not None and latest_attempted in qualifying_dates
    )
    if ready:
        evidence_state = "accepted_unattended_market_data_soak"
        classification = "unattended_authoritative_market_data_proven"
    elif latest_attempted is not None and not latest_qualified:
        evidence_state = "blocked_latest_expected_session_not_accepted"
        classification = "operational_data_provenance_capability"
    else:
        evidence_state = "collecting_unattended_market_data_soak"
        classification = "operational_data_provenance_capability"

    next_expected: date | None = None
    if latest_attempted is not None and not latest_qualified:
        next_expected = latest_attempted
    elif current_streak:
        next_expected = _next_session(current_streak[-1])

    return {
        "milestone": _MILESTONE,
        "record_type": _REPORT_RECORD_TYPE,
        "schema_version": 1,
        "evidence_state": evidence_state,
        "classification": classification,
        "required_consecutive_expected_sessions": required,
        "attempt_count": len(receipts),
        "distinct_attempted_session_count": len(attempted_dates),
        "qualifying_session_count": len(qualifying_dates),
        "current_consecutive_qualifying_sessions": len(current_streak),
        "remaining_consecutive_sessions": max(required - len(current_streak), 0),
        "soak_started_session_date": _iso(attempted_dates[0] if attempted_dates else None),
        "latest_attempted_session_date": _iso(latest_attempted),
        "latest_session_qualified": latest_qualified,
        "qualifying_session_dates": [_iso(value) for value in qualifying_dates],
        "failed_session_dates": [_iso(value) for value in failed_dates],
        "current_streak_session_dates": [_iso(value) for value in current_streak],
        "next_expected_session_date": _iso(next_expected),
        "strategy_evidence_produced": False,
        "profit_claim": "none",
        "network_access_attempted": False,
        "broker_access_attempted": False,
        "broker_mutation_attempted": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_trading_performed": False,
        "operator_action_required": False,
    }


def _qualification_blockers(
    payload: Mapping[str, object],
    *,
    expected_session_date: str,
    provider_latest_bar_date: str,
) -> list[str]:
    blockers: list[str] = []
    calendar = NyseExchangeSessionCalendar()
    if calendar.session_for_date(date.fromisoformat(expected_session_date)) is None:
        blockers.append("expected_date_is_not_nyse_session")
    if str(payload.get("mode", "")) != _LIVE_MODE:
        blockers.append("refresh_mode_not_live_market_data_fetch")
    if not bool(payload.get("refresh_authorized", False)):
        blockers.append("market_data_refresh_not_authorized")
    if str(payload.get("refresh_state", "")) != _ACCEPTED_REFRESH_STATE:
        blockers.append("refresh_state_not_accepted")
    if provider_latest_bar_date != expected_session_date:
        blockers.append("provider_latest_date_mismatch")
    if str(payload.get("http_outcome_category", "")) != "success":
        blockers.append("http_outcome_not_success")
    if not bool(payload.get("network_access_attempted", False)):
        blockers.append("network_fetch_not_attempted")
    if not bool(payload.get("network_destination_allowlist_enforced", False)):
        blockers.append("network_destination_allowlist_not_enforced")
    if not bool(payload.get("revision_check_performed", False)):
        blockers.append("revision_check_not_performed")
    if not str(payload.get("revision_outcome", "")):
        blockers.append("revision_outcome_missing")
    if not str(payload.get("canonical_csv_sha256", "")):
        blockers.append("canonical_hash_missing")
    if not str(payload.get("source_sha256", "")):
        blockers.append("source_hash_missing")
    if _strings(payload.get("refresh_blockers")):
        blockers.append("refresh_blockers_present")
    for field in (
        "market_data_token_value_printed",
        "market_data_token_value_written",
        "broker_access_attempted",
        "broker_mutation_attempted",
        "broker_mutation_performed",
        "paper_submit_performed",
        "live_authorized",
        "live_trading_performed",
    ):
        if bool(payload.get(field, False)):
            blockers.append(f"unsafe_flag_true:{field}")
    return blockers


def _current_qualifying_streak(
    qualifying_dates: Sequence[date],
    *,
    latest_attempted: date | None,
) -> list[date]:
    streak: list[date] = []
    for session in qualifying_dates:
        if streak and session == _next_session(streak[-1]):
            streak.append(session)
        else:
            streak = [session]
    if latest_attempted is not None and (not streak or streak[-1] != latest_attempted):
        return []
    return streak


def _next_session(current: date) -> date:
    calendar = NyseExchangeSessionCalendar()
    for offset in range(1, 15):
        candidate = current + timedelta(days=offset)
        if calendar.session_for_date(candidate) is not None:
            return candidate
    raise ValidationError("next NYSE session not found within fourteen days.")


def _load_receipts(path: Path) -> list[Mapping[str, object]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ValidationError("soak ledger is unreadable.") from exc
    records: list[Mapping[str, object]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError("soak ledger contains invalid JSON.") from exc
        if not isinstance(record, Mapping):
            raise ValidationError("soak ledger records must be JSON objects.")
        records.append(record)
    return records


def _runtime_output_path(value: Path | str, field_name: str) -> Path:
    path = Path(value)
    parts = tuple(part.lower() for part in path.parts)
    if not str(path) or any(part in {"src", "tests", "scripts"} for part in parts):
        raise ValidationError(f"{field_name} must be a runtime output path.")
    if not path.is_absolute() and (not parts or parts[0] not in {".data", "runs"}):
        raise ValidationError(f"{field_name} must be under .data or runs.")
    return path


def _required_session_count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("required_sessions must be an integer.")
    if not 1 <= value <= _MAX_REQUIRED_SESSIONS:
        raise ValidationError("required_sessions must be from 1 to 20.")
    return value


def _observed_at(value: datetime | None) -> str:
    observed = datetime.now(UTC) if value is None else value
    if not isinstance(observed, datetime) or observed.tzinfo is None:
        raise ValidationError("observed_at must be a timezone-aware datetime.")
    return observed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _date_text(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a YYYY-MM-DD date.") from exc
    if parsed.isoformat() != text:
        raise ValidationError(f"{field_name} must be a YYYY-MM-DD date.")
    return text


def _optional_date_text(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    return _date_text(text, field_name) if text else ""


def _strings(value: object) -> list[str]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return []
    return [str(item) for item in value if str(item)]


def _iso(value: date | None) -> str:
    return value.isoformat() if value is not None else ""


def _jsonl_bytes(records: Sequence[Mapping[str, object]]) -> bytes:
    return b"".join(_json_bytes(record) for record in records)


def _json_bytes(value: Mapping[str, object], *, newline: bool = True) -> bytes:
    rendered = json.dumps(
        _json_safe(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return (rendered + ("\n" if newline else "")).encode("utf-8")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    try:
        temporary.write_bytes(data)
        temporary.replace(path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
