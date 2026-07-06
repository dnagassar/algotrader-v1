"""v6.0 supervised crypto trader demo with an offline simulation broker.

The default path is intentionally local-only. It creates fixture-backed crypto
bars, evaluates a small supervised decision router, builds an ExecutionPlan, and
lets a deterministic simulation broker consume only accepted plan intents.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_DOWN
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Literal

from algotrader.core.types import Bar, OrderSide, OrderStatus, OrderType, ProposedOrder, Quote
from algotrader.execution.simulator import ExecutionResult, simulate_order
from algotrader.orchestration.execution_planning_flow import (
    ExecutionPlan,
    build_execution_plan,
)
from algotrader.orchestration.execution_planning_policy import (
    MaxAcceptedIntentsPolicyConfig,
    PlanningPolicyResult,
    apply_max_intents_execution_planning_policy,
)
from algotrader.orchestration.risk_execution_flow import (
    ExecutionIntent,
    build_execution_intents_from_risk_approved,
)
from algotrader.orchestration.screener_signal_flow import ScreenerSignalEvaluation
from algotrader.orchestration.signal_risk_flow import SignalRiskEvaluation
from algotrader.portfolio.state import Account, PortfolioState, apply_fill
from algotrader.risk.config import RiskConfig
from algotrader.risk.engine import RiskEngine
from algotrader.risk.state import RiskVerdict
from algotrader.signals.crypto_trend import normalize_crypto_symbol

SCHEMA_VERSION = "v6_0_tomorrow_supervised_crypto_paper_trader_demo_v1"
COMMAND_NAME = "run_tomorrow_crypto_trader_demo"
VALIDATOR_COMMAND_NAME = "validate_tomorrow_crypto_trader_demo"
DEFAULT_OUTPUT_ROOT = Path("runs/crypto_trader_demo/latest")
DEFAULT_AS_OF = datetime(2026, 7, 6, 14, 30, tzinfo=UTC)
DEFAULT_UNIVERSE = ("BTCUSD", "ETHUSD", "SOLUSD", "ADAUSD")

MAX_NOTIONAL_PER_ORDER = Decimal("5")
MAX_TOTAL_DEMO_EXPOSURE = Decimal("25")
MAX_OPEN_EXPOSURE_SYMBOLS = 2
SIMULATED_STARTING_CASH = Decimal("25")
QTY_INCREMENT = Decimal("0.00000001")
MIN_ORDER_SIZE = Decimal("0.00000001")
MIN_NOTIONAL = Decimal("1")

REQUIRED_SAFETY_LABELS = (
    "simulation_or_paper_only",
    "not_live_authorized",
    "profit_claim=none",
    "no_real_capital",
    "paper_submit_authorized=false",
    "broker_mutation_authorized=false",
    "live_authorized=false",
    "credential_values_exposed=false",
)

SIMBROKER_SAFETY_LABELS = (
    *REQUIRED_SAFETY_LABELS,
    "broker_mode=simulation_broker",
    "simulation_mutation_authorized=true",
    "paper_submit_occurred=false",
    "broker_mutation_occurred=false",
    "broker_state_observed=false",
    "broker_state_mode=offline_simulation",
    "network_used=false",
)

ALPACA_PAPER_SAFETY_LABELS = (
    "simulation_or_paper_only",
    "not_live_authorized",
    "profit_claim=none",
    "no_real_capital",
    "broker_mode=alpaca_paper",
    "simulation_mutation_authorized=false",
    "live_endpoint_touched=false",
    "credential_values_exposed=false",
)

REQUIRED_ARTIFACTS = (
    "operating_brief.md",
    "operating_record.json",
    "events.jsonl",
    "manifest.json",
    "next_operator_action.json",
)

FORBIDDEN_SENTINELS = (
    "SENTINEL_ALPACA_SECRET_DO_NOT_PRINT",
    "script-paper-key-value-not-for-output",
    "script-paper-secret-value-not-for-output",
    "crypto-cycle-key-value-not-for-output",
    "credential-value-not-for-output",
)

Mode = Literal["SimBroker", "AlpacaPaper"]

__all__ = [
    "ALPACA_PAPER_SAFETY_LABELS",
    "COMMAND_NAME",
    "DEFAULT_AS_OF",
    "DEFAULT_OUTPUT_ROOT",
    "DEFAULT_UNIVERSE",
    "MAX_NOTIONAL_PER_ORDER",
    "MAX_TOTAL_DEMO_EXPOSURE",
    "REQUIRED_ARTIFACTS",
    "REQUIRED_SAFETY_LABELS",
    "SCHEMA_VERSION",
    "SIMBROKER_SAFETY_LABELS",
    "VALIDATOR_COMMAND_NAME",
    "SimulationBroker",
    "main",
    "render_operating_brief",
    "run_tomorrow_crypto_trader_demo",
    "validate_tomorrow_crypto_trader_demo",
    "write_tomorrow_crypto_trader_demo_artifacts",
]


@dataclass(frozen=True, slots=True)
class DemoCandidate:
    symbol: str
    strategy_id: str
    strategy_family: str
    signal_state: str
    decision: str
    score: Decimal
    latest_price: Decimal | None
    data_gate_passed: bool
    orderability_gate_passed: bool
    risk_gate_passed: bool
    min_notional_verified: bool
    qty_increment_verified: bool
    blockers: tuple[str, ...]
    features: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "asset_class": "crypto",
            "strategy_id": self.strategy_id,
            "strategy_family": self.strategy_family,
            "signal_state": self.signal_state,
            "decision": self.decision,
            "score": self.score,
            "latest_price": self.latest_price,
            "data_gate_passed": self.data_gate_passed,
            "orderability_gate_passed": self.orderability_gate_passed,
            "risk_gate_passed": self.risk_gate_passed,
            "min_notional_verified": self.min_notional_verified,
            "qty_increment_verified": self.qty_increment_verified,
            "blockers": list(self.blockers),
            "features": dict(self.features),
        }


@dataclass(frozen=True, slots=True)
class DemoPlanMaterial:
    selected_candidate: DemoCandidate | None
    order: ProposedOrder | None
    quote: Quote | None
    risk: RiskVerdict | None
    risk_evaluation: SignalRiskEvaluation | None
    execution_intents: tuple[ExecutionIntent, ...]
    execution_plan: ExecutionPlan
    planning_policy: PlanningPolicyResult
    client_order_id: str
    blockers: tuple[str, ...]


class SimulationBroker:
    """Deterministic local simulation broker for accepted ExecutionPlans."""

    def __init__(
        self,
        portfolio: PortfolioState | None = None,
        *,
        existing_client_order_ids: Iterable[str] = (),
    ) -> None:
        self._portfolio = portfolio or PortfolioState(
            account=Account(SIMULATED_STARTING_CASH, "USD")
        )
        self._seen_client_order_ids = set(existing_client_order_ids)
        self.action_ledger: list[dict[str, object]] = []
        self.fill_ledger: list[dict[str, object]] = []

    @property
    def portfolio(self) -> PortfolioState:
        return self._portfolio

    def apply_plan(
        self,
        *,
        plan: ExecutionPlan,
        planning_policy: PlanningPolicyResult,
        run_id: str,
        as_of: datetime,
        event_sink: list[dict[str, object]],
    ) -> dict[str, object]:
        if plan.intents and not planning_policy.accepted_intents:
            return self._block(
                "no_policy_accepted_intents",
                run_id=run_id,
                as_of=as_of,
                event_sink=event_sink,
            )

        for intent in planning_policy.accepted_intents:
            evaluation = intent.source_evaluation
            order = evaluation.order
            quote = evaluation.quote
            risk = evaluation.risk
            if order is None:
                return self._block(
                    "accepted_intent_missing_order",
                    run_id=run_id,
                    as_of=as_of,
                    event_sink=event_sink,
                )
            client_order_id = order.client_order_id or ""
            if not client_order_id:
                return self._block(
                    "missing_client_order_id",
                    run_id=run_id,
                    as_of=as_of,
                    event_sink=event_sink,
                )
            if client_order_id in self._seen_client_order_ids:
                return self._block(
                    "duplicate_client_order_id",
                    run_id=run_id,
                    as_of=as_of,
                    event_sink=event_sink,
                    symbol=order.symbol,
                    client_order_id=client_order_id,
                )
            if risk is None or not risk.allowed:
                return self._block(
                    "risk_not_approved",
                    run_id=run_id,
                    as_of=as_of,
                    event_sink=event_sink,
                    symbol=order.symbol,
                    client_order_id=client_order_id,
                )

            self._seen_client_order_ids.add(client_order_id)
            action = {
                "event_type": "simulation_order_submitted",
                "run_id": run_id,
                "timestamp": as_of.isoformat(),
                "broker_mode": "simulation_broker",
                "symbol": order.symbol,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "quantity": order.quantity,
                "client_order_id": client_order_id,
                "simulated": True,
            }
            self.action_ledger.append(action)
            event_sink.append(action)

            execution = simulate_order(order=order, quote=quote, order_id=client_order_id)
            self._record_execution(execution, run_id=run_id, event_sink=event_sink)
            if execution.fill is not None:
                self._portfolio = apply_fill(self._portfolio, execution.fill)
                event_sink.append(
                    {
                        "event_type": "simulation_reconciliation_checked",
                        "run_id": run_id,
                        "timestamp": as_of.isoformat(),
                        "broker_mode": "simulation_broker",
                        "portfolio": _portfolio_snapshot(self._portfolio),
                    }
                )

        return {
            "status": "completed",
            "blocker": "",
            "action_count": len(self.action_ledger),
            "fill_count": len(self.fill_ledger),
            "portfolio": _portfolio_snapshot(self._portfolio),
        }

    def cancel_current_run_order(self, client_order_id: str, as_of: datetime) -> dict[str, object]:
        event = {
            "event_type": "simulation_order_canceled",
            "timestamp": as_of.isoformat(),
            "broker_mode": "simulation_broker",
            "client_order_id": client_order_id,
            "simulated": True,
        }
        self.action_ledger.append(event)
        return event

    def flatten_current_run_positions(self, as_of: datetime) -> dict[str, object]:
        event = {
            "event_type": "simulation_flatten_recorded",
            "timestamp": as_of.isoformat(),
            "broker_mode": "simulation_broker",
            "simulated": True,
            "positions_before": [
                _position_snapshot(position) for position in self._portfolio.positions
            ],
        }
        self.action_ledger.append(event)
        self._portfolio = PortfolioState(
            account=self._portfolio.account,
            positions=(),
            timestamp=as_of,
        )
        return event

    def _record_execution(
        self,
        execution: ExecutionResult,
        *,
        run_id: str,
        event_sink: list[dict[str, object]],
    ) -> None:
        ack = execution.ack
        ack_event = {
            "event_type": "simulation_order_acknowledged",
            "run_id": run_id,
            "timestamp": ack.timestamp.isoformat(),
            "broker_mode": "simulation_broker",
            "client_order_id": ack.order_id,
            "symbol": ack.order.symbol,
            "status": ack.status.value,
            "message": ack.message,
            "simulated": True,
        }
        self.action_ledger.append(ack_event)
        event_sink.append(ack_event)
        if execution.fill is None:
            return
        fill = execution.fill
        fill_event = {
            "event_type": "simulation_order_filled",
            "run_id": run_id,
            "timestamp": fill.timestamp.isoformat(),
            "broker_mode": "simulation_broker",
            "client_order_id": fill.order_id,
            "symbol": fill.symbol,
            "side": fill.side.value,
            "quantity": fill.quantity,
            "price": fill.price,
            "notional": fill.notional,
            "simulated": True,
        }
        self.fill_ledger.append(fill_event)
        event_sink.append(fill_event)

    def _block(
        self,
        blocker: str,
        *,
        run_id: str,
        as_of: datetime,
        event_sink: list[dict[str, object]],
        symbol: str = "",
        client_order_id: str = "",
    ) -> dict[str, object]:
        event = {
            "event_type": "simulation_blocked",
            "run_id": run_id,
            "timestamp": as_of.isoformat(),
            "broker_mode": "simulation_broker",
            "blocker": blocker,
            "symbol": symbol,
            "client_order_id": client_order_id,
            "simulated": True,
        }
        self.action_ledger.append(event)
        event_sink.append(event)
        return {
            "status": "blocked",
            "blocker": blocker,
            "action_count": len(self.action_ledger),
            "fill_count": len(self.fill_ledger),
            "portfolio": _portfolio_snapshot(self._portfolio),
        }


def run_tomorrow_crypto_trader_demo(
    *,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    mode: Mode = "SimBroker",
    allow_alpaca_paper_mutation: bool = False,
    universe: Sequence[str] = DEFAULT_UNIVERSE,
    as_of: datetime | str | None = None,
    write_artifacts: bool = True,
    existing_client_order_ids: Iterable[str] = (),
    paper_environment: Mapping[str, object] | None = None,
    alpaca_paper_snapshot: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Run the v6.0 demo packet builder.

    SimBroker is the only implemented acceptance path. AlpacaPaper mode returns
    explicit gated statuses without contacting a broker.
    """

    run_mode = _mode(mode)
    as_of_value = _utc_datetime(as_of or DEFAULT_AS_OF, "as_of")
    root = Path(output_root)
    normalized_universe = tuple(normalize_crypto_symbol(symbol) for symbol in universe)
    git_state = _git_state()
    run_id = _run_id(run_mode, as_of_value, normalized_universe, git_state["short_sha"])
    events: list[dict[str, object]] = [
        {
            "event_type": "demo_run_started",
            "run_id": run_id,
            "timestamp": as_of_value.isoformat(),
            "mode": run_mode,
            "network_used": False,
        }
    ]

    if run_mode == "AlpacaPaper":
        packet = _alpaca_paper_packet(
            output_root=root,
            run_id=run_id,
            as_of=as_of_value,
            universe=normalized_universe,
            git_state=git_state,
            allow_alpaca_paper_mutation=allow_alpaca_paper_mutation,
            paper_environment=paper_environment,
            alpaca_paper_snapshot=alpaca_paper_snapshot,
            events=events,
        )
        if write_artifacts:
            packet["artifact_paths"] = write_tomorrow_crypto_trader_demo_artifacts(
                root,
                packet,
            )
        return packet

    bars_by_symbol = _offline_fixture_bars(normalized_universe, as_of_value)
    input_paths: dict[str, object] = {}
    if write_artifacts:
        input_path = root / "inputs" / "offline_crypto_bars.csv"
        _write_bars_csv(input_path, bars_by_symbol)
        input_paths["offline_crypto_bars_csv"] = str(input_path)
    else:
        input_paths["offline_crypto_bars_csv"] = "generated_offline_fixture"

    candidates = _evaluate_candidates(
        bars_by_symbol=bars_by_symbol,
        universe=normalized_universe,
        as_of=as_of_value,
    )
    for candidate in candidates:
        events.append(
            {
                "event_type": "candidate_evaluated",
                "run_id": run_id,
                "timestamp": as_of_value.isoformat(),
                "candidate": candidate.to_dict(),
            }
        )

    plan_material = _build_plan_material(
        candidates=candidates,
        bars_by_symbol=bars_by_symbol,
        run_id=run_id,
        as_of=as_of_value,
        git_short_sha=git_state["short_sha"],
        existing_client_order_ids=existing_client_order_ids,
    )
    events.extend(_plan_events(plan_material, run_id=run_id, as_of=as_of_value))

    sim_broker = SimulationBroker(existing_client_order_ids=existing_client_order_ids)
    broker_result = sim_broker.apply_plan(
        plan=plan_material.execution_plan,
        planning_policy=plan_material.planning_policy,
        run_id=run_id,
        as_of=as_of_value,
        event_sink=events,
    )
    decision = _sim_decision(plan_material, broker_result)
    final_blocker = _final_blocker(plan_material, broker_result)
    simulation_mutation_occurred = bool(sim_broker.fill_ledger)
    events.append(
        {
            "event_type": "demo_run_completed",
            "run_id": run_id,
            "timestamp": as_of_value.isoformat(),
            "mode": run_mode,
            "decision": decision,
            "final_blocker_status": final_blocker,
        }
    )

    safety = _simbroker_safety(simulation_mutation_occurred=simulation_mutation_occurred)
    packet = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "tomorrow_crypto_trader_demo",
        "operator_command": COMMAND_NAME,
        "run_id": run_id,
        "as_of": as_of_value.isoformat(),
        "output_root": str(root),
        "mode": run_mode,
        "broker_mode": "simulation_broker",
        "git_state": git_state,
        "input_data_paths": input_paths,
        "data_provenance": {
            "data_basis": "offline_fixture",
            "market_data_basis": "offline_fixture",
            "market_data_observed": False,
            "orderability_basis": "offline_fixture",
            "orderability_observed": False,
            "broker_state_observed": False,
            "broker_state_mode": "offline_simulation",
            "network_used": False,
        },
        "candidate_universe": list(normalized_universe),
        "evaluated_subset": list(normalized_universe),
        "evaluated_subset_reason": "default_v6_demo_universe_fully_evaluated",
        "signal_states": [candidate.to_dict() for candidate in candidates],
        "selected_candidate": (
            None
            if plan_material.selected_candidate is None
            else plan_material.selected_candidate.to_dict()
        ),
        "selected_candidate_status": (
            "selected_candidate_for_supervised_demo"
            if plan_material.selected_candidate is not None
            else "no_trade_all_scores_below_threshold"
        ),
        "decision": decision,
        "risk_decision": _risk_decision(plan_material.risk),
        "execution_intent": _execution_intent_record(plan_material),
        "execution_plan": _execution_plan_record(plan_material.execution_plan),
        "planning_policy_decision": _planning_policy_record(plan_material.planning_policy),
        "broker_mode_adapter": {
            "adapter": "simulation_broker",
            "accepted_execution_plan_required": True,
            "broker_sdk_imported": False,
            "network_used": False,
        },
        "sim_broker_action_ledger": list(sim_broker.action_ledger),
        "fill_ledger": list(sim_broker.fill_ledger),
        "portfolio_snapshot": _portfolio_snapshot(sim_broker.portfolio),
        "broker_result": broker_result,
        "final_blocker_status": final_blocker,
        "blockers": list(_dedupe((*plan_material.blockers, _text(broker_result.get("blocker"))))),
        "next_operator_action": _next_action(decision, final_blocker),
        "safety": safety,
        "safety_labels": list(SIMBROKER_SAFETY_LABELS),
        "labels": list(SIMBROKER_SAFETY_LABELS),
        "profit_claim": "none",
        "events": events,
    }
    if write_artifacts:
        packet["artifact_paths"] = write_tomorrow_crypto_trader_demo_artifacts(root, packet)
    return packet


def write_tomorrow_crypto_trader_demo_artifacts(
    output_root: Path | str,
    packet: Mapping[str, object],
) -> dict[str, str]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "operating_brief": root / "operating_brief.md",
        "operating_record": root / "operating_record.json",
        "events": root / "events.jsonl",
        "manifest": root / "manifest.json",
        "next_operator_action": root / "next_operator_action.json",
    }
    artifact_paths = {key: str(path) for key, path in paths.items()}
    packet_payload = {**dict(packet), "artifact_paths": artifact_paths}
    next_action = {
        **_mapping(packet.get("next_operator_action")),
        "run_id": _text(packet.get("run_id")),
        "as_of": _text(packet.get("as_of")),
        "safety_labels": list(_string_sequence(packet.get("safety_labels"))),
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "tomorrow_crypto_trader_demo_manifest",
        "run_id": _text(packet.get("run_id")),
        "as_of": _text(packet.get("as_of")),
        "output_root": str(root),
        "mode": _text(packet.get("mode")),
        "broker_mode": _text(packet.get("broker_mode")),
        "required_artifacts": {},
        "generated_under_runs": _generated_under_runs(root),
        "safety": dict(_mapping(packet.get("safety"))),
        "safety_labels": list(_string_sequence(packet.get("safety_labels"))),
        "labels": list(_string_sequence(packet.get("labels"))),
        "profit_claim": "none",
    }

    paths["operating_brief"].write_text(
        render_operating_brief(packet_payload) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_json(paths["operating_record"], packet_payload)
    _write_events(paths["events"], _mapping_sequence(packet.get("events")))
    _write_json(paths["next_operator_action"], next_action)
    manifest["required_artifacts"] = {
        name: {
            "path": str(path),
            "exists": path.is_file(),
            "sha256": _file_sha256(path) if path.is_file() else "",
        }
        for name, path in sorted(paths.items())
        if name != "manifest"
    }
    _write_json(paths["manifest"], manifest)
    return artifact_paths


def render_operating_brief(packet: Mapping[str, object]) -> str:
    selected = _mapping(packet.get("selected_candidate"))
    selected_symbol = _text(selected.get("symbol")) or "none"
    fills = _mapping_sequence(packet.get("fill_ledger"))
    positions = _mapping_sequence(_mapping(packet.get("portfolio_snapshot")).get("positions"))
    safety_labels = _string_sequence(packet.get("safety_labels"))
    lines = [
        "# v6.0 Tomorrow Supervised Crypto Trader Demo",
        "",
        f"- run_id: `{_text(packet.get('run_id'))}`",
        f"- as_of: `{_text(packet.get('as_of'))}`",
        f"- mode: `{_text(packet.get('mode'))}`",
        f"- broker_mode: `{_text(packet.get('broker_mode'))}`",
        f"- decision: `{_text(packet.get('decision'))}`",
        f"- selected_symbol: `{selected_symbol}`",
        f"- final_blocker_status: `{_text(packet.get('final_blocker_status'))}`",
        f"- broker_read_occurred: `{_bool_text(_mapping(packet.get('safety')).get('broker_read_occurred'))}`",
        f"- broker_mutation_occurred: `{_bool_text(_mapping(packet.get('safety')).get('broker_mutation_occurred'))}`",
        f"- paper_submit_occurred: `{_bool_text(_mapping(packet.get('safety')).get('paper_submit_occurred'))}`",
        f"- simulation_mutation_occurred: `{_bool_text(_mapping(packet.get('safety')).get('simulation_mutation_occurred'))}`",
        f"- network_used: `{_bool_text(_mapping(packet.get('safety')).get('network_used'))}`",
        "",
        "## Safety Labels",
    ]
    lines.extend(f"- `{label}`" for label in safety_labels)
    lines.extend(
        [
            "",
            "## Candidate Universe",
            ", ".join(_string_sequence(packet.get("candidate_universe"))) or "none",
            "",
            "## Selected Candidate",
            json.dumps(_json_safe(selected), sort_keys=True),
            "",
            "## Simulated Fills",
            json.dumps(_json_safe(fills), sort_keys=True),
            "",
            "## Final Positions",
            json.dumps(_json_safe(positions), sort_keys=True),
            "",
            "## Next Operator Action",
            json.dumps(_json_safe(_mapping(packet.get("next_operator_action"))), sort_keys=True),
        ]
    )
    return "\n".join(lines)


def validate_tomorrow_crypto_trader_demo(
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
) -> dict[str, object]:
    root = Path(output_root)
    errors: list[str] = []
    artifact_paths = {name: root / name for name in REQUIRED_ARTIFACTS}
    for name, path in artifact_paths.items():
        if not path.is_file():
            errors.append(f"missing_artifact:{name}")

    record = _read_json_or_error(artifact_paths["operating_record.json"], errors)
    manifest = _read_json_or_error(artifact_paths["manifest.json"], errors)
    next_action = _read_json_or_error(artifact_paths["next_operator_action.json"], errors)
    events = _read_jsonl_or_error(artifact_paths["events.jsonl"], errors)
    brief_text = ""
    try:
        brief_text = artifact_paths["operating_brief.md"].read_text(encoding="utf-8")
    except OSError:
        if artifact_paths["operating_brief.md"].is_file():
            errors.append("operating_brief_unreadable")

    if record:
        _validate_record_contract(record, events, errors)
    if manifest:
        _validate_labels("manifest", manifest, errors)
    if next_action:
        _validate_labels("next_operator_action", next_action, errors)
    if brief_text:
        for label in REQUIRED_SAFETY_LABELS:
            if label not in brief_text:
                errors.append(f"operating_brief_missing_label:{label}")
    if _git_ls_files_runs():
        errors.append("generated_runs_artifacts_tracked")
    _validate_forbidden_sentinels(root, errors)

    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "tomorrow_crypto_trader_demo_validation",
        "output_root": str(root),
        "validation_status": "failed" if errors else "passed",
        "errors": errors,
        "required_artifacts": {name: str(path) for name, path in artifact_paths.items()},
    }


def _validate_record_contract(
    record: Mapping[str, object],
    events: Sequence[Mapping[str, object]],
    errors: list[str],
) -> None:
    _validate_labels("operating_record", record, errors)
    safety = _mapping(record.get("safety"))
    mode = _text(record.get("mode"))
    broker_mode = _text(record.get("broker_mode"))
    if mode == "SimBroker":
        expected_false = (
            "paper_submit_authorized",
            "broker_mutation_authorized",
            "paper_submit_occurred",
            "broker_mutation_occurred",
            "broker_state_observed",
            "network_used",
            "credential_values_exposed",
            "live_authorized",
        )
        for field in expected_false:
            if safety.get(field) is not False:
                errors.append(f"simbroker_flag_not_false:{field}")
        if broker_mode != "simulation_broker":
            errors.append("simbroker_broker_mode_mismatch")
        if safety.get("broker_state_mode") != "offline_simulation":
            errors.append("simbroker_broker_state_mode_not_offline")
        provenance = _mapping(record.get("data_provenance"))
        if provenance.get("market_data_observed") is not False:
            errors.append("simbroker_claims_market_data_observed")
        if provenance.get("orderability_observed") is not False:
            errors.append("simbroker_claims_orderability_observed")
        if provenance.get("market_data_basis") not in {
            "offline_fixture",
            "local_replay",
            "stale_local",
            "mixed",
        }:
            errors.append("simbroker_invalid_market_data_basis")
        if safety.get("simulation_mutation_occurred") is True and not events:
            errors.append("events_empty_after_simulated_action")
    if mode == "AlpacaPaper":
        if broker_mode != "alpaca_paper":
            errors.append("alpaca_paper_broker_mode_mismatch")
        if safety.get("live_endpoint_touched") is not False:
            errors.append("alpaca_paper_live_endpoint_touched")

    selected = record.get("selected_candidate")
    if isinstance(selected, Mapping):
        if selected.get("data_gate_passed") is not True:
            errors.append("selected_candidate_without_data_gate")
        if selected.get("orderability_gate_passed") is not True:
            errors.append("selected_candidate_without_orderability_gate")
        risk_decision = _mapping(record.get("risk_decision"))
        if risk_decision.get("status") != "risk_approved":
            errors.append("selected_candidate_without_risk_approval")
        if mode == "AlpacaPaper":
            if selected.get("min_notional_verified") is not True:
                errors.append("paper_candidate_without_min_notional_verification")
            if selected.get("qty_increment_verified") is not True:
                errors.append("paper_candidate_without_qty_increment_verification")


def _validate_labels(
    name: str,
    payload: Mapping[str, object],
    errors: list[str],
) -> None:
    labels = set(_string_sequence(payload.get("safety_labels") or payload.get("labels")))
    for label in REQUIRED_SAFETY_LABELS:
        if label not in labels:
            errors.append(f"{name}_missing_label:{label}")


def _alpaca_paper_packet(
    *,
    output_root: Path,
    run_id: str,
    as_of: datetime,
    universe: Sequence[str],
    git_state: Mapping[str, object],
    allow_alpaca_paper_mutation: bool,
    paper_environment: Mapping[str, object] | None,
    alpaca_paper_snapshot: Mapping[str, object] | None,
    events: list[dict[str, object]],
) -> dict[str, object]:
    status = _alpaca_paper_status(
        allow_alpaca_paper_mutation=allow_alpaca_paper_mutation,
        paper_environment=paper_environment,
        alpaca_paper_snapshot=alpaca_paper_snapshot,
    )
    paper_authorized = status == "not_attempted"
    safety = {
        "broker_mode": "alpaca_paper",
        "paper_submit_authorized": paper_authorized,
        "broker_mutation_authorized": paper_authorized,
        "simulation_mutation_authorized": False,
        "paper_submit_occurred": False,
        "broker_mutation_occurred": False,
        "simulation_mutation_occurred": False,
        "broker_read_occurred": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "live_authorized": False,
        "network_used": False,
    }
    labels = (
        *ALPACA_PAPER_SAFETY_LABELS,
        f"paper_submit_authorized={_bool_text(paper_authorized)}",
        f"broker_mutation_authorized={_bool_text(paper_authorized)}",
        "paper_submit_occurred=false",
        "broker_mutation_occurred=false",
        "live_authorized=false",
    )
    events.append(
        {
            "event_type": "alpaca_paper_mode_blocked",
            "run_id": run_id,
            "timestamp": as_of.isoformat(),
            "status": status,
            "network_used": False,
            "broker_mutation_occurred": False,
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "tomorrow_crypto_trader_demo",
        "operator_command": COMMAND_NAME,
        "run_id": run_id,
        "as_of": as_of.isoformat(),
        "output_root": str(output_root),
        "mode": "AlpacaPaper",
        "broker_mode": "alpaca_paper",
        "git_state": dict(git_state),
        "candidate_universe": list(universe),
        "evaluated_subset": [],
        "evaluated_subset_reason": "alpaca_paper_mode_blocked_before_market_or_broker_access",
        "data_provenance": {
            "data_basis": "not_observed",
            "market_data_observed": False,
            "orderability_observed": False,
            "broker_state_observed": False,
            "network_used": False,
        },
        "signal_states": [],
        "selected_candidate": None,
        "decision": status,
        "risk_decision": {"status": "not_evaluated", "reason": status},
        "execution_intent": None,
        "execution_plan": {"intent_count": 0, "intents": []},
        "planning_policy_decision": {"accepted_count": 0, "skipped_count": 0},
        "broker_mode_adapter": {
            "adapter": "alpaca_paper",
            "adapter_constructed": False,
            "network_used": False,
            "status": status,
        },
        "sim_broker_action_ledger": [],
        "paper_mutation_ledger": [],
        "fill_ledger": [],
        "portfolio_snapshot": {"cash": "", "currency": "USD", "positions": []},
        "final_blocker_status": status,
        "blockers": [status],
        "next_operator_action": {
            "action": _alpaca_next_action(status),
            "status": status,
            "requires_operator": True,
        },
        "safety": safety,
        "safety_labels": list(labels),
        "labels": list(labels),
        "profit_claim": "none",
        "events": events,
    }


def _alpaca_paper_status(
    *,
    allow_alpaca_paper_mutation: bool,
    paper_environment: Mapping[str, object] | None,
    alpaca_paper_snapshot: Mapping[str, object] | None,
) -> str:
    if not allow_alpaca_paper_mutation:
        return "blocked_not_authorized"
    env = paper_environment or _paper_environment_from_os()
    if _text(env.get("APP_PROFILE")) != "paper":
        return "blocked_not_paper_profile"
    if not _paper_credentials_loaded(env):
        return "blocked_credentials_not_loaded"
    snapshot = _mapping(alpaca_paper_snapshot)
    if not snapshot:
        return "not_attempted"
    if _mapping_sequence(snapshot.get("positions")) or _mapping_sequence(
        snapshot.get("open_orders")
    ):
        return "blocked_unexpected_preexisting_position_or_order"
    if snapshot.get("current_run_attribution_complete") is False:
        return "blocked_paper_state_ambiguous"
    if snapshot.get("min_notional_verified") is False or snapshot.get(
        "qty_increment_verified"
    ) is False:
        return "blocked_min_notional_or_increment_not_verified"
    return "not_attempted"


def _paper_environment_from_os() -> dict[str, object]:
    names = (
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    )
    return {
        name: (
            os.environ.get(name)
            if name == "APP_PROFILE"
            else bool(os.environ.get(name))
        )
        for name in names
    }


def _paper_credentials_loaded(env: Mapping[str, object]) -> bool:
    alpaca_pair = bool(env.get("ALPACA_API_KEY")) and (
        bool(env.get("ALPACA_API_SECRET_KEY")) or bool(env.get("ALPACA_SECRET_KEY"))
    )
    apca_pair = bool(env.get("APCA_API_KEY_ID")) and bool(env.get("APCA_API_SECRET_KEY"))
    return alpaca_pair or apca_pair


def _offline_fixture_bars(
    universe: Sequence[str],
    as_of: datetime,
) -> dict[str, tuple[Bar, ...]]:
    bars: dict[str, tuple[Bar, ...]] = {}
    for symbol in universe:
        normalized = normalize_crypto_symbol(symbol)
        if normalized == "BTCUSD":
            bars[normalized] = _fixture_series(normalized, as_of, count=80, start="100", step="1.20")
        elif normalized == "ETHUSD":
            bars[normalized] = _fixture_series(normalized, as_of, count=80, start="220", step="-0.80")
        elif normalized == "SOLUSD":
            bars[normalized] = _fixture_series(
                normalized,
                as_of,
                count=80,
                start="40",
                step="0.35",
                shock_every=9,
            )
        elif normalized == "ADAUSD":
            bars[normalized] = _fixture_series(normalized, as_of, count=30, start="0.40", step="0.003")
        else:
            bars[normalized] = _fixture_series(normalized, as_of, count=60, start="25", step="0")
    return bars


def _fixture_series(
    symbol: str,
    as_of: datetime,
    *,
    count: int,
    start: str,
    step: str,
    shock_every: int = 0,
) -> tuple[Bar, ...]:
    first = as_of - timedelta(hours=count - 1)
    bars: list[Bar] = []
    start_value = Decimal(start)
    step_value = Decimal(step)
    for index in range(count):
        price = start_value + (step_value * Decimal(index))
        if shock_every and index and index % shock_every == 0:
            price *= Decimal("1.08")
        if price <= Decimal("0"):
            price = Decimal("0.01")
        timestamp = first + timedelta(hours=index)
        high = price * Decimal("1.003")
        low = price * Decimal("0.997")
        bars.append(
            Bar(
                symbol=symbol,
                timestamp=timestamp,
                open=price,
                high=high,
                low=low,
                close=price,
                volume=Decimal("1000") + Decimal(index),
            )
        )
    return tuple(bars)


def _evaluate_candidates(
    *,
    bars_by_symbol: Mapping[str, tuple[Bar, ...]],
    universe: Sequence[str],
    as_of: datetime,
) -> tuple[DemoCandidate, ...]:
    candidates: list[DemoCandidate] = []
    for symbol in universe:
        bars = tuple(bars_by_symbol.get(symbol, ()))
        candidates.append(_candidate_for_symbol(symbol, bars, as_of))
    return tuple(candidates)


def _candidate_for_symbol(
    symbol: str,
    bars: tuple[Bar, ...],
    as_of: datetime,
) -> DemoCandidate:
    usable = tuple(bar for bar in sorted(bars, key=lambda item: item.timestamp) if bar.timestamp <= as_of)
    blockers: list[str] = []
    data_gate_passed = len(usable) >= 50
    if not data_gate_passed:
        blockers.append("insufficient_history")
    latest_price = usable[-1].close if usable else None
    short_sma = _mean_close(usable[-20:]) if len(usable) >= 20 else None
    long_sma = _mean_close(usable[-50:]) if len(usable) >= 50 else None
    trend_risk_on = short_sma is not None and long_sma is not None and short_sma > long_sma
    breakout = _is_breakout(usable)
    volatility = _average_abs_return(usable[-20:])
    volatility_sane = volatility <= Decimal("0.06")
    if not trend_risk_on:
        blockers.append("trend_filter_risk_off")
    if not breakout:
        blockers.append("breakout_not_confirmed")
    if not volatility_sane:
        blockers.append("volatility_filter_block")
    orderability_gate_passed = latest_price is not None
    if not orderability_gate_passed:
        blockers.append("latest_price_missing")
    score = Decimal("0")
    if data_gate_passed:
        score += Decimal("0.25")
    if trend_risk_on:
        score += Decimal("0.30")
    if breakout:
        score += Decimal("0.20")
    if volatility_sane:
        score += Decimal("0.15")
    if orderability_gate_passed:
        score += Decimal("0.10")
    signal_state = "trade_candidate" if score >= Decimal("0.75") and not blockers else "no_trade"
    decision = (
        "selected_candidate_for_supervised_demo"
        if signal_state == "trade_candidate"
        else _no_trade_reason(blockers)
    )
    return DemoCandidate(
        symbol=symbol,
        strategy_id=_strategy_id(symbol, trend_risk_on, breakout),
        strategy_family="supervised_demo_crypto_long_only_router",
        signal_state=signal_state,
        decision=decision,
        score=score,
        latest_price=latest_price,
        data_gate_passed=data_gate_passed,
        orderability_gate_passed=orderability_gate_passed,
        risk_gate_passed=False,
        min_notional_verified=True,
        qty_increment_verified=True,
        blockers=tuple(_dedupe(blockers)),
        features={
            "short_sma": short_sma,
            "long_sma": long_sma,
            "trend_risk_on": trend_risk_on,
            "breakout_continuation": breakout,
            "average_abs_return_20": volatility,
            "volatility_sane": volatility_sane,
            "usable_bar_count": len(usable),
            "latest_price": latest_price,
        },
    )


def _build_plan_material(
    *,
    candidates: Sequence[DemoCandidate],
    bars_by_symbol: Mapping[str, tuple[Bar, ...]],
    run_id: str,
    as_of: datetime,
    git_short_sha: str,
    existing_client_order_ids: Iterable[str],
) -> DemoPlanMaterial:
    selected = _select_candidate(candidates)
    duplicate_ids = set(existing_client_order_ids)
    blockers: list[str] = []
    if selected is None:
        blockers.append("no_trade_all_scores_below_threshold")
        empty_plan = build_execution_plan(())
        return DemoPlanMaterial(
            selected_candidate=None,
            order=None,
            quote=None,
            risk=None,
            risk_evaluation=None,
            execution_intents=(),
            execution_plan=empty_plan,
            planning_policy=apply_max_intents_execution_planning_policy(
                empty_plan,
                MaxAcceptedIntentsPolicyConfig(max_accepted_intents=1),
            ),
            client_order_id="",
            blockers=tuple(blockers),
        )
    latest_price = selected.latest_price
    if latest_price is None:
        blockers.append("latest_price_missing")
        latest_price = Decimal("0")
    client_order_id = _client_order_id(
        run_id=run_id,
        symbol=selected.symbol,
        side="buy",
        as_of=as_of,
        strategy_id=selected.strategy_id,
        git_short_sha=git_short_sha,
    )
    if client_order_id in duplicate_ids:
        blockers.append("duplicate_client_order_id")
    quantity = _demo_quantity(latest_price)
    if quantity < MIN_ORDER_SIZE:
        blockers.append("quantity_below_min_order_size")
    notional = quantity * latest_price
    if notional < MIN_NOTIONAL:
        blockers.append("min_notional_not_met")
    if notional > MAX_NOTIONAL_PER_ORDER:
        blockers.append("max_order_notional_exceeded")
    quote = Quote(
        symbol=selected.symbol,
        timestamp=as_of,
        bid=latest_price * Decimal("0.999"),
        ask=latest_price,
    )
    order = ProposedOrder(
        symbol=selected.symbol,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=quantity,
        client_order_id=client_order_id,
    )
    portfolio = PortfolioState(account=Account(SIMULATED_STARTING_CASH, "USD"))
    risk = RiskEngine(
        RiskConfig(
            max_order_notional=MAX_NOTIONAL_PER_ORDER,
            allow_short=False,
            allow_fractional_shares=True,
            max_positions=MAX_OPEN_EXPOSURE_SYMBOLS,
        )
    ).check(order, portfolio, quote)
    if not risk.allowed:
        blockers.append(risk.reason or "risk_rejected")
    if notional > MAX_TOTAL_DEMO_EXPOSURE:
        blockers.append("max_total_demo_exposure_exceeded")

    risk_passed = risk.allowed and not blockers
    selected = DemoCandidate(
        symbol=selected.symbol,
        strategy_id=selected.strategy_id,
        strategy_family=selected.strategy_family,
        signal_state=selected.signal_state,
        decision=selected.decision,
        score=selected.score,
        latest_price=selected.latest_price,
        data_gate_passed=selected.data_gate_passed,
        orderability_gate_passed=selected.orderability_gate_passed,
        risk_gate_passed=risk_passed,
        min_notional_verified=selected.min_notional_verified,
        qty_increment_verified=selected.qty_increment_verified,
        blockers=tuple(_dedupe((*selected.blockers, *blockers))),
        features=selected.features,
    )
    status = "risk_approved" if risk_passed else "risk_rejected"
    previous_bar = tuple(bars_by_symbol[selected.symbol])[-1]
    screener_eval = ScreenerSignalEvaluation(
        symbol=selected.symbol,
        previous_bar=previous_bar,
        quote=quote,
        order=order if risk_passed else None,
    )
    risk_eval = SignalRiskEvaluation(
        symbol=selected.symbol,
        previous_bar=screener_eval.previous_bar,
        quote=screener_eval.quote,
        order=order if risk_passed else None,
        risk=risk,
        status=status,
    )
    intents = build_execution_intents_from_risk_approved((risk_eval,))
    plan = build_execution_plan(intents)
    policy = apply_max_intents_execution_planning_policy(
        plan,
        MaxAcceptedIntentsPolicyConfig(max_accepted_intents=1),
    )
    return DemoPlanMaterial(
        selected_candidate=selected if risk_passed else None,
        order=order if risk_passed else None,
        quote=quote,
        risk=risk,
        risk_evaluation=risk_eval,
        execution_intents=intents,
        execution_plan=plan,
        planning_policy=policy,
        client_order_id=client_order_id,
        blockers=tuple(_dedupe(blockers)),
    )


def _select_candidate(candidates: Sequence[DemoCandidate]) -> DemoCandidate | None:
    eligible = [
        candidate
        for candidate in candidates
        if candidate.signal_state == "trade_candidate"
        and candidate.data_gate_passed
        and candidate.orderability_gate_passed
        and not candidate.blockers
    ]
    if not eligible:
        return None
    return sorted(eligible, key=lambda item: (-item.score, item.symbol))[0]


def _plan_events(
    plan_material: DemoPlanMaterial,
    *,
    run_id: str,
    as_of: datetime,
) -> list[dict[str, object]]:
    return [
        {
            "event_type": "execution_intent_created",
            "run_id": run_id,
            "timestamp": as_of.isoformat(),
            "intent_count": len(plan_material.execution_intents),
            "client_order_id": plan_material.client_order_id,
        },
        {
            "event_type": "execution_plan_created",
            "run_id": run_id,
            "timestamp": as_of.isoformat(),
            "intent_count": len(plan_material.execution_plan.intents),
            "immutable_pre_broker_plan": True,
        },
        {
            "event_type": "planning_policy_decision",
            "run_id": run_id,
            "timestamp": as_of.isoformat(),
            "accepted_count": len(plan_material.planning_policy.accepted_intents),
            "skipped_count": len(plan_material.planning_policy.skipped_intents),
        },
    ]


def _simbroker_safety(*, simulation_mutation_occurred: bool) -> dict[str, object]:
    return {
        "broker_mode": "simulation_broker",
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "simulation_mutation_authorized": True,
        "paper_submit_occurred": False,
        "broker_mutation_occurred": False,
        "simulation_mutation_occurred": simulation_mutation_occurred,
        "broker_read_occurred": False,
        "broker_state_observed": False,
        "broker_state_mode": "offline_simulation",
        "market_data_observed": False,
        "orderability_observed": False,
        "network_used": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "live_authorized": False,
    }


def _risk_decision(risk: RiskVerdict | None) -> dict[str, object]:
    if risk is None:
        return {"status": "not_evaluated", "reason": "no_selected_candidate"}
    return {
        "status": "risk_approved" if risk.allowed else "risk_rejected",
        "allowed": risk.allowed,
        "reason": risk.reason,
        "order_notional": getattr(risk, "order_notional", None),
        "detail": getattr(risk, "detail", None),
        "max_notional_per_order": MAX_NOTIONAL_PER_ORDER,
        "max_total_demo_exposure": MAX_TOTAL_DEMO_EXPOSURE,
        "max_symbols_with_open_exposure": MAX_OPEN_EXPOSURE_SYMBOLS,
        "long_only": True,
        "no_leverage": True,
        "no_shorting": True,
    }


def _execution_intent_record(plan_material: DemoPlanMaterial) -> dict[str, object] | None:
    if plan_material.risk_evaluation is None or plan_material.order is None:
        return None
    order = plan_material.order
    return {
        "source": "SignalRiskEvaluation",
        "status": plan_material.risk_evaluation.status,
        "symbol": order.symbol,
        "side": order.side.value,
        "order_type": order.order_type.value,
        "quantity": order.quantity,
        "client_order_id": order.client_order_id,
        "note": "ExecutionIntent is not a broker order.",
    }


def _execution_plan_record(plan: ExecutionPlan) -> dict[str, object]:
    return {
        "immutable_pre_broker": True,
        "intent_count": len(plan.intents),
        "intents": [
            {
                "symbol": intent.source_evaluation.symbol,
                "status": intent.source_evaluation.status,
            }
            for intent in plan.intents
        ],
    }


def _planning_policy_record(policy: PlanningPolicyResult) -> dict[str, object]:
    return {
        "policy": "max_accepted_intents",
        "max_accepted_intents": 1,
        "accepted_count": len(policy.accepted_intents),
        "skipped_count": len(policy.skipped_intents),
        "accepted_symbols": [intent.source_evaluation.symbol for intent in policy.accepted_intents],
        "skipped": [
            {
                "symbol": skipped.intent.source_evaluation.symbol,
                "reason": skipped.reason,
            }
            for skipped in policy.skipped_intents
        ],
        "submitted_directly": False,
    }


def _next_action(decision: str, final_blocker: str) -> dict[str, object]:
    if final_blocker == "none":
        return {
            "action": "review_simulated_demo_packet",
            "requires_operator": True,
            "paper_or_live_authorization": "not_authorized",
            "next_safe_command": "scripts\\validate_tomorrow_crypto_trader_demo.ps1 -OutputRoot runs\\crypto_trader_demo\\latest",
        }
    return {
        "action": "review_blocked_no_trade_reasons",
        "requires_operator": True,
        "decision": decision,
        "blocker": final_blocker,
    }


def _alpaca_next_action(status: str) -> str:
    if status == "blocked_not_authorized":
        return "rerun_only_if_operator_explicitly_authorizes_alpaca_paper_mutation"
    if status in {"blocked_not_paper_profile", "blocked_credentials_not_loaded"}:
        return "operator_prepare_dedicated_paper_shell_or_use_simbroker"
    if status.startswith("blocked_"):
        return "repair_or_review_paper_blocker_before_any_mutation"
    return "not_attempted_simbroker_acceptance_is_primary"


def _sim_decision(
    plan_material: DemoPlanMaterial,
    broker_result: Mapping[str, object],
) -> str:
    if _text(broker_result.get("status")) == "completed" and plan_material.selected_candidate:
        return "offline_simulated_trade_only"
    if plan_material.blockers:
        if "duplicate_client_order_id" in plan_material.blockers:
            return "blocked_duplicate_client_order_id"
        if any("risk" in blocker for blocker in plan_material.blockers):
            return "no_trade_risk_block"
    blocker = _text(broker_result.get("blocker"))
    if blocker:
        return blocker
    return "no_trade_all_scores_below_threshold"


def _final_blocker(
    plan_material: DemoPlanMaterial,
    broker_result: Mapping[str, object],
) -> str:
    broker_blocker = _text(broker_result.get("blocker"))
    if broker_blocker:
        return broker_blocker
    if plan_material.blockers:
        return ",".join(plan_material.blockers)
    if not plan_material.selected_candidate:
        return "no_trade_all_scores_below_threshold"
    return "none"


def _client_order_id(
    *,
    run_id: str,
    symbol: str,
    side: str,
    as_of: datetime,
    strategy_id: str,
    git_short_sha: str,
) -> str:
    bucket = as_of.strftime("%Y%m%d%H")
    strategy_token = "".join(ch for ch in strategy_id.lower() if ch.isalnum())[:10]
    digest = hashlib.sha256(
        f"{run_id}|{symbol}|{side}|{bucket}|{strategy_id}|{git_short_sha}".encode(
            "utf-8"
        )
    ).hexdigest()[:8]
    return f"v6_demo_{symbol.lower()}_{side}_{bucket}_{strategy_token}_{git_short_sha}_{digest}"[:120]


def _run_id(
    mode: str,
    as_of: datetime,
    universe: Sequence[str],
    git_short_sha: str,
) -> str:
    digest = hashlib.sha256(
        "|".join((mode, as_of.isoformat(), ",".join(universe), git_short_sha)).encode(
            "utf-8"
        )
    ).hexdigest()[:10]
    return f"v6_demo_{as_of.strftime('%Y%m%dT%H%M%SZ')}_{digest}"


def _demo_quantity(price: Decimal) -> Decimal:
    if price <= 0:
        return Decimal("0")
    return (MAX_NOTIONAL_PER_ORDER / price).quantize(QTY_INCREMENT, rounding=ROUND_DOWN)


def _strategy_id(symbol: str, trend_risk_on: bool, breakout: bool) -> str:
    if trend_risk_on and breakout:
        return f"{symbol.lower()}_trend_breakout_continuation_demo"
    if trend_risk_on:
        return f"{symbol.lower()}_sma_momentum_demo"
    return f"{symbol.lower()}_cash_no_trade_demo"


def _no_trade_reason(blockers: Sequence[str]) -> str:
    if "insufficient_history" in blockers:
        return "no_trade_data_quality_block"
    if "volatility_filter_block" in blockers:
        return "no_trade_risk_block"
    if "trend_filter_risk_off" in blockers:
        return "no_trade_all_scores_below_threshold"
    return "no_trade_orderability_block" if blockers else "no_trade_all_scores_below_threshold"


def _is_breakout(bars: Sequence[Bar]) -> bool:
    if len(bars) < 21:
        return False
    latest = bars[-1].close
    prior_high = max(bar.close for bar in bars[-21:-1])
    return latest > prior_high


def _average_abs_return(bars: Sequence[Bar]) -> Decimal:
    if len(bars) < 2:
        return Decimal("0")
    returns: list[Decimal] = []
    for previous, current in zip(bars, bars[1:]):
        if previous.close <= 0:
            continue
        returns.append(abs((current.close - previous.close) / previous.close))
    if not returns:
        return Decimal("0")
    return sum(returns, Decimal("0")) / Decimal(len(returns))


def _mean_close(bars: Sequence[Bar]) -> Decimal:
    if not bars:
        return Decimal("0")
    return sum((bar.close for bar in bars), Decimal("0")) / Decimal(len(bars))


def _write_bars_csv(path: Path, bars_by_symbol: Mapping[str, Sequence[Bar]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("timestamp", "symbol", "asset_class", "open", "high", "low", "close", "volume"))
        for symbol in sorted(bars_by_symbol):
            for bar in bars_by_symbol[symbol]:
                writer.writerow(
                    (
                        bar.timestamp.isoformat(),
                        bar.symbol,
                        "crypto",
                        _decimal_text(bar.open),
                        _decimal_text(bar.high),
                        _decimal_text(bar.low),
                        _decimal_text(bar.close),
                        _decimal_text(bar.volume),
                    )
                )


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_events(path: Path, events: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for event in events:
            stream.write(json.dumps(_json_safe(event), sort_keys=True))
            stream.write("\n")


def _read_json_or_error(path: Path, errors: list[str]) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        errors.append(f"invalid_json:{path.name}")
        return {}
    except OSError:
        errors.append(f"unreadable_json:{path.name}")
        return {}
    if not isinstance(payload, Mapping):
        errors.append(f"json_not_object:{path.name}")
        return {}
    return payload


def _read_jsonl_or_error(
    path: Path,
    errors: list[str],
) -> tuple[Mapping[str, object], ...]:
    if not path.is_file():
        return ()
    records: list[Mapping[str, object]] = []
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"invalid_jsonl:{path.name}:{line_number}")
                continue
            if not isinstance(payload, Mapping):
                errors.append(f"jsonl_record_not_object:{path.name}:{line_number}")
                continue
            records.append(payload)
    except OSError:
        errors.append(f"unreadable_jsonl:{path.name}")
    return tuple(records)


def _validate_forbidden_sentinels(root: Path, errors: list[str]) -> None:
    if not root.exists():
        return
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError:
            errors.append(f"artifact_unreadable_for_sentinel_scan:{path.name}")
            continue
        for sentinel in FORBIDDEN_SENTINELS:
            if sentinel in text:
                errors.append(f"credential_sentinel_exposed:{path.name}")


def _git_state() -> dict[str, object]:
    head = _git_output("rev-parse", "HEAD")
    short_sha = head[:8] if head else "unknown"
    status_short = _git_output("status", "--short")
    return {
        "head": head or "unknown",
        "short_sha": short_sha,
        "dirty": bool(status_short.strip()),
        "status_short": status_short.splitlines(),
    }


def _git_output(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _git_ls_files_runs() -> str:
    return _git_output("ls-files", "runs")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _generated_under_runs(path: Path) -> bool:
    parts = tuple(part.lower() for part in path.parts)
    return "runs" in parts


def _portfolio_snapshot(portfolio: PortfolioState) -> dict[str, object]:
    return {
        "cash": portfolio.account.cash,
        "currency": portfolio.account.currency,
        "positions": [_position_snapshot(position) for position in portfolio.positions],
        "gross_exposure": sum(
            position.quantity * position.average_price for position in portfolio.positions
        ),
        "timestamp": None if portfolio.timestamp is None else portfolio.timestamp.isoformat(),
    }


def _position_snapshot(position: object) -> dict[str, object]:
    return {
        "symbol": getattr(position, "symbol", ""),
        "quantity": getattr(position, "quantity", ""),
        "average_price": getattr(position, "average_price", ""),
    }


def _mode(value: object) -> Mode:
    if value in {"SimBroker", "AlpacaPaper"}:
        return value  # type: ignore[return-value]
    raise ValueError("mode must be SimBroker or AlpacaPaper.")


def _utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str and value.strip():
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError(f"{field_name} must be a timezone-aware UTC datetime.")
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include timezone information.")
    return parsed.astimezone(UTC)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mapping_sequence(value: object) -> tuple[Mapping[str, object], ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item).strip())
    if value in (None, ""):
        return ()
    return (str(value),)


def _text(value: object) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "true" if value else "false"
    enum_value = getattr(value, "value", None)
    if type(enum_value) is str:
        return enum_value.strip()
    return str(value).strip()


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=COMMAND_NAME,
        description="Run or validate the v6.0 supervised crypto trader demo.",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--mode", choices=("SimBroker", "AlpacaPaper"), default="SimBroker")
    parser.add_argument("--allow-alpaca-paper-mutation", action="store_true")
    parser.add_argument("--as-of", default="")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    if args.validate_only:
        validation = validate_tomorrow_crypto_trader_demo(args.output_root)
        if args.format == "json":
            print(json.dumps(_json_safe(validation), sort_keys=True))
        else:
            print(f"tomorrow_crypto_trader_demo_validation_status={validation['validation_status']}")
            print("errors=" + ",".join(_string_sequence(validation.get("errors"))))
        return 0 if validation["validation_status"] == "passed" else 1

    packet = run_tomorrow_crypto_trader_demo(
        output_root=args.output_root,
        mode=args.mode,
        allow_alpaca_paper_mutation=args.allow_alpaca_paper_mutation,
        as_of=args.as_of or None,
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(packet), sort_keys=True))
    else:
        safety = _mapping(packet.get("safety"))
        artifact_paths = _mapping(packet.get("artifact_paths"))
        print("tomorrow_crypto_trader_demo_status=complete")
        print(f"mode={packet.get('mode', '')}")
        print(f"broker_mode={packet.get('broker_mode', '')}")
        print(f"decision={packet.get('decision', '')}")
        print(f"final_blocker_status={packet.get('final_blocker_status', '')}")
        print(f"simulation_mutation_occurred={_bool_text(safety.get('simulation_mutation_occurred'))}")
        print(f"paper_submit_occurred={_bool_text(safety.get('paper_submit_occurred'))}")
        print(f"broker_mutation_occurred={_bool_text(safety.get('broker_mutation_occurred'))}")
        print(f"network_used={_bool_text(safety.get('network_used'))}")
        print(f"artifact_operating_record={artifact_paths.get('operating_record', '')}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
