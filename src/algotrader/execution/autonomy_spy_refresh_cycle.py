"""Authorized SPY market-data refresh followed by one offline self-refresh cycle.

This is the narrow integration seam between the V5.51 read-only Tiingo fetch
and the V5.52 operator-input-bound offline executor.  The network stage keeps
its existing exact endpoint, finite-cap, credential-provider, interlock, and
audit boundaries.  Only its canonical adjusted SPY CSV crosses into the
offline stage.  The offline stage receives an empty environment mapping, so
paper-profile and credential variables cannot reach the M441-M444 subprocess.

The seam performs no broker or account access and no order, position, capital,
paper, or live mutation.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
import sys
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.autonomy_offline_executor import OfflineOperatorInputs
from algotrader.execution.autonomy_read_only_network_executor import (
    run_autonomy_read_only_network_executor,
)
from algotrader.execution.autonomy_self_refresh_cycle import build_self_refresh_cycle
from algotrader.execution.autonomy_supervisor import AutonomySupervisorConfig
from algotrader.execution.spy_decision_time_shadow import (
    reconcile_spy_decision_time_shadow,
)

__all__ = [
    "AUTONOMY_SPY_REFRESH_ACTION_TOKEN",
    "CANONICAL_SPY_DAILY_BARS_RELPATH",
    "CANONICAL_SPY_DAILY_CYCLE_MANIFEST_RELPATH",
    "main",
    "run_autonomy_spy_refresh_cycle",
]

AUTONOMY_SPY_REFRESH_ACTION_TOKEN = "run_authorized_read_only_spy_refresh_cycle"
CANONICAL_SPY_DAILY_BARS_RELPATH = Path(
    "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
)
CANONICAL_SPY_DAILY_CYCLE_MANIFEST_RELPATH = Path(
    "runs/paper_lab/m444_offline_daily_cycle_run.jsonl"
)

_NETWORK_RESULT_KEYS = frozenset(
    {
        "action_token",
        "adapter_refresh_state",
        "apply",
        "apply_eligible",
        "as_of",
        "attempt_number",
        "exit_code",
        "interlock_verdict",
        "network_access_attempted",
        "refusal_category",
        "run_id",
        "session_already_qualified",
        "session_id",
    }
)
_INTERLOCK_RESULT_KEYS = frozenset(
    {
        "app_profile",
        "blockers",
        "broker_action_performed",
        "credential_access_attempted",
        "endpoint_class",
        "expected_paper_account_present",
        "live_authorized",
        "live_signals",
        "mutated",
        "network_access_attempted",
        "paper_boundary_ok",
        "paper_endpoint_ok",
        "profile_is_paper",
        "submitted",
    }
)
_SELF_REFRESH_RESULT_KEYS = (
    "run_id",
    "as_of",
    "apply",
    "operator_inputs_provided",
    "operator_input_bound_actions",
    "before_system_status",
    "before_plan_class",
    "eligible_count",
    "execution_count",
    "all_executions_succeeded",
    "after_system_status",
    "cycle_outcome",
    "converged",
    "refreshed_lanes",
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_SHADOW_RECONCILIATION_RESULT_KEYS = (
    "milestone",
    "mode",
    "state",
    "session_id",
    "observed_at",
    "classification",
    "provisional_decision",
    "authoritative_decision",
    "canonical_latest_bar_date",
    "provisional_receipt_path",
    "reconciliation_receipt_path",
    "network_access_attempted",
    "credential_access_attempted",
    "broker_access_attempted",
    "broker_mutation_performed",
    "paper_submit_performed",
    "submitted",
    "mutated",
    "live_trading_performed",
    "live_authorized",
    "profit_claim",
    "refusal_category",
    "exit_code",
)


def run_autonomy_spy_refresh_cycle(
    *,
    as_of: str,
    apply: bool = False,
    format: str = "json",
    network_runner=None,
    self_refresh_builder=None,
    shadow_reconciler=None,
) -> dict[str, Any]:
    """Run read-only refresh -> canonical CSV -> offline M444 self-refresh."""

    if type(as_of) is not str or not as_of.strip():
        return _refusal("as_of_invalid")
    if type(apply) is not bool:
        return _refusal("apply_invalid")
    if format != "json":
        return _refusal("format_invalid")

    try:
        root = _canonical_root()
    except ValidationError:
        return _refusal("noncanonical_target")

    active_network_runner = (
        run_autonomy_read_only_network_executor
        if network_runner is None
        else network_runner
    )
    try:
        raw_network = active_network_runner(
            as_of=as_of,
            apply=apply,
            format="json",
        )
    except Exception:  # noqa: BLE001 - fail closed without leaking exception text
        return _refusal("network_executor_internal_failure")
    if not isinstance(raw_network, Mapping):
        return _refusal("network_result_invalid")

    network = _network_summary(raw_network)
    result = _base_result(apply=apply)
    result["network_refresh"] = network
    result["network_access_attempted"] = (
        network.get("network_access_attempted") is True
    )
    result["credential_access_attempted"] = _credential_access_attempted(network)

    network_exit = network.get("exit_code")
    if type(network_exit) is not int or network_exit not in (0, 1, 2):
        result.update(
            {
                "stage_status": "network_refused",
                "observable_outcome": "network_result_invalid",
                "refusal_category": "network_result_invalid",
                "exit_code": 2,
            }
        )
        return result
    if network_exit != 0:
        refusal = network.get("refusal_category")
        result.update(
            {
                "stage_status": (
                    "network_dry_run_preview"
                    if network_exit == 1 and not apply
                    else "network_refused"
                ),
                "observable_outcome": (
                    "network_dry_run_preview"
                    if network_exit == 1 and not apply
                    else "network_refresh_not_accepted"
                ),
                "refusal_category": (
                    str(refusal) if isinstance(refusal, str) and refusal else None
                ),
                "exit_code": network_exit,
            }
        )
        return result

    adapter_state = network.get("adapter_refresh_state")
    accepted = (
        isinstance(adapter_state, str)
        and adapter_state.startswith("accepted")
    )
    already_qualified = network.get("session_already_qualified") is True
    if not accepted and not already_qualified:
        result.update(
            {
                "stage_status": "network_refused",
                "observable_outcome": "network_result_invalid",
                "refusal_category": "network_result_invalid",
                "exit_code": 2,
            }
        )
        return result

    canonical_csv = (root / CANONICAL_SPY_DAILY_BARS_RELPATH).resolve()
    try:
        canonical_csv.relative_to(root)
    except ValueError:
        result.update(
            {
                "stage_status": "offline_refused",
                "observable_outcome": "canonical_daily_bars_noncanonical",
                "refusal_category": "canonical_daily_bars_noncanonical",
                "exit_code": 2,
            }
        )
        return result
    if not canonical_csv.is_file():
        result.update(
            {
                "stage_status": "offline_refused",
                "observable_outcome": "canonical_daily_bars_missing",
                "refusal_category": "canonical_daily_bars_missing",
                "exit_code": 2,
            }
        )
        return result

    session_id = network.get("session_id")
    normalized_as_of = network.get("as_of")
    if (
        not isinstance(session_id, str)
        or not session_id
        or not isinstance(normalized_as_of, str)
        or not normalized_as_of
    ):
        result.update(
            {
                "stage_status": "offline_refused",
                "observable_outcome": "network_result_invalid",
                "refusal_category": "network_result_invalid",
                "exit_code": 2,
            }
        )
        return result

    config = AutonomySupervisorConfig(
        run_id=f"v5.53-spy-{session_id}",
        as_of=normalized_as_of,
        lanes_root="runs",
    )
    operator_inputs = OfflineOperatorInputs(
        validated_at=normalized_as_of,
        daily_bars_csv=canonical_csv,
    )
    active_self_refresh_builder = (
        build_self_refresh_cycle
        if self_refresh_builder is None
        else self_refresh_builder
    )
    try:
        raw_cycle = active_self_refresh_builder(
            config,
            apply=apply,
            operator_inputs=operator_inputs,
            # This explicit empty mapping is the trust-domain boundary: none of
            # the network stage's profile or credential variables can reach the
            # offline executor or its M441-M444 child process.
            environ={},
        )
    except Exception:  # noqa: BLE001 - fail closed without leaking exception text
        result.update(
            {
                "stage_status": "offline_refused",
                "observable_outcome": "offline_self_refresh_internal_failure",
                "refusal_category": "offline_self_refresh_internal_failure",
                "exit_code": 2,
            }
        )
        return result
    if not isinstance(raw_cycle, Mapping):
        result.update(
            {
                "stage_status": "offline_refused",
                "observable_outcome": "offline_self_refresh_result_invalid",
                "refusal_category": "offline_self_refresh_result_invalid",
                "exit_code": 2,
            }
        )
        return result

    cycle = _self_refresh_summary(raw_cycle)
    result["offline_self_refresh"] = cycle
    execution_count = cycle.get("execution_count")
    all_succeeded = cycle.get("all_executions_succeeded")
    converged = cycle.get("converged") is True
    valid_execution_count = (
        type(execution_count) is int and execution_count >= 0
    )
    execution_succeeded = valid_execution_count and (
        (execution_count == 0 and all_succeeded is None)
        or (execution_count > 0 and all_succeeded is True)
    )
    refreshed_lanes = cycle.get("refreshed_lanes")
    spy_refreshed = (
        isinstance(refreshed_lanes, list)
        and "spy_offline_daily_cycle" in refreshed_lanes
    )
    result["spy_daily_cycle_refreshed"] = spy_refreshed
    result["m444_manifest"] = (
        CANONICAL_SPY_DAILY_CYCLE_MANIFEST_RELPATH.as_posix()
    )

    if not execution_succeeded:
        result.update(
            {
                "stage_status": "offline_failed",
                "observable_outcome": "offline_execution_failed",
                "refusal_category": None,
                "exit_code": 1,
            }
        )
    elif not converged:
        result.update(
            {
                "stage_status": "offline_incomplete",
                "observable_outcome": "cycle_not_converged",
                "refusal_category": None,
                "exit_code": 1,
            }
        )
    elif spy_refreshed:
        result.update(
            {
                "stage_status": "completed",
                "observable_outcome": "m444_refreshed_nominal",
                "refusal_category": None,
                "exit_code": 0,
            }
        )
    else:
        result.update(
            {
                "stage_status": "completed",
                "observable_outcome": "cycle_converged_no_spy_refresh",
                "refusal_category": None,
                "exit_code": 0,
            }
        )
    if apply and result["exit_code"] == 0:
        active_shadow_reconciler = (
            reconcile_spy_decision_time_shadow
            if shadow_reconciler is None
            else shadow_reconciler
        )
        try:
            raw_shadow = active_shadow_reconciler(
                session_id=session_id,
                as_of=normalized_as_of,
            )
        except Exception:  # noqa: BLE001 - never echo credential-bearing details
            result["decision_time_shadow"] = {
                "state": "reconciliation_internal_failure",
                "network_access_attempted": False,
                "credential_access_attempted": False,
                "broker_access_attempted": False,
                "broker_mutation_performed": False,
                "paper_submit_performed": False,
                "submitted": False,
                "mutated": False,
                "live_trading_performed": False,
                "live_authorized": False,
                "profit_claim": "none",
                "exit_code": 2,
            }
        else:
            result["decision_time_shadow"] = (
                _shadow_reconciliation_summary(raw_shadow)
                if isinstance(raw_shadow, Mapping)
                else {
                    "state": "reconciliation_result_invalid",
                    "network_access_attempted": False,
                    "credential_access_attempted": False,
                    "broker_access_attempted": False,
                    "broker_mutation_performed": False,
                    "paper_submit_performed": False,
                    "submitted": False,
                    "mutated": False,
                    "live_trading_performed": False,
                    "live_authorized": False,
                    "profit_claim": "none",
                    "exit_code": 2,
                }
            )
    return result


def _canonical_root() -> Path:
    root = Path.cwd().resolve()
    if not (root / "pyproject.toml").is_file():
        raise ValidationError("noncanonical_target")
    if not (root / "src" / "algotrader").is_dir():
        raise ValidationError("noncanonical_target")
    return root


def _network_summary(value: Mapping[str, object]) -> dict[str, Any]:
    summary = {
        key: _json_safe(item)
        for key, item in value.items()
        if key in _NETWORK_RESULT_KEYS
    }
    verdict = summary.get("interlock_verdict")
    if isinstance(verdict, Mapping):
        summary["interlock_verdict"] = {
            key: _json_safe(item)
            for key, item in verdict.items()
            if key in _INTERLOCK_RESULT_KEYS
        }
    elif verdict is not None:
        summary["interlock_verdict"] = None
    return summary


def _self_refresh_summary(value: Mapping[str, object]) -> dict[str, Any]:
    return {
        key: _json_safe(value[key])
        for key in _SELF_REFRESH_RESULT_KEYS
        if key in value
    }


def _shadow_reconciliation_summary(
    value: Mapping[str, object],
) -> dict[str, Any]:
    return {
        key: _json_safe(value[key])
        for key in _SHADOW_RECONCILIATION_RESULT_KEYS
        if key in value
    }


def _credential_access_attempted(network: Mapping[str, object]) -> bool:
    if network.get("network_access_attempted") is True:
        return True
    return network.get("refusal_category") == "token_not_available"


def _base_result(*, apply: bool) -> dict[str, Any]:
    return {
        "action_token": AUTONOMY_SPY_REFRESH_ACTION_TOKEN,
        "apply": apply,
        "canonical_daily_bars_csv": CANONICAL_SPY_DAILY_BARS_RELPATH.as_posix(),
        "offline_environment_sanitized": True,
        "stage_status": "not_started",
        "observable_outcome": "not_started",
        "refusal_category": None,
        "spy_daily_cycle_refreshed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "broker_access_attempted": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "submitted": False,
        "mutated": False,
        "live_trading_performed": False,
        "live_authorized": False,
        "profit_claim": "none",
        "decision_time_shadow": {
            "state": "not_evaluated",
            "network_access_attempted": False,
            "credential_access_attempted": False,
            "broker_access_attempted": False,
            "broker_mutation_performed": False,
            "paper_submit_performed": False,
            "submitted": False,
            "mutated": False,
            "live_trading_performed": False,
            "live_authorized": False,
            "profit_claim": "none",
        },
        "exit_code": 2,
    }


def _refusal(category: str) -> dict[str, Any]:
    result = _base_result(apply=False)
    result.update(
        {
            "stage_status": "refused",
            "observable_outcome": category,
            "refusal_category": category,
            "exit_code": 2,
        }
    )
    return result


def _json_safe(value: object) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValidationError("parser_invalid_argument")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _SanitizedArgumentParser(
        description=(
            "Run one authorized read-only SPY refresh and bind its canonical "
            "CSV into the offline M444 self-refresh cycle."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--as-of", required=True, help="ISO-8601 UTC timestamp")
    parser.add_argument("--apply", action="store_true", default=False)
    parser.add_argument("--format", choices=["json"], default="json")
    try:
        args, unknown = parser.parse_known_args(argv)
        if unknown:
            raise ValidationError("parser_invalid_argument")
    except ValidationError:
        result = _refusal("parser_invalid_argument")
    else:
        result = run_autonomy_spy_refresh_cycle(
            as_of=args.as_of,
            apply=args.apply,
            format=args.format,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return int(result["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
