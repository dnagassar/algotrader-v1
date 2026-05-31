"""Offline ETF/SMA research-to-paper evidence packet contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_backtest_summary import EtfSmaBacktestSummary
from algotrader.research.etf_sma_paper_experiment_plan import (
    EtfSmaPaperExperimentPlan,
)
from algotrader.research.etf_sma_research_candidate import (
    ETF_SMA_CANDIDATE_LABELS,
    ETF_SMA_CANDIDATE_POSTURES,
    SmaResearchToPaperCandidate,
)

__all__ = [
    "ETF_SMA_RESEARCH_TO_PAPER_PACKET_LABELS",
    "ETF_SMA_RESEARCH_TO_PAPER_PACKET_LIMITATIONS",
    "EtfSmaResearchToPaperPacket",
    "build_etf_sma_research_to_paper_packet",
]


_PACKET_TYPE = "etf_sma_research_to_paper_evidence_packet"
_READY_STATUS = "ready_for_paper_lab_preview_design"
_BLOCKED_STATUS = "blocked_from_paper_lab_preview_design"
_NEXT_ACTION = "draft_separate_paper_lab_preview_plan"

ETF_SMA_RESEARCH_TO_PAPER_PACKET_LABELS = ETF_SMA_CANDIDATE_LABELS
ETF_SMA_RESEARCH_TO_PAPER_PACKET_LIMITATIONS = (
    "not_profit_evidence",
    "offline_research_only",
    "paper_preview_requires_separate_milestone",
    "no_broker_action_authorized",
    "not_live_authorized",
)


@dataclass(frozen=True, slots=True)
class EtfSmaResearchToPaperPacket:
    """Immutable offline evidence packet with no capital authority."""

    packet_type: str
    status: str
    symbol: str
    strategy_name: str
    as_of: str
    candidate_status: str
    candidate_eligibility_status: str
    plan_review_status: str
    plan_action_posture: str
    backtest_eligibility_status: str
    latest_posture: str
    bar_count: int
    signal_count: int
    exposure_count: int
    defensive_count: int
    posture_change_count: int
    ignored_future_bar_count: int
    strategy_total_return: Decimal
    benchmark_total_return: Decimal
    max_drawdown: Decimal
    candidate_labels: tuple[str, ...]
    plan_labels: tuple[str, ...]
    backtest_labels: tuple[str, ...]
    labels: tuple[str, ...]
    eligibility_status: str
    blocking_reasons: tuple[str, ...]
    required_next_action: str
    limitations: tuple[str, ...]
    evidence_summary: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_fixed_metadata(
            packet_type=self.packet_type,
            status=self.status,
            eligibility_status=self.eligibility_status,
            required_next_action=self.required_next_action,
            labels=self.labels,
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
            "candidate_status",
            _required_string(self.candidate_status, "candidate_status"),
        )
        object.__setattr__(
            self,
            "candidate_eligibility_status",
            _required_string(
                self.candidate_eligibility_status,
                "candidate_eligibility_status",
            ),
        )
        object.__setattr__(
            self,
            "plan_review_status",
            _required_string(self.plan_review_status, "plan_review_status"),
        )
        object.__setattr__(
            self,
            "plan_action_posture",
            _required_string(self.plan_action_posture, "plan_action_posture"),
        )
        object.__setattr__(
            self,
            "backtest_eligibility_status",
            _required_string(
                self.backtest_eligibility_status,
                "backtest_eligibility_status",
            ),
        )
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
            "ignored_future_bar_count",
            _non_negative_int(
                self.ignored_future_bar_count,
                "ignored_future_bar_count",
            ),
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
            "candidate_labels",
            _label_tuple(self.candidate_labels, "candidate_labels"),
        )
        object.__setattr__(
            self,
            "plan_labels",
            _label_tuple(self.plan_labels, "plan_labels"),
        )
        object.__setattr__(
            self,
            "backtest_labels",
            _label_tuple(self.backtest_labels, "backtest_labels"),
        )
        object.__setattr__(self, "labels", _packet_labels(self.labels))
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
            "limitations",
            _limitations(self.limitations),
        )
        object.__setattr__(
            self,
            "evidence_summary",
            _string_tuple(
                self.evidence_summary,
                "evidence_summary",
                allow_empty=False,
            ),
        )
        _validate_packet_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only packet metadata."""

        return {
            "packet_type": self.packet_type,
            "status": self.status,
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "as_of": self.as_of,
            "candidate_status": self.candidate_status,
            "candidate_eligibility_status": self.candidate_eligibility_status,
            "plan_review_status": self.plan_review_status,
            "plan_action_posture": self.plan_action_posture,
            "backtest_eligibility_status": self.backtest_eligibility_status,
            "latest_posture": self.latest_posture,
            "bar_count": self.bar_count,
            "signal_count": self.signal_count,
            "exposure_count": self.exposure_count,
            "defensive_count": self.defensive_count,
            "posture_change_count": self.posture_change_count,
            "ignored_future_bar_count": self.ignored_future_bar_count,
            "strategy_total_return": str(self.strategy_total_return),
            "benchmark_total_return": str(self.benchmark_total_return),
            "max_drawdown": str(self.max_drawdown),
            "candidate_labels": list(self.candidate_labels),
            "plan_labels": list(self.plan_labels),
            "backtest_labels": list(self.backtest_labels),
            "labels": list(self.labels),
            "eligibility_status": self.eligibility_status,
            "blocking_reasons": list(self.blocking_reasons),
            "required_next_action": self.required_next_action,
            "limitations": list(self.limitations),
            "evidence_summary": list(self.evidence_summary),
        }


def build_etf_sma_research_to_paper_packet(
    candidate: SmaResearchToPaperCandidate,
    plan: EtfSmaPaperExperimentPlan,
    backtest_summary: EtfSmaBacktestSummary,
    *,
    as_of: str,
) -> EtfSmaResearchToPaperPacket:
    """Build a conservative offline packet from M335, M336, and M337 artifacts."""

    checked_candidate = _candidate(candidate)
    checked_plan = _plan(plan)
    checked_backtest = _backtest(backtest_summary)
    checked_as_of = _iso_date(as_of, "as_of")
    _validate_source_alignment(
        candidate=checked_candidate,
        plan=checked_plan,
        backtest_summary=checked_backtest,
        as_of=checked_as_of,
    )
    blocking_reasons = _blocking_reasons(
        candidate=checked_candidate,
        plan=checked_plan,
        backtest_summary=checked_backtest,
    )
    status = _BLOCKED_STATUS if blocking_reasons else _READY_STATUS

    return EtfSmaResearchToPaperPacket(
        packet_type=_PACKET_TYPE,
        status=status,
        symbol=checked_candidate.symbol,
        strategy_name=checked_candidate.strategy_name,
        as_of=checked_as_of,
        candidate_status=checked_candidate.status,
        candidate_eligibility_status=checked_candidate.eligibility_status,
        plan_review_status=checked_plan.review_status,
        plan_action_posture=checked_plan.intended_paper_action_posture,
        backtest_eligibility_status=checked_backtest.eligibility_status,
        latest_posture=checked_backtest.latest_posture,
        bar_count=checked_backtest.bar_count,
        signal_count=checked_backtest.signal_count,
        exposure_count=checked_backtest.exposure_count,
        defensive_count=checked_backtest.defensive_count,
        posture_change_count=checked_backtest.posture_change_count,
        ignored_future_bar_count=checked_backtest.ignored_future_bar_count,
        strategy_total_return=checked_backtest.strategy_total_return,
        benchmark_total_return=checked_backtest.benchmark_total_return,
        max_drawdown=checked_backtest.max_drawdown,
        candidate_labels=checked_candidate.labels,
        plan_labels=checked_plan.labels,
        backtest_labels=checked_backtest.labels,
        labels=ETF_SMA_RESEARCH_TO_PAPER_PACKET_LABELS,
        eligibility_status=status,
        blocking_reasons=blocking_reasons,
        required_next_action=_NEXT_ACTION,
        limitations=_merged_strings(
            checked_candidate.limitations,
            checked_plan.limitations,
            checked_backtest.limitations,
            ETF_SMA_RESEARCH_TO_PAPER_PACKET_LIMITATIONS,
        ),
        evidence_summary=_evidence_summary(
            candidate=checked_candidate,
            plan=checked_plan,
            backtest_summary=checked_backtest,
            blocking_reasons=blocking_reasons,
        ),
    )


def _candidate(value: object) -> SmaResearchToPaperCandidate:
    if type(value) is not SmaResearchToPaperCandidate:
        raise ValidationError("candidate must be a SmaResearchToPaperCandidate.")

    return value


def _plan(value: object) -> EtfSmaPaperExperimentPlan:
    if type(value) is not EtfSmaPaperExperimentPlan:
        raise ValidationError("plan must be an EtfSmaPaperExperimentPlan.")

    return value


def _backtest(value: object) -> EtfSmaBacktestSummary:
    if type(value) is not EtfSmaBacktestSummary:
        raise ValidationError("backtest_summary must be an EtfSmaBacktestSummary.")

    return value


def _validate_source_alignment(
    *,
    candidate: SmaResearchToPaperCandidate,
    plan: EtfSmaPaperExperimentPlan,
    backtest_summary: EtfSmaBacktestSummary,
    as_of: str,
) -> None:
    if candidate.symbol != plan.symbol or candidate.symbol != backtest_summary.symbol:
        raise ValidationError("candidate, plan, and backtest symbols must match.")
    if (
        candidate.short_window != plan.short_window
        or candidate.short_window != backtest_summary.short_window
    ):
        raise ValidationError("candidate, plan, and backtest short_window must match.")
    if (
        candidate.long_window != plan.long_window
        or candidate.long_window != backtest_summary.long_window
    ):
        raise ValidationError("candidate, plan, and backtest long_window must match.")
    if candidate.as_of != as_of or plan.as_of != as_of or backtest_summary.as_of != as_of:
        raise ValidationError("candidate, plan, and backtest as_of must match.")
    if plan.candidate_posture != candidate.posture:
        raise ValidationError("plan candidate_posture must match candidate posture.")
    if backtest_summary.latest_posture != candidate.posture:
        raise ValidationError("backtest latest_posture must match candidate posture.")
    if plan.source_candidate_type != candidate.candidate_type:
        raise ValidationError("plan source candidate type must match candidate.")
    if plan.source_candidate_status != candidate.status:
        raise ValidationError("plan source candidate status must match candidate.")
    if plan.source_candidate_eligibility_status != candidate.eligibility_status:
        raise ValidationError("plan source eligibility must match candidate.")


def _blocking_reasons(
    *,
    candidate: SmaResearchToPaperCandidate,
    plan: EtfSmaPaperExperimentPlan,
    backtest_summary: EtfSmaBacktestSummary,
) -> tuple[str, ...]:
    reasons: list[str] = []
    source_labels = (
        _label_tuple(candidate.labels, "candidate_labels"),
        _label_tuple(plan.labels, "plan_labels"),
        _label_tuple(backtest_summary.labels, "backtest_labels"),
    )

    if _has_live_authorized_label(*source_labels):
        reasons.append("source_contains_live_authorized_label")
    if "paper_lab_candidate" not in source_labels[0]:
        reasons.append("candidate_missing_paper_lab_candidate_label")
    if not all("research_only" in labels for labels in source_labels):
        reasons.append("source_missing_research_only_label")
    if not all("not_live_authorized" in labels for labels in source_labels):
        reasons.append("source_missing_not_live_authorized_label")
    if not all("profit_claim=none" in labels for labels in source_labels):
        reasons.append("source_missing_profit_claim_none_label")
    if candidate.posture == "insufficient_history":
        reasons.append("candidate_insufficient_history")
    if plan.intended_paper_action_posture == "observe_only":
        reasons.append("plan_observe_only")
    if plan.intended_paper_action_posture == "candidate_defensive_bias":
        reasons.append("plan_defensive_bias")
    if plan.review_status != "requires_operator_review":
        reasons.append("plan_not_review_only")
    if plan.authorization_status != "not_broker_authorized":
        reasons.append("plan_has_capital_authority")
    if backtest_summary.eligibility_status != "research_measurement_only":
        reasons.append("backtest_not_research_measurement_only")
    if backtest_summary.bar_count == 0:
        reasons.append("backtest_zero_bars")
    if backtest_summary.signal_count == 0:
        reasons.append("backtest_zero_signal_count")
    if backtest_summary.latest_posture == "insufficient_history":
        reasons.append("backtest_insufficient_history")

    return _dedupe(reasons)


def _evidence_summary(
    *,
    candidate: SmaResearchToPaperCandidate,
    plan: EtfSmaPaperExperimentPlan,
    backtest_summary: EtfSmaBacktestSummary,
    blocking_reasons: tuple[str, ...],
) -> tuple[str, ...]:
    items = [
        *candidate.evidence_summary,
        (
            f"Candidate posture {candidate.posture}; plan posture "
            f"{plan.intended_paper_action_posture}; backtest posture "
            f"{backtest_summary.latest_posture}."
        ),
        (
            f"Offline metric record: bars={backtest_summary.bar_count}, "
            f"signals={backtest_summary.signal_count}, "
            f"exposures={backtest_summary.exposure_count}, "
            f"defensive={backtest_summary.defensive_count}, "
            f"posture_changes={backtest_summary.posture_change_count}."
        ),
        (
            "Return metrics are carried as research measurement only and do not "
            "change profit_claim=none."
        ),
    ]
    if blocking_reasons:
        items.append("Packet blocked for: " + ", ".join(blocking_reasons) + ".")
    else:
        items.append("Packet is ready only for separate paper-lab preview design.")

    return tuple(items)


def _validate_fixed_metadata(
    *,
    packet_type: object,
    status: object,
    eligibility_status: object,
    required_next_action: object,
    labels: object,
) -> None:
    if packet_type != _PACKET_TYPE:
        raise ValidationError(
            "packet_type must be exactly etf_sma_research_to_paper_evidence_packet."
        )
    if status not in (_READY_STATUS, _BLOCKED_STATUS):
        raise ValidationError("status must be a supported packet status.")
    if eligibility_status != status:
        raise ValidationError("eligibility_status must match packet status.")
    if required_next_action != _NEXT_ACTION:
        raise ValidationError("required_next_action must require preview plan draft.")
    if _packet_labels(labels) != ETF_SMA_RESEARCH_TO_PAPER_PACKET_LABELS:
        raise ValidationError("labels must preserve the ETF/SMA label set.")


def _validate_packet_consistency(packet: EtfSmaResearchToPaperPacket) -> None:
    if packet.exposure_count + packet.defensive_count != packet.bar_count:
        raise ValidationError(
            "exposure_count plus defensive_count must equal bar_count."
        )
    if packet.signal_count > packet.bar_count:
        raise ValidationError("signal_count must not exceed bar_count.")
    if packet.posture_change_count > packet.bar_count:
        raise ValidationError("posture_change_count must not exceed bar_count.")
    if packet.status == _READY_STATUS and packet.blocking_reasons:
        raise ValidationError("ready packets must not contain blocking reasons.")
    if packet.status == _BLOCKED_STATUS and not packet.blocking_reasons:
        raise ValidationError("blocked packets must contain blocking reasons.")
    if packet.required_next_action != _NEXT_ACTION:
        raise ValidationError("required_next_action must match packet constant.")
    if packet.backtest_eligibility_status != "research_measurement_only":
        raise ValidationError("backtest eligibility must remain measurement-only.")


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
    if posture not in ETF_SMA_CANDIDATE_POSTURES:
        allowed = ", ".join(ETF_SMA_CANDIDATE_POSTURES)
        raise ValidationError(f"latest_posture must be one of: {allowed}.")

    return posture


def _label_tuple(values: object, field_name: str) -> tuple[str, ...]:
    labels = _string_tuple(values, field_name, allow_empty=False)
    if len(frozenset(labels)) != len(labels):
        raise ValidationError(f"{field_name} must not contain duplicates.")

    return labels


def _packet_labels(values: object) -> tuple[str, ...]:
    labels = _label_tuple(values, "labels")
    if labels != ETF_SMA_RESEARCH_TO_PAPER_PACKET_LABELS:
        raise ValidationError("labels must match the ETF/SMA packet label set.")

    return labels


def _limitations(values: object) -> tuple[str, ...]:
    limitations = _string_tuple(values, "limitations", allow_empty=False)
    missing = tuple(
        limitation
        for limitation in ETF_SMA_RESEARCH_TO_PAPER_PACKET_LIMITATIONS
        if limitation not in limitations
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(f"limitations missing required value(s): {missing_text}.")
    if len(frozenset(limitations)) != len(limitations):
        raise ValidationError("limitations must not contain duplicates.")

    return limitations


def _has_live_authorized_label(*label_groups: tuple[str, ...]) -> bool:
    return any("live_authorized" in labels for labels in label_groups)


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
