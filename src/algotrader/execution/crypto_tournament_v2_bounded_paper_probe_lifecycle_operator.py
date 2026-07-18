"""Crash-resumable exact-winner USD 10 Alpaca-paper lifecycle operator."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
import uuid

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL, AlpacaPaperConfig
from algotrader.core.crypto_bounded_probe_lifecycle import (
    BUDGETS,
    ENTRY_NOTIONAL_USD,
    LIFECYCLE_RUNTIME_SOURCE_RELATIVE_PATHS,
    LIFECYCLE_RECORD_TYPE,
    LIFECYCLE_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    SAFETY_POLICY_FINGERPRINT,
    SUPPORTED_SYMBOLS,
    canonical_json_bytes,
    exact_operation_authorization_text,
    stable_hash,
    utc_datetime,
    validate_lifecycle_plan,
)
from algotrader.core.paper_account_binding import (
    build_alpaca_paper_account_binding,
    validate_alpaca_paper_account_binding,
)
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import (
    AlpacaOrderRequest,
    AlpacaRecentOrderQuery,
)
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.execution.crypto_bounded_probe_safety import (
    CryptoBoundedProbeObservation,
    CryptoBoundedProbeSafetyState,
    CryptoBoundedProbeSafetyStore,
)
from algotrader.execution.durable_cancel import (
    DurableCancelCoordinator,
    DurableCancelEvidence,
    DurableCancelIdentity,
    DurableCancelObservation,
)
from algotrader.execution.durable_submit import (
    DurableBrokerObservation,
    DurableSubmitCoordinator,
    DurableSubmitEvidence,
    DurableSubmitIdentity,
)
from algotrader.execution.order_journal import (
    CancelJournalState,
    OrderJournalState,
    SqliteOrderJournal,
)


DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_strategy_tournament/v2/bounded_paper_probe_lifecycle"
)
DEFAULT_JOURNAL_PATH = DEFAULT_OUTPUT_ROOT / "lifecycle_orders.sqlite3"
DEFAULT_SAFETY_STATE_PATH = DEFAULT_OUTPUT_ROOT / "bounded_probe_safety.sqlite3"
LEASE_TTL_SECONDS = 60

BrokerClientFactory = Callable[[AlpacaPaperConfig], Any]

_CREDENTIAL_NAMES = (
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
)
_EXPECTED_ACCOUNT_NAMES = (
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID",
)
_NETWORK_TEST_FLAG_NAMES = (
    "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
    "PYTEST_NETWORK",
    "NETWORK_TESTS",
    "ALLOW_NETWORK_TESTS",
)
_TERMINAL_STATUSES = {
    "filled",
    "canceled",
    "cancelled",
    "rejected",
    "expired",
}
_RESULT_KEYS = {
    "schema_version",
    "record_type",
    "as_of",
    "subject",
    "plan_fingerprint",
    "plan_source_sha256",
    "terminal_binding",
    "venue_binding",
    "safety_binding",
    "account_binding",
    "authorization",
    "operator_preflight",
    "deterministic_ids",
    "budgets",
    "entry_attempt_count",
    "cancel_attempt_count",
    "exit_attempt_count",
    "action_claim_fingerprints",
    "entry_final_order",
    "exit_final_order",
    "final_position_count",
    "final_open_order_count",
    "broker_read_occurred",
    "broker_mutation_performed",
    "paper_submit_performed",
    "paper_cancel_performed",
    "paper_replace_performed",
    "paper_close_performed",
    "paper_liquidate_performed",
    "broker_ambiguity",
    "outcome_classification",
    "blockers",
    "next_action",
    "paper_only",
    "live_endpoint_touched",
    "credential_values_exposed",
    "capital_allocation_authorized",
    "live_authorized",
    "profit_claim",
    "lifecycle_fingerprint",
}


__all__ = [
    "DEFAULT_JOURNAL_PATH",
    "DEFAULT_OUTPUT_ROOT",
    "DEFAULT_SAFETY_STATE_PATH",
    "main",
    "run_crypto_tournament_v2_bounded_paper_probe_lifecycle",
    "validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_receipt",
]


def run_crypto_tournament_v2_bounded_paper_probe_lifecycle(
    plan: Mapping[str, object],
    *,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    journal_path: Path | str = DEFAULT_JOURNAL_PATH,
    safety_state_path: Path | str = DEFAULT_SAFETY_STATE_PATH,
    timestamp: datetime | str | None = None,
    plan_source_bytes: bytes | None = None,
    clock: Callable[[], datetime] | None = None,
    env: Mapping[str, str] | None = None,
    broker_client_factory: BrokerClientFactory | None = None,
    exact_operation_authorization: str = "",
    expected_paper_account_id: str = "",
    paper_mutation_authorized: bool = False,
    allow_network: bool = False,
    reconciliation_poll_attempts: int = 3,
    reconciliation_poll_interval_seconds: float = 1.0,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Execute or resume one exact bounded paper lifecycle."""

    validate_lifecycle_plan(plan)
    as_of = utc_datetime(timestamp or datetime.now(UTC), "timestamp")
    trusted_clock = clock or (lambda: datetime.now(UTC))
    root = _path(output_root, "output_root")
    canonical_plan = canonical_json_bytes(plan)
    if plan_source_bytes is not None and plan_source_bytes != canonical_plan:
        raise ValidationError("lifecycle plan is not canonical JSON.")
    resolved_plan_bytes = (
        canonical_plan if plan_source_bytes is None else plan_source_bytes
    )
    plan_sha256 = hashlib.sha256(resolved_plan_bytes).hexdigest()
    base = _base_result(plan, as_of=as_of, plan_sha256=plan_sha256)
    if plan.get("classification") == "dormant_pending_terminal_winner":
        return _finish(
            root,
            {
                **base,
                "outcome_classification": "dormant_pending_terminal_winner",
                "blockers": ["v5_25_terminal_winner_not_available"],
                "next_action": "continue_receipt_bound_forward_shadow_accrual",
            },
            plan=plan,
            write_artifacts=write_artifacts,
        )

    plan_at = utc_datetime(plan["as_of"], "plan.as_of")
    if as_of < plan_at:
        return _finish(
            root,
            {
                **base,
                "blockers": ["plan_as_of_from_future"],
                "outcome_classification": "blocked_before_broker_read",
                "next_action": "wait_until_the_exact_plan_is_current",
            },
            plan=plan,
            write_artifacts=write_artifacts,
        )

    try:
        runtime_source_bundle_sha256 = _runtime_source_bundle_sha256()
    except ValidationError:
        runtime_source_bundle_sha256 = ""
    if runtime_source_bundle_sha256 != dict(
        plan["safety_binding"]
    ).get("runtime_source_bundle_sha256"):
        return _finish(
            root,
            {
                **base,
                "blockers": ["runtime_source_bundle_mismatch"],
                "outcome_classification": "blocked_before_broker_read",
                "next_action": (
                    "rebuild_plan_for_current_runtime_and_obtain_new_grant"
                ),
            },
            plan=plan,
            write_artifacts=write_artifacts,
        )

    source_env = _normalized_env(dict(os.environ) if env is None else env)
    expected_account = (
        str(expected_paper_account_id).strip()
        or _first_nonempty(source_env, _EXPECTED_ACCOUNT_NAMES)
    )
    preflight = {
        **_preflight(source_env, expected_account=expected_account),
        "runtime_source_bundle_matched": True,
    }
    authorization_text = str(exact_operation_authorization).strip()
    authorization_sha = hashlib.sha256(
        authorization_text.encode("utf-8")
    ).hexdigest()
    exact_authorization_matched = (
        bool(authorization_text)
        and authorization_sha == plan["required_authorization_sha256"]
        and authorization_text == exact_operation_authorization_text(plan)
    )
    blockers: list[str] = []
    if paper_mutation_authorized is not True:
        blockers.append("exact_paper_mutation_switch_required")
    if allow_network is not True:
        blockers.append("allow_network_switch_required")
    if not exact_authorization_matched:
        blockers.append("exact_operation_authorization_mismatch")
    blockers.extend(_preflight_blockers(preflight))
    if expected_account:
        expected_binding = build_alpaca_paper_account_binding(
            {"account_id": expected_account},
            expected_account_configured=True,
            expected_account_matched=True,
        )
        if expected_binding != plan["account_binding"]:
            blockers.append("expected_paper_account_binding_mismatch")
    authorization = {
        "paper_mutation_authorized": paper_mutation_authorized is True,
        "network_authorized": allow_network is True,
        "exact_operation_authorization_matched": exact_authorization_matched,
        "authorization_fingerprint": (
            authorization_sha if exact_authorization_matched else ""
        ),
        "entry_authorization_valid_until": plan[
            "entry_authorization_valid_until"
        ],
        "risk_reducing_unwind_authorized_for_claimed_entry": (
            exact_authorization_matched
        ),
        "live_authorized": False,
        "capital_allocation_authorized": False,
    }
    base = {
        **base,
        "authorization": authorization,
        "operator_preflight": preflight,
    }
    if blockers:
        return _finish(
            root,
            {
                **base,
                "blockers": list(dict.fromkeys(blockers)),
                "outcome_classification": "blocked_before_broker_read",
                "next_action": "resolve_exact_paper_lifecycle_preflight",
            },
            plan=plan,
            write_artifacts=write_artifacts,
        )

    client = _build_client(source_env, broker_client_factory)
    if client is None:
        return _finish(
            root,
            {
                **base,
                "blockers": ["paper_broker_client_unavailable"],
                "outcome_classification": "blocked_before_broker_read",
                "next_action": "repair_paper_client_without_mutation",
            },
            plan=plan,
            write_artifacts=write_artifacts,
        )

    symbol = str(plan["subject"]["symbol"])
    journal = SqliteOrderJournal(_path(journal_path, "journal_path"))
    store = CryptoBoundedProbeSafetyStore(
        _path(safety_state_path, "safety_state_path")
    )
    try:
        journal.initialize()
        state = store.initialize(selected_symbol=symbol, as_of=as_of)
    except ValidationError as exc:
        return _finish(
            root,
            {
                **base,
                "blockers": [f"durable_state_unavailable:{exc}"],
                "outcome_classification": "blocked_before_broker_read",
                "next_action": "repair_durable_state_without_mutation",
            },
            plan=plan,
            write_artifacts=write_artifacts,
        )

    ids = dict(plan["deterministic_ids"])
    snapshot = _read_snapshot(
        client,
        symbol=symbol,
        expected_account=expected_account,
        not_before=as_of,
        clock=trusted_clock,
    )
    historical_mutations = _historical_mutation_flags(journal, ids)
    observed_base = {
        **base,
        **historical_mutations,
        "broker_read_occurred": snapshot["broker_read_occurred"],
        "account_binding": snapshot.get("account_binding", {}),
        "final_position_count": snapshot["position_count"],
        "final_open_order_count": snapshot["open_order_count"],
    }
    if snapshot["blockers"]:
        return _finish_with_state(
            root,
            observed_base,
            plan=plan,
            state=state,
            outcome="blocked_by_broker_snapshot",
            blockers=snapshot["blockers"],
            next_action="repair_or_reconcile_paper_state_without_mutation",
            write_artifacts=write_artifacts,
        )
    if snapshot["account_binding"] != plan["account_binding"]:
        return _finish_with_state(
            root,
            observed_base,
            plan=plan,
            state=state,
            outcome="blocked_by_broker_snapshot",
            blockers=["observed_paper_account_binding_mismatch"],
            next_action="use_the_exact_authorized_paper_account",
            write_artifacts=write_artifacts,
        )

    entry_record = journal.get(ids["entry_client_order_id"])
    exit_record = journal.get(ids["exit_client_order_id"])
    if entry_record is None and exit_record is not None:
        return _finish_with_state(
            root,
            observed_base,
            plan=plan,
            state=state,
            outcome="manual_reconciliation_required",
            blockers=["exit_journal_exists_without_entry_journal"],
            next_action="inspect_durable_journal_without_mutation",
            write_artifacts=write_artifacts,
        )
    if (
        exit_record is not None
        and exit_record.state is not OrderJournalState.RESERVED
    ):
        restart = _reconcile_attempted_exit(
            plan=plan,
            client=client,
            journal=journal,
            ids=ids,
            symbol=symbol,
            snapshot=snapshot,
            as_of=as_of,
        )
        state = store.load()
        restart_base = {
            **observed_base,
            "as_of": _latest_order_evidence_time(
                snapshot["observed_at"],
                restart["entry_order"],
                restart["exit_order"],
            ).isoformat(),
            "entry_final_order": restart["entry_order"],
            "exit_final_order": restart["exit_order"],
            "broker_ambiguity": restart["ambiguous"],
            "final_position_count": snapshot["position_count"],
            "final_open_order_count": snapshot["open_order_count"],
        }
        if restart["success"]:
            result = _finish_with_state(
                root,
                restart_base,
                plan=plan,
                state=state,
                outcome="filled_exit_confirmed",
                blockers=[],
                next_action="run_v5_29_independent_flat_collector",
                write_artifacts=write_artifacts,
            )
            validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_receipt(
                result
            )
            return result
        return _finish_with_state(
            root,
            restart_base,
            plan=plan,
            state=state,
            outcome=(
                "exit_ambiguous_residual_position"
                if restart["ambiguous"]
                else "exit_not_flat_reconciliation_required"
            ),
            blockers=restart["blockers"],
            next_action="reconcile_exact_exit_without_resubmit",
            write_artifacts=write_artifacts,
        )

    entry_needs_submit = (
        entry_record is None
        or entry_record.state is OrderJournalState.RESERVED
    )
    entry_action_at = _trusted_clock_time(
        trusted_clock,
        not_before=snapshot["observed_at"],
    )
    if entry_needs_submit and snapshot["entry_blockers"]:
        return _finish_with_state(
            root,
            observed_base,
            plan=plan,
            state=state,
            outcome="blocked_before_entry",
            blockers=snapshot["entry_blockers"],
            next_action="refresh_entry_only_broker_evidence",
            write_artifacts=write_artifacts,
        )
    if entry_needs_submit and entry_action_at > utc_datetime(
        plan["entry_authorization_valid_until"],
        "entry_authorization_valid_until",
    ):
        return _finish_with_state(
            root,
            observed_base,
            plan=plan,
            state=state,
            outcome="entry_authorization_expired",
            blockers=["entry_authorization_expired"],
            next_action="build_a_fresh_exact_plan_and_authorization",
            write_artifacts=write_artifacts,
        )
    if entry_needs_submit and (
        snapshot["position_count"] or snapshot["open_order_count"]
    ):
        return _finish_with_state(
            root,
            observed_base,
            plan=plan,
            state=state,
            outcome="blocked_before_entry",
            blockers=["entry_requires_account_wide_flat_no_open_orders"],
            next_action="reconcile_account_state_without_mutation",
            write_artifacts=write_artifacts,
        )

    entry_request = _entry_order_request(plan)
    if entry_record is None:
        existing_entry = _lookup_order(
            client,
            ids["entry_client_order_id"],
            symbol=symbol,
            expected_side="buy",
            expected_request=entry_request,
        )
        existing_exit = _lookup_order(
            client,
            ids["exit_client_order_id"],
            symbol=symbol,
            expected_side="sell",
        )
        prelookup_blockers = [
            str(result["blocker"])
            for result in (existing_entry, existing_exit)
            if result["blocker"]
            and result["blocker"] != "deterministic_order_lookup_absent"
        ]
        if (
            existing_entry["order"]
            or existing_exit["order"]
            or prelookup_blockers
        ):
            return _finish_with_state(
                root,
                observed_base,
                plan=plan,
                state=state,
                outcome="manual_reconciliation_required",
                blockers=(
                    prelookup_blockers
                    or ["unbound_deterministic_broker_order_observed"]
                ),
                next_action="bind_existing_order_to_durable_journal_manually",
                write_artifacts=write_artifacts,
            )
        if as_of > utc_datetime(
            plan["entry_authorization_valid_until"],
            "entry_authorization_valid_until",
        ):
            return _finish_with_state(
                root,
                observed_base,
                plan=plan,
                state=state,
                outcome="entry_authorization_expired",
                blockers=["entry_authorization_expired"],
                next_action="build_a_fresh_exact_plan_and_authorization",
                write_artifacts=write_artifacts,
            )
        if snapshot["positions"] or snapshot["open_orders"]:
            return _finish_with_state(
                root,
                observed_base,
                plan=plan,
                state=state,
                outcome="blocked_before_entry",
                blockers=["entry_requires_account_wide_flat_no_open_orders"],
                next_action="reconcile_account_state_without_mutation",
                write_artifacts=write_artifacts,
            )
        if state.entry_attempt_count != 0:
            return _finish_with_state(
                root,
                observed_base,
                plan=plan,
                state=state,
                outcome="manual_reconciliation_required",
                blockers=["entry_attempt_claim_without_order_reservation"],
                next_action="inspect_durable_state_without_mutation",
                write_artifacts=write_artifacts,
            )
        try:
            state = store.record_operator_control(
                entry_enabled=True,
                authorization_fingerprint=authorization_sha,
                as_of=entry_action_at,
            )
            state = store.record_loss_observation(
                cumulative_net_pnl_usd="0",
                loss_basis_fingerprint=_loss_basis(plan, snapshot, "entry"),
                as_of=entry_action_at,
            )
        except ValidationError as exc:
            return _finish_with_state(
                root,
                observed_base,
                plan=plan,
                state=state,
                outcome="blocked_before_entry",
                blockers=[f"safety_state_update_failed:{exc}"],
                next_action="repair_safety_state_without_mutation",
                write_artifacts=write_artifacts,
            )


    entry_action = _submit_or_reconcile(
        role="entry",
        request=entry_request,
        plan=plan,
        client=client,
        journal=journal,
        store=store,
        snapshot=snapshot,
        as_of=entry_action_at,
        clock=trusted_clock,
        entry_valid_until=utc_datetime(
            plan["entry_authorization_valid_until"],
            "entry_authorization_valid_until",
        ),
        poll_attempts=reconciliation_poll_attempts,
        poll_interval=reconciliation_poll_interval_seconds,
    )
    state = store.load()
    try:
        entry_observed_at = _trusted_clock_time(
            trusted_clock,
            not_before=entry_action_at,
        )
    except ValidationError:
        return _finish_with_state(
            root,
            {
                **observed_base,
                "broker_mutation_performed": bool(
                    observed_base["broker_mutation_performed"]
                    or entry_action["broker_called"]
                ),
                "paper_submit_performed": bool(
                    observed_base["paper_submit_performed"]
                    or entry_action["broker_called"]
                ),
                "entry_final_order": entry_action["order"],
                "broker_ambiguity": bool(entry_action["ambiguous"]),
            },
            plan=plan,
            state=state,
            outcome="manual_reconciliation_required",
            blockers=["trusted_clock_invalid_after_entry_action"],
            next_action="reconcile_exact_entry_without_new_mutation",
            write_artifacts=write_artifacts,
        )
    if entry_action["ambiguous"]:
        return _finish_with_state(
            root,
            {
                **observed_base,
                "broker_mutation_performed": bool(
                    observed_base["broker_mutation_performed"]
                    or entry_action["broker_called"]
                ),
                "paper_submit_performed": bool(
                    observed_base["paper_submit_performed"]
                    or entry_action["broker_called"]
                ),
                "entry_final_order": entry_action["order"],
                "broker_ambiguity": True,
            },
            plan=plan,
            state=state,
            outcome="entry_ambiguous",
            blockers=entry_action["blockers"],
            next_action="reconcile_exact_entry_id_without_resubmit",
            write_artifacts=write_artifacts,
        )
    if entry_action["blockers"]:
        return _finish_with_state(
            root,
            {
                **observed_base,
                "entry_final_order": entry_action["order"],
            },
            plan=plan,
            state=state,
            outcome="blocked_before_entry",
            blockers=entry_action["blockers"],
            next_action="repair_local_safety_without_mutation",
            write_artifacts=write_artifacts,
        )
    entry_order = entry_action["order"]
    entry_status = str(entry_order.get("status", ""))
    post_entry_not_before = entry_observed_at
    if entry_status not in _TERMINAL_STATUSES:
        if entry_observed_at <= utc_datetime(
            plan["entry_authorization_valid_until"],
            "entry_authorization_valid_until",
        ):
            return _finish_with_state(
                root,
                {
                    **observed_base,
                    "broker_mutation_performed": bool(
                        observed_base["broker_mutation_performed"]
                        or entry_action["broker_called"]
                    ),
                    "paper_submit_performed": bool(
                        observed_base["paper_submit_performed"]
                        or entry_action["broker_called"]
                    ),
                    "entry_final_order": entry_order,
                },
                plan=plan,
                state=state,
                outcome="entry_open_waiting_for_expiry",
                blockers=[],
                next_action="rerun_after_expiry_for_exact_same_order_cancel",
                write_artifacts=write_artifacts,
            )
        cancel_snapshot = _read_snapshot(
            client,
            symbol=symbol,
            expected_account=expected_account,
            not_before=entry_observed_at,
            clock=trusted_clock,
        )
        cancel_action = _cancel_entry_or_reconcile(
            plan=plan,
            client=client,
            journal=journal,
            store=store,
            entry_order=entry_action["raw_order"],
            snapshot=cancel_snapshot,
            as_of=cancel_snapshot["observed_at"],
        )
        state = store.load()
        if cancel_action["ambiguous"]:
            return _finish_with_state(
                root,
                {
                    **observed_base,
                    "broker_mutation_performed": True,
                    "paper_submit_performed": bool(
                        observed_base["paper_submit_performed"]
                        or entry_action["broker_called"]
                    ),
                    "paper_cancel_performed": bool(
                        observed_base["paper_cancel_performed"]
                        or cancel_action["broker_called"]
                    ),
                    "entry_final_order": cancel_action["order"],
                    "broker_ambiguity": True,
                },
                plan=plan,
                state=state,
                outcome="entry_cancel_ambiguous",
                blockers=cancel_action["blockers"],
                next_action="reconcile_exact_cancel_target_without_retry",
                write_artifacts=write_artifacts,
            )
        if cancel_action["blockers"]:
            return _finish_with_state(
                root,
                {
                    **observed_base,
                    "entry_final_order": cancel_action["order"],
                },
                plan=plan,
                state=state,
                outcome="blocked_before_cancel",
                blockers=cancel_action["blockers"],
                next_action="repair_cancel_safety_without_mutation",
                write_artifacts=write_artifacts,
            )
        entry_order = cancel_action["order"]
        entry_action["raw_order"] = cancel_action["raw_order"]
        entry_action["cancel_called"] = cancel_action["broker_called"]
        entry_status = str(entry_order.get("status", ""))
        post_entry_not_before = cancel_snapshot["observed_at"]

    post_entry = _read_snapshot(
        client,
        symbol=symbol,
        expected_account=expected_account,
        not_before=post_entry_not_before,
        clock=trusted_clock,
    )
    post_entry_base = {
        **observed_base,
        "broker_mutation_performed": bool(
            observed_base["broker_mutation_performed"]
            or entry_action["broker_called"]
            or entry_action.get("cancel_called", False)
        ),
        "paper_submit_performed": bool(
            observed_base["paper_submit_performed"]
            or entry_action["broker_called"]
        ),
        "paper_cancel_performed": bool(
            observed_base["paper_cancel_performed"]
            or entry_action.get("cancel_called", False)
        ),
        "entry_final_order": entry_order,
        "final_position_count": post_entry["position_count"],
        "final_open_order_count": post_entry["open_order_count"],
    }
    if post_entry["blockers"]:
        return _finish_with_state(
            root,
            post_entry_base,
            plan=plan,
            state=state,
            outcome="manual_reconciliation_required",
            blockers=post_entry["blockers"],
            next_action="reconcile_post_entry_snapshot_without_new_mutation",
            write_artifacts=write_artifacts,
        )
    position = _single_selected_position(post_entry["positions"], symbol)
    filled_qty = _decimal(entry_order.get("filled_qty", "0"), "filled_qty")
    if position is None and post_entry["position_count"]:
        return _finish_with_state(
            root,
            post_entry_base,
            plan=plan,
            state=state,
            outcome="manual_reconciliation_required",
            blockers=["entry_position_attribution_or_open_order_mismatch"],
            next_action=(
                "reconcile_exact_target_exposure_without_foreign_mutation"
            ),
            write_artifacts=write_artifacts,
        )
    if position is None:
        return _finish_with_state(
            root,
            post_entry_base,
            plan=plan,
            state=state,
            outcome=(
                "entry_rejected_no_position"
                if entry_status == "rejected"
                else "entry_terminal_no_position"
            ),
            blockers=[],
            next_action="bounded_lifecycle_ended_without_capability_evidence",
            write_artifacts=write_artifacts,
        )
    position_qty = _decimal(position["qty"], "position.qty")
    if (
        post_entry["open_orders"]
        or filled_qty <= 0
        or position_qty != filled_qty
        or position["symbol"] != symbol
    ):
        return _finish_with_state(
            root,
            post_entry_base,
            plan=plan,
            state=state,
            outcome="manual_reconciliation_required",
            blockers=["entry_position_attribution_or_open_order_mismatch"],
            next_action="reconcile_exact_entry_and_position_without_resubmit",
            write_artifacts=write_artifacts,
        )

    try:
        state = store.record_loss_observation(
            cumulative_net_pnl_usd=position["unrealized_pl"],
            loss_basis_fingerprint=_loss_basis(plan, post_entry, "exit"),
            as_of=post_entry["observed_at"],
        )
    except ValidationError as exc:
        return _finish_with_state(
            root,
            post_entry_base,
            plan=plan,
            state=state,
            outcome="blocked_before_exit",
            blockers=[f"loss_observation_failed:{exc}"],
            next_action="repair_loss_context_before_exact_exit",
            write_artifacts=write_artifacts,
        )

    exit_action_at = _trusted_clock_time(
        trusted_clock,
        not_before=post_entry["observed_at"],
    )
    exit_request = _exit_order_request(plan, position_qty)
    exit_action = _submit_or_reconcile(
        role="exit",
        request=exit_request,
        plan=plan,
        client=client,
        journal=journal,
        store=store,
        snapshot=post_entry,
        as_of=exit_action_at,
        clock=trusted_clock,
        entry_valid_until=None,
        poll_attempts=reconciliation_poll_attempts,
        poll_interval=reconciliation_poll_interval_seconds,
    )
    state = store.load()
    mutation_performed = bool(
        observed_base["broker_mutation_performed"] or
        entry_action["broker_called"]
        or entry_action.get("cancel_called")
        or exit_action["broker_called"]
    )
    common_final = {
        **post_entry_base,
        "as_of": _latest_order_evidence_time(
            exit_action_at,
            entry_order,
            exit_action["order"],
        ).isoformat(),
        "broker_mutation_performed": mutation_performed,
        "paper_submit_performed": bool(
            observed_base["paper_submit_performed"] or
            entry_action["broker_called"] or exit_action["broker_called"]
        ),
        "paper_cancel_performed": bool(
            observed_base["paper_cancel_performed"]
            or entry_action.get("cancel_called", False)
        ),
        "entry_final_order": entry_order,
        "exit_final_order": exit_action["order"],
    }
    if exit_action["ambiguous"]:
        return _finish_with_state(
            root,
            {**common_final, "broker_ambiguity": True},
            plan=plan,
            state=state,
            outcome="exit_ambiguous_residual_position",
            blockers=exit_action["blockers"],
            next_action="reconcile_exact_exit_id_without_resubmit",
            write_artifacts=write_artifacts,
        )
    if exit_action["blockers"]:
        return _finish_with_state(
            root,
            common_final,
            plan=plan,
            state=state,
            outcome="blocked_before_exit",
            blockers=exit_action["blockers"],
            next_action="repair_exit_safety_without_mutation",
            write_artifacts=write_artifacts,
        )
    final_snapshot = _read_snapshot(
        client,
        symbol=symbol,
        expected_account=expected_account,
        not_before=exit_action_at,
        clock=trusted_clock,
    )
    exit_order = exit_action["order"]
    if (
        exit_order.get("status") == "filled"
        and not final_snapshot["blockers"]
        and not final_snapshot["positions"]
        and not final_snapshot["open_orders"]
        and _decimal(exit_order.get("filled_qty"), "exit.filled_qty")
        == position_qty
    ):
        result = _finish_with_state(
            root,
            {
                **common_final,
                "final_position_count": 0,
                "as_of": _latest_order_evidence_time(
                    final_snapshot["observed_at"],
                    entry_order,
                    exit_order,
                ).isoformat(),
                "final_open_order_count": 0,
            },
            plan=plan,
            state=state,
            outcome="filled_exit_confirmed",
            blockers=[],
            next_action="run_v5_29_independent_flat_collector",
            write_artifacts=write_artifacts,
        )
        validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_receipt(
            result
        )
        return result
    return _finish_with_state(
        root,
        {
            **common_final,
            "as_of": _latest_order_evidence_time(
                final_snapshot["observed_at"],
                entry_order,
                exit_order,
            ).isoformat(),
            "final_position_count": final_snapshot["position_count"],
            "final_open_order_count": final_snapshot["open_order_count"],
        },
        plan=plan,
        state=state,
        outcome="exit_not_flat_reconciliation_required",
        blockers=(
            final_snapshot["blockers"]
            or ["filled_exit_and_account_wide_flat_not_confirmed"]
        ),
        next_action="reconcile_exact_exit_without_resubmit",
        write_artifacts=write_artifacts,

    )

def _entry_order_request(
    plan: Mapping[str, object],
) -> AlpacaOrderRequest:
    ids = dict(plan["deterministic_ids"])
    return AlpacaOrderRequest(
        client_order_id=str(ids["entry_client_order_id"]),
        symbol=str(plan["subject"]["symbol"]),
        side="buy",
        asset_class="crypto",
        notional=ENTRY_NOTIONAL_USD,
        order_type="market",
        time_in_force="gtc",
    )


def _exit_order_request(
    plan: Mapping[str, object],
    quantity: Decimal,
) -> AlpacaOrderRequest:
    ids = dict(plan["deterministic_ids"])
    return AlpacaOrderRequest(
        client_order_id=str(ids["exit_client_order_id"]),
        symbol=str(plan["subject"]["symbol"]),
        side="sell",
        asset_class="crypto",
        qty=quantity,
        order_type="market",
        time_in_force="gtc",
    )


def _reconcile_attempted_exit(
    *,
    plan: Mapping[str, object],
    client: Any,
    journal: SqliteOrderJournal,
    ids: Mapping[str, object],
    symbol: str,
    snapshot: Mapping[str, Any],
    as_of: datetime,
) -> dict[str, object]:
    raw_orders: dict[str, Any] = {}
    blockers: list[str] = []
    entry_record = journal.get(str(ids["entry_client_order_id"]))
    exit_record = journal.get(str(ids["exit_client_order_id"]))
    if (
        entry_record is None
        or exit_record is None
        or exit_record.quantity is None
    ):
        return {
            "success": False,
            "ambiguous": True,
            "blockers": ["attempted_exit_journal_shape_invalid"],
            "entry_order": {},
            "exit_order": {},
        }
    requests = {
        "entry": _entry_order_request(plan),
        "exit": _exit_order_request(plan, exit_record.quantity),
    }
    records = {"entry": entry_record, "exit": exit_record}
    for role, client_order_id in (
        ("entry", str(ids["entry_client_order_id"])),
        ("exit", str(ids["exit_client_order_id"])),
    ):
        lookup = _lookup_order(
            client,
            client_order_id,
            symbol=symbol,
            expected_side="buy" if role == "entry" else "sell",
            expected_request=requests[role],
            expected_broker_order_fingerprint=_broker_order_fingerprint(
                records[role].broker_order_id
            ),
        )
        raw_order = lookup["order"]
        raw_orders[role] = raw_order
        if not raw_order:
            blockers.append(
                str(lookup["blocker"])
                or f"deterministic_{role}_lookup_absent"
            )
            continue
        observed = _durable_broker_observation(raw_order)
        try:
            journal.record_broker_observation(
                client_order_id,
                as_of,
                broker_order_id=observed.broker_order_id,
                broker_status=observed.broker_status,
                filled_quantity=observed.filled_quantity,
                filled_average_price=observed.filled_average_price,
            )
        except ValidationError:
            blockers.append(f"{role}_broker_observation_not_persisted")

    entry_order = (
        _public_order(raw_orders["entry"]) if raw_orders["entry"] else {}
    )
    exit_order = (
        _public_order(raw_orders["exit"]) if raw_orders["exit"] else {}
    )
    quantities_match = False
    try:
        entry_qty = _decimal(entry_order.get("filled_qty"), "entry.filled_qty")
        exit_qty = _decimal(exit_order.get("filled_qty"), "exit.filled_qty")
        quantities_match = entry_qty > 0 and entry_qty == exit_qty
    except ValidationError:
        blockers.append("attempted_exit_fill_quantity_invalid")

    success = bool(
        not blockers
        and entry_order.get("status") == "filled"
        and exit_order.get("status") == "filled"
        and quantities_match
        and not snapshot["positions"]
        and not snapshot["open_orders"]
    )
    if not success and not blockers:
        blockers.append("filled_exit_and_account_wide_flat_not_confirmed")
    return {
        "success": success,
        "ambiguous": bool(blockers),
        "blockers": list(dict.fromkeys(blockers)),
        "entry_order": entry_order,
        "exit_order": exit_order,
    }
def _submit_or_reconcile(
    *,
    role: str,
    request: AlpacaOrderRequest,
    plan: Mapping[str, object],
    client: Any,
    journal: SqliteOrderJournal,
    store: CryptoBoundedProbeSafetyStore,
    snapshot: Mapping[str, Any],
    as_of: datetime,
    clock: Callable[[], datetime],
    entry_valid_until: datetime | None,
    poll_attempts: int,
    poll_interval: float,
) -> dict[str, Any]:
    existing_record = journal.get(request.client_order_id)
    if (
        role == "entry"
        and (
            existing_record is None
            or existing_record.state is OrderJournalState.RESERVED
        )
        and (
            entry_valid_until is None
            or _trusted_clock_time(clock, not_before=as_of)
            > entry_valid_until
        )
    ):
        return _action_result(
            "entry_authorization_expired_before_submit",
            broker_called=False,
            ambiguous=False,
        )
    ids = dict(plan["deterministic_ids"])
    identity = DurableSubmitIdentity(
        client_order_id=request.client_order_id,
        execution_plan_id=ids["execution_plan_id"],
        reservation_run_id=f"v530-{role}-{plan['plan_fingerprint'][:20]}",
        symbol=request.symbol,
        side=request.side,
        quantity=request.qty,
        notional=request.notional,
    )
    coordinator = DurableSubmitCoordinator(journal)
    reservation = coordinator.reserve(identity, as_of)
    record = reservation.record
    broker_called = False
    if reservation.status == "client_order_id_conflict":
        return _action_result(
            "durable_order_identity_conflict",
            broker_called=False,
        )
    if record.state is OrderJournalState.RESERVED:
        claim = _ensure_safety_claim(
            role=role,
            request=request,
            plan=plan,
            store=store,
            snapshot=snapshot,
            as_of=as_of,
        )
        if not claim["admitted"]:
            return _action_result(
                "local_safety_claim_not_admitted:"
                + ",".join(claim["blockers"]),
                broker_called=False,
                ambiguous=False,
            )
        lease = coordinator.acquire_lease(
            lease_name=f"v530:{plan['plan_fingerprint']}:{role}",
            owner_run_id=uuid.uuid4().hex,
            occurred_at=as_of,
            ttl_seconds=LEASE_TTL_SECONDS,
        )
        if not lease.acquired:
            return _action_result(
                lease.blocker or "durable_submit_lease_unavailable",
                broker_called=False,
                ambiguous=False,
            )
        try:
            if role == "entry" and (
                entry_valid_until is None
                or _trusted_clock_time(clock, not_before=as_of)
                > entry_valid_until
            ):
                return _action_result(
                    "entry_authorization_expired_before_submit",
                    broker_called=False,
                    ambiguous=False,
                )
            outcome = coordinator.execute(
                identity=identity,
                lease=lease,
                evidence=DurableSubmitEvidence(
                    canonical_risk_allowed=True,
                    snapshot_fresh=True,
                ),
                occurred_at=as_of,
                submit=lambda: client.submit_order(request),
                observe=lambda value: _observe_exact_order(value, request),
            )
        finally:
            coordinator.release_lease(lease)
        broker_called = outcome.broker_called
        if outcome.status == "blocked":
            return _action_result(
                outcome.blocker or "durable_submit_blocked",
                broker_called=broker_called,
                ambiguous=False,
            )
    observed_record = journal.get(request.client_order_id)
    expected_broker_fingerprint = _broker_order_fingerprint(
        "" if observed_record is None else observed_record.broker_order_id
    )
    lookup = _poll_lookup(
        client,
        request.client_order_id,
        symbol=request.symbol,
        expected_side=request.side,
        expected_request=request,
        expected_broker_order_fingerprint=(
            expected_broker_fingerprint
        ),
        attempts=poll_attempts,
        interval_seconds=poll_interval,
    )
    raw_order = lookup["order"]
    if raw_order:
        observed = _durable_broker_observation(raw_order)
        try:
            journal.record_broker_observation(
                request.client_order_id,
                as_of,
                broker_order_id=observed.broker_order_id,
                broker_status=observed.broker_status,
                filled_quantity=observed.filled_quantity,
                filled_average_price=observed.filled_average_price,
            )
        except ValidationError:
            return _action_result(
                "broker_order_observation_not_persisted",
                broker_called=broker_called,
            )
        return {
            "ambiguous": False,
            "broker_called": broker_called,
            "blockers": [],
            "raw_order": raw_order,
            "order": _public_order(raw_order),
        }
    return _action_result(
        lookup["blocker"] or "deterministic_order_lookup_absent",
        broker_called=broker_called,
    )


def _ensure_safety_claim(
    *,
    role: str,
    request: AlpacaOrderRequest,
    plan: Mapping[str, object],
    store: CryptoBoundedProbeSafetyStore,
    snapshot: Mapping[str, Any],
    as_of: datetime,
) -> dict[str, Any]:
    state = store.load()
    claim_fingerprint = _action_claim_fingerprint(plan, role)
    counter = getattr(state, f"{role}_attempt_count")
    if counter == 1:
        matched = state.last_action_fingerprint == claim_fingerprint
        return {
            "admitted": matched,
            "blockers": [] if matched else [
                "persisted_action_claim_identity_mismatch"
            ],
        }
    if counter != 0:
        return {
            "admitted": False,
            "blockers": [f"{role}_attempt_budget_exhausted"],
        }
    symbol = str(plan["subject"]["symbol"])
    position = _single_selected_position(snapshot["positions"], symbol)
    position_qty = (
        Decimal("0") if position is None else _decimal(position["qty"], "qty")
    )
    observation = CryptoBoundedProbeObservation(
        symbol=symbol,
        action=role,
        as_of=as_of,
        broker_snapshot_as_of=snapshot["observed_at"],
        capability_valid_until=utc_datetime(
            plan["entry_authorization_valid_until"],
            "entry_authorization_valid_until",
        ),
        market_data_as_of=(
            snapshot["market_data_at"] if role == "entry" else None
        ),
        requested_notional_usd=(
            request.notional or Decimal("0")
            if role == "entry"
            else Decimal("0")
        ),
        requested_exit_quantity=(
            request.qty or Decimal("0")
            if role == "exit"
            else Decimal("0")
        ),
        principal_at_risk_usd=_principal_at_risk(snapshot["positions"]),
        available_cash_usd=snapshot["cash"],
        position_quantity=position_qty,
        position_count=snapshot["position_count"],
        open_order_count=snapshot["open_order_count"],
        entry_attempt_count=state.entry_attempt_count,
        exit_attempt_count=state.exit_attempt_count,
        cancel_attempt_count=state.cancel_attempt_count,
        replacement_attempt_count=0,
        loss_context_complete=True,
        cumulative_net_pnl_usd=state.cumulative_net_pnl_usd,
        account_trading_blocked=snapshot["account_trading_blocked"],
        margin_used=False,
        broker_ambiguity=False,
        unexpected_symbol_exposure=_cross_symbol_exposure(
            snapshot["positions"],
            snapshot["open_orders"],
            symbol,
        ),
    )
    verdict = store.evaluate_and_claim(
        observation,
        claim_fingerprint=claim_fingerprint,
    )["verdict"]
    return {
        "admitted": (
            verdict.get("local_safety_admitted") is True
            and verdict.get("claim_recorded") is True
        ),
        "blockers": list(verdict.get("blockers", [])),
    }


def _cancel_entry_or_reconcile(
    *,
    plan: Mapping[str, object],
    client: Any,
    journal: SqliteOrderJournal,
    store: CryptoBoundedProbeSafetyStore,
    entry_order: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    as_of: datetime,
) -> dict[str, Any]:
    ids = dict(plan["deterministic_ids"])
    entry_request = _entry_order_request(plan)
    broker_order_id = _text(_field(entry_order, "id", "order_id"))
    expected_broker_fingerprint = _broker_order_fingerprint(broker_order_id)
    raw_snapshot_order = (
        snapshot["raw_open_orders"][0]
        if snapshot["open_order_count"] == 1
        else {}
    )
    entry_shape_blocker = _order_request_shape_blocker(
        entry_order,
        entry_request,
        expected_broker_order_fingerprint=expected_broker_fingerprint,
    )
    snapshot_shape_blocker = (
        _order_request_shape_blocker(
            raw_snapshot_order,
            entry_request,
            expected_broker_order_fingerprint=expected_broker_fingerprint,
        )
        if raw_snapshot_order
        else "cancel_snapshot_order_absent"
    )
    if (
        not broker_order_id
        or snapshot["open_order_count"] != 1
        or entry_shape_blocker
        or snapshot_shape_blocker
        or _order_status(raw_snapshot_order) in _TERMINAL_STATUSES
    ):
        return _action_result(
            entry_shape_blocker
            or snapshot_shape_blocker
            or "cancel_requires_exactly_one_identity_bound_entry_order",
            broker_called=False,
            ambiguous=False,
        )
    entry_public = _public_order(entry_order)
    order_fingerprint = stable_hash(
        {
            "client_order_id": entry_public["client_order_id"],
            "broker_order_fingerprint": entry_public[
                "broker_order_fingerprint"
            ],
            "symbol": entry_public["symbol"],
            "side": entry_public["side"],
        }
    )
    state = store.load()
    claim_fingerprint = _action_claim_fingerprint(plan, "cancel")
    if state.cancel_attempt_count == 0:
        position = _single_selected_position(
            snapshot["positions"],
            str(plan["subject"]["symbol"]),
        )
        observation = CryptoBoundedProbeObservation(
            symbol=str(plan["subject"]["symbol"]),
            action="cancel",
            as_of=as_of,
            broker_snapshot_as_of=snapshot["observed_at"],
            capability_valid_until=utc_datetime(
                plan["entry_authorization_valid_until"],
                "entry_authorization_valid_until",
            ),
            principal_at_risk_usd=_principal_at_risk(snapshot["positions"]),
            available_cash_usd=snapshot["cash"],
            position_quantity=(
                Decimal("0")
                if position is None
                else _decimal(position["qty"], "qty")
            ),
            position_count=snapshot["position_count"],
            open_order_count=1,
            entry_attempt_count=state.entry_attempt_count,
            exit_attempt_count=state.exit_attempt_count,
            cancel_attempt_count=state.cancel_attempt_count,
            replacement_attempt_count=0,
            loss_context_complete=True,
            cumulative_net_pnl_usd=state.cumulative_net_pnl_usd,
            observed_order_fingerprint=order_fingerprint,
            cancel_target_fingerprint=order_fingerprint,
            account_trading_blocked=snapshot["account_trading_blocked"],
            margin_used=False,
            broker_ambiguity=False,
            unexpected_symbol_exposure=_cross_symbol_exposure(
                snapshot["positions"],
                snapshot["open_orders"],
                str(plan["subject"]["symbol"]),
            ),
        )
        verdict = store.evaluate_and_claim(
            observation,
            claim_fingerprint=claim_fingerprint,
        )["verdict"]
        if (
            verdict.get("local_safety_admitted") is not True
            or verdict.get("claim_recorded") is not True
        ):
            return _action_result(
                "cancel_safety_claim_not_admitted",
                broker_called=False,
                ambiguous=False,
            )
    elif not (
        state.cancel_attempt_count == 1
        and state.last_action_fingerprint == claim_fingerprint
    ):
        return _action_result(
            "cancel_attempt_budget_or_identity_mismatch",
            broker_called=False,
            ambiguous=False,
        )

    identity = DurableCancelIdentity(
        cancel_intent_id=ids["cancel_intent_id"],
        client_order_id=ids["entry_client_order_id"],
        broker_order_id=broker_order_id,
        reservation_run_id=f"v530-cancel-{plan['plan_fingerprint'][:20]}",
        reason="entry_open_at_authorization_expiry",
    )
    coordinator = DurableCancelCoordinator(journal)
    reservation = coordinator.reserve(identity, as_of)
    if reservation.status not in {"reserved", "existing_same_intent"}:
        return _action_result(
            "durable_cancel_identity_conflict",
            broker_called=False,
        )
    broker_called = False
    if reservation.record.state is CancelJournalState.RESERVED:
        lease = coordinator.acquire_lease(
            lease_name=f"v530:{plan['plan_fingerprint']}:cancel",
            owner_run_id=uuid.uuid4().hex,
            occurred_at=as_of,
            ttl_seconds=LEASE_TTL_SECONDS,
        )
        if not lease.acquired:
            return _action_result(
                lease.blocker or "durable_cancel_lease_unavailable",
                broker_called=False,
                ambiguous=False,
            )
        try:
            outcome = coordinator.execute(
                identity=identity,
                lease=lease,
                evidence=DurableCancelEvidence(
                    cancel_allowed=True,
                    snapshot_fresh=True,
                ),
                occurred_at=as_of,
                cancel=lambda: _cancel_order(client, broker_order_id),
                observe=lambda _response: _cancel_observation(
                    client,
                    ids["entry_client_order_id"],
                    symbol=str(plan["subject"]["symbol"]),
                    expected_request=entry_request,
                    expected_broker_order_fingerprint=str(
                        entry_public["broker_order_fingerprint"]
                    ),
                ),
            )
        finally:
            coordinator.release_lease(lease)
        broker_called = outcome.broker_called
        if outcome.status == "blocked":
            return _action_result(
                outcome.blocker or "durable_cancel_blocked",
                broker_called=broker_called,
                ambiguous=False,
            )
    lookup = _lookup_order(
        client,
        ids["entry_client_order_id"],
        symbol=str(plan["subject"]["symbol"]),
        expected_side="buy",
        expected_request=entry_request,
        expected_broker_order_fingerprint=str(
            entry_public["broker_order_fingerprint"]
        ),
    )
    raw_order = lookup["order"]
    if raw_order and _order_status(raw_order) in _TERMINAL_STATUSES:
        observed = _durable_broker_observation(raw_order)
        journal.record_broker_observation(
            ids["entry_client_order_id"],
            as_of,
            broker_order_id=observed.broker_order_id,
            broker_status=observed.broker_status,
            filled_quantity=observed.filled_quantity,
            filled_average_price=observed.filled_average_price,
        )
        return {
            "ambiguous": False,
            "broker_called": broker_called,
            "blockers": [],
            "raw_order": raw_order,
            "order": _public_order(raw_order),
        }
    return _action_result(
        lookup["blocker"] or "cancel_target_not_terminal",
        broker_called=broker_called,
    )


def _read_snapshot(
    client: Any,
    *,
    symbol: str,
    expected_account: str,
    not_before: datetime,
    clock: Callable[[], datetime],
) -> dict[str, Any]:
    integrity_blockers: list[str] = []
    entry_blockers: list[str] = []
    account: dict[str, Any] = {}
    positions: list[dict[str, Any]] = []
    position_count = 0
    open_orders: list[dict[str, Any]] = []
    open_order_count = 0
    raw_open_orders: list[Any] = []
    asset: dict[str, Any] = {}
    market_data_at: datetime | None = None
    market_price = Decimal("0")
    try:
        account = _object_data(client.get_account())
    except Exception:
        integrity_blockers.append("paper_account_read_failed")
    try:
        raw_positions = list(client.get_positions())
        for item in raw_positions:
            try:
                qty = _position_qty(item)
            except ValidationError:
                position_count += 1
                integrity_blockers.append(
                    "account_wide_position_quantity_invalid"
                )
                continue
            if qty == 0:
                continue
            position_count += 1
            position = _public_position(item)
            positions.append(position)
            side = position["side"]
            if side == "short":
                integrity_blockers.append("short_position_observed")
            elif side != "long":
                integrity_blockers.append(
                    "account_wide_position_side_invalid"
                )
    except Exception:
        integrity_blockers.append("account_wide_positions_read_failed")
    try:
        query = AlpacaRecentOrderQuery(
            status_filter="open",
            limit=100,
        )
        orders = list(client.get_orders(query))
        raw_open_orders = orders
        open_order_count = len(orders)
        if open_order_count >= 100:
            integrity_blockers.append(
                "account_wide_open_order_scan_may_be_truncated"
            )
        open_orders = [_public_order(item) for item in orders]
    except Exception:
        integrity_blockers.append("account_wide_open_orders_read_failed")
    try:
        asset = _read_asset(client, symbol)
    except Exception:
        entry_blockers.append("selected_asset_read_failed")
    try:
        market = _read_market_data(client, symbol)
        market_data_at = market["timestamp"]
        market_price = market["price"]
    except Exception:
        entry_blockers.append("timestamped_market_data_read_failed")
    try:
        observed_at = _trusted_clock_time(clock, not_before=not_before)
    except ValidationError:
        observed_at = not_before
        integrity_blockers.append("trusted_clock_invalid")

    status = _text(_field(account, "status")).upper()
    account_blocked, blocking_fields_valid = _account_blocking_state(account)
    if not blocking_fields_valid:
        entry_blockers.append("paper_account_blocking_fields_invalid")
    elif account_blocked:
        entry_blockers.append("paper_account_trading_blocked")
    cash = _nonnegative_decimal(
        _field(account, "cash"),
        "account.cash",
        entry_blockers,
    )
    account_id = _text(
        _field(account, "account_id", "id", "account_number")
    )
    account_binding: dict[str, object] = {}
    if account_id and expected_account and account_id == expected_account:
        try:
            account_binding = build_alpaca_paper_account_binding(
                _normalized_account_for_binding(account),
                expected_account_configured=True,
                expected_account_matched=True,
            )
        except ValidationError:
            integrity_blockers.append("paper_account_binding_failed")
    else:
        integrity_blockers.append("expected_paper_account_mismatch")
    if status not in {"ACTIVE", "ACCOUNT_ACTIVE"}:
        entry_blockers.append("paper_account_not_active")
    if cash < ENTRY_NOTIONAL_USD:
        entry_blockers.append("paper_account_cash_below_ten_usd")
    if (
        _normalize_symbol(_field(asset, "symbol")) != symbol
        or _text(_field(asset, "asset_class", "class")).lower() != "crypto"
        or _field(asset, "tradable") is not True
        or _text(_field(asset, "status")).lower() != "active"
    ):
        entry_blockers.append("selected_asset_not_tradable")
    if market_data_at is not None:
        if market_data_at > observed_at:
            entry_blockers.append("market_data_from_future")
        elif observed_at - market_data_at > timedelta(hours=2):
            entry_blockers.append("market_data_stale")
    return {
        "observed_at": observed_at,
        "broker_read_occurred": True,
        "account_binding": account_binding,
        "cash": cash,
        "account_trading_blocked": account_blocked,
        "positions": positions,
        "position_count": position_count,
        "open_orders": open_orders,
        "raw_open_orders": raw_open_orders,
        "open_order_count": open_order_count,
        "market_data_at": market_data_at,
        "market_price": market_price,
        "blockers": list(dict.fromkeys(integrity_blockers)),
        "entry_blockers": list(dict.fromkeys(entry_blockers)),
    }


def _read_asset(client: Any, symbol: str) -> dict[str, Any]:
    raw = getattr(client, "raw_trading_client", client)
    method = getattr(raw, "get_asset", None)
    if callable(method):
        return _object_data(method(symbol))
    assets = (
        client.list_assets()
        if callable(getattr(client, "list_assets", None))
        else raw.get_all_assets()
    )
    matches = [
        _object_data(item)
        for item in assets
        if _normalize_symbol(_field(item, "symbol")) == symbol
    ]
    if len(matches) != 1:
        raise ValidationError("selected asset observation is not unique.")
    return matches[0]


def _read_market_data(client: Any, symbol: str) -> dict[str, Any]:
    response: Any = None
    raw = getattr(client, "raw_trading_client", client)
    for source in (raw, client):
        for method_name in (
            "get_crypto_latest_trade",
            "get_latest_crypto_trade",
            "get_crypto_latest_quote",
            "get_latest_crypto_quote",
        ):
            method = getattr(source, method_name, None)
            if callable(method):
                response = method(symbol)
                break
        if response is not None:
            break
    if response is None:
        raise ValidationError("timestamped market data is unavailable.")
    value = response
    if isinstance(response, Mapping):
        for key in (symbol, symbol.replace("USD", "/USD")):
            if key in response:
                value = response[key]
                break
    timestamp = utc_datetime(
        _field(value, "timestamp", "t"),
        "market_data.timestamp",
    )
    price = _decimal(
        _field(value, "price", "p", "ask_price", "ap", "bid_price", "bp"),
        "market_data.price",
    )
    if price <= 0:
        raise ValidationError("market data price must be positive.")
    return {"timestamp": timestamp, "price": price}


def _order_request_shape_blocker(
    value: Any,
    request: AlpacaOrderRequest,
    *,
    expected_broker_order_fingerprint: str = "",
) -> str:
    if _text(_field(value, "client_order_id")) != request.client_order_id:
        return "lookup_client_order_id_mismatch"
    if _normalize_symbol(_field(value, "symbol")) != request.symbol:
        return "lookup_symbol_mismatch"
    if _text(_field(value, "side")).lower() != request.side:
        return "lookup_side_mismatch"
    if _text(_field(value, "asset_class", "class")).lower() != (
        request.asset_class
    ):
        return "lookup_asset_class_mismatch"
    type_value = _text(_field(value, "type")).lower()
    order_type_value = _text(_field(value, "order_type")).lower()
    if type_value and order_type_value and type_value != order_type_value:
        return "lookup_order_type_ambiguous"
    if (type_value or order_type_value) != request.order_type:
        return "lookup_order_type_mismatch"
    if _text(_field(value, "time_in_force")).lower() != (
        request.time_in_force
    ):
        return "lookup_time_in_force_mismatch"
    if _field(value, "limit_price") not in (None, ""):
        return "lookup_unexpected_limit_price"

    try:
        observed_qty = _strict_optional_order_decimal(value, "qty")
        observed_notional = _strict_optional_order_decimal(
            value,
            "notional",
        )
    except ValidationError:
        return "lookup_order_sizing_invalid"
    if observed_qty != request.qty:
        return "lookup_order_quantity_mismatch"
    if observed_notional != request.notional:
        return "lookup_order_notional_mismatch"
    if expected_broker_order_fingerprint:
        observed_fingerprint = _text(
            _field(value, "broker_order_fingerprint")
        )
        if not observed_fingerprint:
            broker_id = _text(_field(value, "id", "order_id"))
            observed_fingerprint = (
                ""
                if not broker_id
                else hashlib.sha256(broker_id.encode()).hexdigest()
            )
        if observed_fingerprint != expected_broker_order_fingerprint:
            return "lookup_broker_order_identity_mismatch"
    return ""


def _strict_optional_order_decimal(
    value: Any,
    field_name: str,
) -> Decimal | None:
    raw = _field(value, field_name)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    return _decimal(raw, f"order.{field_name}")


def _broker_order_fingerprint(broker_order_id: object) -> str:
    text = _text(broker_order_id)
    return "" if not text else hashlib.sha256(text.encode()).hexdigest()


def _lookup_order(
    client: Any,
    client_order_id: str,
    *,
    symbol: str,
    expected_side: str,
    expected_request: AlpacaOrderRequest | None = None,
    expected_broker_order_fingerprint: str = "",
) -> dict[str, Any]:
    def identity_blocker(value: Any) -> str:
        if expected_request is not None:
            return _order_request_shape_blocker(
                value,
                expected_request,
                expected_broker_order_fingerprint=(
                    expected_broker_order_fingerprint
                ),
            )
        if _text(_field(value, "client_order_id")) != client_order_id:
            return "lookup_client_order_id_mismatch"
        if _normalize_symbol(_field(value, "symbol")) != symbol:
            return "lookup_symbol_mismatch"
        if _text(_field(value, "side")).lower() != expected_side:
            return "lookup_side_mismatch"
        if expected_broker_order_fingerprint:
            observed = _broker_order_fingerprint(
                _field(value, "id", "order_id")
            )
            if observed != expected_broker_order_fingerprint:
                return "lookup_broker_order_identity_mismatch"
        return ""

    raw = getattr(client, "raw_trading_client", client)
    for method_name in (
        "get_order_by_client_id",
        "get_order_by_client_order_id",
    ):
        method = getattr(raw, method_name, None)
        if callable(method):
            try:
                value = method(client_order_id)
            except Exception:
                continue
            if value is not None:
                blocker = identity_blocker(value)
                return {
                    "order": {} if blocker else value,
                    "blocker": blocker,
                }
    try:
        query = AlpacaRecentOrderQuery(
            status_filter="all",
            limit=100,
            asset_class_filter="crypto",
        )
        orders = list(client.get_orders(query))
    except Exception:
        return {"order": {}, "blocker": "deterministic_order_lookup_failed"}
    if len(orders) >= 100:
        return {"order": {}, "blocker": "order_lookup_may_be_truncated"}
    matches = [
        item
        for item in orders
        if _text(_field(item, "client_order_id")) == client_order_id
    ]
    if len(matches) != 1:
        return {
            "order": {},
            "blocker": (
                "deterministic_order_lookup_absent"
                if not matches
                else "deterministic_order_lookup_not_unique"
            ),
        }
    blocker = identity_blocker(matches[0])
    return {
        "order": {} if blocker else matches[0],
        "blocker": blocker,
    }


def _poll_lookup(
    client: Any,
    client_order_id: str,
    *,
    symbol: str,
    expected_side: str,
    expected_request: AlpacaOrderRequest | None = None,
    expected_broker_order_fingerprint: str = "",
    attempts: int,
    interval_seconds: float,
) -> dict[str, Any]:
    count = max(1, int(attempts))
    interval = max(0.0, float(interval_seconds))
    latest = {"order": {}, "blocker": "deterministic_order_lookup_absent"}
    for index in range(count):
        latest = _lookup_order(
            client,
            client_order_id,
            symbol=symbol,
            expected_side=expected_side,
            expected_request=expected_request,
            expected_broker_order_fingerprint=(
                expected_broker_order_fingerprint
            ),
        )
        if (
            latest["order"]
            and _order_status(latest["order"]) in _TERMINAL_STATUSES
        ):
            return latest
        if index + 1 < count and interval:
            time.sleep(interval)
    return latest


def _cancel_order(client: Any, broker_order_id: str) -> Any:
    raw = getattr(client, "raw_trading_client", client)
    for method_name in ("cancel_order_by_id", "cancel_order"):
        method = getattr(raw, method_name, None)
        if callable(method):
            return method(broker_order_id)
    raise RuntimeError("paper client lacks exact-order cancellation")


def _cancel_observation(
    client: Any,
    client_order_id: str,
    *,
    symbol: str,
    expected_request: AlpacaOrderRequest,
    expected_broker_order_fingerprint: str,
) -> DurableCancelObservation:
    lookup = _lookup_order(
        client,
        client_order_id,
        symbol=symbol,
        expected_side="buy",
        expected_request=expected_request,
        expected_broker_order_fingerprint=(
            expected_broker_order_fingerprint
        ),
    )
    if not lookup["order"]:
        raise ValidationError("cancel target lookup is ambiguous.")
    return DurableCancelObservation(
        broker_status=_order_status(lookup["order"])
    )




def _observe_exact_order(
    value: Any,
    request: AlpacaOrderRequest,
) -> DurableBrokerObservation:
    blocker = _order_request_shape_blocker(value, request)
    if blocker:
        raise ValidationError(blocker)
    return _durable_broker_observation(value)


def _durable_broker_observation(value: Any) -> DurableBrokerObservation:
    broker_order_id = _text(_field(value, "id", "order_id"))
    status = _order_status(value)
    if not broker_order_id or not status:
        raise ValidationError("broker order identity is incomplete.")
    return DurableBrokerObservation(
        broker_order_id=broker_order_id,
        broker_status=status,
        filled_quantity=_decimal_or_none(_field(value, "filled_qty")),
        filled_average_price=_decimal_or_none(
            _field(value, "filled_avg_price")
        ),
    )


def _public_order(value: Any) -> dict[str, object]:
    if not value:
        return {}
    broker_id = _text(_field(value, "id", "order_id"))
    submitted_at = _optional_time(
        _field(value, "submitted_at", "created_at")
    )
    filled_at = _optional_time(_field(value, "filled_at"))
    type_value = _text(_field(value, "type")).lower()
    order_type_value = _text(_field(value, "order_type")).lower()
    payload: dict[str, object] = {
        "client_order_id": _text(_field(value, "client_order_id")),
        "broker_order_fingerprint": _broker_order_fingerprint(broker_id),
        "symbol": _normalize_symbol(_field(value, "symbol")),
        "side": _text(_field(value, "side")).lower(),
        "asset_class": _text(
            _field(value, "asset_class", "class")
        ).lower(),
        "order_type": type_value or order_type_value,
        "time_in_force": _text(_field(value, "time_in_force")).lower(),
        "limit_price": _optional_order_decimal_text(value, "limit_price"),
        "status": _order_status(value),
        "qty": _optional_order_decimal_text(value, "qty"),
        "notional": _optional_order_decimal_text(value, "notional"),
        "filled_qty": _optional_order_decimal_text(value, "filled_qty"),
        "filled_avg_price": _optional_order_decimal_text(
            value,
            "filled_avg_price",
        ),
        "submitted_at": (
            "" if submitted_at is None else submitted_at.isoformat()
        ),
        "filled_at": "" if filled_at is None else filled_at.isoformat(),
    }
    payload["order_fingerprint"] = stable_hash(payload)
    return payload


def _optional_order_decimal_text(value: Any, field_name: str) -> str:
    parsed = _strict_optional_order_decimal(value, field_name)
    return "" if parsed is None else _decimal_text(parsed)


def _latest_order_evidence_time(
    base: datetime,
    *orders: Mapping[str, object],
) -> datetime:
    observed = [base]
    for order in orders:
        for field_name in ("submitted_at", "filled_at"):
            parsed = _optional_time(order.get(field_name))
            if parsed is not None:
                observed.append(parsed)
    return max(observed)


def _public_position(value: Any) -> dict[str, object]:
    qty = _position_qty(value)
    average = _decimal_or_zero(
        _field(value, "avg_entry_price", "average_entry_price")
    )
    market_value = _decimal_or_zero(_field(value, "market_value"))
    unrealized = _decimal_or_none(_field(value, "unrealized_pl"))
    if unrealized is None:
        unrealized = market_value - (average * qty)
    return {
        "symbol": _normalize_symbol(_field(value, "symbol")),
        "qty": _decimal_text(qty),
        "side": _text(_field(value, "side")).lower(),
        "average_entry_price": _decimal_text(average),
        "market_value": _decimal_text(market_value),
        "unrealized_pl": _decimal_text(unrealized),
    }


def _historical_mutation_flags(
    journal: SqliteOrderJournal,
    ids: Mapping[str, object],
) -> dict[str, bool]:
    order_records = (
        journal.get(str(ids["entry_client_order_id"])),
        journal.get(str(ids["exit_client_order_id"])),
    )
    paper_submit_performed = any(
        record is not None and record.state is not OrderJournalState.RESERVED
        for record in order_records
    )
    cancel_record = journal.get_cancel_intent(str(ids["cancel_intent_id"]))
    paper_cancel_performed = (
        cancel_record is not None
        and cancel_record.state is not CancelJournalState.RESERVED
    )
    return {
        "broker_mutation_performed": bool(
            paper_submit_performed or paper_cancel_performed
        ),
        "paper_submit_performed": paper_submit_performed,
        "paper_cancel_performed": paper_cancel_performed,
    }


def _base_result(
    plan: Mapping[str, object],
    *,
    as_of: datetime,
    plan_sha256: str,
) -> dict[str, object]:
    return {
        "schema_version": LIFECYCLE_SCHEMA_VERSION,
        "record_type": LIFECYCLE_RECORD_TYPE,
        "as_of": as_of.isoformat(),
        "subject": dict(plan.get("subject", {})),
        "plan_fingerprint": plan["plan_fingerprint"],
        "plan_source_sha256": plan_sha256,
        "terminal_binding": dict(plan.get("terminal_binding", {})),
        "venue_binding": dict(plan.get("venue_binding", {})),
        "safety_binding": dict(plan.get("safety_binding", {})),
        "account_binding": dict(plan.get("account_binding", {})),
        "authorization": {
            "paper_mutation_authorized": False,
            "network_authorized": False,
            "exact_operation_authorization_matched": False,
            "authorization_fingerprint": "",
            "entry_authorization_valid_until": plan.get(
                "entry_authorization_valid_until",
                "",
            ),
            "risk_reducing_unwind_authorized_for_claimed_entry": False,
            "live_authorized": False,
            "capital_allocation_authorized": False,
        },
        "operator_preflight": {},
        "deterministic_ids": dict(plan.get("deterministic_ids", {})),
        "budgets": dict(BUDGETS),
        "entry_attempt_count": 0,
        "cancel_attempt_count": 0,
        "exit_attempt_count": 0,
        "action_claim_fingerprints": [],
        "entry_final_order": {},
        "exit_final_order": {},
        "final_position_count": -1,
        "final_open_order_count": -1,
        "broker_read_occurred": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "paper_cancel_performed": False,
        "paper_replace_performed": False,
        "paper_close_performed": False,
        "paper_liquidate_performed": False,
        "broker_ambiguity": False,
        "outcome_classification": "blocked_before_broker_read",
        "blockers": [],
        "next_action": "",
        "paper_only": True,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "capital_allocation_authorized": False,
        "live_authorized": False,
        "profit_claim": "none",
        "lifecycle_fingerprint": "",
    }


def _finish_with_state(
    root: Path,
    base: Mapping[str, object],
    *,
    plan: Mapping[str, object],
    state: CryptoBoundedProbeSafetyState,
    outcome: str,
    blockers: Sequence[str],
    next_action: str,
    write_artifacts: bool,
) -> dict[str, object]:
    counts = {
        "entry_attempt_count": state.entry_attempt_count,
        "cancel_attempt_count": state.cancel_attempt_count,
        "exit_attempt_count": state.exit_attempt_count,
    }
    claims = [
        _action_claim_fingerprint(plan, role)
        for role, count in (
            ("entry", state.entry_attempt_count),
            ("cancel", state.cancel_attempt_count),
            ("exit", state.exit_attempt_count),
        )
        if count
    ]
    return _finish(
        root,
        {
            **base,
            **counts,
            "action_claim_fingerprints": claims,
            "outcome_classification": outcome,
            "blockers": list(dict.fromkeys(str(item) for item in blockers)),
            "next_action": next_action,
        },
        plan=plan,
        write_artifacts=write_artifacts,
    )


def _finish(
    root: Path,
    result: Mapping[str, object],
    *,
    plan: Mapping[str, object],
    write_artifacts: bool,
) -> dict[str, object]:
    unsigned = {
        key: value
        for key, value in result.items()
        if key != "lifecycle_fingerprint"
    }
    packet = {**unsigned, "lifecycle_fingerprint": stable_hash(unsigned)}
    if set(packet) != _RESULT_KEYS:
        raise ValidationError("lifecycle receipt keys drifted.")
    if packet["outcome_classification"] == "filled_exit_confirmed":
        validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_receipt(
            packet
        )
    if write_artifacts:
        latest = root / "latest"
        latest.mkdir(parents=True, exist_ok=True)
        plan_bytes = canonical_json_bytes(plan)
        result_bytes = canonical_json_bytes(packet)
        _atomic_write(latest / "lifecycle_plan.json", plan_bytes)
        _atomic_write(latest / "lifecycle_result.json", result_bytes)
        manifest: dict[str, object] = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "record_type": (
                "crypto_tournament_v2_bounded_paper_probe_lifecycle_manifest"
            ),
            "as_of": packet["as_of"],
            "symbol": dict(packet["subject"]).get("symbol", ""),
            "plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
            "receipt_sha256": hashlib.sha256(result_bytes).hexdigest(),
            "operator_source_sha256": hashlib.sha256(
                Path(__file__).resolve().read_bytes()
            ).hexdigest(),
            "outcome_classification": packet["outcome_classification"],
            "entry_attempt_count": packet["entry_attempt_count"],
            "cancel_attempt_count": packet["cancel_attempt_count"],
            "exit_attempt_count": packet["exit_attempt_count"],
            "paper_only": True,
            "live_endpoint_touched": False,
            "credential_values_exposed": False,
            "capital_allocation_authorized": False,
            "live_authorized": False,
        }
        manifest["manifest_fingerprint"] = stable_hash(manifest)
        _atomic_write(latest / "manifest.json", canonical_json_bytes(manifest))
    return packet


def validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_receipt(
    receipt: Mapping[str, object],
) -> None:
    if set(receipt) != _RESULT_KEYS:
        raise ValidationError("target lifecycle receipt keys drifted.")
    unsigned = dict(receipt)
    fingerprint = str(unsigned.pop("lifecycle_fingerprint", ""))
    if fingerprint != stable_hash(unsigned):
        raise ValidationError("target lifecycle receipt fingerprint mismatch.")
    if (
        receipt.get("schema_version") != LIFECYCLE_SCHEMA_VERSION
        or receipt.get("record_type") != LIFECYCLE_RECORD_TYPE
        or receipt.get("outcome_classification") != "filled_exit_confirmed"
        or receipt.get("budgets") != BUDGETS
        or receipt.get("entry_attempt_count") != 1
        or receipt.get("exit_attempt_count") != 1
        or receipt.get("cancel_attempt_count") not in {0, 1}
        or receipt.get("broker_ambiguity") is not False
        or receipt.get("broker_mutation_performed") is not True
        or receipt.get("paper_submit_performed") is not True
        or receipt.get("paper_replace_performed") is not False
        or receipt.get("paper_close_performed") is not False
        or receipt.get("paper_liquidate_performed") is not False
        or receipt.get("paper_only") is not True
        or receipt.get("live_endpoint_touched") is not False
        or receipt.get("credential_values_exposed") is not False
        or receipt.get("capital_allocation_authorized") is not False
        or receipt.get("live_authorized") is not False
        or receipt.get("profit_claim") != "none"
        or receipt.get("final_position_count") != 0
        or receipt.get("final_open_order_count") != 0
        or receipt.get("blockers") != []
    ):
        raise ValidationError("target lifecycle success semantics drifted.")
    validate_alpaca_paper_account_binding(dict(receipt["account_binding"]))
    mapping_fields = (
        "subject",
        "terminal_binding",
        "venue_binding",
        "safety_binding",
        "authorization",
        "operator_preflight",
        "deterministic_ids",
        "account_binding",
        "entry_final_order",
        "exit_final_order",
    )
    if any(
        not isinstance(receipt.get(field), Mapping)
        for field in mapping_fields
    ):
        raise ValidationError("target lifecycle receipt mapping drifted.")
    subject = dict(receipt["subject"])
    authorization = dict(receipt["authorization"])
    preflight = dict(receipt["operator_preflight"])
    ids = dict(receipt["deterministic_ids"])
    safety_binding = dict(receipt["safety_binding"])
    symbol = str(subject.get("symbol", ""))
    expected_id_prefix = f"v530-bounded-probe-{symbol.lower()}-"
    sha_values = (
        receipt.get("plan_fingerprint"),
        receipt.get("plan_source_sha256"),
        authorization.get("authorization_fingerprint"),
        ids.get("execution_plan_id"),
    )
    if (
        subject
        != {
            "asset_class": "crypto",
            "symbol": symbol,
            "environment": "alpaca_paper",
        }
        or symbol not in SUPPORTED_SYMBOLS
        or receipt.get("broker_read_occurred") is not True
        or any(
            len(str(value)) != 64
            or any(
                character not in "0123456789abcdef"
                for character in str(value)
            )
            for value in sha_values
        )
        or set(ids)
        != {
            "execution_plan_id",
            "entry_client_order_id",
            "exit_client_order_id",
            "cancel_intent_id",
        }
        or not str(ids["entry_client_order_id"]).startswith(
            expected_id_prefix + "entry-"
        )
        or not str(ids["exit_client_order_id"]).startswith(
            expected_id_prefix + "exit-"
        )
        or not str(ids["cancel_intent_id"]).startswith(
            expected_id_prefix + "cancel-"
        )
        or safety_binding.get("policy_fingerprint")
        != SAFETY_POLICY_FINGERPRINT
        or not dict(receipt["terminal_binding"])
        or not dict(receipt["venue_binding"])
    ):
        raise ValidationError("target lifecycle provenance envelope drifted.")
    if (
        authorization.get("paper_mutation_authorized") is not True
        or authorization.get("network_authorized") is not True
        or authorization.get("exact_operation_authorization_matched")
        is not True
        or authorization.get(
            "risk_reducing_unwind_authorized_for_claimed_entry"
        )
        is not True
        or authorization.get("live_authorized") is not False
        or authorization.get("capital_allocation_authorized") is not False
        or preflight.get("APP_PROFILE_is_paper") is not True
        or preflight.get("APP_PROFILE_is_live") is not False
        or preflight.get("paper_credentials_present") is not True
        or preflight.get("expected_paper_account_id_loaded") is not True
        or preflight.get("paper_endpoint_exact_match_indicator") is not True
        or preflight.get("live_endpoint_indicator") is not False
        or preflight.get("network_test_flag_enabled") is not False
        or preflight.get("runtime_source_bundle_matched") is not True
    ):
        raise ValidationError("target lifecycle authorization envelope drifted.")
    utc_datetime(
        authorization.get("entry_authorization_valid_until"),
        "authorization.entry_authorization_valid_until",
    )
    expected_claims = [
        _action_claim_fingerprint(receipt, role)
        for role, count in (
            ("entry", receipt["entry_attempt_count"]),
            ("cancel", receipt["cancel_attempt_count"]),
            ("exit", receipt["exit_attempt_count"]),
        )
        if count
    ]
    if receipt.get("action_claim_fingerprints") != expected_claims:
        raise ValidationError("target lifecycle action claims drifted.")
    if (
        receipt.get("paper_cancel_performed") not in {True, False}
        or (
            receipt.get("cancel_attempt_count") == 0
            and receipt.get("paper_cancel_performed") is not False
        )
    ):
        raise ValidationError("target lifecycle cancel evidence drifted.")

    entry = dict(receipt["entry_final_order"])
    exit_order = dict(receipt["exit_final_order"])
    for field_name, order in (
        ("entry_final_order", entry),
        ("exit_final_order", exit_order),
    ):
        unsigned_order = dict(order)
        order_fingerprint = str(
            unsigned_order.pop("order_fingerprint", "")
        )
        broker_fingerprint = str(
            unsigned_order.get("broker_order_fingerprint", "")
        )
        if (
            order_fingerprint != stable_hash(unsigned_order)
            or len(broker_fingerprint) != 64
            or any(
                character not in "0123456789abcdef"
                for character in broker_fingerprint
            )
        ):
            raise ValidationError(
                f"target lifecycle {field_name} fingerprint drifted."
            )
    if (
        entry.get("client_order_id") != ids["entry_client_order_id"]
        or exit_order.get("client_order_id") != ids["exit_client_order_id"]
        or _decimal(entry.get("notional"), "entry.notional")
        != ENTRY_NOTIONAL_USD
    ):
        raise ValidationError("target lifecycle deterministic order drifted.")

    entry_qty = _decimal(entry.get("filled_qty"), "entry.filled_qty")
    exit_qty = _decimal(exit_order.get("filled_qty"), "exit.filled_qty")
    for role, order, request in (
        ("entry", entry, _entry_order_request(receipt)),
        ("exit", exit_order, _exit_order_request(receipt, entry_qty)),
    ):
        blocker = _order_request_shape_blocker(order, request)
        if blocker:
            raise ValidationError(
                "target lifecycle "
                f"{role} request shape drifted: {blocker}."
            )

    entry_submitted = utc_datetime(
        entry.get("submitted_at"),
        "entry.submitted_at",
    )
    entry_filled = utc_datetime(entry.get("filled_at"), "entry.filled_at")
    exit_submitted = utc_datetime(
        exit_order.get("submitted_at"),
        "exit.submitted_at",
    )
    exit_filled = utc_datetime(exit_order.get("filled_at"), "exit.filled_at")
    if (
        entry.get("status") not in {"filled", "canceled", "cancelled"}
        or exit_order.get("status") != "filled"
        or entry.get("side") != "buy"
        or exit_order.get("side") != "sell"
        or entry.get("symbol") != receipt["subject"]["symbol"]
        or exit_order.get("symbol") != receipt["subject"]["symbol"]
        or entry_qty <= 0
        or exit_qty != entry_qty
        or not (
            entry_submitted
            <= entry_filled
            <= exit_submitted
            <= exit_filled
            <= utc_datetime(receipt["as_of"], "receipt.as_of")
        )
    ):
        raise ValidationError("target lifecycle order chronology drifted.")


def _preflight(
    env: Mapping[str, str],
    *,
    expected_account: str,
) -> dict[str, bool]:
    endpoint = (
        env.get("ALPACA_PAPER_BASE_URL", "")
        or DEFAULT_ALPACA_PAPER_BASE_URL
    )
    return {
        "APP_PROFILE_is_paper": env.get("APP_PROFILE", "").lower() == "paper",
        "APP_PROFILE_is_live": env.get("APP_PROFILE", "").lower() == "live",
        "paper_credentials_present": bool(
            env.get("ALPACA_API_KEY") and env.get("ALPACA_SECRET_KEY")
        ),
        "expected_paper_account_id_loaded": bool(expected_account),
        "paper_endpoint_exact_match_indicator": (
            _endpoint(endpoint) == _endpoint(DEFAULT_ALPACA_PAPER_BASE_URL)
        ),
        "live_endpoint_indicator": _live_endpoint(env),
        "network_test_flag_enabled": any(
            env.get(name, "").strip().lower()
            in {"1", "true", "yes", "on"}
            for name in _NETWORK_TEST_FLAG_NAMES
        )
        or "--allow-network"
        in env.get("PYTEST_ADDOPTS", "").strip().lower(),
        **{
            f"{name}_present": bool(env.get(name))
            for name in _CREDENTIAL_NAMES
        },
    }


def _preflight_blockers(preflight: Mapping[str, bool]) -> list[str]:
    checks = (
        ("APP_PROFILE_is_paper", True, "APP_PROFILE_paper_required"),
        ("APP_PROFILE_is_live", False, "APP_PROFILE_live_forbidden"),
        ("paper_credentials_present", True, "paper_credentials_required"),
        (
            "expected_paper_account_id_loaded",
            True,
            "expected_paper_account_id_required",
        ),
        (
            "paper_endpoint_exact_match_indicator",
            True,
            "exact_paper_endpoint_required",
        ),
        ("live_endpoint_indicator", False, "live_endpoint_forbidden"),
        (
            "network_test_flag_enabled",
            False,
            "network_test_flag_must_remain_disabled",
        ),
    )
    return [
        blocker
        for field, expected, blocker in checks
        if preflight.get(field) is not expected
    ]


def _build_client(
    env: Mapping[str, str],
    factory: BrokerClientFactory | None,
) -> Any | None:
    try:
        config = AlpacaPaperConfig(
            app_profile=env["APP_PROFILE"],
            alpaca_api_key=env["ALPACA_API_KEY"],
            alpaca_secret_key=env["ALPACA_SECRET_KEY"],
            alpaca_paper_base_url=(
                env.get("ALPACA_PAPER_BASE_URL")
                or DEFAULT_ALPACA_PAPER_BASE_URL
            ),
        )
        return AlpacaSdkClient(config, sdk_client_factory=factory)
    except Exception:
        return None


def _normalized_env(raw: Mapping[str, str]) -> dict[str, str]:
    env = {
        str(key): str(value).strip()
        for key, value in raw.items()
        if value is not None
    }
    env["ALPACA_API_KEY"] = (
        env.get("ALPACA_API_KEY") or env.get("APCA_API_KEY_ID", "")
    )
    env["ALPACA_SECRET_KEY"] = (
        env.get("ALPACA_SECRET_KEY")
        or env.get("ALPACA_API_SECRET_KEY")
        or env.get("APCA_API_SECRET_KEY", "")
    )
    return env


def _action_claim_fingerprint(
    plan: Mapping[str, object],
    role: str,
) -> str:
    return stable_hash(
        {
            "plan_fingerprint": plan["plan_fingerprint"],
            "execution_plan_id": plan["deterministic_ids"][
                "execution_plan_id"
            ],
            "role": role,
            "policy_fingerprint": plan["safety_binding"][
                "policy_fingerprint"
            ],
        }
    )


def _loss_basis(
    plan: Mapping[str, object],
    snapshot: Mapping[str, Any],
    phase: str,
) -> str:
    return stable_hash(
        {
            "plan_fingerprint": plan["plan_fingerprint"],
            "phase": phase,
            "positions": snapshot["positions"],
            "market_data_at": (
                ""
                if snapshot["market_data_at"] is None
                else snapshot["market_data_at"].isoformat()
            ),
        }
    )


def _principal_at_risk(
    positions: Sequence[Mapping[str, object]],
) -> Decimal:
    total = Decimal("0")
    for position in positions:
        total += abs(
            _decimal(
                position["average_entry_price"],
                "average_entry_price",
            )
            * _decimal(position["qty"], "qty")
        )
    return total


def _cross_symbol_exposure(
    positions: Sequence[Mapping[str, object]],
    orders: Sequence[Mapping[str, object]],
    symbol: str,
) -> bool:
    return any(
        item.get("symbol") != symbol
        for item in (*positions, *orders)
    )


def _single_selected_position(
    positions: Sequence[Mapping[str, object]],
    symbol: str,
) -> Mapping[str, object] | None:
    if len(positions) != 1 or positions[0].get("symbol") != symbol:
        return None
    return positions[0]


def _action_result(
    blocker: str,
    *,
    broker_called: bool,
    ambiguous: bool = True,
) -> dict[str, Any]:
    return {
        "ambiguous": ambiguous,
        "broker_called": broker_called,
        "blockers": [blocker],
        "raw_order": {},
        "order": {},
    }


def _order_status(value: Any) -> str:
    return _text(_field(value, "status")).lower()


def _position_qty(value: Any) -> Decimal:
    qty = _decimal(_field(value, "qty", "quantity"), "position.qty")
    if qty < 0:
        raise ValidationError("position.qty cannot be negative.")
    return qty


def _normalize_symbol(value: object) -> str:
    return _text(value).replace("/", "").replace("-", "").upper()


def _field(value: Any, *names: str) -> Any:
    if isinstance(value, Mapping):
        for name in names:
            if name in value:
                return value[name]
        return None
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
    return None


def _object_data(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    for method_name in ("model_dump", "dict", "to_dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            payload = method()
            if isinstance(payload, Mapping):
                return dict(payload)
    data = getattr(value, "__dict__", None)
    if isinstance(data, Mapping):
        return {
            str(key): item
            for key, item in data.items()
            if not str(key).startswith("_")
        }
    return {}


def _trusted_clock_time(
    clock: Callable[[], datetime],
    *,
    not_before: datetime,
) -> datetime:
    observed = utc_datetime(clock(), "trusted_clock")
    if observed < not_before:
        raise ValidationError("trusted clock regressed.")
    return observed


def _normalized_account_for_binding(
    account: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = dict(account)
    for field_name in ("account_id", "id", "account_number"):
        if field_name in normalized and normalized[field_name] is not None:
            normalized[field_name] = str(normalized[field_name])
    return normalized


def _account_blocking_state(
    account: Mapping[str, Any],
) -> tuple[bool, bool]:
    values: list[bool] = []
    for field_name in ("account_blocked", "trading_blocked"):
        value = _field(account, field_name)
        if type(value) is not bool:
            return True, False
        values.append(value)
    if _field_present(account, "blocked"):
        alias = _field(account, "blocked")
        if type(alias) is not bool:
            return True, False
        values.append(alias)
    return any(values), True


def _field_present(value: Any, name: str) -> bool:
    if isinstance(value, Mapping):
        return name in value
    return hasattr(value, name)


def _optional_time(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return utc_datetime(value, "broker_time")
    except ValidationError:
        return None


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).lower() in {"1", "true", "yes"}


def _text(value: object) -> str:
    if value is None:
        return ""
    raw = getattr(value, "value", value)
    return str(raw).strip()


def _decimal(value: object, field_name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a decimal.") from exc
    if not parsed.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return parsed


def _decimal_or_none(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return _decimal(value, "decimal")
    except ValidationError:
        return None


def _decimal_or_zero(value: object) -> Decimal:
    return _decimal_or_none(value) or Decimal("0")


def _decimal_text(value: Decimal | object) -> str:
    parsed = _decimal(value, "decimal")
    text = format(parsed, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _nonnegative_decimal(
    value: object,
    field_name: str,
    blockers: list[str],
) -> Decimal:
    try:
        parsed = _decimal(value, field_name)
    except ValidationError:
        blockers.append(f"{field_name}_invalid")
        return Decimal("0")
    if parsed < 0:
        blockers.append(f"{field_name}_negative")
        return Decimal("0")
    return parsed


def _first_nonempty(
    values: Mapping[str, str],
    names: Sequence[str],
) -> str:
    return next(
        (values.get(name, "") for name in names if values.get(name)),
        "",
    )


def _endpoint(value: str) -> str:
    return str(value).strip().rstrip("/").lower()


def _live_endpoint(env: Mapping[str, str]) -> bool:
    for name in (
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
    ):
        value = _endpoint(env.get(name, ""))
        if value and value != _endpoint(DEFAULT_ALPACA_PAPER_BASE_URL):
            return True
    return False


def _runtime_source_bundle_sha256() -> str:
    source_root = Path(__file__).resolve().parents[2]
    source_digests: dict[str, str] = {}
    for role, relative_path in sorted(
        LIFECYCLE_RUNTIME_SOURCE_RELATIVE_PATHS.items()
    ):
        path = source_root / relative_path
        if not path.is_file():
            raise ValidationError(
                f"lifecycle runtime source is absent: {role}"
            )
        payload = path.read_bytes()
        if not payload:
            raise ValidationError(
                f"lifecycle runtime source is empty: {role}"
            )
        source_digests[role] = hashlib.sha256(payload).hexdigest()
    return stable_hash(source_digests)


def _path(value: Path | str, field_name: str) -> Path:
    path = Path(value)
    if not str(path).strip():
        raise ValidationError(f"{field_name} is required.")
    return path


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _load_canonical_plan(path: Path | str) -> tuple[dict[str, object], bytes]:
    payload = Path(path).read_bytes()

    def reject_duplicates(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValidationError(
                    "lifecycle plan contains duplicate JSON keys."
                )
            result[key] = value
        return result

    try:
        decoded = payload.decode("utf-8")
        plan = json.loads(decoded, object_pairs_hook=reject_duplicates)
    except UnicodeDecodeError as exc:
        raise ValidationError(
            "lifecycle plan is not canonical JSON."
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(
            "lifecycle plan is not canonical JSON."
        ) from exc
    if not isinstance(plan, dict):
        raise ValidationError("lifecycle plan must be a JSON object.")
    if payload != canonical_json_bytes(plan):
        raise ValidationError("lifecycle plan is not canonical JSON.")
    return plan, payload


def _read_exact_authorization_stdin() -> str:
    stream = getattr(sys.stdin, "buffer", sys.stdin)
    payload = stream.read(4097)
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    if len(payload) > 4096:
        raise ValidationError(
            "exact operation authorization exceeds 4096 bytes."
        )
    try:
        authorization = payload.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise ValidationError(
            "exact operation authorization must be UTF-8."
        ) from exc
    if not authorization or "\x00" in authorization:
        raise ValidationError(
            "exact operation authorization stdin is invalid."
        )
    return authorization


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one exact V5.30 bounded Alpaca-paper lifecycle.",
        allow_abbrev=False,
    )
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--journal-path", default=str(DEFAULT_JOURNAL_PATH))
    parser.add_argument(
        "--safety-state-path",
        default=str(DEFAULT_SAFETY_STATE_PATH),
    )
    parser.add_argument(
        "--exact-operation-authorization-stdin",
        action="store_true",
        required=True,
    )
    parser.add_argument("--paper-mutation-authorized", action="store_true")
    parser.add_argument("--allow-network", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan, plan_bytes = _load_canonical_plan(args.plan)
    authorization = _read_exact_authorization_stdin()
    result = run_crypto_tournament_v2_bounded_paper_probe_lifecycle(
        plan,
        output_root=args.output_root,
        journal_path=args.journal_path,
        safety_state_path=args.safety_state_path,
        plan_source_bytes=plan_bytes,
        exact_operation_authorization=authorization,
        paper_mutation_authorized=args.paper_mutation_authorized,
        allow_network=args.allow_network,
    )
    print(json.dumps(result, sort_keys=True))
    return (
        0
        if result["outcome_classification"] == "filled_exit_confirmed"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
