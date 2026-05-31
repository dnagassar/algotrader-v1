"""Offline ETF/SMA paper-lab preview design contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_research_to_paper_packet import (
    ETF_SMA_RESEARCH_TO_PAPER_PACKET_LABELS,
    EtfSmaResearchToPaperPacket,
)

__all__ = [
    "ETF_SMA_PAPER_PREVIEW_DESIGN_LABELS",
    "ETF_SMA_PAPER_PREVIEW_DESIGN_LIMITATIONS",
    "ETF_SMA_PAPER_PREVIEW_DESIGN_REQUIRED_OPERATOR_CHECKS",
    "EtfSmaPaperPreviewDesign",
    "EtfSmaPaperPreviewDesignConfig",
    "build_etf_sma_paper_preview_design",
]


_PREVIEW_DESIGN_TYPE = "etf_sma_paper_lab_preview_design"
_SOURCE_READY_STATUS = "ready_for_paper_lab_preview_design"
_SOURCE_NEXT_ACTION = "draft_separate_paper_lab_preview_plan"
_READY_STATUS = "ready_for_paper_lab_preview_prompt_review"
_BLOCKED_STATUS = "blocked_from_paper_lab_preview_prompt_review"
_READY_NEXT_ACTION = "draft_separate_paper_lab_preview_prompt"
_BLOCKED_NEXT_ACTION = "resolve_research_to_paper_packet_blockers"
_SUPPORTED_POSTURES = (
    "bullish_trend_candidate",
    "defensive_or_cash_candidate",
    "insufficient_history",
)

ETF_SMA_PAPER_PREVIEW_DESIGN_LABELS = ETF_SMA_RESEARCH_TO_PAPER_PACKET_LABELS
ETF_SMA_PAPER_PREVIEW_DESIGN_REQUIRED_OPERATOR_CHECKS = (
    "fresh read-only paper snapshot before any future broker-facing preview",
    "paper profile only",
    "explicit operator approval before any future broker-facing preview",
    "separate milestone required before broker-facing preview",
    "separate milestone required before any submit",
    "no live trading authorization",
    "no retry/cancel/liquidate/fix-forward behavior from this design",
)
ETF_SMA_PAPER_PREVIEW_DESIGN_LIMITATIONS = (
    "offline_design_only",
    "not_profit_evidence",
    "no_broker_preview_authorized",
    "no_broker_action_authorized",
    "paper_preview_requires_separate_milestone",
    "submit_requires_separate_explicit_milestone",
    "not_live_authorized",
)


@dataclass(frozen=True, slots=True)
class EtfSmaPaperPreviewDesignConfig:
    """Static offline review gates for a future preview-prompt milestone."""

    required_future_operator_checks: tuple[
        str, ...
    ] = ETF_SMA_PAPER_PREVIEW_DESIGN_REQUIRED_OPERATOR_CHECKS
    additional_limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "required_future_operator_checks",
            _operator_checks(self.required_future_operator_checks),
        )
        object.__setattr__(
            self,
            "additional_limitations",
            _string_tuple(
                self.additional_limitations,
                "additional_limitations",
                allow_empty=True,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only config metadata."""

        return {
            "required_future_operator_checks": list(
                self.required_future_operator_checks
            ),
            "additional_limitations": list(self.additional_limitations),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaPaperPreviewDesign:
    """Immutable offline design metadata with no capital authority."""

    preview_design_type: str
    status: str
    preview_design_status: str
    symbol: str
    strategy_name: str
    as_of: str
    source_packet_status: str
    source_packet_eligibility_status: str
    source_packet_required_next_action: str
    source_labels: tuple[str, ...]
    labels: tuple[str, ...]
    latest_posture: str
    bar_count: int
    signal_count: int
    exposure_count: int
    defensive_count: int
    posture_change_count: int
    strategy_total_return: Decimal
    benchmark_total_return: Decimal
    max_drawdown: Decimal
    blocking_reasons: tuple[str, ...]
    required_future_operator_checks: tuple[str, ...]
    required_next_action: str
    source_limitations: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_fixed_metadata(
            preview_design_type=self.preview_design_type,
            status=self.status,
            preview_design_status=self.preview_design_status,
            labels=self.labels,
            required_next_action=self.required_next_action,
        )
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(
            self,
            "strategy_name",
            _required_string(self.strategy_name, "strategy_name"),
        )
        object.__setattr__(self, "as_of", _iso_date(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "source_packet_status",
            _required_string(self.source_packet_status, "source_packet_status"),
        )
        object.__setattr__(
            self,
            "source_packet_eligibility_status",
            _required_string(
                self.source_packet_eligibility_status,
                "source_packet_eligibility_status",
            ),
        )
        object.__setattr__(
            self,
            "source_packet_required_next_action",
            _required_string(
                self.source_packet_required_next_action,
                "source_packet_required_next_action",
            ),
        )
        object.__setattr__(
            self,
            "source_labels",
            _label_tuple(self.source_labels, "source_labels"),
        )
        object.__setattr__(self, "labels", _design_labels(self.labels))
        object.__setattr__(self, "latest_posture", _posture(self.latest_posture))
        object.__setattr__(
            self,
            "bar_count",
            _non_negative_int(self.bar_count, "bar_count"),
        )
        object.__setattr__(
            self,
            "signal_count",
            _non_negative_int(self.signal_count, "signal_count"),
        )
        object.__setattr__(
            self,
            "exposure_count",
            _non_negative_int(self.exposure_count, "exposure_count"),
        )
        object.__setattr__(
            self,
            "defensive_count",
            _non_negative_int(self.defensive_count, "defensive_count"),
        )
        object.__setattr__(
            self,
            "posture_change_count",
            _non_negative_int(self.posture_change_count, "posture_change_count"),
        )
        object.__setattr__(
            self,
            "strategy_total_return",
            _decimal(self.strategy_total_return, "strategy_total_return"),
        )
        object.__setattr__(
            self,
            "benchmark_total_return",
            _decimal(self.benchmark_total_return, "benchmark_total_return"),
        )
        object.__setattr__(
            self,
            "max_drawdown",
            _non_negative_decimal(self.max_drawdown, "max_drawdown"),
        )
        object.__setattr__(
            self,
            "blocking_reasons",
            _string_tuple(
                self.blocking_reasons,
                "blocking_reasons",
                allow_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "required_future_operator_checks",
            _operator_checks(self.required_future_operator_checks),
        )
        object.__setattr__(
            self,
            "source_limitations",
            _string_tuple(
                self.source_limitations,
                "source_limitations",
                allow_empty=False,
            ),
        )
        object.__setattr__(self, "limitations", _limitations(self.limitations))
        _validate_design_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only preview design metadata."""

        return {
            "preview_design_type": self.preview_design_type,
            "status": self.status,
            "preview_design_status": self.preview_design_status,
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "as_of": self.as_of,
            "source_packet_status": self.source_packet_status,
            "source_packet_eligibility_status": (
                self.source_packet_eligibility_status
            ),
            "source_packet_required_next_action": (
                self.source_packet_required_next_action
            ),
            "source_labels": list(self.source_labels),
            "labels": list(self.labels),
            "latest_posture": self.latest_posture,
            "bar_count": self.bar_count,
            "signal_count": self.signal_count,
            "exposure_count": self.exposure_count,
            "defensive_count": self.defensive_count,
            "posture_change_count": self.posture_change_count,
            "strategy_total_return": str(self.strategy_total_return),
            "benchmark_total_return": str(self.benchmark_total_return),
            "max_drawdown": str(self.max_drawdown),
            "blocking_reasons": list(self.blocking_reasons),
            "required_future_operator_checks": list(
                self.required_future_operator_checks
            ),
            "required_next_action": self.required_next_action,
            "source_limitations": list(self.source_limitations),
            "limitations": list(self.limitations),
        }


def build_etf_sma_paper_preview_design(
    packet: EtfSmaResearchToPaperPacket,
    config: EtfSmaPaperPreviewDesignConfig,
) -> EtfSmaPaperPreviewDesign:
    """Build an offline preview design only from an M338 packet."""

    checked_packet = _packet(packet)
    checked_config = _config(config)
    source_labels = _label_tuple(checked_packet.labels, "source_labels")
    source_limitations = _string_tuple(
        checked_packet.limitations,
        "source_limitations",
        allow_empty=False,
    )
    blocking_reasons = _blocking_reasons(checked_packet, source_labels)
    status = _BLOCKED_STATUS if blocking_reasons else _READY_STATUS
    required_next_action = (
        _BLOCKED_NEXT_ACTION if blocking_reasons else _READY_NEXT_ACTION
    )

    return EtfSmaPaperPreviewDesign(
        preview_design_type=_PREVIEW_DESIGN_TYPE,
        status=status,
        preview_design_status=status,
        symbol=checked_packet.symbol,
        strategy_name=checked_packet.strategy_name,
        as_of=checked_packet.as_of,
        source_packet_status=checked_packet.status,
        source_packet_eligibility_status=checked_packet.eligibility_status,
        source_packet_required_next_action=checked_packet.required_next_action,
        source_labels=source_labels,
        labels=ETF_SMA_PAPER_PREVIEW_DESIGN_LABELS,
        latest_posture=checked_packet.latest_posture,
        bar_count=checked_packet.bar_count,
        signal_count=checked_packet.signal_count,
        exposure_count=checked_packet.exposure_count,
        defensive_count=checked_packet.defensive_count,
        posture_change_count=checked_packet.posture_change_count,
        strategy_total_return=checked_packet.strategy_total_return,
        benchmark_total_return=checked_packet.benchmark_total_return,
        max_drawdown=checked_packet.max_drawdown,
        blocking_reasons=blocking_reasons,
        required_future_operator_checks=(
            checked_config.required_future_operator_checks
        ),
        required_next_action=required_next_action,
        source_limitations=source_limitations,
        limitations=_merged_strings(
            source_limitations,
            ETF_SMA_PAPER_PREVIEW_DESIGN_LIMITATIONS,
            checked_config.additional_limitations,
        ),
    )


def _packet(value: object) -> EtfSmaResearchToPaperPacket:
    if type(value) is not EtfSmaResearchToPaperPacket:
        raise ValidationError("packet must be an EtfSmaResearchToPaperPacket.")

    return value


def _config(value: object) -> EtfSmaPaperPreviewDesignConfig:
    if type(value) is not EtfSmaPaperPreviewDesignConfig:
        raise ValidationError("config must be an EtfSmaPaperPreviewDesignConfig.")

    return value


def _blocking_reasons(
    packet: EtfSmaResearchToPaperPacket,
    source_labels: tuple[str, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []
    source_blockers = _string_tuple(
        packet.blocking_reasons,
        "source_blocking_reasons",
        allow_empty=True,
    )

    if packet.status != _SOURCE_READY_STATUS:
        reasons.append("source_packet_not_ready_for_paper_lab_preview_design")
    if packet.eligibility_status != _SOURCE_READY_STATUS:
        reasons.append(
            "source_packet_eligibility_not_ready_for_paper_lab_preview_design"
        )
    if packet.required_next_action != _SOURCE_NEXT_ACTION:
        reasons.append("source_packet_required_next_action_unexpected")
    reasons.extend(source_blockers)

    if "paper_lab_candidate" not in source_labels:
        reasons.append("source_missing_paper_lab_candidate_label")
    if "research_only" not in source_labels:
        reasons.append("source_missing_research_only_label")
    if "not_live_authorized" not in source_labels:
        reasons.append("source_missing_not_live_authorized_label")
    if "profit_claim=none" not in source_labels:
        reasons.append("source_missing_profit_claim_none_label")
    if "live_authorized" in source_labels or _has_live_authorized_status(packet):
        reasons.append("source_contains_live_authorized")
    if _has_profit_claim_other_than_none(source_labels):
        reasons.append("source_contains_profit_claim_other_than_none")
    if packet.latest_posture == "insufficient_history":
        reasons.append("source_insufficient_history_posture")
    if packet.latest_posture == "defensive_or_cash_candidate":
        reasons.append("source_defensive_posture")

    return _dedupe(reasons)


def _validate_fixed_metadata(
    *,
    preview_design_type: object,
    status: object,
    preview_design_status: object,
    labels: object,
    required_next_action: object,
) -> None:
    if preview_design_type != _PREVIEW_DESIGN_TYPE:
        raise ValidationError(
            "preview_design_type must be exactly etf_sma_paper_lab_preview_design."
        )
    if status not in (_READY_STATUS, _BLOCKED_STATUS):
        raise ValidationError("status must be a supported preview design status.")
    if preview_design_status != status:
        raise ValidationError("preview_design_status must match status.")
    if _design_labels(labels) != ETF_SMA_PAPER_PREVIEW_DESIGN_LABELS:
        raise ValidationError("labels must preserve the ETF/SMA label set.")
    if status == _READY_STATUS and required_next_action != _READY_NEXT_ACTION:
        raise ValidationError("ready designs must draft the separate prompt.")
    if status == _BLOCKED_STATUS and required_next_action != _BLOCKED_NEXT_ACTION:
        raise ValidationError("blocked designs must resolve source packet blockers.")


def _validate_design_consistency(design: EtfSmaPaperPreviewDesign) -> None:
    if design.exposure_count + design.defensive_count != design.bar_count:
        raise ValidationError(
            "exposure_count plus defensive_count must equal bar_count."
        )
    if design.signal_count > design.bar_count:
        raise ValidationError("signal_count must not exceed bar_count.")
    if design.posture_change_count > design.bar_count:
        raise ValidationError("posture_change_count must not exceed bar_count.")
    if design.status == _READY_STATUS and design.blocking_reasons:
        raise ValidationError("ready preview designs must not contain blockers.")
    if design.status == _BLOCKED_STATUS and not design.blocking_reasons:
        raise ValidationError("blocked preview designs must contain blockers.")
    if design.status == _READY_STATUS:
        _validate_ready_source(design)


def _validate_ready_source(design: EtfSmaPaperPreviewDesign) -> None:
    if design.source_packet_status != _SOURCE_READY_STATUS:
        raise ValidationError("ready designs require a ready source packet.")
    if design.source_packet_eligibility_status != _SOURCE_READY_STATUS:
        raise ValidationError("ready designs require ready source eligibility.")
    if design.source_packet_required_next_action != _SOURCE_NEXT_ACTION:
        raise ValidationError("ready designs require the M338 next action.")
    for label in ETF_SMA_PAPER_PREVIEW_DESIGN_LABELS:
        if label not in design.source_labels:
            raise ValidationError("ready designs require all source labels.")
    if "live_authorized" in design.source_labels:
        raise ValidationError("ready designs cannot contain live authorization.")
    if _has_profit_claim_other_than_none(design.source_labels):
        raise ValidationError("ready designs cannot contain a profit claim.")
    if design.latest_posture != "bullish_trend_candidate":
        raise ValidationError("ready designs require bullish research posture.")


def _iso_date(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date string.")

    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be an ISO YYYY-MM-DD date string."
        ) from exc

    if parsed.isoformat() != value:
        raise ValidationError(f"{field_name} must use YYYY-MM-DD date format.")

    return value


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _string_tuple(
    values: object,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if not allow_empty and not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")

    return items


def _symbol(value: object) -> str:
    symbol = _required_string(value, "symbol")
    normalized = symbol.upper()
    if normalized != symbol:
        raise ValidationError("symbol must use uppercase deterministic text.")
    if any(character.isspace() for character in normalized):
        raise ValidationError("symbol must not contain whitespace.")

    return normalized


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be non-negative.")

    return value


def _decimal(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _non_negative_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal(value, field_name)
    if decimal_value < Decimal("0"):
        raise ValidationError(f"{field_name} must be non-negative.")

    return decimal_value


def _posture(value: object) -> str:
    posture = _required_string(value, "latest_posture")
    if posture not in _SUPPORTED_POSTURES:
        allowed = ", ".join(_SUPPORTED_POSTURES)
        raise ValidationError(f"latest_posture must be one of: {allowed}.")

    return posture


def _label_tuple(values: object, field_name: str) -> tuple[str, ...]:
    labels = _string_tuple(values, field_name, allow_empty=False)
    if len(frozenset(labels)) != len(labels):
        raise ValidationError(f"{field_name} must not contain duplicates.")

    return labels


def _design_labels(values: object) -> tuple[str, ...]:
    labels = _label_tuple(values, "labels")
    if labels != ETF_SMA_PAPER_PREVIEW_DESIGN_LABELS:
        raise ValidationError("labels must match the ETF/SMA preview label set.")

    return labels


def _limitations(values: object) -> tuple[str, ...]:
    limitations = _string_tuple(values, "limitations", allow_empty=False)
    missing = tuple(
        limitation
        for limitation in ETF_SMA_PAPER_PREVIEW_DESIGN_LIMITATIONS
        if limitation not in limitations
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(f"limitations missing required value(s): {missing_text}.")
    if len(frozenset(limitations)) != len(limitations):
        raise ValidationError("limitations must not contain duplicates.")

    return limitations


def _operator_checks(values: object) -> tuple[str, ...]:
    checks = _string_tuple(
        values,
        "required_future_operator_checks",
        allow_empty=False,
    )
    missing = tuple(
        check
        for check in ETF_SMA_PAPER_PREVIEW_DESIGN_REQUIRED_OPERATOR_CHECKS
        if check not in checks
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            "required_future_operator_checks missing required value(s): "
            f"{missing_text}."
        )
    if len(frozenset(checks)) != len(checks):
        raise ValidationError("required_future_operator_checks must not duplicate.")

    return checks


def _has_live_authorized_status(packet: EtfSmaResearchToPaperPacket) -> bool:
    return any(
        _is_live_authorized_text(text)
        for text in (
            packet.status,
            packet.eligibility_status,
            packet.candidate_status,
            packet.candidate_eligibility_status,
            packet.plan_review_status,
            packet.plan_action_posture,
            packet.backtest_eligibility_status,
            packet.required_next_action,
        )
    )


def _is_live_authorized_text(value: str) -> bool:
    if value.startswith("not_live_authorized"):
        return False

    return value == "live_authorized" or value.startswith("live_authorized_")


def _has_profit_claim_other_than_none(labels: tuple[str, ...]) -> bool:
    return any(
        label.startswith("profit_claim=") and label != "profit_claim=none"
        for label in labels
    )


def _merged_strings(*groups: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    for group in groups:
        for item in _string_tuple(group, "string_group", allow_empty=True):
            if item not in merged:
                merged.append(item)

    return tuple(merged)


def _dedupe(values: list[str]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        checked_value = _required_string(value, "blocking_reason")
        if checked_value not in deduped:
            deduped.append(checked_value)

    return tuple(deduped)
