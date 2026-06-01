"""Offline ETF/SMA signal-to-execution-preview bridge with no broker action."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from algotrader.core.time import require_utc_datetime
from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError
from algotrader.signals.etf_sma_evaluator import (
    ETF_SMA_SIGNAL_POSTURES,
    EtfSmaSignalResult,
)

__all__ = [
    "ETF_SMA_EXECUTION_PREVIEW_LABELS",
    "EtfSmaExecutionPreview",
    "EtfSmaExecutionPreviewConfig",
    "build_etf_sma_execution_preview",
]

_ASSET_CLASS = "equity"
_DEFAULT_SYMBOL = "SPY"
_DEFAULT_ALLOWLIST = (_DEFAULT_SYMBOL,)
_MAX_NOTIONAL_CAP = Decimal("25.00")
_PROFIT_CLAIM = "none"
_INTENDED_SIDE = "buy"
_INTENDED_ORDER_STYLE = "notional_market_preview"
_ACCEPTED_REASON = "bullish_spy_signal_within_offline_preview_constraints"
_NEXT_ACTION = "m347_local_etf_sma_preview_jsonl_artifact_no_broker_action"

ETF_SMA_EXECUTION_PREVIEW_LABELS = (
    "paper_lab_only",
    "offline_execution_preview_only",
    "not_live_authorized",
    "profit_claim=none",
)


@dataclass(frozen=True, slots=True)
class EtfSmaExecutionPreviewConfig:
    """Static offline preview constraints for the first ETF/SMA bridge path."""

    as_of: datetime
    symbol: str = _DEFAULT_SYMBOL
    asset_class: str = _ASSET_CLASS
    max_notional: Decimal = _MAX_NOTIONAL_CAP
    allowlist: tuple[str, ...] = _DEFAULT_ALLOWLIST
    require_bullish_posture: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "as_of", _utc_datetime(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "symbol",
            _fixed_string(symbol_value(self.symbol), _DEFAULT_SYMBOL, "symbol"),
        )
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, _ASSET_CLASS, "asset_class"),
        )
        object.__setattr__(
            self,
            "max_notional",
            _positive_capped_notional(self.max_notional, "max_notional"),
        )
        object.__setattr__(self, "allowlist", _allowlist(self.allowlist))
        object.__setattr__(
            self,
            "require_bullish_posture",
            _true_bool(
                self.require_bullish_posture,
                "require_bullish_posture",
            ),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaExecutionPreview:
    """Immutable pre-broker ETF/SMA preview artifact."""

    symbol: str
    asset_class: str
    as_of: datetime
    source_signal_result: EtfSmaSignalResult
    signal_posture: str
    signal_is_bullish_risk_on: bool
    eligible_for_future_paper_lab_preview: bool
    accepted_for_offline_preview: bool
    would_create_execution_facing_candidate_later: bool
    skipped: bool
    skip_reason: str
    decision_reason: str
    max_notional: Decimal
    allowlist: tuple[str, ...]
    intended_side: str | None
    intended_order_style: str | None
    preview_notional: Decimal | None
    labels: tuple[str, ...]
    profit_claim: str
    broker_action_performed: bool
    broker_preview_performed: bool
    submit_allowed: bool
    mutated: bool
    next_action: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, _ASSET_CLASS, "asset_class"),
        )
        object.__setattr__(self, "as_of", _utc_datetime(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "source_signal_result",
            _source_signal_result(self.source_signal_result),
        )
        object.__setattr__(self, "signal_posture", _posture(self.signal_posture))
        object.__setattr__(
            self,
            "signal_is_bullish_risk_on",
            _bool(self.signal_is_bullish_risk_on, "signal_is_bullish_risk_on"),
        )
        object.__setattr__(
            self,
            "eligible_for_future_paper_lab_preview",
            _bool(
                self.eligible_for_future_paper_lab_preview,
                "eligible_for_future_paper_lab_preview",
            ),
        )
        object.__setattr__(
            self,
            "accepted_for_offline_preview",
            _bool(
                self.accepted_for_offline_preview,
                "accepted_for_offline_preview",
            ),
        )
        object.__setattr__(
            self,
            "would_create_execution_facing_candidate_later",
            _bool(
                self.would_create_execution_facing_candidate_later,
                "would_create_execution_facing_candidate_later",
            ),
        )
        object.__setattr__(self, "skipped", _bool(self.skipped, "skipped"))
        object.__setattr__(
            self,
            "skip_reason",
            _string(self.skip_reason, "skip_reason"),
        )
        object.__setattr__(
            self,
            "decision_reason",
            _non_empty_string(self.decision_reason, "decision_reason"),
        )
        object.__setattr__(
            self,
            "max_notional",
            _positive_capped_notional(self.max_notional, "max_notional"),
        )
        object.__setattr__(self, "allowlist", _allowlist(self.allowlist))
        object.__setattr__(
            self,
            "intended_side",
            _optional_fixed_string(self.intended_side, _INTENDED_SIDE, "intended_side"),
        )
        object.__setattr__(
            self,
            "intended_order_style",
            _optional_fixed_string(
                self.intended_order_style,
                _INTENDED_ORDER_STYLE,
                "intended_order_style",
            ),
        )
        object.__setattr__(
            self,
            "preview_notional",
            _optional_positive_capped_notional(
                self.preview_notional,
                "preview_notional",
            ),
        )
        object.__setattr__(
            self,
            "labels",
            _fixed_string_tuple(
                self.labels,
                ETF_SMA_EXECUTION_PREVIEW_LABELS,
                "labels",
            ),
        )
        object.__setattr__(
            self,
            "profit_claim",
            _fixed_string(self.profit_claim, _PROFIT_CLAIM, "profit_claim"),
        )
        object.__setattr__(
            self,
            "broker_action_performed",
            _false_bool(
                self.broker_action_performed,
                "broker_action_performed",
            ),
        )
        object.__setattr__(
            self,
            "broker_preview_performed",
            _false_bool(
                self.broker_preview_performed,
                "broker_preview_performed",
            ),
        )
        object.__setattr__(
            self,
            "submit_allowed",
            _false_bool(self.submit_allowed, "submit_allowed"),
        )
        object.__setattr__(self, "mutated", _false_bool(self.mutated, "mutated"))
        object.__setattr__(
            self,
            "next_action",
            _fixed_string(self.next_action, _NEXT_ACTION, "next_action"),
        )
        _validate_preview_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only preview metadata."""

        return {
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "as_of": self.as_of.isoformat(),
            "source_signal_result": self.source_signal_result.to_dict(),
            "signal_posture": self.signal_posture,
            "signal_is_bullish_risk_on": self.signal_is_bullish_risk_on,
            "eligible_for_future_paper_lab_preview": (
                self.eligible_for_future_paper_lab_preview
            ),
            "accepted_for_offline_preview": self.accepted_for_offline_preview,
            "would_create_execution_facing_candidate_later": (
                self.would_create_execution_facing_candidate_later
            ),
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "decision_reason": self.decision_reason,
            "max_notional": str(self.max_notional),
            "allowlist": list(self.allowlist),
            "intended_side": self.intended_side,
            "intended_order_style": self.intended_order_style,
            "preview_notional": _decimal_text(self.preview_notional),
            "labels": list(self.labels),
            "profit_claim": self.profit_claim,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
            "submit_allowed": self.submit_allowed,
            "mutated": self.mutated,
            "next_action": self.next_action,
        }


def build_etf_sma_execution_preview(
    source_signal_result: EtfSmaSignalResult,
    config: EtfSmaExecutionPreviewConfig,
) -> EtfSmaExecutionPreview:
    """Build a deterministic offline preview artifact from an ETF/SMA signal."""

    checked_source = _source_signal_result(source_signal_result)
    checked_config = _config(config)
    if checked_source.as_of != checked_config.as_of:
        raise ValidationError("as_of must match source signal result as_of.")

    skip_reason = _skip_reason(checked_source, checked_config)
    accepted = skip_reason == ""
    decision_reason = _ACCEPTED_REASON if accepted else skip_reason

    return EtfSmaExecutionPreview(
        symbol=checked_source.symbol,
        asset_class=checked_source.asset_class,
        as_of=checked_source.as_of,
        source_signal_result=checked_source,
        signal_posture=checked_source.posture,
        signal_is_bullish_risk_on=checked_source.posture == "bullish_risk_on",
        eligible_for_future_paper_lab_preview=accepted,
        accepted_for_offline_preview=accepted,
        would_create_execution_facing_candidate_later=accepted,
        skipped=not accepted,
        skip_reason=skip_reason,
        decision_reason=decision_reason,
        max_notional=checked_config.max_notional,
        allowlist=checked_config.allowlist,
        intended_side=_INTENDED_SIDE if accepted else None,
        intended_order_style=_INTENDED_ORDER_STYLE if accepted else None,
        preview_notional=checked_config.max_notional if accepted else None,
        labels=ETF_SMA_EXECUTION_PREVIEW_LABELS,
        profit_claim=_PROFIT_CLAIM,
        broker_action_performed=False,
        broker_preview_performed=False,
        submit_allowed=False,
        mutated=False,
        next_action=_NEXT_ACTION,
    )


def _config(value: object) -> EtfSmaExecutionPreviewConfig:
    if type(value) is not EtfSmaExecutionPreviewConfig:
        raise ValidationError("config must be an EtfSmaExecutionPreviewConfig.")

    return value


def _source_signal_result(value: object) -> EtfSmaSignalResult:
    if type(value) is not EtfSmaSignalResult:
        raise ValidationError("source_signal_result must be an EtfSmaSignalResult.")

    return value


def _skip_reason(
    source_signal_result: EtfSmaSignalResult,
    config: EtfSmaExecutionPreviewConfig,
) -> str:
    if (
        source_signal_result.symbol != config.symbol
        or source_signal_result.symbol not in config.allowlist
    ):
        return "symbol_not_allowed"
    if source_signal_result.asset_class != config.asset_class:
        return "asset_class_not_supported"
    if source_signal_result.posture == "insufficient_history":
        return "signal_insufficient_history"
    if source_signal_result.posture != "bullish_risk_on":
        return "signal_posture_not_bullish"

    return ""


def _validate_preview_consistency(preview: EtfSmaExecutionPreview) -> None:
    source = preview.source_signal_result
    accepted = preview.accepted_for_offline_preview

    if preview.symbol != source.symbol:
        raise ValidationError("symbol must match source signal result symbol.")
    if preview.asset_class != source.asset_class:
        raise ValidationError("asset_class must match source signal result asset_class.")
    if preview.as_of != source.as_of:
        raise ValidationError("as_of must match source signal result as_of.")
    if preview.signal_posture != source.posture:
        raise ValidationError("signal_posture must match source signal result posture.")
    if preview.signal_is_bullish_risk_on != (source.posture == "bullish_risk_on"):
        raise ValidationError("signal_is_bullish_risk_on must match source posture.")
    if preview.eligible_for_future_paper_lab_preview != accepted:
        raise ValidationError(
            "eligible_for_future_paper_lab_preview must match accepted status."
        )
    if preview.would_create_execution_facing_candidate_later != accepted:
        raise ValidationError(
            "would_create_execution_facing_candidate_later must match accepted status."
        )
    if preview.skipped == accepted:
        raise ValidationError("skipped must be the inverse of accepted status.")

    if accepted:
        if preview.skip_reason != "":
            raise ValidationError("skip_reason must be empty for accepted previews.")
        if preview.decision_reason != _ACCEPTED_REASON:
            raise ValidationError("decision_reason must be the accepted preview reason.")
        if preview.intended_side != _INTENDED_SIDE:
            raise ValidationError("intended_side must be buy for accepted previews.")
        if preview.intended_order_style != _INTENDED_ORDER_STYLE:
            raise ValidationError(
                "intended_order_style must be notional_market_preview."
            )
        if preview.preview_notional != preview.max_notional:
            raise ValidationError(
                "preview_notional must match max_notional for accepted previews."
            )
        return

    if preview.skip_reason == "":
        raise ValidationError("skip_reason is required for skipped previews.")
    if preview.decision_reason != preview.skip_reason:
        raise ValidationError("decision_reason must match skip_reason when skipped.")
    if preview.intended_side is not None:
        raise ValidationError("intended_side must be None when skipped.")
    if preview.intended_order_style is not None:
        raise ValidationError("intended_order_style must be None when skipped.")
    if preview.preview_notional is not None:
        raise ValidationError("preview_notional must be None when skipped.")


def _utc_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a timezone-aware UTC datetime.")

    try:
        return require_utc_datetime(value)
    except ValidationError as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc


def _positive_capped_notional(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal or not value.is_finite():
        raise ValidationError(f"{field_name} must be a positive Decimal.")
    if value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be a positive Decimal.")
    if value > _MAX_NOTIONAL_CAP:
        raise ValidationError(f"{field_name} must be less than or equal to 25.00.")

    return value


def _optional_positive_capped_notional(
    value: object,
    field_name: str,
) -> Decimal | None:
    if value is None:
        return None

    return _positive_capped_notional(value, field_name)


def _allowlist(values: object) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError("allowlist must be a tuple or list of symbols.")

    symbols = tuple(symbol_value(symbol) for symbol in values)
    if symbols != _DEFAULT_ALLOWLIST:
        raise ValidationError("allowlist must be exactly ('SPY',).")

    return symbols


def _fixed_string(value: object, expected: str, field_name: str) -> str:
    if type(value) is not str or value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")

    return value


def _optional_fixed_string(
    value: object,
    expected: str,
    field_name: str,
) -> str | None:
    if value is None:
        return None

    return _fixed_string(value, expected, field_name)


def _string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")

    return value


def _non_empty_string(value: object, field_name: str) -> str:
    text = _string(value, field_name)
    if text == "":
        raise ValidationError(f"{field_name} is required.")

    return text


def _fixed_string_tuple(
    values: object,
    expected: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if items != expected:
        raise ValidationError(f"{field_name} must match the required values.")

    return items


def _posture(value: object) -> str:
    if type(value) is not str or value not in ETF_SMA_SIGNAL_POSTURES:
        allowed = ", ".join(ETF_SMA_SIGNAL_POSTURES)
        raise ValidationError(f"signal_posture must be one of: {allowed}.")

    return value


def _bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a boolean.")

    return value


def _true_bool(value: object, field_name: str) -> bool:
    if type(value) is not bool or value is not True:
        raise ValidationError(f"{field_name} must be true.")

    return value


def _false_bool(value: object, field_name: str) -> bool:
    if type(value) is not bool or value is not False:
        raise ValidationError(f"{field_name} must be false.")

    return value


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return str(value)
