"""Run the v2.00 post-drill operating guard from a local v1.99 packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from algotrader.execution.etf_sma_v200_post_drill_operating_guard import (
    POST_DRILL_GUARD_READY,
    V200_DEFAULT_OUTPUT_ROOT,
    V200_DEFAULT_SOURCE_PACKET_PATH,
    run_v200_post_drill_operating_guard,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run_v200_post_drill_operating_guard.py")
    parser.add_argument(
        "--source-paper-drill-packet",
        default=V200_DEFAULT_SOURCE_PACKET_PATH,
        help="Local v1.99 paper_drill_packet.json path or containing directory.",
    )
    parser.add_argument(
        "--output-root",
        default=V200_DEFAULT_OUTPUT_ROOT,
        help="Runtime artifact root for the v2.00 post-drill guard.",
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
    packet = run_v200_post_drill_operating_guard(
        source_paper_drill_packet_path=Path(args.source_paper_drill_packet),
        output_root=Path(args.output_root),
    )
    summary = _safe_summary(packet)
    if args.output_format == "json":
        print(json.dumps(summary, sort_keys=True, indent=2))
    else:
        for key, value in summary.items():
            print(f"{key}={value}")
    return 0 if summary["post_drill_guard_classification"] == POST_DRILL_GUARD_READY else 2


def _safe_summary(packet: dict[str, object]) -> dict[str, object]:
    latest = packet.get("latest_bounded_paper_drill")
    latest_drill = latest if isinstance(latest, dict) else {}
    artifact_paths = packet.get("artifact_paths")
    artifact_root = ""
    if isinstance(artifact_paths, dict):
        packet_path = str(artifact_paths.get("post_drill_guard_packet", ""))
        artifact_root = str(Path(packet_path).parent) if packet_path else ""
    return {
        "post_drill_guard_classification": packet.get(
            "post_drill_guard_classification",
            "",
        ),
        "blocker": packet.get("blocker", ""),
        "source_paper_drill_outcome": packet.get("source_paper_drill_outcome", ""),
        "source_v199_paper_drill_packet_path": packet.get(
            "source_v199_paper_drill_packet_path",
            "",
        ),
        "symbol": latest_drill.get("symbol", ""),
        "side": latest_drill.get("side", ""),
        "order_type": latest_drill.get("order_type", ""),
        "time_in_force": latest_drill.get("time_in_force", ""),
        "notional": latest_drill.get("notional", ""),
        "quantity": latest_drill.get("quantity", ""),
        "cap": latest_drill.get("cap", ""),
        "client_order_id": latest_drill.get("client_order_id", ""),
        "submit_attempted_from_source_packet": packet.get(
            "submit_attempted_from_source_packet",
            False,
        ),
        "submit_status_from_source_packet": packet.get(
            "submit_status_from_source_packet",
            "",
        ),
        "cancel_attempted_from_source_packet": packet.get(
            "cancel_attempted_from_source_packet",
            False,
        ),
        "cancel_confirmed_from_source_packet": packet.get(
            "cancel_confirmed_from_source_packet",
            False,
        ),
        "fill_status_from_source_packet": packet.get(
            "fill_status_from_source_packet",
            "",
        ),
        "final_broker_order_status_from_source_packet": packet.get(
            "final_broker_order_status_from_source_packet",
            "",
        ),
        "last_authorization_consumed": packet.get(
            "last_authorization_consumed",
            False,
        ),
        "paper_submit_authorized": packet.get("paper_submit_authorized", False),
        "paper_cancel_authorized": packet.get("paper_cancel_authorized", False),
        "next_paper_action_requires_new_authorization": packet.get(
            "next_paper_action_requires_new_authorization",
            True,
        ),
        "next_operator_action": packet.get("next_operator_action", ""),
        "broker_read_performed": packet.get("broker_read_performed", False),
        "broker_mutation_performed": packet.get("broker_mutation_performed", False),
        "paper_submit_performed": packet.get("paper_submit_performed", False),
        "paper_cancel_performed": packet.get("paper_cancel_performed", False),
        "live_read_performed": packet.get("live_read_performed", False),
        "live_mutation_performed": packet.get("live_mutation_performed", False),
        "live_trading_performed": packet.get("live_trading_performed", False),
        "artifact_root": artifact_root,
    }


if __name__ == "__main__":
    sys.exit(main())
