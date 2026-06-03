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
PAPER_SPY_CLOSE_PREVIEW_REQUIRED_OBSERVATION_STATUS = (
    "fresh_read_only_spy_position_observation_completed"
)
PAPER_SPY_CLOSE_PREVIEW_RECOMMENDED_ACTION = (
    "review_m354_close_preview_then_scope_m355_explicit_close_submit_if_approved"
)
PAPER_SPY_CLOSE_PREVIEW_REPAIR_ACTION = (
    "resolve_spy_close_preview_blockers_before_m355"
)
PAPER_SPY_CLOSE_PREVIEW_OPERATOR_INSTRUCTION = (
    "Review only. Do not submit in M354. Use M355 for explicit close submit if "
    "approved."
)
PAPER_SPY_CLOSE_SUBMIT_CONTRACT_VERSION = "paper_spy_close_submit_v1"
PAPER_SPY_CLOSE_SUBMIT_CLIENT_ORDER_ID = (
    "paper-order-close-m355_spy_paper_close_submit"
)
PAPER_SPY_CLOSE_SUBMIT_EXPECTED_QUANTITY = Decimal("0.032905647")
PAPER_SPY_CLOSE_SUBMIT_READY_M354_STATE = (
    "ready_for_separate_spy_close_submit_milestone"
)
PAPER_SPY_CLOSE_SUBMIT_READY_STATE = "ready_for_single_spy_paper_close_submit"
PAPER_SPY_CLOSE_SUBMIT_BLOCKED_STATE = "blocked_from_spy_paper_close_submit"
PAPER_SPY_CLOSE_SUBMIT_GATE_ORDER = (
    "profile_gate",
    "halt_gate",
    "submit_confirmation_gate",
    "m354_state_gate",
    "m354_ok_gate",
    "m354_no_submission_gate",
    "m354_no_mutation_gate",
    "m354_no_broker_action_gate",
    "m354_not_live_gate",
    "m354_requested_quantity_gate",
    "asset_class_gate",
    "allowlist_gate",
    "symbol_gate",
    "side_gate",
    "order_type_gate",
    "time_in_force_gate",
    "client_order_id_gate",
    "quantity_gate",
    "account_observation_gate",
    "positions_observation_gate",
    "orders_observation_gate",
    "observed_position_gate",
    "observed_position_quantity_gate",
    "close_quantity_within_observed_position_gate",
    "no_shorting_gate",
    "recent_order_query_metadata_gate",
    "recent_open_order_gate",
    "duplicate_client_order_id_gate",
    "unexpected_position_gate",
    "unavailable_observation_gate",
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
            "broker_action_performed": False,
            "close_order_submitted": False,
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
            "max_quantity": _decimal_payload_text(self.observed_position_quantity),
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
            "quantity": _decimal_payload_text(self.requested_close_quantity),
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


@dataclass(frozen=True)
class PaperSpyCloseSubmitContract:
    ok: bool
    asset_class: str
    symbol: str
    side: str
    order_type: str
    time_in_force: str
    client_order_id: str
    requested_close_quantity: Decimal | None
    observed_position_quantity: Decimal | None
    remaining_quantity_after_submit: Decimal | None
    gates: tuple[PaperClosePreviewGate, ...]

    def to_payload(self) -> dict[str, object]:
        gate_payload = {gate.name: gate.to_payload() for gate in self.gates}
        close_quantity_gate = gate_payload[
            "close_quantity_within_observed_position_gate"
        ]
        no_shorting_gate = gate_payload["no_shorting_gate"]
        return {
            "asset_class": self.asset_class,
            "broker_action_performed": False,
            "client_order_id": self.client_order_id,
            "close_order_submitted": False,
            "close_quantity_within_observed_position": bool(
                close_quantity_gate["passed"]
            ),
            "command": "paper-lab-spy-close-submit",
            "gates": gate_payload,
            "live_authorized": False,
            "mutated": False,
            "no_shorting_gate": _gate_status(no_shorting_gate),
            "observed_position_quantity": _decimal_payload_text(
                self.observed_position_quantity
            ),
            "ok": self.ok,
            "order_type": self.order_type,
            "paper_lab_only": True,
            "paper_only": True,
            "paper_spy_close_submit_contract_version": (
                PAPER_SPY_CLOSE_SUBMIT_CONTRACT_VERSION
            ),
            "preview_only": not self.ok,
            "profit_claim": "none",
            "quantity": _decimal_payload_text(self.requested_close_quantity),
            "remaining_quantity_after_submit": _decimal_payload_text(
                self.remaining_quantity_after_submit
            ),
            "requested_close_quantity": _decimal_payload_text(
                self.requested_close_quantity
            ),
            "side": self.side,
            "state": (
                PAPER_SPY_CLOSE_SUBMIT_READY_STATE
                if self.ok
                else PAPER_SPY_CLOSE_SUBMIT_BLOCKED_STATE
            ),
            "submitted": False,
            "symbol": self.symbol,
            "time_in_force": self.time_in_force,
        }


_POLICIES = {
    ASSET_CLASS_EQUITY: PaperOrderPolicy(
        asset_class=ASSET_CLASS_EQUITY,
        symbol_allowlist=("SPY",),
        allowed_sizing_modes=("qty", "notional"),
        max_notional_cap=Decimal("25.00"),
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


def build_spy_paper_close_preview_contract(
    *,
    observed_position_quantity: Decimal | str | None,
    requested_close_quantity: Decimal | str | None,
    fresh_observation_status: str,
    recent_order_query_metadata_complete: bool,
    source_mutated: bool | None,
    source_submitted: bool | None,
    source_traceability_ready: bool,
    recent_open_order_count: int | None,
    unexpected_position_symbols: tuple[str, ...] = (),
    unavailable_observations: tuple[str, ...] = (),
    asset_class: str = ASSET_CLASS_EQUITY,
    symbol: str = "SPY",
    side: str = "sell",
    order_type: str = "market",
    time_in_force: str | None = None,
    command: str = "paper-lab-spy-close-preview",
) -> PaperClosePreviewContract:
    """Build a local SPY close/cleanup preview contract without broker action."""

    equity_policy = paper_order_policy_for_asset_class(ASSET_CLASS_EQUITY)
    normalized_asset_class = str(asset_class).strip().lower()
    normalized_symbol = str(symbol).strip().upper()
    normalized_side = str(side).strip().lower()
    normalized_order_type = str(order_type).strip().lower()
    normalized_time_in_force = str(
        equity_policy.time_in_force if time_in_force is None else time_in_force
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
    open_order_count_zero = recent_open_order_count == 0
    gates = tuple(
        [
            _close_preview_gate(
                "asset_class_gate",
                normalized_asset_class == ASSET_CLASS_EQUITY,
                ASSET_CLASS_EQUITY,
                "asset_class_must_be_equity",
            ),
            _close_preview_gate(
                "allowlist_gate",
                equity_policy.allows_symbol(normalized_symbol),
                equity_policy.allowlist_detail(normalized_symbol),
                "symbol_not_in_SPY_allowlist",
            ),
            _close_preview_gate(
                "symbol_gate",
                normalized_symbol == "SPY",
                "symbol=SPY",
                "symbol_must_be_SPY",
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
                normalized_time_in_force == equity_policy.time_in_force,
                equity_policy.time_in_force,
                f"time_in_force_must_be_{equity_policy.time_in_force}",
            ),
            _close_preview_gate(
                "fresh_observation_gate",
                fresh_observation_status
                == PAPER_SPY_CLOSE_PREVIEW_REQUIRED_OBSERVATION_STATUS,
                PAPER_SPY_CLOSE_PREVIEW_REQUIRED_OBSERVATION_STATUS,
                "fresh_read_only_spy_observation_required",
            ),
            _close_preview_gate(
                "source_traceability_gate",
                source_traceability_ready is True,
                "m353_traceability_ready",
                "m353_traceability_must_be_ready",
            ),
            _close_preview_gate(
                "observed_position_gate",
                observed_quantity is not None,
                "observed_SPY_position_quantity_positive",
                observed_quantity_error or "observed_SPY_position_required",
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
                "requested_close_quantity_would_short_SPY",
            ),
            _close_preview_gate(
                "recent_order_query_metadata_gate",
                recent_order_query_metadata_complete is True,
                "recent_order_query_metadata_complete",
                "recent_order_query_metadata_must_be_complete",
            ),
            _close_preview_gate(
                "recent_open_order_gate",
                open_order_count_zero,
                "recent_open_spy_order_count_zero",
                "recent_open_spy_orders_must_be_zero",
            ),
            _close_preview_gate(
                "unexpected_position_gate",
                not unexpected_position_symbols,
                "only_SPY_position_observed",
                "unexpected_non_SPY_positions_observed",
            ),
            _close_preview_gate(
                "unavailable_observation_gate",
                not unavailable_observations,
                "account_positions_and_orders_available",
                "required_observations_unavailable",
            ),
            _close_preview_gate(
                "source_mutation_gate",
                source_mutated is False,
                "mutated_false",
                "source_evidence_mutated_must_be_false",
            ),
            _close_preview_gate(
                "source_submission_gate",
                source_submitted is False,
                "submitted_false",
                "source_evidence_submitted_must_be_false",
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
    recommended_action = (
        PAPER_SPY_CLOSE_PREVIEW_RECOMMENDED_ACTION
        if ok
        else _spy_close_preview_action(failed_gate_names)
    )
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
        fresh_snapshot_status=str(fresh_observation_status),
        recent_order_query_metadata_complete=(
            recent_order_query_metadata_complete is True
        ),
        mutated=source_mutated,
        submitted=source_submitted,
        gates=gates,
        recommended_next_operator_action=recommended_action,
        limitations=_close_preview_limitations(gates),
    )


def build_spy_paper_close_submit_contract(
    *,
    m354_state: str,
    m354_ok: bool,
    m354_submitted: bool | None,
    m354_mutated: bool | None,
    m354_broker_action_performed: bool | None,
    m354_close_order_submitted: bool | None,
    m354_live_authorized: bool | None,
    m354_requested_close_quantity: Decimal | str | None,
    observed_position_quantity: Decimal | str | None,
    account_observed: bool,
    positions_observed: bool,
    orders_observed: bool,
    recent_order_query_metadata_complete: bool,
    recent_open_order_count: int | None,
    duplicate_client_order_id_found: bool,
    profile_gate_passed: bool = True,
    halt_not_set: bool = True,
    submit_flag: bool = True,
    i_mean_it_flag: bool = True,
    unexpected_position_symbols: tuple[str, ...] = (),
    unavailable_observations: tuple[str, ...] = (),
    asset_class: str = ASSET_CLASS_EQUITY,
    symbol: str = "SPY",
    side: str = "sell",
    order_type: str = "market",
    time_in_force: str | None = None,
    requested_close_quantity: Decimal | str | None = (
        PAPER_SPY_CLOSE_SUBMIT_EXPECTED_QUANTITY
    ),
    client_order_id: str = PAPER_SPY_CLOSE_SUBMIT_CLIENT_ORDER_ID,
) -> PaperSpyCloseSubmitContract:
    """Build a gated SPY paper close submit contract from preview evidence."""

    equity_policy = paper_order_policy_for_asset_class(ASSET_CLASS_EQUITY)
    normalized_asset_class = str(asset_class).strip().lower()
    normalized_symbol = str(symbol).strip().upper()
    normalized_side = str(side).strip().lower()
    normalized_order_type = str(order_type).strip().lower()
    normalized_time_in_force = str(
        equity_policy.time_in_force if time_in_force is None else time_in_force
    ).strip().lower()
    normalized_client_order_id = str(client_order_id).strip()
    requested_quantity, requested_quantity_error = _positive_decimal_value(
        requested_close_quantity,
        "requested_close_quantity",
    )
    observed_quantity, observed_quantity_error = _positive_decimal_value(
        observed_position_quantity,
        "observed_position_quantity",
    )
    m354_quantity, m354_quantity_error = _positive_decimal_value(
        m354_requested_close_quantity,
        "m354_requested_close_quantity",
    )
    requested_quantity_matches = (
        requested_quantity is not None
        and m354_quantity is not None
        and requested_quantity == m354_quantity
    )
    m354_quantity_matches = (
        m354_quantity is not None
        and requested_quantity is not None
        and m354_quantity == requested_quantity
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
    open_order_count_zero = recent_open_order_count == 0
    submit_confirmed = submit_flag is True and i_mean_it_flag is True
    gates = tuple(
        [
            _close_preview_gate(
                "profile_gate",
                profile_gate_passed is True,
                "paper_profile_ready",
                "paper_profile_required",
            ),
            _close_preview_gate(
                "halt_gate",
                halt_not_set is True,
                "halt_not_set",
                "ALGOTRADER_PAPER_HALT=1",
            ),
            _close_preview_gate(
                "submit_confirmation_gate",
                submit_confirmed,
                "explicit_spy_close_submit_confirmed",
                "submit_requires_submit_and_i_mean_it",
            ),
            _close_preview_gate(
                "m354_state_gate",
                str(m354_state) == PAPER_SPY_CLOSE_SUBMIT_READY_M354_STATE,
                PAPER_SPY_CLOSE_SUBMIT_READY_M354_STATE,
                "m354_state_must_be_ready",
            ),
            _close_preview_gate(
                "m354_ok_gate",
                m354_ok is True,
                "m354_ok_true",
                "m354_ok_must_be_true",
            ),
            _close_preview_gate(
                "m354_no_submission_gate",
                m354_submitted is False,
                "m354_submitted_false",
                "m354_submitted_must_be_false",
            ),
            _close_preview_gate(
                "m354_no_mutation_gate",
                m354_mutated is False,
                "m354_mutated_false",
                "m354_mutated_must_be_false",
            ),
            _close_preview_gate(
                "m354_no_broker_action_gate",
                m354_broker_action_performed is False
                and m354_close_order_submitted is False,
                "m354_no_broker_action",
                "m354_broker_action_must_be_false",
            ),
            _close_preview_gate(
                "m354_not_live_gate",
                m354_live_authorized is False,
                "m354_live_authorized_false",
                "m354_live_authorized_must_be_false",
            ),
            _close_preview_gate(
                "m354_requested_quantity_gate",
                m354_quantity_matches,
                f"m354_requested_close_quantity={requested_quantity}",
                m354_quantity_error or "m354_requested_close_quantity_mismatch",
            ),
            _close_preview_gate(
                "asset_class_gate",
                normalized_asset_class == ASSET_CLASS_EQUITY,
                ASSET_CLASS_EQUITY,
                "asset_class_must_be_equity",
            ),
            _close_preview_gate(
                "allowlist_gate",
                equity_policy.allows_symbol(normalized_symbol),
                equity_policy.allowlist_detail(normalized_symbol),
                "symbol_not_in_SPY_allowlist",
            ),
            _close_preview_gate(
                "symbol_gate",
                normalized_symbol == "SPY",
                "symbol=SPY",
                "symbol_must_be_SPY",
            ),
            _close_preview_gate(
                "side_gate",
                normalized_side == "sell",
                "sell_only_close_submit",
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
                normalized_time_in_force == equity_policy.time_in_force,
                equity_policy.time_in_force,
                f"time_in_force_must_be_{equity_policy.time_in_force}",
            ),
            _close_preview_gate(
                "client_order_id_gate",
                _valid_spy_close_submit_client_order_id(normalized_client_order_id),
                "paper-order-close-*_spy_paper_close_submit",
                "client_order_id_must_be_spy_close_submit",
            ),
            _close_preview_gate(
                "quantity_gate",
                requested_quantity_matches,
                f"requested_close_quantity={m354_quantity}",
                requested_quantity_error or "requested_close_quantity_mismatch",
            ),
            _close_preview_gate(
                "account_observation_gate",
                account_observed is True,
                "account_observed",
                "account_must_be_observed",
            ),
            _close_preview_gate(
                "positions_observation_gate",
                positions_observed is True,
                "positions_observed",
                "positions_must_be_observed",
            ),
            _close_preview_gate(
                "orders_observation_gate",
                orders_observed is True,
                "orders_observed",
                "orders_must_be_observed",
            ),
            _close_preview_gate(
                "observed_position_gate",
                observed_quantity is not None,
                "observed_SPY_position_quantity_positive",
                observed_quantity_error or "observed_SPY_position_required",
            ),
            _close_preview_gate(
                "observed_position_quantity_gate",
                observed_quantity is not None and observed_quantity > 0,
                "observed_SPY_quantity_positive",
                "observed_SPY_quantity_must_be_positive",
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
                "requested_close_quantity_would_short_SPY",
            ),
            _close_preview_gate(
                "recent_order_query_metadata_gate",
                recent_order_query_metadata_complete is True,
                "recent_order_query_metadata_complete",
                "recent_order_query_metadata_must_be_complete",
            ),
            _close_preview_gate(
                "recent_open_order_gate",
                open_order_count_zero,
                "recent_open_spy_order_count_zero",
                "recent_open_spy_orders_must_be_zero",
            ),
            _close_preview_gate(
                "duplicate_client_order_id_gate",
                duplicate_client_order_id_found is False,
                "client_order_id_not_seen",
                "client_order_id_already_exists",
            ),
            _close_preview_gate(
                "unexpected_position_gate",
                not unexpected_position_symbols,
                "only_SPY_position_observed",
                "unexpected_non_SPY_positions_observed",
            ),
            _close_preview_gate(
                "unavailable_observation_gate",
                not unavailable_observations,
                "account_positions_and_orders_available",
                "required_observations_unavailable",
            ),
        ]
    )
    return PaperSpyCloseSubmitContract(
        ok=all(gate.passed for gate in gates),
        asset_class=normalized_asset_class,
        symbol=normalized_symbol,
        side=normalized_side,
        order_type=normalized_order_type,
        time_in_force=normalized_time_in_force,
        client_order_id=normalized_client_order_id,
        requested_close_quantity=requested_quantity,
        observed_position_quantity=observed_quantity,
        remaining_quantity_after_submit=remaining_quantity,
        gates=gates,
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


def _valid_spy_close_submit_client_order_id(client_order_id: str) -> bool:
    return (
        client_order_id.startswith("paper-order-close-")
        and client_order_id.endswith("_spy_paper_close_submit")
    )


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


def _spy_close_preview_action(failed_gate_names: tuple[str, ...]) -> str:
    if not failed_gate_names:
        return PAPER_SPY_CLOSE_PREVIEW_RECOMMENDED_ACTION
    if failed_gate_names[0] in {
        "quantity_gate",
        "close_quantity_within_observed_position_gate",
        "no_shorting_gate",
    }:
        return PAPER_CLOSE_PREVIEW_ADJUST_QUANTITY_ACTION

    return PAPER_SPY_CLOSE_PREVIEW_REPAIR_ACTION


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
    "PAPER_SPY_CLOSE_PREVIEW_OPERATOR_INSTRUCTION",
    "PAPER_SPY_CLOSE_PREVIEW_RECOMMENDED_ACTION",
    "PAPER_SPY_CLOSE_PREVIEW_REQUIRED_OBSERVATION_STATUS",
    "PAPER_SPY_CLOSE_PREVIEW_REPAIR_ACTION",
    "PAPER_SPY_CLOSE_SUBMIT_BLOCKED_STATE",
    "PAPER_SPY_CLOSE_SUBMIT_CLIENT_ORDER_ID",
    "PAPER_SPY_CLOSE_SUBMIT_CONTRACT_VERSION",
    "PAPER_SPY_CLOSE_SUBMIT_EXPECTED_QUANTITY",
    "PAPER_SPY_CLOSE_SUBMIT_GATE_ORDER",
    "PAPER_SPY_CLOSE_SUBMIT_READY_M354_STATE",
    "PAPER_SPY_CLOSE_SUBMIT_READY_STATE",
    "PaperClosePreviewContract",
    "PaperClosePreviewGate",
    "PaperOrderPolicy",
    "PaperSpyCloseSubmitContract",
    "build_btcusd_paper_close_preview_contract",
    "build_spy_paper_close_preview_contract",
    "build_spy_paper_close_submit_contract",
    "paper_order_policy_for_asset_class",
]
