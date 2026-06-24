"""Preview-only SPY intraday SMA posture artifacts.

This module is local-file only. It validates SPY 15-minute bars against the
deterministic regular-session calendar and emits a supervised review artifact,
not an order, intent, execution plan, or broker-facing instruction.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.research.intraday_trend_probe import (
    IntradayBar,
    LocalIntradayBarsCsvResult,
    load_local_intraday_bars_csv,
    validate_regular_session_intraday_bars,
)

__all__ = [
    "INTRADAY_PREVIEW_LABELS",
    "INTRADAY_PREVIEW_STRATEGY",
    "IntradayPreviewConfig",
    "build_intraday_preview_from_csv",
    "render_intraday_preview_summary_markdown",
    "write_intraday_preview_artifacts",
]


INTRADAY_PREVIEW_STRATEGY = "intraday_sma_8_32_preview_only"
INTRADAY_PREVIEW_LABELS = (
    "research_only",
    "signal_evaluation_only",
    "preview_only",
    "not_live_authorized",
    "no_broker_access",
    "no_paper_submit",
    "profit_claim=none",
    "source_calendar_validated",
)

_RECORD_TYPE = "spy_intraday_preview"
_MANIFEST_RECORD_TYPE = "spy_intraday_preview_manifest"
_SCHEMA_VERSION = "1"
_SYMBOL = "SPY"
_TIMEFRAME_MINUTES = 15
_TIMEFRAME = "15m"
_FAST_WINDOW = 8
_SLOW_WINDOW = 32
_POSTURE_INSUFFICIENT = "insufficient_history"
_POSTURE_RISK_ON = "risk_on"
_POSTURE_RISK_OFF = "risk_off"
_DECISION_INSUFFICIENT = "insufficient_history"
_DECISION_CALENDAR_BLOCKED = "blocked/calendar_validation_failed"
_DECISION_DATA_BLOCKED = "blocked/intraday_data_unavailable"
_DECISION_RISK_ON = "risk_on_preview_only"
_DECISION_RISK_OFF = "risk_off_preview_only"
_BLOCKER_NONE = "none"
_BLOCKER_INSUFFICIENT = "insufficient_history"
_BLOCKER_CALENDAR = "calendar_validation_failed"
_BLOCKER_DATA = "intraday_data_unavailable"
_BLOCKER_STALE = "stale_intraday_data"
_CALENDAR_PASSED = "passed"
_CALENDAR_FAILED = "failed"
_CALENDAR_NOT_RUN_MISSING_DATA = "not_run_missing_data"
_DATA_AVAILABLE = "available"
_DATA_MISSING = "missing"
_DATA_STALE = "stale"
_HASH_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class IntradayPreviewConfig:
    """Explicit local inputs for one SPY intraday preview artifact."""

    run_id: str
    intraday_bars_csv: Path | str
    data_source_kind: str = "local_intraday_csv"
    source_timeframe_minutes: int = _TIMEFRAME_MINUTES
    expected_accepted_session_date: date | str | None = None

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
            _preview_timeframe_minutes(self.source_timeframe_minutes),
        )
        object.__setattr__(
            self,
            "expected_accepted_session_date",
            _optional_date(
                self.expected_accepted_session_date,
                "expected_accepted_session_date",
            ),
        )


def build_intraday_preview_from_csv(config: IntradayPreviewConfig) -> dict[str, object]:
    """Build one deterministic preview state from local SPY 15-minute bars."""

    checked_config = _config(config)
    source_path = checked_config.intraday_bars_csv
    if not source_path.is_file():
        return _preview_state(
            checked_config,
            calendar_validation_status=_CALENDAR_NOT_RUN_MISSING_DATA,
            data_availability_status=_DATA_MISSING,
            preview_decision=_DECISION_DATA_BLOCKED,
            blocker_status=_BLOCKER_DATA,
            next_operator_action=(
                "provide_calendar_valid_spy_15m_csv_or_authorize_read_only_refresh"
            ),
            load_error="intraday_bars_csv does not exist",
        )

    try:
        csv_result = load_local_intraday_bars_csv(
            source_path,
            symbol=_SYMBOL,
            source_timeframe_minutes=checked_config.source_timeframe_minutes,
        )
    except ValidationError as exc:
        return _preview_state(
            checked_config,
            calendar_validation_status=_CALENDAR_NOT_RUN_MISSING_DATA,
            data_availability_status=_DATA_MISSING,
            preview_decision=_DECISION_DATA_BLOCKED,
            blocker_status=_BLOCKER_DATA,
            next_operator_action=(
                "provide_calendar_valid_spy_15m_csv_or_authorize_read_only_refresh"
            ),
            load_error=str(exc),
        )

    if not csv_result.bars:
        return _preview_state(
            checked_config,
            csv_result=csv_result,
            calendar_validation_status=_CALENDAR_NOT_RUN_MISSING_DATA,
            data_availability_status=_DATA_MISSING,
            preview_decision=_DECISION_DATA_BLOCKED,
            blocker_status=_BLOCKER_DATA,
            next_operator_action=(
                "provide_calendar_valid_spy_15m_csv_or_authorize_read_only_refresh"
            ),
        )

    calendar_validation = validate_regular_session_intraday_bars(
        csv_result.bars,
        source_timeframe_minutes=checked_config.source_timeframe_minutes,
    )
    calendar_report = calendar_validation.to_report()
    accepted_bars = calendar_validation.accepted_bars
    accepted_session_date = _latest_accepted_session_date(calendar_report)
    calendar_failed = bool(calendar_validation.rejected_sessions) or not accepted_bars
    if calendar_failed:
        return _preview_state(
            checked_config,
            csv_result=csv_result,
            calendar_report=calendar_report,
            accepted_bars=accepted_bars,
            calendar_validation_status=_CALENDAR_FAILED,
            data_availability_status=(
                _DATA_AVAILABLE if accepted_bars else _DATA_MISSING
            ),
            preview_decision=_DECISION_CALENDAR_BLOCKED,
            blocker_status=_BLOCKER_CALENDAR,
            next_operator_action="repair_or_replace_calendar_valid_intraday_csv",
            bars_used=0,
        )

    signal = _latest_signal(accepted_bars)
    if _is_stale(checked_config, accepted_session_date):
        return _preview_state(
            checked_config,
            csv_result=csv_result,
            calendar_report=calendar_report,
            accepted_bars=accepted_bars,
            calendar_validation_status=_CALENDAR_PASSED,
            data_availability_status=_DATA_STALE,
            signal=signal,
            preview_decision=_DECISION_DATA_BLOCKED,
            blocker_status=_BLOCKER_STALE,
            next_operator_action=(
                "provide_calendar_valid_spy_15m_csv_for_expected_session"
            ),
        )

    if signal["posture"] == _POSTURE_INSUFFICIENT:
        return _preview_state(
            checked_config,
            csv_result=csv_result,
            calendar_report=calendar_report,
            accepted_bars=accepted_bars,
            calendar_validation_status=_CALENDAR_PASSED,
            data_availability_status=_DATA_AVAILABLE,
            signal=signal,
            preview_decision=_DECISION_INSUFFICIENT,
            blocker_status=_BLOCKER_INSUFFICIENT,
            next_operator_action="provide_more_calendar_valid_intraday_bars",
        )

    return _preview_state(
        checked_config,
        csv_result=csv_result,
        calendar_report=calendar_report,
        accepted_bars=accepted_bars,
        calendar_validation_status=_CALENDAR_PASSED,
        data_availability_status=_DATA_AVAILABLE,
        signal=signal,
        preview_decision=(
            _DECISION_RISK_ON
            if signal["posture"] == _POSTURE_RISK_ON
            else _DECISION_RISK_OFF
        ),
        blocker_status=_BLOCKER_NONE,
        next_operator_action="review_preview_artifacts_no_broker_action_authorized",
    )


def write_intraday_preview_artifacts(
    preview_state: Mapping[str, object],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write deterministic ignored run artifacts for one preview state."""

    state = _mapping(preview_state, "preview_state")
    root = _output_dir(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    latest_path = root / "latest_intraday_preview.json"
    _write_json(latest_path, state)

    record_path = root / "intraday_preview_record.jsonl"
    record_path.write_text(
        json.dumps(_json_safe(state), sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    summary_path = root / "intraday_preview_summary.md"
    summary_path.write_text(
        render_intraday_preview_summary_markdown(state),
        encoding="utf-8",
        newline="\n",
    )

    manifest_path = root / "intraday_preview_manifest.json"
    manifest = _manifest(
        state,
        artifact_paths=(summary_path, record_path, latest_path),
    )
    _write_json(manifest_path, manifest)

    return {
        "summary": summary_path,
        "record": record_path,
        "manifest": manifest_path,
        "latest": latest_path,
    }


def render_intraday_preview_summary_markdown(
    preview_state: Mapping[str, object],
) -> str:
    """Render a compact Markdown summary for supervised operator review."""

    state = _mapping(preview_state, "preview_state")
    lines = [
        "# SPY Intraday Preview",
        "",
        f"- Run ID: {state.get('run_id', '')}",
        f"- Classification: {state.get('classification_recommendation', '')}",
        f"- Symbol: {state.get('symbol', '')}",
        f"- Timeframe: {state.get('timeframe', '')}",
        f"- Strategy: {state.get('strategy', '')}",
        f"- Data source kind: {state.get('data_source_kind', '')}",
        f"- Source path: {state.get('source_path', '')}",
        f"- Data as-of timestamp: {state.get('data_as_of_timestamp', '')}",
        f"- Calendar validation status: {state.get('calendar_validation_status', '')}",
        f"- Accepted session date: {state.get('accepted_session_date', '')}",
        f"- Bars used: {state.get('bars_used', 0)}",
        f"- SMA8: {state.get('SMA8', '')}",
        f"- SMA32: {state.get('SMA32', '')}",
        f"- Posture: {state.get('posture', '')}",
        f"- Prior posture: {state.get('prior_posture', '')}",
        f"- Transition: {state.get('transition', '')}",
        f"- Preview decision: {state.get('preview_decision', '')}",
        f"- Blocker status: {state.get('blocker_status', '')}",
        f"- Broker state mode: {state.get('broker_state_mode', '')}",
        f"- Broker access attempted: {_bool_text(state.get('broker_access_attempted'))}",
        f"- Broker mutation attempted: {_bool_text(state.get('broker_mutation_attempted'))}",
        f"- Paper submit attempted: {_bool_text(state.get('paper_submit_attempted'))}",
        f"- Live trading attempted: {_bool_text(state.get('live_trading_attempted'))}",
        f"- Paper submit authorized: {_bool_text(state.get('paper_submit_authorized'))}",
        f"- Profit claim: {state.get('profit_claim', '')}",
        f"- Next operator action: {state.get('next_operator_action', '')}",
        f"- Labels: {', '.join(_labels(state.get('labels')))}",
        "",
    ]
    return "\n".join(lines)


def _preview_state(
    config: IntradayPreviewConfig,
    *,
    csv_result: LocalIntradayBarsCsvResult | None = None,
    calendar_report: Mapping[str, object] | None = None,
    accepted_bars: tuple[IntradayBar, ...] = (),
    calendar_validation_status: str,
    data_availability_status: str,
    preview_decision: str,
    blocker_status: str,
    next_operator_action: str,
    signal: Mapping[str, object] | None = None,
    bars_used: int | None = None,
    load_error: str | None = None,
) -> dict[str, object]:
    checked_config = _config(config)
    checked_signal = dict(signal or {})
    checked_calendar_report = dict(calendar_report or {})
    accepted_session_date = _latest_accepted_session_date(checked_calendar_report)
    data_as_of_timestamp = (
        None if not accepted_bars else accepted_bars[-1].timestamp_text
    )
    used_bars = len(accepted_bars) if bars_used is None else bars_used
    classification = (
        "intraday_preview_only_ready_for_supervised_review"
        if blocker_status == _BLOCKER_NONE
        else "intraday_preview_only_blocked_or_incomplete"
    )
    state: dict[str, object] = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "run_id": checked_config.run_id,
        "classification_recommendation": classification,
        "symbol": _SYMBOL,
        "timeframe": _TIMEFRAME,
        "timeframe_minutes": checked_config.source_timeframe_minutes,
        "strategy": INTRADAY_PREVIEW_STRATEGY,
        "fast_window": _FAST_WINDOW,
        "slow_window": _SLOW_WINDOW,
        "data_source_kind": checked_config.data_source_kind,
        "source_path": str(checked_config.intraday_bars_csv),
        "source_input_sha256": _optional_sha256(checked_config.intraday_bars_csv),
        "data_as_of_timestamp": data_as_of_timestamp,
        "data_availability_status": data_availability_status,
        "calendar_validation_status": calendar_validation_status,
        "accepted_session_date": accepted_session_date,
        "expected_accepted_session_date": (
            None
            if checked_config.expected_accepted_session_date is None
            else checked_config.expected_accepted_session_date.isoformat()
        ),
        "bars_used": used_bars,
        "SMA8": checked_signal.get("SMA8"),
        "SMA32": checked_signal.get("SMA32"),
        "posture": checked_signal.get("posture"),
        "prior_posture": checked_signal.get("prior_posture"),
        "transition": checked_signal.get("transition"),
        "preview_decision": preview_decision,
        "blocker_status": blocker_status,
        "broker_state_mode": "not_observed_for_intraday",
        "broker_access_attempted": False,
        "broker_mutation_attempted": False,
        "paper_submit_attempted": False,
        "live_trading_attempted": False,
        "paper_submit_authorized": False,
        "paper_submit_authorization_status": "not_authorized",
        "live_authorized": False,
        "market_data_fetch_attempted": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "next_operator_action": next_operator_action,
        "labels": list(INTRADAY_PREVIEW_LABELS),
        "research_only": True,
        "signal_evaluation_only": True,
        "preview_only": True,
        "calendar_validation": checked_calendar_report,
        "source": _source_summary(csv_result, checked_calendar_report),
    }
    if load_error is not None:
        state["load_error"] = load_error
    return state


def _latest_signal(bars: tuple[IntradayBar, ...]) -> dict[str, object]:
    closes = tuple(_decimal_value(bar.close, "close") for bar in bars)
    latest_sma8 = _sma(closes, _FAST_WINDOW)
    latest_sma32 = _sma(closes, _SLOW_WINDOW)
    posture = _posture(latest_sma8, latest_sma32)

    prior_posture = None
    transition = None
    if len(closes) > 1:
        prior_sma8 = _sma(closes[:-1], _FAST_WINDOW)
        prior_sma32 = _sma(closes[:-1], _SLOW_WINDOW)
        prior_posture = _posture(prior_sma8, prior_sma32)
        if (
            prior_posture != _POSTURE_INSUFFICIENT
            and posture != _POSTURE_INSUFFICIENT
        ):
            transition = (
                "unchanged"
                if prior_posture == posture
                else f"{prior_posture}_to_{posture}"
            )

    return {
        "SMA8": _optional_decimal_text(latest_sma8),
        "SMA32": _optional_decimal_text(latest_sma32),
        "posture": posture,
        "prior_posture": prior_posture,
        "transition": transition,
    }


def _sma(closes: tuple[Decimal, ...], window: int) -> Decimal | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:], Decimal("0")) / Decimal(window)


def _posture(sma8: Decimal | None, sma32: Decimal | None) -> str:
    if sma8 is None or sma32 is None:
        return _POSTURE_INSUFFICIENT
    return _POSTURE_RISK_ON if sma8 > sma32 else _POSTURE_RISK_OFF


def _source_summary(
    csv_result: LocalIntradayBarsCsvResult | None,
    calendar_report: Mapping[str, object],
) -> dict[str, object]:
    if csv_result is None:
        return {
            "symbol": _SYMBOL,
            "source_timeframe": _TIMEFRAME,
            "source_timeframe_minutes": _TIMEFRAME_MINUTES,
            "bar_count": 0,
            "accepted_bar_count": 0,
            "rejected_bar_count": 0,
        }
    return {
        **csv_result.source_metadata(),
        "accepted_bar_count": calendar_report.get("accepted_bar_count", 0),
        "rejected_bar_count": calendar_report.get("rejected_bar_count", 0),
        "accepted_session_count": calendar_report.get("accepted_session_count", 0),
        "rejected_session_count": calendar_report.get("rejected_session_count", 0),
    }


def _manifest(
    state: Mapping[str, object],
    *,
    artifact_paths: tuple[Path, ...],
) -> dict[str, object]:
    return {
        "record_type": _MANIFEST_RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "run_id": state.get("run_id", ""),
        "symbol": state.get("symbol", ""),
        "timeframe": state.get("timeframe", ""),
        "strategy": state.get("strategy", ""),
        "data_source_kind": state.get("data_source_kind", ""),
        "source_path": state.get("source_path", ""),
        "source_input_sha256": state.get("source_input_sha256"),
        "data_as_of_timestamp": state.get("data_as_of_timestamp"),
        "accepted_session_date": state.get("accepted_session_date"),
        "calendar_validation_status": state.get("calendar_validation_status", ""),
        "preview_decision": state.get("preview_decision", ""),
        "blocker_status": state.get("blocker_status", ""),
        "labels": _labels(state.get("labels")),
        "broker_access_attempted": False,
        "broker_mutation_attempted": False,
        "paper_submit_attempted": False,
        "live_trading_attempted": False,
        "paper_submit_authorized": False,
        "market_data_fetch_attempted": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "artifact_hashes": [
            {"path": path.as_posix(), "sha256": _sha256_file(path)}
            for path in artifact_paths
        ],
    }


def _latest_accepted_session_date(calendar_report: Mapping[str, object]) -> str | None:
    sessions = calendar_report.get("accepted_sessions")
    if not isinstance(sessions, list) or not sessions:
        return None
    latest = sessions[-1]
    if not isinstance(latest, Mapping):
        return None
    value = latest.get("date")
    return value if type(value) is str else None


def _is_stale(config: IntradayPreviewConfig, accepted_session_date: str | None) -> bool:
    expected = config.expected_accepted_session_date
    return expected is not None and accepted_session_date != expected.isoformat()


def _config(value: object) -> IntradayPreviewConfig:
    if type(value) is not IntradayPreviewConfig:
        raise ValidationError("config must be an IntradayPreviewConfig.")
    return value


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _labels(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return list(INTRADAY_PREVIEW_LABELS)
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
    path = _path_value(value, "output_dir")
    if path.exists() and not path.is_dir():
        raise ValidationError("output_dir must be a directory path.")
    return path


def _preview_timeframe_minutes(value: object) -> int:
    parsed = _positive_int(value, "source_timeframe_minutes")
    if parsed != _TIMEFRAME_MINUTES:
        raise ValidationError("intraday preview supports only 15-minute bars.")
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


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _optional_date(value: object, field_name: str) -> date | None:
    if value is None:
        return None
    if type(value) is date:
        return value
    if type(value) is str:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be an ISO date.") from exc
    raise ValidationError(f"{field_name} must be an ISO date.")


def _decimal_value(value: object, field_name: str) -> Decimal:
    if type(value) is Decimal:
        decimal_value = value
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


def _optional_decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = format(value, "f")
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
        return _optional_decimal_text(value)
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _optional_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return _sha256_file(path)


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(_HASH_CHUNK_SIZE):
            hasher.update(chunk)
    return hasher.hexdigest()


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"
