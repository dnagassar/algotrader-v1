"""Run the offline SPY intraday trend research probe."""

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
from algotrader.research.intraday_trend_probe import (  # noqa: E402
    IntradayTrendProbeConfig,
    build_intraday_trend_probe_from_csv,
    write_intraday_probe_artifacts,
    write_sample_spy_intraday_fixture,
)


DEFAULT_OUTPUT_DIR = "runs/intraday_probe/v1_80"
DEFAULT_INPUT = f"{DEFAULT_OUTPUT_DIR}/spy_intraday_fixture_15m.csv"
DEFAULT_RUN_ID = "v1_80_spy_intraday_fixture_probe"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run-spy-intraday-probe",
        description="Run a local-only SPY intraday SMA trend probe.",
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help="Local SPY intraday CSV path. Default writes/uses the phase fixture path.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Ignored run artifact directory.",
    )
    parser.add_argument(
        "--run-id",
        default=DEFAULT_RUN_ID,
        help="Deterministic run identifier.",
    )
    parser.add_argument(
        "--source-timeframe-minutes",
        type=int,
        default=15,
        help="Input bar timeframe in minutes.",
    )
    parser.add_argument(
        "--slippage-bps",
        default="2",
        help="Fixed slippage bps per exposure change.",
    )
    parser.add_argument(
        "--data-source-kind",
        choices=("local_intraday_csv", "deterministic_fixture"),
        default="deterministic_fixture",
        help="Input classification for the generated artifact.",
    )
    parser.add_argument(
        "--write-sample-fixture",
        action="store_true",
        help="Write the deterministic SPY 15-minute fixture before running.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input)
    if args.write_sample_fixture:
        write_sample_spy_intraday_fixture(input_path)

    try:
        build = build_intraday_trend_probe_from_csv(
            IntradayTrendProbeConfig(
                run_id=args.run_id,
                intraday_bars_csv=input_path,
                source_timeframe_minutes=args.source_timeframe_minutes,
                slippage_bps=args.slippage_bps,
                data_source_kind=args.data_source_kind,
            )
        )
        paths = write_intraday_probe_artifacts(build, args.output_dir)
    except ValidationError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2

    payload = build.payload
    print(f"classification: {payload['classification_recommendation']}")
    print(f"decision_quality: {payload['decision_quality']}")
    for name, path in paths.items():
        print(f"{name}: {path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
