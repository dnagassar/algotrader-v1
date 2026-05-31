"""Asset-class policy matrix for guarded paper order probes."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


ASSET_CLASS_EQUITY = "equity"
ASSET_CLASS_CRYPTO = "crypto"
ASSET_CLASS_OPTION = "option"
ASSET_CLASS_CHOICES = (
    ASSET_CLASS_EQUITY,
    ASSET_CLASS_CRYPTO,
    ASSET_CLASS_OPTION,
)

PAPER_MARKET_SESSION_NOTE = (
    "Market DAY equity orders submitted after hours may be accepted or queued "
    "by the broker and may not fill until the next regular session."
)
PAPER_ORDER_PROBE_QTY_DISABLED_REASON = (
    "qty_submission_disabled_until_quote_based_cap_is_supported"
)
PAPER_CRYPTO_SESSION_NOTE = (
    "Crypto paper observations are a shared broker-path harness only and do "
    "not prove equity behavior."
)
PAPER_CRYPTO_BTCUSD_MIN_NOTIONAL = Decimal("10.00")
OPTIONS_SUBMIT_DISABLED_REASON = (
    "options_submit_disabled_until_options_risk_contract_exists"
)
PAPER_CLOSE_PREVIEW_CONTRACT_VERSION = "paper_close_preview_v1"
PAPER_CLOSE_PREVIEW_SUBMISSION_DISABLED_REASON = (
    "close_preview_submission_disabled_design_only"
)
PAPER_CLOSE_PREVIEW_REQUIRED_SNAPSHOT_STATUS = (
    "read_only_snapshot_completed_for_manual_review"
)
PAPER_CLOSE_PREVIEW_RECOMMENDED_ACTION = (
    "manual_review_close_preview_design_before_any_broker_action"
)
PAPER_CLOSE_PREVIEW_REPAIR_ACTION = (
    "collect_fresh_read_only_snapshot_before_close_preview_design"
)
PAPER_CLOSE_PREVIEW_ADJUST_QUANTITY_ACTION = (
    "adjust_close_quantity_within_observed_position_before_manual_review"
)
PAPER_CLOSE_PREVIEW_GATE_ORDER = (
    "asset_class_gate",
    "symbol_gate",
    "side_gate",
    "order_type_gate",
    "time_in_force_gate",
    "fresh_snapshot_gate",
    "observed_position_gate",
    "quantity_gate",
    "close_quantity_within_observed_position_gate",
    "no_shorting_gate",
    "recent_order_query_metadata_gate",
    "source_mutation_gate",
    "source_submission_gate",
    "submit_disabled_gate",
    "manual_review_gate",
)


@dataclass(frozen=True)
class PaperOrderPolicy:
    asset_class: str
    symbol_allowlist: tuple[str, ...] | None
    allowed_sizing_modes: tuple[str, ...]
    time_in_force: str
    submit_enabled: bool
    submit_disabled_reason: str
    max_notional_cap: Decimal | None = None
    min_notional: Decimal | None = None
    required_qty: Decimal | None = None
    market_session_note: str = ""

    def allows_symbol(self, symbol: str) -> bool:
        normalized_symbol = symbol.strip().upper()
        if self.symbol_allowlist is None:
            return bool(normalized_symbol)

        return normalized_symbol in self.symbol_allowlist

    def allowlist_detail(self, symbol: str) -> str:
        normalized_symbol = symbol.strip().upper()
        if self.symbol_allowlist is None:
            return f"symbol={normalized_symbol} explicit_contract_symbol"

        return (
            f"symbol={normalized_symbol} "
            f"allowlist={','.join(self.symbol_allowlist)}"
        )

    def sizing_failure_detail(self) -> str:
        if self.asset_class == ASSET_CLASS_CRYPTO:
            return "crypto_notional_required"
        if self.asset_class == ASSET_CLASS_OPTION:
            return "option_qty_1_contract_required"

        return "exactly_one_of_qty_or_notional_required"

    def quantity_detail(self, sizing_mode: str = "qty") -> str:
        if self.asset_class == ASSET_CLASS_CRYPTO and sizing_mode == "notional":
            return "not_applicable_for_notional"
        if self.required_qty is not None:
            return f"qty={self.required_qty}_contract_only"

        return "positive_whole_share_quantity"

    def quantity_failure_detail(self, quantity_error: str) -> str:
        if quantity_error:
            return quantity_error
        if self.required_qty is not None:
            return f"qty_must_equal_{self.required_qty}_contract"

        return "invalid_quantity"

    def notional_cap_detail(self) -> str:
        if self.max_notional_cap is None:
            return "max_notional_not_applicable"

        return f"max_notional_cap={self.max_notional_cap}"

    def notional_minimum_detail(self) -> str:
        if self.min_notional is None:
            return "min_notional_not_applicable"

        return f"min_notional={self.min_notional}"

    def notional_minimum_failure_detail(self) -> str:
        if self.asset_class == ASSET_CLASS_CRYPTO:
            return "notional_below_crypto_min_notional"

        return "notional_below_min_notional"


@dataclass(frozen=True)
class PaperClosePreviewGate:
    name: str
    passed: bool
    detail: str

    def to_payload(self) -> dict[str, object]:
        return {"detail": self.detail, "passed": self.passed}


@dataclass(frozen=True)
class PaperClosePreviewContract:
    command: str
    ok: bool
    asset_class: str
    symbol: str
    side: str
    order_type: str
    time_in_force: str
    observed_position_quantity: Decimal | None
    requested_close_quantity: Decimal | None
    remaining_quantity_after_preview: Decimal | None
    fresh_snapshot_status: str
    recent_order_query_metadata_complete: bool
    mutated: bool | None
    submitted: bool | None
    gates: tuple[PaperClosePreviewGate, ...]
    recommended_next_operator_action: str
    limitations: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        gate_payload = {gate.name: gate.to_payload() for gate in self.gates}
        close_quantity_gate = gate_payload[
            "close_quantity_within_observed_position_gate"
        ]
        no_shorting_gate = gate_payload["no_shorting_gate"]
        return {
            "asset_class": self.asset_class,
            "close_preview_status": (
                "design_ready_manual_review_only"
                if self.ok
                else "blocked_manual_review_only"
            ),
            "close_quantity_within_observed_position": bool(
                close_quantity_gate["passed"]
            ),
            "command": self.command,
            "fresh_snapshot_required": True,
            "fresh_snapshot_status": self.fresh_snapshot_status,
            "gates": gate_payload,
            "manual_review_required": True,
            "mutated": self.mutated,
            "no_shorting_gate": _gate_status(no_shorting_gate),
            "not_live_authorized": True,
            "observed_position_quantity": _decimal_payload_text(
                self.observed_position_quantity
            ),
            "ok": self.ok,
            "order_type": self.order_type,
            "paper_close_preview_contract_version": (
                PAPER_CLOSE_PREVIEW_CONTRACT_VERSION
            ),
            "paper_lab_only": True,
            "preview_only": True,
            "profit_claim": "none",
            "recent_order_query_metadata_complete": (
                self.recent_order_query_metadata_complete
            ),
            "recommended_next_operator_action": (
                self.recommended_next_operator_action
            ),
            "remaining_quantity_after_preview": _decimal_payload_text(
                self.remaining_quantity_after_preview
            ),
            "requested_close_quantity": _decimal_payload_text(
                self.requested_close_quantity
            ),
            "side": self.side,
            "submission_disabled_reason": (
                PAPER_CLOSE_PREVIEW_SUBMISSION_DISABLED_REASON
            ),
            "submitted": self.submitted,
            "symbol": self.symbol,
            "time_in_force": self.time_in_force,
            "limitations": list(self.limitations),
        }


_POLICIES = {
    ASSET_CLASS_EQUITY: PaperOrderPolicy(
        asset_class=ASSET_CLASS_EQUITY,
        symbol_allowlist=("SPY",),
        allowed_sizing_modes=("qty", "notional"),
        max_notional_cap=Decimal("10"),
        time_in_force="day",
        submit_enabled=True,
        submit_disabled_reason="",
        market_session_note=PAPER_MARKET_SESSION_NOTE,
    ),
    ASSET_CLASS_CRYPTO: PaperOrderPolicy(
        asset_class=ASSET_CLASS_CRYPTO,
        symbol_allowlist=("BTCUSD",),
        allowed_sizing_modes=("notional",),
        max_notional_cap=Decimal("10.00"),
        min_notional=PAPER_CRYPTO_BTCUSD_MIN_NOTIONAL,
        time_in_force="gtc",
        submit_enabled=True,
        submit_disabled_reason="",
        market_session_note=PAPER_CRYPTO_SESSION_NOTE,
    ),
    ASSET_CLASS_OPTION: PaperOrderPolicy(
        asset_class=ASSET_CLASS_OPTION,
        symbol_allowlist=None,
        allowed_sizing_modes=("qty",),
        time_in_force="day",
        submit_enabled=False,
        submit_disabled_reason=OPTIONS_SUBMIT_DISABLED_REASON,
        required_qty=Decimal("1"),
    ),
}


def build_btcusd_paper_close_preview_contract(
    *,
    observed_position_quantity: Decimal | str | None,
    requested_close_quantity: Decimal | str | None,
    fresh_snapshot_status: str,
    recent_order_query_metadata_complete: bool,
    source_mutated: bool | None,
    source_submitted: bool | None,
    asset_class: str = ASSET_CLASS_CRYPTO,
    symbol: str = "BTCUSD",
    side: str = "sell",
    order_type: str = "market",
    time_in_force: str | None = None,
    command: str = "paper-close-preview",
) -> PaperClosePreviewContract:
    """Build a local BTCUSD close/exit preview contract without broker action."""

    crypto_policy = paper_order_policy_for_asset_class(ASSET_CLASS_CRYPTO)
    normalized_asset_class = str(asset_class).strip().lower()
    normalized_symbol = str(symbol).strip().upper()
    normalized_side = str(side).strip().lower()
    normalized_order_type = str(order_type).strip().lower()
    normalized_time_in_force = str(
        crypto_policy.time_in_force if time_in_force is None else time_in_force
    ).strip().lower()
    requested_quantity, requested_quantity_error = _positive_decimal_value(
        requested_close_quantity,
        "requested_close_quantity",
    )
    observed_quantity, observed_quantity_error = _positive_decimal_value(
        observed_position_quantity,
        "observed_position_quantity",
    )
    within_observed_position = (
        observed_quantity is not None
        and requested_quantity is not None
        and requested_quantity <= observed_quantity
    )
    remaining_quantity = (
        observed_quantity - requested_quantity
        if within_observed_position
        else None
    )
    gates = tuple(
        [
            _close_preview_gate(
                "asset_class_gate",
                normalized_asset_class == ASSET_CLASS_CRYPTO,
                ASSET_CLASS_CRYPTO,
                "asset_class_must_be_crypto",
            ),
            _close_preview_gate(
                "symbol_gate",
                normalized_symbol == "BTCUSD",
                "symbol=BTCUSD",
                "symbol_must_be_BTCUSD",
            ),
            _close_preview_gate(
                "side_gate",
                normalized_side == "sell",
                "sell_only_close_preview",
                "side_must_be_sell",
            ),
            _close_preview_gate(
                "order_type_gate",
                normalized_order_type == "market",
                "market",
                "order_type_must_be_market",
            ),
            _close_preview_gate(
                "time_in_force_gate",
                normalized_time_in_force == crypto_policy.time_in_force,
                crypto_policy.time_in_force,
                f"time_in_force_must_be_{crypto_policy.time_in_force}",
            ),
            _close_preview_gate(
                "fresh_snapshot_gate",
                fresh_snapshot_status
                == PAPER_CLOSE_PREVIEW_REQUIRED_SNAPSHOT_STATUS,
                PAPER_CLOSE_PREVIEW_REQUIRED_SNAPSHOT_STATUS,
                "fresh_read_only_snapshot_required",
            ),
            _close_preview_gate(
                "observed_position_gate",
                observed_quantity is not None,
                "observed_BTCUSD_position_quantity_positive",
                observed_quantity_error or "observed_BTCUSD_position_required",
            ),
            _close_preview_gate(
                "quantity_gate",
                requested_quantity is not None,
                "requested_close_quantity_positive",
                requested_quantity_error or "requested_close_quantity_required",
            ),
            _close_preview_gate(
                "close_quantity_within_observed_position_gate",
                within_observed_position,
                "requested_close_quantity_within_observed_position",
                "requested_close_quantity_exceeds_observed_position",
            ),
            _close_preview_gate(
                "no_shorting_gate",
                within_observed_position,
                "no_shorting_requested",
                "requested_close_quantity_would_short_BTCUSD",
            ),
            _close_preview_gate(
                "recent_order_query_metadata_gate",
                recent_order_query_metadata_complete is True,
                "recent_order_query_metadata_complete",
                "recent_order_query_metadata_must_be_complete",
            ),
            _close_preview_gate(
                "source_mutation_gate",
                source_mutated is False,
                "mutated_false",
                "source_snapshot_mutated_must_be_false",
            ),
            _close_preview_gate(
                "source_submission_gate",
                source_submitted is False,
                "submitted_false",
                "source_snapshot_submitted_must_be_false",
            ),
            _close_preview_gate(
                "submit_disabled_gate",
                True,
                PAPER_CLOSE_PREVIEW_SUBMISSION_DISABLED_REASON,
                "",
            ),
            _close_preview_gate(
                "manual_review_gate",
                True,
                "manual_review_required",
                "",
            ),
        ]
    )
    ok = all(gate.passed for gate in gates)
    failed_gate_names = tuple(gate.name for gate in gates if not gate.passed)
    return PaperClosePreviewContract(
        command=command,
        ok=ok,
        asset_class=normalized_asset_class,
        symbol=normalized_symbol,
        side=normalized_side,
        order_type=normalized_order_type,
        time_in_force=normalized_time_in_force,
        observed_position_quantity=observed_quantity,
        requested_close_quantity=requested_quantity,
        remaining_quantity_after_preview=remaining_quantity,
        fresh_snapshot_status=str(fresh_snapshot_status),
        recent_order_query_metadata_complete=(
            recent_order_query_metadata_complete is True
        ),
        mutated=source_mutated,
        submitted=source_submitted,
        gates=gates,
        recommended_next_operator_action=_close_preview_action(
            failed_gate_names
        ),
        limitations=_close_preview_limitations(gates),
    )


def paper_order_policy_for_asset_class(asset_class: str) -> PaperOrderPolicy:
    normalized_asset_class = asset_class.strip().lower()
    try:
        return _POLICIES[normalized_asset_class]
    except KeyError:
        expected = ", ".join(ASSET_CLASS_CHOICES)
        raise ValueError(
            f"unsupported paper order asset_class: {asset_class!r}; "
            f"expected one of {expected}"
        ) from None


def _close_preview_gate(
    name: str,
    passed: bool,
    detail: str,
    failure_detail: str,
) -> PaperClosePreviewGate:
    return PaperClosePreviewGate(
        name=name,
        passed=bool(passed),
        detail=detail if passed else failure_detail,
    )


def _positive_decimal_value(
    raw_value: Decimal | str | None,
    field_name: str,
) -> tuple[Decimal | None, str]:
    if raw_value in (None, ""):
        return None, f"{field_name}_required"
    try:
        value = raw_value if isinstance(raw_value, Decimal) else Decimal(str(raw_value))
    except (InvalidOperation, ValueError):
        return None, f"{field_name}_must_be_decimal"

    if value <= 0:
        return None, f"{field_name}_must_be_positive"

    return value, ""


def _decimal_payload_text(value: Decimal | None) -> str:
    if value is None:
        return ""
    if value == 0:
        return "0"

    return format(value.normalize(), "f")


def _gate_status(gate_payload: dict[str, object]) -> str:
    return "passed" if gate_payload["passed"] else "failed"


def _close_preview_action(failed_gate_names: tuple[str, ...]) -> str:
    if not failed_gate_names:
        return PAPER_CLOSE_PREVIEW_RECOMMENDED_ACTION
    if failed_gate_names[0] in {
        "quantity_gate",
        "close_quantity_within_observed_position_gate",
        "no_shorting_gate",
    }:
        return PAPER_CLOSE_PREVIEW_ADJUST_QUANTITY_ACTION

    return PAPER_CLOSE_PREVIEW_REPAIR_ACTION


def _close_preview_limitations(
    gates: tuple[PaperClosePreviewGate, ...],
) -> tuple[str, ...]:
    limitations = tuple(
        gate.detail
        for gate in gates
        if not gate.passed
        and gate.name not in {"submit_disabled_gate", "manual_review_gate"}
    )
    if limitations:
        return limitations

    return ("preview-only design contract; no broker order is submitted",)


__all__ = [
    "ASSET_CLASS_CHOICES",
    "ASSET_CLASS_CRYPTO",
    "ASSET_CLASS_EQUITY",
    "ASSET_CLASS_OPTION",
    "OPTIONS_SUBMIT_DISABLED_REASON",
    "PAPER_CLOSE_PREVIEW_CONTRACT_VERSION",
    "PAPER_CLOSE_PREVIEW_GATE_ORDER",
    "PAPER_CLOSE_PREVIEW_RECOMMENDED_ACTION",
    "PAPER_CLOSE_PREVIEW_REQUIRED_SNAPSHOT_STATUS",
    "PAPER_CLOSE_PREVIEW_SUBMISSION_DISABLED_REASON",
    "PAPER_CRYPTO_BTCUSD_MIN_NOTIONAL",
    "PAPER_CRYPTO_SESSION_NOTE",
    "PAPER_MARKET_SESSION_NOTE",
    "PAPER_ORDER_PROBE_QTY_DISABLED_REASON",
    "PaperClosePreviewContract",
    "PaperClosePreviewGate",
    "PaperOrderPolicy",
    "build_btcusd_paper_close_preview_contract",
    "paper_order_policy_for_asset_class",
]
