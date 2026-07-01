"""Classify an existing strategy-router SMA/RSI shadow replay packet."""

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
from algotrader.research.strategy_router_shadow_conflict_classifier import (  # noqa: E402
    DEFAULT_REPLAY_JSONL,
    build_strategy_router_shadow_conflict_classification,
    write_strategy_router_shadow_conflict_artifacts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run-strategy-router-shadow-conflict-classifier",
        description=(
            "Classify an existing local SMA/RSI strategy-router shadow replay JSONL "
            "packet into deterministic conflict and shadow-block buckets."
        ),
    )
    parser.add_argument(
        "--replay-jsonl",
        default=str(DEFAULT_REPLAY_JSONL),
        help="Existing local replay.jsonl packet.",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Ignored runtime artifact directory. Defaults to replay-jsonl parent.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    replay_path = Path(args.replay_jsonl)
    output_root = Path(args.output_root) if args.output_root else replay_path.parent

    try:
        classification = build_strategy_router_shadow_conflict_classification(
            replay_path,
        )
        paths = write_strategy_router_shadow_conflict_artifacts(
            classification,
            output_root,
        )
    except ValidationError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2

    summary = classification["summary"]
    print(f"classification_status={summary['classification_status']}")
    print(f"row_count={summary['row_count']}")
    print(f"conflict_row_count={summary['conflict_row_count']}")
    print(f"shadow_blocked_row_count={summary['shadow_blocked_row_count']}")
    print(f"classification_recommendation={summary['classification_recommendation']}")
    for name, path in paths.items():
        print(f"{name}={path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
