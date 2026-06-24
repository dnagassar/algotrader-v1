"""Run the offline SPY intraday preview-only lane."""

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
from algotrader.research.intraday_preview import (  # noqa: E402
    IntradayPreviewConfig,
    build_intraday_preview_from_csv,
    write_intraday_preview_artifacts,
)


DEFAULT_INPUT = "runs/intraday_probe/v1_82/normalized_spy_intraday_15m_calendar_valid.csv"
DEFAULT_OUTPUT_DIR = "runs/intraday_preview/v1_83"
DEFAULT_RUN_ID = "v1_83_spy_intraday_sma_8_32_preview_only"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run-spy-intraday-preview",
        description="Generate a local-only SPY 15m SMA(8/32) preview artifact.",
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help="Local calendar-valid SPY 15-minute CSV path.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Ignored intraday preview run artifact directory.",
    )
    parser.add_argument(
        "--run-id",
        default=DEFAULT_RUN_ID,
        help="Deterministic run identifier.",
    )
    parser.add_argument(
        "--data-source-kind",
        default="local_intraday_csv",
        help="Data source classification recorded in the preview artifact.",
    )
    parser.add_argument(
        "--expected-session-date",
        default=None,
        help="Optional ISO date that the latest accepted session must match.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        preview = build_intraday_preview_from_csv(
            IntradayPreviewConfig(
                run_id=args.run_id,
                intraday_bars_csv=Path(args.input),
                data_source_kind=args.data_source_kind,
                expected_accepted_session_date=args.expected_session_date,
            )
        )
        paths = write_intraday_preview_artifacts(preview, Path(args.output_dir))
    except ValidationError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2

    print(f"classification: {preview['classification_recommendation']}")
    print(f"preview_decision: {preview['preview_decision']}")
    print(f"blocker_status: {preview['blocker_status']}")
    for name, path in paths.items():
        print(f"{name}: {path.as_posix()}")
    return 2 if str(preview["preview_decision"]).startswith("blocked/") else 0


if __name__ == "__main__":
    raise SystemExit(main())
