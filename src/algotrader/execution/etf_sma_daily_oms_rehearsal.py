"""Offline daily ExecutionPlan to Paper OMS rehearsal.

This module is deterministic and fixture-only. It does not select, construct,
or import a real broker client.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL, AlpacaPaperConfig
from algotrader.execution.etf_sma_daily_paper_lab import EtfSmaDailyExecutionPlan
from algotrader.execution.paper_mutation_oms import (
    OFFLINE_FIXTURE_BROKER_STATE_MODE,
    OFFLINE_OMS_REHEARSAL_MODE,
    PaperCertificationRuntime,
    PaperMutationGateway,
    evaluate_strategy_plan_mutation_lane,
    run_paper_certification_drill,
)

V191_RUN_ID = "v191_offline_oms_rehearsal"
V191_DEFAULT_OUTPUT_ROOT = "runs/paper_lab/v191_offline_oms_rehearsal"
V191_PACKET_VERSION = "v191_offline_oms_rehearsal_packet_v1"
V191_RECONCILIATION_VERSION = "v191_offline_oms_rehearsal_reconciliation_v1"
V191_MANIFEST_VERSION = "v191_offline_oms_rehearsal_manifest_v1"
V191_CLIENT_ORDER_ID_PREFIX = "v191-spy"
V191_SAFETY_LABELS = (
    "paper_lab_only",
    "offline_only",
    "not_live_authorized",
    "profit_claim=none",
    "paper_submit_authorized=false",
)
TERMINAL_OMS_OUTCOMES = frozenset(
    {
        "ambiguous_submit_reconciled",
        "submitted_cancel_confirmed",
        "submitted_then_rejected",
        "submitted_partial_fill_then_cancelled",
        "submitted_filled_before_cancel",
        "cancel_ambiguous_reconciled",
        "blocked_duplicate_client_order_id",
        "not_submitted_hold_noop",
    }
)
UNRESOLVED_OMS_OUTCOMES = frozenset(
    {
        "unresolved_order_outcome",
        "ambiguous_submit_unresolved",
        "cancel_ambiguous_unresolved",
    }
)
ACTIONABLE_PLAN_ACTIONS = frozenset({"buy_preview", "sell_preview"})
HOLD_PLAN_ACTIONS = frozenset({"hold/noop", "hold", "noop"})
REQUIRED_EXECUTION_PLAN_FIELDS = (
    "execution_plan_version",
    "execution_plan_id",
    "execution_plan_status",
    "execution_plan_action",
    "execution_plan_symbol",
    "execution_plan_reason",
    "execution_plan_blocker",
    "execution_plan_source_preview_decision",
    "execution_plan_requires_approval",
    "execution_plan_broker_order_required",
    "execution_plan_submit_allowed",
    "execution_plan_paper_submit_authorized",
    "execution_plan_live_authorized",
    "execution_plan_broker_mutation_performed",
    "execution_plan_created_order_payload",
    "execution_plan_labels",
)


@dataclass(frozen=True, slots=True)
class OfflineOmsFixture:
    """Explicit offline broker-state fixture for the fake OMS client."""

    account_id: str = "offline-fixture-paper-account"
    positions: tuple[Mapping[str, Any], ...] = field(default_factory=lambda: (_spy_position(),))
    open_orders: tuple[Mapping[str, Any], ...] = ()
    all_orders: tuple[Mapping[str, Any], ...] = ()
    asset: Mapping[str, Any] = field(default_factory=lambda: _active_spy_asset())
    submit_status: str = "accepted"
    submit_exception_message: str = ""
    ambiguous_creates_order: bool = False
    cancel_status: str = "canceled"
    cancel_filled_qty: str = "0"
    cancel_exception_message: str = ""
    cancel_status_on_exception: str = ""
    lookup_sequence: tuple[Mapping[str, Any] | None, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "account_id", str(self.account_id).strip())
        object.__setattr__(self, "positions", tuple(dict(item) for item in self.positions))
        object.__setattr__(self, "open_orders", tuple(dict(item) for item in self.open_orders))
        object.__setattr__(self, "all_orders", tuple(dict(item) for item in self.all_orders))
        object.__setattr__(self, "asset", dict(self.asset))
        object.__setattr__(
            self,
            "lookup_sequence",
            tuple(None if item is None else dict(item) for item in self.lookup_sequence),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "positions": [dict(item) for item in self.positions],
            "open_orders": [dict(item) for item in self.open_orders],
            "all_orders": [dict(item) for item in self.all_orders],
            "asset": dict(self.asset),
            "submit_status": self.submit_status,
            "submit_exception_message": bool(self.submit_exception_message),
            "ambiguous_creates_order": self.ambiguous_creates_order,
            "cancel_status": self.cancel_status,
            "cancel_filled_qty": self.cancel_filled_qty,
            "cancel_exception_message": bool(self.cancel_exception_message),
            "cancel_status_on_exception": self.cancel_status_on_exception,
            "lookup_sequence_count": len(self.lookup_sequence),
        }


class OfflinePaperOmsFakeClient:
    """Minimal deterministic fake client for the PaperMutationGateway."""

    def __init__(self, fixture: OfflineOmsFixture) -> None:
        self.account_id = fixture.account_id
        self.positions = [dict(item) for item in fixture.positions]
        self.open_orders = [dict(item) for item in fixture.open_orders]
        self.all_orders = [dict(item) for item in fixture.all_orders]
        self.asset = dict(fixture.asset)
        self.submit_status = fixture.submit_status
        self.submit_exception_message = fixture.submit_exception_message
        self.ambiguous_creates_order = fixture.ambiguous_creates_order
        self.cancel_status = fixture.cancel_status
        self.cancel_filled_qty = fixture.cancel_filled_qty
        self.cancel_exception_message = fixture.cancel_exception_message
        self.cancel_status_on_exception = fixture.cancel_status_on_exception
        self.lookup_sequence = list(fixture.lookup_sequence)
        self.calls: list[str] = []
        self.submitted_requests: list[Any] = []
        self.cancelled_order_ids: list[str] = []
        self.current_order: dict[str, Any] | None = None

    @property
    def raw_trading_client(self) -> "OfflinePaperOmsFakeClient":
        return self

    def get_account(self) -> dict[str, Any]:
        self.calls.append("get_account")
        return {
            "account_id": self.account_id,
            "status": "ACTIVE",
            "currency": "USD",
        }

    def get_positions(self) -> list[dict[str, Any]]:
        self.calls.append("get_positions")
        return [dict(position) for position in self.positions]

    def get_orders(self, query: Any) -> list[dict[str, Any]]:
        status_filter = str(getattr(query, "status_filter", ""))
        self.calls.append(f"get_orders:{status_filter}")
        if status_filter == "open":
            return [dict(order) for order in self.open_orders]
        return [dict(order) for order in self.all_orders]

    def get_asset(self, symbol: str) -> dict[str, Any]:
        self.calls.append(f"get_asset:{symbol}")
        return dict(self.asset)

    def submit_order(self, request: Any) -> dict[str, Any]:
        self.calls.append("submit_order")
        self.submitted_requests.append(request)
        request_payload = _request_payload_from_object(request)
        if self.submit_exception_message:
            if self.ambiguous_creates_order:
                self.current_order = _order(
                    client_order_id=request_payload["client_order_id"],
                    status="accepted",
                    side=request_payload["side"],
                    qty=request_payload["quantity"],
                    notional=request_payload["notional"],
                    order_type=request_payload["order_type"],
                    time_in_force=request_payload["time_in_force"],
                    limit_price=request_payload["limit_price"],
                )
                self.all_orders = [dict(self.current_order)]
                self.open_orders = [dict(self.current_order)]
            raise RuntimeError(self.submit_exception_message)

        self.current_order = _order(
            client_order_id=request_payload["client_order_id"],
            status=self.submit_status,
            side=request_payload["side"],
            qty=request_payload["quantity"],
            notional=request_payload["notional"],
            order_type=request_payload["order_type"],
            time_in_force=request_payload["time_in_force"],
            limit_price=request_payload["limit_price"],
        )
        self.all_orders = [dict(self.current_order)]
        self.open_orders = (
            [dict(self.current_order)]
            if self.submit_status not in {"rejected", "filled"}
            else []
        )
        return dict(self.current_order)

    def get_order_by_client_id(self, client_order_id: str) -> dict[str, Any] | None:
        self.calls.append(f"get_order_by_client_id:{client_order_id}")
        if self.lookup_sequence:
            next_order = self.lookup_sequence.pop(0)
            if next_order is not None:
                self.current_order = dict(next_order)
                self.all_orders = [dict(self.current_order)]
                self.open_orders = (
                    []
                    if _normalized_status(self.current_order.get("status"))
                    in {"canceled", "cancelled", "rejected", "filled", "expired"}
                    else [dict(self.current_order)]
                )
            return None if next_order is None else dict(next_order)
        if (
            self.current_order is not None
            and self.current_order.get("client_order_id") == client_order_id
        ):
            return dict(self.current_order)
        for order in self.all_orders:
            if order.get("client_order_id") == client_order_id:
                self.current_order = dict(order)
                return dict(order)
        return None

    def cancel_order_by_id(self, order_id: str) -> dict[str, Any]:
        self.calls.append(f"cancel_order_by_id:{order_id}")
        self.cancelled_order_ids.append(order_id)
        if self.current_order is None:
            for order in self.all_orders:
                if str(order.get("id", order.get("order_id", ""))) == order_id:
                    self.current_order = dict(order)
                    break
        if self.cancel_exception_message:
            if self.cancel_status_on_exception and self.current_order is not None:
                self.current_order = {
                    **self.current_order,
                    "status": self.cancel_status_on_exception,
                    "filled_qty": Decimal(str(self.cancel_filled_qty)),
                }
                self.all_orders = [dict(self.current_order)]
                self.open_orders = (
                    []
                    if _normalized_status(self.cancel_status_on_exception)
                    in {"canceled", "cancelled", "rejected", "filled", "expired"}
                    else [dict(self.current_order)]
                )
            raise RuntimeError(self.cancel_exception_message)
        if self.current_order is not None:
            self.current_order = {
                **self.current_order,
                "status": self.cancel_status,
                "filled_qty": Decimal(str(self.cancel_filled_qty)),
            }
            self.all_orders = [dict(self.current_order)]
            self.open_orders = []
        return {"id": order_id, "status": "accepted"}


@dataclass(frozen=True, slots=True)
class _OfflineRehearsalOrderRequest:
    """Request-shaped object used only by the fake offline rehearsal gateway."""

    client_order_id: str
    symbol: str
    side: str
    asset_class: str
    qty: Decimal | None = None
    notional: Decimal | None = None
    order_type: str = "limit"
    time_in_force: str = "day"
    limit_price: Decimal | None = None


class _OfflineRehearsalGateway(PaperMutationGateway):
    """Translate v1.92 intent fields before the existing fake OMS submit step."""

    def __init__(
        self,
        client: OfflinePaperOmsFakeClient,
        *,
        rehearsal_order_request: Mapping[str, Any],
    ) -> None:
        super().__init__(client)
        self._rehearsal_order_request = dict(rehearsal_order_request)

    def submit_order(self, request: Any) -> Any:
        return super().submit_order(
            _coerce_rehearsal_order_request(
                request,
                self._rehearsal_order_request,
            )
        )


def sample_daily_execution_plan_packet() -> dict[str, Any]:
    """Build a deterministic serialized daily-lab ExecutionPlan sample."""

    plan = EtfSmaDailyExecutionPlan(
        execution_plan_version="assistant_v1.64_pre_broker_execution_plan",
        execution_plan_id="daily_execution_plan_v191_smoke_2026_06_24",
        execution_plan_status="preview_only",
        execution_plan_action="buy_preview",
        execution_plan_symbol="SPY",
        execution_plan_reason="buy_preview_requires_explicit_authorization",
        execution_plan_blocker="none",
        execution_plan_source_preview_decision="buy_preview",
        execution_plan_requires_approval=True,
        execution_plan_broker_order_required=False,
        execution_plan_submit_allowed=False,
        execution_plan_paper_submit_authorized=False,
        execution_plan_live_authorized=False,
        execution_plan_broker_mutation_performed=False,
        execution_plan_created_order_payload=False,
        execution_plan_labels=V191_SAFETY_LABELS,
    ).to_dict()
    return {
        "packet_version": "v191_sample_daily_execution_plan_packet_v1",
        "as_of_date": "2026-06-24",
        "symbol": "SPY",
        "posture": "bullish_risk_on",
        "sma_posture_status": "risk_on: SMA50 is above SMA200",
        "preview_decision": "buy_preview",
        "execution_plan": plan,
        "safety_labels": list(V191_SAFETY_LABELS),
    }


def load_daily_execution_plan_packet(path: Path | str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("daily execution plan packet must be a JSON object")
    return dict(value)


def deterministic_execution_plan_digest(
    daily_packet_or_execution_plan: Mapping[str, Any],
) -> str:
    plan = _extract_execution_plan(daily_packet_or_execution_plan)
    return hashlib.sha256(_canonical_json(plan).encode("utf-8")).hexdigest()


def deterministic_client_order_id(
    daily_packet_or_execution_plan: Mapping[str, Any],
) -> str:
    plan = _extract_execution_plan(daily_packet_or_execution_plan)
    digest = deterministic_execution_plan_digest(plan)
    return f"{V191_CLIENT_ORDER_ID_PREFIX}-{digest[:24]}"


def run_v191_offline_oms_rehearsal(
    daily_packet_or_execution_plan: Mapping[str, Any],
    *,
    output_root: Path | str = V191_DEFAULT_OUTPUT_ROOT,
    input_path: Path | str | None = None,
    fixture: OfflineOmsFixture | None = None,
    run_id: str = V191_RUN_ID,
    client_order_id_override: str | None = None,
    order_intent_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a fixture-only daily ExecutionPlan to Paper OMS rehearsal."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    oms_root = root / "oms"
    plan = _extract_execution_plan(daily_packet_or_execution_plan)
    _validate_execution_plan(plan)
    packet_source = _packet_source(daily_packet_or_execution_plan)
    plan_digest = deterministic_execution_plan_digest(plan)
    client_order_id = str(client_order_id_override or deterministic_client_order_id(plan))
    rehearsal_order_request = _rehearsal_order_request_shape(
        plan,
        client_order_id=client_order_id,
        order_intent_override=order_intent_override,
    )
    previous_lifecycle = _read_json_mapping(oms_root / "latest_run.json")
    action = str(plan.get("execution_plan_action", "")).strip().lower()

    if action in HOLD_PLAN_ACTIONS:
        lane_result = evaluate_strategy_plan_mutation_lane(plan)
        fake_client: OfflinePaperOmsFakeClient | None = None
        oms_latest = {
            "outcome_classification": lane_result["outcome_classification"],
            "classification_aliases": [],
            "blocker": "",
            "client_order_id": client_order_id,
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_performed": False,
            "real_broker_read_performed": False,
            "real_broker_mutation_performed": False,
            "simulated_submit_performed": False,
            "simulated_broker_mutation_performed": False,
            "reconciliation": {},
        }
        fixture_used = fixture or OfflineOmsFixture()
    elif _is_actionable_rehearsal_plan(plan):
        fixture_used = fixture or _fixture_with_prior_terminal_order(
            oms_root,
            client_order_id=client_order_id,
        )
        fake_client = OfflinePaperOmsFakeClient(fixture_used)
        oms_latest = run_paper_certification_drill(
            paper_config=_offline_paper_config(),
            gateway=_OfflineRehearsalGateway(
                fake_client,
                rehearsal_order_request=rehearsal_order_request,
            ),
            runtime=PaperCertificationRuntime(
                output_root=oms_root,
                expected_paper_account_id=fixture_used.account_id,
                timeout_seconds=0,
                poll_interval_seconds=0,
                client_order_id=client_order_id,
                run_id=f"{run_id}_oms",
                execution_mode=OFFLINE_OMS_REHEARSAL_MODE,
                broker_state_mode=OFFLINE_FIXTURE_BROKER_STATE_MODE,
                paper_submit_authorized=False,
                labels=V191_SAFETY_LABELS,
            ),
            env=_offline_env(),
        )
    else:
        fake_client = None
        fixture_used = fixture or OfflineOmsFixture()
        blocker = _execution_plan_blocker(plan)
        oms_latest = {
            "outcome_classification": blocker,
            "classification_aliases": [],
            "blocker": blocker,
            "client_order_id": client_order_id,
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_performed": False,
            "real_broker_read_performed": False,
            "real_broker_mutation_performed": False,
            "simulated_submit_performed": False,
            "simulated_broker_mutation_performed": False,
            "reconciliation": {},
        }

    packet = _build_packet(
        run_id=run_id,
        root=root,
        oms_root=oms_root,
        input_path=input_path,
        packet_source=packet_source,
        plan=plan,
        plan_digest=plan_digest,
        client_order_id=client_order_id,
        previous_lifecycle=previous_lifecycle,
        oms_latest=oms_latest,
        fixture=fixture_used,
        fake_client=fake_client,
        rehearsal_order_request=rehearsal_order_request,
    )
    _write_artifacts(root, packet)
    return packet


def run_v191_offline_oms_rehearsal_from_path(
    input_path: Path | str,
    *,
    output_root: Path | str = V191_DEFAULT_OUTPUT_ROOT,
    fixture: OfflineOmsFixture | None = None,
    run_id: str = V191_RUN_ID,
    client_order_id_override: str | None = None,
    order_intent_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    packet = load_daily_execution_plan_packet(input_path)
    return run_v191_offline_oms_rehearsal(
        packet,
        output_root=output_root,
        input_path=input_path,
        fixture=fixture,
        run_id=run_id,
        client_order_id_override=client_order_id_override,
        order_intent_override=order_intent_override,
    )


def _build_packet(
    *,
    run_id: str,
    root: Path,
    oms_root: Path,
    input_path: Path | str | None,
    packet_source: Mapping[str, Any],
    plan: Mapping[str, Any],
    plan_digest: str,
    client_order_id: str,
    previous_lifecycle: Mapping[str, Any],
    oms_latest: Mapping[str, Any],
    fixture: OfflineOmsFixture,
    fake_client: OfflinePaperOmsFakeClient | None,
    rehearsal_order_request: Mapping[str, Any],
) -> dict[str, Any]:
    classification = str(oms_latest.get("outcome_classification", ""))
    blocker = str(oms_latest.get("blocker") or "")
    if not blocker and classification.startswith("blocked_"):
        blocker = classification
    fake_submit_count = len(fake_client.submitted_requests) if fake_client else 0
    fake_cancel_count = len(fake_client.cancelled_order_ids) if fake_client else 0
    return {
        "packet_version": V191_PACKET_VERSION,
        "reconciliation_version": V191_RECONCILIATION_VERSION,
        "run_id": run_id,
        "generated_at": _utc_now_text(),
        "input_daily_packet_or_execution_plan_path": (
            str(input_path) if input_path is not None else ""
        ),
        "as_of_date": _source_value(packet_source, "as_of_date"),
        "symbol": str(plan.get("execution_plan_symbol", "")),
        "sma_posture": _source_posture(packet_source),
        "source_decision_posture": _source_posture(packet_source),
        "preview_decision": str(
            plan.get("execution_plan_source_preview_decision")
            or _source_value(packet_source, "preview_decision")
        ),
        "execution_plan": dict(plan),
        "execution_plan_id": str(plan.get("execution_plan_id", "")),
        "execution_plan_digest": plan_digest,
        "deterministic_client_order_id": client_order_id,
        "client_order_id": client_order_id,
        "side": str(rehearsal_order_request.get("side", "")),
        "rehearsal_order_request": dict(rehearsal_order_request),
        "fake_submitted_request_fields": _submitted_request_fields(fake_client),
        "execution_mode": OFFLINE_OMS_REHEARSAL_MODE,
        "broker_state_mode": OFFLINE_FIXTURE_BROKER_STATE_MODE,
        "broker_state_fixture": fixture.to_dict(),
        "oms_classification": classification,
        "outcome_classification": classification,
        "classification_aliases": list(oms_latest.get("classification_aliases", [])),
        "previous_lifecycle_state": _lifecycle_summary(previous_lifecycle),
        "reconciled_lifecycle_state": _lifecycle_summary(oms_latest),
        "unresolved_prior_status": _unresolved_prior_status(
            previous_lifecycle,
            classification,
        ),
        "fake_submit_call_count": fake_submit_count,
        "fake_cancel_call_count": fake_cancel_count,
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "real_broker_read_performed": False,
        "real_broker_mutation_performed": False,
        "broker_mutation_performed": False,
        "simulated_submit_performed": bool(
            oms_latest.get("simulated_submit_performed")
        ),
        "simulated_broker_mutation_performed": bool(
            oms_latest.get("simulated_broker_mutation_performed")
        ),
        "blocker": blocker,
        "next_operator_action": _next_operator_action(classification, blocker),
        "safety_labels": list(V191_SAFETY_LABELS),
        "oms_latest": dict(oms_latest),
        "artifact_paths": {
            "operating_brief": str(root / "operating_brief.md"),
            "reconciliation_record": str(root / "reconciliation_record.json"),
            "operating_record": str(root / "operating_record.jsonl"),
            "operating_packet": str(root / "operating_packet.json"),
            "manifest": str(root / "manifest.jsonl"),
            "oms_latest": str(oms_root / "latest_run.json"),
            "oms_lifecycle": str(oms_root / "order_lifecycle.jsonl"),
        },
    }


def _write_artifacts(root: Path, packet: Mapping[str, Any]) -> None:
    _write_json(root / "operating_packet.json", packet)
    _write_json(root / "reconciliation_record.json", packet)
    (root / "operating_record.jsonl").write_text(
        json.dumps(_json_safe(packet), sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (root / "operating_brief.md").write_text(
        _render_operating_brief(packet),
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "manifest_version": V191_MANIFEST_VERSION,
        "run_id": packet["run_id"],
        "generated_at": packet["generated_at"],
        "execution_mode": OFFLINE_OMS_REHEARSAL_MODE,
        "artifacts": {
            path.name: {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
            }
            for path in (
                root / "operating_packet.json",
                root / "reconciliation_record.json",
                root / "operating_record.jsonl",
                root / "operating_brief.md",
            )
        },
    }
    (root / "manifest.jsonl").write_text(
        json.dumps(_json_safe(manifest), sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _render_operating_brief(packet: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# v1.91 Offline OMS Rehearsal",
            "",
            f"- Outcome: `{packet.get('oms_classification')}`",
            f"- Blocker: `{packet.get('blocker') or 'none'}`",
            f"- As-of date: `{packet.get('as_of_date')}`",
            f"- Symbol: `{packet.get('symbol')}`",
            f"- Preview decision: `{packet.get('preview_decision')}`",
            f"- Execution plan digest: `{packet.get('execution_plan_digest')}`",
            f"- Client order id: `{packet.get('client_order_id')}`",
            f"- Execution mode: `{packet.get('execution_mode')}`",
            f"- Broker-state mode: `{packet.get('broker_state_mode')}`",
            f"- Fake submit calls: `{packet.get('fake_submit_call_count')}`",
            f"- Fake cancel calls: `{packet.get('fake_cancel_call_count')}`",
            f"- Paper submit authorized: `{packet.get('paper_submit_authorized')}`",
            f"- Paper submit performed: `{packet.get('paper_submit_performed')}`",
            f"- Real broker read performed: `{packet.get('real_broker_read_performed')}`",
            f"- Real broker mutation performed: `{packet.get('real_broker_mutation_performed')}`",
            f"- Next operator action: `{packet.get('next_operator_action')}`",
            "",
            "Labels: "
            + ", ".join(str(label) for label in packet.get("safety_labels", [])),
            "",
        ]
    )


def _extract_execution_plan(value: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value.get("execution_plan"), Mapping):
        return dict(value["execution_plan"])
    if all(field in value for field in REQUIRED_EXECUTION_PLAN_FIELDS):
        return dict(value)
    latest = value.get("latest_run")
    if isinstance(latest, Mapping) and isinstance(latest.get("execution_plan"), Mapping):
        return dict(latest["execution_plan"])
    raise ValueError("daily packet does not contain a serialized ExecutionPlan")


def _validate_execution_plan(plan: Mapping[str, Any]) -> None:
    missing = [field for field in REQUIRED_EXECUTION_PLAN_FIELDS if field not in plan]
    if missing:
        raise ValueError(f"ExecutionPlan is missing required fields: {', '.join(missing)}")
    if str(plan.get("execution_plan_symbol", "")).upper() != "SPY":
        raise ValueError("v1.91 offline OMS rehearsal accepts SPY ExecutionPlans only")
    if plan.get("execution_plan_live_authorized") is not False:
        raise ValueError("ExecutionPlan live authorization must be false")
    if plan.get("execution_plan_paper_submit_authorized") is not False:
        raise ValueError("ExecutionPlan paper submit authorization must be false")


def _packet_source(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return value if not all(field in value for field in REQUIRED_EXECUTION_PLAN_FIELDS) else {}


def _is_actionable_rehearsal_plan(plan: Mapping[str, Any]) -> bool:
    action = str(plan.get("execution_plan_action", "")).strip().lower()
    return (
        action in ACTIONABLE_PLAN_ACTIONS
        and plan.get("execution_plan_requires_approval") is True
        and plan.get("execution_plan_live_authorized") is False
        and plan.get("execution_plan_paper_submit_authorized") is False
    )


def _execution_plan_blocker(plan: Mapping[str, Any]) -> str:
    blocker = str(plan.get("execution_plan_blocker", "")).strip()
    if blocker and blocker != "none":
        return f"blocked_{blocker}"
    return "blocked_unaccepted_execution_plan"


def _rehearsal_order_request_shape(
    plan: Mapping[str, Any],
    *,
    client_order_id: str,
    order_intent_override: Mapping[str, Any] | None,
) -> dict[str, Any]:
    side = _side_from_action(str(plan.get("execution_plan_action", "")))
    shape: dict[str, Any] = {
        "client_order_id": client_order_id,
        "symbol": str(plan.get("execution_plan_symbol", "")).upper(),
        "side": side,
        "asset_class": "equity",
        "quantity": "",
        "notional": "",
        "order_type": "",
        "time_in_force": "",
        "limit_price": "",
    }
    if order_intent_override is None:
        return shape

    shape.update(
        {
            "client_order_id": str(
                order_intent_override.get("client_order_id")
                or order_intent_override.get("deterministic_client_order_id")
                or client_order_id
            ),
            "symbol": str(order_intent_override.get("symbol") or shape["symbol"]).upper(),
            "side": str(order_intent_override.get("side") or side).strip().lower(),
            "asset_class": str(
                order_intent_override.get("asset_class") or shape["asset_class"]
            ),
            "quantity": str(
                order_intent_override.get("quantity")
                or order_intent_override.get("qty")
                or ""
            ),
            "notional": str(order_intent_override.get("notional") or ""),
            "order_type": str(order_intent_override.get("order_type") or ""),
            "time_in_force": str(order_intent_override.get("time_in_force") or ""),
            "limit_price": str(order_intent_override.get("limit_price") or ""),
        }
    )
    return shape


def _coerce_rehearsal_order_request(
    request: Any,
    rehearsal_order_request: Mapping[str, Any],
) -> _OfflineRehearsalOrderRequest:
    side = str(rehearsal_order_request.get("side") or _field_text(request, "side"))
    symbol = str(rehearsal_order_request.get("symbol") or _field_text(request, "symbol"))
    quantity = str(
        rehearsal_order_request.get("quantity")
        or rehearsal_order_request.get("qty")
        or ""
    )
    notional = str(rehearsal_order_request.get("notional") or "")
    order_type = str(
        rehearsal_order_request.get("order_type")
        or _field_text(request, "order_type")
        or "limit"
    )
    time_in_force = str(
        rehearsal_order_request.get("time_in_force")
        or _field_text(request, "time_in_force")
        or "day"
    )
    limit_price = str(
        rehearsal_order_request.get("limit_price") or ""
    )
    fallback_quantity = "" if notional else _field_text(request, "qty")
    fallback_limit_price = (
        ""
        if order_type.strip().lower() == "market"
        else _field_text(request, "limit_price")
    )
    return _OfflineRehearsalOrderRequest(
        client_order_id=str(
            rehearsal_order_request.get("client_order_id")
            or _field_text(request, "client_order_id")
        ),
        symbol=symbol,
        side=side,
        asset_class=str(
            rehearsal_order_request.get("asset_class")
            or _field_text(request, "asset_class")
            or "equity"
        ),
        qty=_optional_decimal(quantity or fallback_quantity),
        notional=_optional_decimal(notional or _field_text(request, "notional")),
        order_type=order_type,
        time_in_force=time_in_force,
        limit_price=_optional_decimal(limit_price or fallback_limit_price),
    )


def _submitted_request_fields(
    fake_client: OfflinePaperOmsFakeClient | None,
) -> dict[str, Any]:
    if fake_client is None or not fake_client.submitted_requests:
        return {}
    return _request_payload_from_object(fake_client.submitted_requests[-1])


def _request_payload_from_object(request: Any) -> dict[str, str]:
    return {
        "client_order_id": _field_text(request, "client_order_id"),
        "symbol": _field_text(request, "symbol"),
        "side": _field_text(request, "side").lower(),
        "asset_class": _field_text(request, "asset_class") or "equity",
        "quantity": _optional_decimal_text(_field_value(request, "qty")),
        "notional": _optional_decimal_text(_field_value(request, "notional")),
        "order_type": _field_text(request, "order_type"),
        "time_in_force": _field_text(request, "time_in_force"),
        "limit_price": _optional_decimal_text(_field_value(request, "limit_price")),
    }


def _side_from_action(action: str) -> str:
    normalized = action.strip().lower()
    if normalized == "buy_preview":
        return "buy"
    if normalized == "sell_preview":
        return "sell"
    return ""


def _fixture_with_prior_terminal_order(
    oms_root: Path,
    *,
    client_order_id: str,
) -> OfflineOmsFixture:
    latest = _read_json_mapping(oms_root / "latest_run.json")
    reconciliation = latest.get("reconciliation")
    if not isinstance(reconciliation, Mapping):
        return OfflineOmsFixture()
    final_order = reconciliation.get("final_order")
    if not isinstance(final_order, Mapping):
        return OfflineOmsFixture()
    if str(final_order.get("client_order_id", "")) != client_order_id:
        return OfflineOmsFixture()
    status = _normalized_status(
        final_order.get("normalized_status") or final_order.get("status")
    )
    if status not in {"canceled", "cancelled", "expired", "filled", "rejected"}:
        return OfflineOmsFixture()
    return OfflineOmsFixture(all_orders=(dict(final_order),))


def _offline_paper_config() -> AlpacaPaperConfig:
    return AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key="",
        alpaca_secret_key="",
        alpaca_paper_base_url=DEFAULT_ALPACA_PAPER_BASE_URL,
    )


def _offline_env() -> dict[str, str]:
    return {
        "APP_PROFILE": "paper",
        "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
    }


def _source_value(packet_source: Mapping[str, Any], key: str) -> str:
    value = packet_source.get(key)
    if value not in (None, ""):
        return str(value)
    latest = packet_source.get("latest_run")
    if isinstance(latest, Mapping) and latest.get(key) not in (None, ""):
        return str(latest.get(key))
    decision = packet_source.get("daily_decision_summary")
    if isinstance(decision, Mapping) and decision.get(key) not in (None, ""):
        return str(decision.get(key))
    return ""


def _source_posture(packet_source: Mapping[str, Any]) -> str:
    return (
        _source_value(packet_source, "posture")
        or _source_value(packet_source, "sma_posture_status")
        or _source_value(packet_source, "source_decision_posture")
    )


def _lifecycle_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    reconciliation = value.get("reconciliation")
    if not isinstance(reconciliation, Mapping):
        reconciliation = {}
    return {
        "present": bool(value),
        "outcome_classification": str(value.get("outcome_classification", "")),
        "client_order_id": str(value.get("client_order_id", "")),
        "blocker": str(value.get("blocker", "")),
        "final_order_status": str(reconciliation.get("final_order_status", "")),
        "restart_recovery_performed": value.get("restart_recovery_performed") is True,
    }


def _unresolved_prior_status(
    previous_lifecycle: Mapping[str, Any],
    classification: str,
) -> str:
    if classification == "blocked_unresolved_prior_mutation":
        return "blocked_unresolved_prior_mutation"
    previous_outcome = str(previous_lifecycle.get("outcome_classification", ""))
    if previous_outcome in UNRESOLVED_OMS_OUTCOMES:
        return "unresolved_prior_present"
    return "none"


def _next_operator_action(classification: str, blocker: str) -> str:
    if classification == "not_submitted_hold_noop":
        return "record_noop_no_broker_action"
    if classification == "blocked_unresolved_prior_mutation":
        return "resolve_prior_unresolved_oms_state_before_new_rehearsal"
    if classification == "blocked_broker_local_divergence":
        return "review_offline_fixture_against_local_lifecycle_before_rehearsal"
    if classification == "blocked_lock_contention":
        return "wait_for_existing_oms_rehearsal_lock_to_clear"
    if classification.startswith("blocked_") or blocker:
        return "review_blocker_before_any_operator_authorization"
    if classification in TERMINAL_OMS_OUTCOMES:
        return "review_reconciliation_packet_no_broker_action"
    if classification in UNRESOLVED_OMS_OUTCOMES:
        return "resolve_unresolved_fake_lifecycle_before_replay_or_new_plan"
    return "review_offline_oms_rehearsal_packet"


def _read_json_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))


def _spy_position() -> dict[str, Any]:
    return {
        "symbol": "SPY",
        "qty": Decimal("0.01"),
        "market_value": Decimal("6.00"),
        "average_entry_price": Decimal("500.00"),
        "side": "long",
    }


def _active_spy_asset() -> dict[str, Any]:
    return {
        "symbol": "SPY",
        "asset_class": "us_equity",
        "status": "active",
        "tradable": True,
        "fractionable": True,
    }


def _order(
    *,
    client_order_id: str,
    status: str,
    qty: str = "0.0001",
    notional: str = "",
    filled_qty: str = "0",
    side: str = "sell",
    order_type: str = "limit",
    time_in_force: str = "day",
    limit_price: str = "630.00",
) -> dict[str, Any]:
    now = datetime(2026, 6, 24, 15, 30, tzinfo=UTC)
    order = {
        "id": "offline-fixture-order-1",
        "client_order_id": client_order_id,
        "symbol": "SPY",
        "asset_class": "equity",
        "side": side,
        "type": order_type,
        "time_in_force": time_in_force,
        "status": status,
        "filled_qty": Decimal(str(filled_qty)),
        "filled_avg_price": Decimal("0") if filled_qty == "0" else Decimal("620.00"),
        "created_at": now.isoformat(),
        "submitted_at": now.isoformat(),
    }
    if str(qty).strip():
        order["qty"] = Decimal(str(qty))
    if str(notional).strip():
        order["notional"] = Decimal(str(notional))
    if str(limit_price).strip():
        order["limit_price"] = Decimal(str(limit_price))
    return order


def _normalized_status(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _utc_now_text() -> str:
    return datetime.now(tz=UTC).isoformat()


def _field_value(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _field_text(value: Any, name: str) -> str:
    raw = _field_value(value, name)
    if raw is None:
        return ""
    enum_value = getattr(raw, "value", None)
    return str(enum_value if enum_value is not None else raw).strip()


def _optional_decimal(value: Any) -> Decimal | None:
    text = str(value or "").strip()
    if not text:
        return None
    return Decimal(text)


def _optional_decimal_text(value: Any) -> str:
    decimal_value = _optional_decimal(value)
    return "" if decimal_value is None else str(decimal_value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


__all__ = [
    "ACTIONABLE_PLAN_ACTIONS",
    "HOLD_PLAN_ACTIONS",
    "OFFLINE_FIXTURE_BROKER_STATE_MODE",
    "OFFLINE_OMS_REHEARSAL_MODE",
    "OfflineOmsFixture",
    "OfflinePaperOmsFakeClient",
    "V191_DEFAULT_OUTPUT_ROOT",
    "V191_RUN_ID",
    "V191_SAFETY_LABELS",
    "deterministic_client_order_id",
    "deterministic_execution_plan_digest",
    "load_daily_execution_plan_packet",
    "run_v191_offline_oms_rehearsal",
    "run_v191_offline_oms_rehearsal_from_path",
    "sample_daily_execution_plan_packet",
]
