"""Compact read-only status receipt for daily paper-lab artifacts."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any


CANONICAL_ARTIFACT_FILENAME = "latest_run.json"


class DailyPaperLabStatusReceiptError(ValueError):
    """Raised when the daily paper-lab artifact contract cannot be read."""


@dataclass(frozen=True)
class ReceiptField:
    key: str
    paths: tuple[tuple[str, ...], ...]
    required: bool = True


_OPTIONAL_CONTEXT_FIELDS: tuple[ReceiptField, ...] = (
    ReceiptField("run_date", (("run_date",),), required=False),
    ReceiptField(
        "input_data_path",
        (
            ("daily_decision_summary", "input_data_path"),
            ("current_accepted_data_path",),
        ),
        required=False,
    ),
    ReceiptField(
        "data_as_of_date",
        (
            ("daily_decision_summary", "as_of_date"),
            ("current_data_as_of",),
            ("accepted_data_as_of",),
        ),
        required=False,
    ),
    ReceiptField("safety_labels", (("safety_labels",),), required=False),
)


_REQUIRED_RECEIPT_FIELDS: tuple[ReceiptField, ...] = (
    ReceiptField("validation_status", (("validation_status",),)),
    ReceiptField(
        "data_freshness_status",
        (
            ("data_freshness_status",),
            ("daily_decision_summary", "data_freshness_status"),
        ),
    ),
    ReceiptField("latest_bar_date", (("daily_decision_summary", "latest_bar_date"),)),
    ReceiptField("sma_posture", (("daily_decision_summary", "sma_posture"),)),
    ReceiptField(
        "market_signal_preview",
        (
            ("market_signal_preview",),
            ("daily_decision_summary", "market_signal_preview"),
        ),
    ),
    ReceiptField(
        "broker_state_mode",
        (
            ("broker_state_mode",),
            ("daily_decision_summary", "broker_state_mode"),
        ),
    ),
    ReceiptField(
        "broker_snapshot_freshness_status",
        (("daily_decision_summary", "broker_snapshot_freshness_status"),),
    ),
    ReceiptField(
        "broker_state_observed",
        (
            ("broker_state_observed",),
            ("daily_decision_summary", "broker_state_observed"),
        ),
    ),
    ReceiptField(
        "broker_state_status",
        (
            ("broker_state_status",),
            ("daily_decision_summary", "broker_state_status"),
        ),
    ),
    ReceiptField(
        "broker_aware_preview_decision",
        (("daily_decision_summary", "broker_aware_preview_decision"),),
    ),
    ReceiptField(
        "execution_plan_status",
        (
            ("execution_plan", "execution_plan_status"),
            ("execution_plan_status",),
        ),
    ),
    ReceiptField(
        "execution_plan_action",
        (
            ("execution_plan", "execution_plan_action"),
            ("execution_plan_action",),
        ),
    ),
    ReceiptField(
        "execution_plan_blocker",
        (
            ("execution_plan", "execution_plan_blocker"),
            ("execution_plan_blocker",),
        ),
    ),
    ReceiptField(
        "execution_plan_reason",
        (
            ("execution_plan", "execution_plan_reason"),
            ("execution_plan_reason",),
        ),
    ),
    ReceiptField(
        "approval_state",
        (
            ("daily_approval_gate", "approval_state"),
            ("daily_approval_gate_approval_state",),
        ),
    ),
    ReceiptField(
        "submit_allowed",
        (
            ("daily_approval_gate", "submit_allowed"),
            ("submit_allowed",),
        ),
    ),
    ReceiptField(
        "autopilot_control_status",
        (
            ("daily_autopilot_controller", "autopilot_control_status"),
            ("autopilot_control_status",),
        ),
    ),
    ReceiptField(
        "can_continue_without_daniel",
        (
            ("daily_autopilot_controller", "can_continue_without_daniel"),
            ("can_continue_without_daniel",),
        ),
    ),
    ReceiptField(
        "next_safe_action",
        (
            ("daily_autopilot_controller", "next_safe_action"),
            ("next_safe_action",),
        ),
    ),
    ReceiptField(
        "selected_agent",
        (
            ("daily_autopilot_controller", "selected_agent"),
            ("selected_agent",),
        ),
    ),
    ReceiptField(
        "hard_gate_required",
        (
            ("daily_autopilot_controller", "hard_gate_required"),
            ("hard_gate_required",),
        ),
    ),
    ReceiptField(
        "hard_gate_type",
        (
            ("daily_autopilot_controller", "hard_gate_type"),
            ("hard_gate_type",),
        ),
    ),
    ReceiptField(
        "hard_gate_reason",
        (
            ("daily_autopilot_controller", "hard_gate_reason"),
            ("hard_gate_reason",),
        ),
    ),
    ReceiptField(
        "paper_submit_authorized",
        (
            ("daily_approval_gate", "paper_submit_authorized"),
            ("paper_submit_authorized",),
        ),
    ),
    ReceiptField(
        "live_authorized",
        (
            ("daily_approval_gate", "live_authorized"),
            ("live_authorized",),
        ),
    ),
    ReceiptField(
        "broker_mutation_performed",
        (
            ("daily_approval_gate", "broker_mutation_performed"),
            ("broker_mutation_performed",),
        ),
    ),
)


_RECEIPT_FIELDS = (*_OPTIONAL_CONTEXT_FIELDS, *_REQUIRED_RECEIPT_FIELDS)


def build_daily_paper_lab_status_receipt(output_root: str | Path) -> dict[str, str]:
    """Read the canonical latest run artifact and return stable receipt lines."""

    output_path = Path(output_root)
    if not output_path.exists():
        raise DailyPaperLabStatusReceiptError(
            f"missing output root: {output_path}"
        )
    if not output_path.is_dir():
        raise DailyPaperLabStatusReceiptError(
            f"output root is not a directory: {output_path}"
        )

    artifact_path = output_path / CANONICAL_ARTIFACT_FILENAME
    payload = _read_json_object(artifact_path)

    receipt = {
        "artifact_source_path": _format_path(artifact_path),
    }
    for field in _RECEIPT_FIELDS:
        found, value = _first_available(payload, field.paths)
        if not found:
            if field.required:
                paths = ", ".join(".".join(path) for path in field.paths)
                raise DailyPaperLabStatusReceiptError(
                    "missing required contract field: "
                    f"{field.key} ({paths}) in {artifact_path}"
                )
            continue
        receipt[field.key] = _format_value(value)

    return receipt


def render_daily_paper_lab_status_receipt(output_root: str | Path) -> str:
    receipt = build_daily_paper_lab_status_receipt(output_root)
    return "\n".join(f"{key}={value}" for key, value in receipt.items())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="daily-paper-lab-status-receipt",
        description="Print a compact read-only status receipt from latest_run.json.",
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Daily paper-lab output root containing latest_run.json.",
    )
    args = parser.parse_args(argv)

    try:
        print(render_daily_paper_lab_status_receipt(args.output_root))
    except DailyPaperLabStatusReceiptError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


def _read_json_object(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        raise DailyPaperLabStatusReceiptError(
            f"missing canonical artifact: {path}"
        )
    if not path.is_file():
        raise DailyPaperLabStatusReceiptError(
            f"canonical artifact is not a file: {path}"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DailyPaperLabStatusReceiptError(
            f"malformed JSON artifact: {path}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise DailyPaperLabStatusReceiptError(
            f"unreadable canonical artifact: {path}: {exc.strerror or exc}"
        ) from exc

    if not isinstance(payload, Mapping):
        raise DailyPaperLabStatusReceiptError(
            f"malformed JSON artifact: {path}: top-level value is not an object"
        )
    return payload


def _first_available(
    payload: Mapping[str, Any],
    paths: Iterable[tuple[str, ...]],
) -> tuple[bool, Any]:
    for path in paths:
        current: Any = payload
        found = True
        for key in path:
            if not isinstance(current, Mapping) or key not in current:
                found = False
                break
            current = current[key]
        if found:
            return True, current
    return False, None


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return "none"
    if isinstance(value, str):
        return value
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return ",".join(_format_value(item) for item in value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _format_path(path: Path) -> str:
    return path.as_posix()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
