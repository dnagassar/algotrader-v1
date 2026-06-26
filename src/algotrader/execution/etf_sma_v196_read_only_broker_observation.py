"""v1.96 read-only paper broker observation for a v1.95 approval packet.

This module performs a scoped paper broker read only after a ready v1.95
approval packet has been loaded. It does not submit, cancel, replace, close,
liquidate, delete, or retry broker actions.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from algotrader.config import (
    DEFAULT_ALPACA_PAPER_BASE_URL,
    PAPER_APP_PROFILE,
    AlpacaPaperConfig,
)
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import AlpacaRecentOrderQuery
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.execution.etf_sma_v195_bounded_paper_drill_approval_packet import (
    APPROVAL_PACKET_READY_NO_MUTATION,
    V195_PACKET_VERSION,
)


V196_RUN_ID = "v196_read_only_broker_observation"
V196_DEFAULT_OUTPUT_ROOT = "runs/paper_lab/v196_read_only_broker_observation"
V196_PACKET_VERSION = "v196_read_only_broker_observation_packet_v1"
V196_MANIFEST_VERSION = "v196_read_only_broker_observation_manifest_v1"
V196_SYMBOL = "SPY"

PAPER_OBSERVATION_ELIGIBLE = (
    "paper_observation_eligible_for_separate_drill_authorization"
)
PAPER_OBSERVATION_BLOCKED_CREDENTIALS_UNAVAILABLE = (
    "paper_observation_blocked_credentials_unavailable"
)
PAPER_OBSERVATION_BLOCKED_EXPECTED_ACCOUNT_MISMATCH = (
    "paper_observation_blocked_expected_account_mismatch"
)
PAPER_OBSERVATION_BLOCKED_LIVE_ENDPOINT_OR_PROFILE = (
    "paper_observation_blocked_live_endpoint_or_profile"
)
PAPER_OBSERVATION_BLOCKED_OPEN_SPY_ORDER_PRESENT = (
    "paper_observation_blocked_open_spy_order_present"
)
PAPER_OBSERVATION_BLOCKED_UNEXPECTED_NON_SPY_POSITION = (
    "paper_observation_blocked_unexpected_non_spy_position"
)
PAPER_OBSERVATION_BLOCKED_DUPLICATE_CLIENT_ORDER_ID = (
    "paper_observation_blocked_duplicate_client_order_id"
)
PAPER_OBSERVATION_BLOCKED_ACCOUNT_NOT_TRADABLE = (
    "paper_observation_blocked_account_not_tradable"
)
PAPER_OBSERVATION_BLOCKED_BROKER_RESPONSE_AMBIGUOUS = (
    "paper_observation_blocked_broker_response_ambiguous"
)
PAPER_OBSERVATION_BLOCKED_APPROVAL_PACKET_MISSING = (
    "paper_observation_blocked_approval_packet_missing"
)
PAPER_OBSERVATION_BLOCKED_APPROVAL_PACKET_NOT_READY = (
    "paper_observation_blocked_approval_packet_not_ready"
)
PAPER_OBSERVATION_BLOCKED_BROKER_READ_SCOPE_VIOLATION = (
    "paper_observation_blocked_broker_read_scope_violation"
)

V196_SAFETY_LABELS = (
    "paper_lab_only",
    "read_only_broker_observation",
    "not_live_authorized",
    "not_paper_submit_authorized",
    "broker_mutation_performed=false",
    "paper_submit_performed=false",
    "profit_claim=none",
)

_APPROVAL_PACKET_NAMES = ("approval_packet.json", "operating_packet.json")
_EXPECTED_ACCOUNT_ENV = "ALPACA_EXPECTED_PAPER_ACCOUNT_ID"
_ACTIVE_ACCOUNT_STATUS_VALUES = {"ACTIVE", "ACCOUNT_STATUS_ACTIVE"}
_MISSING = object()


BrokerClientFactory = Callable[[AlpacaPaperConfig], Any]


@dataclass(frozen=True, slots=True)
class V196BrokerObservation:
    """Sanitized result of the scoped paper broker reads."""

    attestation: Mapping[str, object]
    expected_account_check: Mapping[str, object]
    account_observed: bool = False
    account_summary: Mapping[str, object] | None = None
    positions_observed: bool = False
    positions: tuple[Mapping[str, object], ...] = ()
    open_spy_orders_observed: bool = False
    open_spy_orders: tuple[Mapping[str, object], ...] = ()
    recent_orders_observed: bool = False
    recent_orders: tuple[Mapping[str, object], ...] = ()
    broker_read_performed: bool = False
    broker_read_scope_used: Mapping[str, object] | None = None
    unavailable_observations: tuple[str, ...] = ()
    unavailable_reasons: Mapping[str, object] | None = None


def run_v196_read_only_broker_observation(
    *,
    approval_packet_path: Path | str | None = None,
    approval_search_root: Path | str = "runs/paper_lab",
    output_root: Path | str = V196_DEFAULT_OUTPUT_ROOT,
    run_id: str = V196_RUN_ID,
    timestamp: str | None = None,
    env: Mapping[str, str] | None = None,
    expected_paper_account_id: str | None = None,
    broker_client_factory: BrokerClientFactory | None = None,
) -> dict[str, object]:
    """Load a v1.95 packet, run scoped read-only observations, and write artifacts."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    generated_at = timestamp or _utc_now_text()

    source_path = _resolve_approval_packet_path(
        approval_packet_path=approval_packet_path,
        approval_search_root=approval_search_root,
    )
    if source_path is None:
        packet = _build_packet(
            run_id=run_id,
            timestamp=generated_at,
            output_root=root,
            source_path=Path(str(approval_packet_path or "")),
            source_approval_packet={},
            projected_request_fields={},
            observation=_empty_observation(
                attestation=_empty_attestation(),
                expected_account_check=_expected_account_check(
                    expected_paper_account_id or _expected_account_from_env(env)
                ),
            ),
            classification=PAPER_OBSERVATION_BLOCKED_APPROVAL_PACKET_MISSING,
            blocker="approval_packet_missing",
            next_operator_action="provide_ready_v195_approval_packet_then_rerun_observation",
        )
        _write_artifacts(root, packet)
        return packet

    source_approval_packet = _load_json_object(source_path)
    projected_request_fields = extract_projected_future_paper_request_fields(
        source_approval_packet
    )

    source_classification = str(
        source_approval_packet.get("approval_packet_classification", "")
    )
    if source_classification != APPROVAL_PACKET_READY_NO_MUTATION:
        packet = _build_packet(
            run_id=run_id,
            timestamp=generated_at,
            output_root=root,
            source_path=source_path,
            source_approval_packet=source_approval_packet,
            projected_request_fields=projected_request_fields,
            observation=_empty_observation(
                attestation=_empty_attestation(),
                expected_account_check=_expected_account_check(
                    expected_paper_account_id or _expected_account_from_env(env)
                ),
            ),
            classification=PAPER_OBSERVATION_BLOCKED_APPROVAL_PACKET_NOT_READY,
            blocker="approval_packet_not_ready",
            next_operator_action="regenerate_or_review_v195_approval_packet_before_broker_observation",
        )
        _write_artifacts(root, packet)
        return packet

    scope_blocker = _projected_request_scope_blocker(projected_request_fields)
    if scope_blocker:
        packet = _build_packet(
            run_id=run_id,
            timestamp=generated_at,
            output_root=root,
            source_path=source_path,
            source_approval_packet=source_approval_packet,
            projected_request_fields=projected_request_fields,
            observation=_empty_observation(
                attestation=_empty_attestation(),
                expected_account_check=_expected_account_check(
                    expected_paper_account_id or _expected_account_from_env(env)
                ),
            ),
            classification=PAPER_OBSERVATION_BLOCKED_BROKER_READ_SCOPE_VIOLATION,
            blocker=scope_blocker,
            next_operator_action="return_to_gpt_for_scope_review_before_any_broker_read",
        )
        _write_artifacts(root, packet)
        return packet

    normalized_env = _normalized_paper_env(env)
    expected_account_id = (
        expected_paper_account_id
        if expected_paper_account_id is not None
        else normalized_env.get(_EXPECTED_ACCOUNT_ENV, "")
    )
    paper_config = _paper_config_from_env(normalized_env)
    attestation = _paper_attestation(paper_config)
    expected_account_check = _expected_account_check(expected_account_id)

    profile_blocker = _profile_or_endpoint_blocker(attestation)
    if profile_blocker:
        packet = _build_packet(
            run_id=run_id,
            timestamp=generated_at,
            output_root=root,
            source_path=source_path,
            source_approval_packet=source_approval_packet,
            projected_request_fields=projected_request_fields,
            observation=_empty_observation(
                attestation=attestation,
                expected_account_check=expected_account_check,
            ),
            classification=PAPER_OBSERVATION_BLOCKED_LIVE_ENDPOINT_OR_PROFILE,
            blocker=profile_blocker,
            next_operator_action="fix_paper_profile_and_endpoint_before_rerun",
        )
        _write_artifacts(root, packet)
        return packet

    if not attestation["credentials_available"]:
        packet = _build_packet(
            run_id=run_id,
            timestamp=generated_at,
            output_root=root,
            source_path=source_path,
            source_approval_packet=source_approval_packet,
            projected_request_fields=projected_request_fields,
            observation=_empty_observation(
                attestation=attestation,
                expected_account_check=expected_account_check,
            ),
            classification=PAPER_OBSERVATION_BLOCKED_CREDENTIALS_UNAVAILABLE,
            blocker="paper_credentials_unavailable",
            next_operator_action="load_paper_credentials_in_scoped_broker_read_shell_then_rerun",
        )
        _write_artifacts(root, packet)
        return packet

    expected_account_blocker = _expected_account_blocker(expected_account_check)
    if expected_account_blocker == "expected_paper_account_id_not_configured":
        packet = _build_packet(
            run_id=run_id,
            timestamp=generated_at,
            output_root=root,
            source_path=source_path,
            source_approval_packet=source_approval_packet,
            projected_request_fields=projected_request_fields,
            observation=_empty_observation(
                attestation=attestation,
                expected_account_check=expected_account_check,
            ),
            classification=PAPER_OBSERVATION_BLOCKED_EXPECTED_ACCOUNT_MISMATCH,
            blocker=expected_account_blocker,
            next_operator_action="configure_expected_paper_account_id_before_broker_observation",
        )
        _write_artifacts(root, packet)
        return packet

    try:
        client = (broker_client_factory or AlpacaSdkClient)(paper_config)
    except Exception as exc:  # pragma: no cover - real SDK construction failure path
        observation = _empty_observation(
            attestation=attestation,
            expected_account_check=expected_account_check,
            unavailable_observations=("broker_client",),
            unavailable_reasons={"broker_client": _safe_exception_payload(exc)},
        )
        packet = _build_packet(
            run_id=run_id,
            timestamp=generated_at,
            output_root=root,
            source_path=source_path,
            source_approval_packet=source_approval_packet,
            projected_request_fields=projected_request_fields,
            observation=observation,
            classification=PAPER_OBSERVATION_BLOCKED_BROKER_RESPONSE_AMBIGUOUS,
            blocker="broker_client_construction_failed",
            next_operator_action="review_broker_client_configuration_without_mutation",
        )
        _write_artifacts(root, packet)
        return packet

    observation = _observe_broker(
        client=client,
        symbol=str(projected_request_fields["symbol"]),
        client_order_id=str(projected_request_fields["client_order_id"]),
        attestation=attestation,
        expected_account_id=expected_account_id or "",
    )
    classification, blocker, next_action = _classify_observation(observation)
    packet = _build_packet(
        run_id=run_id,
        timestamp=generated_at,
        output_root=root,
        source_path=source_path,
        source_approval_packet=source_approval_packet,
        projected_request_fields=projected_request_fields,
        observation=observation,
        classification=classification,
        blocker=blocker,
        next_operator_action=next_action,
    )
    _write_artifacts(root, packet)
    return packet


def extract_projected_future_paper_request_fields(
    approval_packet: Mapping[str, object],
) -> dict[str, object]:
    """Extract the future broker request fields from a v1.95 approval packet."""

    projected = _mapping(approval_packet.get("projected_broker_request_fields"))
    return {
        "symbol": _text(
            projected.get("symbol")
            or approval_packet.get("symbol")
            or approval_packet.get("order_symbol")
        ).upper(),
        "side": _text(
            projected.get("side")
            or projected.get("order_side")
            or approval_packet.get("order_side")
        ).lower(),
        "order_type": _text(
            projected.get("order_type") or approval_packet.get("order_type")
        ).lower(),
        "time_in_force": _text(
            projected.get("time_in_force") or approval_packet.get("time_in_force")
        ).lower(),
        "notional": _text(projected.get("notional") or approval_packet.get("notional")),
        "quantity": _text(
            projected.get("quantity")
            or projected.get("qty")
            or approval_packet.get("quantity")
        ),
        "deterministic_client_order_id": _text(
            projected.get("deterministic_client_order_id")
            or projected.get("client_order_id")
            or approval_packet.get("deterministic_client_order_id")
            or approval_packet.get("client_order_id")
        ),
        "client_order_id": _text(
            projected.get("client_order_id")
            or projected.get("deterministic_client_order_id")
            or approval_packet.get("client_order_id")
            or approval_packet.get("deterministic_client_order_id")
        ),
        "cap": {
            "maximum_notional": _text(approval_packet.get("maximum_notional_cap")),
            "maximum_quantity": _text(approval_packet.get("maximum_quantity_cap")),
            "maximum_notional_or_quantity": _text(
                approval_packet.get("maximum_notional_or_quantity_cap")
            ),
            "maximum_notional_or_quantity_kind": _text(
                approval_packet.get("maximum_notional_or_quantity_cap_kind")
            ),
            "source": _text(
                approval_packet.get("maximum_notional_or_quantity_cap_source")
            ),
        },
    }


def locate_latest_v195_approval_packet(
    search_root: Path | str = "runs/paper_lab",
) -> Path | None:
    """Return the newest local v1.95 approval packet under search_root."""

    root = Path(search_root)
    if not root.exists():
        return None

    candidates: list[tuple[str, int, Path]] = []
    for name in _APPROVAL_PACKET_NAMES:
        for path in root.glob(f"**/{name}"):
            if not path.is_file():
                continue
            try:
                payload = _load_json_object(path)
            except ValidationError:
                continue
            if str(payload.get("packet_version", "")) != V195_PACKET_VERSION:
                continue
            created_at = _text(
                payload.get("created_at") or payload.get("generated_at")
            )
            candidates.append((created_at, path.stat().st_mtime_ns, path))

    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item[0], item[1], str(item[2])))[-1][2]


def render_v196_broker_observation_brief(packet: Mapping[str, object]) -> str:
    """Render a concise operator brief without credential material."""

    request = _mapping(packet.get("projected_future_paper_request_fields"))
    account = _mapping(packet.get("paper_account_status"))
    return "\n".join(
        (
            "# v1.96 Read-Only Paper Broker Observation",
            "",
            f"- Classification: `{packet.get('eligibility_classification', '')}`",
            f"- Blocker: `{packet.get('blocker', '')}`",
            f"- Source v1.95 approval packet: `{packet.get('source_v195_approval_packet_path', '')}`",
            f"- Source approval classification: `{packet.get('source_approval_packet_classification', '')}`",
            f"- Symbol / side: `{request.get('symbol', '')}` / `{request.get('side', '')}`",
            f"- Order type / TIF: `{request.get('order_type', '')}` / `{request.get('time_in_force', '')}`",
            f"- Notional / quantity: `{request.get('notional', '')}` / `{request.get('quantity', '')}`",
            f"- Client order id: `{request.get('client_order_id', '')}`",
            f"- Broker read performed: `{_bool_text(packet.get('broker_read_performed'))}`",
            f"- Broker mutation performed: `{_bool_text(packet.get('broker_mutation_performed'))}`",
            f"- Paper submit performed: `{_bool_text(packet.get('paper_submit_performed'))}`",
            f"- Live read performed: `{_bool_text(packet.get('live_read_performed'))}`",
            f"- Account status / tradable / blocker: `{packet.get('account_status', '')}` / `{_bool_text(packet.get('account_tradable'))}` / `{packet.get('account_blocker', '')}`",
            f"- Expected account configured / matched / mode / blocker: `{_bool_text(packet.get('expected_account_configured'))}` / `{_bool_text(packet.get('expected_account_matched'))}` / `{packet.get('expected_account_match_mode', '')}` / `{packet.get('expected_account_blocker', '')}`",
            f"- SPY position observed: `{_bool_text(packet.get('spy_position_observed'))}`",
            f"- Open SPY order observed: `{_bool_text(packet.get('open_spy_order_observed'))}`",
            f"- Unexpected non-SPY position observed: `{_bool_text(packet.get('unexpected_non_spy_position_observed'))}`",
            f"- Duplicate client_order_id observed: `{_bool_text(packet.get('duplicate_client_order_id_observed'))}`",
            f"- Next operator action: `{packet.get('next_operator_action', '')}`",
            "",
        )
    )


def _observe_broker(
    *,
    client: Any,
    symbol: str,
    client_order_id: str,
    attestation: Mapping[str, object],
    expected_account_id: str,
) -> V196BrokerObservation:
    read_scope = _broker_read_scope(symbol=symbol, client_order_id=client_order_id)
    expected_account_check = _expected_account_check(expected_account_id)

    try:
        account_summary = _account_summary(client.get_account())
    except Exception as exc:
        return _empty_observation(
            attestation=attestation,
            expected_account_check=expected_account_check,
            broker_read_performed=True,
            broker_read_scope_used=read_scope,
            unavailable_observations=("account",),
            unavailable_reasons={"account": _safe_exception_payload(exc)},
        )

    expected_account_check = _expected_account_check(
        expected_account_id,
        observed_account_id=_text(account_summary.get("account_id")),
        observed_account_number=_text(account_summary.get("account_number")),
    )

    try:
        positions = tuple(_position_summary(position) for position in client.get_positions())
    except Exception as exc:
        return _empty_observation(
            attestation=attestation,
            expected_account_check=expected_account_check,
            account_observed=True,
            account_summary=account_summary,
            broker_read_performed=True,
            broker_read_scope_used=read_scope,
            unavailable_observations=("positions",),
            unavailable_reasons={"positions": _safe_exception_payload(exc)},
        )

    try:
        open_query = AlpacaRecentOrderQuery(
            status_filter="open",
            limit=100,
            symbol_filter=symbol,
            direction="desc",
            nested=False,
        )
        open_spy_orders = tuple(
            _order_summary(order) for order in client.get_orders(open_query)
        )
    except Exception as exc:
        return _empty_observation(
            attestation=attestation,
            expected_account_check=expected_account_check,
            account_observed=True,
            account_summary=account_summary,
            positions_observed=True,
            positions=positions,
            broker_read_performed=True,
            broker_read_scope_used=read_scope,
            unavailable_observations=("open_spy_orders",),
            unavailable_reasons={"open_spy_orders": _safe_exception_payload(exc)},
        )

    try:
        recent_query = AlpacaRecentOrderQuery(
            status_filter="all",
            limit=100,
            symbol_filter=symbol,
            direction="desc",
            nested=False,
        )
        recent_orders = tuple(
            _order_summary(order) for order in client.get_orders(recent_query)
        )
    except Exception as exc:
        return _empty_observation(
            attestation=attestation,
            expected_account_check=expected_account_check,
            account_observed=True,
            account_summary=account_summary,
            positions_observed=True,
            positions=positions,
            open_spy_orders_observed=True,
            open_spy_orders=open_spy_orders,
            broker_read_performed=True,
            broker_read_scope_used=read_scope,
            unavailable_observations=("recent_client_order_id_lookup",),
            unavailable_reasons={
                "recent_client_order_id_lookup": _safe_exception_payload(exc)
            },
        )

    return V196BrokerObservation(
        attestation=dict(attestation),
        expected_account_check=dict(expected_account_check),
        account_observed=True,
        account_summary=account_summary,
        positions_observed=True,
        positions=positions,
        open_spy_orders_observed=True,
        open_spy_orders=open_spy_orders,
        recent_orders_observed=True,
        recent_orders=recent_orders,
        broker_read_performed=True,
        broker_read_scope_used=read_scope,
    )


def _build_packet(
    *,
    run_id: str,
    timestamp: str,
    output_root: Path,
    source_path: Path,
    source_approval_packet: Mapping[str, object],
    projected_request_fields: Mapping[str, object],
    observation: V196BrokerObservation,
    classification: str,
    blocker: str,
    next_operator_action: str,
) -> dict[str, object]:
    spy_positions = [
        dict(position)
        for position in observation.positions
        if _text(position.get("symbol")).upper() == V196_SYMBOL
    ]
    unexpected_positions = [
        dict(position)
        for position in observation.positions
        if _text(position.get("symbol")).upper() != V196_SYMBOL
    ]
    open_spy_orders = [
        dict(order)
        for order in observation.open_spy_orders
        if _text(order.get("symbol")).upper() == V196_SYMBOL
    ]
    client_order_id = _text(projected_request_fields.get("client_order_id"))
    duplicate_orders = [
        dict(order)
        for order in observation.recent_orders
        if _text(order.get("client_order_id")) == client_order_id
    ]
    account_summary = dict(observation.account_summary or {})
    account_status = {
        "observed": observation.account_observed,
        "status": _text(account_summary.get("status")),
        "trading_blocked": _optional_bool(account_summary.get("trading_blocked")),
        "account_blocked": _optional_bool(account_summary.get("account_blocked")),
        "trade_suspended_by_user": _optional_bool(
            account_summary.get("trade_suspended_by_user")
        ),
    }
    account_blocker = _account_blocker(account_summary)
    expected_account_check = dict(observation.expected_account_check)
    expected_account_blocker = _expected_account_blocker(expected_account_check)
    packet = {
        "packet_version": V196_PACKET_VERSION,
        "run_id": run_id,
        "timestamp": timestamp,
        "generated_at": timestamp,
        "source_v1_95_approval_packet_path": str(source_path) if str(source_path) else "",
        "source_v195_approval_packet_path": str(source_path) if str(source_path) else "",
        "source_approval_packet_classification": _text(
            source_approval_packet.get("approval_packet_classification")
        ),
        "source_approval_packet_ready": (
            _text(source_approval_packet.get("approval_packet_classification"))
            == APPROVAL_PACKET_READY_NO_MUTATION
        ),
        "source_approval_packet_is_authorization": bool(
            source_approval_packet.get("approval_packet_is_authorization") is True
        ),
        "projected_future_paper_request_fields": dict(projected_request_fields),
        "observed_paper_account_attestation": dict(observation.attestation),
        "paper_account_attestation": dict(observation.attestation),
        "expected_account_check": expected_account_check,
        "account_status": account_status["status"],
        "account_trading_blocked": account_status["trading_blocked"],
        "account_blocked": account_status["account_blocked"],
        "account_tradable": account_blocker == "none",
        "account_blocker": account_blocker,
        "observed_account_id_present": (
            expected_account_check.get("observed_account_id_present") is True
        ),
        "observed_account_number_present": (
            expected_account_check.get("observed_account_number_present") is True
        ),
        "expected_account_configured": (
            expected_account_check.get("expected_account_configured") is True
        ),
        "expected_account_id_matched": expected_account_check.get(
            "expected_account_id_matched"
        ),
        "expected_account_number_matched": expected_account_check.get(
            "expected_account_number_matched"
        ),
        "expected_account_matched": expected_account_check.get(
            "expected_account_matched"
        ),
        "expected_account_match_mode": _text(
            expected_account_check.get("expected_account_match_mode")
        ),
        "expected_account_blocker": expected_account_blocker,
        "paper_account_status": account_status,
        "account_observed": observation.account_observed,
        "positions_observed": observation.positions_observed,
        "orders_observed": observation.open_spy_orders_observed,
        "recent_orders_observed": observation.recent_orders_observed,
        "spy_position_observed": bool(spy_positions),
        "spy_position_summary": _summaries_without_empty(spy_positions),
        "open_spy_order_observed": bool(open_spy_orders),
        "open_spy_order_summary": _summaries_without_empty(open_spy_orders),
        "unexpected_non_spy_position_observed": bool(unexpected_positions),
        "unexpected_non_spy_position_summary": _summaries_without_empty(
            unexpected_positions
        ),
        "duplicate_client_order_id_observed": bool(duplicate_orders),
        "duplicate_client_order_id_summary": _summaries_without_empty(
            duplicate_orders
        ),
        "duplicate_client_order_id_lookup_supported": True,
        "broker_read_scope_used": dict(observation.broker_read_scope_used or {}),
        "broker_read_performed": observation.broker_read_performed,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "paper_cancel_performed": False,
        "live_read_performed": False,
        "live_mutation_performed": False,
        "paper_submit_authorized": False,
        "paper_cancel_authorized": False,
        "broker_mutation_authorized": False,
        "eligibility_classification": classification,
        "outcome_classification": classification,
        "blocker": blocker,
        "next_operator_action": next_operator_action,
        "unavailable_observations": list(observation.unavailable_observations),
        "unavailable_reasons": dict(observation.unavailable_reasons or {}),
        "safety_labels": list(V196_SAFETY_LABELS),
        "paper_lab_only": True,
        "read_only_broker_observation": True,
        "not_live_authorized": True,
        "not_paper_submit_authorized": True,
        "profit_claim": "none",
        "artifact_paths": {
            "broker_observation_packet": str(
                output_root / "broker_observation_packet.json"
            ),
            "broker_observation_brief": str(
                output_root / "broker_observation_brief.md"
            ),
            "broker_observation_record": str(
                output_root / "broker_observation_record.jsonl"
            ),
            "manifest": str(output_root / "manifest.jsonl"),
        },
    }
    _validate_packet_safety(packet)
    return _json_safe(packet)


def _classify_observation(
    observation: V196BrokerObservation,
) -> tuple[str, str, str]:
    if observation.unavailable_observations:
        return (
            PAPER_OBSERVATION_BLOCKED_BROKER_RESPONSE_AMBIGUOUS,
            "broker_response_ambiguous",
            "review_read_only_broker_response_before_any_separate_drill_authorization",
        )

    expected_check = observation.expected_account_check
    expected_account_blocker = _expected_account_blocker(expected_check)
    if expected_account_blocker != "none":
        return (
            PAPER_OBSERVATION_BLOCKED_EXPECTED_ACCOUNT_MISMATCH,
            expected_account_blocker,
            "verify_expected_paper_account_without_exposing_account_id",
        )

    account = observation.account_summary or {}
    account_blocker = _account_blocker(account)
    if account_blocker != "none":
        return (
            PAPER_OBSERVATION_BLOCKED_ACCOUNT_NOT_TRADABLE,
            "account_not_tradable_or_blocked",
            "operator_review_paper_account_status_before_any_drill",
        )

    open_spy_orders = [
        order
        for order in observation.open_spy_orders
        if _text(order.get("symbol")).upper() == V196_SYMBOL
    ]
    if open_spy_orders:
        return (
            PAPER_OBSERVATION_BLOCKED_OPEN_SPY_ORDER_PRESENT,
            "open_spy_order_present",
            "operator_review_open_spy_order_without_mutation_before_any_drill",
        )

    unexpected_positions = [
        position
        for position in observation.positions
        if _text(position.get("symbol")).upper() != V196_SYMBOL
    ]
    if unexpected_positions:
        return (
            PAPER_OBSERVATION_BLOCKED_UNEXPECTED_NON_SPY_POSITION,
            "unexpected_non_spy_position",
            "operator_review_unexpected_non_spy_position_without_mutation_before_any_drill",
        )

    read_scope = _mapping(observation.broker_read_scope_used)
    client_order_id = _text(
        _mapping(read_scope.get("recent_client_order_id_lookup")).get(
            "client_order_id"
        )
    )
    if any(
        _text(order.get("client_order_id")) == client_order_id
        for order in observation.recent_orders
    ):
        return (
            PAPER_OBSERVATION_BLOCKED_DUPLICATE_CLIENT_ORDER_ID,
            "duplicate_client_order_id",
            "choose_new_operator_approved_packet_or_wait_for_prior_order_resolution",
        )

    return (
        PAPER_OBSERVATION_ELIGIBLE,
        "none",
        "return_to_gpt_for_separate_bounded_spy_paper_drill_authorization_decision",
    )


def _account_not_tradable(account: Mapping[str, object]) -> bool:
    return _account_blocker(account) != "none"


def _account_blocker(account: Mapping[str, object]) -> str:
    if not account:
        return "account_not_observed"

    status = _text(account.get("status"))
    if not _account_status_is_active(status):
        return "account_status_not_active"

    trading_blocked = _optional_bool(account.get("trading_blocked"))
    if trading_blocked is True:
        return "account_trading_blocked"
    if trading_blocked is not False:
        return "account_trading_blocked_unknown"

    account_blocked = _optional_bool(account.get("account_blocked"))
    if account_blocked is True:
        return "account_blocked"
    if account_blocked is not False:
        return "account_blocked_unknown"

    if _optional_bool(account.get("trade_suspended_by_user")) is True:
        return "account_trade_suspended_by_user"

    return "none"


def _account_status_is_active(status: object) -> bool:
    normalized = _text(status).upper()
    if not normalized:
        return False
    enum_token = normalized.rsplit(".", maxsplit=1)[-1]
    return (
        normalized in _ACTIVE_ACCOUNT_STATUS_VALUES
        or enum_token in _ACTIVE_ACCOUNT_STATUS_VALUES
    )


def _expected_account_blocker(expected_check: Mapping[str, object]) -> str:
    if expected_check.get("expected_account_configured") is not True:
        return "expected_paper_account_id_not_configured"
    matched = expected_check.get("expected_account_matched")
    if matched is True:
        return "none"
    if matched is False:
        return "expected_account_mismatch"
    return "expected_account_match_not_observed"


def _projected_request_scope_blocker(
    projected_request_fields: Mapping[str, object],
) -> str:
    symbol = _text(projected_request_fields.get("symbol")).upper()
    client_order_id = _text(projected_request_fields.get("client_order_id"))
    side = _text(projected_request_fields.get("side")).lower()
    order_type = _text(projected_request_fields.get("order_type")).lower()
    time_in_force = _text(projected_request_fields.get("time_in_force")).lower()
    has_notional_or_quantity = bool(
        _text(projected_request_fields.get("notional"))
        or _text(projected_request_fields.get("quantity"))
    )
    if symbol != V196_SYMBOL:
        return "projected_symbol_outside_authorized_spy_scope"
    if not client_order_id:
        return "projected_client_order_id_missing"
    if side not in {"buy", "sell"}:
        return "projected_side_missing_or_unsupported"
    if order_type != "market":
        return "projected_order_type_outside_authorized_market_scope"
    if time_in_force != "day":
        return "projected_time_in_force_outside_authorized_day_scope"
    if not has_notional_or_quantity:
        return "projected_notional_or_quantity_missing"
    return ""


def _resolve_approval_packet_path(
    *,
    approval_packet_path: Path | str | None,
    approval_search_root: Path | str,
) -> Path | None:
    if approval_packet_path is not None:
        path = Path(approval_packet_path)
        return path if path.exists() and path.is_file() else None
    return locate_latest_v195_approval_packet(approval_search_root)


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValidationError(f"unable to read JSON object from {path}.") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON object in {path}.") from exc
    if not isinstance(parsed, dict):
        raise ValidationError(f"JSON payload in {path} must be an object.")
    return parsed


def _write_artifacts(root: Path, packet: Mapping[str, object]) -> None:
    packet_path = root / "broker_observation_packet.json"
    brief_path = root / "broker_observation_brief.md"
    record_path = root / "broker_observation_record.jsonl"
    manifest_path = root / "manifest.jsonl"

    _write_json(packet_path, packet)
    brief_path.write_text(
        render_v196_broker_observation_brief(packet),
        encoding="utf-8",
    )
    record_path.write_text(
        json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "manifest_version": V196_MANIFEST_VERSION,
        "run_id": packet["run_id"],
        "generated_at": packet["generated_at"],
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "artifacts": {
            "broker_observation_packet": _artifact_entry(packet_path),
            "broker_observation_brief": _artifact_entry(brief_path),
            "broker_observation_record": _artifact_entry(record_path),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _artifact_entry(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def _normalized_paper_env(env: Mapping[str, str] | None) -> dict[str, str]:
    source = dict(os.environ if env is None else env)
    normalized = {str(key): str(value) for key, value in source.items()}
    if not normalized.get("ALPACA_API_KEY") and normalized.get("APCA_API_KEY_ID"):
        normalized["ALPACA_API_KEY"] = normalized["APCA_API_KEY_ID"]
    if not normalized.get("ALPACA_SECRET_KEY"):
        normalized["ALPACA_SECRET_KEY"] = (
            normalized.get("ALPACA_API_SECRET_KEY")
            or normalized.get("APCA_API_SECRET_KEY")
            or ""
        )
    return normalized


def _expected_account_from_env(env: Mapping[str, str] | None) -> str:
    return _normalized_paper_env(env).get(_EXPECTED_ACCOUNT_ENV, "")


def _paper_config_from_env(env: Mapping[str, str]) -> AlpacaPaperConfig:
    return AlpacaPaperConfig(
        app_profile=env.get("APP_PROFILE", ""),
        alpaca_api_key=env.get("ALPACA_API_KEY"),
        alpaca_secret_key=env.get("ALPACA_SECRET_KEY"),
        alpaca_paper_base_url=env.get(
            "ALPACA_PAPER_BASE_URL",
            DEFAULT_ALPACA_PAPER_BASE_URL,
        ),
    )


def _paper_attestation(config: AlpacaPaperConfig) -> dict[str, object]:
    profile = _text(config.app_profile).lower()
    endpoint_url = _text(config.alpaca_paper_base_url)
    host = _endpoint_host(endpoint_url)
    live_endpoint_detected = _live_endpoint_detected(host)
    paper_endpoint_detected = host == "paper-api.alpaca.markets"
    profile_is_paper = profile == PAPER_APP_PROFILE
    return {
        "account_mode": (
            "paper" if profile_is_paper and paper_endpoint_detected else "not_attested"
        ),
        "profile_is_paper": profile_is_paper,
        "profile_attestation": "paper" if profile_is_paper else "not_paper",
        "endpoint_family": (
            "paper"
            if paper_endpoint_detected
            else "live"
            if live_endpoint_detected
            else "unknown"
        ),
        "endpoint_host_attestation": (
            "paper-api.alpaca.markets"
            if paper_endpoint_detected
            else "live_endpoint_detected"
            if live_endpoint_detected
            else "non_paper_or_unknown"
        ),
        "paper_endpoint_detected": paper_endpoint_detected,
        "live_endpoint_detected": live_endpoint_detected,
        "credentials_available": bool(
            _text(config.alpaca_api_key) and _text(config.alpaca_secret_key)
        ),
        "credential_values_exposed": False,
    }


def _profile_or_endpoint_blocker(attestation: Mapping[str, object]) -> str:
    if attestation.get("profile_is_paper") is not True:
        return "app_profile_not_paper"
    if attestation.get("live_endpoint_detected") is True:
        return "live_endpoint_detected"
    if attestation.get("paper_endpoint_detected") is not True:
        return "paper_endpoint_not_attested"
    return ""


def _endpoint_host(url: str) -> str:
    endpoint = _text(url).lower()
    if "://" in endpoint:
        endpoint = endpoint.split("://", maxsplit=1)[1]
    for separator in ("/", "?", "#"):
        endpoint = endpoint.split(separator, maxsplit=1)[0]
    if "@" in endpoint:
        endpoint = endpoint.rsplit("@", maxsplit=1)[1]
    return endpoint.strip()


def _live_endpoint_detected(host: str) -> bool:
    return host == "api.alpaca.markets"


def _expected_account_check(
    expected_account_id: str | None,
    *,
    observed_account_id: str | None = None,
    observed_account_number: str | None = None,
) -> dict[str, object]:
    expected = _text(expected_account_id)
    observed_id = _text(observed_account_id)
    observed_number = _text(observed_account_number)
    configured = bool(expected)
    account_id_matched = (
        (observed_id == expected) if configured and observed_id else None
    )
    account_number_matched = (
        (observed_number == expected) if configured and observed_number else None
    )
    if account_id_matched is True:
        matched = True
        match_mode = "account_id"
    elif account_number_matched is True:
        matched = True
        match_mode = "account_number"
    elif account_id_matched is False or account_number_matched is False:
        matched = False
        match_mode = "none"
    else:
        matched = None
        match_mode = "none"
    return {
        "observed_account_id_present": bool(observed_id),
        "observed_account_number_present": bool(observed_number),
        "expected_account_configured": configured,
        "expected_account_id_matched": account_id_matched,
        "expected_account_number_matched": account_number_matched,
        "expected_account_matched": matched,
        "expected_account_match_mode": match_mode,
    }


def _broker_read_scope(*, symbol: str, client_order_id: str) -> dict[str, object]:
    return {
        "account": {
            "performed": True,
            "scope": "paper_account_profile_status_only",
        },
        "positions": {
            "performed": True,
            "scope": "paper_positions_all_symbols_to_detect_unexpected_non_spy",
        },
        "open_spy_orders": {
            "performed": True,
            "status_filter": "open",
            "symbol_filter": symbol,
        },
        "recent_client_order_id_lookup": {
            "performed": True,
            "status_filter": "all",
            "symbol_filter": symbol,
            "limit": 100,
            "client_order_id": client_order_id,
        },
    }


def _account_summary(account: object) -> dict[str, object]:
    return {
        "account_id": _text(_first_field(account, "account_id", "id")),
        "account_number": _text(_first_field(account, "account_number")),
        "status": _text(_first_field(account, "status")),
        "trading_blocked": _optional_bool(_first_field(account, "trading_blocked")),
        "account_blocked": _optional_bool(_first_field(account, "account_blocked")),
        "trade_suspended_by_user": _optional_bool(
            _first_field(account, "trade_suspended_by_user")
        ),
    }


def _position_summary(position: object) -> dict[str, object]:
    return {
        "symbol": _text(_first_field(position, "symbol")).upper(),
        "quantity": _text(_first_field(position, "quantity", "qty")),
        "notional": _text(_first_field(position, "notional", "market_value")),
        "side": _text(_first_field(position, "side")),
    }


def _order_summary(order: object) -> dict[str, object]:
    return {
        "order_id": _text(_first_field(order, "order_id", "id")),
        "client_order_id": _text(_first_field(order, "client_order_id")),
        "symbol": _text(_first_field(order, "symbol")).upper(),
        "side": _text(_first_field(order, "side")).lower(),
        "status": _text(
            _first_field(order, "status", "normalized_status", "raw_status")
        ).lower(),
        "order_type": _text(_first_field(order, "order_type", "type")).lower(),
        "time_in_force": _text(_first_field(order, "time_in_force")).lower(),
        "quantity": _text(_first_field(order, "quantity", "qty")),
        "notional": _text(_first_field(order, "notional")),
        "submitted_at": _time_text(_first_field(order, "submitted_at")),
        "filled_at": _time_text(_first_field(order, "filled_at")),
    }


def _first_field(value: object, *names: str) -> object:
    for name in names:
        field_value = _field(value, name)
        if field_value is not _MISSING and field_value is not None:
            return field_value
    return ""


def _field(value: object, name: str) -> object:
    if isinstance(value, Mapping):
        return value.get(name, _MISSING)
    if is_dataclass(value):
        names = {field.name for field in fields(value)}
        if name in names:
            return getattr(value, name)
        return _MISSING
    if hasattr(value, name):
        return getattr(value, name)
    return _MISSING


def _empty_observation(
    *,
    attestation: Mapping[str, object],
    expected_account_check: Mapping[str, object],
    account_observed: bool = False,
    account_summary: Mapping[str, object] | None = None,
    positions_observed: bool = False,
    positions: Sequence[Mapping[str, object]] = (),
    open_spy_orders_observed: bool = False,
    open_spy_orders: Sequence[Mapping[str, object]] = (),
    recent_orders_observed: bool = False,
    recent_orders: Sequence[Mapping[str, object]] = (),
    broker_read_performed: bool = False,
    broker_read_scope_used: Mapping[str, object] | None = None,
    unavailable_observations: Sequence[str] = (),
    unavailable_reasons: Mapping[str, object] | None = None,
) -> V196BrokerObservation:
    return V196BrokerObservation(
        attestation=dict(attestation),
        expected_account_check=dict(expected_account_check),
        account_observed=account_observed,
        account_summary=dict(account_summary or {}),
        positions_observed=positions_observed,
        positions=tuple(dict(position) for position in positions),
        open_spy_orders_observed=open_spy_orders_observed,
        open_spy_orders=tuple(dict(order) for order in open_spy_orders),
        recent_orders_observed=recent_orders_observed,
        recent_orders=tuple(dict(order) for order in recent_orders),
        broker_read_performed=broker_read_performed,
        broker_read_scope_used=dict(broker_read_scope_used or {}),
        unavailable_observations=tuple(unavailable_observations),
        unavailable_reasons=dict(unavailable_reasons or {}),
    )


def _empty_attestation() -> dict[str, object]:
    return {
        "account_mode": "not_observed",
        "profile_is_paper": False,
        "profile_attestation": "not_observed",
        "endpoint_family": "not_observed",
        "endpoint_host_attestation": "not_observed",
        "paper_endpoint_detected": False,
        "live_endpoint_detected": False,
        "credentials_available": False,
        "credential_values_exposed": False,
    }


def _safe_exception_payload(exc: Exception) -> dict[str, object]:
    return {
        "error_type": exc.__class__.__name__,
        "message": "broker_read_failed_sanitized_no_credentials_exposed",
    }


def _validate_packet_safety(packet: Mapping[str, object]) -> None:
    for field_name in (
        "broker_mutation_performed",
        "paper_submit_performed",
        "paper_cancel_performed",
        "live_read_performed",
        "live_mutation_performed",
        "paper_submit_authorized",
        "paper_cancel_authorized",
        "broker_mutation_authorized",
    ):
        if packet.get(field_name) is not False:
            raise ValidationError(f"{field_name} must remain false.")
    attestation = _mapping(packet.get("paper_account_attestation"))
    if attestation.get("credential_values_exposed") is not False:
        raise ValidationError("credential values must not be exposed.")


def _summaries_without_empty(
    rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for row in rows:
        result.append({key: value for key, value in row.items() if _text(value)})
    return result


def _mapping(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _optional_bool(value: object) -> bool | None:
    if value is None or value is _MISSING or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return None


def _text(value: object) -> str:
    if value is None or value is _MISSING:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    return str(value).strip()


def _time_text(value: object) -> str:
    if value is None or value is _MISSING:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _bool_text(value: object) -> str:
    return "true" if value is True else "false" if value is False else ""


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


__all__ = [
    "PAPER_OBSERVATION_BLOCKED_ACCOUNT_NOT_TRADABLE",
    "PAPER_OBSERVATION_BLOCKED_APPROVAL_PACKET_MISSING",
    "PAPER_OBSERVATION_BLOCKED_APPROVAL_PACKET_NOT_READY",
    "PAPER_OBSERVATION_BLOCKED_BROKER_READ_SCOPE_VIOLATION",
    "PAPER_OBSERVATION_BLOCKED_BROKER_RESPONSE_AMBIGUOUS",
    "PAPER_OBSERVATION_BLOCKED_CREDENTIALS_UNAVAILABLE",
    "PAPER_OBSERVATION_BLOCKED_DUPLICATE_CLIENT_ORDER_ID",
    "PAPER_OBSERVATION_BLOCKED_EXPECTED_ACCOUNT_MISMATCH",
    "PAPER_OBSERVATION_BLOCKED_LIVE_ENDPOINT_OR_PROFILE",
    "PAPER_OBSERVATION_BLOCKED_OPEN_SPY_ORDER_PRESENT",
    "PAPER_OBSERVATION_BLOCKED_UNEXPECTED_NON_SPY_POSITION",
    "PAPER_OBSERVATION_ELIGIBLE",
    "V196_DEFAULT_OUTPUT_ROOT",
    "V196_RUN_ID",
    "V196_SAFETY_LABELS",
    "extract_projected_future_paper_request_fields",
    "locate_latest_v195_approval_packet",
    "render_v196_broker_observation_brief",
    "run_v196_read_only_broker_observation",
]
