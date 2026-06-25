"""Run the v1.96 read-only paper broker observation packet."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from algotrader.execution.etf_sma_v196_read_only_broker_observation import (  # noqa: E402
    PAPER_OBSERVATION_ELIGIBLE,
    V196_DEFAULT_OUTPUT_ROOT,
    V196_RUN_ID,
    render_v196_broker_observation_brief,
    run_v196_read_only_broker_observation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_v196_read_only_broker_observation.py",
        description=(
            "Build a read-only paper broker observation packet for a ready v1.95 "
            "bounded SPY paper-drill approval packet."
        ),
    )
    parser.add_argument(
        "--approval-packet",
        default=None,
        help="Explicit v1.95 approval_packet.json path. Defaults to latest under --approval-search-root.",
    )
    parser.add_argument(
        "--approval-search-root",
        default="runs/paper_lab",
        help="Search root used when --approval-packet is omitted.",
    )
    parser.add_argument(
        "--output-root",
        default=V196_DEFAULT_OUTPUT_ROOT,
        help="Runtime artifact directory for v1.96 observation artifacts.",
    )
    parser.add_argument(
        "--run-id",
        default=V196_RUN_ID,
        help="Run id to include in the observation packet.",
    )
    parser.add_argument(
        "--timestamp",
        default=None,
        help="Optional timezone-aware timestamp override for deterministic tests.",
    )
    parser.add_argument(
        "--expected-paper-account-id",
        default=None,
        help="Optional expected paper account id. The raw value is not written to artifacts.",
    )
    args = parser.parse_args(argv)

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=args.approval_packet,
        approval_search_root=args.approval_search_root,
        output_root=args.output_root,
        run_id=args.run_id,
        timestamp=args.timestamp,
        expected_paper_account_id=args.expected_paper_account_id,
    )
    print(render_v196_broker_observation_brief(packet))
    if packet.get("eligibility_classification") == PAPER_OBSERVATION_ELIGIBLE:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
