"""Single operator entrypoint for the bounded paper-autopilot loop.

The operator layer composes the v2.07 loop and v2.08 durable history. It does
not add any broker surface; all broker-facing behavior remains inside the
bounded paper-autopilot loop.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.paper_autopilot_history import (
    PaperAutopilotHistoryConfig,
    paper_autopilot_history_exit_status,
    update_paper_autopilot_operating_history,
)
from algotrader.execution.paper_autopilot_loop import (
    BrokerClientFactory,
    DailyLabRunner,
    PaperAutopilotLoopConfig,
    paper_autopilot_loop_exit_status,
    run_paper_autopilot_loop,
)


PAPER_AUTOPILOT_OPERATOR_SCHEMA_VERSION = "v209_paper_autopilot_operator_v1"
PAPER_AUTOPILOT_OPERATOR_COMMAND = "paper-autopilot-operator"

_SUMMARY_FIELDS = (
    "classification",
    "autonomy_status",
    "autonomy_next_action",
    "readiness_status",
    "readiness_blockers",
    "required_operator_action",
    "readiness_packet_generated",
    "paper_mutation_readiness_packet",
    "changed_since_previous",
    "hard_stop",
    "attention_required",
    "reason_codes",
    "final_supervisor_classification",
    "run_id",
    "as_of_date",
    "latest_bar_date",
    "data_refresh_status",
    "data_freshness_status",
    "symbol",
    "sma_posture",
    "selected_strategy_id",
    "operating_mode",
    "no_submit_mode",
    "broker_state_mode",
    "broker_read_performed",
    "broker_state_observed",
    "expected_account_matched",
    "spy_position_observed",
    "spy_position_quantity",
    "open_spy_orders_observed",
    "unexpected_non_spy_positions_count",
    "unexpected_non_spy_positions",
    "pre_broker_daily_cycle_status",
    "pre_broker_daily_cycle_classification",
    "blocker_status",
    "final_supervisor_status",
    "broker_observed_supervisor_status",
    "execution_plan_action",
    "action_decision",
    "paper_mutation_readiness_packet_consumed",
    "paper_mutation_readiness_gate_status",
    "paper_mutation_readiness_status",
    "paper_mutation_source_autonomy_status",
    "vol_scaled_preview_visible",
    "vol_scaled_preview_intended_action",
    "vol_scaled_preview_mutation_allowed",
    "vol_scaled_preview_submit_allowed",
    "vol_scaled_preview_non_mutation_status",
    "paper_submit_performed",
    "broker_mutation_performed",
    "live_mutation_performed",
    "reconciliation_status",
    "anomaly_classification",
    "next_operator_action",
    "final_operator_action",
)

LoopRunner = Callable[..., Mapping[str, Any]]
HistoryUpdater = Callable[[PaperAutopilotHistoryConfig], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class PaperAutopilotOperatorConfig:
    """Configuration for one operator-facing paper-autopilot run."""

    output_root: Path | str = "runs/paper_autopilot/latest"
    bars_csv: Path | str = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
    history_root: Path | str | None = None
    as_of_date: str | None = None
    run_date: str | None = None
    symbol: str = "SPY"
    sma_fast_window: int = 50
    sma_slow_window: int = 200
    max_notional: str = "25.00"
    no_submit: bool = False
    readiness_packet_path: Path | str | None = None

    def __post_init__(self) -> None:
        loop_config = self.to_loop_config()
        object.__setattr__(self, "output_root", loop_config.output_root)
        object.__setattr__(self, "bars_csv", loop_config.bars_csv)
        if self.history_root is None:
            history_root = Path(loop_config.output_root).parent / "history"
        else:
            history_root = _path(self.history_root, "history_root")
        object.__setattr__(self, "history_root", history_root)

    def to_loop_config(self) -> PaperAutopilotLoopConfig:
        return PaperAutopilotLoopConfig(
            output_root=self.output_root,
            bars_csv=self.bars_csv,
            as_of_date=self.as_of_date,
            run_date=self.run_date,
            symbol=self.symbol,
            sma_fast_window=self.sma_fast_window,
            sma_slow_window=self.sma_slow_window,
            max_notional=self.max_notional,
            no_submit=self.no_submit,
            readiness_packet_path=self.readiness_packet_path,
        )


def run_paper_autopilot_operator(
    config: PaperAutopilotOperatorConfig | None = None,
    *,
    env: Mapping[str, str] | None = None,
    broker_client_factory: BrokerClientFactory | None = None,
    daily_lab_runner: DailyLabRunner | None = None,
    timestamp: str | None = None,
    loop_runner: LoopRunner | None = None,
    history_updater: HistoryUpdater | None = None,
) -> dict[str, Any]:
    """Run the loop, update durable history once, and return operator status."""

    resolved = config or PaperAutopilotOperatorConfig()
    output_root = Path(resolved.output_root)
    latest_status_path = output_root / "latest_status.json"
    missing_status_path = output_root / ".missing_latest_status.json"
    loop_config = resolved.to_loop_config()
    runner = loop_runner or run_paper_autopilot_loop
    updater = history_updater or update_paper_autopilot_operating_history

    loop_record: Mapping[str, Any] = {}
    loop_error = ""
    loop_exit_code = 0
    try:
        loop_record = runner(
            loop_config,
            env=env,
            broker_client_factory=broker_client_factory,
            daily_lab_runner=daily_lab_runner,
            timestamp=timestamp,
            update_history=False,
        )
        loop_exit_code = paper_autopilot_loop_exit_status(loop_record)
    except Exception as exc:
        loop_error = _safe_error_text(exc)
        loop_exit_code = 2

    status_path_for_history = (
        latest_status_path
        if not loop_error and latest_status_path.is_file()
        else missing_status_path
    )
    rollup = dict(
        updater(
            PaperAutopilotHistoryConfig(
                latest_status_path=status_path_for_history,
                history_root=resolved.history_root,
            )
        )
    )
    history_exit_code = paper_autopilot_history_exit_status(rollup)
    operator_exit_code = history_exit_code if history_exit_code != 0 else loop_exit_code
    summary = build_paper_autopilot_operator_summary(
        rollup,
        operator_exit_code=operator_exit_code,
    )

    return {
        "schema_version": PAPER_AUTOPILOT_OPERATOR_SCHEMA_VERSION,
        "command": PAPER_AUTOPILOT_OPERATOR_COMMAND,
        "loop_exit_code": loop_exit_code,
        "history_exit_code": history_exit_code,
        "operator_exit_code": operator_exit_code,
        "loop_error": loop_error,
        "latest_status_path": str(latest_status_path),
        "history_root": str(resolved.history_root),
        "rollup": rollup,
        "operator_summary": summary,
        "loop_record": dict(loop_record),
    }


def build_paper_autopilot_operator_summary(
    rollup: Mapping[str, Any],
    *,
    operator_exit_code: int,
) -> dict[str, Any]:
    """Build the compact machine-readable operator summary."""

    classification = _text(rollup.get("classification"))
    summary = {
        "classification": classification,
        "autonomy_status": _text(rollup.get("autonomy_status")),
        "autonomy_next_action": _text(rollup.get("autonomy_next_action")),
        "readiness_status": _text(rollup.get("readiness_status")),
        "readiness_blockers": list(_string_list(rollup.get("readiness_blockers"))),
        "required_operator_action": _text(rollup.get("required_operator_action")),
        "readiness_packet_generated": (
            rollup.get("readiness_packet_generated") is True
        ),
        "paper_mutation_readiness_packet": _text(
            _mapping(rollup.get("artifact_paths")).get(
                "paper_mutation_readiness_packet"
            )
        ),
        "changed_since_previous": rollup.get("changed_since_previous") is True,
        "hard_stop": rollup.get("hard_stop") is True,
        "attention_required": rollup.get("attention_required") is True,
        "reason_codes": list(_string_list(rollup.get("reason_codes"))),
        "final_supervisor_classification": _text(
            rollup.get("final_supervisor_classification")
        ),
        "run_id": _text(rollup.get("run_id")),
        "as_of_date": _text(rollup.get("as_of_date")),
        "latest_bar_date": _text(rollup.get("latest_bar_date")),
        "data_refresh_status": _text(rollup.get("data_refresh_status")),
        "data_freshness_status": _text(rollup.get("data_freshness_status")),
        "symbol": _text(rollup.get("symbol")),
        "sma_posture": _text(rollup.get("sma_posture")),
        "selected_strategy_id": _text(rollup.get("selected_strategy_id")),
        "operating_mode": _text(rollup.get("operating_mode")),
        "no_submit_mode": rollup.get("no_submit_mode") is True,
        "broker_state_mode": _text(rollup.get("broker_state_mode")),
        "broker_read_performed": rollup.get("broker_read_performed") is True,
        "broker_state_observed": rollup.get("broker_state_observed") is True,
        "expected_account_matched": rollup.get("expected_account_matched"),
        "spy_position_observed": rollup.get("spy_position_observed") is True,
        "spy_position_quantity": _text(rollup.get("spy_position_quantity")),
        "open_spy_orders_observed": rollup.get("open_spy_orders_observed") or 0,
        "unexpected_non_spy_positions_count": (
            rollup.get("unexpected_non_spy_positions_count") or 0
        ),
        "unexpected_non_spy_positions": list(
            _string_list(rollup.get("unexpected_non_spy_positions"))
        ),
        "pre_broker_daily_cycle_status": _text(
            rollup.get("pre_broker_daily_cycle_status")
        ),
        "pre_broker_daily_cycle_classification": _text(
            rollup.get("pre_broker_daily_cycle_classification")
        ),
        "blocker_status": _text(rollup.get("blocker_status")),
        "final_supervisor_status": _text(rollup.get("final_supervisor_status")),
        "broker_observed_supervisor_status": _text(
            rollup.get("broker_observed_supervisor_status")
        ),
        "execution_plan_action": _text(rollup.get("execution_plan_action")),
        "action_decision": _text(rollup.get("action_decision")),
        "paper_mutation_readiness_packet_consumed": (
            rollup.get("paper_mutation_readiness_packet_consumed") is True
        ),
        "paper_mutation_readiness_gate_status": _text(
            rollup.get("paper_mutation_readiness_gate_status")
        ),
        "paper_mutation_readiness_status": _text(
            rollup.get("paper_mutation_readiness_status")
        ),
        "paper_mutation_source_autonomy_status": _text(
            rollup.get("paper_mutation_source_autonomy_status")
        ),
        "vol_scaled_preview_visible": (
            rollup.get("vol_scaled_preview_visible") is True
        ),
        "vol_scaled_preview_intended_action": _text(
            rollup.get("vol_scaled_preview_intended_action")
        ),
        "vol_scaled_preview_mutation_allowed": (
            rollup.get("vol_scaled_preview_mutation_allowed") is True
        ),
        "vol_scaled_preview_submit_allowed": (
            rollup.get("vol_scaled_preview_submit_allowed") is True
        ),
        "vol_scaled_preview_non_mutation_status": _text(
            rollup.get("vol_scaled_preview_non_mutation_status")
        ),
        "paper_submit_performed": rollup.get("paper_submit_performed") is True,
        "broker_mutation_performed": rollup.get("broker_mutation_performed") is True,
        "live_mutation_performed": rollup.get("live_mutation_performed") is True,
        "reconciliation_status": _text(rollup.get("reconciliation_status")),
        "anomaly_classification": classification,
        "next_operator_action": _text(rollup.get("next_operator_action")),
        "final_operator_action": _text(rollup.get("final_operator_action")),
        "operator_exit_code": operator_exit_code,
    }
    return summary


def render_paper_autopilot_operator_summary(summary: Mapping[str, Any]) -> str:
    """Render compact key=value operator status."""

    lines = [f"{field}={_value_text(summary.get(field))}" for field in _SUMMARY_FIELDS]
    lines.append(f"operator_exit_code={_value_text(summary.get('operator_exit_code'))}")
    return "\n".join(lines) + "\n"


def paper_autopilot_operator_exit_status(result: Mapping[str, Any]) -> int:
    return int(result.get("operator_exit_code") or 0)


def result_to_json(result: Mapping[str, Any]) -> str:
    return json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"


def _safe_error_text(exc: Exception) -> str:
    message = " ".join(str(exc).split())
    return message[:240].rstrip()


def _path(value: object, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str):
        path = Path(value)
    else:
        raise ValidationError(f"{field_name} must be a Path or string.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _value_text(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (list, tuple)):
        return ",".join(_text(item) for item in value if _text(item))
    return _text(value)


def _string_list(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [_text(item) for item in value if _text(item)]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


__all__ = [
    "PAPER_AUTOPILOT_OPERATOR_COMMAND",
    "PAPER_AUTOPILOT_OPERATOR_SCHEMA_VERSION",
    "PaperAutopilotOperatorConfig",
    "build_paper_autopilot_operator_summary",
    "paper_autopilot_operator_exit_status",
    "render_paper_autopilot_operator_summary",
    "result_to_json",
    "run_paper_autopilot_operator",
]
