"""M375 read-only SPY paper position close-preview gate."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import AlpacaRecentOrderQuery
from algotrader.execution.paper_lab_snapshot import (
    account_observation_payload,
    order_observation_payloads,
    position_observation_payloads,
    position_symbols,
    recent_order_query_payload,
)

M375_COMMAND = "etf-sma-m375-spy-close-preview"
M375_DEFAULT_RUN_ID = "m375_spy_position_close_preview"
M375_DEFAULT_OUTPUT_PATH = "runs/paper_lab/m375_spy_position_close_preview.jsonl"
M375_EXPECTED_M370C_FILLED_QUANTITY = Decimal("0.033172072")
M375_QUANTITY_MATCH_TOLERANCE = Decimal("0.000000001")
M375_REQUIRED_NEXT_MILESTONE = (
    "M376 - Explicit operator-reviewed SPY paper close submit"
)
M375_SOURCE_POSITION_MILESTONE = "M370C"
M375_SOURCE_RECONCILIATION_MILESTONE = "M374"

READY_FOR_SEPARATE_SPY_CLOSE_SUBMIT_MILESTONE = (
    "ready_for_separate_spy_close_submit_milestone"
)
BLOCKED_OPEN_ORDERS_PRESENT = "blocked_open_orders_present"
BLOCKED_UNEXPECTED_NON_SPY_POSITIONS = "blocked_unexpected_non_spy_positions"
BLOCKED_SPY_POSITION_ABSENT_OR_ZERO = "blocked_spy_position_absent_or_zero"
BLOCKED_SPY_QUANTITY_MISMATCH = "blocked_spy_quantity_mismatch"
BLOCKED_BROKER_OBSERVATION_UNAVAILABLE = "blocked_broker_observation_unavailable"
BLOCKED_PROFILE_GATE_FAILED = "blocked_profile_gate_failed"
BLOCKED_AMBIGUOUS_BROKER_RESPONSE = "blocked_ambiguous_broker_response"

M375_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
    "close_preview_only",
)


def run_m375_spy_close_preview(
    *,
    run_id: str = M375_DEFAULT_RUN_ID,
    output_artifact_path: str | Path | None = M375_DEFAULT_OUTPUT_PATH,
    paper_profile_gate_passed: bool,
    paper_profile_gate_detail: str = "",
    broker_factory: Callable[[], Any] | None,
    redactor: Callable[[str], str] | None = None,
    expected_quantity: Decimal = M375_EXPECTED_M370C_FILLED_QUANTITY,
    quantity_tolerance: Decimal = M375_QUANTITY_MATCH_TOLERANCE,
) -> dict[str, object]:
    """Build a read-only M375 readiness payload from fresh paper observations."""

    sanitize = redactor or (lambda value: value)
    payload = _base_payload(
        run_id=run_id,
        output_artifact_path=output_artifact_path,
        paper_profile_gate_passed=paper_profile_gate_passed,
        paper_profile_gate_detail=paper_profile_gate_detail,
        expected_quantity=expected_quantity,
        quantity_tolerance=quantity_tolerance,
    )
    if not paper_profile_gate_passed:
        return _finalize_payload(
            payload,
            readiness=BLOCKED_PROFILE_GATE_FAILED,
            blockers=("paper_profile_gate_failed",),
        )
    if broker_factory is None:
        return _mark_all_observations_unavailable(
            payload,
            reason="broker_factory_missing",
            message="broker_factory_required",
        )

    try:
        broker = broker_factory()
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _mark_all_observations_unavailable(
            payload,
            reason="broker_factory_failed",
            message=sanitize(str(exc)),
            error_type=exc.__class__.__name__,
        )

    payload = _observe_account(payload, broker, sanitize)
    payload = _observe_positions(payload, broker, sanitize)
    payload = _observe_open_orders(payload, broker, sanitize)
    return _finalize_payload(payload)


def render_m375_spy_close_preview_json(payload: Mapping[str, object]) -> str:
    """Render one deterministic JSONL record."""

    return json.dumps(
        _json_safe(dict(payload)),
        sort_keys=True,
        separators=(",", ":"),
    )


def render_m375_spy_close_preview_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-facing M375 summary."""

    blockers = _string_items(payload.get("blockers"))
    return "\n".join(
        [
            "M375 SPY paper position close preview",
            f"run_id: {_text(payload.get('run_id'))}",
            f"readiness_classification: {_text(payload.get('readiness_classification'))}",
            f"ok: {_bool_text(payload.get('ok'))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            f"submit_authorized: {_bool_text(payload.get('submit_authorized'))}",
            "close_submit_authorized: "
            f"{_bool_text(payload.get('close_submit_authorized'))}",
            "broker_mutation_authorized: "
            f"{_bool_text(payload.get('broker_mutation_authorized'))}",
            "account_observation_available: "
            f"{_bool_text(payload.get('account_observation_available'))}",
            "positions_observation_available: "
            f"{_bool_text(payload.get('positions_observation_available'))}",
            "open_recent_orders_observation_available: "
            f"{_bool_text(payload.get('open_recent_orders_observation_available'))}",
            f"expected_m370c_filled_quantity: {_text(payload.get('expected_m370c_filled_quantity'))}",
            f"observed_spy_quantity: {_text(payload.get('observed_spy_quantity')) or 'none'}",
            "observed_spy_average_entry_price: "
            f"{_text(payload.get('observed_spy_average_entry_price')) or 'none'}",
            "observed_spy_quantity_matches_expected: "
            f"{_bool_text(payload.get('observed_spy_quantity_matches_expected'))}",
            f"non_spy_positions_present: {_bool_text(payload.get('non_spy_positions_present'))}",
            f"open_orders_present: {_bool_text(payload.get('open_orders_present'))}",
            f"blockers: {', '.join(blockers) if blockers else 'none'}",
            f"target_output_artifact: {_text(payload.get('target_output_artifact'))}",
        ]
    )


def write_m375_spy_close_preview_artifact(
    payload: Mapping[str, object],
    output_path: str | Path = M375_DEFAULT_OUTPUT_PATH,
) -> dict[str, object]:
    """Append one M375 JSONL evidence record to the local run artifact."""

    path = _path(output_path, "output_path")
    line = render_m375_spy_close_preview_json(payload) + "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line)
    except OSError as exc:
        raise ValidationError(
            f"M375 SPY close-preview artifact write failed: {exc.__class__.__name__}."
        ) from None
    return {
        "bytes_written": len(line.encode("utf-8")),
        "newline_terminated": True,
        "output_path": str(path),
        "record_count": 1,
    }


def _base_payload(
    *,
    run_id: str,
    output_artifact_path: str | Path | None,
    paper_profile_gate_passed: bool,
    paper_profile_gate_detail: str,
    expected_quantity: Decimal,
    quantity_tolerance: Decimal,
) -> dict[str, object]:
    empty_query = _empty_open_order_query_payload()
    return {
        "account": None,
        "account_cash": "",
        "account_currency": "",
        "account_observation_available": False,
        "asset_class": "equity",
        "blockers": [],
        "broker_action_performed": False,
        "broker_mutation_authorized": False,
        "close_intent_preview": None,
        "close_intent_preview_available": False,
        "close_order_submitted": False,
        "close_preview_only": True,
        "close_submit_authorized": False,
        "command": M375_COMMAND,
        "error": "",
        "expected_m370c_filled_quantity": str(expected_quantity),
        "labels": list(M375_LABELS),
        "live_authorized": False,
        "milestone": "M375",
        "mutated": False,
        "non_spy_position_symbols": [],
        "non_spy_positions_present": False,
        "not_live_authorized": True,
        "observed_spy_average_entry_price": "",
        "observed_spy_quantity": "",
        "observed_spy_quantity_delta": "",
        "observed_spy_quantity_matches_expected": False,
        "ok": False,
        "open_order_count": 0,
        "open_order_symbols": [],
        "open_orders": [],
        "open_orders_present": False,
        "open_recent_orders_observation_available": False,
        "order_type": "market",
        "orders_observation_available": False,
        "paper_lab_only": True,
        "paper_only": True,
        "paper_profile_gate_detail": paper_profile_gate_detail,
        "paper_profile_gate_passed": paper_profile_gate_passed,
        "position_count": 0,
        "position_symbols": [],
        "positions": [],
        "positions_observation_available": False,
        "preview_only": True,
        "profit_claim": "none",
        "quantity_match_tolerance": _decimal_text(quantity_tolerance),
        "readiness_classification": "",
        "redaction": "credentials_redacted",
        "required_next_milestone": M375_REQUIRED_NEXT_MILESTONE,
        "run_id": run_id,
        "side": "sell",
        "source_position_milestone": M375_SOURCE_POSITION_MILESTONE,
        "source_reconciliation_milestone": M375_SOURCE_RECONCILIATION_MILESTONE,
        "spy_position_observed": False,
        "spy_position_status": "unobserved",
        "submitted": False,
        "submit_authorized": False,
        "symbol": "SPY",
        "target_output_artifact": (
            "" if output_artifact_path is None else str(output_artifact_path)
        ),
        "time_in_force": "day",
        "unavailable_observations": [],
        "unavailable_reasons": {},
        **empty_query,
    }


def _observe_account(
    payload: dict[str, object],
    broker: Any,
    redactor: Callable[[str], str],
) -> dict[str, object]:
    try:
        account = account_observation_payload(broker.get_account())
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _mark_observation_unavailable(payload, "account", exc, redactor)

    return {
        **payload,
        "account": account,
        "account_cash": account.get("cash", ""),
        "account_currency": account.get("currency", ""),
        "account_observation_available": True,
    }


def _observe_positions(
    payload: dict[str, object],
    broker: Any,
    redactor: Callable[[str], str],
) -> dict[str, object]:
    try:
        positions = position_observation_payloads(broker.get_positions())
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _mark_observation_unavailable(payload, "positions", exc, redactor)

    position_list = list(positions)
    spy_position = _position_for_symbol(position_list, "SPY")
    observed_quantity = _text(spy_position.get("quantity"))
    observed_average_price = _text(spy_position.get("average_price"))
    position_quantity = _decimal_payload(observed_quantity)
    expected_quantity = _decimal_payload(payload.get("expected_m370c_filled_quantity"))
    tolerance = _decimal_payload(payload.get("quantity_match_tolerance"))
    quantity_delta = (
        position_quantity - expected_quantity
        if position_quantity is not None and expected_quantity is not None
        else None
    )
    quantity_matches = (
        quantity_delta is not None
        and tolerance is not None
        and abs(quantity_delta) <= tolerance
    )
    non_spy_symbols = tuple(
        symbol for symbol in position_symbols(positions) if symbol != "SPY"
    )

    return {
        **payload,
        "non_spy_position_symbols": list(non_spy_symbols),
        "non_spy_positions_present": bool(non_spy_symbols),
        "observed_spy_average_entry_price": observed_average_price,
        "observed_spy_quantity": observed_quantity,
        "observed_spy_quantity_delta": (
            "" if quantity_delta is None else _decimal_text(quantity_delta)
        ),
        "observed_spy_quantity_matches_expected": quantity_matches,
        "position_count": len(position_list),
        "position_symbols": list(position_symbols(positions)),
        "positions": position_list,
        "positions_observation_available": True,
        "spy_position_observed": bool(spy_position),
        "spy_position_status": _spy_position_status(
            position_quantity,
            quantity_matches=quantity_matches,
        ),
    }


def _observe_open_orders(
    payload: dict[str, object],
    broker: Any,
    redactor: Callable[[str], str],
) -> dict[str, object]:
    query = AlpacaRecentOrderQuery(status_filter="open", limit=100)
    query_payload = {
        **recent_order_query_payload(query),
        "recent_order_query_attempted": True,
        "recent_order_query_available": False,
        "recent_order_query_returned_count": 0,
        "open_recent_order_query_attempted": True,
        "open_recent_order_query_available": False,
        "open_recent_order_query_returned_count": 0,
    }
    try:
        open_orders = order_observation_payloads(broker.get_recent_orders(query))
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _mark_observation_unavailable(
            {**payload, **query_payload},
            "open_recent_orders",
            exc,
            redactor,
        )

    open_order_list = list(open_orders)
    query_available = {
        **query_payload,
        "recent_order_query_available": True,
        "recent_order_query_returned_count": len(open_order_list),
        "open_recent_order_query_available": True,
        "open_recent_order_query_returned_count": len(open_order_list),
    }
    return {
        **payload,
        **query_available,
        "open_order_count": len(open_order_list),
        "open_order_symbols": _order_symbols(open_orders),
        "open_orders": open_order_list,
        "open_orders_present": bool(open_order_list),
        "open_recent_orders_observation_available": True,
        "orders_observation_available": True,
    }


def _finalize_payload(
    payload: dict[str, object],
    *,
    readiness: str | None = None,
    blockers: Sequence[str] = (),
) -> dict[str, object]:
    classification = readiness or _classify_readiness(payload)
    all_blockers = tuple(blockers) or _blockers_for_classification(payload, classification)
    ready = classification == READY_FOR_SEPARATE_SPY_CLOSE_SUBMIT_MILESTONE
    close_intent = _close_intent_payload(payload) if ready else None
    return {
        **payload,
        "blockers": list(all_blockers),
        "close_intent_preview": close_intent,
        "close_intent_preview_available": close_intent is not None,
        "error": "" if ready else classification,
        "ok": ready,
        "readiness_classification": classification,
    }


def _classify_readiness(payload: Mapping[str, object]) -> str:
    if payload.get("paper_profile_gate_passed") is not True:
        return BLOCKED_PROFILE_GATE_FAILED
    if payload.get("unavailable_observations"):
        return BLOCKED_BROKER_OBSERVATION_UNAVAILABLE
    if (
        payload.get("account_observation_available") is not True
        or payload.get("positions_observation_available") is not True
        or payload.get("open_recent_orders_observation_available") is not True
    ):
        return BLOCKED_BROKER_OBSERVATION_UNAVAILABLE
    if payload.get("recent_order_query_metadata_complete") is not True:
        return BLOCKED_AMBIGUOUS_BROKER_RESPONSE
    if payload.get("open_orders_present") is True:
        return BLOCKED_OPEN_ORDERS_PRESENT
    if payload.get("non_spy_positions_present") is True:
        return BLOCKED_UNEXPECTED_NON_SPY_POSITIONS
    if payload.get("spy_position_status") == "absent_or_zero":
        return BLOCKED_SPY_POSITION_ABSENT_OR_ZERO
    if payload.get("observed_spy_quantity_matches_expected") is not True:
        return BLOCKED_SPY_QUANTITY_MISMATCH
    return READY_FOR_SEPARATE_SPY_CLOSE_SUBMIT_MILESTONE


def _blockers_for_classification(
    payload: Mapping[str, object],
    classification: str,
) -> tuple[str, ...]:
    if classification == READY_FOR_SEPARATE_SPY_CLOSE_SUBMIT_MILESTONE:
        return ()
    if classification == BLOCKED_BROKER_OBSERVATION_UNAVAILABLE:
        observations = _string_items(payload.get("unavailable_observations"))
        return observations or ("required_broker_observations_unavailable",)
    if classification == BLOCKED_AMBIGUOUS_BROKER_RESPONSE:
        missing = _string_items(payload.get("recent_order_query_metadata_missing_fields"))
        return missing or ("recent_order_query_metadata_incomplete",)
    return (classification,)


def _close_intent_payload(payload: Mapping[str, object]) -> dict[str, object]:
    return {
        "asset_class": "equity",
        "notional": None,
        "order_type": "market",
        "quantity": payload["expected_m370c_filled_quantity"],
        "required_next_milestone": M375_REQUIRED_NEXT_MILESTONE,
        "side": "sell",
        "source_position_milestone": M375_SOURCE_POSITION_MILESTONE,
        "source_reconciliation_milestone": M375_SOURCE_RECONCILIATION_MILESTONE,
        "submit_authorized": False,
        "symbol": "SPY",
        "time_in_force": "day",
    }


def _empty_open_order_query_payload() -> dict[str, object]:
    query = AlpacaRecentOrderQuery(status_filter="open", limit=100)
    return {
        **recent_order_query_payload(query),
        "recent_order_query_attempted": False,
        "recent_order_query_available": False,
        "recent_order_query_returned_count": 0,
        "open_recent_order_query_attempted": False,
        "open_recent_order_query_available": False,
        "open_recent_order_query_returned_count": 0,
    }


def _mark_all_observations_unavailable(
    payload: dict[str, object],
    *,
    reason: str,
    message: str,
    error_type: str = "",
) -> dict[str, object]:
    reasons: dict[str, object] = {}
    for observation in ("account", "positions", "open_recent_orders"):
        reasons[observation] = {
            "error_type": error_type,
            "message": message,
            "reason": reason,
        }
    return _finalize_payload(
        {
            **payload,
            "unavailable_observations": [
                "account",
                "positions",
                "open_recent_orders",
            ],
            "unavailable_reasons": reasons,
        },
        readiness=BLOCKED_BROKER_OBSERVATION_UNAVAILABLE,
    )


def _mark_observation_unavailable(
    payload: dict[str, object],
    observation_name: str,
    exc: Exception,
    redactor: Callable[[str], str],
) -> dict[str, object]:
    unavailable = list(payload.get("unavailable_observations", []))
    if observation_name not in unavailable:
        unavailable.append(observation_name)
    reasons = dict(payload.get("unavailable_reasons", {}))
    reasons[observation_name] = {
        "error_type": exc.__class__.__name__,
        "message": redactor(str(exc)),
    }
    return {
        **payload,
        "unavailable_observations": unavailable,
        "unavailable_reasons": reasons,
    }


def _position_for_symbol(
    positions: Sequence[Mapping[str, object]],
    symbol: str,
) -> Mapping[str, object]:
    for position in positions:
        if str(position.get("symbol", "")).upper() == symbol:
            return position
    return {}


def _spy_position_status(
    quantity: Decimal | None,
    *,
    quantity_matches: bool,
) -> str:
    if quantity is None or quantity <= 0:
        return "absent_or_zero"
    if quantity_matches:
        return "expected_m370c_spy_position_observed"
    return "quantity_mismatch"


def _order_symbols(orders: Sequence[Mapping[str, object]]) -> list[str]:
    symbols = sorted({str(order.get("symbol", "")).upper() for order in orders})
    return [symbol for symbol in symbols if symbol]


def _path(value: str | Path, field_name: str) -> Path:
    if value in (None, ""):
        raise ValidationError(f"{field_name} must be provided.")
    return Path(value)


def _decimal_payload(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _string_items(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


__all__ = [
    "BLOCKED_AMBIGUOUS_BROKER_RESPONSE",
    "BLOCKED_BROKER_OBSERVATION_UNAVAILABLE",
    "BLOCKED_OPEN_ORDERS_PRESENT",
    "BLOCKED_PROFILE_GATE_FAILED",
    "BLOCKED_SPY_POSITION_ABSENT_OR_ZERO",
    "BLOCKED_SPY_QUANTITY_MISMATCH",
    "BLOCKED_UNEXPECTED_NON_SPY_POSITIONS",
    "M375_COMMAND",
    "M375_DEFAULT_OUTPUT_PATH",
    "M375_DEFAULT_RUN_ID",
    "M375_EXPECTED_M370C_FILLED_QUANTITY",
    "M375_QUANTITY_MATCH_TOLERANCE",
    "M375_REQUIRED_NEXT_MILESTONE",
    "READY_FOR_SEPARATE_SPY_CLOSE_SUBMIT_MILESTONE",
    "render_m375_spy_close_preview_json",
    "render_m375_spy_close_preview_text",
    "run_m375_spy_close_preview",
    "write_m375_spy_close_preview_artifact",
]
