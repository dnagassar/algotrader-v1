"""Run the v1.99 authorized bounded SPY paper drill."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from algotrader.execution.etf_sma_v199_authorized_bounded_spy_paper_drill import (
    V199_AUTHORIZATION_PHRASE,
    V199_DEFAULT_APPROVAL_PACKET_PATH,
    V199_DEFAULT_OUTPUT_ROOT,
    run_v199_authorized_bounded_spy_paper_drill,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_v199_authorized_bounded_spy_paper_drill.py"
    )
    parser.add_argument(
        "--approval-packet",
        default=V199_DEFAULT_APPROVAL_PACKET_PATH,
        help="Ready v1.95 approval packet path.",
    )
    parser.add_argument(
        "--output-root",
        default=V199_DEFAULT_OUTPUT_ROOT,
        help="Runtime artifact root for the v1.99 drill.",
    )
    parser.add_argument(
        "--authorization-phrase",
        required=True,
        help="Exact one-time operator authorization phrase.",
    )
    parser.add_argument(
        "--expected-paper-account-id",
        default=None,
        help=(
            "Optional expected paper account value. If omitted, "
            "ALPACA_EXPECTED_PAPER_ACCOUNT_ID is used."
        ),
    )
    parser.add_argument(
        "--reconciliation-poll-attempts",
        type=int,
        default=3,
        help="Bounded same-order lookup attempts after cancellation.",
    )
    parser.add_argument(
        "--reconciliation-poll-interval-seconds",
        type=float,
        default=1.0,
        help="Seconds between bounded same-order lookup attempts.",
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
    packet = run_v199_authorized_bounded_spy_paper_drill(
        approval_packet_path=Path(args.approval_packet),
        output_root=Path(args.output_root),
        authorization_phrase=args.authorization_phrase,
        expected_paper_account_id=args.expected_paper_account_id,
        reconciliation_poll_attempts=args.reconciliation_poll_attempts,
        reconciliation_poll_interval_seconds=(
            args.reconciliation_poll_interval_seconds
        ),
    )
    summary = _safe_summary(packet)
    if args.output_format == "json":
        print(json.dumps(summary, sort_keys=True, indent=2))
    else:
        for key, value in summary.items():
            print(f"{key}={value}")
    return 0


def _safe_summary(packet: dict[str, object]) -> dict[str, object]:
    artifact_paths = packet.get("artifact_paths")
    artifact_root = ""
    if isinstance(artifact_paths, dict):
        packet_path = str(artifact_paths.get("paper_drill_packet", ""))
        artifact_root = str(Path(packet_path).parent) if packet_path else ""
    return {
        "authorization_phrase_observed": packet.get(
            "explicit_authorization_phrase_observed",
            False,
        ),
        "outcome_classification": packet.get("outcome_classification", ""),
        "blocker": packet.get("blocker", ""),
        "source_approval_classification": packet.get(
            "source_approval_classification",
            "",
        ),
        "pre_submit_observation_classification": packet.get(
            "pre_submit_observation_classification",
            "",
        ),
        "symbol": packet.get("symbol", ""),
        "side": packet.get("side", ""),
        "order_type": packet.get("order_type", ""),
        "time_in_force": packet.get("time_in_force", ""),
        "notional": packet.get("notional", ""),
        "quantity": packet.get("quantity", ""),
        "cap": packet.get("cap", ""),
        "client_order_id": packet.get("client_order_id", ""),
        "expected_account_configured": packet.get(
            "expected_account_configured",
            False,
        ),
        "expected_account_matched": packet.get("expected_account_matched", False),
        "expected_account_match_mode": packet.get("expected_account_match_mode", ""),
        "account_status": packet.get("account_status", ""),
        "account_tradable": packet.get("account_tradable", False),
        "open_spy_order_observed": packet.get("open_spy_order_observed", False),
        "unexpected_non_spy_position_observed": packet.get(
            "unexpected_non_spy_position_observed",
            False,
        ),
        "duplicate_client_order_id_observed": packet.get(
            "duplicate_client_order_id_observed",
            False,
        ),
        "submit_attempted": packet.get("submit_attempted", False),
        "submit_status": packet.get("submit_status", ""),
        "cancel_attempted": packet.get("cancel_attempted", False),
        "cancel_confirmed": packet.get("cancel_confirmed", False),
        "fill_status": packet.get("fill_status", ""),
        "final_broker_order_status": packet.get("final_broker_order_status", ""),
        "broker_read_performed": packet.get("broker_read_performed", False),
        "broker_mutation_performed": packet.get("broker_mutation_performed", False),
        "paper_submit_performed": packet.get("paper_submit_performed", False),
        "paper_cancel_performed": packet.get("paper_cancel_performed", False),
        "live_read_performed": packet.get("live_read_performed", False),
        "live_mutation_performed": packet.get("live_mutation_performed", False),
        "live_trading_performed": packet.get("live_trading_performed", False),
        "artifact_root": artifact_root,
        "expected_authorization_phrase": V199_AUTHORIZATION_PHRASE,
    }


if __name__ == "__main__":
    sys.exit(main())
