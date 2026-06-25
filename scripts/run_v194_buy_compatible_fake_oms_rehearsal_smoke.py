"""Run the v1.94 buy-compatible fake OMS rehearsal smoke."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from algotrader.execution.etf_sma_daily_order_intent_adapter import (
    OfflineOrderIntentApprovalFixture,
    sample_v192_daily_execution_plan_packet,
)
from algotrader.execution.etf_sma_daily_order_intent_review_packet import (
    run_v193_order_intent_review_packet_from_path,
)

V194_RUN_ID = "v194_buy_compatible_fake_oms_rehearsal_smoke"
V194_DEFAULT_OUTPUT_ROOT = "runs/paper_lab/v194_buy_compatible_fake_oms_rehearsal_smoke"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_v194_buy_compatible_fake_oms_rehearsal_smoke.py"
    )
    parser.add_argument(
        "--input-packet",
        default="",
        help=(
            "Local JSON daily packet or serialized ExecutionPlan. If omitted, "
            "the script writes and consumes a deterministic buy-preview sample."
        ),
    )
    parser.add_argument(
        "--output-root",
        default=V194_DEFAULT_OUTPUT_ROOT,
        help="Runtime artifact root for the v1.94 buy-compatible smoke.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        dest="output_format",
        help="Safe summary output format.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_root = Path(args.output_root)
    input_path = Path(args.input_packet) if args.input_packet else _write_sample(output_root)
    packet = run_v193_order_intent_review_packet_from_path(
        input_path,
        approval_fixture=OfflineOrderIntentApprovalFixture(approval_granted=True),
        output_root=output_root,
        run_id=V194_RUN_ID,
    )
    summary = _safe_summary(packet)
    if args.output_format == "json":
        print(json.dumps(summary, sort_keys=True, indent=2))
    else:
        for key, value in summary.items():
            print(f"{key}={value}")
    return 0


def _write_sample(output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    packet = sample_v192_daily_execution_plan_packet()
    packet["preview_decision"] = "buy_preview"
    plan = packet["execution_plan"]
    plan["execution_plan_id"] = "daily_execution_plan_v194_smoke_buy_preview"
    plan["execution_plan_action"] = "buy_preview"
    plan["execution_plan_source_preview_decision"] = "buy_preview"
    plan["execution_plan_reason"] = "buy_preview_requires_explicit_authorization"
    input_path = output_root / "sample_daily_execution_plan_packet.json"
    input_path.write_text(
        json.dumps(packet, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return input_path


def _safe_summary(packet: dict[str, object]) -> dict[str, object]:
    artifact_paths = packet.get("artifact_paths")
    operator_review_packet = (
        str(artifact_paths.get("operator_review_packet", ""))
        if isinstance(artifact_paths, dict)
        else ""
    )
    return {
        "run_id": packet.get("run_id", ""),
        "as_of_date": packet.get("as_of_date", ""),
        "symbol": packet.get("symbol", ""),
        "preview_decision": packet.get("preview_decision", ""),
        "order_side": packet.get("order_side", ""),
        "notional_or_quantity": packet.get("notional_or_quantity", ""),
        "notional_or_quantity_kind": packet.get("notional_or_quantity_kind", ""),
        "quantity_or_notional_source": packet.get("quantity_or_notional_source", ""),
        "order_type": packet.get("order_type", ""),
        "time_in_force": packet.get("time_in_force", ""),
        "client_order_id": packet.get("client_order_id", ""),
        "projected_broker_request_fields": packet.get(
            "projected_broker_request_fields",
            {},
        ),
        "projected_broker_request_status": packet.get(
            "projected_broker_request_status",
            "",
        ),
        "broker_request_sent": packet.get("broker_request_sent", False),
        "fake_oms_classification": packet.get("fake_oms_classification", ""),
        "fake_submit_call_count": packet.get("fake_submit_call_count", 0),
        "fake_cancel_call_count": packet.get("fake_cancel_call_count", 0),
        "final_review_classification": packet.get("final_review_classification", ""),
        "paper_submit_authorized": packet.get("paper_submit_authorized", False),
        "paper_submit_performed": packet.get("paper_submit_performed", False),
        "real_broker_read_performed": packet.get("real_broker_read_performed", False),
        "real_broker_mutation_performed": packet.get(
            "real_broker_mutation_performed",
            False,
        ),
        "live_trading_authorized": packet.get("live_trading_authorized", False),
        "live_trading_performed": packet.get("live_trading_performed", False),
        "next_operator_action": packet.get("next_operator_action", ""),
        "safety_labels": packet.get("safety_labels", []),
        "artifact_root": (
            str(Path(operator_review_packet).parent) if operator_review_packet else ""
        ),
    }


if __name__ == "__main__":
    sys.exit(main())
