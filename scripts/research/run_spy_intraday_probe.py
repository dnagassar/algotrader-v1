"""Run the offline SPY intraday trend research probe."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import datetime
import json
import sys
from pathlib import Path
from typing import Sequence


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_PATH = _REPO_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from algotrader.errors import ValidationError  # noqa: E402
from algotrader.research.intraday_trend_probe import (  # noqa: E402
    INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL,
    IntradayBar,
    IntradayTrendProbeConfig,
    build_intraday_trend_probe_from_csv,
    load_local_intraday_bars_csv,
    validate_regular_session_intraday_bars,
    write_calendar_validation_report,
    write_intraday_bars_csv,
    write_intraday_probe_artifacts,
    write_sample_spy_intraday_fixture,
)


DEFAULT_OUTPUT_DIR = "runs/intraday_probe/v1_80"
DEFAULT_INPUT = f"{DEFAULT_OUTPUT_DIR}/spy_intraday_fixture_15m.csv"
DEFAULT_RUN_ID = "v1_80_spy_intraday_fixture_probe"
_COMPARISON_METRIC_KEYS = (
    "signal_flips",
    "average_holding_period_bars",
    "average_holding_period_hours",
    "exposure_percentage",
    "rough_turnover",
    "turnover_fraction",
    "gross_return",
    "slippage_adjusted_return",
    "max_drawdown",
    "buy_and_hold_return",
)


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
        "--tiingo-response-json",
        default=None,
        help="Optional local Tiingo IEX response JSON to normalize before running.",
    )
    parser.add_argument(
        "--calendar-validate",
        action="store_true",
        help="Validate and filter input bars against the NY regular-session calendar.",
    )
    parser.add_argument(
        "--calendar-valid-output",
        default=None,
        help="CSV path for calendar-valid normalized bars.",
    )
    parser.add_argument(
        "--calendar-validation-report",
        default=None,
        help="JSON path for the calendar validation report.",
    )
    parser.add_argument(
        "--normalized-artifact-name",
        default="normalized_spy_intraday_15m.csv",
        help="Normalized CSV artifact file name inside the output directory.",
    )
    parser.add_argument(
        "--before-results",
        default=None,
        help="Optional previous probe results JSON for before/after filtering metrics.",
    )
    parser.add_argument(
        "--write-sample-fixture",
        action="store_true",
        help="Write the deterministic SPY 15-minute fixture before running.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = Path(args.output_dir)
    input_path = Path(args.input)
    calendar_report: dict[str, object] | None = None
    calendar_report_path: Path | None = None
    raw_tiingo_response_reused = False

    try:
        if args.write_sample_fixture:
            write_sample_spy_intraday_fixture(input_path)
        if args.tiingo_response_json:
            raw_tiingo_response_reused = True
            write_intraday_bars_csv(
                _bars_from_tiingo_response(Path(args.tiingo_response_json)),
                input_path,
            )
        if args.calendar_validate:
            csv_result = load_local_intraday_bars_csv(
                input_path,
                symbol="SPY",
                source_timeframe_minutes=args.source_timeframe_minutes,
            )
            validation = validate_regular_session_intraday_bars(
                csv_result.bars,
                source_timeframe_minutes=args.source_timeframe_minutes,
            )
            calendar_report = validation.to_report()
            calendar_report_path = (
                Path(args.calendar_validation_report)
                if args.calendar_validation_report
                else output_dir / "calendar_validation_report.json"
            )
            write_calendar_validation_report(validation, calendar_report_path)
            if not validation.accepted_bars:
                raise ValidationError(
                    "calendar validation left no accepted SPY intraday bars."
                )
            calendar_valid_output = (
                Path(args.calendar_valid_output)
                if args.calendar_valid_output
                else output_dir / "normalized_spy_intraday_15m_calendar_valid.csv"
            )
            write_intraday_bars_csv(validation.accepted_bars, calendar_valid_output)
            input_path = calendar_valid_output

        build = build_intraday_trend_probe_from_csv(
            IntradayTrendProbeConfig(
                run_id=args.run_id,
                intraday_bars_csv=input_path,
                source_timeframe_minutes=args.source_timeframe_minutes,
                slippage_bps=args.slippage_bps,
                data_source_kind=args.data_source_kind,
                source_calendar_label=(
                    INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL
                    if calendar_report is not None
                    else None
                ),
                calendar_validation=calendar_report,
            )
        )
        build.payload["raw_tiingo_response_reused"] = raw_tiingo_response_reused
        if calendar_report is not None:
            build.payload["source_calendar_investigation"] = (
                _source_calendar_investigation(
                    calendar_report,
                    raw_tiingo_response_reused=raw_tiingo_response_reused,
                )
            )
        if args.before_results:
            build.payload["calendar_filter_comparison"] = (
                _calendar_filter_comparison(
                    _read_json_mapping(Path(args.before_results)),
                    build.payload,
                )
            )
        extra_artifacts: tuple[Path, ...] = (
            (calendar_report_path,) if calendar_report_path is not None else ()
        )
        paths = write_intraday_probe_artifacts(
            build,
            output_dir,
            normalized_filename=args.normalized_artifact_name,
            extra_artifact_paths=extra_artifacts,
        )
        if calendar_report_path is not None:
            paths["calendar_validation_report"] = calendar_report_path
    except ValidationError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2

    payload = build.payload
    print(f"classification: {payload['classification_recommendation']}")
    print(f"decision_quality: {payload['decision_quality']}")
    for name, path in paths.items():
        print(f"{name}: {path.as_posix()}")
    return 0


def _bars_from_tiingo_response(path: Path) -> tuple[IntradayBar, ...]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValidationError("Tiingo response JSON must contain a list of bars.")
    bars: list[IntradayBar] = []
    for index, row in enumerate(data, start=1):
        if not isinstance(row, Mapping):
            raise ValidationError(f"Tiingo response row {index} must be an object.")
        volume = row.get("volume", 0)
        bars.append(
            IntradayBar(
                symbol="SPY",
                timestamp=_parse_tiingo_timestamp(
                    _required_tiingo_field(row, "date", index),
                    index,
                ),
                open=str(_required_tiingo_field(row, "open", index)),
                high=str(_required_tiingo_field(row, "high", index)),
                low=str(_required_tiingo_field(row, "low", index)),
                close=str(_required_tiingo_field(row, "close", index)),
                volume=str(volume),
            )
        )
    return tuple(bars)


def _required_tiingo_field(
    row: Mapping[str, object],
    field_name: str,
    row_number: int,
) -> object:
    if field_name not in row or row[field_name] is None:
        raise ValidationError(
            f"Tiingo response row {row_number} is missing {field_name}."
        )
    return row[field_name]


def _parse_tiingo_timestamp(value: object, row_number: int) -> datetime:
    if type(value) is not str:
        raise ValidationError(
            f"Tiingo response row {row_number} date must be an ISO timestamp."
        )
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(
            f"Tiingo response row {row_number} date must be an ISO timestamp."
        ) from exc


def _read_json_mapping(path: Path) -> Mapping[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValidationError(f"{path.as_posix()} must contain a JSON object.")
    return data


def _source_calendar_investigation(
    calendar_report: Mapping[str, object],
    *,
    raw_tiingo_response_reused: bool,
) -> dict[str, object]:
    reason_codes = sorted(
        {
            str(reason.get("code", ""))
            for session in _mapping_sequence(calendar_report.get("rejected_sessions"))
            for reason in _mapping_sequence(session.get("reasons"))
        }
    )
    holiday_rejections = "market_holiday" in reason_codes
    return {
        "raw_v1_81_tiingo_response_reused": raw_tiingo_response_reused,
        "new_tiingo_fetch_performed": False,
        "request_receipt_inspected": False,
        "request_receipt_note": (
            "Skipped to avoid exposing possible credential material in the saved receipt."
        ),
        "finding": (
            "stored_raw_response_contains_known_market_holiday_regular_session_bars"
            if holiday_rejections
            else "stored_raw_response_passed_known_holiday_filter"
        ),
        "holiday_session_origin": (
            "stored_raw_tiingo_response" if holiday_rejections else "none_detected"
        ),
        "normalization_bug_indicated": False,
        "timezone_grouping_error_indicated": False,
        "request_parameter_cause_determined": False,
        "source_trust_posture": "calendar_filter_required_before_research_use",
        "provider_source_promotable_without_calendar_filter": False,
        "source_validation_conclusion": (
            "calendar_valid_after_filtering_known_holiday_sessions"
            if holiday_rejections
            else "calendar_valid_without_known_holiday_rejections"
        ),
        "recommendation_scope": (
            "research_only_later_preview_design_consideration_not_paper_or_live"
        ),
        "rejected_reason_codes": reason_codes,
    }


def _calendar_filter_comparison(
    before_payload: Mapping[str, object],
    after_payload: Mapping[str, object],
) -> dict[str, object]:
    before_candidates = {
        str(result.get("candidate", "")): result
        for result in _mapping_sequence(before_payload.get("candidate_results"))
    }
    comparisons: list[dict[str, object]] = []
    for after_result in _mapping_sequence(after_payload.get("candidate_results")):
        candidate = str(after_result.get("candidate", ""))
        before_result = before_candidates.get(candidate, {})
        comparisons.append(
            {
                "candidate": candidate,
                "before_filtering": _candidate_snapshot(before_result),
                "after_filtering": _candidate_snapshot(after_result),
            }
        )
    return {
        "before_filtering": _source_snapshot(before_payload),
        "after_filtering": _source_snapshot(after_payload),
        "candidates": comparisons,
    }


def _source_snapshot(payload: Mapping[str, object]) -> dict[str, object]:
    source = _mapping(payload.get("source"))
    return {
        "bar_count": source.get("bar_count"),
        "start_timestamp": source.get("start_timestamp"),
        "end_timestamp": source.get("end_timestamp"),
        "recommendation": payload.get("recommendation"),
    }


def _candidate_snapshot(result: Mapping[str, object]) -> dict[str, object]:
    metrics = _mapping(result.get("metrics"))
    return {
        "bar_count": result.get("bar_count"),
        "start_timestamp": result.get("start_timestamp"),
        "end_timestamp": result.get("end_timestamp"),
        "metrics": {
            key: metrics.get(key)
            for key in _COMPARISON_METRIC_KEYS
            if key in metrics
        },
        "churn_assessment": result.get("churn_assessment"),
    }


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _mapping_sequence(value: object) -> tuple[Mapping[str, object], ...]:
    if isinstance(value, list | tuple):
        return tuple(_mapping(item) for item in value)
    return ()


if __name__ == "__main__":
    raise SystemExit(main())
