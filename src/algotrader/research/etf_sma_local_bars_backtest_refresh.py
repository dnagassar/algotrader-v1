"""Offline SPY ETF/SMA local-bars backtest evidence refresh artifact."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_backtest_stats import (
    ETF_SMA_BACKTEST_STATS_LOOKAHEAD_POLICY,
    EtfSmaBacktestStatsConfig,
    build_etf_sma_backtest_stats,
)

__all__ = [
    "ETF_SMA_LOCAL_BARS_BACKTEST_REFRESH_LABELS",
    "EtfSmaLocalBarsBacktestRefreshConfig",
    "build_etf_sma_local_bars_backtest_refresh",
    "render_etf_sma_local_bars_backtest_refresh_json",
    "render_etf_sma_local_bars_backtest_refresh_text",
    "write_etf_sma_local_bars_backtest_refresh_jsonl",
]


ETF_SMA_LOCAL_BARS_BACKTEST_REFRESH_LABELS = (
    "research_only",
    "signal_evaluation_only",
    "paper_lab_only",
    "not_live_authorized",
)

_RECORD_TYPE = "etf_sma_local_bars_backtest_refresh"
_SCHEMA_VERSION = "1"
_COMMAND = "etf-sma-local-bars-backtest-refresh"
_SOURCE_RECORD_TYPE = "etf_sma_backtest_stats"
_SOURCE_COMMAND = "etf-sma-backtest-stats"
_STRATEGY = "spy_etf_sma_50_200_daily_long_only"
_SYMBOL = "SPY"
_SHORT_WINDOW = 50
_LONG_WINDOW = 200
_MINIMUM_USABLE_BARS_FOR_POST_SIGNAL_EVIDENCE = 201
_DEFAULT_STARTING_EQUITY = Decimal("25.00")
_ZERO_TEXT = "0"
_POSTURE_INSUFFICIENT = "insufficient_history"
_REFRESHED = "backtest_evidence_refreshed"
_BLOCKED_INSUFFICIENT_EXTENDED = "blocked_insufficient_extended_daily_bars"
_BLOCKED_INVALID_SOURCE = "blocked_invalid_source_backtest_log"
_BLOCKED_MALFORMED_CANDIDATE = "blocked_malformed_candidate_daily_bars_csv"
_BLOCKED_MISSING_CANDIDATE = "blocked_missing_candidate_daily_bars_csv"
_PERFORMANCE_EVALUATED = "post_signal_returns_evaluated"
_PERFORMANCE_INVALID_SOURCE = "invalid_source_backtest_log"
_PERFORMANCE_MALFORMED_CSV = "malformed_candidate_daily_bars_csv"
_PERFORMANCE_MISSING_CSV = "missing_candidate_daily_bars_csv"
_PERFORMANCE_INSUFFICIENT_HISTORY = "insufficient_history"
_PERFORMANCE_INSUFFICIENT_RETURNS = "insufficient_post_signal_returns"
_SOURCE_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "submit_authorized",
    "paper_submit_approved",
    "broker_mutation_authorized",
    "live_authorized",
    "credential_access_attempted",
    "network_access_attempted",
)


@dataclass(frozen=True, slots=True)
class EtfSmaLocalBarsBacktestRefreshConfig:
    """Explicit inputs for one offline local-bars backtest refresh artifact."""

    run_id: str
    source_backtest_log: Path | str
    candidate_daily_bars_csv: Path | str
    symbol: str = _SYMBOL

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", _spy_symbol(self.symbol))
        object.__setattr__(
            self,
            "source_backtest_log",
            _path_value(
                self.source_backtest_log,
                "source_backtest_log",
                required_suffix=".jsonl",
            ),
        )
        object.__setattr__(
            self,
            "candidate_daily_bars_csv",
            _path_value(
                self.candidate_daily_bars_csv,
                "candidate_daily_bars_csv",
                required_suffix=".csv",
            ),
        )


@dataclass(frozen=True, slots=True)
class _SourceBacktestValidation:
    record: dict[str, object] | None
    run_id: str | None
    starting_equity: Decimal
    blockers: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.blockers


def build_etf_sma_local_bars_backtest_refresh(
    config: EtfSmaLocalBarsBacktestRefreshConfig,
) -> dict[str, object]:
    """Build one deterministic M407 refresh artifact from local files only."""

    checked_config = _config(config)
    source_validation = _validate_source_backtest_log(checked_config.source_backtest_log)
    if not source_validation.valid:
        return _blocked_payload(
            checked_config,
            source_validation=source_validation,
            refresh_state=_BLOCKED_INVALID_SOURCE,
            backtest_state=_BLOCKED_INVALID_SOURCE,
            performance_evidence_state=_PERFORMANCE_INVALID_SOURCE,
            blockers=source_validation.blockers,
        )

    try:
        stats_payload = build_etf_sma_backtest_stats(
            EtfSmaBacktestStatsConfig(
                run_id=checked_config.run_id,
                symbol=checked_config.symbol,
                daily_bars_csv=checked_config.candidate_daily_bars_csv,
                starting_equity=source_validation.starting_equity,
            )
        )
    except ValidationError as exc:
        return _blocked_payload(
            checked_config,
            source_validation=source_validation,
            refresh_state=_BLOCKED_MALFORMED_CANDIDATE,
            backtest_state=_BLOCKED_MALFORMED_CANDIDATE,
            performance_evidence_state=_PERFORMANCE_MALFORMED_CSV,
            blockers=(
                _BLOCKED_MALFORMED_CANDIDATE,
                f"candidate_daily_bars_csv:{_blocker_text(str(exc))}",
            ),
            source_bar_count=_candidate_row_count(checked_config.candidate_daily_bars_csv),
            starting_equity=source_validation.starting_equity,
        )

    source_bar_count = _non_negative_int(
        stats_payload.get("source_bar_count"),
        "source_bar_count",
    )
    usable_bar_count = _non_negative_int(
        stats_payload.get("usable_bar_count"),
        "usable_bar_count",
    )
    evaluated_return_count = _non_negative_int(
        stats_payload.get("evaluated_return_count"),
        "evaluated_return_count",
    )
    backtest_state = _required_string(
        stats_payload.get("backtest_state"),
        "backtest_state",
    )
    stats_performance_state = _required_string(
        stats_payload.get("performance_evidence_state"),
        "performance_evidence_state",
    )

    if backtest_state == "blocked_missing_daily_bars_csv":
        return _payload_from_stats(
            checked_config,
            source_validation=source_validation,
            stats_payload=stats_payload,
            refresh_state=_BLOCKED_MISSING_CANDIDATE,
            performance_evidence_state=_PERFORMANCE_MISSING_CSV,
            blockers=(_BLOCKED_MISSING_CANDIDATE, "missing_candidate_daily_bars_csv"),
        )

    if usable_bar_count >= _MINIMUM_USABLE_BARS_FOR_POST_SIGNAL_EVIDENCE:
        if evaluated_return_count <= 0:
            return _payload_from_stats(
                checked_config,
                source_validation=source_validation,
                stats_payload=stats_payload,
                refresh_state=_BLOCKED_INSUFFICIENT_EXTENDED,
                performance_evidence_state=_PERFORMANCE_INSUFFICIENT_RETURNS,
                blockers=(
                    _BLOCKED_INSUFFICIENT_EXTENDED,
                    "missing_post_signal_return_evaluation",
                ),
            )
        return _payload_from_stats(
            checked_config,
            source_validation=source_validation,
            stats_payload=stats_payload,
            refresh_state=_REFRESHED,
            performance_evidence_state=_PERFORMANCE_EVALUATED,
            blockers=(),
        )

    performance_evidence_state = (
        _PERFORMANCE_INSUFFICIENT_HISTORY
        if usable_bar_count < _LONG_WINDOW
        else _PERFORMANCE_INSUFFICIENT_RETURNS
    )
    stats_blockers = _string_tuple(stats_payload.get("blockers"), "blockers")
    return _payload_from_stats(
        checked_config,
        source_validation=source_validation,
        stats_payload=stats_payload,
        refresh_state=_BLOCKED_INSUFFICIENT_EXTENDED,
        performance_evidence_state=performance_evidence_state,
        blockers=_dedupe(
            (
                _BLOCKED_INSUFFICIENT_EXTENDED,
                *stats_blockers,
                stats_performance_state,
            )
        ),
    )


def render_etf_sma_local_bars_backtest_refresh_json(
    payload: Mapping[str, object],
) -> str:
    """Return one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_local_bars_backtest_refresh_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing M407 summary."""

    return "\n".join(
        (
            "ETF/SMA local-bars backtest refresh",
            f"run_id: {payload.get('run_id', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"source_backtest_log: {payload.get('source_backtest_log', '')}",
            f"candidate_daily_bars_csv: {payload.get('candidate_daily_bars_csv', '')}",
            f"refresh_state: {payload.get('refresh_state', '')}",
            f"backtest_state: {payload.get('backtest_state', '')}",
            "performance_evidence_state: "
            f"{payload.get('performance_evidence_state', '')}",
            f"usable_bar_count: {payload.get('usable_bar_count', '')}",
            f"evaluated_return_count: {payload.get('evaluated_return_count', '')}",
            f"starting_equity: {payload.get('starting_equity', '')}",
            f"ending_equity: {payload.get('ending_equity', '')}",
            f"total_return: {payload.get('total_return', '')}",
            f"max_drawdown: {payload.get('max_drawdown', '')}",
            f"exposure_fraction: {payload.get('exposure_fraction', '')}",
            f"trade_count: {payload.get('trade_count', '')}",
            f"final_posture: {payload.get('final_posture', '')}",
            f"final_exposure: {payload.get('final_exposure', '')}",
            f"final_decision: {payload.get('final_decision', '')}",
            f"profit_claim: {payload.get('profit_claim', '')}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
        )
    )


def write_etf_sma_local_bars_backtest_refresh_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> None:
    """Write exactly one JSONL record, replacing any previous file."""

    path = _output_path(output_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_etf_sma_local_bars_backtest_refresh_json(payload))
        stream.write("\n")


def _validate_source_backtest_log(path: Path) -> _SourceBacktestValidation:
    blockers: list[str] = []
    record: dict[str, object] | None = None
    try:
        record = _last_jsonl_record(path)
    except ValidationError as exc:
        blockers.append(f"source_backtest_log:{_blocker_text(str(exc))}")
    if record is None:
        return _SourceBacktestValidation(
            record=None,
            run_id=None,
            starting_equity=_DEFAULT_STARTING_EQUITY,
            blockers=tuple(blockers or ("missing_source_backtest_record",)),
        )

    identity_valid = (
        record.get("record_type") == _SOURCE_RECORD_TYPE
        or record.get("command") == _SOURCE_COMMAND
    )
    if not identity_valid:
        blockers.append("source_backtest_log_record_type_invalid")
    if record.get("symbol") != _SYMBOL:
        blockers.append("source_backtest_log_symbol_invalid")
    if record.get("profit_claim") != "none":
        blockers.append("source_backtest_log_profit_claim_not_none")
    for field_name in _SOURCE_SAFETY_FALSE_FIELDS:
        if record.get(field_name) is not False:
            blockers.append(f"source_backtest_log_{field_name}_not_false")

    run_id = record.get("run_id")
    source_run_id = run_id if type(run_id) is str and run_id else None
    starting_equity = _source_starting_equity(record, blockers)
    return _SourceBacktestValidation(
        record=record,
        run_id=source_run_id,
        starting_equity=starting_equity,
        blockers=tuple(blockers),
    )


def _last_jsonl_record(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValidationError("source_backtest_log must reference an existing JSONL file.")

    last_record: dict[str, object] | None = None
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    candidate = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValidationError(
                        f"source_backtest_log line {line_number} must be JSON."
                    ) from exc
                if type(candidate) is not dict:
                    raise ValidationError(
                        f"source_backtest_log line {line_number} must be an object."
                    )
                last_record = dict(candidate)
    except OSError as exc:
        raise ValidationError("source_backtest_log could not be read.") from exc

    if last_record is None:
        raise ValidationError("source_backtest_log must contain a JSONL record.")
    return last_record


def _source_starting_equity(
    record: Mapping[str, object],
    blockers: list[str],
) -> Decimal:
    value = record.get("starting_equity", str(_DEFAULT_STARTING_EQUITY))
    try:
        return _positive_decimal(value, "source_backtest_log_starting_equity")
    except ValidationError:
        blockers.append("source_backtest_log_starting_equity_invalid")
        return _DEFAULT_STARTING_EQUITY


def _payload_from_stats(
    config: EtfSmaLocalBarsBacktestRefreshConfig,
    *,
    source_validation: _SourceBacktestValidation,
    stats_payload: Mapping[str, object],
    refresh_state: str,
    performance_evidence_state: str,
    blockers: tuple[str, ...],
) -> dict[str, object]:
    return _payload(
        config,
        source_validation=source_validation,
        source_bar_count=_non_negative_int(
            stats_payload.get("source_bar_count"),
            "source_bar_count",
        ),
        usable_bar_count=_non_negative_int(
            stats_payload.get("usable_bar_count"),
            "usable_bar_count",
        ),
        evaluated_return_count=_non_negative_int(
            stats_payload.get("evaluated_return_count"),
            "evaluated_return_count",
        ),
        short_window=_non_negative_int(stats_payload.get("short_window"), "short_window"),
        long_window=_non_negative_int(stats_payload.get("long_window"), "long_window"),
        refresh_state=refresh_state,
        backtest_state=_required_string(
            stats_payload.get("backtest_state"),
            "backtest_state",
        ),
        performance_evidence_state=performance_evidence_state,
        starting_equity=_required_string(
            stats_payload.get("starting_equity"),
            "starting_equity",
        ),
        ending_equity=_required_string(
            stats_payload.get("ending_equity"),
            "ending_equity",
        ),
        total_return=_required_string(stats_payload.get("total_return"), "total_return"),
        max_drawdown=_required_string(stats_payload.get("max_drawdown"), "max_drawdown"),
        exposure_fraction=_required_string(
            stats_payload.get("exposure_fraction"),
            "exposure_fraction",
        ),
        trade_count=_non_negative_int(stats_payload.get("trade_count"), "trade_count"),
        entry_count=_non_negative_int(stats_payload.get("entry_count"), "entry_count"),
        exit_count=_non_negative_int(stats_payload.get("exit_count"), "exit_count"),
        final_exposure=_non_negative_int(
            stats_payload.get("final_exposure"),
            "final_exposure",
        ),
        final_posture=_required_string(
            stats_payload.get("final_posture"),
            "final_posture",
        ),
        final_decision=_required_string(
            stats_payload.get("final_decision"),
            "final_decision",
        ),
        blockers=blockers,
        posture_history=_object_list(stats_payload.get("posture_history")),
        equity_curve=_object_list(stats_payload.get("equity_curve")),
        events=_object_list(stats_payload.get("events")),
    )


def _blocked_payload(
    config: EtfSmaLocalBarsBacktestRefreshConfig,
    *,
    source_validation: _SourceBacktestValidation,
    refresh_state: str,
    backtest_state: str,
    performance_evidence_state: str,
    blockers: tuple[str, ...],
    source_bar_count: int = 0,
    starting_equity: Decimal | None = None,
) -> dict[str, object]:
    equity = starting_equity or source_validation.starting_equity
    equity_text = _decimal_text(equity)
    return _payload(
        config,
        source_validation=source_validation,
        source_bar_count=source_bar_count,
        usable_bar_count=0,
        evaluated_return_count=0,
        short_window=_SHORT_WINDOW,
        long_window=_LONG_WINDOW,
        refresh_state=refresh_state,
        backtest_state=backtest_state,
        performance_evidence_state=performance_evidence_state,
        starting_equity=equity_text,
        ending_equity=equity_text,
        total_return=_ZERO_TEXT,
        max_drawdown=_ZERO_TEXT,
        exposure_fraction=_ZERO_TEXT,
        trade_count=0,
        entry_count=0,
        exit_count=0,
        final_exposure=0,
        final_posture=_POSTURE_INSUFFICIENT,
        final_decision=refresh_state,
        blockers=blockers,
        posture_history=[],
        equity_curve=[],
        events=[],
    )


def _payload(
    config: EtfSmaLocalBarsBacktestRefreshConfig,
    *,
    source_validation: _SourceBacktestValidation,
    source_bar_count: int,
    usable_bar_count: int,
    evaluated_return_count: int,
    short_window: int,
    long_window: int,
    refresh_state: str,
    backtest_state: str,
    performance_evidence_state: str,
    starting_equity: str,
    ending_equity: str,
    total_return: str,
    max_drawdown: str,
    exposure_fraction: str,
    trade_count: int,
    entry_count: int,
    exit_count: int,
    final_exposure: int,
    final_posture: str,
    final_decision: str,
    blockers: tuple[str, ...],
    posture_history: list[dict[str, object]],
    equity_curve: list[dict[str, object]],
    events: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "strategy": _STRATEGY,
        "labels": list(ETF_SMA_LOCAL_BARS_BACKTEST_REFRESH_LABELS),
        "source_backtest_log": str(config.source_backtest_log),
        "source_backtest_run_id": source_validation.run_id,
        "candidate_daily_bars_csv": str(config.candidate_daily_bars_csv),
        "source_bar_count": source_bar_count,
        "usable_bar_count": usable_bar_count,
        "minimum_usable_bars_for_post_signal_evidence": (
            _MINIMUM_USABLE_BARS_FOR_POST_SIGNAL_EVIDENCE
        ),
        "evaluated_return_count": evaluated_return_count,
        "short_window": short_window,
        "long_window": long_window,
        "lookahead_policy": ETF_SMA_BACKTEST_STATS_LOOKAHEAD_POLICY,
        "refresh_state": refresh_state,
        "backtest_state": backtest_state,
        "performance_evidence_state": performance_evidence_state,
        "profit_claim": "none",
        "starting_equity": starting_equity,
        "ending_equity": ending_equity,
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "exposure_fraction": exposure_fraction,
        "trade_count": trade_count,
        "entry_count": entry_count,
        "exit_count": exit_count,
        "final_exposure": final_exposure,
        "final_posture": final_posture,
        "final_decision": final_decision,
        "blockers": list(blockers),
        "data_provenance": {
            "local_csv_only": True,
            "network_access_attempted": False,
            "credential_access_attempted": False,
            "operator_evidence_synthetic": False,
        },
        "posture_history": posture_history,
        "equity_curve": equity_curve,
        "events": events,
        "submitted": False,
        "mutated": False,
        "submit_authorized": False,
        "paper_submit_approved": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "credential_access_attempted": False,
        "network_access_attempted": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "market_data_fetch_performed": False,
        "paper_lab_only": True,
        "research_only": True,
        "signal_evaluation_only": True,
        "not_live_authorized": True,
    }


def _candidate_row_count(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            try:
                next(reader)
            except StopIteration:
                return 0
            return sum(1 for _row in reader)
    except OSError:
        return 0


def _config(value: object) -> EtfSmaLocalBarsBacktestRefreshConfig:
    if type(value) is not EtfSmaLocalBarsBacktestRefreshConfig:
        raise ValidationError(
            "config must be an EtfSmaLocalBarsBacktestRefreshConfig."
        )
    return value


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _spy_symbol(value: object) -> str:
    symbol = _required_string(value, "symbol")
    normalized = symbol.upper()
    if normalized != symbol:
        raise ValidationError("symbol must use uppercase deterministic text.")
    if normalized != _SYMBOL:
        raise ValidationError("M407 etf-sma-local-bars-backtest-refresh supports only SPY.")
    return normalized


def _path_value(
    value: object,
    field_name: str,
    *,
    required_suffix: str,
) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a path.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    if isinstance(value, str) and "://" in value:
        raise ValidationError(f"{field_name} must be a local path.")
    if path.suffix.lower() != required_suffix:
        raise ValidationError(f"{field_name} must reference a {required_suffix} file.")
    return path


def _output_path(value: object) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError("output_path must be a path.")
    if str(path).strip() == "":
        raise ValidationError("output_path is required.")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
    return path


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    return value


def _positive_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal_value(value, field_name)
    if decimal_value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be greater than zero.")
    return decimal_value


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


def _decimal_text(value: object) -> str:
    return str(_decimal_value(value, "decimal"))


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if type(value) is not list:
        raise ValidationError(f"{field_name} must be a list.")
    items: list[str] = []
    for index, item in enumerate(value):
        if type(item) is not str:
            raise ValidationError(f"{field_name}[{index}] must be a string.")
        items.append(item)
    return tuple(items)


def _object_list(value: object) -> list[dict[str, object]]:
    if type(value) is not list:
        return []
    items: list[dict[str, object]] = []
    for item in value:
        if type(item) is dict:
            items.append(dict(item))
    return items


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            output.append(value)
            seen.add(value)
    return tuple(output)


def _blocker_text(value: str) -> str:
    return "_".join(value.lower().replace(".", "").replace(",", "").split())


def _json_safe(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"
