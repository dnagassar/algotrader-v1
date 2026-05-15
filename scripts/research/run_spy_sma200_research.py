"""Local-only SPY SMA-200 research report runner."""

from __future__ import annotations

import argparse
import hashlib
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_PATH = _REPO_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from algotrader.errors import ValidationError
from algotrader.research.daily_backtest import (  # noqa: E402
    DailyBacktestAssumptions,
    DailyBacktestResult,
    run_daily_backtest,
)
from algotrader.research.price_snapshot import (  # noqa: E402
    load_historical_price_snapshot_csv,
)
from algotrader.research.price_snapshot_manifest import (  # noqa: E402
    ADJUSTMENT_POLICY_ADJUSTED_CLOSE,
    SOURCE_TYPE_MANUAL_DOWNLOAD,
    LocalPriceSnapshotManifest,
    build_local_price_snapshot_manifest,
)
from algotrader.research.sma_exposure import build_sma_200_daily_exposures  # noqa: E402


DEFAULT_INITIAL_EQUITY = Decimal("10000")
DEFAULT_FEE_BPS = Decimal("0")
DEFAULT_SLIPPAGE_BPS = Decimal("0")
DEFAULT_SOURCE_NAME = "manual_local_snapshot"
DEFAULT_SOURCE_TYPE = SOURCE_TYPE_MANUAL_DOWNLOAD
DEFAULT_ADJUSTMENT_POLICY = ADJUSTMENT_POLICY_ADJUSTED_CLOSE
REPORT_TITLE = "SPY SMA-200 Local Research Run"
_SNAPSHOT_SYMBOL = "SPY"
_DATA_DIR = Path(".data") / "research_snapshots"
_HASH_CHUNK_SIZE = 1024 * 1024

_DISCLAIMER = (
    "Advisory only: this local report is not validated evidence, not approved, "
    "and not a trading recommendation. It must not be used as production "
    "signal/evaluator behavior or a trading workflow."
)
_RULE_LINES = (
    "Exposure = 1 when adjusted_close > trailing 200-day SMA.",
    "Exposure = 0 otherwise.",
    "First 199 bars are exposure 0.",
    "The trailing SMA is computed from the 200 adjusted_close values through the current bar.",
    "Backtest applies exposure to next day return through previous-exposure convention.",
)
_LIMITATION_LINES = (
    "Local snapshot only.",
    "Source not approved.",
    "No benchmark comparison yet.",
    "No parameter sweep.",
    "No transaction-cost realism unless assumptions are explicitly set.",
    "Not validated evidence.",
    "Not a trading recommendation.",
    "Not production signal/evaluator behavior.",
)
_VERDICT = "Advisory only / not validated / not approved."


def run_spy_sma200_research(
    csv_path: str | Path | None,
    *,
    initial_equity: Decimal | str = DEFAULT_INITIAL_EQUITY,
    fee_bps: Decimal | str = DEFAULT_FEE_BPS,
    slippage_bps: Decimal | str = DEFAULT_SLIPPAGE_BPS,
    source_name: str = DEFAULT_SOURCE_NAME,
    source_type: str = DEFAULT_SOURCE_TYPE,
    adjustment_policy: str = DEFAULT_ADJUSTMENT_POLICY,
    allow_outside_data_dir: bool = False,
    output_path: str | Path | None = None,
    repo_root: str | Path | None = None,
) -> str:
    """Run the local SPY SMA-200 research path and return markdown text."""
    checked_repo_root = _repo_root_value(repo_root)
    checked_csv_path = _csv_path_value(
        csv_path,
        repo_root=checked_repo_root,
        allow_outside_data_dir=allow_outside_data_dir,
    )
    checked_output_path = _output_path_value(output_path)
    assumptions = DailyBacktestAssumptions(
        initial_equity=_decimal_value(initial_equity, "initial_equity"),
        fee_bps=_decimal_value(fee_bps, "fee_bps"),
        slippage_bps=_decimal_value(slippage_bps, "slippage_bps"),
    )

    snapshot = load_historical_price_snapshot_csv(checked_csv_path, _SNAPSHOT_SYMBOL)
    file_sha256 = compute_file_sha256(checked_csv_path)
    manifest = build_local_price_snapshot_manifest(
        snapshot,
        source_name=source_name,
        source_type=source_type,
        file_name=checked_csv_path.name,
        file_sha256=file_sha256,
        adjustment_policy=adjustment_policy,
        created_at=snapshot.bars[-1].date,
        limitations=_LIMITATION_LINES,
    )
    exposures = build_sma_200_daily_exposures(snapshot)
    result = run_daily_backtest(snapshot, exposures, assumptions)
    report = render_spy_sma200_report(manifest=manifest, result=result)

    if checked_output_path is not None:
        checked_output_path.write_text(report, encoding="utf-8")

    return report


def compute_file_sha256(path: str | Path) -> str:
    """Return the sha256 hex digest for a local file using stdlib hashing."""
    checked_path = Path(path)
    digest = hashlib.sha256()

    with checked_path.open("rb") as source:
        while True:
            chunk = source.read(_HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def render_spy_sma200_report(
    *,
    manifest: LocalPriceSnapshotManifest,
    result: DailyBacktestResult,
) -> str:
    """Render a metadata-only markdown research report."""
    lines = [
        f"# {REPORT_TITLE}",
        "",
        _DISCLAIMER,
        "",
        "## Data Source",
        f"- Source name: {manifest.source_name}",
        f"- Source type: {manifest.source_type}",
        f"- CSV file: {manifest.file_name}",
        f"- File SHA-256: {manifest.file_sha256}",
        f"- Snapshot fingerprint: {manifest.snapshot_fingerprint}",
        f"- Date range: {manifest.start_date.isoformat()} to {manifest.end_date.isoformat()}",
        f"- Row count: {manifest.row_count}",
        f"- Adjustment policy: {manifest.adjustment_policy}",
        "",
        "## Assumptions",
        f"- Initial equity: {_decimal_text(result.assumptions.initial_equity)}",
        f"- Fee bps: {_decimal_text(result.assumptions.fee_bps)}",
        f"- Slippage bps: {_decimal_text(result.assumptions.slippage_bps)}",
        "",
        "## Rule",
        *[f"- {line}" for line in _RULE_LINES],
        "",
        "## Metrics",
        f"- Starting equity: {_decimal_text(result.starting_equity)}",
        f"- Ending equity: {_decimal_text(result.ending_equity)}",
        f"- Total return: {_decimal_text(result.total_return)}",
        f"- Max drawdown: {_decimal_text(result.max_drawdown)}",
        f"- Exposure ratio: {_decimal_text(result.exposure_ratio)}",
        f"- Turnover: {_decimal_text(result.turnover)}",
        "",
        "## Limitations",
        *[f"- {line}" for line in _LIMITATION_LINES],
        "",
        "## Verdict",
        f"- {_VERDICT}",
        "",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a local-only SPY SMA-200 research report from an explicit CSV snapshot.",
    )
    parser.add_argument("csv_path", help="Explicit local SPY daily CSV path.")
    parser.add_argument(
        "--initial-equity",
        default=str(DEFAULT_INITIAL_EQUITY),
        help="Initial equity Decimal string. Default: 10000.",
    )
    parser.add_argument(
        "--fee-bps",
        default=str(DEFAULT_FEE_BPS),
        help="Fee assumption in basis points. Default: 0.",
    )
    parser.add_argument(
        "--slippage-bps",
        default=str(DEFAULT_SLIPPAGE_BPS),
        help="Slippage assumption in basis points. Default: 0.",
    )
    parser.add_argument(
        "--source-name",
        default=DEFAULT_SOURCE_NAME,
        help="Local provenance source name.",
    )
    parser.add_argument(
        "--source-type",
        default=DEFAULT_SOURCE_TYPE,
        help="Local provenance source type.",
    )
    parser.add_argument(
        "--adjustment-policy",
        default=DEFAULT_ADJUSTMENT_POLICY,
        help="Adjustment policy metadata value.",
    )
    parser.add_argument(
        "--allow-outside-data-dir",
        action="store_true",
        help="Allow CSV paths outside .data/research_snapshots/.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional markdown output path. Stdout is used when omitted.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        report = run_spy_sma200_research(
            args.csv_path,
            initial_equity=args.initial_equity,
            fee_bps=args.fee_bps,
            slippage_bps=args.slippage_bps,
            source_name=args.source_name,
            source_type=args.source_type,
            adjustment_policy=args.adjustment_policy,
            allow_outside_data_dir=args.allow_outside_data_dir,
            output_path=args.output,
        )
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.output is None:
        sys.stdout.write(report)

    return 0


def _repo_root_value(repo_root: str | Path | None) -> Path:
    if repo_root is None:
        return _REPO_ROOT
    if isinstance(repo_root, str) and not repo_root.strip():
        raise ValidationError("repo_root is required.")
    if not isinstance(repo_root, (str, Path)):
        raise ValidationError("repo_root must be a local path.")

    return Path(repo_root).expanduser().resolve()


def _csv_path_value(
    csv_path: str | Path | None,
    *,
    repo_root: Path,
    allow_outside_data_dir: bool,
) -> Path:
    if csv_path is None:
        raise ValidationError("CSV path is required.")
    if isinstance(csv_path, str) and not csv_path.strip():
        raise ValidationError("CSV path is required.")
    if not isinstance(csv_path, (str, Path)):
        raise ValidationError("CSV path must be a local path.")

    checked_path = Path(csv_path).expanduser().resolve()
    allowed_dir = (repo_root / _DATA_DIR).resolve()
    if not allow_outside_data_dir and not _is_relative_to(checked_path, allowed_dir):
        raise ValidationError(
            "CSV path must be under .data/research_snapshots/ unless "
            "--allow-outside-data-dir is provided."
        )

    return checked_path


def _output_path_value(output_path: str | Path | None) -> Path | None:
    if output_path is None:
        return None
    if isinstance(output_path, str) and not output_path.strip():
        raise ValidationError("output path is required when --output is provided.")
    if not isinstance(output_path, (str, Path)):
        raise ValidationError("output path must be a local path.")

    checked_path = Path(output_path).expanduser().resolve()
    if any(part == ".data" for part in checked_path.parts):
        raise ValidationError("output path must not point inside .data/.")

    return checked_path


def _decimal_value(value: Decimal | str, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a Decimal string.")

    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} must be a Decimal string.")

    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} must be a Decimal string.") from exc


def _decimal_text(value: Decimal) -> str:
    return str(value)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False

    return True


if __name__ == "__main__":
    raise SystemExit(main())
