"""Run the offline SPY intraday SMA8/32 evidence gate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_PATH = _REPO_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from algotrader.errors import ValidationError  # noqa: E402
from algotrader.research.intraday_evidence import (  # noqa: E402
    IntradayEvidenceConfig,
    build_intraday_evidence_from_csv,
    write_intraday_evidence_artifacts,
)


DEFAULT_INPUT = "runs/intraday_probe/v1_82/normalized_spy_intraday_15m_calendar_valid.csv"
DEFAULT_OUTPUT_ROOT = "runs/intraday_evidence/v1_84"
DEFAULT_RUN_ID = "v1_84_spy_intraday_sma_8_32_evidence_gate"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run-spy-intraday-evidence",
        description="Generate local-only SPY 15m SMA(8/32) signal evidence.",
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help="Local calendar-valid SPY 15-minute CSV path.",
    )
    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
        help="Ignored intraday evidence artifact directory.",
    )
    parser.add_argument(
        "--run-id",
        default=DEFAULT_RUN_ID,
        help="Deterministic run identifier.",
    )
    parser.add_argument(
        "--data-source-kind",
        default="local_intraday_csv",
        help="Data source classification recorded in the evidence artifact.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        evidence = build_intraday_evidence_from_csv(
            IntradayEvidenceConfig(
                run_id=args.run_id,
                intraday_bars_csv=Path(args.input),
                data_source_kind=args.data_source_kind,
            )
        )
        paths = write_intraday_evidence_artifacts(evidence, Path(args.output_root))
    except ValidationError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2

    print(f"evaluation_status: {evidence['evaluation_status']}")
    print(f"execution_semantics_status: {evidence['execution_semantics_status']}")
    print(
        "non_authoritative_recommendation: "
        f"{evidence['non_authoritative_recommendation']}"
    )
    for name, path in paths.items():
        print(f"{name}: {path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
