"""Run the v1.95 bounded paper-drill approval packet smoke."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from algotrader.execution.etf_sma_daily_order_intent_adapter import (
    OfflineOrderIntentApprovalFixture,
)
from algotrader.execution.etf_sma_v195_bounded_paper_drill_approval_packet import (
    V195_DEFAULT_OUTPUT_ROOT,
    run_v195_bounded_paper_drill_approval_packet_from_path,
    sample_v195_daily_execution_plan_packet,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_v195_bounded_paper_drill_approval_packet_smoke.py"
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
        default=V195_DEFAULT_OUTPUT_ROOT,
        help="Runtime artifact root for the v1.95 approval-packet smoke.",
    )
    parser.add_argument(
        "--side",
        choices=("buy", "sell"),
        default="buy",
        help="Sample side used only when --input-packet is omitted.",
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
    input_path = (
        Path(args.input_packet)
        if args.input_packet
        else _write_sample(output_root, args.side)
    )
    packet = run_v195_bounded_paper_drill_approval_packet_from_path(
        input_path,
        approval_fixture=OfflineOrderIntentApprovalFixture(approval_granted=True),
        output_root=output_root,
        run_id="v195_bounded_paper_drill_approval_packet_smoke",
    )
    summary = _safe_summary(packet)
    if args.output_format == "json":
        print(json.dumps(summary, sort_keys=True, indent=2))
    else:
        for key, value in summary.items():
            print(f"{key}={value}")
    return 0


def _write_sample(output_root: Path, side: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    packet = sample_v195_daily_execution_plan_packet(f"{side}_preview")
    input_path = output_root / "sample_daily_execution_plan_packet.json"
    input_path.write_text(
        json.dumps(packet, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return input_path


def _safe_summary(packet: dict[str, object]) -> dict[str, object]:
    artifact_paths = packet.get("artifact_paths")
    approval_packet = (
        str(artifact_paths.get("approval_packet", ""))
        if isinstance(artifact_paths, dict)
        else ""
    )
    return {
        "approval_packet_classification": packet.get(
            "approval_packet_classification",
            "",
        ),
        "operator_review_classification": packet.get(
            "operator_review_classification",
            "",
        ),
        "approval_packet_is_authorization": packet.get(
            "approval_packet_is_authorization",
            True,
        ),
        "source_execution_plan_digest": packet.get(
            "source_execution_plan_digest",
            "",
        ),
        "client_order_id": packet.get("client_order_id", ""),
        "order_side": packet.get("order_side", ""),
        "projected_broker_request_status": packet.get(
            "projected_broker_request_status",
            "",
        ),
        "projected_fields_are_projected_only": packet.get(
            "projected_fields_are_projected_only",
            False,
        ),
        "broker_request_sent": packet.get("broker_request_sent", False),
        "paper_submit_authorized": packet.get("paper_submit_authorized", False),
        "paper_submit_performed": packet.get("paper_submit_performed", False),
        "real_broker_read_performed": packet.get("real_broker_read_performed", False),
        "real_broker_mutation_performed": packet.get(
            "real_broker_mutation_performed",
            False,
        ),
        "future_broker_read_required": packet.get(
            "future_broker_read_required",
            False,
        ),
        "future_paper_submit_requires_explicit_authorization": packet.get(
            "future_paper_submit_requires_explicit_authorization",
            False,
        ),
        "required_future_authorization_phrase": packet.get(
            "required_future_authorization_phrase",
            "",
        ),
        "next_operator_action": packet.get("next_operator_action", ""),
        "artifact_root": str(Path(approval_packet).parent) if approval_packet else "",
    }


if __name__ == "__main__":
    sys.exit(main())
