"""v6.2 supervised crypto trader demo with an offline simulation broker.

The default path is intentionally local-only. It creates fixture-backed crypto
bars, evaluates a small supervised decision router, builds an ExecutionPlan, and
lets a deterministic simulation broker consume only accepted plan intents while
persisting simulated cash, positions, orders, fills, and cycle history. It also
emits a deterministic no-submit paper-readiness preview packet.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable, Mapping, Sequence
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

from algotrader.core.types import Bar, Fill, OrderSide, OrderStatus, OrderType, ProposedOrder, Quote
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
from algotrader.portfolio.state import Account, PortfolioState, Position, apply_fill
from algotrader.risk.config import RiskConfig
from algotrader.risk.engine import RiskEngine
from algotrader.risk.state import RiskVerdict
from algotrader.signals.crypto_trend import normalize_crypto_symbol

SCHEMA_VERSION = "v6_3_crypto_gated_broker_observed_readiness_lane_v1"
COMMAND_NAME = "run_tomorrow_crypto_trader_demo"
VALIDATOR_COMMAND_NAME = "validate_tomorrow_crypto_trader_demo"
DEFAULT_OUTPUT_ROOT = Path("runs/crypto_trader_demo/latest")
DEFAULT_AS_OF = datetime(2026, 7, 6, 14, 30, tzinfo=UTC)
DEFAULT_UNIVERSE = ("BTCUSD", "ETHUSD", "SOLUSD", "ADAUSD")
DEFAULT_SCENARIO = "risk_on"
DEFAULT_ALPACA_PAPER_ENDPOINT = "https://paper-api.alpaca.markets"

MAX_NOTIONAL_PER_ORDER = Decimal("5")
MAX_TOTAL_DEMO_EXPOSURE = Decimal("25")
MAX_OPEN_EXPOSURE_SYMBOLS = 2
SIMULATED_STARTING_CASH = Decimal("25")
QTY_INCREMENT = Decimal("0.00000001")
MIN_ORDER_SIZE = Decimal("0.00000001")
MIN_NOTIONAL = Decimal("1")
PAPER_READINESS_PRICE_MAX_AGE = timedelta(hours=2)
BROKER_OBSERVED_PRICE_MAX_AGE = PAPER_READINESS_PRICE_MAX_AGE

OBSERVED_LATEST_PRICE_SOURCES = (
    "broker_observed",
    "provider_observed",
)
READINESS_ONLY_LATEST_PRICE_SOURCES = (
    "deterministic_fixture",
    "local_replay",
)
LATEST_PRICE_SOURCES = (
    *OBSERVED_LATEST_PRICE_SOURCES,
    *READINESS_ONLY_LATEST_PRICE_SOURCES,
    "unavailable",
    "ambiguous",
)
LATEST_PRICE_FRESHNESS_STATUSES = (
    "fresh",
    "stale",
    "missing_timestamp",
    "unavailable",
    "ambiguous",
)

PAPER_READINESS_DECISIONS = (
    "fixture_ready_preview",
    "fixture_blocked_preview",
)

PAPER_READINESS_BLOCKERS = (
    "blocked_missing_price",
    "blocked_stale_price",
    "blocked_missing_orderability",
    "blocked_min_notional_or_increment_not_verified",
    "blocked_exceeds_max_notional",
    "blocked_exceeds_total_exposure",
    "blocked_duplicate_client_order_id",
    "blocked_open_order_present",
    "blocked_unexpected_preexisting_position",
    "blocked_no_selected_candidate",
    "blocked_sim_state_reconciliation_failed",
)

BROKER_OBSERVED_READINESS_DECISIONS = (
    "broker_observed_ready_preview",
    "broker_observed_ready_preview_with_fixture_price",
    "broker_observed_blocked_preview",
    "broker_observed_not_attempted",
    "broker_observed_blocked_credentials_not_loaded",
    "broker_observed_blocked_not_authorized",
    "broker_observed_blocked_not_paper_profile",
    "broker_observed_blocked_live_endpoint_detected",
    "broker_observed_blocked_adapter_unavailable",
    "broker_observed_blocked_read_not_implemented",
    "broker_observed_blocked_read_failed",
    "broker_observed_blocked_ambiguous_response",
)

BROKER_OBSERVED_SPECIFIC_BLOCKERS = (
    "broker_min_notional_field_missing",
    "broker_min_notional_direct_field_missing_but_equivalent_available",
    "broker_min_notional_equivalent_not_available",
    "broker_min_order_size_field_missing",
    "broker_qty_increment_field_missing",
    "broker_orderability_metadata_missing",
    "broker_orderability_metadata_ambiguous",
    "broker_price_metadata_missing",
    "broker_price_metadata_stale",
    "broker_latest_price_missing",
    "broker_latest_price_stale",
    "broker_latest_price_timestamp_missing",
    "broker_latest_price_ambiguous",
    "broker_latest_price_symbol_mismatch",
    "broker_price_not_broker_observed",
    "broker_price_source_not_acceptable_for_full_readiness",
    "broker_price_evidence_not_verified",
    "broker_price_adapter_unavailable",
    "broker_price_read_failed",
    "broker_price_read_not_authorized",
    "broker_price_read_blocked_not_paper_profile",
    "broker_price_read_blocked_credentials_not_loaded",
    "broker_price_read_blocked_live_endpoint_detected",
    "broker_quote_bid_ask_invalid",
    "broker_trade_price_invalid",
    "broker_bar_close_invalid",
    "broker_price_source_not_acceptable_for_equivalence",
    "broker_intended_notional_below_min_notional",
    "broker_derived_min_notional_exceeds_intended_notional",
    "broker_estimated_quantity_below_min_order_size",
    "broker_estimated_quantity_not_increment_aligned",
    "broker_min_order_size_or_increment_missing_for_derivation",
    "broker_quantity_increment_alignment_failed",
    "broker_min_notional_not_verified",
)

BROKER_OBSERVED_CONSISTENCY_FIELDS = (
    "broker_read_authorized",
    "broker_read_attempted",
    "broker_read_occurred",
    "broker_read_blocked",
    "broker_read_adapter_unavailable",
    "broker_read_failed",
    "broker_state_observed",
    "network_used",
    "broker_observed_readiness_decision",
    "broker_observed_blocker",
    "live_endpoint_touched",
    "credential_values_exposed",
    "paper_submit_occurred",
    "broker_mutation_occurred",
    "broker_observed_orderability_source",
    "broker_observed_orderability_check_status",
    "broker_observed_min_notional_value",
    "broker_observed_min_notional_source",
    "broker_observed_min_notional_check_status",
    "broker_observed_min_order_size_value",
    "broker_observed_min_order_size_source",
    "broker_observed_min_order_size_check_status",
    "broker_observed_quantity_increment_value",
    "broker_observed_quantity_increment_source",
    "broker_observed_quantity_increment_check_status",
    "broker_observed_price_source",
    "broker_observed_price_check_status",
    "latest_price_value",
    "latest_price_source",
    "latest_price_observed_at",
    "latest_price_age_seconds",
    "latest_price_symbol",
    "latest_price_bid",
    "latest_price_ask",
    "latest_price_mid",
    "latest_price_last",
    "latest_price_basis",
    "latest_price_freshness_status",
    "latest_price_source_acceptability",
    "price_used_for_quantity",
    "price_used_for_min_notional_derivation",
    "price_evidence_status",
    "price_evidence_blocker",
    "direct_min_notional_available",
    "direct_min_notional_source",
    "derived_min_notional_available",
    "derived_min_notional_value",
    "derived_min_notional_formula",
    "derived_min_notional_sources",
    "derived_min_notional_check_status",
    "min_notional_equivalence_basis",
    "price_source_for_derivation",
    "price_source_acceptability",
    "final_feasibility_basis",
)

BROKER_OBSERVED_APPROVED_READINESS_DECISIONS = (
    "broker_observed_ready_preview",
    "broker_observed_ready_preview_with_fixture_price",
)

RUN_SUMMARY_CONSOLE_FIELDS = (
    "status",
    "mode",
    "broker_mode",
    "scenario",
    "cycle_index",
    "planned_action",
    "decision",
    "final_blocker_status",
    *BROKER_OBSERVED_CONSISTENCY_FIELDS,
)

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
    "broker_read_occurred=false",
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
    "run_summary.json",
    "paper_readiness_packet.json",
    "paper_readiness_packet.md",
)

STATE_ARTIFACTS = (
    "simbroker_state.json",
    "positions.json",
    "fills.jsonl",
    "cycle_history.jsonl",
    "events.jsonl",
)

FORBIDDEN_SENTINELS = (
    "SENTINEL_ALPACA_SECRET_DO_NOT_PRINT",
    "script-paper-key-value-not-for-output",
    "script-paper-secret-value-not-for-output",
    "crypto-cycle-key-value-not-for-output",
    "credential-value-not-for-output",
)

Mode = Literal["SimBroker", "AlpacaPaper"]
Scenario = Literal["risk_on", "risk_off", "all_blocked", "bad_data"]

__all__ = [
    "ALPACA_PAPER_SAFETY_LABELS",
    "COMMAND_NAME",
    "DEFAULT_AS_OF",
    "DEFAULT_OUTPUT_ROOT",
    "DEFAULT_SCENARIO",
    "DEFAULT_UNIVERSE",
    "MAX_NOTIONAL_PER_ORDER",
    "MAX_TOTAL_DEMO_EXPOSURE",
    "REQUIRED_ARTIFACTS",
    "REQUIRED_SAFETY_LABELS",
    "SCHEMA_VERSION",
    "SIMBROKER_SAFETY_LABELS",
    "STATE_ARTIFACTS",
    "VALIDATOR_COMMAND_NAME",
    "SimulationBroker",
    "build_no_submit_paper_readiness_packet",
    "main",
    "render_operating_brief",
    "render_broker_observed_readiness_packet",
    "render_paper_readiness_packet",
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
    planned_action: str
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


@dataclass(frozen=True, slots=True)
class SimBrokerStateSnapshot:
    state_root: Path
    exists: bool
    payload: Mapping[str, object]
    portfolio: PortfolioState
    seen_client_order_ids: tuple[str, ...]
    orders: tuple[Mapping[str, object], ...]
    fills: tuple[Mapping[str, object], ...]
    cycle_history: tuple[Mapping[str, object], ...]
    events: tuple[Mapping[str, object], ...]
    open_orders: tuple[Mapping[str, object], ...]
    errors: tuple[str, ...]


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
        cycle_index: int = 0,
        cycle_key: str = "",
    ) -> dict[str, object]:
        if plan.intents and not planning_policy.accepted_intents:
                return self._block(
                    "no_policy_accepted_intents",
                    run_id=run_id,
                    as_of=as_of,
                    event_sink=event_sink,
                    cycle_index=cycle_index,
                    cycle_key=cycle_key,
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
                    cycle_index=cycle_index,
                    cycle_key=cycle_key,
                )
            client_order_id = order.client_order_id or ""
            if not client_order_id:
                return self._block(
                    "missing_client_order_id",
                    run_id=run_id,
                    as_of=as_of,
                    event_sink=event_sink,
                    cycle_index=cycle_index,
                    cycle_key=cycle_key,
                )
            if client_order_id in self._seen_client_order_ids:
                return self._block(
                    "duplicate_client_order_id",
                    run_id=run_id,
                    as_of=as_of,
                    event_sink=event_sink,
                    cycle_index=cycle_index,
                    cycle_key=cycle_key,
                    symbol=order.symbol,
                    client_order_id=client_order_id,
                )
            if risk is None or not risk.allowed:
                return self._block(
                    "risk_not_approved",
                    run_id=run_id,
                    as_of=as_of,
                    event_sink=event_sink,
                    cycle_index=cycle_index,
                    cycle_key=cycle_key,
                    symbol=order.symbol,
                    client_order_id=client_order_id,
                )

            self._seen_client_order_ids.add(client_order_id)
            action = {
                "event_type": "simulation_order_submitted",
                "run_id": run_id,
                "cycle_index": cycle_index,
                "cycle_key": cycle_key,
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
            self._record_execution(
                execution,
                run_id=run_id,
                event_sink=event_sink,
                cycle_index=cycle_index,
                cycle_key=cycle_key,
            )
            if execution.fill is not None:
                self._portfolio = apply_fill(self._portfolio, execution.fill)
                event_sink.append(
                    {
                        "event_type": "simulation_reconciliation_checked",
                        "run_id": run_id,
                        "cycle_index": cycle_index,
                        "cycle_key": cycle_key,
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
        cycle_index: int = 0,
        cycle_key: str = "",
    ) -> None:
        ack = execution.ack
        ack_event = {
            "event_type": "simulation_order_acknowledged",
            "run_id": run_id,
            "cycle_index": cycle_index,
            "cycle_key": cycle_key,
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
            "cycle_index": cycle_index,
            "cycle_key": cycle_key,
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
        cycle_index: int = 0,
        cycle_key: str = "",
        symbol: str = "",
        client_order_id: str = "",
    ) -> dict[str, object]:
        event = {
            "event_type": "simulation_blocked",
            "run_id": run_id,
            "cycle_index": cycle_index,
            "cycle_key": cycle_key,
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
    broker_observed_readiness: bool = False,
    allow_alpaca_paper_read: bool = False,
    universe: Sequence[str] = DEFAULT_UNIVERSE,
    as_of: datetime | str | None = None,
    state_root: Path | str | None = None,
    scenario: Scenario | str = DEFAULT_SCENARIO,
    reset_state: bool = False,
    write_artifacts: bool = True,
    existing_client_order_ids: Iterable[str] = (),
    paper_environment: Mapping[str, object] | None = None,
    alpaca_paper_snapshot: Mapping[str, object] | None = None,
    broker_observed_client: object | None = None,
    broker_observed_client_factory: Callable[[], object] | None = None,
    broker_observed_network_used: bool | None = None,
) -> dict[str, object]:
    """Run the v6.1 deterministic SimBroker operating-loop packet builder.

    SimBroker is the only implemented acceptance path. AlpacaPaper mode returns
    explicit gated statuses without contacting a broker.
    """

    run_mode = _mode(mode)
    as_of_value = _utc_datetime(as_of or DEFAULT_AS_OF, "as_of")
    scenario_value = _scenario(scenario)
    root = Path(output_root)
    state_root_path = _state_root(root, state_root)
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

    state_snapshot = _load_simbroker_state(
        state_root_path,
        reset_state=reset_state,
    )
    cycle_index = _next_cycle_index(state_snapshot)
    cycle_key = _cycle_key(
        as_of=as_of_value,
        scenario=scenario_value,
        universe=normalized_universe,
    )
    events[0].update(
        {
            "cycle_index": cycle_index,
            "cycle_key": cycle_key,
            "scenario": scenario_value,
            "state_root": str(state_root_path),
            "reset_state": reset_state,
        }
    )

    bars_by_symbol = _offline_fixture_bars(
        normalized_universe,
        as_of_value,
        scenario_value,
    )
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
                "cycle_index": cycle_index,
                "cycle_key": cycle_key,
                "timestamp": as_of_value.isoformat(),
                "candidate": candidate.to_dict(),
            }
        )

    state_blocker = _state_blocker(state_snapshot)
    combined_existing_client_order_ids = _dedupe(
        (*state_snapshot.seen_client_order_ids, *tuple(str(item) for item in existing_client_order_ids))
    )
    sim_broker = SimulationBroker(
        portfolio=state_snapshot.portfolio,
        existing_client_order_ids=combined_existing_client_order_ids,
    )
    if state_blocker:
        plan_material = _empty_plan_material(
            planned_action="blocked_state_reconciliation",
            blockers=(state_blocker,),
            selected_candidate=None,
        )
        broker_result = _blocked_broker_result(
            state_blocker,
            portfolio=state_snapshot.portfolio,
        )
        events.append(
            {
                "event_type": "simulation_blocked",
                "run_id": run_id,
                "cycle_index": cycle_index,
                "cycle_key": cycle_key,
                "timestamp": as_of_value.isoformat(),
                "broker_mode": "simulation_broker",
                "blocker": state_blocker,
                "simulated": True,
            }
        )
    else:
        plan_material = _build_plan_material(
            candidates=candidates,
            bars_by_symbol=bars_by_symbol,
            run_id=run_id,
            as_of=as_of_value,
            git_short_sha=git_state["short_sha"],
            existing_client_order_ids=combined_existing_client_order_ids,
            portfolio=state_snapshot.portfolio,
            scenario=scenario_value,
        )
        events.extend(
            _plan_events(
                plan_material,
                run_id=run_id,
                as_of=as_of_value,
                cycle_index=cycle_index,
                cycle_key=cycle_key,
            )
        )
        broker_result = sim_broker.apply_plan(
            plan=plan_material.execution_plan,
            planning_policy=plan_material.planning_policy,
            run_id=run_id,
            as_of=as_of_value,
            event_sink=events,
            cycle_index=cycle_index,
            cycle_key=cycle_key,
        )
    decision = _sim_decision(plan_material, broker_result)
    final_blocker = _final_blocker(plan_material, broker_result)
    simulation_mutation_occurred = bool(sim_broker.fill_ledger)
    state_reconciliation = {
        "status": "failed" if state_snapshot.errors else "passed",
        "errors": list(state_snapshot.errors),
        "state_root": str(state_root_path),
        "state_exists": state_snapshot.exists,
        "open_simulated_order_count": len(state_snapshot.open_orders),
        "portfolio_before": _portfolio_snapshot(state_snapshot.portfolio),
        "portfolio_after": _portfolio_snapshot(sim_broker.portfolio),
    }
    paper_readiness_packet = _paper_readiness_packet_for_plan(
        run_id=run_id,
        cycle_index=cycle_index,
        as_of=as_of_value,
        planned_action=plan_material.planned_action,
        candidates=candidates,
        plan_material=plan_material,
        state_snapshot=state_snapshot,
        state_reconciliation=state_reconciliation,
        existing_client_order_ids=combined_existing_client_order_ids,
    )
    broker_observed_preview = _broker_observed_readiness_preview(
        run_id=run_id,
        cycle_index=cycle_index,
        as_of=as_of_value,
        requested=broker_observed_readiness,
        broker_read_authorized=allow_alpaca_paper_read,
        fixture_readiness=paper_readiness_packet,
        paper_environment=paper_environment,
        broker_client=broker_observed_client,
        broker_client_factory=broker_observed_client_factory,
        network_used=broker_observed_network_used,
    )
    broker_read_occurred = broker_observed_preview["broker_read_occurred"] is True
    broker_state_observed = broker_observed_preview["broker_state_observed"] is True
    run_network_used = broker_observed_preview["network_used"] is True
    safety = _simbroker_safety(
        simulation_mutation_occurred=simulation_mutation_occurred,
        broker_read_occurred=broker_read_occurred,
        broker_state_observed=broker_state_observed,
        network_used=run_network_used,
    )
    safety_labels = _simbroker_labels(
        simulation_mutation_occurred=simulation_mutation_occurred,
        broker_read_occurred=broker_read_occurred,
        broker_state_observed=broker_state_observed,
        network_used=run_network_used,
    )
    broker_observed_telemetry = _broker_observed_consistency_summary(
        broker_observed=broker_observed_preview,
        safety=safety,
    )
    events.append(
        {
            "event_type": "paper_readiness_evaluated",
            "run_id": run_id,
            "cycle_index": cycle_index,
            "cycle_key": cycle_key,
            "timestamp": as_of_value.isoformat(),
            "readiness_decision": paper_readiness_packet["readiness_decision"],
            "blocker_code": paper_readiness_packet["blocker_code"],
            "readiness_basis": paper_readiness_packet["readiness_basis"],
            "paper_submit_authorized": False,
            "paper_submit_occurred": False,
            "broker_mutation_occurred": False,
            "broker_read_occurred": False,
            "network_used": False,
        }
    )
    if broker_observed_readiness:
        events.append(
            {
                "event_type": "broker_observed_readiness_evaluated",
                "run_id": run_id,
                "cycle_index": cycle_index,
                "cycle_key": cycle_key,
                "timestamp": as_of_value.isoformat(),
                "broker_observed_readiness_decision": broker_observed_preview[
                    "broker_observed_readiness_decision"
                ],
                "blocker_code": broker_observed_preview["blocker_code"],
                "broker_read_authorized": broker_observed_preview["broker_read_authorized"],
                "broker_read_attempted": broker_observed_preview["broker_read_attempted"],
                "broker_read_occurred": broker_observed_preview["broker_read_occurred"],
                "broker_read_blocked": broker_observed_preview["broker_read_blocked"],
                "broker_read_adapter_unavailable": broker_observed_preview[
                    "broker_read_adapter_unavailable"
                ],
                "broker_read_failed": broker_observed_preview["broker_read_failed"],
                "broker_state_observed": broker_observed_preview["broker_state_observed"],
                "live_endpoint_touched": broker_observed_preview["live_endpoint_touched"],
                "paper_submit_authorized": False,
                "paper_submit_occurred": False,
                "broker_mutation_occurred": False,
                "network_used": broker_observed_preview["network_used"],
                "blocker_codes": list(
                    _string_sequence(broker_observed_preview.get("blocker_codes"))
                ),
                "orderability_check_status": _text(
                    _mapping(
                        broker_observed_preview.get("broker_observed_orderability_check")
                    ).get("status")
                ),
                "min_notional_check_status": _text(
                    _mapping(
                        broker_observed_preview.get("broker_observed_min_notional_check")
                    ).get("status")
                ),
                "min_order_size_check_status": _text(
                    _mapping(
                        broker_observed_preview.get("broker_observed_min_order_size_check")
                    ).get("status")
                ),
                "quantity_increment_check_status": _text(
                    _mapping(
                        broker_observed_preview.get(
                            "broker_observed_quantity_increment_check"
                        )
                    ).get("status")
                ),
                "price_check_status": _text(
                    _mapping(
                        broker_observed_preview.get("broker_observed_price_freshness_check")
                    ).get("status")
                ),
                "latest_price_value": _text(
                    broker_observed_preview.get("latest_price_value")
                ),
                "latest_price_source": _text(
                    broker_observed_preview.get("latest_price_source")
                ),
                "latest_price_freshness_status": _text(
                    broker_observed_preview.get("latest_price_freshness_status")
                ),
                "price_evidence_status": _text(
                    broker_observed_preview.get("price_evidence_status")
                ),
                "price_evidence_blocker": _text(
                    broker_observed_preview.get("price_evidence_blocker")
                ),
            }
        )
    events.append(
        {
            "event_type": "demo_run_completed",
            "run_id": run_id,
            "cycle_index": cycle_index,
            "cycle_key": cycle_key,
            "timestamp": as_of_value.isoformat(),
            "mode": run_mode,
            "scenario": scenario_value,
            "planned_action": plan_material.planned_action,
            "decision": decision,
            "final_blocker_status": final_blocker,
            "simulation_mutation_occurred": simulation_mutation_occurred,
            "paper_readiness_decision": paper_readiness_packet["readiness_decision"],
            "broker_observed_readiness_decision": broker_observed_preview[
                "broker_observed_readiness_decision"
            ],
            "safety_labels": list(safety_labels),
        }
    )
    cycle_record = _cycle_record(
        cycle_index=cycle_index,
        cycle_key=cycle_key,
        run_id=run_id,
        as_of=as_of_value,
        scenario=scenario_value,
        plan_material=plan_material,
        decision=decision,
        final_blocker=final_blocker,
        simulation_mutation_occurred=simulation_mutation_occurred,
        portfolio_before=state_snapshot.portfolio,
        portfolio_after=sim_broker.portfolio,
        fill_ledger=sim_broker.fill_ledger,
        safety_labels=safety_labels,
    )
    cumulative_events = (
        (*state_snapshot.events, *events)
        if not state_snapshot.errors
        else tuple(events)
    )
    updated_state = _updated_simbroker_state(
        state_snapshot=state_snapshot,
        portfolio=sim_broker.portfolio,
        orders=sim_broker.action_ledger,
        fills=sim_broker.fill_ledger,
        cycle_record=cycle_record,
        events=cumulative_events,
        safety_labels=safety_labels,
    )
    state_artifact_paths = _state_artifact_paths(state_root_path)
    if write_artifacts and not state_snapshot.errors:
        state_artifact_paths = _write_simbroker_state_artifacts(
            state_root_path,
            updated_state,
        )
    next_operator_action = _next_action(decision, final_blocker)
    next_operator_action["paper_readiness_preview"] = {
        "selected_symbol": paper_readiness_packet["symbol"] or "none",
        "action": paper_readiness_packet["side"] or plan_material.planned_action,
        "readiness_decision": paper_readiness_packet["readiness_decision"],
        "readiness_basis": paper_readiness_packet["readiness_basis"],
        "blocker_code": paper_readiness_packet["blocker_code"] or "none",
        "paper_submit_authorized": False,
        "next_operator_action": paper_readiness_packet["next_operator_action"],
    }
    next_operator_action["broker_observed_readiness_preview"] = {
        "requested": broker_observed_readiness,
        "selected_symbol": broker_observed_preview["symbol"] or "none",
        "broker_observed_readiness_decision": broker_observed_preview[
            "broker_observed_readiness_decision"
        ],
        "blocker_code": broker_observed_preview["blocker_code"] or "none",
        "broker_read_authorized": broker_observed_preview["broker_read_authorized"],
        "broker_read_attempted": broker_observed_preview["broker_read_attempted"],
        "broker_read_occurred": broker_observed_preview["broker_read_occurred"],
        "broker_read_blocked": broker_observed_preview["broker_read_blocked"],
        "broker_read_adapter_unavailable": broker_observed_preview[
            "broker_read_adapter_unavailable"
        ],
        "broker_read_failed": broker_observed_preview["broker_read_failed"],
        "broker_state_observed": broker_observed_preview["broker_state_observed"],
        "network_used": broker_observed_preview["network_used"],
        "paper_submit_authorized": False,
        "blocker_codes": list(
            _string_sequence(broker_observed_preview.get("blocker_codes"))
        ),
        "orderability_check_status": _text(
            _mapping(broker_observed_preview.get("broker_observed_orderability_check")).get(
                "status"
            )
        ),
        "min_notional_check_status": _text(
            _mapping(broker_observed_preview.get("broker_observed_min_notional_check")).get(
                "status"
            )
        ),
        "min_order_size_check_status": _text(
            _mapping(
                broker_observed_preview.get("broker_observed_min_order_size_check")
            ).get("status")
        ),
        "quantity_increment_check_status": _text(
            _mapping(
                broker_observed_preview.get("broker_observed_quantity_increment_check")
            ).get("status")
        ),
        "price_check_status": _text(
            _mapping(broker_observed_preview.get("broker_observed_price_freshness_check")).get(
                "status"
            )
        ),
        "latest_price_value": _text(broker_observed_preview.get("latest_price_value")),
        "latest_price_source": _text(broker_observed_preview.get("latest_price_source")),
        "latest_price_freshness_status": _text(
            broker_observed_preview.get("latest_price_freshness_status")
        ),
        "price_evidence_status": _text(
            broker_observed_preview.get("price_evidence_status")
        ),
        "price_evidence_blocker": _text(
            broker_observed_preview.get("price_evidence_blocker")
        ),
        "next_operator_action": broker_observed_preview["next_operator_action"],
    }

    packet = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "tomorrow_crypto_trader_demo",
        "operator_command": COMMAND_NAME,
        "run_id": run_id,
        "as_of": as_of_value.isoformat(),
        "cycle_index": cycle_index,
        "cycle_key": cycle_key,
        "scenario": scenario_value,
        "output_root": str(root),
        "state_root": str(state_root_path),
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
            "broker_state_observed": broker_state_observed,
            "broker_state_mode": safety["broker_state_mode"],
            "fixture_readiness_basis": paper_readiness_packet["readiness_basis"],
            "fixture_readiness_decision": paper_readiness_packet["readiness_decision"],
            "broker_observed_readiness_requested": broker_observed_readiness,
            "broker_observed_readiness_decision": broker_observed_preview[
                "broker_observed_readiness_decision"
            ],
            "broker_observed_blocker": broker_observed_preview["blocker_code"],
            "network_used": run_network_used,
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
            else plan_material.planned_action
        ),
        "planned_action": plan_material.planned_action,
        "decision": decision,
        "risk_decision": _risk_decision(plan_material.risk),
        "execution_intent": _execution_intent_record(plan_material),
        "execution_plan": _execution_plan_record(plan_material.execution_plan),
        "planning_policy_decision": _planning_policy_record(plan_material.planning_policy),
        "broker_mode_adapter": {
            "adapter": "simulation_broker",
            "accepted_execution_plan_required": True,
            "broker_sdk_imported": False,
            "network_used": run_network_used,
        },
        "sim_broker_action_ledger": list(sim_broker.action_ledger),
        "fill_ledger": list(sim_broker.fill_ledger),
        "cumulative_fill_ledger": list(_mapping_sequence(updated_state.get("fills"))),
        "portfolio_snapshot": _portfolio_snapshot(sim_broker.portfolio),
        "state_reconciliation": state_reconciliation,
        "cycle_record": cycle_record,
        "broker_result": broker_result,
        "paper_readiness_packet": paper_readiness_packet,
        "broker_observed_readiness_requested": broker_observed_readiness,
        "broker_observed_readiness_preview": broker_observed_preview,
        "broker_observed_telemetry": broker_observed_telemetry,
        **broker_observed_telemetry,
        "final_blocker_status": final_blocker,
        "blockers": list(_dedupe((*plan_material.blockers, _text(broker_result.get("blocker"))))),
        "next_operator_action": next_operator_action,
        "safety": safety,
        "safety_labels": list(safety_labels),
        "labels": list(safety_labels),
        "profit_claim": "none",
        "state_artifact_paths": state_artifact_paths,
        "events": list(cumulative_events),
    }
    if broker_observed_readiness:
        packet["broker_observed_readiness_packet"] = broker_observed_preview
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
        "run_summary": root / "run_summary.json",
        "paper_readiness_packet": root / "paper_readiness_packet.json",
        "paper_readiness_packet_markdown": root / "paper_readiness_packet.md",
    }
    broker_observed_packet = _mapping(packet.get("broker_observed_readiness_packet"))
    if broker_observed_packet:
        paths["broker_observed_readiness_packet"] = (
            root / "broker_observed_readiness_packet.json"
        )
        paths["broker_observed_readiness_packet_markdown"] = (
            root / "broker_observed_readiness_packet.md"
        )
    artifact_paths = {key: str(path) for key, path in paths.items()}
    packet_payload = {**dict(packet), "artifact_paths": artifact_paths}
    run_summary = _run_summary_payload(packet_payload)
    packet_payload["run_summary"] = run_summary
    broker_observed_telemetry = _mapping(packet_payload.get("broker_observed_telemetry"))
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
        "state_artifacts": {},
        "generated_under_runs": _generated_under_runs(root),
        "readiness_bases": {
            "fixture": {
                "decision": _text(
                    _mapping(packet.get("paper_readiness_packet")).get("readiness_decision")
                ),
                "blocker_code": _text(
                    _mapping(packet.get("paper_readiness_packet")).get("blocker_code")
                ),
                "artifact": "paper_readiness_packet",
            },
            "broker_observed": {
                "requested": packet.get("broker_observed_readiness_requested") is True,
                "decision": _text(
                    _mapping(packet.get("broker_observed_readiness_preview")).get(
                        "broker_observed_readiness_decision"
                    )
                ),
                "blocker_code": _text(
                    _mapping(packet.get("broker_observed_readiness_preview")).get(
                        "blocker_code"
                    )
                ),
                "broker_read_authorized": _mapping(
                    packet.get("broker_observed_readiness_preview")
                ).get("broker_read_authorized")
                is True,
                "broker_read_occurred": _mapping(
                    packet.get("broker_observed_readiness_preview")
                ).get("broker_read_occurred")
                is True,
                "broker_read_attempted": _mapping(
                    packet.get("broker_observed_readiness_preview")
                ).get("broker_read_attempted")
                is True,
                "broker_read_blocked": _mapping(
                    packet.get("broker_observed_readiness_preview")
                ).get("broker_read_blocked")
                is True,
                "broker_read_adapter_unavailable": _mapping(
                    packet.get("broker_observed_readiness_preview")
                ).get("broker_read_adapter_unavailable")
                is True,
                "broker_read_failed": _mapping(
                    packet.get("broker_observed_readiness_preview")
                ).get("broker_read_failed")
                is True,
                "broker_state_observed": _mapping(
                    packet.get("broker_observed_readiness_preview")
                ).get("broker_state_observed")
                is True,
                "network_used": _mapping(packet.get("safety")).get("network_used") is True,
                "live_endpoint_touched": _mapping(
                    packet.get("broker_observed_readiness_preview")
                ).get("live_endpoint_touched")
                is True,
                "credential_values_exposed": _mapping(packet.get("safety")).get(
                    "credential_values_exposed"
                )
                is True,
                "paper_submit_occurred": _mapping(packet.get("safety")).get(
                    "paper_submit_occurred"
                )
                is True,
                "broker_mutation_occurred": _mapping(packet.get("safety")).get(
                    "broker_mutation_occurred"
                )
                is True,
                "artifact": (
                    "broker_observed_readiness_packet"
                    if broker_observed_packet
                    else ""
                ),
            },
        },
        "broker_observed_telemetry": dict(broker_observed_telemetry),
        "run_summary": {
            "artifact": "run_summary",
            "console_fields": dict(_mapping(run_summary.get("console_fields"))),
        },
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
    _write_json(paths["run_summary"], run_summary)
    _write_json(
        paths["paper_readiness_packet"],
        _mapping(packet.get("paper_readiness_packet")),
    )
    paths["paper_readiness_packet_markdown"].write_text(
        render_paper_readiness_packet(_mapping(packet.get("paper_readiness_packet"))) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if broker_observed_packet:
        _write_json(paths["broker_observed_readiness_packet"], broker_observed_packet)
        paths["broker_observed_readiness_packet_markdown"].write_text(
            render_broker_observed_readiness_packet(broker_observed_packet) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    else:
        for stale_path in (
            root / "broker_observed_readiness_packet.json",
            root / "broker_observed_readiness_packet.md",
        ):
            try:
                stale_path.unlink()
            except FileNotFoundError:
                pass
    manifest["required_artifacts"] = {
        name: {
            "path": str(path),
            "exists": path.is_file(),
            "sha256": _file_sha256(path) if path.is_file() else "",
        }
        for name, path in sorted(paths.items())
        if name != "manifest"
    }
    manifest["state_artifacts"] = {
        name: {
            "path": str(path),
            "exists": path.is_file(),
            "sha256": _file_sha256(path) if path.is_file() else "",
        }
        for name, path in sorted(
            (name, Path(path_text))
            for name, path_text in _mapping(packet.get("state_artifact_paths")).items()
            if _text(path_text)
        )
    }
    _write_json(paths["manifest"], manifest)
    return artifact_paths


def render_operating_brief(packet: Mapping[str, object]) -> str:
    selected = _mapping(packet.get("selected_candidate"))
    selected_symbol = _text(selected.get("symbol")) or "none"
    paper = _mapping(packet.get("paper_readiness_packet"))
    broker_observed = _mapping(packet.get("broker_observed_readiness_preview"))
    paper_symbol = _text(paper.get("symbol")) or selected_symbol
    paper_action = _text(paper.get("side") or packet.get("planned_action")) or "none"
    paper_blocker = _text(paper.get("blocker_code")) or "none"
    broker_observed_blocker = _text(broker_observed.get("blocker_code")) or "none"
    fills = _mapping_sequence(packet.get("fill_ledger"))
    positions = _mapping_sequence(_mapping(packet.get("portfolio_snapshot")).get("positions"))
    safety_labels = _string_sequence(packet.get("safety_labels"))
    lines = [
        "# v6.1 Crypto SimBroker Multi-Cycle Operating Loop",
        "",
        f"- run_id: `{_text(packet.get('run_id'))}`",
        f"- cycle_index: `{_text(packet.get('cycle_index'))}`",
        f"- cycle_key: `{_text(packet.get('cycle_key'))}`",
        f"- as_of: `{_text(packet.get('as_of'))}`",
        f"- scenario: `{_text(packet.get('scenario'))}`",
        f"- mode: `{_text(packet.get('mode'))}`",
        f"- broker_mode: `{_text(packet.get('broker_mode'))}`",
        f"- state_root: `{_text(packet.get('state_root'))}`",
        f"- planned_action: `{_text(packet.get('planned_action'))}`",
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
            "## Paper readiness preview",
            f"- selected_symbol: `{paper_symbol}`",
            f"- action: `{paper_action}`",
            f"- readiness_basis: `{_text(paper.get('readiness_basis'))}`",
            f"- readiness_decision: `{_text(paper.get('readiness_decision'))}`",
            f"- blocker_status: `{paper_blocker}`",
            f"- paper_submit_authorized: `{_bool_text(paper.get('paper_submit_authorized'))}`",
            f"- next_operator_action: `{_text(paper.get('next_operator_action'))}`",
            "",
            "## Broker-observed readiness preview",
            f"- requested: `{_bool_text(broker_observed.get('broker_read_requested'))}`",
            f"- selected_symbol: `{_text(broker_observed.get('symbol')) or 'none'}`",
            f"- broker_observed_readiness_decision: `{_text(broker_observed.get('broker_observed_readiness_decision'))}`",
            f"- blocker_status: `{broker_observed_blocker}`",
            f"- broker_read_authorized: `{_bool_text(broker_observed.get('broker_read_authorized'))}`",
            f"- broker_read_attempted: `{_bool_text(broker_observed.get('broker_read_attempted'))}`",
            f"- broker_read_occurred: `{_bool_text(broker_observed.get('broker_read_occurred'))}`",
            f"- broker_read_blocked: `{_bool_text(broker_observed.get('broker_read_blocked'))}`",
            f"- broker_state_observed: `{_bool_text(broker_observed.get('broker_state_observed'))}`",
            f"- network_used: `{_bool_text(broker_observed.get('network_used'))}`",
            f"- paper_submit_authorized: `{_bool_text(broker_observed.get('paper_submit_authorized'))}`",
            f"- min_notional_check_status: `{_text(_mapping(broker_observed.get('broker_observed_min_notional_check')).get('status')) or 'none'}`",
            f"- min_order_size_check_status: `{_text(_mapping(broker_observed.get('broker_observed_min_order_size_check')).get('status')) or 'none'}`",
            f"- quantity_increment_check_status: `{_text(_mapping(broker_observed.get('broker_observed_quantity_increment_check')).get('status')) or 'none'}`",
            f"- price_check_status: `{_text(_mapping(broker_observed.get('broker_observed_price_freshness_check')).get('status')) or 'none'}`",
            f"- latest_price_value: `{_text(broker_observed.get('latest_price_value')) or 'none'}`",
            f"- latest_price_source: `{_text(broker_observed.get('latest_price_source')) or 'none'}`",
            f"- latest_price_freshness_status: `{_text(broker_observed.get('latest_price_freshness_status')) or 'none'}`",
            f"- price_evidence_status: `{_text(broker_observed.get('price_evidence_status')) or 'none'}`",
            f"- price_evidence_blocker: `{_text(broker_observed.get('price_evidence_blocker')) or 'none'}`",
            f"- next_operator_action: `{_text(broker_observed.get('next_operator_action'))}`",
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


def render_paper_readiness_packet(packet: Mapping[str, object]) -> str:
    return "\n".join(
        [
            "# Paper Readiness Packet",
            "",
            f"- run_id: `{_text(packet.get('run_id'))}`",
            f"- cycle_index: `{_text(packet.get('cycle_index'))}`",
            f"- symbol: `{_text(packet.get('symbol')) or 'none'}`",
            f"- side: `{_text(packet.get('side')) or 'none'}`",
            f"- readiness_decision: `{_text(packet.get('readiness_decision'))}`",
            f"- readiness_basis: `{_text(packet.get('readiness_basis'))}`",
            f"- blocker_code: `{_text(packet.get('blocker_code')) or 'none'}`",
            f"- intended_notional: `{_text(packet.get('intended_notional'))}`",
            f"- estimated_quantity: `{_text(packet.get('estimated_quantity'))}`",
            f"- paper_submit_authorized: `{_bool_text(packet.get('paper_submit_authorized'))}`",
            f"- paper_submit_occurred: `{_bool_text(packet.get('paper_submit_occurred'))}`",
            f"- broker_read_occurred: `{_bool_text(packet.get('broker_read_occurred'))}`",
            f"- broker_mutation_occurred: `{_bool_text(packet.get('broker_mutation_occurred'))}`",
            f"- network_used: `{_bool_text(packet.get('network_used'))}`",
            "",
            "## Bases",
            f"- latest_price_basis: `{_text(_mapping(packet.get('latest_price_basis')).get('basis'))}`",
            f"- orderability_basis: `{_text(_mapping(packet.get('orderability_basis')).get('basis'))}`",
            f"- min_notional_basis: `{_text(_mapping(packet.get('min_notional_basis')).get('basis'))}`",
            f"- quantity_increment_basis: `{_text(_mapping(packet.get('quantity_increment_basis')).get('basis'))}`",
            "",
            "## Safety Labels",
            *[f"- `{label}`" for label in _string_sequence(packet.get("safety_labels"))],
        ]
    )


def _markdown_table_value(value: object) -> str:
    text = _text(value)
    return text if text else "none"


def _broker_observed_evidence_table_rows(
    packet: Mapping[str, object],
) -> list[tuple[str, str, str, str, str]]:
    asset_summary = _mapping(
        packet.get("observed_crypto_assets_or_orderability_summary")
    )
    field_sources = _mapping(
        packet.get("broker_orderability_field_sources")
        or asset_summary.get("field_sources")
    )
    normalized = _mapping(
        packet.get("broker_orderability_normalized")
        or asset_summary.get("normalized_orderability_fields")
    )
    orderability_check = _mapping(packet.get("broker_observed_orderability_check"))
    min_notional_check = _mapping(packet.get("broker_observed_min_notional_check"))
    min_order_size_check = _mapping(packet.get("broker_observed_min_order_size_check"))
    quantity_increment_check = _mapping(
        packet.get("broker_observed_quantity_increment_check")
    )
    price_check = _mapping(packet.get("broker_observed_price_freshness_check"))
    if not price_check:
        price_check = _mapping(packet.get("observed_latest_price_basis"))
    selected_source = "deterministic_fixture" if _text(packet.get("symbol")) else "unavailable"
    not_applicable = "not_applicable"
    return [
        (
            "selected_symbol",
            _markdown_table_value(packet.get("symbol")),
            selected_source,
            not_applicable,
            "present" if selected_source != "unavailable" else "missing",
        ),
        (
            "intended_side",
            _markdown_table_value(packet.get("intended_side") or packet.get("side")),
            selected_source,
            not_applicable,
            "present" if _text(packet.get("intended_side") or packet.get("side")) else "missing",
        ),
        (
            "intended_notional",
            _markdown_table_value(packet.get("intended_notional")),
            selected_source,
            not_applicable,
            "present" if _text(packet.get("intended_notional")) else "missing",
        ),
        (
            "estimated_quantity",
            _markdown_table_value(packet.get("estimated_quantity")),
            selected_source,
            not_applicable,
            "present" if _text(packet.get("estimated_quantity")) else "missing",
        ),
        (
            "latest_price_value",
            _markdown_table_value(price_check.get("latest_price_value")),
            _markdown_table_value(price_check.get("latest_price_source")),
            _markdown_table_value(price_check.get("latest_price_freshness_status")),
            _markdown_table_value(price_check.get("price_evidence_status")),
        ),
        (
            "latest_price_basis",
            _markdown_table_value(price_check.get("latest_price_basis")),
            _markdown_table_value(price_check.get("latest_price_source")),
            _markdown_table_value(price_check.get("latest_price_freshness_status")),
            _markdown_table_value(price_check.get("price_evidence_blocker")),
        ),
        (
            "price_used_for_quantity",
            _markdown_table_value(price_check.get("price_used_for_quantity")),
            _markdown_table_value(price_check.get("latest_price_source_acceptability")),
            _markdown_table_value(price_check.get("latest_price_freshness_status")),
            _markdown_table_value(price_check.get("price_evidence_status")),
        ),
        (
            "price_used_for_min_notional_derivation",
            _markdown_table_value(price_check.get("price_used_for_min_notional_derivation")),
            _markdown_table_value(price_check.get("latest_price_source_acceptability")),
            _markdown_table_value(price_check.get("latest_price_freshness_status")),
            _markdown_table_value(price_check.get("price_evidence_status")),
        ),
        (
            "orderability",
            _markdown_table_value(asset_summary.get("basis")),
            _markdown_table_value(orderability_check.get("source")),
            not_applicable,
            _markdown_table_value(orderability_check.get("status")),
        ),
        (
            "asset_status",
            _markdown_table_value(normalized.get("status") or asset_summary.get("asset_status")),
            _markdown_table_value(field_sources.get("status")),
            not_applicable,
            "observed" if field_sources.get("status") == "broker_observed" else "missing",
        ),
        (
            "tradable",
            _markdown_table_value(normalized.get("tradable")),
            _markdown_table_value(field_sources.get("tradable")),
            not_applicable,
            "observed" if field_sources.get("tradable") == "broker_observed" else "missing",
        ),
        (
            "fractional",
            _markdown_table_value(normalized.get("fractional")),
            _markdown_table_value(field_sources.get("fractional")),
            not_applicable,
            "observed" if field_sources.get("fractional") == "broker_observed" else "missing",
        ),
        (
            "min_notional",
            _markdown_table_value(min_notional_check.get("min_notional")),
            _markdown_table_value(min_notional_check.get("source")),
            not_applicable,
            _markdown_table_value(min_notional_check.get("status")),
        ),
        (
            "direct_min_notional_available",
            _markdown_table_value(packet.get("direct_min_notional_available")),
            _markdown_table_value(packet.get("direct_min_notional_source")),
            not_applicable,
            "observed" if packet.get("direct_min_notional_available") is True else "missing",
        ),
        (
            "derived_min_notional",
            _markdown_table_value(packet.get("derived_min_notional_value")),
            _markdown_table_value(packet.get("derived_min_notional_sources")),
            not_applicable,
            _markdown_table_value(packet.get("derived_min_notional_check_status")),
        ),
        (
            "derived_min_notional_formula",
            _markdown_table_value(packet.get("derived_min_notional_formula")),
            "readiness_packet",
            not_applicable,
            "present" if _text(packet.get("derived_min_notional_formula")) else "missing",
        ),
        (
            "min_notional_equivalence_basis",
            _markdown_table_value(packet.get("min_notional_equivalence_basis")),
            "readiness_packet",
            not_applicable,
            _markdown_table_value(packet.get("derived_min_notional_check_status")),
        ),
        (
            "price_source_for_derivation",
            _markdown_table_value(packet.get("price_source_for_derivation")),
            _markdown_table_value(packet.get("price_source_acceptability")),
            _markdown_table_value(price_check.get("latest_price_freshness_status")),
            _markdown_table_value(price_check.get("status")),
        ),
        (
            "final_feasibility_basis",
            _markdown_table_value(packet.get("final_feasibility_basis")),
            "readiness_packet",
            not_applicable,
            _markdown_table_value(packet.get("broker_observed_readiness_decision")),
        ),
        (
            "min_order_size",
            _markdown_table_value(min_order_size_check.get("min_order_size")),
            _markdown_table_value(min_order_size_check.get("source")),
            not_applicable,
            _markdown_table_value(min_order_size_check.get("status")),
        ),
        (
            "quantity_increment",
            _markdown_table_value(quantity_increment_check.get("quantity_increment")),
            _markdown_table_value(quantity_increment_check.get("source")),
            not_applicable,
            _markdown_table_value(quantity_increment_check.get("status")),
        ),
        (
            "price_increment",
            _markdown_table_value(normalized.get("price_increment")),
            _markdown_table_value(field_sources.get("price_increment")),
            not_applicable,
            "observed"
            if field_sources.get("price_increment") == "broker_observed"
            else "missing",
        ),
    ]


def render_broker_observed_readiness_packet(packet: Mapping[str, object]) -> str:
    evidence_rows = _broker_observed_evidence_table_rows(packet)
    return "\n".join(
        [
            "# Broker-Observed Readiness Packet",
            "",
            f"- run_id: `{_text(packet.get('run_id'))}`",
            f"- cycle_index: `{_text(packet.get('cycle_index'))}`",
            f"- symbol: `{_text(packet.get('symbol')) or 'none'}`",
            f"- side: `{_text(packet.get('intended_side') or packet.get('side')) or 'none'}`",
            f"- broker_observed_readiness_decision: `{_text(packet.get('broker_observed_readiness_decision'))}`",
            f"- blocker_code: `{_text(packet.get('blocker_code')) or 'none'}`",
            f"- blocker_codes: `{','.join(_string_sequence(packet.get('blocker_codes'))) or 'none'}`",
            f"- intended_notional: `{_text(packet.get('intended_notional')) or 'none'}`",
            f"- estimated_quantity: `{_text(packet.get('estimated_quantity')) or 'none'}`",
            f"- direct_min_notional_available: `{_bool_text(packet.get('direct_min_notional_available'))}`",
            f"- derived_min_notional_available: `{_bool_text(packet.get('derived_min_notional_available'))}`",
            f"- derived_min_notional_value: `{_text(packet.get('derived_min_notional_value')) or 'none'}`",
            f"- latest_price_value: `{_text(packet.get('latest_price_value')) or 'none'}`",
            f"- latest_price_source: `{_text(packet.get('latest_price_source')) or 'none'}`",
            f"- latest_price_freshness_status: `{_text(packet.get('latest_price_freshness_status')) or 'none'}`",
            f"- price_evidence_status: `{_text(packet.get('price_evidence_status')) or 'none'}`",
            f"- price_evidence_blocker: `{_text(packet.get('price_evidence_blocker')) or 'none'}`",
            f"- price_source_for_derivation: `{_text(packet.get('price_source_for_derivation')) or 'none'}`",
            f"- price_source_acceptability: `{_text(packet.get('price_source_acceptability')) or 'none'}`",
            f"- final_feasibility_basis: `{_text(packet.get('final_feasibility_basis')) or 'none'}`",
            f"- broker_read_authorized: `{_bool_text(packet.get('broker_read_authorized'))}`",
            f"- broker_read_attempted: `{_bool_text(packet.get('broker_read_attempted'))}`",
            f"- broker_read_occurred: `{_bool_text(packet.get('broker_read_occurred'))}`",
            f"- broker_read_blocked: `{_bool_text(packet.get('broker_read_blocked'))}`",
            f"- broker_read_adapter_unavailable: `{_bool_text(packet.get('broker_read_adapter_unavailable'))}`",
            f"- broker_read_failed: `{_bool_text(packet.get('broker_read_failed'))}`",
            f"- broker_state_observed: `{_bool_text(packet.get('broker_state_observed'))}`",
            f"- network_used: `{_bool_text(packet.get('network_used'))}`",
            f"- broker_endpoint_type: `{_text(packet.get('broker_endpoint_type'))}`",
            f"- live_endpoint_touched: `{_bool_text(packet.get('live_endpoint_touched'))}`",
            f"- paper_account_status: `{_text(packet.get('paper_account_status')) or 'not_observed'}`",
            f"- paper_submit_authorized: `{_bool_text(packet.get('paper_submit_authorized'))}`",
            f"- broker_mutation_occurred: `{_bool_text(packet.get('broker_mutation_occurred'))}`",
            f"- next_operator_action: `{_text(packet.get('next_operator_action'))}`",
            "",
            "## Observed Summaries",
            f"- positions: `{_text(_mapping(packet.get('observed_positions_summary')).get('status'))}`",
            f"- open_orders: `{_text(_mapping(packet.get('observed_open_orders_summary')).get('status'))}`",
            f"- crypto_assets: `{_text(_mapping(packet.get('observed_crypto_assets_or_orderability_summary')).get('status'))}`",
            f"- min_notional_or_increment: `{_text(_mapping(packet.get('observed_min_notional_or_increment_basis')).get('status'))}`",
            "",
            "## Min-Notional / Orderability Evidence",
            "",
            "field | value | source | freshness | status",
            "--- | --- | --- | --- | ---",
            *[
                f"{field} | `{value}` | `{source}` | `{freshness}` | `{status}`"
                for field, value, source, freshness, status in evidence_rows
            ],
            "",
            "## Safety Labels",
            *[f"- `{label}`" for label in _string_sequence(packet.get("safety_labels"))],
        ]
    )


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
    run_summary = _read_json_or_error(artifact_paths["run_summary.json"], errors)
    paper_readiness = _read_json_or_error(
        artifact_paths["paper_readiness_packet.json"],
        errors,
    )
    broker_observed_path = root / "broker_observed_readiness_packet.json"
    broker_observed_md_path = root / "broker_observed_readiness_packet.md"
    broker_observed_readiness: Mapping[str, object] = {}
    events = _read_jsonl_or_error(artifact_paths["events.jsonl"], errors)
    state_paths: dict[str, Path] = {}
    state_payload: Mapping[str, object] = {}
    state_events: tuple[Mapping[str, object], ...] = ()
    brief_text = ""
    paper_readiness_text = ""
    try:
        brief_text = artifact_paths["operating_brief.md"].read_text(encoding="utf-8")
    except OSError:
        if artifact_paths["operating_brief.md"].is_file():
            errors.append("operating_brief_unreadable")
    try:
        paper_readiness_text = artifact_paths["paper_readiness_packet.md"].read_text(
            encoding="utf-8"
        )
    except OSError:
        if artifact_paths["paper_readiness_packet.md"].is_file():
            errors.append("paper_readiness_packet_md_unreadable")

    if record:
        _validate_record_contract(record, events, errors)
        if paper_readiness:
            _validate_paper_readiness_packet(
                packet=paper_readiness,
                record=record,
                markdown=paper_readiness_text,
                errors=errors,
            )
        elif isinstance(record.get("selected_candidate"), Mapping) or int(
            _mapping(record.get("execution_plan")).get("intent_count", 0) or 0
        ) > 0:
            errors.append("selected_candidate_or_execution_plan_missing_paper_readiness_packet")
        if _text(record.get("mode")) == "SimBroker":
            if record.get("broker_observed_readiness_requested") is True:
                if not broker_observed_path.is_file():
                    errors.append("missing_artifact:broker_observed_readiness_packet.json")
                else:
                    broker_observed_readiness = _read_json_or_error(
                        broker_observed_path,
                        errors,
                    )
                if not broker_observed_md_path.is_file():
                    errors.append("missing_artifact:broker_observed_readiness_packet.md")
            state_paths = _state_paths_for_record(record, root)
            for name, path in state_paths.items():
                if not path.is_file():
                    errors.append(f"missing_state_artifact:{name}")
            state_payload = _read_json_or_error(
                state_paths.get("simbroker_state.json", root / "__missing_state__.json"),
                errors,
            )
            positions_payload = _read_json_or_error(
                state_paths.get("positions.json", root / "__missing_positions__.json"),
                errors,
            )
            fills = _read_jsonl_or_error(
                state_paths.get("fills.jsonl", root / "__missing_fills__.jsonl"),
                errors,
            )
            cycle_history = _read_jsonl_or_error(
                state_paths.get("cycle_history.jsonl", root / "__missing_cycle_history__.jsonl"),
                errors,
            )
            state_events = _read_jsonl_or_error(
                state_paths.get("events.jsonl", root / "__missing_state_events__.jsonl"),
                errors,
            )
            if state_payload:
                _validate_state_artifacts(
                    record=record,
                    state_payload=state_payload,
                    positions_payload=positions_payload,
                    fills=fills,
                    cycle_history=cycle_history,
                    state_events=state_events,
                    errors=errors,
                )
        if broker_observed_readiness:
            broker_observed_text = ""
            try:
                broker_observed_text = broker_observed_md_path.read_text(encoding="utf-8")
            except OSError:
                if broker_observed_md_path.is_file():
                    errors.append("broker_observed_readiness_packet_md_unreadable")
            _validate_broker_observed_readiness_packet(
                packet=broker_observed_readiness,
                record=record,
                markdown=broker_observed_text,
                errors=errors,
            )
        if run_summary:
            _validate_run_summary(
                run_summary=run_summary,
                record=record,
                broker_observed_readiness=broker_observed_readiness,
                errors=errors,
            )
    if manifest:
        _validate_labels("manifest", manifest, errors)
        _validate_manifest_references_paper_readiness(manifest, errors)
        _validate_manifest_readiness_bases(manifest, record, errors)
        _validate_manifest_telemetry(manifest, record, broker_observed_readiness, errors)
    if next_action:
        _validate_labels("next_operator_action", next_action, errors)
    if brief_text:
        for label in REQUIRED_SAFETY_LABELS:
            if label not in brief_text:
                errors.append(f"operating_brief_missing_label:{label}")
        if "Paper readiness preview" not in brief_text:
            errors.append("operating_brief_missing_paper_readiness_preview")
    if paper_readiness_text and "Paper Readiness Packet" not in paper_readiness_text:
        errors.append("paper_readiness_packet_md_missing_title")
    if _git_ls_files_runs():
        errors.append("generated_runs_artifacts_tracked")
    _validate_forbidden_sentinels(root, errors)

    validation_fields = _validation_summary_fields(
        record=record,
        broker_observed_readiness=broker_observed_readiness,
        run_summary=run_summary,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "tomorrow_crypto_trader_demo_validation",
        "output_root": str(root),
        "validation_status": "failed" if errors else "passed",
        "errors": errors,
        "required_artifacts": {name: str(path) for name, path in artifact_paths.items()},
        "state_artifacts": {name: str(path) for name, path in state_paths.items()},
        **validation_fields,
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
        broker_observed_requested = record.get("broker_observed_readiness_requested") is True
        labels = set(_string_sequence(record.get("safety_labels") or record.get("labels")))
        expected_labels = (
            _simbroker_labels(
                simulation_mutation_occurred=safety.get("simulation_mutation_occurred") is True,
                broker_read_occurred=safety.get("broker_read_occurred") is True,
                broker_state_observed=safety.get("broker_state_observed") is True,
                network_used=safety.get("network_used") is True,
            )
            if broker_observed_requested
            else SIMBROKER_SAFETY_LABELS
        )
        for label in expected_labels:
            if label not in labels:
                errors.append(f"operating_record_missing_label:{label}")
        expected_mutation_label = (
            f"simulation_mutation_occurred={_bool_text(safety.get('simulation_mutation_occurred'))}"
        )
        if expected_mutation_label not in labels:
            errors.append(f"operating_record_missing_label:{expected_mutation_label}")
        expected_false = (
            "paper_submit_authorized",
            "broker_mutation_authorized",
            "paper_submit_occurred",
            "broker_mutation_occurred",
            "credential_values_exposed",
            "live_authorized",
        )
        for field in expected_false:
            if safety.get(field) is not False:
                errors.append(f"simbroker_flag_not_false:{field}")
        if not broker_observed_requested:
            for field in ("broker_read_occurred", "broker_state_observed", "network_used"):
                if safety.get(field) is not False:
                    errors.append(f"simbroker_flag_not_false:{field}")
        if safety.get("broker_read_occurred") is True and not broker_observed_requested:
            errors.append("broker_read_occurred_in_default_simbroker_mode")
        if safety.get("simulation_mutation_authorized") is not True:
            errors.append("simbroker_simulation_mutation_not_authorized")
        if broker_mode != "simulation_broker":
            errors.append("simbroker_broker_mode_mismatch")
        allowed_state_modes = {"offline_simulation"}
        if broker_observed_requested:
            allowed_state_modes.add("alpaca_paper_read_only_observed")
        if safety.get("broker_state_mode") not in allowed_state_modes:
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
        telemetry = _mapping(record.get("broker_observed_telemetry"))
        if telemetry:
            for field in BROKER_OBSERVED_CONSISTENCY_FIELDS:
                if field not in telemetry:
                    errors.append(f"operating_record_broker_observed_telemetry_missing:{field}")
                elif record.get(field) != telemetry.get(field):
                    errors.append(f"operating_record_top_level_telemetry_mismatch:{field}")
            if telemetry.get("network_used") != safety.get("network_used"):
                errors.append("operating_record_safety_network_flag_mismatch")
            if telemetry.get("broker_read_occurred") != safety.get("broker_read_occurred"):
                errors.append("operating_record_safety_broker_read_flag_mismatch")
            if telemetry.get("broker_state_observed") != safety.get("broker_state_observed"):
                errors.append("operating_record_safety_broker_state_flag_mismatch")
            if telemetry.get("network_used") != provenance.get("network_used"):
                errors.append("operating_record_provenance_network_flag_mismatch")
            if telemetry.get("broker_state_observed") != provenance.get("broker_state_observed"):
                errors.append("operating_record_provenance_broker_state_flag_mismatch")
            adapter = _mapping(record.get("broker_mode_adapter"))
            if telemetry.get("network_used") != adapter.get("network_used"):
                errors.append("operating_record_adapter_network_flag_mismatch")
            decision = _text(telemetry.get("broker_observed_readiness_decision"))
            blocker = _text(telemetry.get("broker_observed_blocker"))
            if broker_observed_requested and not decision:
                errors.append("broker_observed_readiness_decision_missing")
            if (
                telemetry.get("broker_read_authorized") is True
                and telemetry.get("broker_read_occurred") is False
                and not blocker
            ):
                errors.append("broker_read_authorized_without_read_or_blocker")
            if (
                telemetry.get("network_used") is True
                and telemetry.get("broker_read_occurred") is False
                and not blocker
            ):
                errors.append("inconsistent_network_without_broker_read")
        else:
            errors.append("operating_record_broker_observed_telemetry_missing")
    if mode == "AlpacaPaper":
        if broker_mode != "alpaca_paper":
            errors.append("alpaca_paper_broker_mode_mismatch")
        if safety.get("live_endpoint_touched") is not False:
            errors.append("alpaca_paper_live_endpoint_touched")

    selected = record.get("selected_candidate")
    if isinstance(selected, Mapping) and _text(record.get("planned_action")) == "simulated_buy":
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


def _validate_run_summary(
    *,
    run_summary: Mapping[str, object],
    record: Mapping[str, object],
    broker_observed_readiness: Mapping[str, object],
    errors: list[str],
) -> None:
    _validate_labels("run_summary", run_summary, errors)
    if run_summary.get("record_type") != "tomorrow_crypto_trader_demo_run_summary":
        errors.append("run_summary_record_type_mismatch")
    if _text(run_summary.get("run_id")) != _text(record.get("run_id")):
        errors.append("run_summary_run_id_mismatch")
    fields = _mapping(run_summary.get("console_fields"))
    if not fields:
        errors.append("run_summary_console_fields_missing")
        return
    expected_lines = _console_summary_lines(fields)
    if list(_string_sequence(run_summary.get("console_lines"))) != expected_lines:
        errors.append("run_summary_console_lines_mismatch")

    record_telemetry = _mapping(record.get("broker_observed_telemetry"))
    for field in BROKER_OBSERVED_CONSISTENCY_FIELDS:
        if field not in fields:
            errors.append(f"run_summary_console_field_missing:{field}")
            continue
        if fields.get(field) != record_telemetry.get(field):
            if field == "network_used":
                errors.append("inconsistent_console_artifact_network_flag")
            else:
                errors.append(f"inconsistent_console_artifact_field:{field}")

    if broker_observed_readiness:
        _validate_broker_observed_artifact_consistency(
            record=record,
            broker_observed_readiness=broker_observed_readiness,
            errors=errors,
        )


def _validate_paper_readiness_packet(
    *,
    packet: Mapping[str, object],
    record: Mapping[str, object],
    markdown: str,
    errors: list[str],
) -> None:
    _validate_labels("paper_readiness_packet", packet, errors)
    if packet.get("record_type") != "paper_readiness_packet":
        errors.append("paper_readiness_packet_record_type_mismatch")
    if _text(packet.get("run_id")) != _text(record.get("run_id")):
        errors.append("paper_readiness_packet_run_id_mismatch")
    decision = _text(packet.get("readiness_decision") or packet.get("final_readiness_decision"))
    if not decision:
        errors.append("paper_readiness_decision_missing")
    elif decision not in PAPER_READINESS_DECISIONS:
        errors.append(f"paper_readiness_decision_invalid:{decision}")
    if decision.startswith("broker_observed_"):
        errors.append("fixture_readiness_labeled_as_broker_observed")
    if _text(packet.get("readiness_basis")) != "fixture":
        errors.append("paper_readiness_basis_not_fixture")
    blocker_code = _text(packet.get("blocker_code"))
    if blocker_code and blocker_code not in PAPER_READINESS_BLOCKERS:
        errors.append(f"paper_readiness_blocker_invalid:{blocker_code}")
    if decision == "fixture_ready_preview" and blocker_code:
        errors.append("fixture_ready_preview_has_blocker")
    if decision == "fixture_blocked_preview" and not blocker_code:
        errors.append("fixture_blocked_preview_missing_blocker")

    for field in (
        "paper_submit_authorized",
        "paper_submit_occurred",
        "broker_mutation_authorized",
        "broker_mutation_occurred",
        "broker_read_occurred",
        "broker_state_observed",
        "network_used",
        "credential_values_exposed",
    ):
        if packet.get(field) is not False:
            errors.append(f"paper_readiness_flag_not_false:{field}")
        if _mapping(packet.get("safety")).get(field) is not False:
            errors.append(f"paper_readiness_safety_flag_not_false:{field}")

    if markdown:
        if decision and decision not in markdown:
            errors.append("paper_readiness_packet_md_missing_decision")
        if _text(packet.get("symbol")) and _text(packet.get("symbol")) not in markdown:
            errors.append("paper_readiness_packet_md_missing_symbol")

    embedded = _mapping(record.get("paper_readiness_packet"))
    if embedded and _text(embedded.get("readiness_decision")) != decision:
        errors.append("embedded_paper_readiness_decision_mismatch")

    if decision == "fixture_ready_preview":
        _validate_paper_ready_checks(packet, errors)


def _validate_paper_ready_checks(
    packet: Mapping[str, object],
    errors: list[str],
) -> None:
    if _mapping(packet.get("min_notional_basis")).get("verified") is not True:
        errors.append("paper_readiness_approved_without_min_notional_evidence")
    if _mapping(packet.get("quantity_increment_basis")).get("verified") is not True:
        errors.append("paper_readiness_approved_without_quantity_increment_evidence")
    if _mapping(packet.get("orderability_basis")).get("verified") is not True:
        errors.append("paper_readiness_approved_without_orderability_evidence")
    if _mapping(packet.get("stale_missing_price_policy_result")).get("status") != "passed":
        errors.append("paper_readiness_approved_without_valid_price")
    if _mapping(packet.get("max_order_notional_check")).get("status") != "passed":
        errors.append("paper_readiness_approved_despite_max_notional_check")
    if _mapping(packet.get("max_total_exposure_check")).get("status") != "passed":
        errors.append("paper_readiness_approved_despite_total_exposure_check")
    if _mapping(packet.get("duplicate_client_order_id_check")).get("status") != "passed":
        errors.append("paper_readiness_approved_despite_duplicate_client_order_id_check")
    if _mapping(packet.get("one_open_order_per_symbol_check")).get("status") != "passed":
        errors.append("paper_readiness_approved_despite_open_order_check")
    if _mapping(packet.get("preexisting_position_policy_result")).get("status") not in {
        "passed",
        "allowed_exit",
    }:
        errors.append("paper_readiness_approved_despite_preexisting_position_check")
    if _mapping(packet.get("state_reconciliation_check")).get("status") != "passed":
        errors.append("paper_readiness_approved_despite_state_reconciliation_failed")


def _validate_broker_observed_readiness_packet(
    *,
    packet: Mapping[str, object],
    record: Mapping[str, object],
    markdown: str,
    errors: list[str],
) -> None:
    _validate_labels("broker_observed_readiness_packet", packet, errors)
    if packet.get("record_type") != "broker_observed_readiness_packet":
        errors.append("broker_observed_readiness_packet_record_type_mismatch")
    if _text(packet.get("run_id")) != _text(record.get("run_id")):
        errors.append("broker_observed_readiness_packet_run_id_mismatch")
    decision = _text(
        packet.get("broker_observed_readiness_decision")
        or packet.get("readiness_decision")
        or packet.get("final_readiness_decision")
    )
    if not decision:
        errors.append("broker_observed_readiness_decision_missing")
    elif decision not in BROKER_OBSERVED_READINESS_DECISIONS:
        errors.append(f"broker_observed_readiness_decision_invalid:{decision}")
    if decision in {"fixture_ready_preview", "fixture_blocked_preview"}:
        errors.append("broker_observed_readiness_labeled_as_fixture")
    if _text(packet.get("readiness_basis")) != "broker_observed":
        errors.append("broker_observed_readiness_basis_mismatch")

    for field in (
        "paper_submit_authorized",
        "paper_submit_occurred",
        "broker_mutation_authorized",
        "broker_mutation_occurred",
        "simulation_mutation_authorized",
        "simulation_mutation_occurred",
        "credential_values_exposed",
        "live_authorized",
        "live_endpoint_touched",
    ):
        if packet.get(field) is not False:
            errors.append(f"broker_observed_readiness_flag_not_false:{field}")
        if _mapping(packet.get("safety")).get(field) is not False:
            errors.append(f"broker_observed_readiness_safety_flag_not_false:{field}")

    if packet.get("broker_read_occurred") is True and packet.get("broker_read_authorized") is not True:
        errors.append("broker_read_occurred_without_authorization")
    if _mapping(packet.get("safety")).get("broker_read_occurred") is True and _mapping(
        packet.get("safety")
    ).get("broker_read_authorized") is not True:
        errors.append("broker_read_safety_occurred_without_authorization")
    if packet.get("broker_read_occurred") is True and packet.get("broker_read_attempted") is not True:
        errors.append("broker_read_occurred_without_attempt")
    if packet.get("broker_state_observed") is True and packet.get("broker_read_occurred") is not True:
        errors.append("broker_state_observed_without_broker_read")
    if (
        record.get("broker_observed_readiness_requested") is not True
        and packet.get("broker_read_occurred") is True
    ):
        errors.append("broker_read_occurred_in_default_simbroker_mode")
    blocker_code = _text(packet.get("blocker_code"))
    blocker_codes = tuple(_string_sequence(packet.get("blocker_codes")))
    if blocker_code and blocker_code not in blocker_codes:
        errors.append("broker_observed_primary_blocker_missing_from_blocker_list")
    check_blockers = tuple(
        blocker
        for blocker in (
            _text(_mapping(packet.get("broker_observed_orderability_check")).get("blocker_code")),
            _text(_mapping(packet.get("broker_observed_price_freshness_check")).get("blocker_code")),
            _text(_mapping(packet.get("broker_observed_min_notional_check")).get("blocker_code")),
            _text(_mapping(packet.get("broker_observed_min_order_size_check")).get("blocker_code")),
            _text(
                _mapping(packet.get("broker_observed_quantity_increment_check")).get(
                    "blocker_code"
                )
            ),
        )
        if blocker
    )
    for check_blocker in check_blockers:
        if check_blocker not in blocker_codes and decision == "broker_observed_blocked_preview":
            errors.append(f"broker_observed_blocker_list_missing:{check_blocker}")
    if blocker_code == "broker_min_notional_not_verified" and any(
        blocker in BROKER_OBSERVED_SPECIFIC_BLOCKERS for blocker in check_blockers
    ):
        errors.append("broker_observed_generic_blocker_with_specific_missing_field")
    if (
        packet.get("broker_read_authorized") is True
        and packet.get("broker_read_occurred") is False
        and not blocker_code
    ):
        errors.append("broker_read_authorized_without_read_or_blocker")
    if (
        packet.get("network_used") is True
        and packet.get("broker_read_occurred") is False
        and not blocker_code
    ):
        errors.append("inconsistent_network_without_broker_read")
    if packet.get("broker_read_blocked") is True and not blocker_code:
        errors.append("broker_read_blocked_without_blocker")
    if decision in {
        "broker_observed_blocked_credentials_not_loaded",
        "broker_observed_blocked_not_authorized",
        "broker_observed_blocked_not_paper_profile",
        "broker_observed_blocked_live_endpoint_detected",
        "broker_observed_blocked_adapter_unavailable",
        "broker_observed_blocked_read_not_implemented",
        "broker_observed_blocked_read_failed",
        "broker_observed_blocked_ambiguous_response",
    }:
        if packet.get("broker_read_blocked") is not True:
            errors.append("broker_observed_blocked_decision_without_blocked_flag")

    orderability_check = _mapping(packet.get("broker_observed_orderability_check"))
    min_notional_check = _mapping(packet.get("broker_observed_min_notional_check"))
    min_order_size_check = _mapping(packet.get("broker_observed_min_order_size_check"))
    quantity_increment_check = _mapping(
        packet.get("broker_observed_quantity_increment_check")
    )
    price_check = _mapping(packet.get("broker_observed_price_freshness_check"))
    if not price_check:
        price_check = _mapping(packet.get("observed_latest_price_basis"))
    _validate_broker_observed_latest_price_evidence(
        packet=packet,
        price_check=price_check,
        decision=decision,
        errors=errors,
    )
    equivalence_fields = _broker_observed_min_notional_equivalence_fields(
        min_notional_check
    )
    for field, expected_value in equivalence_fields.items():
        if field not in packet:
            errors.append(f"broker_observed_readiness_equivalence_field_missing:{field}")
            continue
        actual_value = packet.get(field)
        if field == "derived_min_notional_value":
            actual_value = _evidence_decimal_text(actual_value)
        if actual_value != expected_value:
            errors.append(f"broker_observed_readiness_equivalence_field_mismatch:{field}")

    direct_min_notional_available = packet.get("direct_min_notional_available") is True
    derived_min_notional_available = packet.get("derived_min_notional_available") is True
    derived_min_notional = _first_decimal(
        packet.get("derived_min_notional_value"),
        min_notional_check.get("derived_min_notional_value"),
    )
    price_source_for_derivation = _text(packet.get("price_source_for_derivation"))
    if (
        packet.get("broker_read_occurred") is True
        and _mapping(packet.get("observed_crypto_assets_or_orderability_summary")).get(
            "asset_found"
        )
        is True
        and not direct_min_notional_available
        and not derived_min_notional_available
    ):
        errors.append("broker_observed_direct_min_notional_missing_without_derived_evidence")
    if derived_min_notional_available:
        if not _text(packet.get("derived_min_notional_formula")):
            errors.append("broker_observed_derived_min_notional_missing_formula")
        if not _text(packet.get("derived_min_notional_sources")):
            errors.append("broker_observed_derived_min_notional_missing_sources")
        if derived_min_notional is None:
            errors.append("broker_observed_derived_min_notional_value_missing")
    if (
        decision == "broker_observed_ready_preview"
        and price_source_for_derivation not in OBSERVED_LATEST_PRICE_SOURCES
    ):
        errors.append("broker_price_not_broker_observed")

    if decision in BROKER_OBSERVED_APPROVED_READINESS_DECISIONS:
        if _text(packet.get("fixture_readiness_decision")) != "fixture_ready_preview":
            errors.append("broker_observed_ready_without_fixture_ready_preview")
        if not _text(packet.get("symbol")):
            errors.append("broker_observed_ready_without_selected_candidate")
        if _first_decimal(packet.get("intended_notional")) is None:
            errors.append("broker_observed_ready_without_intended_notional")
        if _first_decimal(packet.get("estimated_quantity")) is None:
            errors.append("broker_observed_ready_without_estimated_quantity")
        if packet.get("broker_read_occurred") is not True:
            errors.append("broker_observed_ready_without_broker_read")
        if packet.get("broker_read_authorized") is not True:
            errors.append("broker_observed_ready_without_authorization")
        if packet.get("broker_state_observed") is not True:
            errors.append("broker_observed_ready_without_state_observed")
        if packet.get("live_endpoint_touched") is not False:
            errors.append("broker_observed_ready_with_live_endpoint_touched")
        if packet.get("app_profile_is_paper") is not True:
            errors.append("broker_observed_ready_without_paper_profile")
        if _mapping(packet.get("observed_crypto_assets_or_orderability_summary")).get(
            "orderability_verified"
        ) is not True:
            errors.append("broker_observed_ready_without_orderability_evidence")
        if orderability_check.get("source") != "broker_observed":
            errors.append("broker_observed_ready_without_broker_observed_orderability")
        if orderability_check.get("status") != "passed":
            errors.append("broker_observed_ready_without_orderability_check")
        min_increment = _mapping(packet.get("observed_min_notional_or_increment_basis"))
        if min_increment.get("min_notional_verified") is not True:
            errors.append("broker_observed_ready_without_min_notional_evidence")
        if min_increment.get("quantity_increment_verified") is not True:
            errors.append("broker_observed_ready_without_increment_evidence")
        if min_notional_check.get("source") == "deterministic_fixture":
            errors.append("broker_observed_ready_with_fixture_only_min_notional_evidence")
        if not direct_min_notional_available and not derived_min_notional_available:
            errors.append("broker_observed_ready_without_min_notional_evidence")
        if min_notional_check.get("source") not in {
            "broker_observed",
            "broker_observed_equivalent",
        }:
            errors.append("broker_observed_ready_without_broker_observed_min_notional")
        if min_notional_check.get("status") != "passed":
            errors.append("broker_observed_ready_without_min_notional_check")
        if (
            derived_min_notional_available
            and packet.get("derived_min_notional_check_status") != "passed"
        ):
            errors.append("broker_observed_ready_without_derived_min_notional_check")
        if min_order_size_check.get("source") != "broker_observed":
            errors.append("broker_observed_ready_without_broker_observed_min_order_size")
        if min_order_size_check.get("status") != "passed":
            errors.append("broker_observed_ready_without_min_order_size_check")
        if quantity_increment_check.get("source") != "broker_observed":
            errors.append("broker_observed_ready_without_broker_observed_increment")
        if quantity_increment_check.get("status") != "passed":
            errors.append("broker_observed_ready_without_quantity_increment_check")
        if price_check.get("status") != "passed":
            errors.append("broker_observed_ready_without_valid_price")
        if price_check.get("accepted_for_broker_observed_readiness") is not True:
            errors.append("broker_observed_ready_without_accepted_price_basis")
        if decision == "broker_observed_ready_preview":
            if price_check.get("accepted_for_full_broker_observed_readiness") is not True:
                errors.append("broker_price_source_not_acceptable_for_full_readiness")
            if price_check.get("latest_price_freshness_status") != "fresh":
                errors.append("broker_observed_ready_without_fresh_observed_price")
        if decision == "broker_observed_ready_preview_with_fixture_price":
            if price_check.get("latest_price_source") not in READINESS_ONLY_LATEST_PRICE_SOURCES:
                errors.append("broker_fixture_price_preview_without_fixture_or_local_price")
        if packet.get("broker_endpoint_type") != "paper":
            errors.append("broker_observed_ready_without_paper_endpoint")
        if _mapping(packet.get("observed_open_orders_summary")).get("open_order_present") is True:
            errors.append("broker_observed_ready_with_open_order_present")
        if _mapping(packet.get("observed_positions_summary")).get(
            "unexpected_preexisting_position"
        ) is True:
            errors.append("broker_observed_ready_with_unexpected_preexisting_position")
        intended_notional = _first_decimal(packet.get("intended_notional"))
        estimated_quantity = _first_decimal(packet.get("estimated_quantity"))
        min_order_size = _first_decimal(min_order_size_check.get("min_order_size"))
        quantity_increment = _first_decimal(quantity_increment_check.get("quantity_increment"))
        if (
            derived_min_notional_available
            and intended_notional is not None
            and derived_min_notional is not None
            and intended_notional < derived_min_notional
        ):
            errors.append("broker_observed_ready_with_intended_below_derived_min_notional")
        if (
            estimated_quantity is not None
            and min_order_size is not None
            and estimated_quantity < min_order_size
        ):
            errors.append("broker_observed_ready_with_quantity_below_min_order_size")
        aligned, _remainder = _quantity_increment_aligned(
            estimated_quantity,
            quantity_increment,
        )
        if aligned is not True:
            errors.append("broker_observed_ready_with_quantity_increment_misaligned")

    if markdown and decision and decision not in markdown:
        errors.append("broker_observed_readiness_packet_md_missing_decision")
    if markdown and "field | value | source | freshness | status" not in markdown:
        errors.append("broker_observed_readiness_packet_md_missing_evidence_table")


def _validate_broker_observed_latest_price_evidence(
    *,
    packet: Mapping[str, object],
    price_check: Mapping[str, object],
    decision: str,
    errors: list[str],
) -> None:
    required_fields = (
        "latest_price_value",
        "latest_price_source",
        "latest_price_observed_at",
        "latest_price_age_seconds",
        "latest_price_symbol",
        "latest_price_bid",
        "latest_price_ask",
        "latest_price_mid",
        "latest_price_last",
        "latest_price_basis",
        "latest_price_freshness_status",
        "latest_price_source_acceptability",
        "price_used_for_quantity",
        "price_used_for_min_notional_derivation",
        "price_evidence_status",
        "price_evidence_blocker",
    )
    for field in required_fields:
        if field not in packet:
            errors.append(f"broker_latest_price_field_missing:{field}")
        if field not in price_check:
            errors.append(f"broker_latest_price_evidence_field_missing:{field}")
            continue
        packet_value = _text(packet.get(field))
        evidence_value = _text(price_check.get(field))
        if field in {
            "latest_price_value",
            "latest_price_bid",
            "latest_price_ask",
            "latest_price_mid",
            "latest_price_last",
            "price_used_for_quantity",
            "price_used_for_min_notional_derivation",
        }:
            packet_value = _evidence_decimal_text(packet.get(field))
            evidence_value = _evidence_decimal_text(price_check.get(field))
        if packet_value != evidence_value:
            errors.append(f"broker_latest_price_field_mismatch:{field}")

    source = _text(price_check.get("latest_price_source") or price_check.get("source"))
    freshness = _text(price_check.get("latest_price_freshness_status"))
    status = _text(price_check.get("price_evidence_status") or price_check.get("status"))
    blocker = _text(price_check.get("price_evidence_blocker") or price_check.get("blocker_code"))
    symbol = _text(price_check.get("latest_price_symbol"))
    selected_symbol = _text(packet.get("selected_symbol") or packet.get("symbol"))

    if not source:
        errors.append("broker_latest_price_source_missing")
    elif source not in LATEST_PRICE_SOURCES:
        errors.append(f"broker_latest_price_source_invalid:{source}")
    if not freshness:
        errors.append("broker_latest_price_freshness_status_missing")
    elif freshness not in LATEST_PRICE_FRESHNESS_STATUSES:
        errors.append(f"broker_latest_price_freshness_status_invalid:{freshness}")
    if selected_symbol and symbol and _normalize_broker_symbol(symbol) != _normalize_broker_symbol(selected_symbol):
        errors.append("broker_latest_price_symbol_mismatch")
    if status == "passed" and blocker:
        errors.append("broker_latest_price_passed_with_blocker")
    if status == "blocked" and not blocker:
        errors.append("broker_latest_price_blocked_without_blocker")
    if status not in {"passed", "blocked"}:
        errors.append("broker_latest_price_evidence_status_invalid")

    quantity_price = _evidence_decimal_text(price_check.get("price_used_for_quantity"))
    derivation_price = _evidence_decimal_text(
        price_check.get("price_used_for_min_notional_derivation")
    )
    if (
        quantity_price
        and derivation_price
        and quantity_price != derivation_price
        and not _text(price_check.get("price_usage_explanation"))
    ):
        errors.append("broker_latest_price_quantity_derivation_price_mismatch")

    if decision == "broker_observed_ready_preview":
        if source not in OBSERVED_LATEST_PRICE_SOURCES:
            errors.append("broker_price_not_broker_observed")
        if freshness != "fresh":
            errors.append("broker_observed_ready_without_fresh_observed_price")
        if status != "passed":
            errors.append("broker_price_evidence_not_verified")
        if price_check.get("accepted_for_full_broker_observed_readiness") is not True:
            errors.append("broker_price_source_not_acceptable_for_full_readiness")
    if decision == "broker_observed_ready_preview_with_fixture_price":
        if source not in READINESS_ONLY_LATEST_PRICE_SOURCES:
            errors.append("broker_fixture_price_preview_without_fixture_or_local_price")
        if freshness != "fresh" or status != "passed":
            errors.append("broker_price_evidence_not_verified")
    if decision in BROKER_OBSERVED_APPROVED_READINESS_DECISIONS and blocker:
        errors.append(f"broker_observed_ready_with_price_blocker:{blocker}")


def _validate_broker_observed_artifact_consistency(
    *,
    record: Mapping[str, object],
    broker_observed_readiness: Mapping[str, object],
    errors: list[str],
) -> None:
    record_telemetry = _mapping(record.get("broker_observed_telemetry"))
    packet_summary = _broker_observed_consistency_summary(
        broker_observed=broker_observed_readiness,
        safety=_mapping(record.get("safety")),
    )
    for field in BROKER_OBSERVED_CONSISTENCY_FIELDS:
        if record_telemetry.get(field) != packet_summary.get(field):
            if field == "network_used":
                errors.append("inconsistent_operating_record_broker_observed_network_flag")
            elif field == "broker_read_occurred":
                errors.append("inconsistent_operating_record_broker_observed_read_flag")
            else:
                errors.append(f"inconsistent_operating_record_broker_observed_field:{field}")


def _validate_manifest_references_paper_readiness(
    manifest: Mapping[str, object],
    errors: list[str],
) -> None:
    required = _mapping(manifest.get("required_artifacts"))
    for name in ("paper_readiness_packet", "paper_readiness_packet_markdown"):
        artifact = _mapping(required.get(name))
        if not artifact:
            errors.append(f"manifest_missing_required_artifact:{name}")
            continue
        if artifact.get("exists") is not True:
            errors.append(f"manifest_required_artifact_missing:{name}")


def _validate_manifest_readiness_bases(
    manifest: Mapping[str, object],
    record: Mapping[str, object],
    errors: list[str],
) -> None:
    bases = _mapping(manifest.get("readiness_bases"))
    fixture = _mapping(bases.get("fixture"))
    broker_observed = _mapping(bases.get("broker_observed"))
    fixture_decision = _text(fixture.get("decision"))
    broker_decision = _text(broker_observed.get("decision"))
    if fixture_decision.startswith("broker_observed_"):
        errors.append("manifest_fixture_readiness_labeled_broker_observed")
    if broker_decision in {"fixture_ready_preview", "fixture_blocked_preview"}:
        errors.append("manifest_broker_observed_readiness_labeled_fixture")
    if not fixture_decision:
        errors.append("manifest_fixture_readiness_decision_missing")
    if not broker_decision:
        errors.append("manifest_broker_observed_readiness_decision_missing")
    if record.get("broker_observed_readiness_requested") is True:
        required = _mapping(manifest.get("required_artifacts"))
        if not _mapping(required.get("broker_observed_readiness_packet")):
            errors.append("manifest_missing_required_artifact:broker_observed_readiness_packet")
        if not _mapping(required.get("broker_observed_readiness_packet_markdown")):
            errors.append(
                "manifest_missing_required_artifact:broker_observed_readiness_packet_markdown"
            )


def _validate_manifest_telemetry(
    manifest: Mapping[str, object],
    record: Mapping[str, object],
    broker_observed_readiness: Mapping[str, object],
    errors: list[str],
) -> None:
    record_telemetry = _mapping(record.get("broker_observed_telemetry"))
    manifest_telemetry = _mapping(manifest.get("broker_observed_telemetry"))
    if not manifest_telemetry:
        errors.append("manifest_broker_observed_telemetry_missing")
    for field in BROKER_OBSERVED_CONSISTENCY_FIELDS:
        if manifest_telemetry.get(field) != record_telemetry.get(field):
            errors.append(f"inconsistent_manifest_operating_record_field:{field}")

    broker_observed = _mapping(_mapping(manifest.get("readiness_bases")).get("broker_observed"))
    field_map = {
        "decision": "broker_observed_readiness_decision",
        "blocker_code": "broker_observed_blocker",
        "broker_read_authorized": "broker_read_authorized",
        "broker_read_attempted": "broker_read_attempted",
        "broker_read_occurred": "broker_read_occurred",
        "broker_read_blocked": "broker_read_blocked",
        "broker_read_adapter_unavailable": "broker_read_adapter_unavailable",
        "broker_read_failed": "broker_read_failed",
        "broker_state_observed": "broker_state_observed",
        "network_used": "network_used",
        "live_endpoint_touched": "live_endpoint_touched",
        "credential_values_exposed": "credential_values_exposed",
        "paper_submit_occurred": "paper_submit_occurred",
        "broker_mutation_occurred": "broker_mutation_occurred",
    }
    for manifest_field, telemetry_field in field_map.items():
        if broker_observed.get(manifest_field) != record_telemetry.get(telemetry_field):
            errors.append(f"inconsistent_manifest_readiness_basis_field:{manifest_field}")

    if broker_observed_readiness:
        _validate_broker_observed_artifact_consistency(
            record=record,
            broker_observed_readiness=broker_observed_readiness,
            errors=errors,
        )


def _validate_labels(
    name: str,
    payload: Mapping[str, object],
    errors: list[str],
) -> None:
    labels = set(_string_sequence(payload.get("safety_labels") or payload.get("labels")))
    for label in REQUIRED_SAFETY_LABELS:
        if label not in labels:
            errors.append(f"{name}_missing_label:{label}")


def _state_paths_for_record(
    record: Mapping[str, object],
    output_root: Path,
) -> dict[str, Path]:
    explicit = _mapping(record.get("state_artifact_paths"))
    if explicit:
        return {
            name: Path(_text(explicit.get(name)))
            for name in STATE_ARTIFACTS
            if _text(explicit.get(name))
        }
    state_root_text = _text(record.get("state_root"))
    state_root = Path(state_root_text) if state_root_text else output_root / "state"
    return {name: state_root / name for name in STATE_ARTIFACTS}


def _validate_state_artifacts(
    *,
    record: Mapping[str, object],
    state_payload: Mapping[str, object],
    positions_payload: Mapping[str, object],
    fills: Sequence[Mapping[str, object]],
    cycle_history: Sequence[Mapping[str, object]],
    state_events: Sequence[Mapping[str, object]],
    errors: list[str],
) -> None:
    _validate_labels("simbroker_state", state_payload, errors)
    if positions_payload:
        _validate_labels("positions", positions_payload, errors)
    if state_payload.get("record_type") != "simbroker_state":
        errors.append("simbroker_state_record_type_mismatch")
    if state_payload.get("broker_mode") != "simulation_broker":
        errors.append("simbroker_state_broker_mode_mismatch")
    state_fills = _mapping_sequence(state_payload.get("fills"))
    state_cycles = _mapping_sequence(state_payload.get("cycle_history"))
    if len(state_fills) != len(fills):
        errors.append("state_fills_jsonl_count_mismatch")
    if len(state_cycles) != len(cycle_history):
        errors.append("state_cycle_history_jsonl_count_mismatch")
    state_errors: list[str] = []
    portfolio = _portfolio_from_state(state_payload, state_errors)
    state_errors.extend(_state_reconciliation_errors(state_payload, portfolio))
    for error in _dedupe(state_errors):
        errors.append(error)
    _validate_cycle_history(cycle_history, fills, errors)
    _validate_event_cycle_order(state_events, errors)
    open_orders = _mapping_sequence(state_payload.get("open_orders"))
    if open_orders and _text(record.get("final_blocker_status")) != "open_simulated_order_present":
        errors.append("open_simulated_order_without_blocker")
    record_cycle_index = record.get("cycle_index")
    if record_cycle_index not in (None, "") and cycle_history:
        last_cycle = cycle_history[-1]
        if _text(last_cycle.get("cycle_index")) != _text(record_cycle_index):
            errors.append("record_cycle_not_latest_state_cycle")


def _validate_cycle_history(
    cycle_history: Sequence[Mapping[str, object]],
    fills: Sequence[Mapping[str, object]],
    errors: list[str],
) -> None:
    prior_index = 0
    mutated_cycle_keys: set[str] = set()
    fills_by_cycle: dict[str, int] = {}
    for fill in fills:
        cycle_index = _text(fill.get("cycle_index"))
        fills_by_cycle[cycle_index] = fills_by_cycle.get(cycle_index, 0) + 1
    for cycle in cycle_history:
        try:
            cycle_index = int(str(cycle.get("cycle_index")))
        except (TypeError, ValueError):
            errors.append("cycle_history_invalid_cycle_index")
            continue
        if cycle_index <= prior_index:
            errors.append("cycle_history_not_monotonic")
        prior_index = cycle_index
        cycle_key = _text(cycle.get("cycle_key"))
        fill_count = int(cycle.get("fill_count", 0) or 0)
        planned_action = _text(cycle.get("planned_action"))
        if planned_action.startswith("hold") and fill_count != 0:
            errors.append(f"hold_cycle_has_fill:{cycle_index}")
        if planned_action.startswith("hold") and fills_by_cycle.get(str(cycle_index), 0):
            errors.append(f"hold_cycle_has_simulated_fill:{cycle_index}")
        if cycle.get("simulation_mutation_occurred") is True:
            if cycle_key in mutated_cycle_keys:
                errors.append(f"duplicate_cycle_mutation:{cycle_key}")
            mutated_cycle_keys.add(cycle_key)
        if planned_action == "simulated_exit" and fill_count > 0:
            before = _decimal_or_error(
                _mapping(cycle.get("portfolio_before")).get("gross_exposure", "0"),
                "cycle.portfolio_before.gross_exposure",
                errors,
            )
            after = _decimal_or_error(
                _mapping(cycle.get("portfolio_after")).get("gross_exposure", "0"),
                "cycle.portfolio_after.gross_exposure",
                errors,
            )
            if after >= before:
                errors.append(f"exit_cycle_did_not_reduce_exposure:{cycle_index}")


def _validate_event_cycle_order(
    events: Sequence[Mapping[str, object]],
    errors: list[str],
) -> None:
    prior = 0
    for event in events:
        value = event.get("cycle_index")
        if value in (None, ""):
            continue
        try:
            cycle_index = int(str(value))
        except (TypeError, ValueError):
            errors.append("event_invalid_cycle_index")
            continue
        if cycle_index < prior:
            errors.append("event_cycle_order_not_monotonic")
        prior = cycle_index


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
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
    )
    return {
        name: (
            os.environ.get(name)
            if name
            in {
                "APP_PROFILE",
                "ALPACA_BASE_URL",
                "ALPACA_PAPER_BASE_URL",
                "APCA_API_BASE_URL",
            }
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


def _broker_observed_quantity_inputs(
    fixture_readiness: Mapping[str, object],
    price_evidence: Mapping[str, object],
) -> tuple[Decimal | None, Decimal | None]:
    side = _text(fixture_readiness.get("side"))
    price = _first_decimal(price_evidence.get("price_used_for_quantity"))
    if (
        side == "buy"
        and price is not None
        and price > Decimal("0")
        and price_evidence.get("price_evidence_status") == "passed"
    ):
        quantity = _demo_quantity(price)
        intended_notional = _first_decimal(fixture_readiness.get("intended_notional"))
        if intended_notional is None:
            intended_notional = quantity * price
        return intended_notional, quantity
    return (
        _first_decimal(fixture_readiness.get("intended_notional")),
        _first_decimal(fixture_readiness.get("estimated_quantity")),
    )


def _broker_observed_readiness_preview(
    *,
    run_id: str,
    cycle_index: int,
    as_of: datetime,
    requested: bool,
    broker_read_authorized: bool,
    fixture_readiness: Mapping[str, object],
    paper_environment: Mapping[str, object] | None,
    broker_client: object | None,
    broker_client_factory: Callable[[], object] | None,
    network_used: bool | None,
) -> dict[str, object]:
    env = paper_environment or _paper_environment_from_os()
    endpoint = _broker_endpoint_status(env)
    symbol = _text(fixture_readiness.get("symbol"))
    side = _text(fixture_readiness.get("side"))
    price_evidence = _broker_observed_price_evidence(fixture_readiness)
    intended_notional, estimated_quantity = _broker_observed_quantity_inputs(
        fixture_readiness,
        price_evidence,
    )
    fixture_decision = _text(fixture_readiness.get("readiness_decision"))
    base_packet = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "broker_observed_readiness_packet",
        "run_id": run_id,
        "cycle_index": cycle_index,
        "as_of": as_of,
        "symbol": symbol,
        "selected_symbol": symbol,
        "side": side,
        "intended_side": side,
        "intended_notional": intended_notional,
        "estimated_quantity": estimated_quantity,
        "latest_price": price_evidence.get("latest_price_value"),
        "latest_price_basis": price_evidence.get("latest_price_basis"),
        "latest_price_evidence": price_evidence,
        **_latest_price_packet_fields(price_evidence),
        "direct_min_notional_available": False,
        "direct_min_notional_source": "unavailable",
        "derived_min_notional_available": False,
        "derived_min_notional_value": "",
        "derived_min_notional_formula": "",
        "derived_min_notional_sources": "",
        "derived_min_notional_check_status": "not_observed",
        "min_notional_equivalence_basis": "unavailable",
        "price_source_for_derivation": price_evidence.get("latest_price_source"),
        "price_source_acceptability": price_evidence.get(
            "latest_price_source_acceptability"
        ),
        "final_feasibility_basis": "not_evaluated",
        "readiness_basis": "broker_observed",
        "fixture_readiness_decision": fixture_decision,
        "fixture_blocker_code": _text(fixture_readiness.get("blocker_code")),
        "broker_read_requested": requested,
        "broker_read_authorized": broker_read_authorized,
        "broker_read_attempted": False,
        "broker_read_occurred": False,
        "broker_read_blocked": False,
        "broker_read_adapter_unavailable": False,
        "broker_read_failed": False,
        "broker_state_observed": False,
        "broker_endpoint_type": endpoint["broker_endpoint_type"],
        "endpoint_proven_paper": endpoint["endpoint_proven_paper"],
        "configured_endpoint_names": endpoint["configured_endpoint_names"],
        "app_profile_is_paper": _text(env.get("APP_PROFILE")) == "paper",
        "live_endpoint_touched": False,
        "paper_account_status": "",
        "trading_blocked": None,
        "account_blocked": None,
        "observed_positions_summary": _empty_observed_summary("positions_not_observed"),
        "observed_open_orders_summary": _empty_observed_summary("open_orders_not_observed"),
        "observed_crypto_assets_or_orderability_summary": _empty_observed_summary(
            "crypto_assets_not_observed"
        ),
        "observed_min_notional_or_increment_basis": {
            "status": "not_observed",
            "min_notional_verified": False,
            "min_order_size_verified": False,
            "quantity_increment_verified": False,
            "min_notional": None,
            "min_order_size": None,
            "quantity_increment": None,
            "broker_observed": False,
        },
        "observed_latest_price_basis": price_evidence,
        "broker_orderability_raw_field_presence": _asset_field_presence(None),
        "broker_orderability_field_sources": {
            "orderability": "unavailable",
            "min_notional": "unavailable",
            "min_order_size": "unavailable",
            "quantity_increment": "unavailable",
            "price_increment": "unavailable",
        },
        "broker_orderability_normalized": {},
        "broker_observed_orderability_check": {
            "status": "blocked",
            "verified": False,
            "source": "unavailable",
            "blocker_code": "broker_orderability_metadata_missing",
        },
        "broker_observed_min_notional_check": {
            "status": "blocked",
            "verified": False,
            "source": "unavailable",
            "intended_notional": intended_notional,
            "min_notional": None,
            "direct_min_notional_available": False,
            "direct_min_notional_source": "unavailable",
            "derived_min_notional_available": False,
            "derived_min_notional_value": None,
            "derived_min_notional_formula": "",
            "derived_min_notional_sources": "",
            "derived_min_notional_check_status": "not_observed",
            "min_notional_equivalence_basis": "unavailable",
            "price_source_for_derivation": price_evidence.get("latest_price_source"),
            "price_source_acceptability": price_evidence.get(
                "latest_price_source_acceptability"
            ),
            "final_feasibility_basis": "not_evaluated",
            "blocker_code": "broker_min_notional_field_missing",
        },
        "broker_observed_min_order_size_check": {
            "status": "blocked",
            "verified": False,
            "source": "unavailable",
            "estimated_quantity": estimated_quantity,
            "min_order_size": None,
            "blocker_code": "broker_min_order_size_field_missing",
        },
        "broker_observed_quantity_increment_check": {
            "status": "blocked",
            "verified": False,
            "source": "unavailable",
            "estimated_quantity": estimated_quantity,
            "quantity_increment": None,
            "remainder": None,
            "blocker_code": "broker_qty_increment_field_missing",
        },
        "broker_observed_price_freshness_check": price_evidence,
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "simulation_mutation_authorized": False,
        "simulation_mutation_occurred": False,
        "credential_values_exposed": False,
        "live_authorized": False,
        "network_used": False,
    }
    if not requested:
        return _broker_observed_packet_with_decision(
            base_packet,
            decision="broker_observed_not_attempted",
            blocker_code="broker_observed_not_requested",
            next_operator_action="default_fixture_preview_only_no_broker_read",
        )
    if not broker_read_authorized:
        return _broker_observed_packet_with_decision(
            {**base_packet, "broker_read_blocked": True},
            decision="broker_observed_blocked_not_authorized",
            blocker_code="broker_price_read_not_authorized",
            next_operator_action="rerun_with_allow_alpaca_paper_read_in_paper_shell",
        )
    if _text(env.get("APP_PROFILE")) != "paper":
        return _broker_observed_packet_with_decision(
            {**base_packet, "broker_read_blocked": True},
            decision="broker_observed_blocked_not_paper_profile",
            blocker_code="broker_price_read_blocked_not_paper_profile",
            next_operator_action="set_APP_PROFILE_paper_in_dedicated_paper_shell",
        )
    if not _paper_credentials_loaded(env):
        return _broker_observed_packet_with_decision(
            {**base_packet, "broker_read_blocked": True},
            decision="broker_observed_blocked_credentials_not_loaded",
            blocker_code="broker_price_read_blocked_credentials_not_loaded",
            next_operator_action="load_paper_credentials_without_printing_values",
        )
    if endpoint["endpoint_proven_paper"] is not True:
        return _broker_observed_packet_with_decision(
            {**base_packet, "broker_read_blocked": True},
            decision="broker_observed_blocked_live_endpoint_detected",
            blocker_code="broker_price_read_blocked_live_endpoint_detected",
            next_operator_action="fix_endpoint_to_paper_before_any_broker_read",
        )

    if (
        paper_environment is not None
        and broker_client is None
        and broker_client_factory is None
    ):
        return _broker_observed_packet_with_decision(
            {
                **base_packet,
                "broker_read_blocked": True,
                "broker_read_adapter_unavailable": True,
            },
            decision="broker_observed_blocked_adapter_unavailable",
            blocker_code="broker_price_adapter_unavailable",
            next_operator_action="provide_read_only_adapter_before_broker_observed_readiness",
        )

    read_attempted = False
    try:
        client = broker_client or (
            broker_client_factory() if broker_client_factory is not None else _build_alpaca_read_client()
        )
        if client is None:
            return _broker_observed_packet_with_decision(
                {
                    **base_packet,
                    "broker_read_blocked": True,
                    "broker_read_adapter_unavailable": True,
                },
                decision="broker_observed_blocked_adapter_unavailable",
                blocker_code="broker_price_adapter_unavailable",
                next_operator_action="provide_read_only_adapter_before_broker_observed_readiness",
            )
        missing_methods = [
            method_name
            for method_name in ("get_account", "get_positions", "get_orders", "list_assets")
            if not callable(getattr(client, method_name, None))
        ]
        if missing_methods:
            return _broker_observed_packet_with_decision(
                {
                    **base_packet,
                    "broker_read_blocked": True,
                    "broker_read_adapter_unavailable": True,
                    "missing_read_methods": missing_methods,
                },
                decision="broker_observed_blocked_read_not_implemented",
                blocker_code="broker_price_adapter_unavailable",
                next_operator_action="implement_required_read_methods_before_retry",
            )
        read_attempted = True
        account = _call_read_method(client, "get_account")
        positions = tuple(_call_read_method(client, "get_positions") or ())
        open_orders = tuple(_read_open_orders(client, symbol))
        assets = tuple(_call_read_method(client, "list_assets") or ())
        price_evidence = _read_latest_price_evidence(
            client=client,
            selected_symbol=symbol,
            as_of=as_of,
            fallback_evidence=price_evidence,
        )
        intended_notional, estimated_quantity = _broker_observed_quantity_inputs(
            fixture_readiness,
            price_evidence,
        )
    except Exception as exc:
        return _broker_observed_packet_with_decision(
            {
                **base_packet,
                "broker_read_attempted": read_attempted,
                "broker_read_occurred": False,
                "broker_read_blocked": True,
                "broker_read_failed": read_attempted,
                "network_used": (
                    (True if network_used is None else network_used) if read_attempted else False
                ),
                "broker_error_type": exc.__class__.__name__,
                "broker_error": _safe_broker_observed_error(exc),
            },
            decision="broker_observed_blocked_read_failed",
            blocker_code="broker_price_read_failed",
            next_operator_action="operator_review_broker_read_failure_before_retry",
        )

    positions_summary = _observed_positions_summary(positions, symbol)
    open_orders_summary = _observed_open_orders_summary(open_orders, symbol)
    asset_summary = _observed_crypto_asset_summary(assets, symbol)
    checks = _broker_observed_feasibility_checks(
        fixture_readiness=fixture_readiness,
        asset_summary=asset_summary,
        price_evidence=price_evidence,
        intended_notional=intended_notional,
        estimated_quantity=estimated_quantity,
    )
    min_notional_check = _mapping(checks["min_notional"])
    equivalence_fields = _broker_observed_min_notional_equivalence_fields(
        min_notional_check
    )
    min_increment_basis = {
        "status": (
            "verified"
            if min_notional_check.get("status") == "passed"
            and _mapping(checks["min_order_size"]).get("status") == "passed"
            and _mapping(checks["quantity_increment"]).get("status") == "passed"
            else "missing"
        ),
        "min_notional_verified": min_notional_check.get("verified") is True,
        "min_order_size_verified": _mapping(checks["min_order_size"]).get("verified") is True,
        "quantity_increment_verified": _mapping(checks["quantity_increment"]).get("verified")
        is True,
        "min_notional": min_notional_check.get("min_notional"),
        "min_order_size": asset_summary["min_order_size"],
        "quantity_increment": asset_summary["quantity_increment"],
        "min_notional_source": min_notional_check.get("source"),
        "min_order_size_source": asset_summary.get("min_order_size_source"),
        "quantity_increment_source": asset_summary.get("quantity_increment_source"),
        **equivalence_fields,
        "broker_observed": True,
        "basis": asset_summary["basis"],
    }
    account_status = _text(_field(account, "status"))
    trading_blocked = _optional_bool(_field(account, "trading_blocked"))
    account_blocked = _optional_bool(_field(account, "account_blocked"))
    observed_packet = {
        **base_packet,
        "intended_notional": intended_notional,
        "estimated_quantity": estimated_quantity,
        "latest_price": price_evidence.get("latest_price_value"),
        "latest_price_basis": price_evidence.get("latest_price_basis"),
        "latest_price_evidence": price_evidence,
        **_latest_price_packet_fields(price_evidence),
        "broker_read_attempted": True,
        "broker_read_occurred": True,
        "broker_state_observed": True,
        "paper_account_status": account_status,
        "trading_blocked": trading_blocked,
        "account_blocked": account_blocked,
        "observed_positions_summary": positions_summary,
        "observed_open_orders_summary": open_orders_summary,
        "observed_crypto_assets_or_orderability_summary": asset_summary,
        "observed_min_notional_or_increment_basis": min_increment_basis,
        "observed_latest_price_basis": checks["price"],
        "broker_observed_price_freshness_check": checks["price"],
        **_latest_price_packet_fields(checks["price"]),
        **equivalence_fields,
        "broker_orderability_raw_field_presence": asset_summary.get("raw_field_presence"),
        "broker_orderability_field_sources": asset_summary.get("field_sources"),
        "broker_orderability_normalized": asset_summary.get("normalized_orderability_fields"),
        "broker_observed_orderability_check": checks["orderability"],
        "broker_observed_min_notional_check": checks["min_notional"],
        "broker_observed_min_order_size_check": checks["min_order_size"],
        "broker_observed_quantity_increment_check": checks["quantity_increment"],
        "network_used": True if network_used is None else network_used,
    }
    blockers = _broker_observed_blockers(
        fixture_decision=fixture_decision,
        account_status=account_status,
        trading_blocked=trading_blocked,
        account_blocked=account_blocked,
        positions_summary=positions_summary,
        open_orders_summary=open_orders_summary,
        asset_summary=asset_summary,
        checks=checks,
    )
    if blockers:
        return _broker_observed_packet_with_decision(
            {**observed_packet, "blocker_codes": list(blockers)},
            decision="broker_observed_blocked_preview",
            blocker_code=blockers[0],
            next_operator_action="resolve_broker_observed_blocker_before_any_paper_submit",
        )
    ready_decision = (
        "broker_observed_ready_preview"
        if _mapping(checks["price"]).get("accepted_for_full_broker_observed_readiness")
        is True
        else "broker_observed_ready_preview_with_fixture_price"
    )
    return _broker_observed_packet_with_decision(
        observed_packet,
        decision=ready_decision,
        blocker_code="",
        next_operator_action="operator_review_broker_observed_readiness_no_submit",
    )


def _build_alpaca_read_client() -> object:
    from algotrader.config import AlpacaPaperConfig
    from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient

    env = os.environ
    config = AlpacaPaperConfig(
        app_profile=env.get("APP_PROFILE", ""),
        alpaca_api_key=env.get("ALPACA_API_KEY") or env.get("APCA_API_KEY_ID"),
        alpaca_secret_key=(
            env.get("ALPACA_SECRET_KEY")
            or env.get("ALPACA_API_SECRET_KEY")
            or env.get("APCA_API_SECRET_KEY")
        ),
        alpaca_paper_base_url=env.get("ALPACA_PAPER_BASE_URL", DEFAULT_ALPACA_PAPER_ENDPOINT),
    )
    return AlpacaSdkClient(config)


def _broker_observed_packet_with_decision(
    packet: Mapping[str, object],
    *,
    decision: str,
    blocker_code: str,
    next_operator_action: str,
) -> dict[str, object]:
    payload = dict(packet)
    payload.update(
        {
            "broker_observed_readiness_decision": decision,
            "readiness_decision": decision,
            "final_readiness_decision": decision,
            "blocker_code": blocker_code,
            "next_operator_action": next_operator_action,
        }
    )
    blocker_codes = list(_string_sequence(payload.get("blocker_codes")))
    if blocker_code and blocker_code not in blocker_codes:
        blocker_codes.insert(0, blocker_code)
    payload["blocker_codes"] = blocker_codes
    safety = {
        "simulation_or_paper_only": True,
        "not_live_authorized": True,
        "no_real_capital": True,
        "profit_claim": "none",
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "simulation_mutation_authorized": False,
        "simulation_mutation_occurred": False,
        "broker_read_authorized": payload["broker_read_authorized"],
        "broker_read_attempted": payload["broker_read_attempted"],
        "broker_read_occurred": payload["broker_read_occurred"],
        "broker_read_blocked": payload["broker_read_blocked"],
        "broker_read_adapter_unavailable": payload["broker_read_adapter_unavailable"],
        "broker_read_failed": payload["broker_read_failed"],
        "broker_state_observed": payload["broker_state_observed"],
        "broker_endpoint_type": payload["broker_endpoint_type"],
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "live_authorized": False,
        "network_used": payload["network_used"],
    }
    labels = (
        *REQUIRED_SAFETY_LABELS,
        "broker_mode=alpaca_paper_read_only",
        f"broker_read_authorized={_bool_text(payload['broker_read_authorized'])}",
        f"broker_read_attempted={_bool_text(payload['broker_read_attempted'])}",
        f"broker_read_occurred={_bool_text(payload['broker_read_occurred'])}",
        f"broker_read_blocked={_bool_text(payload['broker_read_blocked'])}",
        f"broker_read_adapter_unavailable={_bool_text(payload['broker_read_adapter_unavailable'])}",
        f"broker_read_failed={_bool_text(payload['broker_read_failed'])}",
        f"broker_state_observed={_bool_text(payload['broker_state_observed'])}",
        f"live_endpoint_touched={_bool_text(payload['live_endpoint_touched'])}",
        f"network_used={_bool_text(payload['network_used'])}",
        "paper_submit_authorized=false",
        "paper_submit_occurred=false",
        "broker_mutation_authorized=false",
        "broker_mutation_occurred=false",
        "live_authorized=false",
    )
    payload["safety"] = safety
    payload["safety_labels"] = list(labels)
    payload["labels"] = list(labels)
    payload["profit_claim"] = "none"
    return payload


def _broker_observed_min_notional_equivalence_fields(
    min_notional_check: Mapping[str, object],
) -> dict[str, object]:
    return {
        "direct_min_notional_available": min_notional_check.get(
            "direct_min_notional_available"
        )
        is True,
        "direct_min_notional_source": _text(
            min_notional_check.get("direct_min_notional_source")
        )
        or "unavailable",
        "derived_min_notional_available": min_notional_check.get(
            "derived_min_notional_available"
        )
        is True,
        "derived_min_notional_value": _evidence_decimal_text(
            min_notional_check.get("derived_min_notional_value")
        ),
        "derived_min_notional_formula": _text(
            min_notional_check.get("derived_min_notional_formula")
        ),
        "derived_min_notional_sources": _text(
            min_notional_check.get("derived_min_notional_sources")
        ),
        "derived_min_notional_check_status": _text(
            min_notional_check.get("derived_min_notional_check_status")
        )
        or "not_observed",
        "min_notional_equivalence_basis": _text(
            min_notional_check.get("min_notional_equivalence_basis")
        )
        or "unavailable",
        "price_source_for_derivation": _text(
            min_notional_check.get("price_source_for_derivation")
        )
        or "unavailable",
        "price_source_acceptability": _text(
            min_notional_check.get("price_source_acceptability")
        )
        or "blocked_unavailable",
        "final_feasibility_basis": _text(
            min_notional_check.get("final_feasibility_basis")
        )
        or "not_evaluated",
    }


def _broker_observed_evidence_consistency_fields(
    broker_observed: Mapping[str, object],
) -> dict[str, object]:
    asset_summary = _mapping(
        broker_observed.get("observed_crypto_assets_or_orderability_summary")
    )
    field_sources = _mapping(
        broker_observed.get("broker_orderability_field_sources")
        or asset_summary.get("field_sources")
    )
    orderability_check = _mapping(broker_observed.get("broker_observed_orderability_check"))
    min_notional_check = _mapping(
        broker_observed.get("broker_observed_min_notional_check")
    )
    min_order_size_check = _mapping(
        broker_observed.get("broker_observed_min_order_size_check")
    )
    quantity_increment_check = _mapping(
        broker_observed.get("broker_observed_quantity_increment_check")
    )
    price_check = _mapping(broker_observed.get("broker_observed_price_freshness_check"))
    if not price_check:
        price_check = _mapping(broker_observed.get("observed_latest_price_basis"))
    min_notional_value = (
        min_notional_check.get("min_notional")
        if "min_notional" in min_notional_check
        else asset_summary.get("min_notional")
    )
    min_order_size_value = (
        min_order_size_check.get("min_order_size")
        if "min_order_size" in min_order_size_check
        else asset_summary.get("min_order_size")
    )
    quantity_increment_value = (
        quantity_increment_check.get("quantity_increment")
        if "quantity_increment" in quantity_increment_check
        else asset_summary.get("quantity_increment")
    )
    return {
        "broker_observed_orderability_source": _text(
            orderability_check.get("source") or field_sources.get("orderability")
        ),
        "broker_observed_orderability_check_status": _text(
            orderability_check.get("status")
        ),
        "broker_observed_min_notional_value": _evidence_decimal_text(min_notional_value),
        "broker_observed_min_notional_source": _text(
            min_notional_check.get("source") or field_sources.get("min_notional")
        ),
        "broker_observed_min_notional_check_status": _text(
            min_notional_check.get("status")
        ),
        "broker_observed_min_order_size_value": _evidence_decimal_text(
            min_order_size_value
        ),
        "broker_observed_min_order_size_source": _text(
            min_order_size_check.get("source") or field_sources.get("min_order_size")
        ),
        "broker_observed_min_order_size_check_status": _text(
            min_order_size_check.get("status")
        ),
        "broker_observed_quantity_increment_value": _evidence_decimal_text(
            quantity_increment_value
        ),
        "broker_observed_quantity_increment_source": _text(
            quantity_increment_check.get("source")
            or field_sources.get("quantity_increment")
        ),
        "broker_observed_quantity_increment_check_status": _text(
            quantity_increment_check.get("status")
        ),
        "broker_observed_price_source": _text(price_check.get("source")),
        "broker_observed_price_check_status": _text(price_check.get("status")),
        **_latest_price_packet_fields(price_check),
        **_broker_observed_min_notional_equivalence_fields(min_notional_check),
    }


def _evidence_decimal_text(value: object) -> str:
    parsed = _decimal_or_none(value)
    if parsed is None:
        return _text(value)
    return _decimal_text(parsed)


def _broker_observed_consistency_summary(
    *,
    broker_observed: Mapping[str, object],
    safety: Mapping[str, object],
) -> dict[str, object]:
    return {
        "broker_read_authorized": broker_observed.get("broker_read_authorized") is True,
        "broker_read_attempted": broker_observed.get("broker_read_attempted") is True,
        "broker_read_occurred": broker_observed.get("broker_read_occurred") is True,
        "broker_read_blocked": broker_observed.get("broker_read_blocked") is True,
        "broker_read_adapter_unavailable": (
            broker_observed.get("broker_read_adapter_unavailable") is True
        ),
        "broker_read_failed": broker_observed.get("broker_read_failed") is True,
        "broker_state_observed": broker_observed.get("broker_state_observed") is True,
        "network_used": (
            broker_observed.get("network_used") is True
            if "network_used" in broker_observed
            else safety.get("network_used") is True
        ),
        "broker_observed_readiness_decision": _text(
            broker_observed.get("broker_observed_readiness_decision")
            or broker_observed.get("readiness_decision")
            or broker_observed.get("final_readiness_decision")
        ),
        "broker_observed_blocker": _text(broker_observed.get("blocker_code")),
        "live_endpoint_touched": broker_observed.get("live_endpoint_touched") is True,
        "credential_values_exposed": (
            broker_observed.get("credential_values_exposed") is True
            if "credential_values_exposed" in broker_observed
            else safety.get("credential_values_exposed") is True
        ),
        "paper_submit_occurred": (
            broker_observed.get("paper_submit_occurred") is True
            if "paper_submit_occurred" in broker_observed
            else safety.get("paper_submit_occurred") is True
        ),
        "broker_mutation_occurred": (
            broker_observed.get("broker_mutation_occurred") is True
            if "broker_mutation_occurred" in broker_observed
            else safety.get("broker_mutation_occurred") is True
        ),
        **_broker_observed_evidence_consistency_fields(broker_observed),
    }


def _run_summary_payload(packet: Mapping[str, object]) -> dict[str, object]:
    telemetry = _mapping(packet.get("broker_observed_telemetry"))
    if not telemetry:
        telemetry = {
            field: packet.get(field)
            for field in BROKER_OBSERVED_CONSISTENCY_FIELDS
            if field in packet
        }
    console_fields = {
        "status": "complete",
        "mode": _text(packet.get("mode")),
        "broker_mode": _text(packet.get("broker_mode")),
        "scenario": _text(packet.get("scenario")),
        "cycle_index": _text(packet.get("cycle_index")),
        "planned_action": _text(packet.get("planned_action")),
        "decision": _text(packet.get("decision")),
        "final_blocker_status": _text(packet.get("final_blocker_status")),
        **{
            field: telemetry.get(field)
            for field in BROKER_OBSERVED_CONSISTENCY_FIELDS
        },
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "tomorrow_crypto_trader_demo_run_summary",
        "run_id": _text(packet.get("run_id")),
        "as_of": _text(packet.get("as_of")),
        "console_prefix": "tomorrow_crypto_trader_demo",
        "console_fields": console_fields,
        "console_lines": _console_summary_lines(console_fields),
        "safety_labels": list(_string_sequence(packet.get("safety_labels"))),
        "labels": list(_string_sequence(packet.get("labels"))),
        "profit_claim": "none",
    }


def _console_summary_lines(fields: Mapping[str, object]) -> list[str]:
    lines: list[str] = []
    ordered_keys = [
        key
        for key in RUN_SUMMARY_CONSOLE_FIELDS
        if key in fields
    ]
    ordered_keys.extend(sorted(key for key in fields if key not in set(ordered_keys)))
    for key in ordered_keys:
        value = fields.get(key)
        if type(value) is bool:
            rendered = _bool_text(value)
        else:
            rendered = _text(value)
        lines.append(f"tomorrow_crypto_trader_demo_{key}={rendered}")
    return lines


def _validation_summary_fields(
    *,
    record: Mapping[str, object],
    broker_observed_readiness: Mapping[str, object],
    run_summary: Mapping[str, object],
) -> dict[str, object]:
    source = _mapping(record.get("broker_observed_telemetry"))
    if not source:
        source = _mapping(run_summary.get("console_fields"))
    if not source:
        source = _broker_observed_consistency_summary(
            broker_observed=broker_observed_readiness,
            safety=_mapping(record.get("safety")),
        )
    return {
        field: source.get(field)
        for field in BROKER_OBSERVED_CONSISTENCY_FIELDS
    }


def _broker_endpoint_status(env: Mapping[str, object]) -> dict[str, object]:
    configured = {
        name: _text(env.get(name))
        for name in ("ALPACA_BASE_URL", "ALPACA_PAPER_BASE_URL", "APCA_API_BASE_URL")
        if _text(env.get(name))
    }
    if _text(env.get("APP_PROFILE")).lower() == "live":
        return {
            "broker_endpoint_type": "live_or_unproven",
            "endpoint_proven_paper": False,
            "configured_endpoint_names": sorted(configured),
        }
    for value in configured.values():
        if not _is_proven_paper_endpoint(value):
            return {
                "broker_endpoint_type": "live_or_unproven",
                "endpoint_proven_paper": False,
                "configured_endpoint_names": sorted(configured),
            }
    paper_endpoint = configured.get("ALPACA_PAPER_BASE_URL", DEFAULT_ALPACA_PAPER_ENDPOINT)
    return {
        "broker_endpoint_type": "paper" if _is_proven_paper_endpoint(paper_endpoint) else "unknown",
        "endpoint_proven_paper": _is_proven_paper_endpoint(paper_endpoint),
        "configured_endpoint_names": sorted(configured),
    }


def _is_proven_paper_endpoint(value: str) -> bool:
    normalized = value.strip().lower().rstrip("/")
    return normalized == DEFAULT_ALPACA_PAPER_ENDPOINT


def _call_read_method(client: object, method_name: str) -> object:
    method = getattr(client, method_name)
    return method()


def _read_open_orders(client: object, symbol: str) -> Sequence[object]:
    method = getattr(client, "get_orders")
    try:
        from algotrader.execution.alpaca_client import AlpacaRecentOrderQuery

        return method(AlpacaRecentOrderQuery(status_filter="open", symbol_filter=symbol))
    except TypeError:
        return method()


LATEST_PRICE_READ_METHODS = (
    ("get_latest_quote", "quote"),
    ("get_crypto_latest_quote", "quote"),
    ("get_latest_crypto_quote", "quote"),
    ("get_latest_trade", "trade"),
    ("get_crypto_latest_trade", "trade"),
    ("get_latest_crypto_trade", "trade"),
    ("get_latest_bar", "bar"),
    ("get_crypto_latest_bar", "bar"),
    ("get_latest_crypto_bar", "bar"),
    ("get_latest_price", "latest_price"),
    ("get_crypto_latest_price", "latest_price"),
    ("get_latest_crypto_price", "latest_price"),
)


def _read_latest_price_evidence(
    *,
    client: object,
    selected_symbol: str,
    as_of: datetime,
    fallback_evidence: Mapping[str, object],
) -> dict[str, object]:
    for method_name, basis in LATEST_PRICE_READ_METHODS:
        method = getattr(client, method_name, None)
        if not callable(method):
            continue
        response = _call_symbol_read_method(method, selected_symbol)
        return _latest_price_evidence_from_response(
            response=response,
            selected_symbol=selected_symbol,
            as_of=as_of,
            default_basis=basis,
        )
    return dict(fallback_evidence)


def _call_symbol_read_method(method: Callable[..., object], symbol: str) -> object:
    try:
        return method(symbol)
    except TypeError:
        return method()


def _latest_price_evidence_from_response(
    *,
    response: object,
    selected_symbol: str,
    as_of: datetime,
    default_basis: str,
) -> dict[str, object]:
    if response in (None, ""):
        return _latest_price_evidence(
            selected_symbol=selected_symbol,
            source="unavailable",
            basis=default_basis,
            as_of=as_of,
            latest_price=None,
            observed_at=None,
            raw_symbol=selected_symbol,
            blocker_code="broker_latest_price_missing",
            freshness_status="unavailable",
        )
    if isinstance(response, Mapping) and _looks_like_latest_price_symbol_map(response):
        rows = tuple(response.items())
        if len(rows) != 1:
            return _latest_price_evidence(
                selected_symbol=selected_symbol,
                source="ambiguous",
                basis=default_basis,
                as_of=as_of,
                latest_price=None,
                observed_at=None,
                raw_symbol=selected_symbol,
                blocker_code="broker_latest_price_ambiguous",
                freshness_status="ambiguous",
            )
        response_symbol, response_value = rows[0]
        if isinstance(response_value, Mapping):
            payload = dict(response_value)
            payload.setdefault("symbol", response_symbol)
            response = payload
        else:
            response = response_value
    if isinstance(response, Sequence) and not isinstance(response, (str, bytes, bytearray)):
        rows = tuple(response)
        if len(rows) != 1:
            return _latest_price_evidence(
                selected_symbol=selected_symbol,
                source="ambiguous",
                basis=default_basis,
                as_of=as_of,
                latest_price=None,
                observed_at=None,
                raw_symbol=selected_symbol,
                blocker_code="broker_latest_price_ambiguous",
                freshness_status="ambiguous",
            )
        response = rows[0]

    basis = _text(
        _field(response, "latest_price_basis")
        or _field(response, "basis")
        or default_basis
    )
    basis_kind = _latest_price_basis_kind(basis or default_basis)
    source = _text(
        _field(response, "latest_price_source")
        or _field(response, "source")
        or "broker_observed"
    )
    raw_symbol = _text(
        _field(response, "latest_price_symbol")
        or _field(response, "symbol")
        or selected_symbol
    )
    observed_at = (
        _field(response, "latest_price_observed_at")
        or _field(response, "observed_at")
        or _field(response, "timestamp")
        or _field(response, "time")
        or _field(response, "t")
    )
    bid = _first_decimal(
        _field(response, "latest_price_bid"),
        _field(response, "bid"),
        _field(response, "bid_price"),
        _field(response, "bp"),
    )
    ask = _first_decimal(
        _field(response, "latest_price_ask"),
        _field(response, "ask"),
        _field(response, "ask_price"),
        _field(response, "ap"),
    )
    explicit_mid = _first_decimal(_field(response, "latest_price_mid"), _field(response, "mid"))
    mid = explicit_mid
    if mid is None and bid is not None and ask is not None:
        mid = (bid + ask) / Decimal("2")
    last = _first_decimal(
        _field(response, "latest_price_last"),
        _field(response, "last"),
        _field(response, "last_price"),
        _field(response, "trade_price"),
        _field(response, "price"),
        _field(response, "p"),
    )
    close = _first_decimal(
        _field(response, "close"),
        _field(response, "close_price"),
        _field(response, "c"),
    )

    blocker = ""
    latest_price: Decimal | None
    if basis_kind == "quote":
        latest_price = mid
        if (
            bid is None
            or ask is None
            or bid <= Decimal("0")
            or ask <= Decimal("0")
            or bid > ask
        ):
            blocker = "broker_quote_bid_ask_invalid"
    elif basis_kind == "trade":
        latest_price = last
        if latest_price is None or latest_price <= Decimal("0"):
            blocker = "broker_trade_price_invalid"
    elif basis_kind == "bar":
        latest_price = close
        last = last if last is not None else close
        if latest_price is None or latest_price <= Decimal("0"):
            blocker = "broker_bar_close_invalid"
    else:
        latest_price = _first_decimal(
            _field(response, "latest_price_value"),
            _field(response, "latest_price"),
            _field(response, "price"),
            mid,
            last,
            close,
        )
        if latest_price is None or latest_price <= Decimal("0"):
            blocker = "broker_latest_price_missing"

    return _latest_price_evidence(
        selected_symbol=selected_symbol,
        source=source,
        basis=basis or default_basis,
        as_of=as_of,
        latest_price=latest_price,
        observed_at=observed_at,
        bid=bid,
        ask=ask,
        mid=mid,
        last=last,
        raw_symbol=raw_symbol,
        blocker_code=blocker,
    )


LATEST_PRICE_DIRECT_RESPONSE_FIELDS = (
    "latest_price_value",
    "latest_price",
    "latest_price_bid",
    "latest_price_ask",
    "latest_price_mid",
    "latest_price_last",
    "bid",
    "bid_price",
    "bp",
    "ask",
    "ask_price",
    "ap",
    "last",
    "last_price",
    "trade_price",
    "price",
    "p",
    "close",
    "close_price",
    "c",
    "timestamp",
    "time",
    "t",
    "symbol",
    "basis",
    "source",
)


def _looks_like_latest_price_symbol_map(response: Mapping[object, object]) -> bool:
    if not response:
        return False
    return not any(field in response for field in LATEST_PRICE_DIRECT_RESPONSE_FIELDS)


def _latest_price_basis_kind(basis: str) -> str:
    normalized = basis.lower()
    if "quote" in normalized:
        return "quote"
    if "trade" in normalized:
        return "trade"
    if "bar" in normalized:
        return "bar"
    return "latest_price"


BROKER_ASSET_ORDERABILITY_FIELDS = (
    "symbol",
    "asset_class",
    "class",
    "status",
    "tradable",
    "orderable",
    "fractionable",
    "fractional",
    "min_order_value",
    "min_notional",
    "min_order_size",
    "min_trade_size",
    "min_trade_increment",
    "qty_increment",
    "price_increment",
    "min_price_increment",
)


def _asset_field_presence(asset: object | None) -> dict[str, bool]:
    return {
        field_name: bool(asset is not None and _field(asset, field_name) not in (None, ""))
        for field_name in BROKER_ASSET_ORDERABILITY_FIELDS
    }


def _first_nonempty_field(asset: object, *field_names: str) -> tuple[object, str]:
    for field_name in field_names:
        value = _field(asset, field_name)
        if value not in (None, ""):
            return value, field_name
    return None, ""


def _decimal_asset_field(asset: object, *field_names: str) -> tuple[Decimal | None, str, str]:
    value, field_name = _first_nonempty_field(asset, *field_names)
    if not field_name:
        return None, "", "unavailable"
    parsed = _decimal_or_none(value)
    if parsed is None:
        return None, field_name, "ambiguous"
    return parsed, field_name, "broker_observed"


def _bool_asset_field(asset: object, *field_names: str) -> tuple[bool | None, str, str]:
    value, field_name = _first_nonempty_field(asset, *field_names)
    if not field_name:
        return None, "", "unavailable"
    parsed = _optional_bool(value)
    if parsed is None:
        return None, field_name, "ambiguous"
    return parsed, field_name, "broker_observed"


def _text_asset_field(asset: object, *field_names: str) -> tuple[str, str, str]:
    value, field_name = _first_nonempty_field(asset, *field_names)
    if not field_name:
        return "", "", "unavailable"
    return _text(value), field_name, "broker_observed"


def _observed_positions_summary(
    positions: Sequence[object],
    symbol: str,
) -> dict[str, object]:
    rows = [
        {
            "symbol": _text(_field(position, "symbol")),
            "quantity": _text(_field(position, "qty") or _field(position, "quantity")),
            "side": _text(_field(position, "side")),
        }
        for position in positions
    ]
    unexpected = [
        row
        for row in rows
        if _normalize_broker_symbol(row["symbol"]) == _normalize_broker_symbol(symbol)
        and _decimal_or_none(row["quantity"]) not in (None, Decimal("0"))
    ]
    return {
        "status": "blocked" if unexpected else "clear",
        "total_position_count": len(rows),
        "selected_symbol_position_count": len(unexpected),
        "unexpected_preexisting_position": bool(unexpected),
        "positions": rows,
    }


def _observed_open_orders_summary(
    orders: Sequence[object],
    symbol: str,
) -> dict[str, object]:
    rows = [
        {
            "symbol": _text(_field(order, "symbol")),
            "status": _text(_field(order, "status")),
            "side": _text(_field(order, "side")),
            "client_order_id": _text(_field(order, "client_order_id")),
        }
        for order in orders
    ]
    matching = [
        row
        for row in rows
        if _normalize_broker_symbol(row["symbol"]) == _normalize_broker_symbol(symbol)
        and _text(row["status"]).lower() not in {"filled", "canceled", "expired", "rejected"}
    ]
    return {
        "status": "blocked" if matching else "clear",
        "total_open_order_count": len(rows),
        "selected_symbol_open_order_count": len(matching),
        "open_order_present": bool(matching),
        "open_orders": rows,
    }


def _observed_crypto_asset_summary(
    assets: Sequence[object],
    symbol: str,
) -> dict[str, object]:
    normalized_symbol = _normalize_broker_symbol(symbol)
    matching_assets = tuple(
        asset
        for asset in assets
        if _normalize_broker_symbol(_text(_field(asset, "symbol"))) == normalized_symbol
    )
    if not matching_assets:
        return {
            "status": "missing",
            "symbol": symbol,
            "asset_found": False,
            "matching_asset_count": 0,
            "orderability_verified": False,
            "min_order_size_verified": False,
            "min_notional_verified": False,
            "quantity_increment_verified": False,
            "min_notional": None,
            "min_order_size": None,
            "quantity_increment": None,
            "min_trade_increment": None,
            "qty_increment": None,
            "price_increment": None,
            "broker_observed": True,
            "basis": "broker_orderability_metadata_missing",
            "raw_field_presence": _asset_field_presence(None),
            "field_sources": {
                "orderability": "unavailable",
                "asset_class": "unavailable",
                "status": "unavailable",
                "tradable": "unavailable",
                "orderable": "unavailable",
                "fractional": "unavailable",
                "min_notional": "unavailable",
                "min_order_size": "unavailable",
                "quantity_increment": "unavailable",
                "price_increment": "unavailable",
            },
            "normalized_orderability_fields": {},
        }
    selected = matching_assets[0]
    raw_presence = _asset_field_presence(selected)
    asset_class, asset_class_field, asset_class_source = _text_asset_field(
        selected, "asset_class", "class"
    )
    status, status_field, status_source = _text_asset_field(selected, "status")
    tradable, tradable_field, tradable_source = _bool_asset_field(selected, "tradable")
    orderable, orderable_field, orderable_source = _bool_asset_field(
        selected, "orderable"
    )
    fractional, fractional_field, fractional_source = _bool_asset_field(
        selected, "fractionable", "fractional"
    )
    min_notional, min_notional_field, min_notional_source = _decimal_asset_field(
        selected, "min_order_value", "min_notional"
    )
    min_order_size, min_order_size_field, min_order_size_source = _decimal_asset_field(
        selected, "min_order_size", "min_trade_size"
    )
    min_trade_increment, min_trade_increment_field, min_trade_increment_source = (
        _decimal_asset_field(selected, "min_trade_increment")
    )
    qty_increment, qty_increment_field, qty_increment_source = _decimal_asset_field(
        selected, "qty_increment"
    )
    quantity_increment = None
    quantity_increment_field = ""
    quantity_increment_source = "unavailable"
    for value, field_name, source in (
        (min_trade_increment, min_trade_increment_field, min_trade_increment_source),
        (qty_increment, qty_increment_field, qty_increment_source),
    ):
        if source != "unavailable":
            quantity_increment = value
            quantity_increment_field = field_name
            quantity_increment_source = source
            break
    price_increment, price_increment_field, price_increment_source = _decimal_asset_field(
        selected, "price_increment", "min_price_increment"
    )
    normalized_asset_class = asset_class.lower()
    normalized_status = status.lower()
    ambiguous = len(matching_assets) > 1
    orderability_verified = (
        not ambiguous
        and normalized_asset_class in {"crypto", ""}
        and normalized_status in {"active", ""}
        and tradable is True
        and orderable is not False
    )
    orderability_status = (
        "ambiguous"
        if ambiguous
        or tradable_source in {"unavailable", "ambiguous"}
        or status_source == "ambiguous"
        or orderable_source == "ambiguous"
        else "verified"
        if orderability_verified
        else "blocked"
    )
    field_sources = {
        "orderability": "ambiguous" if orderability_status == "ambiguous" else "broker_observed",
        "asset_class": asset_class_source,
        "status": status_source,
        "tradable": tradable_source,
        "orderable": orderable_source,
        "fractional": fractional_source,
        "min_notional": min_notional_source,
        "min_order_size": min_order_size_source,
        "min_trade_increment": min_trade_increment_source,
        "qty_increment": qty_increment_source,
        "quantity_increment": quantity_increment_source,
        "price_increment": price_increment_source,
    }
    return {
        "status": orderability_status,
        "symbol": symbol,
        "asset_found": True,
        "matching_asset_count": len(matching_assets),
        "asset_class": normalized_asset_class or "unknown",
        "asset_class_field": asset_class_field,
        "asset_status": normalized_status or "unknown",
        "status_field": status_field,
        "tradable": tradable,
        "tradable_field": tradable_field,
        "orderable": orderable,
        "orderable_field": orderable_field,
        "fractional": fractional,
        "fractional_field": fractional_field,
        "orderability_verified": orderability_verified,
        "min_notional_verified": (
            min_notional_source == "broker_observed"
            and min_notional is not None
            and min_notional > Decimal("0")
        ),
        "min_order_size_verified": (
            min_order_size_source == "broker_observed"
            and min_order_size is not None
            and min_order_size > Decimal("0")
        ),
        "quantity_increment_verified": (
            quantity_increment_source == "broker_observed"
            and quantity_increment is not None
            and quantity_increment > Decimal("0")
        ),
        "min_notional": min_notional,
        "min_notional_field": min_notional_field,
        "min_notional_source": min_notional_source,
        "min_order_size": min_order_size,
        "min_order_size_field": min_order_size_field,
        "min_order_size_source": min_order_size_source,
        "min_trade_increment": min_trade_increment,
        "min_trade_increment_field": min_trade_increment_field,
        "min_trade_increment_source": min_trade_increment_source,
        "qty_increment": qty_increment,
        "qty_increment_field": qty_increment_field,
        "qty_increment_source": qty_increment_source,
        "quantity_increment": quantity_increment,
        "quantity_increment_field": quantity_increment_field,
        "quantity_increment_source": quantity_increment_source,
        "price_increment": price_increment,
        "price_increment_field": price_increment_field,
        "price_increment_source": price_increment_source,
        "broker_observed": True,
        "basis": "broker_crypto_asset_metadata",
        "raw_field_presence": raw_presence,
        "field_sources": field_sources,
        "normalized_orderability_fields": {
            "asset_class": normalized_asset_class or "",
            "status": normalized_status or "",
            "tradable": tradable,
            "orderable": orderable,
            "fractional": fractional,
            "min_notional": min_notional,
            "min_order_size": min_order_size,
            "min_trade_increment": min_trade_increment,
            "qty_increment": qty_increment,
            "quantity_increment": quantity_increment,
            "price_increment": price_increment,
        },
    }


def _source_for_latest_price_basis(basis_text: str, broker_observed: bool) -> str:
    if broker_observed:
        return "broker_observed"
    normalized = basis_text.lower()
    if "provider_observed" in normalized:
        return "provider_observed"
    if "local_replay" in normalized:
        return "local_replay"
    if basis_text:
        return "deterministic_fixture"
    return "unavailable"


def _price_source_acceptability(status: str, source: str) -> str:
    if status != "passed":
        return "blocked_price_check_failed"
    if source == "broker_observed":
        return "accepted_broker_observed"
    if source == "provider_observed":
        return "accepted_provider_observed"
    if source in {"deterministic_fixture", "local_replay"}:
        return "accepted_readiness_only_preview"
    return "blocked_unacceptable_source"


def _latest_price_packet_fields(price_evidence: Mapping[str, object]) -> dict[str, object]:
    return {
        "latest_price_value": _evidence_decimal_text(price_evidence.get("latest_price_value")),
        "latest_price_source": _text(price_evidence.get("latest_price_source")),
        "latest_price_observed_at": _text(price_evidence.get("latest_price_observed_at")),
        "latest_price_age_seconds": _text(price_evidence.get("latest_price_age_seconds")),
        "latest_price_symbol": _text(price_evidence.get("latest_price_symbol")),
        "latest_price_bid": _evidence_decimal_text(price_evidence.get("latest_price_bid")),
        "latest_price_ask": _evidence_decimal_text(price_evidence.get("latest_price_ask")),
        "latest_price_mid": _evidence_decimal_text(price_evidence.get("latest_price_mid")),
        "latest_price_last": _evidence_decimal_text(price_evidence.get("latest_price_last")),
        "latest_price_basis": _text(price_evidence.get("latest_price_basis")),
        "latest_price_freshness_status": _text(
            price_evidence.get("latest_price_freshness_status")
        ),
        "latest_price_source_acceptability": _text(
            price_evidence.get("latest_price_source_acceptability")
        ),
        "price_used_for_quantity": _evidence_decimal_text(
            price_evidence.get("price_used_for_quantity")
        ),
        "price_used_for_min_notional_derivation": _evidence_decimal_text(
            price_evidence.get("price_used_for_min_notional_derivation")
        ),
        "price_evidence_status": _text(price_evidence.get("price_evidence_status")),
        "price_evidence_blocker": _text(price_evidence.get("price_evidence_blocker")),
    }


def _age_seconds_text(observed_at: datetime | None, as_of: datetime | None) -> str:
    if observed_at is None or as_of is None:
        return ""
    seconds = (as_of - observed_at).total_seconds()
    if seconds == int(seconds):
        return str(int(seconds))
    return format(Decimal(str(seconds)).quantize(Decimal("0.001")).normalize(), "f")


def _latest_price_freshness(
    *,
    latest_price: Decimal | None,
    observed_at: datetime | None,
    as_of: datetime | None,
    max_age: timedelta = BROKER_OBSERVED_PRICE_MAX_AGE,
) -> tuple[str, str, str]:
    if latest_price is None or latest_price <= Decimal("0"):
        return "unavailable", "broker_latest_price_missing", ""
    if observed_at is None:
        return "missing_timestamp", "broker_latest_price_timestamp_missing", ""
    if as_of is None:
        return "missing_timestamp", "broker_latest_price_timestamp_missing", ""
    age_seconds = (as_of - observed_at).total_seconds()
    if age_seconds < 0 or age_seconds > max_age.total_seconds():
        return "stale", "broker_latest_price_stale", _age_seconds_text(observed_at, as_of)
    return "fresh", "", _age_seconds_text(observed_at, as_of)


def _latest_price_evidence(
    *,
    selected_symbol: str,
    source: str,
    basis: str,
    as_of: datetime | None,
    latest_price: Decimal | None,
    observed_at: object,
    bid: Decimal | None = None,
    ask: Decimal | None = None,
    mid: Decimal | None = None,
    last: Decimal | None = None,
    raw_symbol: str = "",
    blocker_code: str = "",
    freshness_status: str = "",
) -> dict[str, object]:
    normalized_source = source if source in LATEST_PRICE_SOURCES else "ambiguous"
    observed_at_value = _datetime_or_none(observed_at)
    symbol = _text(raw_symbol) or selected_symbol
    normalized_selected = _normalize_broker_symbol(selected_symbol)
    normalized_symbol = _normalize_broker_symbol(symbol)
    symbol_mismatch = bool(
        selected_symbol and symbol and normalized_symbol != normalized_selected
    )
    if normalized_source == "ambiguous" and not blocker_code:
        blocker_code = "broker_latest_price_ambiguous"
    if symbol_mismatch and not blocker_code:
        blocker_code = "broker_latest_price_symbol_mismatch"

    computed_freshness, freshness_blocker, age_seconds = _latest_price_freshness(
        latest_price=latest_price,
        observed_at=observed_at_value,
        as_of=as_of,
    )
    resolved_freshness = freshness_status or computed_freshness
    if not blocker_code:
        blocker_code = freshness_blocker
    if blocker_code in {
        "broker_quote_bid_ask_invalid",
        "broker_trade_price_invalid",
        "broker_bar_close_invalid",
    }:
        timestamp_freshness, _timestamp_blocker, timestamp_age_seconds = (
            _latest_price_freshness(
                latest_price=Decimal("1"),
                observed_at=observed_at_value,
                as_of=as_of,
            )
        )
        resolved_freshness = timestamp_freshness
        age_seconds = timestamp_age_seconds
    if blocker_code == "broker_latest_price_ambiguous":
        resolved_freshness = "ambiguous"
    if normalized_source == "unavailable":
        resolved_freshness = "unavailable"
    status = "blocked" if blocker_code else "passed"
    acceptability = _price_source_acceptability(status, normalized_source)
    observed_at_text = "" if observed_at_value is None else observed_at_value.isoformat()
    accepted_full_readiness = (
        normalized_source in OBSERVED_LATEST_PRICE_SOURCES
        and resolved_freshness == "fresh"
        and status == "passed"
    )
    accepted_readiness_only = (
        normalized_source in READINESS_ONLY_LATEST_PRICE_SOURCES
        and resolved_freshness == "fresh"
        and status == "passed"
    )
    price_for_use = latest_price if status == "passed" else None
    return {
        "status": status,
        "source": normalized_source,
        "price_source_acceptability": acceptability,
        "basis": basis,
        "latest_price": latest_price,
        "latest_price_value": latest_price,
        "latest_price_source": normalized_source,
        "latest_price_observed_at": observed_at_text,
        "latest_price_age_seconds": age_seconds,
        "latest_price_symbol": symbol,
        "latest_price_bid": bid,
        "latest_price_ask": ask,
        "latest_price_mid": mid,
        "latest_price_last": last,
        "latest_price_basis": basis,
        "latest_price_freshness_status": resolved_freshness,
        "latest_price_source_acceptability": acceptability,
        "price_used_for_quantity": price_for_use,
        "price_used_for_min_notional_derivation": price_for_use,
        "price_evidence_status": status,
        "price_evidence_blocker": blocker_code,
        "latest_price_timestamp": observed_at_text,
        "as_of": "" if as_of is None else as_of.isoformat(),
        "max_age_seconds": str(int(BROKER_OBSERVED_PRICE_MAX_AGE.total_seconds())),
        "stale_after": ""
        if as_of is None
        else (as_of - BROKER_OBSERVED_PRICE_MAX_AGE).isoformat(),
        "missing": latest_price is None or latest_price <= Decimal("0"),
        "stale": resolved_freshness == "stale",
        "broker_observed": normalized_source == "broker_observed",
        "provider_observed": normalized_source == "provider_observed",
        "accepted_for_broker_observed_readiness": (
            accepted_full_readiness or accepted_readiness_only
        ),
        "accepted_for_full_broker_observed_readiness": accepted_full_readiness,
        "accepted_for_readiness_only_preview": accepted_readiness_only,
        "symbol_mismatch": symbol_mismatch,
        "blocker_code": blocker_code,
    }


def _broker_observed_price_evidence(
    fixture_readiness: Mapping[str, object],
) -> dict[str, object]:
    basis = _mapping(fixture_readiness.get("latest_price_basis"))
    latest_check = _mapping(
        basis.get("latest_price_check")
        or fixture_readiness.get("stale_missing_price_policy_result")
    )
    basis_text = _text(basis.get("basis"))
    source = _source_for_latest_price_basis(
        basis_text,
        basis.get("broker_observed") is True,
    )
    latest_price = _first_decimal(
        fixture_readiness.get("latest_price"),
        latest_check.get("latest_price"),
    )
    observed_at = latest_check.get(
        "latest_price_timestamp",
        _mapping(fixture_readiness.get("latest_price_basis")).get(
            "latest_price_timestamp"
        ),
    )
    as_of = _datetime_or_none(latest_check.get("as_of", fixture_readiness.get("as_of")))
    evidence = _latest_price_evidence(
        selected_symbol=_text(fixture_readiness.get("symbol")),
        source=source,
        basis=basis_text or "offline_fixture_latest_bar_close",
        as_of=as_of,
        latest_price=latest_price,
        observed_at=observed_at,
        raw_symbol=_text(fixture_readiness.get("symbol")),
    )
    if latest_check.get("missing") is True:
        evidence.update(
            {
                "status": "blocked",
                "price_evidence_status": "blocked",
                "latest_price_freshness_status": "unavailable",
                "price_evidence_blocker": "broker_latest_price_missing",
                "blocker_code": "broker_latest_price_missing",
                "price_source_acceptability": "blocked_price_check_failed",
                "latest_price_source_acceptability": "blocked_price_check_failed",
                "accepted_for_broker_observed_readiness": False,
                "accepted_for_full_broker_observed_readiness": False,
                "accepted_for_readiness_only_preview": False,
            }
        )
    elif latest_check.get("stale") is True and not _text(evidence.get("blocker_code")):
        evidence.update(
            {
                "status": "blocked",
                "price_evidence_status": "blocked",
                "latest_price_freshness_status": "stale",
                "price_evidence_blocker": "broker_latest_price_stale",
                "blocker_code": "broker_latest_price_stale",
                "price_source_acceptability": "blocked_price_check_failed",
                "latest_price_source_acceptability": "blocked_price_check_failed",
                "price_used_for_quantity": None,
                "price_used_for_min_notional_derivation": None,
                "accepted_for_broker_observed_readiness": False,
                "accepted_for_full_broker_observed_readiness": False,
                "accepted_for_readiness_only_preview": False,
            }
        )
    return evidence


def _broker_observed_orderability_check(
    asset_summary: Mapping[str, object],
) -> dict[str, object]:
    if asset_summary.get("asset_found") is not True:
        return {
            "status": "blocked",
            "verified": False,
            "source": "unavailable",
            "blocker_code": "broker_orderability_metadata_missing",
        }
    status = _text(asset_summary.get("status"))
    if status == "ambiguous":
        return {
            "status": "blocked",
            "verified": False,
            "source": "ambiguous",
            "blocker_code": "broker_orderability_metadata_ambiguous",
        }
    verified = asset_summary.get("orderability_verified") is True
    return {
        "status": "passed" if verified else "blocked",
        "verified": verified,
        "source": "broker_observed",
        "blocker_code": "" if verified else "broker_orderability_metadata_ambiguous",
        "asset_status": asset_summary.get("asset_status"),
        "tradable": asset_summary.get("tradable"),
        "orderable": asset_summary.get("orderable"),
        "fractional": asset_summary.get("fractional"),
    }


def _broker_observed_min_notional_check(
    *,
    intended_notional: Decimal | None,
    estimated_quantity: Decimal | None,
    asset_summary: Mapping[str, object],
    price_check: Mapping[str, object],
) -> dict[str, object]:
    min_notional = _first_decimal(asset_summary.get("min_notional"))
    source = _text(asset_summary.get("min_notional_source")) or "unavailable"
    direct_available = (
        source == "broker_observed"
        and min_notional is not None
        and min_notional > Decimal("0")
    )
    price = _first_decimal(price_check.get("latest_price"))
    price_source = _text(price_check.get("source")) or "unavailable"
    price_acceptability = (
        _text(price_check.get("price_source_acceptability"))
        or _price_source_acceptability(_text(price_check.get("status")), price_source)
    )
    min_order_size = _first_decimal(asset_summary.get("min_order_size"))
    min_order_size_source = _text(asset_summary.get("min_order_size_source")) or "unavailable"
    quantity_increment = _first_decimal(asset_summary.get("quantity_increment"))
    quantity_increment_source = (
        _text(asset_summary.get("quantity_increment_source")) or "unavailable"
    )
    derived_min_notional = (
        min_order_size * price
        if min_order_size is not None
        and min_order_size > Decimal("0")
        and price is not None
        and price > Decimal("0")
        else None
    )
    derived_sources = (
        f"min_order_size={min_order_size_source};"
        f"quantity_increment={quantity_increment_source};"
        f"price={price_source}"
    )
    derived_formula = "broker_observed_min_order_size * selected_price"
    base = {
        "direct_min_notional_available": direct_available,
        "direct_min_notional_source": source,
        "derived_min_notional_available": False,
        "derived_min_notional_value": derived_min_notional,
        "derived_min_notional_formula": derived_formula if derived_min_notional is not None else "",
        "derived_min_notional_sources": derived_sources,
        "derived_min_notional_check_status": "not_applicable",
        "min_notional_equivalence_basis": (
            "direct_broker_min_notional" if direct_available else "none"
        ),
        "price_source_for_derivation": price_source,
        "price_source_acceptability": price_acceptability,
        "final_feasibility_basis": (
            "direct_broker_min_notional" if direct_available else "blocked_no_min_notional_evidence"
        ),
    }
    if direct_available:
        if intended_notional is None or intended_notional < min_notional:
            return {
                **base,
                "status": "blocked",
                "verified": False,
                "source": source,
                "intended_notional": intended_notional,
                "min_notional": min_notional,
                "blocker_code": "broker_intended_notional_below_min_notional",
                "final_feasibility_basis": "blocked_direct_min_notional_exceeds_intended_notional",
            }
        return {
            **base,
            "status": "passed",
            "verified": True,
            "source": source,
            "intended_notional": intended_notional,
            "min_notional": min_notional,
            "blocker_code": "",
        }
    if source not in {"", "unavailable"}:
        blocker = (
            "broker_min_notional_field_missing"
            if source in {"", "unavailable"}
            else "broker_min_notional_not_verified"
        )
        return {
            "status": "blocked",
            "verified": False,
            "source": source,
            "intended_notional": intended_notional,
            "min_notional": min_notional,
            **base,
            "derived_min_notional_check_status": "blocked",
            "blocker_code": blocker,
        }
    if (
        min_order_size_source != "broker_observed"
        or min_order_size is None
        or min_order_size <= Decimal("0")
        or quantity_increment_source != "broker_observed"
        or quantity_increment is None
        or quantity_increment <= Decimal("0")
    ):
        return {
            **base,
            "status": "blocked",
            "verified": False,
            "source": "unavailable",
            "intended_notional": intended_notional,
            "min_notional": None,
            "derived_min_notional_check_status": "blocked",
            "final_feasibility_basis": "blocked_missing_min_order_size_or_increment",
            "blocker_code": "broker_min_order_size_or_increment_missing_for_derivation",
        }
    aligned, remainder = _quantity_increment_aligned(estimated_quantity, quantity_increment)
    if aligned is not True:
        return {
            **base,
            "status": "blocked",
            "verified": False,
            "source": "broker_observed_equivalent",
            "intended_notional": intended_notional,
            "min_notional": derived_min_notional,
            "derived_min_notional_check_status": "blocked",
            "quantity_increment_remainder": remainder,
            "final_feasibility_basis": "blocked_quantity_increment_alignment_failed",
            "blocker_code": "broker_quantity_increment_alignment_failed",
        }
    if estimated_quantity is None or estimated_quantity < min_order_size:
        return {
            **base,
            "status": "blocked",
            "verified": False,
            "source": "broker_observed_equivalent",
            "intended_notional": intended_notional,
            "min_notional": derived_min_notional,
            "derived_min_notional_check_status": "blocked",
            "final_feasibility_basis": "blocked_quantity_below_min_order_size",
            "blocker_code": "broker_estimated_quantity_below_min_order_size",
        }
    if price_acceptability not in {
        "accepted_broker_observed",
        "accepted_provider_observed",
        "accepted_readiness_only_preview",
    }:
        return {
            **base,
            "status": "blocked",
            "verified": False,
            "source": "broker_observed_equivalent",
            "intended_notional": intended_notional,
            "min_notional": derived_min_notional,
            "derived_min_notional_check_status": "blocked",
            "final_feasibility_basis": "blocked_price_source_not_acceptable",
            "blocker_code": "broker_price_source_not_acceptable_for_equivalence",
        }
    if derived_min_notional is None:
        return {
            **base,
            "status": "blocked",
            "verified": False,
            "source": "broker_observed_equivalent",
            "intended_notional": intended_notional,
            "min_notional": None,
            "derived_min_notional_check_status": "blocked",
            "blocker_code": "broker_min_notional_equivalent_not_available",
        }
    if intended_notional is None or intended_notional < derived_min_notional:
        return {
            **base,
            "status": "blocked",
            "verified": False,
            "source": "broker_observed_equivalent",
            "intended_notional": intended_notional,
            "min_notional": derived_min_notional,
            "derived_min_notional_available": True,
            "derived_min_notional_check_status": "blocked",
            "min_notional_equivalence_basis": "derived_from_broker_min_order_size_and_selected_price",
            "final_feasibility_basis": "blocked_derived_min_notional_exceeds_intended_notional",
            "blocker_code": "broker_derived_min_notional_exceeds_intended_notional",
        }
    return {
        **base,
        "status": "passed",
        "verified": True,
        "source": "broker_observed_equivalent",
        "intended_notional": intended_notional,
        "min_notional": derived_min_notional,
        "derived_min_notional_available": True,
        "derived_min_notional_check_status": "passed",
        "min_notional_equivalence_basis": "derived_from_broker_min_order_size_and_selected_price",
        "final_feasibility_basis": (
            "derived_min_notional_equivalent_with_observed_price"
            if price_source in OBSERVED_LATEST_PRICE_SOURCES
            else "derived_min_notional_equivalent_with_readiness_only_price"
        ),
        "blocker_code": "",
    }


def _broker_observed_min_order_size_check(
    *,
    estimated_quantity: Decimal | None,
    asset_summary: Mapping[str, object],
) -> dict[str, object]:
    min_order_size = _first_decimal(asset_summary.get("min_order_size"))
    source = _text(asset_summary.get("min_order_size_source")) or "unavailable"
    if source != "broker_observed" or min_order_size is None or min_order_size <= Decimal("0"):
        return {
            "status": "blocked",
            "verified": False,
            "source": source,
            "estimated_quantity": estimated_quantity,
            "min_order_size": min_order_size,
            "blocker_code": "broker_min_order_size_field_missing",
        }
    if estimated_quantity is None or estimated_quantity < min_order_size:
        return {
            "status": "blocked",
            "verified": False,
            "source": source,
            "estimated_quantity": estimated_quantity,
            "min_order_size": min_order_size,
            "blocker_code": "broker_estimated_quantity_below_min_order_size",
        }
    return {
        "status": "passed",
        "verified": True,
        "source": source,
        "estimated_quantity": estimated_quantity,
        "min_order_size": min_order_size,
        "blocker_code": "",
    }


def _broker_observed_quantity_increment_check(
    *,
    estimated_quantity: Decimal | None,
    asset_summary: Mapping[str, object],
) -> dict[str, object]:
    quantity_increment = _first_decimal(asset_summary.get("quantity_increment"))
    source = _text(asset_summary.get("quantity_increment_source")) or "unavailable"
    if (
        source != "broker_observed"
        or quantity_increment is None
        or quantity_increment <= Decimal("0")
    ):
        return {
            "status": "blocked",
            "verified": False,
            "source": source,
            "estimated_quantity": estimated_quantity,
            "quantity_increment": quantity_increment,
            "remainder": None,
            "blocker_code": "broker_qty_increment_field_missing",
        }
    aligned, remainder = _quantity_increment_aligned(
        estimated_quantity,
        quantity_increment,
    )
    if aligned is not True:
        return {
            "status": "blocked",
            "verified": False,
            "source": source,
            "estimated_quantity": estimated_quantity,
            "quantity_increment": quantity_increment,
            "remainder": remainder,
            "blocker_code": "broker_estimated_quantity_not_increment_aligned",
        }
    return {
        "status": "passed",
        "verified": True,
        "source": source,
        "estimated_quantity": estimated_quantity,
        "quantity_increment": quantity_increment,
        "remainder": remainder,
        "blocker_code": "",
    }


def _quantity_increment_aligned(
    estimated_quantity: Decimal | None,
    quantity_increment: Decimal | None,
) -> tuple[bool | None, Decimal | None]:
    if (
        estimated_quantity is None
        or quantity_increment is None
        or quantity_increment <= Decimal("0")
    ):
        return None, None
    try:
        remainder = estimated_quantity % quantity_increment
    except Exception:
        return None, None
    return remainder == Decimal("0"), remainder


def _broker_observed_feasibility_checks(
    *,
    fixture_readiness: Mapping[str, object],
    asset_summary: Mapping[str, object],
    price_evidence: Mapping[str, object],
    intended_notional: Decimal | None,
    estimated_quantity: Decimal | None,
) -> dict[str, dict[str, object]]:
    del fixture_readiness
    price = dict(price_evidence)
    min_order_size = _broker_observed_min_order_size_check(
        estimated_quantity=estimated_quantity,
        asset_summary=asset_summary,
    )
    quantity_increment = _broker_observed_quantity_increment_check(
        estimated_quantity=estimated_quantity,
        asset_summary=asset_summary,
    )
    return {
        "orderability": _broker_observed_orderability_check(asset_summary),
        "price": price,
        "min_notional": _broker_observed_min_notional_check(
            intended_notional=intended_notional,
            estimated_quantity=estimated_quantity,
            asset_summary=asset_summary,
            price_check=price,
        ),
        "min_order_size": min_order_size,
        "quantity_increment": quantity_increment,
    }


def _broker_observed_blockers(
    *,
    fixture_decision: str,
    account_status: str,
    trading_blocked: bool | None,
    account_blocked: bool | None,
    positions_summary: Mapping[str, object],
    open_orders_summary: Mapping[str, object],
    asset_summary: Mapping[str, object],
    checks: Mapping[str, Mapping[str, object]],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if fixture_decision != "fixture_ready_preview":
        blockers.append("fixture_readiness_not_ready")
    if account_status and account_status.lower() not in {"active", "account_active"}:
        blockers.append("paper_account_not_active")
    if trading_blocked is True:
        blockers.append("paper_trading_blocked")
    if account_blocked is True:
        blockers.append("paper_account_blocked")
    if positions_summary.get("unexpected_preexisting_position") is True:
        blockers.append("unexpected_preexisting_position")
    if open_orders_summary.get("open_order_present") is True:
        blockers.append("open_order_present")
    orderability_blocker = _text(_mapping(checks.get("orderability")).get("blocker_code"))
    if orderability_blocker:
        blockers.append(orderability_blocker)
    price_blocker = _text(_mapping(checks.get("price")).get("blocker_code"))
    if price_blocker:
        blockers.append(price_blocker)
    for check_name in ("min_notional", "min_order_size", "quantity_increment"):
        blocker = _text(_mapping(checks.get(check_name)).get("blocker_code"))
        if blocker:
            blockers.append(blocker)
    return _dedupe(blockers)


def _empty_observed_summary(status: str) -> dict[str, object]:
    return {"status": status, "broker_observed": False}


def _field(obj: object, name: str) -> object:
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)


def _optional_bool(value: object) -> bool | None:
    if type(value) is bool:
        return value
    text = _text(value).lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _normalize_broker_symbol(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def _safe_broker_observed_error(exc: Exception) -> str:
    text = str(exc)
    for sentinel in FORBIDDEN_SENTINELS:
        text = text.replace(sentinel, "<redacted>")
    return text[:240]


def _offline_fixture_bars(
    universe: Sequence[str],
    as_of: datetime,
    scenario: Scenario = DEFAULT_SCENARIO,
) -> dict[str, tuple[Bar, ...]]:
    bars: dict[str, tuple[Bar, ...]] = {}
    for symbol in universe:
        normalized = normalize_crypto_symbol(symbol)
        if scenario == "risk_off":
            bars[normalized] = _fixture_series(
                normalized,
                as_of,
                count=80,
                start="220" if normalized == "BTCUSD" else "120",
                step="-0.90",
            )
            continue
        if scenario == "all_blocked":
            bars[normalized] = _fixture_series(
                normalized,
                as_of,
                count=80,
                start="100",
                step="0",
            )
            continue
        if scenario == "bad_data":
            bars[normalized] = _fixture_series(
                normalized,
                as_of,
                count=12,
                start="100",
                step="0",
            )
            continue
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
    latest_bar = usable[-1] if usable else None
    latest_price = None if latest_bar is None else latest_bar.close
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
            "latest_price_timestamp": None if latest_bar is None else latest_bar.timestamp,
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
    portfolio: PortfolioState,
    scenario: Scenario,
) -> DemoPlanMaterial:
    selected = _select_candidate(candidates)
    duplicate_ids = set(existing_client_order_ids)
    position = _first_open_position(portfolio)
    data_blocked = _candidate_data_blocked(candidates)
    blockers: list[str] = []

    if position is not None:
        if selected is not None and scenario == "risk_on":
            return _empty_plan_material(
                planned_action="hold_existing_position_risk_on",
                blockers=(),
                selected_candidate=selected,
            )
        if scenario == "risk_off" and not data_blocked:
            return _build_exit_plan_material(
                position=position,
                bars_by_symbol=bars_by_symbol,
                run_id=run_id,
                as_of=as_of,
                git_short_sha=git_short_sha,
                existing_client_order_ids=duplicate_ids,
                portfolio=portfolio,
            )
        blocker = "data_quality_block" if data_blocked else "all_candidates_failed_gates"
        return _empty_plan_material(
            planned_action="blocked_no_trade",
            blockers=(blocker,),
            selected_candidate=selected,
        )

    if selected is None:
        if scenario == "risk_off" and not data_blocked:
            return _empty_plan_material(
                planned_action="hold_no_position_risk_off",
                blockers=(),
                selected_candidate=None,
            )
        blockers.append("data_quality_block" if data_blocked else "all_candidates_failed_gates")
        return _empty_plan_material(
            planned_action="blocked_no_trade",
            blockers=tuple(blockers),
            selected_candidate=None,
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
        planned_action="simulated_buy",
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


def _empty_plan_material(
    *,
    planned_action: str,
    blockers: Sequence[str],
    selected_candidate: DemoCandidate | None,
) -> DemoPlanMaterial:
    empty_plan = build_execution_plan(())
    return DemoPlanMaterial(
        planned_action=planned_action,
        selected_candidate=selected_candidate,
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
        blockers=tuple(_dedupe(blockers)),
    )


def _build_exit_plan_material(
    *,
    position: Position,
    bars_by_symbol: Mapping[str, tuple[Bar, ...]],
    run_id: str,
    as_of: datetime,
    git_short_sha: str,
    existing_client_order_ids: set[str],
    portfolio: PortfolioState,
) -> DemoPlanMaterial:
    blockers: list[str] = []
    bars = tuple(bars_by_symbol.get(position.symbol, ()))
    usable = tuple(bar for bar in sorted(bars, key=lambda item: item.timestamp) if bar.timestamp <= as_of)
    if not usable:
        return _empty_plan_material(
            planned_action="blocked_no_trade",
            blockers=("latest_price_missing",),
            selected_candidate=None,
        )
    latest_price = usable[-1].close
    strategy_id = f"{position.symbol.lower()}_risk_off_exit_demo"
    client_order_id = _client_order_id(
        run_id=run_id,
        symbol=position.symbol,
        side="sell",
        as_of=as_of,
        strategy_id=strategy_id,
        git_short_sha=git_short_sha,
    )
    if client_order_id in existing_client_order_ids:
        blockers.append("duplicate_client_order_id")
    quote = Quote(
        symbol=position.symbol,
        timestamp=as_of,
        bid=latest_price * Decimal("0.999"),
        ask=latest_price,
    )
    order = ProposedOrder(
        symbol=position.symbol,
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=position.quantity,
        client_order_id=client_order_id,
    )
    risk = RiskEngine(
        RiskConfig(
            max_order_notional=MAX_TOTAL_DEMO_EXPOSURE,
            allow_short=False,
            allow_fractional_shares=True,
            max_positions=MAX_OPEN_EXPOSURE_SYMBOLS,
        )
    ).check(order, portfolio, quote)
    if not risk.allowed:
        blockers.append(risk.reason or "risk_rejected")
    risk_passed = risk.allowed and not blockers
    screener_eval = ScreenerSignalEvaluation(
        symbol=position.symbol,
        previous_bar=usable[-1],
        quote=quote,
        order=order if risk_passed else None,
    )
    risk_eval = SignalRiskEvaluation(
        symbol=position.symbol,
        previous_bar=screener_eval.previous_bar,
        quote=screener_eval.quote,
        order=order if risk_passed else None,
        risk=risk,
        status="risk_approved" if risk_passed else "risk_rejected",
    )
    intents = build_execution_intents_from_risk_approved((risk_eval,))
    plan = build_execution_plan(intents)
    policy = apply_max_intents_execution_planning_policy(
        plan,
        MaxAcceptedIntentsPolicyConfig(max_accepted_intents=1),
    )
    return DemoPlanMaterial(
        planned_action="simulated_exit",
        selected_candidate=None,
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


def _first_open_position(portfolio: PortfolioState) -> Position | None:
    open_positions = [position for position in portfolio.positions if not position.is_flat]
    if not open_positions:
        return None
    return sorted(open_positions, key=lambda item: item.symbol)[0]


def _candidate_data_blocked(candidates: Sequence[DemoCandidate]) -> bool:
    if not candidates:
        return True
    return all(
        not candidate.data_gate_passed
        or "insufficient_history" in candidate.blockers
        or "latest_price_missing" in candidate.blockers
        for candidate in candidates
    )


def _plan_events(
    plan_material: DemoPlanMaterial,
    *,
    run_id: str,
    as_of: datetime,
    cycle_index: int,
    cycle_key: str,
) -> list[dict[str, object]]:
    return [
        {
            "event_type": "execution_intent_created",
            "run_id": run_id,
            "cycle_index": cycle_index,
            "cycle_key": cycle_key,
            "timestamp": as_of.isoformat(),
            "planned_action": plan_material.planned_action,
            "intent_count": len(plan_material.execution_intents),
            "client_order_id": plan_material.client_order_id,
        },
        {
            "event_type": "execution_plan_created",
            "run_id": run_id,
            "cycle_index": cycle_index,
            "cycle_key": cycle_key,
            "timestamp": as_of.isoformat(),
            "planned_action": plan_material.planned_action,
            "intent_count": len(plan_material.execution_plan.intents),
            "immutable_pre_broker_plan": True,
        },
        {
            "event_type": "planning_policy_decision",
            "run_id": run_id,
            "cycle_index": cycle_index,
            "cycle_key": cycle_key,
            "timestamp": as_of.isoformat(),
            "planned_action": plan_material.planned_action,
            "accepted_count": len(plan_material.planning_policy.accepted_intents),
            "skipped_count": len(plan_material.planning_policy.skipped_intents),
        },
    ]


def _simbroker_safety(
    *,
    simulation_mutation_occurred: bool,
    broker_read_occurred: bool = False,
    broker_state_observed: bool = False,
    network_used: bool = False,
) -> dict[str, object]:
    return {
        "simulation_or_paper_only": True,
        "not_live_authorized": True,
        "no_real_capital": True,
        "profit_claim": "none",
        "broker_mode": "simulation_broker",
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "simulation_mutation_authorized": True,
        "paper_submit_occurred": False,
        "broker_mutation_occurred": False,
        "simulation_mutation_occurred": simulation_mutation_occurred,
        "broker_read_occurred": broker_read_occurred,
        "broker_state_observed": broker_state_observed,
        "broker_state_mode": (
            "alpaca_paper_read_only_observed"
            if broker_state_observed
            else "offline_simulation"
        ),
        "market_data_observed": False,
        "orderability_observed": False,
        "network_used": network_used,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "live_authorized": False,
    }


def build_no_submit_paper_readiness_packet(
    *,
    run_id: str,
    cycle_index: int,
    as_of: datetime | str,
    selected_candidate: Mapping[str, object] | None,
    execution_intent: Mapping[str, object] | None,
    execution_plan: Mapping[str, object] | None,
    planned_action: str,
    state_reconciliation: Mapping[str, object] | None,
    portfolio_snapshot: Mapping[str, object] | None,
    existing_client_order_ids: Iterable[str] = (),
    open_orders: Sequence[Mapping[str, object]] = (),
    readiness_basis: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build a deterministic no-submit paper-readiness preview packet."""

    as_of_value = _utc_datetime(as_of, "as_of")
    selected = _mapping(selected_candidate)
    intent = _mapping(execution_intent)
    plan = _mapping(execution_plan)
    basis = _mapping(readiness_basis)
    portfolio = _mapping(portfolio_snapshot)
    state = _mapping(state_reconciliation)
    safety = _paper_readiness_safety()
    labels = _paper_readiness_safety_labels()

    symbol = _readiness_symbol(selected, intent, basis)
    side = _readiness_side(intent, basis, planned_action, selected)
    strategy_id = _text(selected.get("strategy_id") or basis.get("strategy_id"))
    client_order_id = _text(intent.get("client_order_id") or basis.get("client_order_id"))
    latest_price = _first_decimal(
        basis.get("latest_price"),
        selected.get("latest_price"),
    )
    latest_price_timestamp = _datetime_or_none(
        basis.get("latest_price_timestamp")
        or _mapping(selected.get("features")).get("latest_price_timestamp")
    )
    price_max_age = _decimal_or_none(basis.get("price_max_age_seconds"))
    max_age_seconds = (
        PAPER_READINESS_PRICE_MAX_AGE.total_seconds()
        if price_max_age is None
        else float(price_max_age)
    )
    stale_after = as_of_value - timedelta(seconds=max_age_seconds)
    price_present = latest_price is not None and latest_price > Decimal("0")
    price_stale = (
        price_present
        and (
            latest_price_timestamp is None
            or latest_price_timestamp < stale_after
            or latest_price_timestamp > as_of_value
        )
    )
    quantity = _first_decimal(
        basis.get("estimated_quantity"),
        basis.get("quantity"),
        intent.get("quantity"),
    )
    if quantity is None and latest_price is not None and latest_price > Decimal("0") and side == "buy":
        quantity = _demo_quantity(latest_price)
    intended_notional = _first_decimal(basis.get("intended_notional"))
    if intended_notional is None and quantity is not None and latest_price is not None:
        intended_notional = quantity * latest_price

    orderability_verified = _strict_true(
        basis.get("orderability_verified", selected.get("orderability_gate_passed"))
    )
    min_notional_verified = _strict_true(
        basis.get("min_notional_verified", selected.get("min_notional_verified"))
    )
    quantity_increment_verified = _strict_true(
        basis.get(
            "quantity_increment_verified",
            basis.get("qty_increment_verified", selected.get("qty_increment_verified")),
        )
    )
    min_notional = (
        _first_decimal(basis.get("min_notional")) or MIN_NOTIONAL
        if min_notional_verified
        else None
    )
    quantity_increment = (
        _first_decimal(basis.get("quantity_increment"), basis.get("qty_increment")) or QTY_INCREMENT
        if quantity_increment_verified
        else None
    )
    max_order_notional = _first_decimal(basis.get("max_order_notional")) or MAX_NOTIONAL_PER_ORDER
    max_total_exposure = _first_decimal(basis.get("max_total_exposure")) or MAX_TOTAL_DEMO_EXPOSURE
    current_exposure = _first_decimal(portfolio.get("gross_exposure")) or Decimal("0")
    projected_total_exposure = _projected_exposure(
        current_exposure=current_exposure,
        intended_notional=intended_notional,
        side=side,
    )

    duplicate_ids = set(_dedupe((*existing_client_order_ids, *_string_sequence(basis.get("seen_client_order_ids")))))
    duplicate_client_order_id = bool(client_order_id and client_order_id in duplicate_ids)
    open_symbol_orders = tuple(
        order for order in open_orders if _open_order_matches_symbol(order, symbol)
    )
    positions = _mapping_sequence(portfolio.get("positions"))
    matching_positions = tuple(
        position for position in positions if _position_matches_symbol(position, symbol)
    )
    preexisting_position_blocked = bool(matching_positions and side != "sell")
    state_status = _text(state.get("status")) or "passed"
    state_passed = state_status == "passed"
    has_selected_or_plan = bool(
        symbol
        and (
            selected
            or intent
            or int(plan.get("intent_count", 0) or 0) > 0
        )
    )

    latest_price_check = {
        "status": "blocked" if not price_present or price_stale else "passed",
        "policy": "latest_price_required_and_not_older_than_offline_fixture_threshold",
        "latest_price": latest_price,
        "latest_price_timestamp": latest_price_timestamp,
        "as_of": as_of_value,
        "max_age_seconds": int(max_age_seconds),
        "stale_after": stale_after,
        "missing": not price_present,
        "stale": bool(price_stale),
        "fresh_market_data_claimed": False,
    }
    orderability_check = {
        "status": "passed" if orderability_verified else "blocked",
        "verified": orderability_verified,
        "basis": _text(basis.get("orderability_basis")) or "deterministic_offline_fixture_symbol_universe",
        "broker_observed": False,
    }
    min_notional_basis = {
        "status": "verified" if min_notional_verified else "missing",
        "verified": min_notional_verified,
        "min_notional": min_notional,
        "basis": _text(basis.get("min_notional_basis")) or "deterministic_demo_fixture",
        "broker_observed": False,
    }
    quantity_increment_basis = {
        "status": "verified" if quantity_increment_verified else "missing",
        "verified": quantity_increment_verified,
        "quantity_increment": quantity_increment,
        "basis": _text(basis.get("quantity_increment_basis")) or "deterministic_demo_fixture",
        "broker_observed": False,
    }
    duplicate_check = {
        "status": "blocked" if duplicate_client_order_id else "passed",
        "client_order_id": client_order_id,
        "duplicate": duplicate_client_order_id,
        "basis": "local_simbroker_seen_client_order_ids_only",
    }
    max_order_check = {
        "status": _cap_status(intended_notional, max_order_notional),
        "intended_notional": intended_notional,
        "max_order_notional": max_order_notional,
    }
    total_exposure_check = {
        "status": _cap_status(projected_total_exposure, max_total_exposure),
        "current_total_exposure": current_exposure,
        "projected_total_exposure": projected_total_exposure,
        "max_total_exposure": max_total_exposure,
    }
    one_open_order_check = {
        "status": "blocked" if open_symbol_orders else "passed",
        "symbol": symbol,
        "open_order_count_for_symbol": len(open_symbol_orders),
        "basis": "local_simbroker_state_only",
    }
    preexisting_position_policy = {
        "status": (
            "blocked"
            if preexisting_position_blocked
            else "allowed_exit"
            if matching_positions and side == "sell"
            else "passed"
        ),
        "symbol": symbol,
        "side": side,
        "matching_position_count": len(matching_positions),
        "policy": "paper_preview_blocks_new_buy_when_local_sim_position_exists",
    }
    state_check = {
        "status": state_status,
        "passed": state_passed,
        "errors": list(_string_sequence(state.get("errors"))),
    }

    blocker_code = _paper_readiness_blocker(
        state_passed=state_passed,
        has_selected_or_plan=has_selected_or_plan,
        price_present=price_present,
        price_stale=bool(price_stale),
        orderability_verified=orderability_verified,
        min_notional_verified=min_notional_verified,
        quantity_increment_verified=quantity_increment_verified,
        max_order_status=_text(max_order_check.get("status")),
        total_exposure_status=_text(total_exposure_check.get("status")),
        duplicate_client_order_id=duplicate_client_order_id,
        open_order_present=bool(open_symbol_orders),
        preexisting_position_blocked=preexisting_position_blocked,
    )
    decision = "fixture_blocked_preview" if blocker_code else "fixture_ready_preview"
    next_operator_action = (
        "operator_review_preview_packet_no_submit"
        if decision == "fixture_ready_preview"
        else "resolve_paper_readiness_blocker_before_any_paper_submit"
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "paper_readiness_packet",
        "run_id": run_id,
        "cycle_index": cycle_index,
        "as_of": as_of_value,
        "symbol": symbol,
        "side": side,
        "strategy_id": strategy_id,
        "client_order_id": client_order_id,
        "planned_action": planned_action,
        "readiness_basis": "fixture",
        "readiness_basis_decision": decision,
        "fixture_readiness_decision": decision,
        "fixture_blocker_code": blocker_code,
        "broker_observed_readiness_decision": "broker_observed_not_attempted",
        "execution_intent_summary": dict(intent),
        "execution_plan_summary": dict(plan),
        "intended_notional": intended_notional,
        "estimated_quantity": quantity,
        "latest_price": latest_price,
        "latest_price_basis": {
            "basis": _text(basis.get("latest_price_basis")) or "offline_fixture_latest_bar_close",
            "market_data_observed": False,
            "broker_observed": False,
            "latest_price_check": latest_price_check,
        },
        "orderability_basis": orderability_check,
        "min_notional_basis": min_notional_basis,
        "quantity_increment_basis": quantity_increment_basis,
        "duplicate_client_order_id_check": duplicate_check,
        "max_order_notional_check": max_order_check,
        "max_total_exposure_check": total_exposure_check,
        "one_open_order_per_symbol_check": one_open_order_check,
        "preexisting_position_policy_result": preexisting_position_policy,
        "stale_missing_price_policy_result": latest_price_check,
        "state_reconciliation_check": state_check,
        "final_readiness_decision": decision,
        "readiness_decision": decision,
        "blocker_code": blocker_code,
        "next_operator_action": next_operator_action,
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "broker_read_occurred": False,
        "broker_state_observed": False,
        "network_used": False,
        "credential_values_exposed": False,
        "safety": safety,
        "safety_labels": list(labels),
        "labels": list(labels),
        "profit_claim": "none",
    }


def _paper_readiness_packet_for_plan(
    *,
    run_id: str,
    cycle_index: int,
    as_of: datetime,
    planned_action: str,
    candidates: Sequence[DemoCandidate],
    plan_material: DemoPlanMaterial,
    state_snapshot: SimBrokerStateSnapshot,
    state_reconciliation: Mapping[str, object],
    existing_client_order_ids: Iterable[str],
) -> dict[str, object]:
    selected = plan_material.selected_candidate or _select_candidate(candidates)
    selected_payload = None if selected is None else selected.to_dict()
    intent_payload = _execution_intent_record(plan_material)
    plan_payload = _execution_plan_record(plan_material.execution_plan)
    latest_timestamp = None
    latest_price = None
    if selected is not None:
        latest_timestamp = _mapping(selected.features).get("latest_price_timestamp")
        latest_price = selected.latest_price
    if latest_price is None and plan_material.quote is not None:
        latest_price = plan_material.quote.ask
        latest_timestamp = plan_material.quote.timestamp
    quantity = None if plan_material.order is None else plan_material.order.quantity
    if quantity is None and latest_price is not None and latest_price > Decimal("0") and planned_action != "simulated_exit":
        quantity = _demo_quantity(latest_price)
    intended_notional = None
    if quantity is not None and latest_price is not None:
        intended_notional = quantity * latest_price
    return build_no_submit_paper_readiness_packet(
        run_id=run_id,
        cycle_index=cycle_index,
        as_of=as_of,
        selected_candidate=selected_payload,
        execution_intent=intent_payload,
        execution_plan=plan_payload,
        planned_action=planned_action,
        state_reconciliation=state_reconciliation,
        portfolio_snapshot=_portfolio_snapshot(state_snapshot.portfolio),
        existing_client_order_ids=existing_client_order_ids,
        open_orders=state_snapshot.open_orders,
        readiness_basis={
            "symbol": "" if selected is None else selected.symbol,
            "side": _plan_material_side(plan_material, planned_action),
            "strategy_id": "" if selected is None else selected.strategy_id,
            "client_order_id": plan_material.client_order_id,
            "latest_price": latest_price,
            "latest_price_timestamp": latest_timestamp,
            "estimated_quantity": quantity,
            "intended_notional": intended_notional,
            "latest_price_basis": "offline_fixture_latest_bar_close",
            "orderability_basis": "deterministic_offline_fixture_symbol_universe",
            "orderability_verified": bool(selected is not None and selected.orderability_gate_passed)
            or bool(intent_payload),
            "min_notional_basis": "deterministic_demo_fixture",
            "min_notional_verified": bool(selected is not None and selected.min_notional_verified)
            or bool(intent_payload),
            "quantity_increment_basis": "deterministic_demo_fixture",
            "quantity_increment_verified": bool(
                selected is not None and selected.qty_increment_verified
            )
            or bool(intent_payload),
            "min_notional": MIN_NOTIONAL,
            "quantity_increment": QTY_INCREMENT,
            "max_order_notional": MAX_NOTIONAL_PER_ORDER,
            "max_total_exposure": MAX_TOTAL_DEMO_EXPOSURE,
        },
    )


def _paper_readiness_safety() -> dict[str, object]:
    return {
        "simulation_or_paper_only": True,
        "not_live_authorized": True,
        "no_real_capital": True,
        "profit_claim": "none",
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "broker_read_occurred": False,
        "broker_state_observed": False,
        "network_used": False,
        "credential_values_exposed": False,
        "live_authorized": False,
        "live_endpoint_touched": False,
    }


def _paper_readiness_safety_labels() -> tuple[str, ...]:
    return (
        *REQUIRED_SAFETY_LABELS,
        "paper_submit_occurred=false",
        "broker_mutation_occurred=false",
        "broker_read_occurred=false",
        "broker_state_observed=false",
        "network_used=false",
        "live_authorized=false",
        "live_endpoint_touched=false",
    )


def _paper_readiness_blocker(
    *,
    state_passed: bool,
    has_selected_or_plan: bool,
    price_present: bool,
    price_stale: bool,
    orderability_verified: bool,
    min_notional_verified: bool,
    quantity_increment_verified: bool,
    max_order_status: str,
    total_exposure_status: str,
    duplicate_client_order_id: bool,
    open_order_present: bool,
    preexisting_position_blocked: bool,
) -> str:
    if not state_passed:
        return "blocked_sim_state_reconciliation_failed"
    if not has_selected_or_plan:
        return "blocked_no_selected_candidate"
    if not price_present:
        return "blocked_missing_price"
    if price_stale:
        return "blocked_stale_price"
    if not orderability_verified:
        return "blocked_missing_orderability"
    if not min_notional_verified or not quantity_increment_verified:
        return "blocked_min_notional_or_increment_not_verified"
    if max_order_status == "blocked":
        return "blocked_exceeds_max_notional"
    if total_exposure_status == "blocked":
        return "blocked_exceeds_total_exposure"
    if duplicate_client_order_id:
        return "blocked_duplicate_client_order_id"
    if open_order_present:
        return "blocked_open_order_present"
    if preexisting_position_blocked:
        return "blocked_unexpected_preexisting_position"
    return ""


def _readiness_symbol(
    selected: Mapping[str, object],
    intent: Mapping[str, object],
    basis: Mapping[str, object],
) -> str:
    return _text(intent.get("symbol") or selected.get("symbol") or basis.get("symbol"))


def _readiness_side(
    intent: Mapping[str, object],
    basis: Mapping[str, object],
    planned_action: str,
    selected: Mapping[str, object],
) -> str:
    side = _text(intent.get("side") or basis.get("side"))
    if side:
        return side
    if planned_action == "simulated_exit":
        return "sell"
    if selected or planned_action in {"simulated_buy", "hold_existing_position_risk_on"}:
        return "buy"
    return ""


def _plan_material_side(plan_material: DemoPlanMaterial, planned_action: str) -> str:
    if plan_material.order is not None:
        return plan_material.order.side.value
    if planned_action == "simulated_exit":
        return "sell"
    if plan_material.selected_candidate is not None or planned_action == "hold_existing_position_risk_on":
        return "buy"
    return ""


def _projected_exposure(
    *,
    current_exposure: Decimal,
    intended_notional: Decimal | None,
    side: str,
) -> Decimal | None:
    if intended_notional is None:
        return None
    if side == "sell":
        return max(Decimal("0"), current_exposure - intended_notional)
    return current_exposure + intended_notional


def _cap_status(value: Decimal | None, cap: Decimal) -> str:
    if value is None:
        return "not_evaluated"
    return "blocked" if value > cap else "passed"


def _open_order_matches_symbol(order: Mapping[str, object], symbol: str) -> bool:
    if not symbol or _text(order.get("symbol")) != symbol:
        return False
    status = _text(order.get("status")).lower()
    return status not in {"filled", "canceled", "cancelled", "closed"}


def _position_matches_symbol(position: Mapping[str, object], symbol: str) -> bool:
    if not symbol or _text(position.get("symbol")) != symbol:
        return False
    quantity = _first_decimal(position.get("quantity"))
    return quantity is None or quantity > Decimal("0")


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


def _state_root(output_root: Path, state_root: Path | str | None) -> Path:
    return Path(state_root) if state_root is not None else output_root / "state"


def _load_simbroker_state(
    state_root: Path,
    *,
    reset_state: bool,
) -> SimBrokerStateSnapshot:
    state_path = state_root / "simbroker_state.json"
    if reset_state or not state_path.is_file():
        return _state_snapshot_from_payload(
            state_root,
            _initial_simbroker_state(state_root),
            exists=False,
        )
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _state_snapshot_from_payload(
            state_root,
            _initial_simbroker_state(state_root),
            exists=True,
            extra_errors=("invalid_json:simbroker_state.json",),
        )
    except OSError:
        return _state_snapshot_from_payload(
            state_root,
            _initial_simbroker_state(state_root),
            exists=True,
            extra_errors=("unreadable_json:simbroker_state.json",),
        )
    if not isinstance(payload, Mapping):
        return _state_snapshot_from_payload(
            state_root,
            _initial_simbroker_state(state_root),
            exists=True,
            extra_errors=("json_not_object:simbroker_state.json",),
        )
    return _state_snapshot_from_payload(state_root, payload, exists=True)


def _state_snapshot_from_payload(
    state_root: Path,
    payload: Mapping[str, object],
    *,
    exists: bool,
    extra_errors: Sequence[str] = (),
) -> SimBrokerStateSnapshot:
    errors: list[str] = list(extra_errors)
    if payload.get("record_type") != "simbroker_state":
        errors.append("state_record_type_mismatch")
    if payload.get("broker_mode") != "simulation_broker":
        errors.append("state_broker_mode_mismatch")
    portfolio = _portfolio_from_state(payload, errors)
    orders = _mapping_sequence(payload.get("orders"))
    fills = _mapping_sequence(payload.get("fills"))
    cycle_history = _mapping_sequence(payload.get("cycle_history"))
    events = _mapping_sequence(payload.get("events"))
    open_orders = _mapping_sequence(payload.get("open_orders"))
    seen_client_order_ids = _dedupe(
        (
            *_string_sequence(payload.get("seen_client_order_ids")),
            *(
                _text(order.get("client_order_id"))
                for order in orders
                if _text(order.get("client_order_id"))
            ),
            *(
                _text(fill.get("client_order_id"))
                for fill in fills
                if _text(fill.get("client_order_id"))
            ),
        )
    )
    errors.extend(_state_reconciliation_errors(payload, portfolio))
    return SimBrokerStateSnapshot(
        state_root=state_root,
        exists=exists,
        payload=payload,
        portfolio=portfolio,
        seen_client_order_ids=seen_client_order_ids,
        orders=orders,
        fills=fills,
        cycle_history=cycle_history,
        events=events,
        open_orders=open_orders,
        errors=tuple(_dedupe(errors)),
    )


def _initial_simbroker_state(state_root: Path) -> dict[str, object]:
    labels = _simbroker_labels(simulation_mutation_occurred=False)
    portfolio = PortfolioState(account=Account(SIMULATED_STARTING_CASH, "USD"))
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "simbroker_state",
        "state_root": str(state_root),
        "broker_mode": "simulation_broker",
        "cash": SIMULATED_STARTING_CASH,
        "currency": "USD",
        "positions": [],
        "gross_exposure": Decimal("0"),
        "open_orders": [],
        "orders": [],
        "fills": [],
        "seen_client_order_ids": [],
        "cycle_history": [],
        "events": [],
        "portfolio_snapshot": _portfolio_snapshot(portfolio),
        "safety": _simbroker_safety(simulation_mutation_occurred=False),
        "safety_labels": list(labels),
        "labels": list(labels),
        "profit_claim": "none",
    }


def _portfolio_from_state(
    payload: Mapping[str, object],
    errors: list[str],
) -> PortfolioState:
    cash = _decimal_or_error(payload.get("cash", SIMULATED_STARTING_CASH), "cash", errors)
    if cash < 0:
        errors.append("state_cash_negative")
        cash = Decimal("0")
    currency = _text(payload.get("currency")) or "USD"
    positions: list[Position] = []
    for index, item in enumerate(_mapping_sequence(payload.get("positions"))):
        symbol = _text(item.get("symbol"))
        quantity = _decimal_or_error(item.get("quantity", "0"), f"positions[{index}].quantity", errors)
        average_price = _decimal_or_error(
            item.get("average_price", "0"),
            f"positions[{index}].average_price",
            errors,
        )
        if quantity < 0:
            errors.append(f"positions[{index}].quantity_negative")
            continue
        if average_price < 0:
            errors.append(f"positions[{index}].average_price_negative")
            continue
        if quantity == 0:
            continue
        try:
            positions.append(Position(symbol, quantity, average_price))
        except Exception:
            errors.append(f"positions[{index}].invalid_position")
    try:
        return PortfolioState(
            account=Account(cash, currency),
            positions=tuple(positions),
        )
    except Exception:
        errors.append("state_portfolio_invalid")
        return PortfolioState(account=Account(SIMULATED_STARTING_CASH, "USD"))


def _state_reconciliation_errors(
    payload: Mapping[str, object],
    portfolio: PortfolioState,
) -> tuple[str, ...]:
    errors: list[str] = []
    expected = PortfolioState(account=Account(SIMULATED_STARTING_CASH, "USD"))
    for index, fill_payload in enumerate(_mapping_sequence(payload.get("fills"))):
        try:
            side = OrderSide(_text(fill_payload.get("side")))
            fill = Fill(
                order_id=_text(fill_payload.get("client_order_id"))
                or _text(fill_payload.get("order_id")),
                symbol=_text(fill_payload.get("symbol")),
                side=side,
                quantity=_decimal_or_error(
                    fill_payload.get("quantity", "0"),
                    f"fills[{index}].quantity",
                    errors,
                ),
                price=_decimal_or_error(
                    fill_payload.get("price", "0"),
                    f"fills[{index}].price",
                    errors,
                ),
                timestamp=_utc_datetime(
                    fill_payload.get("timestamp"),
                    f"fills[{index}].timestamp",
                ),
            )
            expected = apply_fill(expected, fill)
        except Exception:
            errors.append(f"fills[{index}].invalid_fill")
    if expected.account.cash != portfolio.account.cash:
        errors.append("state_cash_arithmetic_mismatch")
    expected_positions = {
        position.symbol: position for position in expected.positions if not position.is_flat
    }
    actual_positions = {
        position.symbol: position for position in portfolio.positions if not position.is_flat
    }
    if set(expected_positions) != set(actual_positions):
        errors.append("state_position_symbols_mismatch")
    for symbol, expected_position in expected_positions.items():
        actual_position = actual_positions.get(symbol)
        if actual_position is None:
            continue
        if actual_position.quantity != expected_position.quantity:
            errors.append(f"state_position_quantity_mismatch:{symbol}")
        if actual_position.average_price != expected_position.average_price:
            errors.append(f"state_position_average_price_mismatch:{symbol}")
    gross_exposure = sum(
        position.quantity * position.average_price for position in portfolio.positions
    )
    recorded_gross = _decimal_or_error(
        payload.get("gross_exposure", gross_exposure),
        "gross_exposure",
        errors,
    )
    if recorded_gross != gross_exposure:
        errors.append("state_gross_exposure_mismatch")
    return tuple(_dedupe(errors))


def _state_blocker(state_snapshot: SimBrokerStateSnapshot) -> str:
    if state_snapshot.errors:
        return "state_reconciliation_failed"
    if state_snapshot.open_orders:
        return "open_simulated_order_present"
    return ""


def _blocked_broker_result(
    blocker: str,
    *,
    portfolio: PortfolioState,
) -> dict[str, object]:
    return {
        "status": "blocked",
        "blocker": blocker,
        "action_count": 0,
        "fill_count": 0,
        "portfolio": _portfolio_snapshot(portfolio),
    }


def _next_cycle_index(state_snapshot: SimBrokerStateSnapshot) -> int:
    indices: list[int] = []
    for cycle in state_snapshot.cycle_history:
        value = cycle.get("cycle_index")
        if isinstance(value, int):
            indices.append(value)
            continue
        try:
            indices.append(int(str(value)))
        except (TypeError, ValueError):
            continue
    return max(indices, default=0) + 1


def _cycle_key(
    *,
    as_of: datetime,
    scenario: Scenario,
    universe: Sequence[str],
) -> str:
    digest = hashlib.sha256(
        "|".join((as_of.isoformat(), scenario, ",".join(universe))).encode("utf-8")
    ).hexdigest()[:10]
    return f"{as_of.strftime('%Y%m%dT%H%M%SZ')}_{scenario}_{digest}"


def _cycle_record(
    *,
    cycle_index: int,
    cycle_key: str,
    run_id: str,
    as_of: datetime,
    scenario: Scenario,
    plan_material: DemoPlanMaterial,
    decision: str,
    final_blocker: str,
    simulation_mutation_occurred: bool,
    portfolio_before: PortfolioState,
    portfolio_after: PortfolioState,
    fill_ledger: Sequence[Mapping[str, object]],
    safety_labels: Sequence[str],
) -> dict[str, object]:
    order = plan_material.order
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "simbroker_cycle",
        "cycle_index": cycle_index,
        "cycle_key": cycle_key,
        "run_id": run_id,
        "as_of": as_of.isoformat(),
        "scenario": scenario,
        "broker_mode": "simulation_broker",
        "planned_action": plan_material.planned_action,
        "decision": decision,
        "final_blocker_status": final_blocker,
        "client_order_id": plan_material.client_order_id,
        "symbol": "" if order is None else order.symbol,
        "side": "" if order is None else order.side.value,
        "fill_count": len(fill_ledger),
        "simulation_mutation_occurred": simulation_mutation_occurred,
        "portfolio_before": _portfolio_snapshot(portfolio_before),
        "portfolio_after": _portfolio_snapshot(portfolio_after),
        "safety_labels": list(safety_labels),
        "labels": list(safety_labels),
        "profit_claim": "none",
    }


def _updated_simbroker_state(
    *,
    state_snapshot: SimBrokerStateSnapshot,
    portfolio: PortfolioState,
    orders: Sequence[Mapping[str, object]],
    fills: Sequence[Mapping[str, object]],
    cycle_record: Mapping[str, object],
    events: Sequence[Mapping[str, object]],
    safety_labels: Sequence[str],
) -> dict[str, object]:
    prior_orders = list(state_snapshot.orders)
    prior_fills = list(state_snapshot.fills)
    prior_cycles = list(state_snapshot.cycle_history)
    order_records = [
        _state_order_record(order, cycle_record, safety_labels)
        for order in orders
        if _text(order.get("event_type")) in {
            "simulation_order_submitted",
            "simulation_order_acknowledged",
            "simulation_order_canceled",
        }
    ]
    fill_records = [
        _state_fill_record(fill, cycle_record, safety_labels)
        for fill in fills
    ]
    seen_client_order_ids = _dedupe(
        (
            *state_snapshot.seen_client_order_ids,
            *(
                _text(order.get("client_order_id"))
                for order in order_records
                if _text(order.get("client_order_id"))
            ),
            *(
                _text(fill.get("client_order_id"))
                for fill in fill_records
                if _text(fill.get("client_order_id"))
            ),
        )
    )
    portfolio_payload = _portfolio_state_payload(portfolio)
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "simbroker_state",
        "state_root": str(state_snapshot.state_root),
        "broker_mode": "simulation_broker",
        "cash": portfolio.account.cash,
        "currency": portfolio.account.currency,
        "positions": portfolio_payload["positions"],
        "gross_exposure": portfolio_payload["gross_exposure"],
        "open_orders": list(state_snapshot.open_orders),
        "orders": [*prior_orders, *order_records],
        "fills": [*prior_fills, *fill_records],
        "seen_client_order_ids": list(seen_client_order_ids),
        "cycle_history": [*prior_cycles, dict(cycle_record)],
        "events": [dict(event) for event in events],
        "portfolio_snapshot": _portfolio_snapshot(portfolio),
        "safety": _simbroker_safety(
            simulation_mutation_occurred=_text(cycle_record.get("simulation_mutation_occurred")) == "true"
        ),
        "safety_labels": list(safety_labels),
        "labels": list(safety_labels),
        "profit_claim": "none",
    }


def _state_order_record(
    order: Mapping[str, object],
    cycle_record: Mapping[str, object],
    safety_labels: Sequence[str],
) -> dict[str, object]:
    return {
        **dict(order),
        "cycle_index": cycle_record.get("cycle_index"),
        "cycle_key": cycle_record.get("cycle_key"),
        "run_id": cycle_record.get("run_id"),
        "broker_mode": "simulation_broker",
        "safety_labels": list(safety_labels),
        "labels": list(safety_labels),
        "profit_claim": "none",
    }


def _state_fill_record(
    fill: Mapping[str, object],
    cycle_record: Mapping[str, object],
    safety_labels: Sequence[str],
) -> dict[str, object]:
    return {
        **dict(fill),
        "cycle_index": cycle_record.get("cycle_index"),
        "cycle_key": cycle_record.get("cycle_key"),
        "run_id": cycle_record.get("run_id"),
        "broker_mode": "simulation_broker",
        "safety_labels": list(safety_labels),
        "labels": list(safety_labels),
        "profit_claim": "none",
    }


def _portfolio_state_payload(portfolio: PortfolioState) -> dict[str, object]:
    return {
        "positions": [_position_snapshot(position) for position in portfolio.positions],
        "gross_exposure": sum(
            position.quantity * position.average_price for position in portfolio.positions
        ),
    }


def _write_simbroker_state_artifacts(
    state_root: Path,
    state_payload: Mapping[str, object],
) -> dict[str, str]:
    state_root.mkdir(parents=True, exist_ok=True)
    paths = {name: state_root / name for name in STATE_ARTIFACTS}
    _write_json(paths["simbroker_state.json"], state_payload)
    positions_payload = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "simbroker_positions",
        "broker_mode": "simulation_broker",
        "state_root": str(state_root),
        "cash": state_payload.get("cash"),
        "currency": state_payload.get("currency"),
        "positions": list(_mapping_sequence(state_payload.get("positions"))),
        "gross_exposure": state_payload.get("gross_exposure"),
        "safety": dict(_mapping(state_payload.get("safety"))),
        "safety_labels": list(_string_sequence(state_payload.get("safety_labels"))),
        "labels": list(_string_sequence(state_payload.get("labels"))),
        "profit_claim": "none",
    }
    _write_json(paths["positions.json"], positions_payload)
    _write_events(paths["fills.jsonl"], _mapping_sequence(state_payload.get("fills")))
    _write_events(
        paths["cycle_history.jsonl"],
        _mapping_sequence(state_payload.get("cycle_history")),
    )
    _write_events(paths["events.jsonl"], _mapping_sequence(state_payload.get("events")))
    return {name: str(path) for name, path in paths.items()}


def _state_artifact_paths(state_root: Path) -> dict[str, str]:
    return {name: str(state_root / name) for name in STATE_ARTIFACTS}


def _simbroker_labels(
    *,
    simulation_mutation_occurred: bool,
    broker_read_occurred: bool = False,
    broker_state_observed: bool = False,
    network_used: bool = False,
) -> tuple[str, ...]:
    return (
        *REQUIRED_SAFETY_LABELS,
        "broker_mode=simulation_broker",
        "simulation_mutation_authorized=true",
        "paper_submit_occurred=false",
        "broker_mutation_occurred=false",
        f"broker_read_occurred={_bool_text(broker_read_occurred)}",
        f"broker_state_observed={_bool_text(broker_state_observed)}",
        "broker_state_mode=alpaca_paper_read_only_observed"
        if broker_state_observed
        else "broker_state_mode=offline_simulation",
        f"network_used={_bool_text(network_used)}",
        f"simulation_mutation_occurred={_bool_text(simulation_mutation_occurred)}",
    )


def _sim_decision(
    plan_material: DemoPlanMaterial,
    broker_result: Mapping[str, object],
) -> str:
    broker_status = _text(broker_result.get("status"))
    broker_blocker = _text(broker_result.get("blocker"))
    if broker_status == "blocked" and broker_blocker:
        if broker_blocker == "duplicate_client_order_id":
            return "blocked_duplicate_client_order_id"
        if broker_blocker == "state_reconciliation_failed":
            return "blocked_state_reconciliation_failed"
        if broker_blocker == "open_simulated_order_present":
            return "blocked_open_simulated_order_present"
        return broker_blocker
    if plan_material.planned_action == "hold_existing_position_risk_on":
        return "hold_noop_existing_simulated_position"
    if plan_material.planned_action == "hold_no_position_risk_off":
        return "hold_noop_no_simulated_position"
    if plan_material.planned_action == "blocked_no_trade":
        if "data_quality_block" in plan_material.blockers:
            return "blocked_no_trade_data_quality"
        return "blocked_no_trade_all_candidates_failed_gates"
    fill_count = int(broker_result.get("fill_count", 0) or 0)
    if (
        broker_status == "completed"
        and plan_material.planned_action == "simulated_exit"
        and plan_material.order is not None
        and fill_count > 0
    ):
        return "offline_simulated_exit_only"
    if (
        broker_status == "completed"
        and plan_material.planned_action == "simulated_buy"
        and plan_material.order is not None
        and fill_count > 0
    ):
        return "offline_simulated_trade_only"
    if plan_material.blockers:
        if "duplicate_client_order_id" in plan_material.blockers:
            return "blocked_duplicate_client_order_id"
        if any("risk" in blocker for blocker in plan_material.blockers):
            return "no_trade_risk_block"
    if broker_blocker:
        return broker_blocker
    return "no_trade_all_scores_below_threshold"


def _final_blocker(
    plan_material: DemoPlanMaterial,
    broker_result: Mapping[str, object],
) -> str:
    broker_blocker = _text(broker_result.get("blocker"))
    if broker_blocker:
        return broker_blocker
    if plan_material.planned_action in {
        "hold_existing_position_risk_on",
        "hold_no_position_risk_off",
    }:
        return "none"
    if plan_material.planned_action in {"simulated_buy", "simulated_exit"} and not plan_material.blockers:
        return "none"
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


def _scenario(value: object) -> Scenario:
    if value in {"risk_on", "risk_off", "all_blocked", "bad_data"}:
        return value  # type: ignore[return-value]
    raise ValueError("scenario must be risk_on, risk_off, all_blocked, or bad_data.")


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


def _strict_true(value: object) -> bool:
    return value is True


def _first_decimal(*values: object) -> Decimal | None:
    for value in values:
        parsed = _decimal_or_none(value)
        if parsed is not None:
            return parsed
    return None


def _decimal_or_none(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except Exception:
        return None
    if not parsed.is_finite():
        return None
    return parsed


def _datetime_or_none(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return _utc_datetime(value, "timestamp")
    except Exception:
        return None


def _decimal_or_error(
    value: object,
    field_name: str,
    errors: list[str],
) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        errors.append(f"invalid_decimal:{field_name}")
        return Decimal("0")


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
        description="Run or validate the v6.1 crypto SimBroker operating loop.",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--state-root", type=Path, default=None)
    parser.add_argument("--mode", choices=("SimBroker", "AlpacaPaper"), default="SimBroker")
    parser.add_argument("--allow-alpaca-paper-mutation", action="store_true")
    parser.add_argument("--broker-observed-readiness", action="store_true")
    parser.add_argument("--allow-alpaca-paper-read", action="store_true")
    parser.add_argument("--as-of", default="")
    parser.add_argument(
        "--scenario",
        choices=("risk_on", "risk_off", "all_blocked", "bad_data"),
        default=DEFAULT_SCENARIO,
    )
    parser.add_argument("--reset-state", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    if args.validate_only:
        validation = validate_tomorrow_crypto_trader_demo(args.output_root)
        if args.format == "json":
            print(json.dumps(_json_safe(validation), sort_keys=True))
        else:
            print(f"tomorrow_crypto_trader_demo_validation_status={validation['validation_status']}")
            for field in BROKER_OBSERVED_CONSISTENCY_FIELDS:
                value = validation.get(field)
                if type(value) is bool:
                    rendered = _bool_text(value)
                else:
                    rendered = _text(value)
                print(f"tomorrow_crypto_trader_demo_validator_{field}={rendered}")
            print("errors=" + ",".join(_string_sequence(validation.get("errors"))))
        return 0 if validation["validation_status"] == "passed" else 1

    packet = run_tomorrow_crypto_trader_demo(
        output_root=args.output_root,
        mode=args.mode,
        allow_alpaca_paper_mutation=args.allow_alpaca_paper_mutation,
        broker_observed_readiness=args.broker_observed_readiness,
        allow_alpaca_paper_read=args.allow_alpaca_paper_read,
        as_of=args.as_of or None,
        state_root=args.state_root,
        scenario=args.scenario,
        reset_state=args.reset_state,
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(packet), sort_keys=True))
    else:
        run_summary = _run_summary_payload(packet)
        for line in _string_sequence(run_summary.get("console_lines")):
            print(line)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
