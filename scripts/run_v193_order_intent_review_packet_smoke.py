"""Run the v1.93 offline order-intent review packet smoke."""

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
    V193_DEFAULT_OUTPUT_ROOT,
    run_v193_order_intent_review_packet_from_path,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_v193_order_intent_review_packet_smoke.py"
    )
    parser.add_argument(
        "--input-packet",
        default="",
        help=(
            "Local JSON daily packet or serialized ExecutionPlan. If omitted, "
            "the script writes and consumes a deterministic sell-preview sample."
        ),
    )
    parser.add_argument(
        "--output-root",
        default=V193_DEFAULT_OUTPUT_ROOT,
        help="Runtime artifact root for the v1.93 review-packet smoke.",
    )
    parser.add_argument(
        "--approval",
        choices=("none", "offline-fixture"),
        default="offline-fixture",
        help="Use no approval or an offline fixture-only approval.",
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
    approval_fixture = (
        OfflineOrderIntentApprovalFixture(approval_granted=True)
        if args.approval == "offline-fixture"
        else None
    )
    packet = run_v193_order_intent_review_packet_from_path(
        input_path,
        approval_fixture=approval_fixture,
        output_root=output_root,
        run_id="v193_order_intent_review_packet_smoke",
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
    packet["preview_decision"] = "sell_preview"
    plan = packet["execution_plan"]
    plan["execution_plan_id"] = "daily_execution_plan_v193_smoke_sell_preview"
    plan["execution_plan_action"] = "sell_preview"
    plan["execution_plan_source_preview_decision"] = "sell_preview"
    plan["execution_plan_reason"] = "sell_preview_requires_explicit_authorization"
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
        "final_review_classification": packet.get("final_review_classification", ""),
        "source_execution_plan_digest": packet.get("source_execution_plan_digest", ""),
        "client_order_id": packet.get("client_order_id", ""),
        "approval_mode": packet.get("approval_mode", ""),
        "approval_source": packet.get("approval_source", ""),
        "approval_granted": packet.get("approval_granted", False),
        "real_operator_authorization": packet.get(
            "real_operator_authorization",
            False,
        ),
        "order_side": packet.get("order_side", ""),
        "projected_broker_request_status": packet.get(
            "projected_broker_request_status",
            "",
        ),
        "broker_request_sent": packet.get("broker_request_sent", False),
        "fake_oms_classification": packet.get("fake_oms_classification", ""),
        "fake_submit_call_count": packet.get("fake_submit_call_count", 0),
        "fake_cancel_call_count": packet.get("fake_cancel_call_count", 0),
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
        "artifact_root": (
            str(Path(operator_review_packet).parent) if operator_review_packet else ""
        ),
    }


if __name__ == "__main__":
    sys.exit(main())
