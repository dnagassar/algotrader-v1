"""Review-only ETF/SMA paper-lab experiment plan contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_research_candidate import (
    ETF_SMA_CANDIDATE_LABELS,
    ETF_SMA_CANDIDATE_POSTURES,
    SmaResearchToPaperCandidate,
)

__all__ = [
    "ETF_SMA_PAPER_EXPERIMENT_PLAN_LABELS",
    "ETF_SMA_PAPER_EXPERIMENT_PLAN_POSTURES",
    "EtfSmaPaperExperimentPlan",
    "EtfSmaPaperExperimentPlanConfig",
    "draft_etf_sma_paper_experiment_plan",
]


_PLAN_TYPE = "etf_sma_paper_experiment_plan"
_EXPERIMENT_STATUS = "paper_experiment_plan_drafted"
_REVIEW_STATUS = "requires_operator_review"
_AUTHORIZATION_STATUS = "not_broker_authorized"
_NEXT_OPERATOR_ACTION = "review_plan_before_separate_preview_or_paper_probe_milestone"

ETF_SMA_PAPER_EXPERIMENT_PLAN_LABELS = ETF_SMA_CANDIDATE_LABELS
ETF_SMA_PAPER_EXPERIMENT_PLAN_POSTURES = (
    "observe_only",
    "candidate_long_bias",
    "candidate_defensive_bias",
)

_DEFAULT_PROPOSED_CAP_POLICY = (
    "metadata_only_notional_cap: USD 0; separate review required before any "
    "executable instruction"
)
_DEFAULT_REQUIRED_PRE_SUBMIT_CHECKS = (
    "operator review of this experiment plan is complete",
    "fresh read-only paper-lab snapshot exists before any future submit",
    "separate preview-only local policy/checklist milestone is reviewed first",
    "separate paper-probe milestone explicitly approves scope before any broker action",
    "candidate labels still preserve research_only, paper_lab_candidate, "
    "not_live_authorized, and profit_claim=none",
    "no ambiguous broker response remains unresolved",
)
_PAPER_LAB_SAFEGUARDS = (
    "fresh read-only snapshot required before any future submit",
    "max one broker action per approved future probe",
    "post-action read-only snapshot required",
    "ambiguous broker response means stop",
    "no retry/cancel/liquidate/close/fix-forward without separate milestone",
)
_PLAN_LIMITATIONS = (
    "review-only paper-lab experiment plan; no capital authority",
    "no paper or live authorization",
    "proposed cap policy is metadata only and not executable",
    "separate preview/checklist milestone required before any paper probe",
)
_INSUFFICIENT_HISTORY_LIMITATION = (
    "insufficient history candidate is observe-only until a separate review "
    "supplies enough local evidence"
)


@dataclass(frozen=True, slots=True)
class EtfSmaPaperExperimentPlanConfig:
    """Static review metadata for drafting an ETF/SMA paper-lab plan."""

    proposed_cap_policy: str = _DEFAULT_PROPOSED_CAP_POLICY
    required_pre_submit_checks: tuple[str, ...] = _DEFAULT_REQUIRED_PRE_SUBMIT_CHECKS
    additional_limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "proposed_cap_policy",
            _required_string(self.proposed_cap_policy, "proposed_cap_policy"),
        )
        object.__setattr__(
            self,
            "required_pre_submit_checks",
            _string_tuple(
                self.required_pre_submit_checks,
                "required_pre_submit_checks",
                allow_empty=False,
            ),
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
            "proposed_cap_policy": self.proposed_cap_policy,
            "required_pre_submit_checks": list(self.required_pre_submit_checks),
            "additional_limitations": list(self.additional_limitations),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaPaperExperimentPlan:
    """Review-only ETF/SMA plan metadata with no executable authority."""

    plan_type: str
    experiment_status: str
    review_status: str
    authorization_status: str
    symbol: str
    strategy_name: str
    as_of: str
    short_window: int
    long_window: int
    latest_close: Decimal | None
    short_sma: Decimal | None
    long_sma: Decimal | None
    candidate_posture: str
    intended_paper_action_posture: str
    proposed_cap_policy: str
    required_pre_submit_checks: tuple[str, ...]
    paper_lab_safeguards: tuple[str, ...]
    limitations: tuple[str, ...]
    labels: tuple[str, ...]
    source_candidate_type: str
    source_candidate_status: str
    source_candidate_eligibility_status: str
    next_operator_action: str

    def __post_init__(self) -> None:
        _validate_plan_metadata(
            plan_type=self.plan_type,
            experiment_status=self.experiment_status,
            review_status=self.review_status,
            authorization_status=self.authorization_status,
            labels=self.labels,
            next_operator_action=self.next_operator_action,
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
            "short_window",
            _positive_int(self.short_window, "short_window"),
        )
        object.__setattr__(
            self,
            "long_window",
            _positive_int(self.long_window, "long_window"),
        )
        if self.short_window >= self.long_window:
            raise ValidationError("short_window must be less than long_window.")
        object.__setattr__(
            self,
            "latest_close",
            _optional_positive_decimal(self.latest_close, "latest_close"),
        )
        object.__setattr__(
            self,
            "short_sma",
            _optional_positive_decimal(self.short_sma, "short_sma"),
        )
        object.__setattr__(
            self,
            "long_sma",
            _optional_positive_decimal(self.long_sma, "long_sma"),
        )
        object.__setattr__(
            self,
            "candidate_posture",
            _candidate_posture(self.candidate_posture),
        )
        object.__setattr__(
            self,
            "intended_paper_action_posture",
            _plan_posture(self.intended_paper_action_posture),
        )
        object.__setattr__(
            self,
            "proposed_cap_policy",
            _required_string(self.proposed_cap_policy, "proposed_cap_policy"),
        )
        object.__setattr__(
            self,
            "required_pre_submit_checks",
            _string_tuple(
                self.required_pre_submit_checks,
                "required_pre_submit_checks",
                allow_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "paper_lab_safeguards",
            _string_tuple(
                self.paper_lab_safeguards,
                "paper_lab_safeguards",
                allow_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations", allow_empty=False),
        )
        object.__setattr__(
            self,
            "labels",
            _validated_label_tuple(self.labels),
        )
        object.__setattr__(
            self,
            "source_candidate_type",
            _required_string(self.source_candidate_type, "source_candidate_type"),
        )
        object.__setattr__(
            self,
            "source_candidate_status",
            _required_string(self.source_candidate_status, "source_candidate_status"),
        )
        object.__setattr__(
            self,
            "source_candidate_eligibility_status",
            _required_string(
                self.source_candidate_eligibility_status,
                "source_candidate_eligibility_status",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only plan metadata."""

        return {
            "plan_type": self.plan_type,
            "experiment_status": self.experiment_status,
            "review_status": self.review_status,
            "authorization_status": self.authorization_status,
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "as_of": self.as_of,
            "short_window": self.short_window,
            "long_window": self.long_window,
            "latest_close": _decimal_text(self.latest_close),
            "short_sma": _decimal_text(self.short_sma),
            "long_sma": _decimal_text(self.long_sma),
            "candidate_posture": self.candidate_posture,
            "intended_paper_action_posture": self.intended_paper_action_posture,
            "proposed_cap_policy": self.proposed_cap_policy,
            "required_pre_submit_checks": list(self.required_pre_submit_checks),
            "paper_lab_safeguards": list(self.paper_lab_safeguards),
            "limitations": list(self.limitations),
            "labels": list(self.labels),
            "source_candidate_type": self.source_candidate_type,
            "source_candidate_status": self.source_candidate_status,
            "source_candidate_eligibility_status": (
                self.source_candidate_eligibility_status
            ),
            "next_operator_action": self.next_operator_action,
        }


def draft_etf_sma_paper_experiment_plan(
    candidate: SmaResearchToPaperCandidate,
    config: EtfSmaPaperExperimentPlanConfig,
) -> EtfSmaPaperExperimentPlan:
    """Draft review-only paper-lab plan metadata from an M335 candidate."""

    checked_candidate = _candidate(candidate)
    checked_config = _config(config)
    labels = _candidate_labels_for_plan(checked_candidate)
    intended_posture = _intended_plan_posture(checked_candidate.posture)
    limitations = (
        *checked_candidate.limitations,
        *_PLAN_LIMITATIONS,
        *checked_config.additional_limitations,
    )
    if checked_candidate.posture == "insufficient_history":
        limitations = (*limitations, _INSUFFICIENT_HISTORY_LIMITATION)

    return EtfSmaPaperExperimentPlan(
        plan_type=_PLAN_TYPE,
        experiment_status=_EXPERIMENT_STATUS,
        review_status=_REVIEW_STATUS,
        authorization_status=_AUTHORIZATION_STATUS,
        symbol=checked_candidate.symbol,
        strategy_name=checked_candidate.strategy_name,
        as_of=checked_candidate.as_of,
        short_window=checked_candidate.short_window,
        long_window=checked_candidate.long_window,
        latest_close=checked_candidate.latest_close,
        short_sma=checked_candidate.short_sma,
        long_sma=checked_candidate.long_sma,
        candidate_posture=checked_candidate.posture,
        intended_paper_action_posture=intended_posture,
        proposed_cap_policy=checked_config.proposed_cap_policy,
        required_pre_submit_checks=checked_config.required_pre_submit_checks,
        paper_lab_safeguards=_PAPER_LAB_SAFEGUARDS,
        limitations=limitations,
        labels=labels,
        source_candidate_type=checked_candidate.candidate_type,
        source_candidate_status=checked_candidate.status,
        source_candidate_eligibility_status=checked_candidate.eligibility_status,
        next_operator_action=_NEXT_OPERATOR_ACTION,
    )


def _validate_plan_metadata(
    *,
    plan_type: object,
    experiment_status: object,
    review_status: object,
    authorization_status: object,
    labels: object,
    next_operator_action: object,
) -> None:
    if plan_type != _PLAN_TYPE:
        raise ValidationError("plan_type must be exactly etf_sma_paper_experiment_plan.")
    if experiment_status != _EXPERIMENT_STATUS:
        raise ValidationError("experiment_status must indicate drafted plan status.")
    if review_status != _REVIEW_STATUS:
        raise ValidationError("review_status must require operator review.")
    if authorization_status != _AUTHORIZATION_STATUS:
        raise ValidationError("authorization_status must prohibit broker authorization.")
    if _validated_label_tuple(labels) != ETF_SMA_PAPER_EXPERIMENT_PLAN_LABELS:
        raise ValidationError("labels must preserve the ETF/SMA candidate labels.")
    if next_operator_action != _NEXT_OPERATOR_ACTION:
        raise ValidationError("next_operator_action must require separate review.")


def _candidate(value: object) -> SmaResearchToPaperCandidate:
    if type(value) is not SmaResearchToPaperCandidate:
        raise ValidationError("candidate must be a SmaResearchToPaperCandidate.")

    return value


def _config(value: object) -> EtfSmaPaperExperimentPlanConfig:
    if type(value) is not EtfSmaPaperExperimentPlanConfig:
        raise ValidationError("config must be an EtfSmaPaperExperimentPlanConfig.")

    return value


def _candidate_labels_for_plan(
    candidate: SmaResearchToPaperCandidate,
) -> tuple[str, ...]:
    labels = _validated_label_tuple(candidate.labels)
    if "live_authorized" in labels or candidate.status == "live_authorized":
        raise ValidationError("live authorized candidates cannot draft paper plans.")
    if "paper_lab_candidate" not in labels:
        raise ValidationError("candidate must include paper_lab_candidate label.")
    if "not_live_authorized" not in labels:
        raise ValidationError("candidate must preserve not_live_authorized label.")
    if "research_only" not in labels:
        raise ValidationError("candidate must preserve research_only label.")
    if "profit_claim=none" not in labels:
        raise ValidationError("candidate must preserve profit_claim=none label.")
    if labels != ETF_SMA_CANDIDATE_LABELS:
        raise ValidationError("candidate labels must match the M335 label set.")

    return labels


def _intended_plan_posture(candidate_posture: str) -> str:
    if candidate_posture == "bullish_trend_candidate":
        return "candidate_long_bias"
    if candidate_posture == "defensive_or_cash_candidate":
        return "candidate_defensive_bias"
    if candidate_posture == "insufficient_history":
        return "observe_only"

    raise ValidationError("candidate posture is not supported for paper planning.")


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


def _validated_label_tuple(values: object) -> tuple[str, ...]:
    labels = _string_tuple(values, "labels", allow_empty=False)
    if len(frozenset(labels)) != len(labels):
        raise ValidationError("labels must not contain duplicates.")

    return labels


def _symbol(value: object) -> str:
    symbol = _required_string(value, "symbol")
    normalized = symbol.upper()
    if normalized != symbol:
        raise ValidationError("symbol must use uppercase deterministic text.")
    if any(character.isspace() for character in normalized):
        raise ValidationError("symbol must not contain whitespace.")

    return normalized


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 1:
        raise ValidationError(f"{field_name} must be at least 1.")

    return value


def _decimal(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _optional_positive_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None

    decimal_value = _decimal(value, field_name)
    if decimal_value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be positive.")

    return decimal_value


def _candidate_posture(value: object) -> str:
    posture = _required_string(value, "candidate_posture")
    if posture not in ETF_SMA_CANDIDATE_POSTURES:
        allowed = ", ".join(ETF_SMA_CANDIDATE_POSTURES)
        raise ValidationError(f"candidate_posture must be one of: {allowed}.")

    return posture


def _plan_posture(value: object) -> str:
    posture = _required_string(value, "intended_paper_action_posture")
    if posture not in ETF_SMA_PAPER_EXPERIMENT_PLAN_POSTURES:
        allowed = ", ".join(ETF_SMA_PAPER_EXPERIMENT_PLAN_POSTURES)
        raise ValidationError(
            f"intended_paper_action_posture must be one of: {allowed}."
        )

    return posture


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return str(value)
