"""Strategy-agnostic no-submit forward-shadow registry and observation ledger.

A forward shadow answers one question honestly: does a hypothesis registered
*now* hold up on data that did not exist when it was registered? Every scored
window in this repository is contaminated by hindsight — the rule was chosen
after its history was visible. This module is the only route that is not.

Five properties are enforced mechanically rather than by convention:

1. **The gates are bound to the registration.** Thresholds, universe, costs,
   sequential boundaries, cohort multiplicity, and the required decision count
   are hashed into an immutable registration fingerprint. Editing any of them
   after seeing data changes the fingerprint and every later load fails closed.
2. **Backfill is impossible.** An observation is admissible only inside
   `registration_date < session <= recorded_at`, with strictly increasing
   sessions.
3. **Early peeking cannot produce a verdict.** Until a frozen stopping
   condition is met, evaluation returns an accrual status carrying no return,
   Sharpe, drawdown, or gate outcome. No argument unlocks it.
4. **Power is counted in decisions, not days.** A monthly rule observed for
   126 sessions has made six decisions, not 126. Gates and the sequential test
   run on completed decision intervals, so a low-frequency rule cannot borrow
   apparent significance from the days it merely held a position.
5. **Waiting is bounded by evidence, not the calendar.** A pre-registered
   sequential probability ratio test can stop early for futility or efficacy,
   so a dead hypothesis is closed in weeks instead of consuming a full window.

The ledger is append-only and hash-chained from the registration fingerprint,
so truncation, reordering, or editing any past entry is detectable.

This module is local and research-only. It cannot load credentials, reach a
network or broker, plan an order, mutate a paper account, or authorize live
capital.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import load_local_daily_bars_csv

__all__ = [
    "FORWARD_SHADOW_POLICY_FINGERPRINT",
    "FORWARD_SHADOW_POLICY_VERSION",
    "FORWARD_SHADOW_SCHEMA_VERSION",
    "ForwardShadowGates",
    "SequentialBoundaries",
    "append_forward_shadow_observation",
    "build_forward_shadow_policy",
    "evaluate_forward_shadow",
    "load_forward_shadow_state",
    "main",
    "register_forward_shadow",
    "register_forward_shadow_cohort",
    "render_forward_shadow_markdown",
]

FORWARD_SHADOW_SCHEMA_VERSION = "v5_90_forward_shadow_registry_v2"
FORWARD_SHADOW_POLICY_VERSION = "v5_90_forward_shadow_policy_v2"
FORWARD_SHADOW_POLICY_FINGERPRINT = (
    "ccd2cb78a81bd746692d20077541cfbdc7902b138cbb778595a3b7685d25d332"
)

_REGISTRATION_NAME = "registration.json"
_LEDGER_NAME = "observations.jsonl"
_STATUS_NAME = "status.json"
_STATUS_MARKDOWN_NAME = "status.md"
_COHORT_NAME = "cohort.json"
_COHORT_MEMBERS_NAME = "cohort_members.jsonl"

_QUANTUM = Decimal("0.000000000001")
_ZERO = Decimal("0")
_ONE = Decimal("1")
_TRADING_DAYS_PER_YEAR = Decimal("252")
_SUPPORTED_CORRECTIONS = ("bonferroni", "none")

_ZERO_AUTHORITY = {
    "network_access_performed": False,
    "credential_access_performed": False,
    "market_data_fetch_performed": False,
    "broker_read_performed": False,
    "broker_mutation_performed": False,
    "paper_submit_authorized": False,
    "paper_submit_performed": False,
    "paper_mutation_performed": False,
    "capital_allocation_authorized": False,
    "live_authorized": False,
    "live_activity_performed": False,
    "profit_claim_made": False,
}


@dataclass(frozen=True, slots=True)
class SequentialBoundaries:
    """Frozen Wald SPRT boundaries on per-decision excess return.

    The test compares `H0: mean excess = 0` against
    `H1: mean excess = minimum_excess_per_decision`, treating per-decision
    excess as normal with the declared reference sigma. Declaring sigma in
    advance is a preregistration commitment, not an estimate fitted later.

    Excess is measured per completed decision interval, so a low-win-rate,
    high-payoff rule is judged on magnitude rather than hit rate — the failure
    mode that would wrongly kill a trend follower.
    """

    alpha: str = "0.050000000000"
    beta: str = "0.200000000000"
    minimum_excess_per_decision: str = "0.010000000000"
    reference_excess_sigma: str = "0.040000000000"
    minimum_decisions_before_stopping: int = 8

    def __post_init__(self) -> None:
        for name in (
            "alpha",
            "beta",
            "minimum_excess_per_decision",
            "reference_excess_sigma",
        ):
            object.__setattr__(self, name, _decimal_text(getattr(self, name), name))
        if not _is_positive_int(self.minimum_decisions_before_stopping):
            raise ValidationError(
                "minimum_decisions_before_stopping must be a positive integer."
            )
        alpha = _decimal(self.alpha, "alpha")
        beta = _decimal(self.beta, "beta")
        if not (_ZERO < alpha < _ONE):
            raise ValidationError("alpha must lie strictly between 0 and 1.")
        if not (_ZERO < beta < _ONE):
            raise ValidationError("beta must lie strictly between 0 and 1.")
        if _decimal(self.reference_excess_sigma, "sigma") <= _ZERO:
            raise ValidationError("reference_excess_sigma must be positive.")
        if _decimal(self.minimum_excess_per_decision, "effect") <= _ZERO:
            raise ValidationError("minimum_excess_per_decision must be positive.")

    def as_payload(self) -> dict[str, object]:
        return {
            "alpha": self.alpha,
            "beta": self.beta,
            "minimum_excess_per_decision": self.minimum_excess_per_decision,
            "reference_excess_sigma": self.reference_excess_sigma,
            "minimum_decisions_before_stopping": (
                self.minimum_decisions_before_stopping
            ),
            "test": "wald_sprt_normal_mean_on_per_decision_excess_return",
        }


@dataclass(frozen=True, slots=True)
class ForwardShadowGates:
    """Terminal thresholds frozen into the registration fingerprint."""

    minimum_decisions: int
    minimum_annualized_return: str = "0.000000000000"
    minimum_sharpe_ratio: str = "0.300000000000"
    maximum_drawdown: str = "0.300000000000"
    minimum_benchmark_annualized_return_delta: str = "-0.010000000000"
    minimum_benchmark_sharpe_delta: str = "0.000000000000"
    sequential: SequentialBoundaries = field(default_factory=SequentialBoundaries)

    def __post_init__(self) -> None:
        if not _is_positive_int(self.minimum_decisions):
            raise ValidationError("minimum_decisions must be a positive integer.")
        for name in (
            "minimum_annualized_return",
            "minimum_sharpe_ratio",
            "maximum_drawdown",
            "minimum_benchmark_annualized_return_delta",
            "minimum_benchmark_sharpe_delta",
        ):
            object.__setattr__(self, name, _decimal_text(getattr(self, name), name))
        if not isinstance(self.sequential, SequentialBoundaries):
            raise ValidationError("sequential must be SequentialBoundaries.")

    def as_payload(self) -> dict[str, object]:
        return {
            "minimum_decisions": self.minimum_decisions,
            "minimum_annualized_return": self.minimum_annualized_return,
            "minimum_sharpe_ratio": self.minimum_sharpe_ratio,
            "maximum_drawdown": self.maximum_drawdown,
            "minimum_benchmark_annualized_return_delta": (
                self.minimum_benchmark_annualized_return_delta
            ),
            "minimum_benchmark_sharpe_delta": self.minimum_benchmark_sharpe_delta,
            "sequential": self.sequential.as_payload(),
        }


def build_forward_shadow_policy() -> dict[str, object]:
    """Return the hypothesis-agnostic policy frozen before any registration."""

    policy: dict[str, object] = {
        "schema_version": FORWARD_SHADOW_SCHEMA_VERSION,
        "policy_version": FORWARD_SHADOW_POLICY_VERSION,
        "record_type": "forward_shadow_policy",
        "temporal_policy": {
            "admissible_session_rule": (
                "registration_date_exclusive_to_recorded_date_inclusive"
            ),
            "backfill_allowed": False,
            "future_session_allowed": False,
            "session_order": "strictly_increasing",
            "window_extension_allowed": False,
            "unplanned_early_stop_allowed": False,
        },
        "power_policy": {
            "unit_of_evidence": "completed_decision_interval",
            "session_count_is_not_evidence": True,
            "decision_interval_rule": (
                "decision_at_d_earns_from_next_session_through_the_next_"
                "decision_session_inclusive"
            ),
        },
        "sequential_policy": {
            "test": "wald_sprt_normal_mean_on_per_decision_excess_return",
            "boundaries_frozen_at_registration": True,
            "efficacy_boundary": "log((1-beta)/effective_alpha)",
            "futility_boundary": "log(beta/(1-effective_alpha))",
            "stop_before_minimum_decisions_allowed": False,
            "boundary_mutation_after_registration_allowed": False,
        },
        "multiplicity_policy": {
            "cohort_planned_member_count_frozen": True,
            "members_beyond_planned_count_refused": True,
            "supported_corrections": list(_SUPPORTED_CORRECTIONS),
            "effective_alpha_frozen_at_registration": True,
        },
        "integrity_policy": {
            "ledger": "append_only_jsonl",
            "chain": "sha256_over_prior_entry_hash_and_canonical_entry_bytes",
            "chain_anchor": "registration_fingerprint",
            "tamper_response": "fail_closed",
        },
        "evaluation_policy": {
            "verdict_before_stopping_condition": "withheld",
            "metrics_before_stopping_condition": "withheld",
            "gate_mutation_after_registration_allowed": False,
            "hypothesis_mutation_after_registration_allowed": False,
            "benchmark_required": True,
        },
        "authority_boundary": {
            "network_access_authorized": False,
            "credential_access_authorized": False,
            "broker_read_authorized": False,
            "broker_mutation_authorized": False,
            "paper_planning_authorized": False,
            "paper_mutation_authorized": False,
            "capital_allocation_authorized": False,
            "live_trading_authorized": False,
            "operator_review_required_after_terminal_window": True,
        },
        "promotion_policy": {
            "pass_routes_to": "operator_review_of_completed_forward_evidence",
            "pass_authorizes_paper": False,
            "pass_authorizes_live": False,
        },
        "profit_claim": "none",
    }
    fingerprint = _stable_hash(policy)
    if fingerprint != FORWARD_SHADOW_POLICY_FINGERPRINT:
        raise RuntimeError(f"forward-shadow policy drift detected: {fingerprint}")
    policy["policy_fingerprint"] = fingerprint
    return policy


def register_forward_shadow_cohort(
    cohort_root: Path | str,
    *,
    cohort_id: str,
    planned_member_count: int,
    family_wise_alpha: str = "0.050000000000",
    correction: str = "bonferroni",
    registered_at: datetime | str,
) -> dict[str, object]:
    """Freeze a multiplicity cohort before any member is registered.

    The planned member count is frozen here so the Bonferroni divisor cannot be
    chosen after the fact. Registering twenty hypotheses and reporting the best
    as if one had been tested is the exact abuse this prevents.
    """

    policy = build_forward_shadow_policy()
    root = _local_root(cohort_root)
    cohort_path = root / _COHORT_NAME
    if cohort_path.exists():
        raise ValidationError("a cohort is already registered at this root.")
    if not _is_positive_int(planned_member_count):
        raise ValidationError("planned_member_count must be a positive integer.")
    if correction not in _SUPPORTED_CORRECTIONS:
        raise ValidationError(f"unsupported correction: {correction}")
    alpha = _decimal(family_wise_alpha, "family_wise_alpha")
    if not (_ZERO < alpha < _ONE):
        raise ValidationError("family_wise_alpha must lie strictly between 0 and 1.")

    moment = _utc_datetime(registered_at, "registered_at")
    basis = {
        "policy_fingerprint": policy["policy_fingerprint"],
        "cohort_id": _required_text(cohort_id, "cohort_id"),
        "planned_member_count": planned_member_count,
        "family_wise_alpha": _decimal_text(family_wise_alpha, "family_wise_alpha"),
        "correction": correction,
        "registered_at": moment.isoformat(),
    }
    payload: dict[str, object] = {
        "schema_version": FORWARD_SHADOW_SCHEMA_VERSION,
        "record_type": "forward_shadow_cohort",
        **basis,
        "cohort_fingerprint": _stable_hash(basis),
        "safety": dict(_ZERO_AUTHORITY),
    }
    root.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(cohort_path, payload)
    _write_text_atomic(root / _COHORT_MEMBERS_NAME, "")
    return payload


def register_forward_shadow(
    root: Path | str,
    *,
    hypothesis_id: str,
    hypothesis_statement: str,
    universe: Sequence[str],
    benchmark_symbol: str,
    rule_reference: str,
    rule_fingerprint: str,
    gates: ForwardShadowGates,
    cost_bps_per_one_way_turnover: str = "5.000000000000",
    registered_at: datetime | str,
    cohort_root: Path | str | None = None,
) -> dict[str, object]:
    """Create the immutable registration and empty ledger. Never overwrites."""

    policy = build_forward_shadow_policy()
    target = _local_root(root)
    registration_path = target / _REGISTRATION_NAME
    ledger_path = target / _LEDGER_NAME
    if registration_path.exists() or ledger_path.exists():
        raise ValidationError(
            "a forward shadow is already registered at this root; "
            "re-registration would destroy untouched evidence."
        )

    moment = _utc_datetime(registered_at, "registered_at")
    symbols = _validated_universe(universe)
    benchmark = _required_text(benchmark_symbol, "benchmark_symbol").upper()
    if benchmark not in symbols:
        raise ValidationError("benchmark_symbol must belong to the universe.")

    cohort_binding = _cohort_binding(cohort_root, gates)
    basis = {
        "policy_fingerprint": policy["policy_fingerprint"],
        "hypothesis_id": _required_text(hypothesis_id, "hypothesis_id"),
        "hypothesis_statement": _required_text(
            hypothesis_statement, "hypothesis_statement"
        ),
        "universe": list(symbols),
        "benchmark_symbol": benchmark,
        "rule_reference": _required_text(rule_reference, "rule_reference"),
        "rule_fingerprint": _validated_sha256(rule_fingerprint, "rule_fingerprint"),
        "gates": gates.as_payload(),
        "cohort_binding": cohort_binding,
        "cost_bps_per_one_way_turnover": _decimal_text(
            cost_bps_per_one_way_turnover, "cost_bps_per_one_way_turnover"
        ),
        "registered_at": moment.isoformat(),
        "registration_date": moment.date().isoformat(),
        "first_admissible_session_exclusive": moment.date().isoformat(),
    }
    fingerprint = _stable_hash(basis)
    payload: dict[str, object] = {
        "schema_version": FORWARD_SHADOW_SCHEMA_VERSION,
        "record_type": "forward_shadow_registration",
        **basis,
        "registration_fingerprint": fingerprint,
        "safety": dict(_ZERO_AUTHORITY),
    }
    target.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(registration_path, payload)
    _write_text_atomic(ledger_path, "")
    if cohort_root is not None:
        _append_cohort_member(
            _local_root(cohort_root),
            hypothesis_id=str(basis["hypothesis_id"]),
            registration_fingerprint=fingerprint,
            registered_at=moment,
        )
    return payload


def append_forward_shadow_observation(
    root: Path | str,
    *,
    session: date | str,
    targets: Mapping[str, object],
    canonical_data_path: Path | str,
    recorded_at: datetime | str,
    is_decision: bool,
) -> dict[str, object]:
    """Append exactly one causally admissible session to the ledger.

    `is_decision` must state explicitly whether the rule made a fresh choice
    for this session. It is required rather than inferred: a rule that
    re-evaluates and deliberately keeps its previous target has still made a
    decision, and only the adapter knows that.
    """

    if not isinstance(is_decision, bool):
        raise ValidationError("is_decision must be an explicit boolean.")
    target_root = _local_root(root)
    registration, entries = load_forward_shadow_state(target_root)
    session_date = _required_date(session, "session")
    moment = _utc_datetime(recorded_at, "recorded_at")

    registration_date = _required_date(
        registration["registration_date"], "registration_date"
    )
    if session_date <= registration_date:
        raise ValidationError(
            "backfill rejected: session must fall strictly after the "
            "registration date."
        )
    if session_date > moment.date():
        raise ValidationError(
            "future session rejected: session must not follow the recorded "
            "observation instant."
        )
    if entries:
        previous = entries[-1]
        previous_session = _required_date(previous["session"], "previous session")
        if session_date <= previous_session:
            raise ValidationError(
                "out-of-order session rejected: sessions must strictly increase."
            )
        if moment < _utc_datetime(previous["recorded_at"], "previous recorded_at"):
            raise ValidationError(
                "recorded_at must not precede the prior observation."
            )
        previous_hash = str(previous["entry_sha256"])
        prior_positions = {
            symbol: _decimal(value, "prior position")
            for symbol, value in dict(previous["positions"]).items()
        }
        prior_equity = _decimal(previous["equity"], "prior equity")
        prior_peak = _decimal(previous["peak_equity"], "prior peak equity")
        prior_benchmark_equity = _decimal(
            previous["benchmark_equity"], "prior benchmark equity"
        )
        sequence = int(previous["sequence"]) + 1
    else:
        if not is_decision:
            raise ValidationError(
                "the first observation must be a decision: it establishes the "
                "position the shadow is testing."
            )
        previous_hash = str(registration["registration_fingerprint"])
        prior_positions = {symbol: _ZERO for symbol in registration["universe"]}
        prior_equity = _ONE
        prior_peak = _ONE
        prior_benchmark_equity = _ONE
        sequence = 1

    symbols = tuple(str(symbol) for symbol in registration["universe"])
    resolved_targets = _validated_targets(targets, symbols)
    if not is_decision and entries:
        previous_targets = {
            symbol: _decimal(value, "previous target")
            for symbol, value in dict(entries[-1]["targets"]).items()
        }
        if resolved_targets != previous_targets:
            raise ValidationError(
                "a non-decision session cannot change the target weights."
            )
    data_path = Path(canonical_data_path)
    data_sha256 = _file_sha256(data_path, "canonical data")
    prices = _session_prices(data_path, symbols, session_date)

    asset_returns = {
        symbol: (prices[symbol]["close"] / prices[symbol]["prior_close"]) - _ONE
        for symbol in symbols
    }
    contributions = {
        symbol: prior_positions[symbol] * asset_returns[symbol] for symbol in symbols
    }
    gross = sum(contributions.values(), _ZERO)
    if gross <= -_ONE:
        raise ValidationError("observation would drive equity nonpositive.")

    drifted = {
        symbol: prior_positions[symbol] * (_ONE + asset_returns[symbol]) / (_ONE + gross)
        for symbol in symbols
    }
    prior_cash = _ONE - sum(drifted.values(), _ZERO)
    target_cash = _ONE - sum(resolved_targets.values(), _ZERO)
    turnover = (
        sum(
            (abs(resolved_targets[symbol] - drifted[symbol]) for symbol in symbols),
            _ZERO,
        )
        + abs(target_cash - prior_cash)
    ) / Decimal("2")
    cost_rate = _decimal(
        registration["cost_bps_per_one_way_turnover"], "cost rate"
    ) / Decimal("10000")
    cost = -turnover * cost_rate * (_ONE + gross)
    net = gross + cost
    if net <= -_ONE:
        raise ValidationError("observation would drive equity nonpositive after cost.")

    equity = prior_equity * (_ONE + net)
    peak = max(prior_peak, equity)
    drawdown = _ONE - (equity / peak)
    benchmark_symbol = str(registration["benchmark_symbol"])
    benchmark_return = asset_returns[benchmark_symbol]
    benchmark_equity = prior_benchmark_equity * (_ONE + benchmark_return)

    entry = {
        "record_type": "forward_shadow_observation",
        "sequence": sequence,
        "session": session_date.isoformat(),
        "recorded_at": moment.isoformat(),
        "is_decision": is_decision,
        "registration_fingerprint": registration["registration_fingerprint"],
        "canonical_data_sha256": data_sha256,
        "targets": {symbol: _text(resolved_targets[symbol]) for symbol in symbols},
        "positions": {symbol: _text(resolved_targets[symbol]) for symbol in symbols},
        "gross_return": _text(gross),
        "turnover": _text(turnover),
        "cost_contribution": _text(cost),
        "net_return": _text(net),
        "equity": _text(equity),
        "peak_equity": _text(peak),
        "drawdown": _text(drawdown),
        "benchmark_return": _text(benchmark_return),
        "benchmark_equity": _text(benchmark_equity),
        "previous_entry_sha256": previous_hash,
        "safety": dict(_ZERO_AUTHORITY),
    }
    entry["entry_sha256"] = _entry_hash(entry)
    with (target_root / _LEDGER_NAME).open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(_canonical_json(entry) + "\n")
    return entry


def load_forward_shadow_state(
    root: Path | str,
) -> tuple[Mapping[str, object], tuple[Mapping[str, object], ...]]:
    """Load the registration and verify the whole ledger chain, or fail closed."""

    target = _local_root(root)
    registration_path = target / _REGISTRATION_NAME
    ledger_path = target / _LEDGER_NAME
    if not registration_path.is_file():
        raise ValidationError("forward-shadow registration is missing.")
    if not ledger_path.is_file():
        raise ValidationError("forward-shadow ledger is missing.")

    registration = _load_json(registration_path)
    recorded_fingerprint = _validated_sha256(
        registration.get("registration_fingerprint"), "registration_fingerprint"
    )
    basis = {
        key: registration.get(key)
        for key in (
            "policy_fingerprint",
            "hypothesis_id",
            "hypothesis_statement",
            "universe",
            "benchmark_symbol",
            "rule_reference",
            "rule_fingerprint",
            "gates",
            "cohort_binding",
            "cost_bps_per_one_way_turnover",
            "registered_at",
            "registration_date",
            "first_admissible_session_exclusive",
        )
    }
    if _stable_hash(basis) != recorded_fingerprint:
        raise ValidationError(
            "registration fingerprint mismatch: the hypothesis, universe, "
            "costs, gates, sequential boundaries, or cohort binding were "
            "edited after registration."
        )
    policy = build_forward_shadow_policy()
    if registration.get("policy_fingerprint") != policy["policy_fingerprint"]:
        raise ValidationError("registration policy fingerprint mismatch.")

    entries: list[Mapping[str, object]] = []
    previous_hash = recorded_fingerprint
    previous_session: date | None = None
    registration_date = _required_date(
        registration["registration_date"], "registration_date"
    )
    for index, line in enumerate(
        ledger_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"ledger line {index} is not valid JSON.") from exc
        if not isinstance(entry, dict):
            raise ValidationError(f"ledger line {index} is not an object.")
        if entry.get("sequence") != index:
            raise ValidationError(f"ledger line {index} has a broken sequence.")
        if entry.get("previous_entry_sha256") != previous_hash:
            raise ValidationError(
                f"ledger line {index} breaks the hash chain; the ledger was "
                "reordered, truncated, or edited."
            )
        recorded_entry_hash = entry.get("entry_sha256")
        if recorded_entry_hash != _entry_hash(entry):
            raise ValidationError(f"ledger line {index} entry hash mismatch.")
        if entry.get("registration_fingerprint") != recorded_fingerprint:
            raise ValidationError(
                f"ledger line {index} is bound to a different registration."
            )
        if not isinstance(entry.get("is_decision"), bool):
            raise ValidationError(f"ledger line {index} lacks an is_decision flag.")
        session = _required_date(entry.get("session"), f"ledger line {index} session")
        if session <= registration_date:
            raise ValidationError(
                f"ledger line {index} contains a backfilled session."
            )
        if previous_session is not None and session <= previous_session:
            raise ValidationError(
                f"ledger line {index} is not in strictly increasing session order."
            )
        previous_session = session
        previous_hash = str(recorded_entry_hash)
        entries.append(entry)
    return registration, tuple(entries)


def evaluate_forward_shadow(
    root: Path | str,
    *,
    as_of: datetime | str,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Report accrual, or a verdict once a frozen stopping condition fires."""

    target = _local_root(root)
    registration, entries = load_forward_shadow_state(target)
    moment = _utc_datetime(as_of, "as_of")
    gates = dict(registration["gates"])
    sequential = dict(gates["sequential"])
    cohort = dict(registration["cohort_binding"])
    required = int(gates["minimum_decisions"])

    excesses = _decision_interval_excesses(entries)
    completed = len(excesses)
    decision_sessions = sum(1 for entry in entries if entry["is_decision"])
    sprt = _sprt_state(excesses, sequential, cohort)

    packet: dict[str, object] = {
        "schema_version": FORWARD_SHADOW_SCHEMA_VERSION,
        "record_type": "forward_shadow_status",
        "as_of": moment.isoformat(),
        "hypothesis_id": registration["hypothesis_id"],
        "registration_fingerprint": registration["registration_fingerprint"],
        "policy_fingerprint": registration["policy_fingerprint"],
        "rule_fingerprint": registration["rule_fingerprint"],
        "registered_at": registration["registered_at"],
        "observation_sessions": len(entries),
        "decision_sessions": decision_sessions,
        "completed_decision_intervals": completed,
        "required_decisions": required,
        "remaining_decisions": max(0, required - completed),
        "first_session": entries[0]["session"] if entries else "",
        "last_session": entries[-1]["session"] if entries else "",
        "ledger_head_sha256": (
            entries[-1]["entry_sha256"]
            if entries
            else registration["registration_fingerprint"]
        ),
        "gates": gates,
        "cohort_binding": cohort,
        "sequential_state": {
            "log_likelihood_ratio": sprt["llr"],
            "efficacy_boundary": sprt["efficacy_boundary"],
            "futility_boundary": sprt["futility_boundary"],
            "effective_alpha": cohort["effective_alpha"],
            "eligible_to_stop": sprt["eligible"],
            "boundary_crossed": sprt["boundary"],
        },
        "safety": dict(_ZERO_AUTHORITY),
    }

    stop_reason = sprt["boundary"] if sprt["eligible"] else None
    window_complete = completed >= required
    if stop_reason is None and not window_complete:
        packet.update(
            {
                "classification": "accruing_untouched_forward_evidence",
                "verdict_available": False,
                "metrics_withheld_until_stopping_condition": True,
                "principal_blocker": "insufficient_completed_decision_intervals",
                "next_action": (
                    "continue_appending_one_session_per_trading_day"
                ),
                "paper_promotion_allowed": False,
                "live_authorized": False,
            }
        )
    else:
        metrics = _terminal_metrics(entries, excesses)
        conditions = {
            "annualized_return_at_least_minimum": (
                _decimal(metrics["annualized_return"], "annualized_return")
                >= _decimal(gates["minimum_annualized_return"], "gate")
            ),
            "sharpe_at_least_minimum": (
                metrics["sharpe_ratio"] is not None
                and _decimal(metrics["sharpe_ratio"], "sharpe")
                >= _decimal(gates["minimum_sharpe_ratio"], "gate")
            ),
            "max_drawdown_within_limit": (
                _decimal(metrics["max_drawdown"], "max_drawdown")
                <= _decimal(gates["maximum_drawdown"], "gate")
            ),
            "benchmark_return_delta_at_least_minimum": (
                _decimal(metrics["benchmark_annualized_return_delta"], "delta")
                >= _decimal(
                    gates["minimum_benchmark_annualized_return_delta"], "gate"
                )
            ),
            "benchmark_sharpe_delta_at_least_minimum": (
                metrics["benchmark_sharpe_delta"] is not None
                and _decimal(metrics["benchmark_sharpe_delta"], "delta")
                >= _decimal(gates["minimum_benchmark_sharpe_delta"], "gate")
            ),
        }
        terminal_pass = all(conditions.values())
        if stop_reason == "futility":
            classification = "stopped_early_for_futility"
            passed = False
            next_action = "close_hypothesis_without_tuning"
        elif stop_reason == "efficacy":
            classification = "stopped_early_for_efficacy"
            passed = terminal_pass
            next_action = (
                "operator_review_of_completed_forward_evidence"
                if passed
                else "close_hypothesis_without_tuning"
            )
        else:
            classification = (
                "forward_evidence_complete_passed"
                if terminal_pass
                else "forward_evidence_complete_failed"
            )
            passed = terminal_pass
            next_action = (
                "operator_review_of_completed_forward_evidence"
                if passed
                else "close_hypothesis_without_tuning"
            )
        packet.update(
            {
                "classification": classification,
                "verdict_available": True,
                "metrics_withheld_until_stopping_condition": False,
                "stopping_reason": stop_reason or "planned_decision_count_reached",
                "metrics": metrics,
                "gate_conditions": conditions,
                "terminal_gates_passed": terminal_pass,
                "all_gates_passed": passed,
                "principal_blocker": "none" if passed else "frozen_gate_failed",
                "next_action": next_action,
                "paper_promotion_allowed": False,
                "live_authorized": False,
            }
        )

    if write_artifacts:
        _write_json_atomic(target / _STATUS_NAME, packet)
        _write_text_atomic(
            target / _STATUS_MARKDOWN_NAME, render_forward_shadow_markdown(packet)
        )
    return packet


def render_forward_shadow_markdown(packet: Mapping[str, object]) -> str:
    """Render a compact status receipt that never leaks withheld metrics."""

    sequential = dict(packet.get("sequential_state", {}))
    lines = [
        "# Forward shadow status",
        "",
        f"- Hypothesis: {packet.get('hypothesis_id', '')}",
        f"- Classification: {packet.get('classification', '')}",
        f"- Registered at: {packet.get('registered_at', '')}",
        (
            "- Completed decision intervals: "
            f"{packet.get('completed_decision_intervals', 0)}"
            f"/{packet.get('required_decisions', 0)}"
        ),
        f"- Observation sessions: {packet.get('observation_sessions', 0)}",
        f"- Registration fingerprint: {packet.get('registration_fingerprint', '')}",
        f"- Ledger head: {packet.get('ledger_head_sha256', '')}",
        f"- Effective alpha: {sequential.get('effective_alpha', '')}",
    ]
    if packet.get("verdict_available"):
        metrics = dict(packet.get("metrics", {}))
        lines.extend(
            [
                f"- Stopping reason: {packet.get('stopping_reason', '')}",
                f"- Annualized return: {metrics.get('annualized_return', '')}",
                f"- Sharpe: {metrics.get('sharpe_ratio', '')}",
                f"- Max drawdown: {metrics.get('max_drawdown', '')}",
                (
                    "- Benchmark annualized delta: "
                    f"{metrics.get('benchmark_annualized_return_delta', '')}"
                ),
                f"- All gates passed: {str(packet.get('all_gates_passed')).lower()}",
            ]
        )
    else:
        lines.append(
            "- Metrics: withheld until a frozen stopping condition fires"
        )
    lines.extend(
        [
            "- Network, credential, broker, paper mutation, and live: false",
            "- Paper promotion: not authorized",
            "- Profit claim: none",
            f"- Next action: {packet.get('next_action', '')}",
            "",
        ]
    )
    return "\n".join(lines)


def _cohort_binding(
    cohort_root: Path | str | None,
    gates: ForwardShadowGates,
) -> dict[str, object]:
    alpha = _decimal(gates.sequential.alpha, "alpha")
    if cohort_root is None:
        return {
            "cohort_id": "",
            "cohort_fingerprint": "",
            "planned_member_count": 1,
            "family_wise_alpha": gates.sequential.alpha,
            "correction": "none",
            "effective_alpha": gates.sequential.alpha,
        }
    root = _local_root(cohort_root)
    cohort = _load_json(root / _COHORT_NAME)
    planned = int(cohort["planned_member_count"])
    correction = str(cohort["correction"])
    family_alpha = _decimal(cohort["family_wise_alpha"], "family_wise_alpha")
    if correction == "bonferroni":
        effective = family_alpha / Decimal(planned)
    else:
        effective = family_alpha
    if effective <= _ZERO or effective >= _ONE:
        raise ValidationError("effective alpha left the open interval (0, 1).")
    del alpha
    return {
        "cohort_id": str(cohort["cohort_id"]),
        "cohort_fingerprint": str(cohort["cohort_fingerprint"]),
        "planned_member_count": planned,
        "family_wise_alpha": _text(family_alpha),
        "correction": correction,
        "effective_alpha": _text(effective),
    }


def _append_cohort_member(
    cohort_root: Path,
    *,
    hypothesis_id: str,
    registration_fingerprint: str,
    registered_at: datetime,
) -> None:
    cohort = _load_json(cohort_root / _COHORT_NAME)
    planned = int(cohort["planned_member_count"])
    members_path = cohort_root / _COHORT_MEMBERS_NAME
    existing = [
        line
        for line in members_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(existing) >= planned:
        raise ValidationError(
            "cohort is full: registering more members than the frozen planned "
            "count would invalidate the multiplicity correction."
        )
    for line in existing:
        payload = json.loads(line)
        if payload.get("hypothesis_id") == hypothesis_id:
            raise ValidationError("hypothesis is already a member of this cohort.")
    record = {
        "hypothesis_id": hypothesis_id,
        "registration_fingerprint": registration_fingerprint,
        "registered_at": registered_at.isoformat(),
        "cohort_fingerprint": cohort["cohort_fingerprint"],
    }
    with members_path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(_canonical_json(record) + "\n")


def _decision_interval_excesses(
    entries: Sequence[Mapping[str, object]],
) -> tuple[Decimal, ...]:
    """Excess return of each completed decision interval.

    A decision recorded at session d takes effect from the next session and is
    held until the next decision session inclusive. Only intervals closed by a
    subsequent decision are counted, so an open position never contributes
    evidence.
    """

    marks = [index for index, entry in enumerate(entries) if entry["is_decision"]]
    excesses: list[Decimal] = []
    for start, end in zip(marks, marks[1:]):
        segment = entries[start + 1 : end + 1]
        if not segment:
            continue
        strategy = _ONE
        benchmark = _ONE
        for entry in segment:
            strategy *= _ONE + _decimal(entry["net_return"], "net_return")
            benchmark *= _ONE + _decimal(entry["benchmark_return"], "benchmark_return")
        excesses.append((strategy - _ONE) - (benchmark - _ONE))
    return tuple(excesses)


def _sprt_state(
    excesses: Sequence[Decimal],
    sequential: Mapping[str, object],
    cohort: Mapping[str, object],
) -> dict[str, object]:
    effective_alpha = float(_decimal(cohort["effective_alpha"], "effective_alpha"))
    beta = float(_decimal(sequential["beta"], "beta"))
    effect = float(
        _decimal(sequential["minimum_excess_per_decision"], "effect")
    )
    sigma = float(_decimal(sequential["reference_excess_sigma"], "sigma"))
    minimum = int(sequential["minimum_decisions_before_stopping"])

    efficacy = math.log((1.0 - beta) / effective_alpha)
    futility = math.log(beta / (1.0 - effective_alpha))
    llr = 0.0
    for value in excesses:
        llr += effect * (float(value) - effect / 2.0) / (sigma * sigma)

    boundary: str | None = None
    eligible = len(excesses) >= minimum
    if eligible:
        if llr >= efficacy:
            boundary = "efficacy"
        elif llr <= futility:
            boundary = "futility"
    return {
        "llr": _text(Decimal(repr(llr))),
        "efficacy_boundary": _text(Decimal(repr(efficacy))),
        "futility_boundary": _text(Decimal(repr(futility))),
        "eligible": eligible and boundary is not None,
        "boundary": boundary,
    }


def _terminal_metrics(
    entries: Sequence[Mapping[str, object]],
    excesses: Sequence[Decimal],
) -> dict[str, object]:
    returns = [_decimal(entry["net_return"], "net_return") for entry in entries]
    benchmark_returns = [
        _decimal(entry["benchmark_return"], "benchmark_return") for entry in entries
    ]
    positive = sum(1 for value in excesses if value > _ZERO)
    return {
        "session_count": len(entries),
        "completed_decision_intervals": len(excesses),
        "first_session": entries[0]["session"],
        "last_session": entries[-1]["session"],
        "total_return": _text(_decimal(entries[-1]["equity"], "equity") - _ONE),
        "annualized_return": _text(_annualized(returns)),
        "sharpe_ratio": _optional_text(_sharpe(returns)),
        "max_drawdown": _text(
            max(_decimal(entry["drawdown"], "drawdown") for entry in entries)
        ),
        "benchmark_total_return": _text(
            _decimal(entries[-1]["benchmark_equity"], "benchmark_equity") - _ONE
        ),
        "benchmark_annualized_return": _text(_annualized(benchmark_returns)),
        "benchmark_sharpe_ratio": _optional_text(_sharpe(benchmark_returns)),
        "benchmark_annualized_return_delta": _text(
            _annualized(returns) - _annualized(benchmark_returns)
        ),
        "benchmark_sharpe_delta": _optional_text(
            None
            if _sharpe(returns) is None or _sharpe(benchmark_returns) is None
            else _sharpe(returns) - _sharpe(benchmark_returns)
        ),
        "mean_decision_excess": _text(
            sum(excesses, _ZERO) / Decimal(len(excesses)) if excesses else _ZERO
        ),
        "positive_decision_intervals": positive,
        "cumulative_turnover": _text(
            sum((_decimal(entry["turnover"], "turnover") for entry in entries), _ZERO)
        ),
    }


def _annualized(returns: Sequence[Decimal]) -> Decimal:
    if not returns:
        return _ZERO
    log_sum = math.fsum(math.log1p(float(value)) for value in returns)
    scaled = log_sum * float(_TRADING_DAYS_PER_YEAR) / len(returns)
    return _quantize(Decimal(repr(math.expm1(scaled))))


def _sharpe(returns: Sequence[Decimal]) -> Decimal | None:
    if len(returns) < 2:
        return None
    values = [float(value) for value in returns]
    mean = math.fsum(values) / len(values)
    variance = math.fsum((value - mean) ** 2 for value in values) / (len(values) - 1)
    if variance <= 0.0:
        return None
    deviation = math.sqrt(variance)
    return _quantize(
        Decimal(repr(mean / deviation * math.sqrt(float(_TRADING_DAYS_PER_YEAR))))
    )


def _session_prices(
    data_path: Path,
    symbols: Sequence[str],
    session: date,
) -> dict[str, dict[str, Decimal]]:
    prices: dict[str, dict[str, Decimal]] = {}
    for symbol in symbols:
        bars = load_local_daily_bars_csv(
            data_path, symbol=symbol, as_of=session
        ).usable_bars
        if len(bars) < 2:
            raise ValidationError(f"{symbol} lacks a prior session before {session}.")
        if bars[-1].date != session:
            raise ValidationError(
                f"{symbol} has no admitted bar for session {session.isoformat()}."
            )
        close = Decimal(str(bars[-1].adjusted_close))
        prior_close = Decimal(str(bars[-2].adjusted_close))
        if close <= _ZERO or prior_close <= _ZERO:
            raise ValidationError(f"{symbol} has a nonpositive adjusted close.")
        prices[symbol] = {"close": close, "prior_close": prior_close}
    return prices


def _validated_universe(universe: Sequence[str]) -> tuple[str, ...]:
    if isinstance(universe, (str, bytes)) or not isinstance(universe, Sequence):
        raise ValidationError("universe must be a sequence of symbols.")
    symbols = tuple(_required_text(item, "universe symbol").upper() for item in universe)
    if not symbols:
        raise ValidationError("universe must not be empty.")
    if len(set(symbols)) != len(symbols):
        raise ValidationError("universe contains duplicate symbols.")
    return symbols


def _validated_targets(
    targets: Mapping[str, object],
    symbols: Sequence[str],
) -> dict[str, Decimal]:
    if not isinstance(targets, Mapping):
        raise ValidationError("targets must be a mapping.")
    unknown = set(str(key).upper() for key in targets) - set(symbols)
    if unknown:
        raise ValidationError(
            f"targets contain symbols outside the frozen universe: {sorted(unknown)}"
        )
    resolved = {symbol: _ZERO for symbol in symbols}
    for key, value in targets.items():
        resolved[str(key).upper()] = _decimal(value, f"target {key}")
    for symbol, weight in resolved.items():
        if weight < _ZERO:
            raise ValidationError(f"target weight for {symbol} is negative.")
    total = sum(resolved.values(), _ZERO)
    if total > _ONE:
        raise ValidationError("target weights must leave nonnegative implicit cash.")
    return resolved


def _entry_hash(entry: Mapping[str, object]) -> str:
    payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
    return _stable_hash(payload)


def _canonical_json(value: Mapping[str, object]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _stable_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path, label: str) -> str:
    if not path.is_file():
        raise ValidationError(f"{label} file is missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValidationError(f"required JSON file is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError(f"JSON payload must be an object: {path}")
    return payload


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_QUANTUM)


def _text(value: Decimal) -> str:
    return format(_quantize(value), "f")


def _optional_text(value: Decimal | None) -> str | None:
    return None if value is None else _text(value)


def _decimal(value: object, label: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{label} must be a decimal number.") from exc
    if not parsed.is_finite():
        raise ValidationError(f"{label} must be finite.")
    return parsed


def _decimal_text(value: object, label: str) -> str:
    return _text(_decimal(value, label))


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be non-empty text.")
    return value.strip()


def _validated_sha256(value: object, label: str) -> str:
    text = _required_text(value, label).lower()
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ValidationError(f"{label} must be lowercase SHA-256 text.")
    return text


def _required_date(value: object, label: str) -> date:
    if isinstance(value, datetime):
        raise ValidationError(f"{label} must be a calendar date, not a timestamp.")
    if isinstance(value, date):
        return value
    text = _required_text(value, label)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{label} must be an ISO-8601 date.") from exc


def _utc_datetime(value: object, label: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = _required_text(value, label)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValidationError(f"{label} must be ISO-8601.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"{label} must include a UTC offset.")
    return parsed.astimezone(UTC)


def _local_root(value: Path | str) -> Path:
    path = Path(value)
    if str(path).startswith(("\\\\", "//")):
        raise ValidationError("root must be a local path.")
    return path


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    _write_text_atomic(
        path, json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    )


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forward-shadow",
        description=(
            "Register, accrue, and report a no-submit forward shadow on data "
            "that did not exist at registration."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    policy = sub.add_parser("policy", help="print the frozen policy contract")
    policy.add_argument("--format", choices=("json", "text"), default="json")

    status = sub.add_parser("status", help="report accrual or a terminal verdict")
    status.add_argument("--root", required=True)
    status.add_argument("--as-of", required=True)
    status.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "policy":
            payload: Mapping[str, object] = build_forward_shadow_policy()
            print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
            return 0
        packet = evaluate_forward_shadow(args.root, as_of=args.as_of)
    except (OSError, ValidationError, RuntimeError) as exc:
        print(f"forward_shadow_status=blocked:{exc}")
        return 2
    if args.format == "json":
        print(json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=True))
    else:
        print(render_forward_shadow_markdown(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
