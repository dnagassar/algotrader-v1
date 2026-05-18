"""Local-only SPY SMA-200 research report runner."""

from __future__ import annotations

import argparse
import hashlib
import json
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
    DailyExposure,
    DailyBacktestResult,
    run_daily_backtest,
)
from algotrader.research.price_snapshot import (  # noqa: E402
    HistoricalPriceSnapshot,
    load_historical_price_snapshot_csv,
)
from algotrader.research.moving_average import MovingAverageInput  # noqa: E402
from algotrader.research.moving_average_replay import (  # noqa: E402
    MovingAverageReplayPackage,
    build_moving_average_replay_package,
)
from algotrader.research.price_snapshot_manifest import (  # noqa: E402
    ADJUSTMENT_POLICIES,
    ADJUSTMENT_POLICY_ADJUSTED_CLOSE,
    ADJUSTMENT_POLICY_RAW,
    ADJUSTMENT_POLICY_TOTAL_RETURN,
    ADJUSTMENT_POLICY_UNKNOWN,
    SOURCE_TYPE_MANUAL_DOWNLOAD,
    LocalPriceSnapshotManifest,
    build_local_price_snapshot_manifest,
)


DEFAULT_INITIAL_EQUITY = Decimal("10000")
DEFAULT_FEE_BPS = Decimal("0")
DEFAULT_SLIPPAGE_BPS = Decimal("0")
DEFAULT_SOURCE_NAME = "manual_local_snapshot"
DEFAULT_SOURCE_TYPE = SOURCE_TYPE_MANUAL_DOWNLOAD
DEFAULT_ADJUSTMENT_POLICY = ADJUSTMENT_POLICY_UNKNOWN
REPORT_TITLE = "SPY SMA-200 Local Research Run"
_SNAPSHOT_SYMBOL = "SPY"
_DATA_DIR = Path(".data") / "research_snapshots"
_HASH_CHUNK_SIZE = 1024 * 1024
_RETURN_BASIS_PRICE_RETURN = "price_return"
_RETURN_BASIS_TOTAL_RETURN = "total_return"
_ADJUSTED_CLOSE_SOURCE_CLOSE_PRICE_FALLBACK = "close_price_fallback"
_ADJUSTED_CLOSE_SOURCE_TRUE_ADJUSTED = "true_adjusted_close"
_SMA_200_WINDOW = 200
_SPY_SMA200_REPLAY_ID = "spy-sma200-local-research"

_DISCLAIMER = (
    "Advisory/research only: this local report is not validated evidence, "
    "not an approved signal, not live or paper trading authority, and not a "
    "trading recommendation."
)
_RULE_LINES = (
    "SMA window: 200 selected close observations.",
    "Exposure = 1 when the selected close series > trailing 200-day SMA.",
    "Exposure = 0 otherwise.",
    "First 199 bars are exposure 0.",
    "The trailing SMA is computed from the 200 selected close values through the current bar.",
    "Backtest applies exposure to next day return through previous-exposure convention.",
)
_BASELINE_LINES = (
    "Buy-and-hold baseline uses the same loaded local snapshot as the SMA-200 run.",
    "Buy-and-hold exposure is 1 on every loaded bar.",
    "The first bar has zero asset return under the daily backtest convention.",
)
_LIMITATION_LINES = (
    "Local snapshot only.",
    "Source not approved.",
    "No external benchmark, second symbol, or second snapshot comparison.",
    "No parameter sweep.",
    "No transaction-cost realism unless assumptions are explicitly set.",
    "Not validated evidence.",
    "Not a trading recommendation.",
    "Not production signal/evaluator behavior.",
    "No dividend, corporate-action, or total-return claim is made unless explicitly supported.",
)
_NON_CLAIM_LINES = (
    "Advisory/research only.",
    "Not validated evidence.",
    "Not a trading recommendation.",
    "Not an approved signal.",
    "Not live or paper trading authority.",
    "No broker, order, fill, account, position, portfolio, allocation, or target-weight behavior.",
    "No executable signals, execution plans, portfolio updates, or trading actions are created.",
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
    json_output_path: str | Path | None = None,
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
    checked_json_output_path = _json_output_path_value(
        json_output_path,
        checked_output_path,
    )
    checked_adjustment_policy = _adjustment_policy_value(adjustment_policy)
    assumptions = DailyBacktestAssumptions(
        initial_equity=_decimal_value(initial_equity, "initial_equity"),
        fee_bps=_decimal_value(fee_bps, "fee_bps"),
        slippage_bps=_decimal_value(slippage_bps, "slippage_bps"),
    )

    snapshot = load_historical_price_snapshot_csv(checked_csv_path, _SNAPSHOT_SYMBOL)
    _validate_adjustment_policy_snapshot(snapshot, checked_adjustment_policy)
    file_sha256 = compute_file_sha256(checked_csv_path)
    manifest = build_local_price_snapshot_manifest(
        snapshot,
        source_name=source_name,
        source_type=source_type,
        file_name=checked_csv_path.name,
        file_sha256=file_sha256,
        adjustment_policy=checked_adjustment_policy,
        created_at=snapshot.bars[-1].date,
        limitations=_LIMITATION_LINES,
    )
    replay_package = _build_spy_sma200_replay_package(snapshot)
    exposures = _daily_exposures_from_replay_package(replay_package)
    buy_and_hold_exposures = _build_buy_and_hold_daily_exposures(snapshot)
    result = run_daily_backtest(snapshot, exposures, assumptions)
    buy_and_hold_result = run_daily_backtest(
        snapshot,
        buy_and_hold_exposures,
        assumptions,
    )
    report = render_spy_sma200_report(
        manifest=manifest,
        result=result,
        buy_and_hold_result=buy_and_hold_result,
    )

    if checked_output_path is not None:
        checked_output_path.write_text(report, encoding="utf-8")
        assert checked_json_output_path is not None
        checked_json_output_path.write_text(
            render_spy_sma200_report_json(
                manifest=manifest,
                result=result,
                buy_and_hold_result=buy_and_hold_result,
            ),
            encoding="utf-8",
        )

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
    buy_and_hold_result: DailyBacktestResult,
) -> str:
    """Render a metadata-only markdown research report."""
    return_metric_name = _return_metric_name(manifest)
    adjusted_close_available = _adjusted_close_available(manifest)
    adjusted_close_source = _adjusted_close_source(manifest)
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
        f"- Return basis: {return_metric_name}",
        f"- Adjusted close available: {str(adjusted_close_available).lower()}",
        f"- Adjusted close source: {adjusted_close_source}",
        "",
        "## Assumptions",
        f"- Initial equity: {_decimal_text(result.assumptions.initial_equity)}",
        f"- Fee bps: {_decimal_text(result.assumptions.fee_bps)}",
        f"- Slippage bps: {_decimal_text(result.assumptions.slippage_bps)}",
        "",
        "## Rule",
        *[f"- {line}" for line in _RULE_LINES],
        "",
        "## SMA Mechanics",
        f"- sma_window: {_SMA_200_WINDOW}",
        f"- minimum_observations: {_SMA_200_WINDOW}",
        f"- fully_formed_sma_observations: {_fully_formed_sma_observations(manifest)}",
        f"- insufficient_observations: {str(_sma_insufficient_observations(manifest)).lower()}",
        "- timing: same-close observation metadata with previous-exposure backtest convention",
        "",
        "## Baseline",
        *[f"- {line}" for line in _BASELINE_LINES],
        "",
        "## Metrics",
        f"- return_basis: {return_metric_name}",
        f"- starting_equity: {_decimal_text(result.starting_equity)}",
        f"- ending_equity_strategy: {_decimal_text(result.ending_equity)}",
        f"- ending_equity_buy_and_hold: {_decimal_text(buy_and_hold_result.ending_equity)}",
        f"- {return_metric_name}_strategy: {_decimal_text(result.total_return)}",
        f"- {return_metric_name}_buy_and_hold: {_decimal_text(buy_and_hold_result.total_return)}",
        f"- max_drawdown_strategy: {_decimal_text(result.max_drawdown)}",
        f"- max_drawdown_buy_and_hold: {_decimal_text(buy_and_hold_result.max_drawdown)}",
        f"- exposure_ratio_strategy: {_decimal_text(result.exposure_ratio)}",
        f"- exposure_ratio_buy_and_hold: {_decimal_text(buy_and_hold_result.exposure_ratio)}",
        f"- turnover_strategy: {_decimal_text(result.turnover)}",
        f"- turnover_buy_and_hold: {_decimal_text(buy_and_hold_result.turnover)}",
        "",
        "## Limitations",
        *[f"- {line}" for line in _LIMITATION_LINES],
        "",
        "## Non-Claims",
        *[f"- {line}" for line in _NON_CLAIM_LINES],
        "",
        "## Verdict",
        f"- {_VERDICT}",
        "",
    ]
    return "\n".join(lines)


def render_spy_sma200_report_json(
    *,
    manifest: LocalPriceSnapshotManifest,
    result: DailyBacktestResult,
    buy_and_hold_result: DailyBacktestResult,
) -> str:
    """Render deterministic JSON sidecar text without raw bar data."""
    payload = _report_payload(
        manifest=manifest,
        result=result,
        buy_and_hold_result=buy_and_hold_result,
    )
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


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
    parser.add_argument(
        "--json-output",
        default=None,
        help="Optional explicit JSON sidecar output path. Defaults to --output with .json suffix.",
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
            json_output_path=args.json_output,
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
    if checked_path.suffix.lower() == ".json":
        raise ValidationError("output path must be the markdown report path, not .json.")

    return checked_path


def _json_output_path_value(
    json_output_path: str | Path | None,
    output_path: Path | None,
) -> Path | None:
    if json_output_path is None:
        if output_path is None:
            return None
        return _json_sidecar_path_value(output_path)
    if output_path is None:
        raise ValidationError("JSON output path requires a markdown output path.")
    if isinstance(json_output_path, str) and not json_output_path.strip():
        raise ValidationError("JSON output path is required when provided.")
    if not isinstance(json_output_path, (str, Path)):
        raise ValidationError("JSON output path must be a local path.")

    checked_path = Path(json_output_path).expanduser().resolve()
    if any(part == ".data" for part in checked_path.parts):
        raise ValidationError("JSON output path must not point inside .data/.")
    if checked_path.suffix.lower() != ".json":
        raise ValidationError("JSON output path must use a .json suffix.")
    if checked_path == output_path:
        raise ValidationError("JSON sidecar path must be separate from markdown output.")

    return checked_path


def _json_sidecar_path_value(output_path: Path) -> Path:
    sidecar_path = output_path.with_suffix(".json")
    if sidecar_path == output_path:
        raise ValidationError("JSON sidecar path must be separate from markdown output.")

    return sidecar_path


def build_sma_200_daily_exposures(
    snapshot: HistoricalPriceSnapshot,
) -> tuple[DailyExposure, ...]:
    replay_package = _build_spy_sma200_replay_package(snapshot)

    return _daily_exposures_from_replay_package(replay_package)


def _build_spy_sma200_replay_package(
    snapshot: HistoricalPriceSnapshot,
) -> MovingAverageReplayPackage:
    checked_snapshot = _snapshot_value(snapshot)
    inputs = _moving_average_inputs_from_snapshot(checked_snapshot)

    return build_moving_average_replay_package(
        replay_id=_SPY_SMA200_REPLAY_ID,
        as_of_date=checked_snapshot.bars[-1].date,
        inputs=inputs,
        window=_SMA_200_WINDOW,
    )


def _moving_average_inputs_from_snapshot(
    snapshot: HistoricalPriceSnapshot,
) -> tuple[MovingAverageInput, ...]:
    return tuple(
        MovingAverageInput(
            observation_date=bar.date,
            value=bar.adjusted_close,
        )
        for bar in snapshot.bars
    )


def _daily_exposures_from_replay_package(
    replay_package: MovingAverageReplayPackage,
) -> tuple[DailyExposure, ...]:
    return tuple(
        DailyExposure(
            date=state.observation_date,
            exposure=Decimal(state.next_exposure),
        )
        for state in replay_package.exposure_states
    )


def _snapshot_value(value: HistoricalPriceSnapshot) -> HistoricalPriceSnapshot:
    if not isinstance(value, HistoricalPriceSnapshot):
        raise ValidationError("snapshot must be a HistoricalPriceSnapshot.")
    if not value.bars:
        raise ValidationError("snapshot bars must contain HistoricalPriceBar values.")

    return value


def _build_buy_and_hold_daily_exposures(
    snapshot: HistoricalPriceSnapshot,
) -> tuple[DailyExposure, ...]:
    return tuple(
        DailyExposure(date=bar.date, exposure=Decimal("1")) for bar in snapshot.bars
    )


def _report_payload(
    *,
    manifest: LocalPriceSnapshotManifest,
    result: DailyBacktestResult,
    buy_and_hold_result: DailyBacktestResult,
) -> dict[str, object]:
    return_metric_name = _return_metric_name(manifest)
    return {
        "adjusted_close_available": _adjusted_close_available(manifest),
        "adjusted_close_source": _adjusted_close_source(manifest),
        "adjustment_policy": manifest.adjustment_policy,
        "assumptions": _assumptions_payload(result),
        "baseline": list(_BASELINE_LINES),
        "disclaimer": _DISCLAIMER,
        "limitations": list(_LIMITATION_LINES),
        "metrics": _metrics_payload(
            return_metric_name=return_metric_name,
            result=result,
            buy_and_hold_result=buy_and_hold_result,
        ),
        "non_claims": list(_NON_CLAIM_LINES),
        "provenance": manifest.to_dict(),
        "report_title": REPORT_TITLE,
        "return_basis": return_metric_name,
        "rule": list(_RULE_LINES),
        "sma_mechanics": _sma_mechanics_payload(manifest),
        "verdict": _VERDICT,
    }


def _assumptions_payload(result: DailyBacktestResult) -> dict[str, str]:
    return {
        "fee_bps": _decimal_text(result.assumptions.fee_bps),
        "initial_equity": _decimal_text(result.assumptions.initial_equity),
        "slippage_bps": _decimal_text(result.assumptions.slippage_bps),
    }


def _metrics_payload(
    *,
    return_metric_name: str,
    result: DailyBacktestResult,
    buy_and_hold_result: DailyBacktestResult,
) -> dict[str, str]:
    return {
        "ending_equity_buy_and_hold": _decimal_text(buy_and_hold_result.ending_equity),
        "ending_equity_strategy": _decimal_text(result.ending_equity),
        "exposure_ratio_buy_and_hold": _decimal_text(
            buy_and_hold_result.exposure_ratio
        ),
        "exposure_ratio_strategy": _decimal_text(result.exposure_ratio),
        "max_drawdown_buy_and_hold": _decimal_text(buy_and_hold_result.max_drawdown),
        "max_drawdown_strategy": _decimal_text(result.max_drawdown),
        f"{return_metric_name}_buy_and_hold": _decimal_text(
            buy_and_hold_result.total_return
        ),
        f"{return_metric_name}_strategy": _decimal_text(result.total_return),
        "starting_equity": _decimal_text(result.starting_equity),
        "turnover_buy_and_hold": _decimal_text(buy_and_hold_result.turnover),
        "turnover_strategy": _decimal_text(result.turnover),
    }


def _return_metric_name(manifest: LocalPriceSnapshotManifest) -> str:
    if manifest.adjustment_policy == ADJUSTMENT_POLICY_TOTAL_RETURN:
        return _RETURN_BASIS_TOTAL_RETURN

    return _RETURN_BASIS_PRICE_RETURN


def _sma_mechanics_payload(manifest: LocalPriceSnapshotManifest) -> dict[str, object]:
    return {
        "fully_formed_sma_observations": _fully_formed_sma_observations(manifest),
        "insufficient_observations": _sma_insufficient_observations(manifest),
        "minimum_observations": _SMA_200_WINDOW,
        "sma_window": _SMA_200_WINDOW,
        "timing": "same-close observation metadata with previous-exposure backtest convention",
    }


def _fully_formed_sma_observations(manifest: LocalPriceSnapshotManifest) -> int:
    return max(manifest.row_count - (_SMA_200_WINDOW - 1), 0)


def _sma_insufficient_observations(manifest: LocalPriceSnapshotManifest) -> bool:
    return manifest.row_count < _SMA_200_WINDOW


def _adjusted_close_available(manifest: LocalPriceSnapshotManifest) -> bool:
    return manifest.adjustment_policy in (
        ADJUSTMENT_POLICY_ADJUSTED_CLOSE,
        ADJUSTMENT_POLICY_TOTAL_RETURN,
    )


def _adjusted_close_source(manifest: LocalPriceSnapshotManifest) -> str:
    if manifest.adjustment_policy in (
        ADJUSTMENT_POLICY_RAW,
        ADJUSTMENT_POLICY_UNKNOWN,
    ):
        return _ADJUSTED_CLOSE_SOURCE_CLOSE_PRICE_FALLBACK

    return _ADJUSTED_CLOSE_SOURCE_TRUE_ADJUSTED


def _adjustment_policy_value(value: str) -> str:
    allowed = ", ".join(ADJUSTMENT_POLICIES)
    if not isinstance(value, str):
        raise ValidationError(f"adjustment_policy must be one of: {allowed}.")

    normalized = value.strip().lower()
    if normalized not in ADJUSTMENT_POLICIES:
        raise ValidationError(f"adjustment_policy must be one of: {allowed}.")

    return normalized


def _validate_adjustment_policy_snapshot(
    snapshot: HistoricalPriceSnapshot,
    adjustment_policy: str,
) -> None:
    if adjustment_policy != ADJUSTMENT_POLICY_TOTAL_RETURN:
        return

    for bar in snapshot.bars:
        if (
            not isinstance(bar.adjusted_close, Decimal)
            or not bar.adjusted_close.is_finite()
            or bar.adjusted_close <= 0
        ):
            raise ValidationError(
                "adjustment_policy=total_return requires usable adjusted_close values."
            )


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
