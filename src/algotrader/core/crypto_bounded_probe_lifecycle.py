"""Pure V5.30 bounded-probe lifecycle plan and receipt contracts."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Any

from algotrader.core.paper_account_binding import (
    validate_alpaca_paper_account_binding,
)
from algotrader.errors import ValidationError


PLAN_SCHEMA_VERSION = (
    "v5_30_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan_v2"
)
LIFECYCLE_SCHEMA_VERSION = (
    "v5_29_crypto_tournament_v2_bounded_paper_probe_lifecycle_v1"
)
MANIFEST_SCHEMA_VERSION = (
    "v5_30_crypto_tournament_v2_bounded_paper_probe_lifecycle_manifest_v1"
)
PLAN_RECORD_TYPE = "crypto_tournament_v2_bounded_paper_probe_lifecycle_plan"
LIFECYCLE_RECORD_TYPE = "crypto_tournament_v2_bounded_paper_probe_lifecycle"
SAFETY_POLICY_FINGERPRINT = (
    "c0abbc047f7bdf01f19d46e06d3824acd980016b4bd992d78dd4994db6d2c407"
)
SUPPORTED_SYMBOLS = ("BTCUSD", "ETHUSD", "SOLUSD")
ENTRY_NOTIONAL_USD = Decimal("10")
ENTRY_AUTHORIZATION_WINDOW = timedelta(minutes=15)
CLIENT_ORDER_ID_PREFIX = "v530-bounded-probe-"
FALSE_PLAN_AUTHORITY = {
    "broker_read_authorized": False,
    "broker_mutation_authorized": False,
    "paper_submit_authorized": False,
    "paper_cancel_authorized": False,
    "paper_exit_authorized": False,
    "paper_mutation_authorized": False,
    "capital_allocation_authorized": False,
    "live_authorized": False,
}
BUDGETS = {
    "maximum_entry_attempts": 1,
    "maximum_exit_attempts": 1,
    "maximum_cancel_attempts_total": 1,
    "maximum_replacements": 0,
    "maximum_close_actions": 0,
    "maximum_liquidate_actions": 0,
}
LIFECYCLE_RUNTIME_SOURCE_RELATIVE_PATHS = {
    "alpaca_client": "algotrader/execution/alpaca_client.py",
    "alpaca_sdk_client": "algotrader/execution/alpaca_sdk_client.py",
    "configuration": "algotrader/config.py",
    "durable_cancel": "algotrader/execution/durable_cancel.py",
    "durable_submit": "algotrader/execution/durable_submit.py",
    "lifecycle_contract": (
        "algotrader/core/crypto_bounded_probe_lifecycle.py"
    ),
    "lifecycle_operator": (
        "algotrader/execution/"
        "crypto_tournament_v2_bounded_paper_probe_lifecycle_operator.py"
    ),
    "order_journal": "algotrader/execution/order_journal.py",
    "paper_account_binding": "algotrader/core/paper_account_binding.py",
    "safety_kernel": (
        "algotrader/execution/crypto_bounded_probe_safety.py"
    ),
}
PLAN_KEYS = {
    "schema_version",
    "record_type",
    "as_of",
    "classification",
    "subject",
    "terminal_binding",
    "venue_binding",
    "safety_binding",
    "account_binding",
    "entry_notional_usd",
    "time_in_force",
    "entry_authorization_valid_until",
    "maximum_duration_hours",
    "budgets",
    "deterministic_ids",
    "plan_identity_fingerprint",
    "required_authorization_sha256",
    "blockers",
    "authority",
    "profit_claim",
    "plan_fingerprint",
}


_TERMINAL_BINDING_KEYS = {
    "selected_symbol",
    "selected_candidate",
    "classification",
    "preregistration_fingerprint",
    "activation_fingerprint",
    "state_fingerprint",
    "terminal_evidence_fingerprint",
    "terminal_closed_at",
    "evidence_export_fingerprint",
    "terminal_source_sha256",
}
_CANDIDATE_KEYS = {
    "candidate_id",
    "symbol",
    "strategy_id",
    "strategy_family",
    "elapsed_hour_parameters",
    "primary_1h_parameters",
    "robustness_4h_parameters",
    "direction",
    "signal_execution",
    "imputed_bar_transition_policy",
    "factory_version",
    "candidate_fingerprint",
}
_VENUE_BINDING_KEYS = {
    "target_symbol",
    "observed_at",
    "bundle_fingerprint",
    "resolved_source_digests",
    "orderability_record",
}
_VENUE_SOURCE_ROLES = {
    "venue_refresh_manifest",
    "venue_universe",
    "orderability_metadata",
    "venue_router_input_manifest",
    "venue_runtime_visibility_status",
    "venue_refresh_source",
    "venue_visibility_operator_source",
    "venue_supervisor_source",
}
_ORDERABILITY_RECORD_KEYS = {
    "symbol",
    "asset_class",
    "source_mode",
    "broker_state_mode",
    "tradable",
    "status",
    "min_notional",
    "min_order_notional",
    "min_order_size",
    "min_trade_increment",
    "price_increment",
    "qty_increment",
    "broker_observed_min_notional",
    "broker_observed_min_order_size",
    "broker_observed_min_trade_increment",
    "broker_observed_price_increment",
    "derived_min_order_value",
    "orderability_basis",
    "metadata_status",
    "metadata_blockers",
    "orderability_status",
    "orderability_blockers",
}

_SAFETY_BINDING_KEYS = {
    "policy_fingerprint",
    "certification_receipt_fingerprint",
    "certification_source_sha256",
    "kernel_source_sha256",
    "certifier_source_sha256",
    "focused_test_source_sha256",
    "runtime_source_bundle_sha256",
    "certified_at",
}


__all__ = [
    "BUDGETS",
    "CLIENT_ORDER_ID_PREFIX",
    "ENTRY_AUTHORIZATION_WINDOW",
    "ENTRY_NOTIONAL_USD",
    "FALSE_PLAN_AUTHORITY",
    "LIFECYCLE_RECORD_TYPE",
    "LIFECYCLE_RUNTIME_SOURCE_RELATIVE_PATHS",
    "LIFECYCLE_SCHEMA_VERSION",
    "MANIFEST_SCHEMA_VERSION",
    "PLAN_RECORD_TYPE",
    "PLAN_SCHEMA_VERSION",
    "SAFETY_POLICY_FINGERPRINT",
    "SUPPORTED_SYMBOLS",
    "build_dormant_lifecycle_plan",
    "build_ready_lifecycle_plan",
    "canonical_json_bytes",
    "exact_operation_authorization_text",
    "stable_hash",
    "utc_datetime",
    "validate_lifecycle_plan",
]


def build_dormant_lifecycle_plan(as_of: datetime | str) -> dict[str, object]:
    evaluated_at = utc_datetime(as_of, "as_of")
    unsigned: dict[str, object] = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "record_type": PLAN_RECORD_TYPE,
        "as_of": evaluated_at.isoformat(),
        "classification": "dormant_pending_terminal_winner",
        "subject": {},
        "terminal_binding": {},
        "venue_binding": {},
        "safety_binding": {},
        "account_binding": {},
        "entry_notional_usd": "10",
        "time_in_force": "gtc",
        "entry_authorization_valid_until": "",
        "maximum_duration_hours": 168,
        "budgets": dict(BUDGETS),
        "deterministic_ids": {},
        "plan_identity_fingerprint": "",
        "required_authorization_sha256": "",
        "blockers": ["v5_25_terminal_winner_not_available"],
        "authority": dict(FALSE_PLAN_AUTHORITY),
        "profit_claim": "none",
    }
    plan = {**unsigned, "plan_fingerprint": stable_hash(unsigned)}
    validate_lifecycle_plan(plan)
    return plan


def build_ready_lifecycle_plan(
    *,
    symbol: str,
    terminal_binding: Mapping[str, object],
    venue_binding: Mapping[str, object],
    safety_binding: Mapping[str, object],
    account_binding: Mapping[str, object],
    as_of: datetime | str,
) -> dict[str, object]:
    selected_symbol = _symbol(symbol)
    evaluated_at = utc_datetime(as_of, "as_of")
    identity_basis: dict[str, object] = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "record_type": PLAN_RECORD_TYPE,
        "subject": {
            "asset_class": "crypto",
            "symbol": selected_symbol,
            "environment": "alpaca_paper",
        },
        "terminal_binding": dict(terminal_binding),
        "venue_binding": dict(venue_binding),
        "safety_binding": dict(safety_binding),
        "account_binding": dict(account_binding),
        "entry_notional_usd": "10",
        "time_in_force": "gtc",
        "entry_authorization_valid_until": (
            evaluated_at + ENTRY_AUTHORIZATION_WINDOW
        ).isoformat(),
        "maximum_duration_hours": 168,
        "budgets": dict(BUDGETS),
    }
    identity_fingerprint = stable_hash(identity_basis)
    unsigned: dict[str, object] = {
        **identity_basis,
        "as_of": evaluated_at.isoformat(),
        "classification": "ready_for_exact_operation_authorization",
        "deterministic_ids": _deterministic_ids(
            selected_symbol,
            identity_fingerprint,
        ),
        "plan_identity_fingerprint": identity_fingerprint,
        "required_authorization_sha256": "",
        "blockers": [],
        "authority": dict(FALSE_PLAN_AUTHORITY),
        "profit_claim": "none",
    }
    unsigned["required_authorization_sha256"] = hashlib.sha256(
        _authorization_text(unsigned).encode("utf-8")
    ).hexdigest()
    plan = {**unsigned, "plan_fingerprint": stable_hash(unsigned)}
    validate_lifecycle_plan(plan)
    return plan


def exact_operation_authorization_text(
    plan: Mapping[str, object],
) -> str:
    validate_lifecycle_plan(plan)
    if plan.get("classification") != "ready_for_exact_operation_authorization":
        raise ValidationError("dormant lifecycle plans cannot be authorized.")
    return _authorization_text(plan)


def validate_lifecycle_plan(plan: Mapping[str, object]) -> None:
    if set(plan) != PLAN_KEYS:
        raise ValidationError("bounded lifecycle plan keys drifted.")
    if (
        plan.get("schema_version") != PLAN_SCHEMA_VERSION
        or plan.get("record_type") != PLAN_RECORD_TYPE
        or plan.get("authority") != FALSE_PLAN_AUTHORITY
        or plan.get("profit_claim") != "none"
    ):
        raise ValidationError("bounded lifecycle plan identity drifted.")
    as_of = utc_datetime(plan.get("as_of"), "plan.as_of")
    unsigned = dict(plan)
    fingerprint = _sha256(
        unsigned.pop("plan_fingerprint"),
        "plan_fingerprint",
    )
    if fingerprint != stable_hash(unsigned):
        raise ValidationError("bounded lifecycle plan fingerprint mismatch.")
    classification = str(plan.get("classification", ""))
    if classification == "dormant_pending_terminal_winner":
        if (
            plan.get("subject") != {}
            or plan.get("terminal_binding") != {}
            or plan.get("venue_binding") != {}
            or plan.get("safety_binding") != {}
            or plan.get("account_binding") != {}
            or plan.get("entry_notional_usd") != "10"
            or plan.get("time_in_force") != "gtc"
            or plan.get("entry_authorization_valid_until") != ""
            or plan.get("maximum_duration_hours") != 168
            or plan.get("budgets") != BUDGETS
            or plan.get("deterministic_ids") != {}
            or plan.get("plan_identity_fingerprint") != ""
            or plan.get("required_authorization_sha256") != ""
            or plan.get("blockers")
            != ["v5_25_terminal_winner_not_available"]
        ):
            raise ValidationError("dormant lifecycle plan is not inert.")
        return
    if classification != "ready_for_exact_operation_authorization":
        raise ValidationError("bounded lifecycle plan classification is invalid.")
    subject = _mapping(plan.get("subject"), "plan.subject")
    symbol = _symbol(subject.get("symbol"))
    if subject != {
        "asset_class": "crypto",
        "symbol": symbol,
        "environment": "alpaca_paper",
    }:
        raise ValidationError("bounded lifecycle plan subject drifted.")
    validate_alpaca_paper_account_binding(
        _mapping(plan.get("account_binding"), "plan.account_binding")
    )
    terminal = _mapping(plan.get("terminal_binding"), "plan.terminal_binding")
    venue = _mapping(plan.get("venue_binding"), "plan.venue_binding")
    safety = _mapping(plan.get("safety_binding"), "plan.safety_binding")
    _validate_ready_bindings(
        terminal,
        venue,
        safety,
        symbol=symbol,
        as_of=as_of,
    )
    if (
        terminal.get("selected_symbol") != symbol
        or venue.get("target_symbol") != symbol
        or safety.get("policy_fingerprint") != SAFETY_POLICY_FINGERPRINT
        or plan.get("entry_notional_usd") != "10"
        or plan.get("time_in_force") != "gtc"
        or plan.get("maximum_duration_hours") != 168
        or plan.get("budgets") != BUDGETS
        or plan.get("blockers") != []
    ):
        raise ValidationError("bounded lifecycle plan binding drifted.")
    valid_until = utc_datetime(
        plan.get("entry_authorization_valid_until"),
        "entry_authorization_valid_until",
    )
    if valid_until != as_of + ENTRY_AUTHORIZATION_WINDOW:
        raise ValidationError("entry authorization window drifted.")
    identity_fingerprint = _sha256(
        plan.get("plan_identity_fingerprint"),
        "plan_identity_fingerprint",
    )
    if identity_fingerprint != stable_hash(_plan_identity_basis(plan)):
        raise ValidationError("lifecycle plan identity fingerprint mismatch.")
    if plan.get("deterministic_ids") != _deterministic_ids(
        symbol,
        identity_fingerprint,
    ):
        raise ValidationError("lifecycle deterministic ids drifted.")
    required_sha = _sha256(
        plan.get("required_authorization_sha256"),
        "required_authorization_sha256",
    )
    if required_sha != hashlib.sha256(
        _authorization_text(plan).encode("utf-8")
    ).hexdigest():
        raise ValidationError("exact operation authorization binding drifted.")


def _validate_ready_bindings(
    terminal: Mapping[str, object],
    venue: Mapping[str, object],
    safety: Mapping[str, object],
    *,
    symbol: str,
    as_of: datetime,
) -> None:
    if set(terminal) != _TERMINAL_BINDING_KEYS:
        raise ValidationError("terminal lifecycle binding keys drifted.")
    candidate = _mapping(
        terminal.get("selected_candidate"),
        "plan.terminal_binding.selected_candidate",
    )
    candidate_unsigned = dict(candidate)
    candidate_fingerprint = _sha256(
        candidate_unsigned.pop("candidate_fingerprint", ""),
        "selected_candidate.candidate_fingerprint",
    )
    strategy_id = str(candidate.get("strategy_id", "")).strip()
    if (
        set(candidate) != _CANDIDATE_KEYS
        or candidate.get("symbol") != symbol
        or not strategy_id
        or candidate.get("candidate_id")
        != f"crypto:tournament_v2:{symbol}:{strategy_id}"
        or not str(candidate.get("strategy_family", "")).strip()
        or candidate.get("direction") != "long_or_cash"
        or candidate.get("signal_execution") != "one_bar_lag"
        or candidate.get("imputed_bar_transition_policy")
        != "hold_prior_target_no_transition"
        or not str(candidate.get("factory_version", "")).strip()
        or any(
            not isinstance(candidate.get(field_name), Mapping)
            for field_name in (
                "elapsed_hour_parameters",
                "primary_1h_parameters",
                "robustness_4h_parameters",
            )
        )
        or candidate_fingerprint != stable_hash(candidate_unsigned)
    ):
        raise ValidationError("terminal selected candidate provenance drifted.")
    if (
        terminal.get("selected_symbol") != symbol
        or terminal.get("classification")
        != "evidence_complete_for_bounded_paper_probe_review"
    ):
        raise ValidationError("terminal lifecycle binding identity drifted.")
    for field_name in (
        "preregistration_fingerprint",
        "activation_fingerprint",
        "state_fingerprint",
        "terminal_evidence_fingerprint",
        "evidence_export_fingerprint",
        "terminal_source_sha256",
    ):
        _sha256(terminal.get(field_name), f"terminal_binding.{field_name}")
    terminal_at = _canonical_time(
        terminal.get("terminal_closed_at"),
        "terminal_binding.terminal_closed_at",
    )
    if terminal_at > as_of:
        raise ValidationError("terminal lifecycle binding is future-dated.")

    if set(venue) != _VENUE_BINDING_KEYS:
        raise ValidationError("venue lifecycle binding keys drifted.")
    venue_at = _canonical_time(
        venue.get("observed_at"),
        "venue_binding.observed_at",
    )
    if venue_at > as_of or as_of - venue_at > timedelta(hours=24):
        raise ValidationError("venue lifecycle binding is stale or future-dated.")
    if venue.get("target_symbol") != symbol:
        raise ValidationError("venue lifecycle symbol binding drifted.")
    _sha256(venue.get("bundle_fingerprint"), "venue_binding.bundle_fingerprint")
    venue_digests = _mapping(
        venue.get("resolved_source_digests"),
        "venue_binding.resolved_source_digests",
    )
    if set(venue_digests) != _VENUE_SOURCE_ROLES:
        raise ValidationError("venue lifecycle source roles drifted.")
    for role, digest in venue_digests.items():
        _sha256(digest, f"venue_binding.resolved_source_digests.{role}")
    record = _mapping(
        venue.get("orderability_record"),
        "venue_binding.orderability_record",
    )
    if (
        set(record) != _ORDERABILITY_RECORD_KEYS
        or record.get("symbol") != symbol
        or record.get("asset_class") != "crypto"
        or record.get("source_mode") != "paper_read_only"
        or record.get("broker_state_mode") != "alpaca_paper_observed"
        or record.get("tradable") is not True
        or record.get("status") != "active"
        or record.get("metadata_status") != "metadata_observed"
        or record.get("metadata_blockers") != []
        or record.get("orderability_status") != "notional_orderable"
        or record.get("orderability_blockers") != []
        or record.get("orderability_basis")
        != "broker_notional_and_qty_metadata"
        or not Decimal("0")
        < _decimal_value(record.get("min_notional"), "min_notional")
        <= ENTRY_NOTIONAL_USD
        or _decimal_value(record.get("min_order_size"), "min_order_size")
        <= 0
        or _decimal_value(
            record.get("min_trade_increment"),
            "min_trade_increment",
        )
        <= 0
    ):
        raise ValidationError("venue lifecycle orderability binding drifted.")

    if set(safety) != _SAFETY_BINDING_KEYS:
        raise ValidationError("safety lifecycle binding keys drifted.")
    if safety.get("policy_fingerprint") != SAFETY_POLICY_FINGERPRINT:
        raise ValidationError("safety lifecycle policy binding drifted.")
    for field_name in (
        "certification_receipt_fingerprint",
        "certification_source_sha256",
        "kernel_source_sha256",
        "certifier_source_sha256",
        "focused_test_source_sha256",
        "runtime_source_bundle_sha256",
    ):
        _sha256(safety.get(field_name), f"safety_binding.{field_name}")
    certified_at = _canonical_time(
        safety.get("certified_at"),
        "safety_binding.certified_at",
    )
    if certified_at > as_of or as_of - certified_at > timedelta(hours=168):
        raise ValidationError("safety lifecycle binding is stale or future-dated.")


def _plan_identity_basis(plan: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": plan["schema_version"],
        "record_type": plan["record_type"],
        "subject": plan["subject"],
        "terminal_binding": plan["terminal_binding"],
        "venue_binding": plan["venue_binding"],
        "safety_binding": plan["safety_binding"],
        "account_binding": plan["account_binding"],
        "entry_notional_usd": plan["entry_notional_usd"],
        "time_in_force": plan["time_in_force"],
        "entry_authorization_valid_until": plan[
            "entry_authorization_valid_until"
        ],
        "maximum_duration_hours": plan["maximum_duration_hours"],
        "budgets": plan["budgets"],
    }


def _deterministic_ids(
    symbol: str,
    identity_fingerprint: str,
) -> dict[str, str]:
    token = identity_fingerprint[:16]
    stem = symbol.lower()
    return {
        "execution_plan_id": identity_fingerprint,
        "entry_client_order_id": (
            f"{CLIENT_ORDER_ID_PREFIX}{stem}-entry-{token}"
        ),
        "exit_client_order_id": (
            f"{CLIENT_ORDER_ID_PREFIX}{stem}-exit-{token}"
        ),
        "cancel_intent_id": f"v530-bounded-probe-{stem}-cancel-{token}",
    }


def _authorization_text(plan: Mapping[str, object]) -> str:
    subject = _mapping(plan.get("subject"), "plan.subject")
    account = _mapping(plan.get("account_binding"), "plan.account_binding")
    ids = _mapping(plan.get("deterministic_ids"), "plan.deterministic_ids")
    return (
        "AUTHORIZE V5.30 ALPACA PAPER BOUNDED LIFECYCLE "
        f"plan={plan.get('plan_identity_fingerprint')} "
        f"account={account.get('account_fingerprint')} "
        f"symbol={subject.get('symbol')} entry_usd=10 "
        f"entry_id={ids.get('entry_client_order_id')} "
        f"exit_id={ids.get('exit_client_order_id')} "
        "entry_attempts=1 cancel_attempts_total=1 exit_attempts=1 "
        "replacements=0 close_actions=0 liquidate_actions=0 live=0 "
        f"entry_valid_until={plan.get('entry_authorization_valid_until')}"
    )


def utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be ISO-8601.") from exc
    else:
        raise ValidationError(f"{field_name} must be a datetime.")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware.")
    return parsed.astimezone(UTC)


def stable_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def canonical_json_bytes(value: Mapping[str, object]) -> bytes:
    return (
        json.dumps(
            dict(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def validate_terminal_evidence_reference(
    pinned: Mapping[str, object],
    reference: Mapping[str, object],
) -> None:
    """Require pinned terminal identity to match a current canonical export."""

    pinned_identity = {
        key: value for key, value in pinned.items() if key != "as_of"
    }
    reference_identity = {
        key: value for key, value in reference.items() if key != "as_of"
    }
    if pinned_identity != reference_identity:
        raise ValidationError(
            "pinned terminal evidence does not match current frozen shadow."
        )


def _mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return dict(value)


def _canonical_time(value: object, field_name: str) -> datetime:
    parsed = utc_datetime(value, field_name)
    if value != parsed.isoformat():
        raise ValidationError(f"{field_name} must be canonical ISO-8601.")
    return parsed


def _decimal_value(value: object, field_name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be decimal.") from exc
    if not parsed.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return parsed


def _symbol(value: object) -> str:
    symbol = str(value).strip().upper()
    if symbol not in SUPPORTED_SYMBOLS:
        raise ValidationError("selected symbol is outside the bounded probe.")
    return symbol


def _sha256(value: object, field_name: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(
        character not in "0123456789abcdef"
        for character in text
    ):
        raise ValidationError(f"{field_name} must be a sha256 digest.")
    return text
