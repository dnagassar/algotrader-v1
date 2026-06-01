"""M350 operator review before any tiny SPY paper probe."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Mapping

from algotrader.errors import ValidationError

__all__ = [
    "ETF_SMA_PAPER_PROBE_OPERATOR_REVIEW_LABELS",
    "ETF_SMA_PAPER_PROBE_OPERATOR_REVIEW_LIMITATIONS",
    "EtfSmaPaperProbeOperatorReview",
    "EtfSmaPaperProbeOperatorReviewConfig",
    "build_etf_sma_paper_probe_operator_review",
    "load_etf_sma_paper_probe_operator_review_from_jsonl",
    "render_etf_sma_paper_probe_operator_review_json",
    "render_etf_sma_paper_probe_operator_review_text",
]


ETF_SMA_PAPER_PROBE_OPERATOR_REVIEW_LABELS = (
    "paper_lab_only",
    "operator_review_only",
    "not_live_authorized",
    "profit_claim=none",
)
ETF_SMA_PAPER_PROBE_OPERATOR_REVIEW_LIMITATIONS = (
    "operator_review_only",
    "not_submit_authorization",
    "separate_future_probe_milestone_required",
    "paper_probe_not_performed",
    "no_broker_preview_or_staging",
    "no_broker_action_authorized",
    "no_cancel_close_liquidate_or_retry",
    "no_account_position_order_fill_or_portfolio_mutation",
    "not_live_authorization",
    "not_profit_evidence",
)

_REVIEW_VERSION = "etf_sma_paper_probe_operator_review_v1"
_RECORD_TYPE = "etf_sma_paper_probe_operator_review"
_SOURCE_RECORD_TYPE = "etf_sma_paper_broker_preview"
_SOURCE_M349_RUN_ID = "m349_etf_sma_paper_preview_only"
_SOURCE_M348_RUN_ID = "m348_etf_sma_fresh_read_only_snapshot"
_SOURCE_PREVIEW_STATUS = "broker_facing_local_payload_previewed"
_SOURCE_NEXT_ACTION = "m350_operator_review_before_any_tiny_spy_paper_probe"
_READY_STATUS = "ready_for_separate_tiny_spy_paper_probe_milestone"
_BLOCKED_STATUS = "blocked_from_tiny_spy_paper_probe_milestone"
_READY_APPROVED_NEXT_ACTION = "scope_m351_tiny_spy_paper_probe_milestone_only"
_BLOCKED_APPROVED_NEXT_ACTION = "resolve_m350_operator_review_blockers"
_NEXT_ACTION = "m351_separate_tiny_spy_paper_probe_scope_if_operator_approves"
_PROFIT_CLAIM = "none"
_SYMBOL = "SPY"
_ASSET_CLASS = "equity"
_SIDE = "buy"
_ORDER_TYPE = "market"
_TIME_IN_FORCE = "day"
_MAX_NOTIONAL_CAP = Decimal("25.00")
_USABLE_REVALIDATION_STATE = "usable_for_manual_review"
_SNAPSHOT_STATUS = "read_only_snapshot_completed_for_manual_review"
_FORBIDDEN_LIVE_AUTHORIZATION_VALUES = {
    "authorized_for_live_trading",
    "live_authorized",
    "live_authorized=true",
    "live_trading_authorized",
}


@dataclass(frozen=True, slots=True)
class EtfSmaPaperProbeOperatorReviewConfig:
    """Static M350 review gates for the M349 local preview record."""

    source_m349_run_id: str = _SOURCE_M349_RUN_ID
    source_m348_run_id: str = _SOURCE_M348_RUN_ID
    max_notional: Decimal = _MAX_NOTIONAL_CAP

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_m349_run_id",
            _non_empty_string(self.source_m349_run_id, "source_m349_run_id"),
        )
        object.__setattr__(
            self,
            "source_m348_run_id",
            _non_empty_string(self.source_m348_run_id, "source_m348_run_id"),
        )
        object.__setattr__(
            self,
            "max_notional",
            _positive_capped_notional(self.max_notional, "max_notional"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return primitive config metadata."""

        return {
            "source_m349_run_id": self.source_m349_run_id,
            "source_m348_run_id": self.source_m348_run_id,
            "max_notional": str(self.max_notional),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaPaperProbeOperatorReview:
    """Immutable M350 review result with no capital authority."""

    review_version: str
    record_type: str
    review_status: str
    approved_next_action: str
    source_m348_run_id: str
    source_m349_run_id: str
    symbol: str
    asset_class: str
    side: str
    order_type: str
    time_in_force: str
    notional: Decimal | None
    max_notional: Decimal | None
    operator_review_required: bool
    separate_future_probe_milestone_required: bool
    submit_allowed: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    broker_preview_performed: bool
    paper_probe_performed: bool
    live_authorized: bool
    labels: tuple[str, ...]
    profit_claim: str
    next_action: str
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "review_version",
            _fixed_string(self.review_version, _REVIEW_VERSION, "review_version"),
        )
        object.__setattr__(
            self,
            "record_type",
            _fixed_string(self.record_type, _RECORD_TYPE, "record_type"),
        )
        object.__setattr__(
            self,
            "review_status",
            _review_status(self.review_status),
        )
        object.__setattr__(
            self,
            "approved_next_action",
            _approved_next_action(self.approved_next_action, self.review_status),
        )
        object.__setattr__(
            self,
            "source_m348_run_id",
            _string(self.source_m348_run_id, "source_m348_run_id"),
        )
        object.__setattr__(
            self,
            "source_m349_run_id",
            _string(self.source_m349_run_id, "source_m349_run_id"),
        )
        object.__setattr__(self, "symbol", _string(self.symbol, "symbol"))
        object.__setattr__(self, "asset_class", _string(self.asset_class, "asset_class"))
        object.__setattr__(self, "side", _string(self.side, "side"))
        object.__setattr__(self, "order_type", _string(self.order_type, "order_type"))
        object.__setattr__(
            self,
            "time_in_force",
            _string(self.time_in_force, "time_in_force"),
        )
        object.__setattr__(
            self,
            "notional",
            _optional_positive_decimal(self.notional, "notional"),
        )
        object.__setattr__(
            self,
            "max_notional",
            _optional_positive_decimal(self.max_notional, "max_notional"),
        )
        _validate_bool(self.operator_review_required, "operator_review_required", True)
        _validate_bool(
            self.separate_future_probe_milestone_required,
            "separate_future_probe_milestone_required",
            True,
        )
        for field_name in (
            "submit_allowed",
            "submitted",
            "mutated",
            "broker_action_performed",
            "broker_preview_performed",
            "paper_probe_performed",
            "live_authorized",
        ):
            _validate_bool(getattr(self, field_name), field_name, False)
        object.__setattr__(
            self,
            "labels",
            _fixed_string_tuple(
                self.labels,
                ETF_SMA_PAPER_PROBE_OPERATOR_REVIEW_LABELS,
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
            "next_action",
            _fixed_string(self.next_action, _NEXT_ACTION, "next_action"),
        )
        object.__setattr__(
            self,
            "blockers",
            _string_tuple(self.blockers, "blockers", allow_empty=True),
        )
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        _validate_review_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only review payload."""

        return {
            "review_version": self.review_version,
            "record_type": self.record_type,
            "review_status": self.review_status,
            "approved_next_action": self.approved_next_action,
            "source_m348_run_id": self.source_m348_run_id,
            "source_m349_run_id": self.source_m349_run_id,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "side": self.side,
            "order_type": self.order_type,
            "time_in_force": self.time_in_force,
            "notional": _decimal_text(self.notional),
            "max_notional": _decimal_text(self.max_notional),
            "operator_review_required": self.operator_review_required,
            "separate_future_probe_milestone_required": (
                self.separate_future_probe_milestone_required
            ),
            "submit_allowed": self.submit_allowed,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
            "paper_probe_performed": self.paper_probe_performed,
            "live_authorized": self.live_authorized,
            "labels": list(self.labels),
            "profit_claim": self.profit_claim,
            "next_action": self.next_action,
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
        }


def build_etf_sma_paper_probe_operator_review(
    m349_preview_record: Mapping[str, object],
    config: EtfSmaPaperProbeOperatorReviewConfig | None = None,
) -> EtfSmaPaperProbeOperatorReview:
    """Review local M349 evidence without broker calls or probe authority."""

    checked_record = _mapping(m349_preview_record, "m349_preview_record")
    checked_config = config or EtfSmaPaperProbeOperatorReviewConfig()
    if type(checked_config) is not EtfSmaPaperProbeOperatorReviewConfig:
        raise ValidationError("config must be an EtfSmaPaperProbeOperatorReviewConfig.")

    blockers = _review_blockers(checked_record, checked_config)
    status = _READY_STATUS if not blockers else _BLOCKED_STATUS
    notional = _decimal_or_none(checked_record.get("notional"))
    max_notional = _decimal_or_none(checked_record.get("max_notional"))
    source_m348_run_id = _m348_run_id(checked_record)

    return EtfSmaPaperProbeOperatorReview(
        review_version=_REVIEW_VERSION,
        record_type=_RECORD_TYPE,
        review_status=status,
        approved_next_action=(
            _READY_APPROVED_NEXT_ACTION
            if status == _READY_STATUS
            else _BLOCKED_APPROVED_NEXT_ACTION
        ),
        source_m348_run_id=source_m348_run_id,
        source_m349_run_id=_string_payload(checked_record.get("run_id")),
        symbol=_string_payload(checked_record.get("symbol")),
        asset_class=_string_payload(checked_record.get("asset_class")),
        side=_string_payload(checked_record.get("side")),
        order_type=_string_payload(checked_record.get("order_type")),
        time_in_force=_string_payload(checked_record.get("time_in_force")),
        notional=notional,
        max_notional=max_notional,
        operator_review_required=True,
        separate_future_probe_milestone_required=True,
        submit_allowed=False,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_preview_performed=False,
        paper_probe_performed=False,
        live_authorized=False,
        labels=ETF_SMA_PAPER_PROBE_OPERATOR_REVIEW_LABELS,
        profit_claim=_PROFIT_CLAIM,
        next_action=_NEXT_ACTION,
        blockers=tuple(blockers),
        limitations=ETF_SMA_PAPER_PROBE_OPERATOR_REVIEW_LIMITATIONS,
    )


def load_etf_sma_paper_probe_operator_review_from_jsonl(
    path: Path | str,
    *,
    source_run_id: str | None = None,
    config: EtfSmaPaperProbeOperatorReviewConfig | None = None,
) -> EtfSmaPaperProbeOperatorReview:
    """Read one local M349 JSONL record and return the deterministic review."""

    checked_path = _path(path)
    records = _jsonl_records(checked_path)
    selected_run_id = source_run_id or (config.source_m349_run_id if config else None)
    if selected_run_id is not None:
        records = tuple(
            record for record in records if record.get("run_id") == selected_run_id
        )
    if len(records) != 1:
        raise ValidationError("expected exactly one M349 preview record to review.")

    return build_etf_sma_paper_probe_operator_review(records[0], config)


def render_etf_sma_paper_probe_operator_review_json(
    review: EtfSmaPaperProbeOperatorReview,
) -> str:
    """Render one newline-free deterministic JSON object."""

    checked_review = _review(review)
    return json.dumps(
        checked_review.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )


def render_etf_sma_paper_probe_operator_review_text(
    review: EtfSmaPaperProbeOperatorReview,
) -> str:
    """Render a compact operator-readable review summary."""

    checked_review = _review(review)
    blockers = ", ".join(checked_review.blockers) if checked_review.blockers else "none"
    lines = [
        "ETF/SMA tiny SPY paper probe operator review",
        f"review_status: {checked_review.review_status}",
        f"approved_next_action: {checked_review.approved_next_action}",
        f"source_m348_run_id: {checked_review.source_m348_run_id}",
        f"source_m349_run_id: {checked_review.source_m349_run_id}",
        f"symbol: {checked_review.symbol}",
        f"asset_class: {checked_review.asset_class}",
        f"side: {checked_review.side}",
        f"notional: {_decimal_text(checked_review.notional) or 'none'}",
        f"max_notional: {_decimal_text(checked_review.max_notional) or 'none'}",
        "separate_future_probe_milestone_required: "
        f"{_bool_text(checked_review.separate_future_probe_milestone_required)}",
        f"submit_allowed: {_bool_text(checked_review.submit_allowed)}",
        f"submitted: {_bool_text(checked_review.submitted)}",
        f"mutated: {_bool_text(checked_review.mutated)}",
        "broker_action_performed: "
        f"{_bool_text(checked_review.broker_action_performed)}",
        "broker_preview_performed: "
        f"{_bool_text(checked_review.broker_preview_performed)}",
        f"paper_probe_performed: {_bool_text(checked_review.paper_probe_performed)}",
        f"live_authorized: {_bool_text(checked_review.live_authorized)}",
        f"next_action: {checked_review.next_action}",
        f"blockers: {blockers}",
    ]
    return "\n".join(lines)


def _review_blockers(
    record: Mapping[str, object],
    config: EtfSmaPaperProbeOperatorReviewConfig,
) -> tuple[str, ...]:
    blockers: list[str] = []
    prior_snapshot = _optional_mapping(record.get("prior_snapshot"))
    labels = _string_items(record.get("labels"))
    notional = _decimal_or_none(record.get("notional"))
    max_notional = _decimal_or_none(record.get("max_notional"))
    source_m348_run_id = _m348_run_id(record)

    _append_if(
        blockers,
        record.get("record_type") != _SOURCE_RECORD_TYPE,
        "m349_record_type_unexpected",
    )
    _append_if(
        blockers,
        record.get("run_id") != config.source_m349_run_id,
        "source_m349_run_id_mismatch",
    )
    _append_if(
        blockers,
        record.get("preview_status") != _SOURCE_PREVIEW_STATUS,
        "m349_preview_status_not_ready",
    )
    _append_if(
        blockers,
        record.get("next_action") != _SOURCE_NEXT_ACTION,
        "m349_next_action_unexpected",
    )
    _append_if(
        blockers,
        record.get("symbol") != _SYMBOL,
        "m349_symbol_not_spy",
    )
    _append_if(
        blockers,
        record.get("asset_class") != _ASSET_CLASS,
        "m349_asset_class_not_equity",
    )
    _append_if(blockers, record.get("side") != _SIDE, "m349_side_not_buy")
    _append_if(
        blockers,
        record.get("order_type") != _ORDER_TYPE,
        "m349_order_type_not_market",
    )
    _append_if(
        blockers,
        record.get("time_in_force") != _TIME_IN_FORCE,
        "m349_time_in_force_not_day",
    )
    _append_if(
        blockers,
        notional is None or notional <= Decimal("0"),
        "m349_notional_missing_or_invalid",
    )
    _append_if(
        blockers,
        max_notional is None or max_notional <= Decimal("0"),
        "m349_max_notional_missing_or_invalid",
    )
    if notional is not None and notional > config.max_notional:
        blockers.append("m349_notional_above_cap")
    if max_notional is not None and max_notional > config.max_notional:
        blockers.append("m349_max_notional_above_cap")
    if notional is not None and max_notional is not None and notional > max_notional:
        blockers.append("m349_notional_above_source_max_notional")
    _append_if(
        blockers,
        record.get("submit_allowed") is not False,
        "m349_submit_allowed_not_false",
    )
    _append_if(blockers, record.get("submitted") is not False, "m349_submitted_true")
    _append_if(blockers, record.get("mutated") is not False, "m349_mutated_true")
    _append_if(
        blockers,
        record.get("broker_action_performed") is not False,
        "m349_broker_action_performed_true",
    )
    _append_if(
        blockers,
        record.get("broker_preview_performed") is not False,
        "m349_broker_preview_performed_true",
    )
    _append_if(
        blockers,
        record.get("local_payload_preview_performed") is not True,
        "m349_local_payload_preview_not_performed",
    )
    _append_if(
        blockers,
        "not_live_authorized" not in labels,
        "m349_not_live_authorized_label_missing",
    )
    _append_if(
        blockers,
        "profit_claim=none" not in labels,
        "m349_profit_claim_none_label_missing",
    )
    _append_if(
        blockers,
        record.get("profit_claim") != _PROFIT_CLAIM,
        "m349_profit_claim_not_none",
    )
    _append_if(
        blockers,
        _contains_forbidden_live_authorization(record),
        "live_authorized_evidence_present",
    )
    _append_if(
        blockers,
        _contains_non_none_profit_claim(record),
        "non_none_profit_claim_present",
    )

    if prior_snapshot is None:
        blockers.append("m348_prior_snapshot_missing")
    else:
        blockers.extend(
            _m348_snapshot_blockers(record, prior_snapshot, source_m348_run_id, config)
        )
    blockers.extend(_broker_payload_blockers(record.get("broker_payload_preview")))

    return tuple(dict.fromkeys(blockers))


def _m348_snapshot_blockers(
    record: Mapping[str, object],
    prior_snapshot: Mapping[str, object],
    source_m348_run_id: str,
    config: EtfSmaPaperProbeOperatorReviewConfig,
) -> tuple[str, ...]:
    blockers: list[str] = []
    top_position_count = _int_or_none(record.get("prior_snapshot_position_count"))
    nested_position_count = _int_or_none(prior_snapshot.get("position_count"))
    top_order_count = _int_or_none(record.get("prior_snapshot_recent_open_order_count"))
    nested_order_count = _int_or_none(prior_snapshot.get("recent_open_order_count"))
    top_metadata_complete = record.get(
        "prior_snapshot_recent_order_query_metadata_complete"
    )
    nested_metadata_complete = prior_snapshot.get(
        "recent_order_query_metadata_complete"
    )
    position_symbols = _string_items(prior_snapshot.get("position_symbols"))

    _append_if(
        blockers,
        source_m348_run_id != config.source_m348_run_id,
        "source_m348_run_id_mismatch",
    )
    _append_if(
        blockers,
        record.get("prior_snapshot_revalidation_state") != _USABLE_REVALIDATION_STATE,
        "m348_revalidation_state_not_usable",
    )
    _append_if(
        blockers,
        prior_snapshot.get("prior_snapshot_revalidation_state")
        != _USABLE_REVALIDATION_STATE,
        "m348_nested_revalidation_state_not_usable",
    )
    _append_if(
        blockers,
        prior_snapshot.get("fresh_snapshot_status") != _SNAPSHOT_STATUS,
        "m348_fresh_snapshot_status_not_ready",
    )
    _append_if(
        blockers,
        prior_snapshot.get("usable_for_manual_review") is not True,
        "m348_not_usable_for_manual_review",
    )
    _append_if(
        blockers,
        prior_snapshot.get("snapshot_records_observed") is not True,
        "m348_snapshot_records_not_observed",
    )
    _append_if(
        blockers,
        prior_snapshot.get("account_observation_available") is not True,
        "m348_account_observation_missing",
    )
    _append_if(
        blockers,
        prior_snapshot.get("positions_observation_available") is not True,
        "m348_positions_observation_missing",
    )
    _append_if(
        blockers,
        prior_snapshot.get("orders_observation_available") is not True,
        "m348_orders_observation_missing",
    )
    _append_if(
        blockers,
        prior_snapshot.get("submitted") is not False,
        "m348_submitted_true",
    )
    _append_if(blockers, prior_snapshot.get("mutated") is not False, "m348_mutated_true")
    _append_if(
        blockers,
        top_position_count is None or nested_position_count is None,
        "m348_position_count_missing_or_invalid",
    )
    if top_position_count is not None and nested_position_count is not None:
        _append_if(
            blockers,
            top_position_count != nested_position_count,
            "m348_position_count_ambiguous",
        )
        _append_if(
            blockers,
            top_position_count != 0 or nested_position_count != 0 or bool(position_symbols),
            "m348_unexpected_positions",
        )
    _append_if(
        blockers,
        top_order_count is None or nested_order_count is None,
        "m348_recent_open_order_count_missing_or_invalid",
    )
    if top_order_count is not None and nested_order_count is not None:
        _append_if(
            blockers,
            top_order_count != nested_order_count,
            "m348_recent_open_order_count_ambiguous",
        )
        _append_if(
            blockers,
            top_order_count != 0 or nested_order_count != 0,
            "m348_recent_open_orders_present",
        )
    _append_if(
        blockers,
        top_metadata_complete is not True or nested_metadata_complete is not True,
        "m348_recent_order_metadata_incomplete",
    )
    _append_if(
        blockers,
        bool(_string_items(prior_snapshot.get("unavailable_observations"))),
        "m348_unavailable_observations_present",
    )
    _append_if(
        blockers,
        prior_snapshot.get("credentials_redacted_present") is not True,
        "m348_missing_credential_redaction",
    )
    _append_if(
        blockers,
        prior_snapshot.get("live_profile_evidence") is not False,
        "m348_live_profile_evidence_present",
    )
    _append_if(
        blockers,
        prior_snapshot.get("credential_leak_evidence") is not False,
        "m348_credential_leak_evidence_present",
    )

    return tuple(blockers)


def _broker_payload_blockers(value: object) -> tuple[str, ...]:
    payload = _optional_mapping(value)
    if payload is None:
        return ("m349_broker_payload_preview_missing",)

    blockers: list[str] = []
    _append_if(blockers, payload.get("symbol") != _SYMBOL, "payload_symbol_not_spy")
    _append_if(
        blockers,
        payload.get("asset_class") != _ASSET_CLASS,
        "payload_asset_class_not_equity",
    )
    _append_if(blockers, payload.get("side") != _SIDE, "payload_side_not_buy")
    _append_if(
        blockers,
        payload.get("order_type") != _ORDER_TYPE,
        "payload_order_type_not_market",
    )
    _append_if(
        blockers,
        payload.get("time_in_force") != _TIME_IN_FORCE,
        "payload_time_in_force_not_day",
    )
    notional = _decimal_or_none(payload.get("notional"))
    _append_if(
        blockers,
        notional is None or notional <= Decimal("0") or notional > _MAX_NOTIONAL_CAP,
        "payload_notional_invalid",
    )
    return tuple(blockers)


def _m348_run_id(record: Mapping[str, object]) -> str:
    prior_snapshot = _optional_mapping(record.get("prior_snapshot"))
    top_level = _string_payload(record.get("prior_snapshot_run_id"))
    nested = (
        _string_payload(prior_snapshot.get("prior_snapshot_run_id"))
        if prior_snapshot is not None
        else ""
    )
    return top_level or nested


def _jsonl_records(path: Path) -> tuple[Mapping[str, object], ...]:
    if not path.exists() or not path.is_file():
        raise ValidationError("M349 preview run log must be an existing file.")

    records: list[Mapping[str, object]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError("M349 preview run log contains invalid JSON.") from exc
        records.append(_mapping(payload, "M349 preview JSONL record"))
    return tuple(records)


def _path(value: object) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError("path must be a path string.")
    if str(path).strip() == "":
        raise ValidationError("path is required.")
    return path


def _review(value: object) -> EtfSmaPaperProbeOperatorReview:
    if type(value) is not EtfSmaPaperProbeOperatorReview:
        raise ValidationError("review must be an EtfSmaPaperProbeOperatorReview.")
    return value


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _optional_mapping(value: object) -> Mapping[str, object] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return value
    return None


def _review_status(value: object) -> str:
    if value not in (_READY_STATUS, _BLOCKED_STATUS):
        raise ValidationError("review_status is invalid.")
    return str(value)


def _approved_next_action(value: object, status: str) -> str:
    expected = (
        _READY_APPROVED_NEXT_ACTION
        if status == _READY_STATUS
        else _BLOCKED_APPROVED_NEXT_ACTION
    )
    return _fixed_string(value, expected, "approved_next_action")


def _validate_review_consistency(review: EtfSmaPaperProbeOperatorReview) -> None:
    if review.review_status == _READY_STATUS and review.blockers:
        raise ValidationError("ready review must not contain blockers.")
    if review.review_status == _BLOCKED_STATUS and not review.blockers:
        raise ValidationError("blocked review must contain blockers.")
    if review.review_status == _READY_STATUS:
        if review.source_m348_run_id != _SOURCE_M348_RUN_ID:
            raise ValidationError("ready review requires the M348 source run id.")
        if review.source_m349_run_id != _SOURCE_M349_RUN_ID:
            raise ValidationError("ready review requires the M349 source run id.")
        if review.symbol != _SYMBOL:
            raise ValidationError("ready review requires SPY.")
        if review.asset_class != _ASSET_CLASS:
            raise ValidationError("ready review requires equity asset_class.")
        if review.side != _SIDE:
            raise ValidationError("ready review requires buy side.")
        if review.order_type != _ORDER_TYPE or review.time_in_force != _TIME_IN_FORCE:
            raise ValidationError("ready review requires market/day payload.")
        if review.notional is None or review.max_notional is None:
            raise ValidationError("ready review requires notional fields.")


def _validate_bool(value: object, field_name: str, expected: bool) -> None:
    if value is not expected:
        raise ValidationError(f"{field_name} must be {str(expected).lower()}.")


def _fixed_string(value: object, expected: str, field_name: str) -> str:
    if type(value) is not str or value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")
    return value


def _non_empty_string(value: object, field_name: str) -> str:
    if type(value) is not str or value.strip() == "":
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    return value


def _string_payload(value: object) -> str:
    return value if type(value) is str else ""


def _string_tuple(
    values: object,
    field_name: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")
    items = tuple(_non_empty_string(item, field_name) for item in values)
    if not items and not allow_empty:
        raise ValidationError(f"{field_name} must not be empty.")
    return items


def _fixed_string_tuple(
    values: object,
    expected: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    items = _string_tuple(values, field_name)
    if _contains_forbidden_live_authorization(items):
        raise ValidationError(f"{field_name} contains live authorization.")
    if items != expected:
        raise ValidationError(f"{field_name} must match the required values.")
    return items


def _string_items(values: object) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        return ()
    return tuple(value for value in values if type(value) is str)


def _int_or_none(value: object) -> int | None:
    if type(value) is int:
        return value
    return None


def _positive_capped_notional(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal or not value.is_finite():
        raise ValidationError(f"{field_name} must be a positive Decimal.")
    if value <= Decimal("0") or value > _MAX_NOTIONAL_CAP:
        raise ValidationError(f"{field_name} must be between 0 and 25.00.")
    return value


def _optional_positive_capped_notional(
    value: object,
    field_name: str,
) -> Decimal | None:
    if value is None:
        return None
    return _positive_capped_notional(value, field_name)


def _optional_positive_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if type(value) is not Decimal or not value.is_finite() or value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be a positive Decimal.")
    return value


def _decimal_or_none(value: object) -> Decimal | None:
    if type(value) is Decimal:
        candidate = value
    elif type(value) is str:
        try:
            candidate = Decimal(value)
        except InvalidOperation:
            return None
    else:
        return None
    if not candidate.is_finite():
        return None
    return candidate


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _append_if(blockers: list[str], condition: bool, blocker: str) -> None:
    if condition:
        blockers.append(blocker)


def _contains_forbidden_live_authorization(value: object) -> bool:
    for item in _walk(value):
        if type(item) is str and item.lower() in _FORBIDDEN_LIVE_AUTHORIZATION_VALUES:
            return True
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "live_authorized" and item is True:
                return True
    return False


def _contains_non_none_profit_claim(value: object) -> bool:
    for key, item in _walk_mapping_items(value):
        if key == "profit_claim" and item != _PROFIT_CLAIM:
            return True
    for item in _walk(value):
        if type(item) is str and item.startswith("profit_claim="):
            if item != "profit_claim=none":
                return True
    return False


def _walk(value: object) -> tuple[object, ...]:
    items: list[object] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            items.append(key)
            items.extend(_walk(item))
    elif type(value) in (list, tuple):
        for item in value:
            items.extend(_walk(item))
    else:
        items.append(value)
    return tuple(items)


def _walk_mapping_items(value: object) -> tuple[tuple[str, object], ...]:
    items: list[tuple[str, object]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is str:
                items.append((key, item))
            items.extend(_walk_mapping_items(item))
    elif type(value) in (list, tuple):
        for item in value:
            items.extend(_walk_mapping_items(item))
    return tuple(items)
