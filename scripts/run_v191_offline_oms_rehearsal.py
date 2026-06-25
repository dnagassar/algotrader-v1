"""Run the v1.91 offline daily ExecutionPlan to Paper OMS rehearsal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from algotrader.execution.etf_sma_daily_oms_rehearsal import (
    V191_DEFAULT_OUTPUT_ROOT,
    run_v191_offline_oms_rehearsal_from_path,
    sample_daily_execution_plan_packet,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run_v191_offline_oms_rehearsal.py")
    parser.add_argument(
        "--input-packet",
        default="",
        help=(
            "Local JSON daily packet or serialized ExecutionPlan. If omitted, "
            "the script writes and consumes a deterministic sample packet."
        ),
    )
    parser.add_argument(
        "--output-root",
        default=V191_DEFAULT_OUTPUT_ROOT,
        help="Runtime artifact root for the v1.91 offline OMS rehearsal.",
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
    packet = run_v191_offline_oms_rehearsal_from_path(
        input_path,
        output_root=output_root,
    )
    summary = _safe_summary(packet)
    if args.output_format == "json":
        print(json.dumps(summary, sort_keys=True, indent=2))
    else:
        print(f"outcome_classification={summary['outcome_classification']}")
        print(f"execution_plan_digest={summary['execution_plan_digest']}")
        print(f"client_order_id={summary['client_order_id']}")
        print(f"execution_mode={summary['execution_mode']}")
        print(f"broker_state_mode={summary['broker_state_mode']}")
        print(f"fake_submit_call_count={summary['fake_submit_call_count']}")
        print(f"fake_cancel_call_count={summary['fake_cancel_call_count']}")
        print(f"paper_submit_authorized={summary['paper_submit_authorized']}")
        print(f"paper_submit_performed={summary['paper_submit_performed']}")
        print(f"real_broker_read_performed={summary['real_broker_read_performed']}")
        print(f"real_broker_mutation_performed={summary['real_broker_mutation_performed']}")
        print(f"next_operator_action={summary['next_operator_action']}")
        print(f"artifact_root={summary['artifact_root']}")
    return 0


def _write_sample(output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    input_path = output_root / "sample_daily_execution_plan_packet.json"
    input_path.write_text(
        json.dumps(sample_daily_execution_plan_packet(), sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return input_path


def _safe_summary(packet: dict[str, object]) -> dict[str, object]:
    artifact_paths = packet.get("artifact_paths")
    operating_packet = (
        str(artifact_paths.get("operating_packet", ""))
        if isinstance(artifact_paths, dict)
        else ""
    )
    return {
        "outcome_classification": packet.get("outcome_classification", ""),
        "execution_plan_digest": packet.get("execution_plan_digest", ""),
        "client_order_id": packet.get("client_order_id", ""),
        "execution_mode": packet.get("execution_mode", ""),
        "broker_state_mode": packet.get("broker_state_mode", ""),
        "fake_submit_call_count": packet.get("fake_submit_call_count", 0),
        "fake_cancel_call_count": packet.get("fake_cancel_call_count", 0),
        "paper_submit_authorized": packet.get("paper_submit_authorized", False),
        "paper_submit_performed": packet.get("paper_submit_performed", False),
        "real_broker_read_performed": packet.get("real_broker_read_performed", False),
        "real_broker_mutation_performed": packet.get(
            "real_broker_mutation_performed",
            False,
        ),
        "next_operator_action": packet.get("next_operator_action", ""),
        "artifact_root": str(Path(operating_packet).parent) if operating_packet else "",
    }


if __name__ == "__main__":
    sys.exit(main())
