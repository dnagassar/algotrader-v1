"""Command-line interface for the deterministic paper-trading core."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
import json
import sys

from .execution.paper_order_policy import (
    ASSET_CLASS_CHOICES as _PAPER_ORDER_ASSET_CLASSES,
    ASSET_CLASS_CRYPTO as _PAPER_ORDER_ASSET_CLASS_CRYPTO,
    ASSET_CLASS_EQUITY as _PAPER_ORDER_ASSET_CLASS_EQUITY,
    ASSET_CLASS_OPTION as _PAPER_ORDER_ASSET_CLASS_OPTION,
    PAPER_CLOSE_PREVIEW_GATE_ORDER as _PAPER_CLOSE_PREVIEW_GATE_ORDER,
    PAPER_MARKET_SESSION_NOTE as _PAPER_MARKET_SESSION_NOTE,
    PAPER_ORDER_PROBE_QTY_DISABLED_REASON as _PAPER_ORDER_PROBE_QTY_DISABLED_REASON,
    PAPER_SPY_CLOSE_PREVIEW_OPERATOR_INSTRUCTION as _PAPER_SPY_CLOSE_PREVIEW_OPERATOR_INSTRUCTION,
    PAPER_SPY_CLOSE_PREVIEW_REQUIRED_OBSERVATION_STATUS as _PAPER_SPY_CLOSE_PREVIEW_REQUIRED_OBSERVATION_STATUS,
    PAPER_SPY_CLOSE_SUBMIT_BLOCKED_STATE as _PAPER_SPY_CLOSE_SUBMIT_BLOCKED_STATE,
    PAPER_SPY_CLOSE_SUBMIT_CLIENT_ORDER_ID as _PAPER_SPY_CLOSE_SUBMIT_CLIENT_ORDER_ID,
    PAPER_SPY_CLOSE_SUBMIT_EXPECTED_QUANTITY as _PAPER_SPY_CLOSE_SUBMIT_EXPECTED_QUANTITY,
    PAPER_SPY_CLOSE_SUBMIT_GATE_ORDER as _PAPER_SPY_CLOSE_SUBMIT_GATE_ORDER,
    PAPER_SPY_CLOSE_SUBMIT_READY_M354_STATE as _PAPER_SPY_CLOSE_SUBMIT_READY_M354_STATE,
    PAPER_SPY_CLOSE_SUBMIT_READY_STATE as _PAPER_SPY_CLOSE_SUBMIT_READY_STATE,
    build_btcusd_paper_close_preview_contract,
    build_spy_paper_close_preview_contract,
    build_spy_paper_close_submit_contract,
    paper_order_policy_for_asset_class,
)

_PROFILE_NAMES = ("dev", "paper", "live")
_PREVIEW_FORMATS = ("text", "json")
_PAPER_ORDER_EQUITY_POLICY = paper_order_policy_for_asset_class("equity")
_PAPER_ORDER_PROBE_SYMBOL_ALLOWLIST = (
    _PAPER_ORDER_EQUITY_POLICY.symbol_allowlist or ()
)
_PAPER_ORDER_PROBE_MAX_NOTIONAL_CAP = (
    _PAPER_ORDER_EQUITY_POLICY.max_notional_cap or Decimal("0")
)
_PAPER_ORDER_PROBE_CLIENT_ORDER_ID = "paper-order-probe-notional-1"
_PAPER_ORDER_PROBE_CLIENT_ORDER_ID_PREFIX = "paper-order-probe"
_PAPER_ORDER_PROBE_CLIENT_ORDER_ID_RUN_ID_LENGTH = 30
_PAPER_CLOSE_PROBE_CLIENT_ORDER_ID_PREFIX = "paper-close-probe"
_PAPER_SAFETY_GATE_ORDER = (
    "profile_gate",
    "halt_gate",
    "allowlist_gate",
    "side_gate",
    "sizing_gate",
    "quantity_gate",
    "notional_value_gate",
    "notional_min_gate",
    "notional_cap_gate",
    "submit_confirmation_gate",
)
_PAPER_CLOSE_PROBE_GATE_ORDER = (
    "profile_gate",
    "halt_gate",
    "asset_class_gate",
    "symbol_gate",
    "side_gate",
    "quantity_gate",
    "max_quantity_gate",
    "quantity_within_max_gate",
    "submit_confirmation_gate",
    "pre_submit_observation_gate",
    "observed_position_gate",
    "observed_position_quantity_gate",
    "close_quantity_within_observed_position_gate",
    "no_shorting_gate",
    "recent_order_query_metadata_gate",
    "recent_open_order_gate",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="algotrader")
    parser.add_argument(
        "--profile",
        choices=_PROFILE_NAMES,
        default=None,
        help="Runtime profile to load. Defaults to ALGOTRADER_PROFILE or dev.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override the configured log level for this run.",
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("config", help="Print the active runtime profile.")
    demo_parser = subparsers.add_parser(
        "demo-core",
        help="Run one deterministic local trading-flow demo.",
    )
    demo_parser.add_argument(
        "--scenario",
        default="approved_and_filled",
        help="Named deterministic scenario to run.",
    )
    demo_parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List available deterministic demo scenarios.",
    )
    preview_parser = subparsers.add_parser(
        "advisory-operating-brief-preview",
        help="Print the synthetic advisory operating brief preview.",
    )
    preview_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Preview output format.",
    )
    content_bundle_preview_parser = subparsers.add_parser(
        "advisory-operating-brief-content-bundle-preview",
        help="Print the synthetic advisory operating brief content bundle preview.",
    )
    content_bundle_preview_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Preview output format.",
    )
    package_preview_parser = subparsers.add_parser(
        "advisory-operating-brief-package-preview",
        help="Print the synthetic advisory operating brief package preview.",
    )
    package_preview_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Preview output format.",
    )
    mvp_preview_parser = subparsers.add_parser(
        "advisory-operating-brief-mvp-preview",
        help="Print the synthetic research MVP operating brief preview.",
    )
    mvp_preview_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Preview output format.",
    )
    paper_account_parser = subparsers.add_parser(
        "paper-account-smoke",
        help="Read Alpaca paper account and positions through the paper boundary.",
    )
    paper_account_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Smoke output format.",
    )
    _add_paper_lab_run_log_options(paper_account_parser)
    paper_lab_snapshot_parser = subparsers.add_parser(
        "paper-lab-snapshot",
        help="Read a deterministic Alpaca paper account, positions, and orders snapshot.",
    )
    paper_lab_snapshot_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Snapshot output format.",
    )
    _add_paper_lab_run_log_options(paper_lab_snapshot_parser)
    paper_lab_order_traceability_parser = subparsers.add_parser(
        "paper-lab-order-traceability-review",
        help="Read a bounded SPY paper order traceability review without mutation.",
    )
    paper_lab_order_traceability_parser.add_argument(
        "--symbol",
        default="SPY",
        help="Paper symbol to review. Default: SPY.",
    )
    paper_lab_order_traceability_parser.add_argument(
        "--source-order-run-log",
        default="runs/paper_lab/m351_spy_tiny_paper_probe.jsonl",
        help="Local M351 paper order probe JSONL evidence path.",
    )
    paper_lab_order_traceability_parser.add_argument(
        "--source-snapshot-run-log",
        default="runs/paper_lab/m352_spy_settlement_review_snapshot.jsonl",
        help="Local M352 read-only snapshot JSONL evidence path.",
    )
    paper_lab_order_traceability_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Traceability review output format.",
    )
    _add_paper_lab_run_log_options(paper_lab_order_traceability_parser)
    paper_lab_spy_close_preview_parser = subparsers.add_parser(
        "paper-lab-spy-close-preview",
        help="Preview SPY paper cleanup-close readiness without mutation.",
    )
    paper_lab_spy_close_preview_parser.add_argument(
        "--symbol",
        default="SPY",
        help="Paper symbol to preview for cleanup close. Default: SPY.",
    )
    paper_lab_spy_close_preview_parser.add_argument(
        "--source-traceability-run-log",
        default="runs/paper_lab/m353_spy_order_traceability_review.jsonl",
        help="Local M353 SPY traceability JSONL evidence path.",
    )
    paper_lab_spy_close_preview_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Close-preview readiness output format.",
    )
    _add_paper_lab_run_log_options(paper_lab_spy_close_preview_parser)
    paper_lab_spy_close_submit_parser = subparsers.add_parser(
        "paper-lab-spy-close-submit",
        help="Submit the explicitly gated M355 SPY paper cleanup close.",
    )
    paper_lab_spy_close_submit_parser.add_argument(
        "--m354-run-log",
        default="runs/paper_lab/m354_spy_cleanup_close_preview.jsonl",
        help="Local M354 SPY close-preview JSONL authorization evidence path.",
    )
    paper_lab_spy_close_submit_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Close-submit output format.",
    )
    paper_lab_spy_close_submit_parser.add_argument(
        "--submit",
        action="store_true",
        help="Request the one-shot M355 SPY paper close submit.",
    )
    paper_lab_spy_close_submit_parser.add_argument(
        "--i-mean-it",
        action="store_true",
        dest="i_mean_it",
        help="Confirm the one-shot M355 SPY paper close submit.",
    )
    _add_paper_lab_run_log_options(paper_lab_spy_close_submit_parser)
    paper_lab_revalidation_brief_parser = subparsers.add_parser(
        "paper-lab-revalidation-brief",
        help="Summarize a local paper-lab snapshot JSONL run log.",
    )
    paper_lab_revalidation_brief_parser.add_argument(
        "--run-log",
        required=True,
        help="Read a deterministic paper-lab observation JSONL run log from PATH.",
    )
    paper_lab_revalidation_brief_parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run/session id to summarize. Defaults to the latest run.",
    )
    paper_lab_revalidation_brief_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Brief output format.",
    )
    etf_sma_paper_preview_parser = subparsers.add_parser(
        "etf-sma-paper-preview-only",
        help="Render a SPY ETF/SMA paper broker-facing preview without submitting.",
    )
    etf_sma_paper_preview_parser.add_argument(
        "--prior-snapshot-run-log",
        required=True,
        help="Read the M348 paper-lab snapshot evidence JSONL from PATH.",
    )
    etf_sma_paper_preview_parser.add_argument(
        "--prior-snapshot-run-id",
        default="m348_etf_sma_fresh_read_only_snapshot",
        help="M348 snapshot run/session id to require.",
    )
    etf_sma_paper_preview_parser.add_argument(
        "--source-scenario",
        choices=("bullish", "defensive", "insufficient-history"),
        default="bullish",
        help="Deterministic local M347 source record scenario.",
    )
    etf_sma_paper_preview_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Preview output format.",
    )
    _add_paper_lab_run_log_options(etf_sma_paper_preview_parser)
    etf_sma_m368_preview_parser = subparsers.add_parser(
        "etf-sma-m368-broker-preview-only",
        help="Render the M368 SPY ETF/SMA paper preview without submitting.",
    )
    etf_sma_m368_preview_parser.add_argument(
        "--m368a-run-log",
        default=(
            "runs/paper_lab/"
            "m368a_offline_spy_etf_sma_next_experiment_review.jsonl"
        ),
        help="Read the M368A offline ready-review JSONL artifact from PATH.",
    )
    etf_sma_m368_preview_parser.add_argument(
        "--m368a-run-id",
        default="m368a_offline_spy_etf_sma_next_experiment_review",
        help="M368A run/session id to require.",
    )
    etf_sma_m368_preview_parser.add_argument(
        "--fresh-snapshot-run-log",
        required=True,
        help="Read the fresh read-only paper snapshot JSONL from PATH.",
    )
    etf_sma_m368_preview_parser.add_argument(
        "--fresh-snapshot-run-id",
        default=None,
        help="Fresh snapshot run/session id to summarize. Defaults to latest.",
    )
    etf_sma_m368_preview_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Preview output format.",
    )
    _add_paper_lab_run_log_options(etf_sma_m368_preview_parser)
    etf_sma_m370_submit_parser = subparsers.add_parser(
        "etf-sma-m370-paper-submit",
        help="Submit the explicitly approved M370 tiny SPY paper buy.",
    )
    etf_sma_m370_submit_parser.add_argument(
        "--source-m369-artifact",
        default=(
            "runs/paper_lab/"
            "m369_tiny_spy_paper_submit_operator_review.jsonl"
        ),
        help="Read the M369 operator-review JSONL artifact from PATH.",
    )
    etf_sma_m370_submit_parser.add_argument(
        "--operator-approval",
        default="",
        help="Exact M370 approval phrase required before any submit.",
    )
    etf_sma_m370_submit_parser.add_argument(
        "--equity-session-status",
        choices=("open", "closed", "unavailable"),
        default="unavailable",
        help="Regular equity session status. Default fails closed.",
    )
    etf_sma_m370_submit_parser.add_argument(
        "--equity-session-source",
        default="",
        help="Source used to verify the regular equity session is open.",
    )
    etf_sma_m370_submit_parser.add_argument(
        "--equity-session-observed-at",
        default="",
        help="Timestamp for the regular equity session status observation.",
    )
    etf_sma_m370_submit_parser.add_argument(
        "--evaluated-at",
        default="",
        help="Explicit timezone-aware ISO-8601 evaluation clock for M370.",
    )
    etf_sma_m370_submit_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Submit output format.",
    )
    _add_paper_lab_run_log_options(etf_sma_m370_submit_parser)
    etf_sma_m370_submit_parser.set_defaults(
        run_log="runs/paper_lab/m370_tiny_spy_paper_submit.jsonl",
        run_id="m370_tiny_spy_paper_submit",
    )
    etf_sma_m375_close_preview_parser = subparsers.add_parser(
        "etf-sma-m375-spy-close-preview",
        help="Preview readiness to close the M370C SPY paper position without mutation.",
    )
    etf_sma_m375_close_preview_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Close-preview output format.",
    )
    _add_paper_lab_run_log_options(etf_sma_m375_close_preview_parser)
    etf_sma_m375_close_preview_parser.set_defaults(
        run_log="runs/paper_lab/m375_spy_position_close_preview.jsonl",
        run_id="m375_spy_position_close_preview",
    )
    paper_close_preview_parser = subparsers.add_parser(
        "paper-close-preview",
        help="Design a local BTCUSD paper close preview from a read-only snapshot log.",
    )
    paper_close_preview_parser.add_argument(
        "--run-log",
        required=True,
        help="Read source paper-lab snapshot JSONL evidence from PATH.",
    )
    paper_close_preview_parser.add_argument(
        "--run-id",
        default=None,
        help="Optional source run/session id. Defaults to the latest run.",
    )
    paper_close_preview_parser.add_argument(
        "--output-run-log",
        default=None,
        help=(
            "Append a deterministic paper_close_preview_designed event to PATH."
        ),
    )
    paper_close_preview_parser.add_argument(
        "--output-run-id",
        default=None,
        help=(
            "Optional run/session id for the appended close-preview event. "
            "Defaults to the selected source run id."
        ),
    )
    paper_close_preview_parser.add_argument("--symbol", required=True)
    paper_close_preview_parser.add_argument("--quantity", required=True)
    paper_close_preview_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Preview output format.",
    )
    paper_order_probe_parser = subparsers.add_parser(
        "paper-order-probe",
        help="Preview a guarded Alpaca paper order request without submitting.",
    )
    paper_order_probe_parser.add_argument(
        "--asset-class",
        choices=_PAPER_ORDER_ASSET_CLASSES,
        default="equity",
        dest="asset_class",
    )
    paper_order_probe_parser.add_argument("--symbol", required=True)
    paper_order_probe_parser.add_argument("--side", required=True)
    paper_order_probe_parser.add_argument("--qty", default=None)
    paper_order_probe_parser.add_argument("--notional", default=None)
    paper_order_probe_parser.add_argument("--max-notional", required=True)
    paper_order_probe_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Probe output format.",
    )
    paper_order_probe_parser.add_argument(
        "--submit",
        action="store_true",
        help=(
            "Request a gated paper submit for submit-enabled paper-lab lanes."
        ),
    )
    paper_order_probe_parser.add_argument(
        "--i-mean-it",
        action="store_true",
        dest="i_mean_it",
        help=(
            "Confirm the gated paper submit request."
        ),
    )
    _add_paper_lab_run_log_options(paper_order_probe_parser)
    paper_close_probe_parser = subparsers.add_parser(
        "paper-close-probe",
        help="Submit one explicitly gated BTCUSD Alpaca paper close order.",
    )
    paper_close_probe_parser.add_argument(
        "--asset-class",
        choices=_PAPER_ORDER_ASSET_CLASSES,
        required=True,
        dest="asset_class",
    )
    paper_close_probe_parser.add_argument("--symbol", required=True)
    paper_close_probe_parser.add_argument("--side", required=True)
    paper_close_probe_parser.add_argument("--quantity", required=True)
    paper_close_probe_parser.add_argument("--max-quantity", required=True)
    paper_close_probe_parser.add_argument(
        "--format",
        choices=_PREVIEW_FORMATS,
        default="text",
        dest="output_format",
        help="Probe output format.",
    )
    paper_close_probe_parser.add_argument(
        "--submit",
        action="store_true",
        help="Request the one-shot gated paper close submit.",
    )
    paper_close_probe_parser.add_argument(
        "--i-mean-it",
        action="store_true",
        dest="i_mean_it",
        help="Confirm the one-shot gated paper close submit.",
    )
    _add_paper_lab_run_log_options(paper_close_probe_parser)
    _add_hidden_option(
        content_bundle_preview_parser,
        "--include-risk-authority",
        action="store_true",
        dest="include_risk_authority",
        help=argparse.SUPPRESS,
    )
    _add_hidden_option(
        content_bundle_preview_parser,
        "--include-research-queue",
        action="store_true",
        dest="include_research_queue",
        help=argparse.SUPPRESS,
    )
    _add_hidden_option(
        content_bundle_preview_parser,
        "--include-sma-research-observation",
        action="store_true",
        dest="include_sma_research_observation",
        help=argparse.SUPPRESS,
    )
    _add_hidden_option(
        content_bundle_preview_parser,
        "--include-sma-research-summary-observation",
        action="store_true",
        dest="include_sma_research_summary_observation",
        help=argparse.SUPPRESS,
    )
    _add_hidden_option(
        content_bundle_preview_parser,
        "--include-research-return-observation",
        action="store_true",
        dest="include_research_return_observation",
        help=argparse.SUPPRESS,
    )
    _add_hidden_option(
        content_bundle_preview_parser,
        "--include-research-return-summary-observation",
        action="store_true",
        dest="include_research_return_summary_observation",
        help=argparse.SUPPRESS,
    )
    _add_hidden_option(
        content_bundle_preview_parser,
        "--include-research-data-source-readiness",
        action="store_true",
        dest="include_research_data_source_readiness",
        help=argparse.SUPPRESS,
    )
    _add_hidden_option(
        content_bundle_preview_parser,
        "--include-research-data-source-readiness-summary",
        action="store_true",
        dest="include_research_data_source_readiness_summary",
        help=argparse.SUPPRESS,
    )
    _add_hidden_option(
        content_bundle_preview_parser,
        "--include-diagnostic-issues",
        action="store_true",
        dest="include_diagnostic_issues",
        help=argparse.SUPPRESS,
    )
    _add_hidden_option(
        content_bundle_preview_parser,
        "--include-advisory-sections",
        action="store_true",
        dest="include_advisory_sections",
        help=argparse.SUPPRESS,
    )
    content_bundle_preview_parser.set_defaults(
        include_risk_authority=False,
        include_research_queue=False,
        include_sma_research_observation=False,
        include_sma_research_summary_observation=False,
        include_research_return_observation=False,
        include_research_return_summary_observation=False,
        include_research_data_source_readiness=False,
        include_research_data_source_readiness_summary=False,
        include_diagnostic_issues=False,
        include_advisory_sections=False,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    argv_items = tuple(sys.argv[1:] if argv is None else argv)
    preview_output_format = _preview_output_format(argv_items)
    if preview_output_format is not None:
        return _run_advisory_operating_brief_preview(preview_output_format)
    content_bundle_preview_options = _content_bundle_preview_options(argv_items)
    if content_bundle_preview_options is not None:
        (
            content_bundle_preview_output_format,
            include_risk_authority,
            include_research_queue,
            include_sma_research_observation,
            include_sma_research_summary_observation,
            include_research_return_observation,
            include_research_return_summary_observation,
            include_research_data_source_readiness,
            include_research_data_source_readiness_summary,
            include_diagnostic_issues,
            include_advisory_sections,
        ) = content_bundle_preview_options
        return _run_advisory_operating_brief_content_bundle_preview(
            content_bundle_preview_output_format,
            include_risk_authority=include_risk_authority,
            include_research_queue=include_research_queue,
            include_sma_research_observation=include_sma_research_observation,
            include_sma_research_summary_observation=(
                include_sma_research_summary_observation
            ),
            include_research_return_observation=include_research_return_observation,
            include_research_return_summary_observation=(
                include_research_return_summary_observation
            ),
            include_research_data_source_readiness=(
                include_research_data_source_readiness
            ),
            include_research_data_source_readiness_summary=(
                include_research_data_source_readiness_summary
            ),
            include_diagnostic_issues=include_diagnostic_issues,
            include_advisory_sections=include_advisory_sections,
        )
    package_preview_output_format = _package_preview_output_format(argv_items)
    if package_preview_output_format is not None:
        return _run_advisory_operating_brief_package_preview(
            package_preview_output_format
        )
    mvp_preview_output_format = _mvp_preview_output_format(argv_items)
    if mvp_preview_output_format is not None:
        return _run_advisory_operating_brief_mvp_preview(
            mvp_preview_output_format
        )

    parser = build_parser()
    args = parser.parse_args(argv_items)

    command = args.command or "config"

    if command == "advisory-operating-brief-preview":
        return _run_advisory_operating_brief_preview(args.output_format)
    if command == "advisory-operating-brief-content-bundle-preview":
        return _run_advisory_operating_brief_content_bundle_preview(
            args.output_format,
            include_risk_authority=args.include_risk_authority,
            include_research_queue=args.include_research_queue,
            include_sma_research_observation=args.include_sma_research_observation,
            include_sma_research_summary_observation=(
                args.include_sma_research_summary_observation
            ),
            include_research_return_observation=(
                args.include_research_return_observation
            ),
            include_research_return_summary_observation=(
                args.include_research_return_summary_observation
            ),
            include_research_data_source_readiness=(
                args.include_research_data_source_readiness
            ),
            include_research_data_source_readiness_summary=(
                args.include_research_data_source_readiness_summary
            ),
            include_diagnostic_issues=args.include_diagnostic_issues,
            include_advisory_sections=args.include_advisory_sections,
        )
    if command == "advisory-operating-brief-package-preview":
        return _run_advisory_operating_brief_package_preview(args.output_format)
    if command == "advisory-operating-brief-mvp-preview":
        return _run_advisory_operating_brief_mvp_preview(args.output_format)
    if command == "paper-lab-revalidation-brief":
        return _run_paper_lab_revalidation_brief(
            args.run_log,
            args.output_format,
            run_id=args.run_id,
        )
    if command == "etf-sma-paper-preview-only":
        return _run_etf_sma_paper_preview_only(args)
    if command == "etf-sma-m368-broker-preview-only":
        return _run_etf_sma_m368_broker_preview_only(args)
    if command == "paper-close-preview":
        return _run_paper_close_preview(
            args.run_log,
            args.symbol,
            args.quantity,
            args.output_format,
            run_id=args.run_id,
            output_run_log=args.output_run_log,
            output_run_id=args.output_run_id,
        )

    config = _load_runtime_config(profile=args.profile)
    log_level = args.log_level or config.log_level
    from .logging_setup import configure_logging, get_logger

    configure_logging(log_level=log_level)

    logger = get_logger(__name__)

    if command == "config":
        logger.info(
            "loaded_config",
            extra={
                "profile": config.profile,
                "data_dir": str(config.data_dir),
                "starting_cash": str(config.starting_cash),
                "paper_exchange": config.paper_exchange,
            },
        )
        return 0

    if command == "demo-core":
        if args.list_scenarios:
            _list_demo_core_scenarios()
            return 0
        return _run_demo_core(args.scenario)
    if command == "paper-account-smoke":
        return _run_paper_account_smoke(
            config,
            args.output_format,
            run_log_path=args.run_log,
            run_id=args.run_id,
        )
    if command == "paper-lab-snapshot":
        return _run_paper_lab_snapshot(
            config,
            args.output_format,
            run_log_path=args.run_log,
            run_id=args.run_id,
        )
    if command == "paper-lab-order-traceability-review":
        return _run_paper_lab_order_traceability_review(config, args)
    if command == "paper-lab-spy-close-preview":
        return _run_paper_lab_spy_close_preview(config, args)
    if command == "paper-lab-spy-close-submit":
        return _run_paper_lab_spy_close_submit(config, args)
    if command == "etf-sma-m370-paper-submit":
        return _run_etf_sma_m370_paper_submit(config, args)
    if command == "etf-sma-m375-spy-close-preview":
        return _run_etf_sma_m375_spy_close_preview(config, args)
    if command == "paper-order-probe":
        return _run_paper_order_probe(config, args)
    if command == "paper-close-probe":
        return _run_paper_close_probe(config, args)

    if hasattr(args, "list_scenarios") and args.list_scenarios:
        _list_demo_core_scenarios()
        return 0

    parser.error(f"unsupported command: {command}")
    return 2


def _list_demo_core_scenarios() -> None:
    from .orchestration.scenarios import SCENARIO_NAMES

    print("Available deterministic core scenarios")
    for scenario_name in SCENARIO_NAMES:
        print(f"- {scenario_name}")


def _run_demo_core(scenario_name: str) -> int:
    from .orchestration.scenarios import SCENARIO_NAMES, run_scenario

    if scenario_name not in SCENARIO_NAMES:
        expected = ", ".join(SCENARIO_NAMES)
        print(
            f"Unknown scenario {scenario_name!r}. Available scenarios: {expected}.",
            file=sys.stderr,
        )
        return 2

    scenario = run_scenario(scenario_name)
    result = scenario.result
    print("Deterministic core demo")
    print(f"scenario: {scenario.name}")
    print(f"signal: {_signal_summary(result)}")
    print(f"risk: {_risk_summary(result)}")
    print(f"execution: {_execution_summary(result)}")
    print(f"fill: {_fill_summary(result)}")

    if result.portfolio is not None:
        print(f"cash_after: {result.portfolio.account.cash}")

    if result.valuation is not None:
        print("valuation: available")
        print(f"portfolio_value: {result.valuation.total_market_value}")
        print(f"unrealized_pnl: {result.valuation.total_unrealized_pnl}")
    else:
        print("valuation: unavailable")
    print(f"final_outcome: {result.status}")
    return 0


def _signal_summary(result) -> str:
    return "generated" if result.order else "none"


def _risk_summary(result) -> str:
    if result.trade_flow is None:
        return "not_checked"
    if result.trade_flow.risk.allowed:
        return "approved"
    return f"rejected ({result.trade_flow.risk.reason})"


def _execution_summary(result) -> str:
    if result.execution is None:
        return "not_run"
    if result.execution.filled:
        return "filled"
    return result.execution.ack.status.value


def _fill_summary(result) -> str:
    if result.execution is None:
        return "not_applicable"
    return "filled" if result.execution.fill is not None else "none"


def _run_paper_account_smoke(
    config,
    output_format: str,
    *,
    run_log_path: str | None = None,
    run_id: str | None = None,
) -> int:
    resolved_run_id = _paper_lab_run_id(run_id) if run_log_path else ""
    if run_log_path and not _ensure_paper_lab_run_log(run_log_path):
        return 1

    profile_gate = _paper_profile_gate(config)
    if not profile_gate["passed"]:
        payload = {
            "account": None,
            "command": "paper-account-smoke",
            "error": "paper_profile_required",
            "gates": {"profile_gate": profile_gate},
            "ok": False,
            "position_count": 0,
            "positions": [],
            "submitted": False,
        }
        if run_log_path and not _write_paper_account_run_log(
            run_log_path,
            resolved_run_id,
            payload,
            config,
        ):
            return 1
        print(_render_paper_account_payload(payload, output_format))
        return 2

    try:
        broker = _build_paper_broker(config.alpaca_paper)
        account = broker.get_account()
        positions = broker.get_positions()
    except Exception as exc:  # pragma: no cover - exercised through fake failures
        payload = {
            "account": None,
            "command": "paper-account-smoke",
            "error": "paper_account_smoke_failed",
            "error_type": exc.__class__.__name__,
            "gates": {"profile_gate": profile_gate},
            "message": _redact_config_secrets(str(exc), config),
            "ok": False,
            "position_count": 0,
            "positions": [],
            "submitted": False,
        }
        if run_log_path and not _write_paper_account_run_log(
            run_log_path,
            resolved_run_id,
            payload,
            config,
        ):
            return 1
        print(_render_paper_account_payload(payload, output_format))
        return 1

    position_rows = [
        {
            "average_price": _decimal_text(position.average_price),
            "quantity": _decimal_text(position.quantity),
            "symbol": position.symbol,
        }
        for position in sorted(positions, key=lambda item: item.symbol)
    ]
    payload = {
        "account": {
            "cash": _decimal_text(account.cash),
            "currency": account.currency,
        },
        "command": "paper-account-smoke",
        "gates": {"profile_gate": profile_gate},
        "ok": True,
        "position_count": len(position_rows),
        "positions": position_rows,
        "redaction": "credentials_redacted",
        "submitted": False,
    }
    if run_log_path and not _write_paper_account_run_log(
        run_log_path,
        resolved_run_id,
        payload,
        config,
    ):
        return 1
    print(_render_paper_account_payload(payload, output_format))
    return 0


def _run_paper_lab_snapshot(
    config,
    output_format: str,
    *,
    run_log_path: str | None = None,
    run_id: str | None = None,
) -> int:
    resolved_run_id = _paper_lab_run_id(run_id) if run_log_path else ""
    if run_log_path and not _ensure_paper_lab_run_log(run_log_path):
        return 1

    payload = _build_paper_lab_snapshot_payload(config)
    if run_log_path and not _write_paper_lab_snapshot_run_log(
        run_log_path,
        resolved_run_id,
        payload,
        config,
    ):
        return 1

    print(_render_paper_lab_snapshot_payload(payload, output_format))
    if payload.get("error") == "profile_gate_failed":
        return 2

    return 0 if payload["ok"] else 1


def _run_paper_lab_order_traceability_review(
    config,
    args: argparse.Namespace,
) -> int:
    run_log_path = args.run_log
    resolved_run_id = _paper_lab_run_id(args.run_id) if run_log_path else ""
    if run_log_path and not _ensure_paper_lab_run_log(run_log_path):
        return 1

    payload = _build_paper_lab_order_traceability_review_payload(
        config,
        symbol=args.symbol,
        source_order_run_log=args.source_order_run_log,
        source_snapshot_run_log=args.source_snapshot_run_log,
    )
    if run_log_path and not _write_paper_lab_order_traceability_review_run_log(
        run_log_path,
        resolved_run_id,
        payload,
        config,
    ):
        return 1

    print(
        _render_paper_lab_order_traceability_review_payload(
            payload,
            args.output_format,
        )
    )
    if payload.get("error") == "profile_gate_failed":
        return 2

    return 0 if payload["ok"] else 1


def _run_paper_lab_spy_close_preview(
    config,
    args: argparse.Namespace,
) -> int:
    run_log_path = args.run_log
    resolved_run_id = _paper_lab_run_id(
        args.run_id or "m354_spy_cleanup_close_preview"
    )
    if run_log_path and not _ensure_paper_lab_run_log(run_log_path):
        return 1

    payload = _build_paper_lab_spy_close_preview_payload(
        config,
        run_id=resolved_run_id,
        symbol=args.symbol,
        source_traceability_run_log=args.source_traceability_run_log,
    )
    if run_log_path and not _write_paper_lab_spy_close_preview_run_log(
        run_log_path,
        resolved_run_id,
        payload,
        config,
    ):
        return 1

    print(_render_paper_lab_spy_close_preview_payload(payload, args.output_format))
    if payload.get("error") == "profile_gate_failed":
        return 2

    return 0 if payload["ok"] else 1


def _run_paper_lab_spy_close_submit(
    config,
    args: argparse.Namespace,
) -> int:
    run_log_path = args.run_log
    resolved_run_id = _paper_lab_run_id(
        args.run_id or "m355_spy_paper_close_submit"
    )
    if run_log_path and not _ensure_paper_lab_run_log(run_log_path):
        return 1

    payload, broker = _build_paper_lab_spy_close_submit_payload(config, args)
    if payload["ok"] and payload["submit_requested"]:
        payload = _submit_paper_lab_spy_close_submit(
            config,
            payload,
            broker=broker,
            observe_post_submit=True,
        )

    if run_log_path and not _write_paper_lab_spy_close_submit_run_log(
        run_log_path,
        resolved_run_id,
        payload,
        config,
    ):
        print(_render_paper_lab_spy_close_submit_payload(payload, args.output_format))
        return 1

    print(_render_paper_lab_spy_close_submit_payload(payload, args.output_format))
    if payload.get("broker_error"):
        return 1

    return 0 if payload["ok"] else 2


def _run_etf_sma_m370_paper_submit(
    config,
    args: argparse.Namespace,
) -> int:
    from .execution.etf_sma_m370_paper_submit import (
        M370EquitySessionStatus,
        render_m370_paper_submit_json,
        render_m370_paper_submit_text,
        run_m370_tiny_spy_paper_submit,
        write_m370_paper_submit_artifact,
    )

    profile_gate = _paper_profile_gate(config)
    halt_gate = _gate(
        _paper_halt_not_set(),
        "halt_not_set",
        "ALGOTRADER_PAPER_HALT=1",
    )
    session_status = M370EquitySessionStatus(
        status=args.equity_session_status,
        source=args.equity_session_source,
        observed_at=args.equity_session_observed_at,
    )
    payload = run_m370_tiny_spy_paper_submit(
        source_m369_artifact_path=args.source_m369_artifact,
        output_artifact_path=args.run_log,
        run_id=args.run_id or "m370_tiny_spy_paper_submit",
        operator_approval=args.operator_approval,
        equity_session_status=session_status,
        paper_profile_gate_passed=profile_gate["passed"] is True,
        paper_profile_gate_detail=str(profile_gate.get("detail", "")),
        halt_gate_passed=halt_gate["passed"] is True,
        halt_gate_detail=str(halt_gate.get("detail", "")),
        evaluated_at=args.evaluated_at,
        broker_factory=lambda: _build_paper_broker(config.alpaca_paper),
        redactor=lambda value: _redact_config_secrets(value, config),
    )
    if args.run_log:
        write_m370_paper_submit_artifact(payload, args.run_log)

    if args.output_format == "json":
        print(render_m370_paper_submit_json(payload))
    else:
        print(render_m370_paper_submit_text(payload))
    if payload.get("broker_error") is True:
        return 1
    return 0 if payload.get("ok") is True else 2


def _run_etf_sma_m375_spy_close_preview(
    config,
    args: argparse.Namespace,
) -> int:
    from .execution.etf_sma_m375_spy_close_preview import (
        M375_DEFAULT_RUN_ID,
        render_m375_spy_close_preview_json,
        render_m375_spy_close_preview_text,
        run_m375_spy_close_preview,
        write_m375_spy_close_preview_artifact,
    )

    profile_gate = _paper_profile_gate(config)
    payload = run_m375_spy_close_preview(
        run_id=args.run_id or M375_DEFAULT_RUN_ID,
        output_artifact_path=args.run_log,
        paper_profile_gate_passed=profile_gate["passed"] is True,
        paper_profile_gate_detail=str(profile_gate.get("detail", "")),
        broker_factory=lambda: _build_paper_broker(config.alpaca_paper),
        redactor=lambda value: _redact_config_secrets(value, config),
    )
    if args.run_log:
        write_m375_spy_close_preview_artifact(payload, args.run_log)

    if args.output_format == "json":
        print(render_m375_spy_close_preview_json(payload))
    else:
        print(render_m375_spy_close_preview_text(payload))
    return 0 if payload.get("ok") is True else 2


def _build_paper_lab_spy_close_submit_payload(
    config,
    args: argparse.Namespace,
) -> tuple[dict[str, object], object | None]:
    profile_gate = _paper_profile_gate(config)
    halt_gate = _gate(
        _paper_halt_not_set(),
        "halt_not_set",
        "ALGOTRADER_PAPER_HALT=1",
    )
    payload = _paper_lab_spy_close_submit_base_payload(
        profile_gate,
        halt_gate,
        run_id=_paper_lab_run_id(args.run_id or "m355_spy_paper_close_submit"),
        m354_run_log=args.m354_run_log,
        submit_flag=bool(args.submit),
        i_mean_it_flag=bool(args.i_mean_it),
    )
    payload = _paper_lab_spy_close_submit_source_payload(payload)
    payload = _finalize_paper_lab_spy_close_submit_contract(payload)
    if not _paper_lab_spy_close_submit_should_observe(payload):
        return payload, None

    payload, broker = _attach_paper_lab_spy_close_submit_pre_submit_observation(
        config,
        payload,
    )
    return _finalize_paper_lab_spy_close_submit_contract(payload), broker


def _paper_lab_spy_close_submit_base_payload(
    profile_gate: dict[str, object],
    halt_gate: dict[str, object],
    *,
    run_id: str,
    m354_run_log: str,
    submit_flag: bool,
    i_mean_it_flag: bool,
) -> dict[str, object]:
    empty_query = _empty_traceability_order_query_payload()
    submit_requested = bool(submit_flag and i_mean_it_flag)
    return {
        "accepted": None,
        "account": None,
        "account_cash": "",
        "account_currency": "",
        "account_observation_available": False,
        "asset_class": "equity",
        "blockers": [],
        "broker_action_performed": False,
        "broker_error": False,
        "broker_normalized_status": "",
        "broker_order_id": "",
        "broker_order_id_available": False,
        "broker_raw_reason": "",
        "broker_raw_status": "",
        "broker_response_parsed": False,
        "broker_response_received": False,
        "broker_result": None,
        "broker_result_classification": "not_submitted",
        "client_order_id": _PAPER_SPY_CLOSE_SUBMIT_CLIENT_ORDER_ID,
        "close_order_submitted": False,
        "command": "paper-lab-spy-close-submit",
        "duplicate_m355_client_order_id_found": False,
        "duplicate_m355_client_order_matches": [],
        "error": "",
        "filled": None,
        "filled_average_price": "",
        "filled_quantity": "",
        "gates": {
            "profile_gate": profile_gate,
            "halt_gate": halt_gate,
        },
        "halt_gate_result": halt_gate,
        "live_authorized": False,
        "m354_artifact_available": False,
        "m354_broker_action_performed": None,
        "m354_close_order_submitted": None,
        "m354_event_type": "",
        "m354_live_authorized": None,
        "m354_mutated": None,
        "m354_ok": False,
        "m354_requested_close_quantity": "",
        "m354_run_id": "",
        "m354_run_log": m354_run_log,
        "m354_state": "",
        "m354_submitted": None,
        "market_session_note": _PAPER_MARKET_SESSION_NOTE,
        "mutated": False,
        "normalized_status": "",
        "order_type": "market",
        "orders_observation_available": False,
        "paper_lab_only": True,
        "paper_only": True,
        "paper_profile_gate_result": profile_gate,
        "position_count": 0,
        "position_symbols": [],
        "positions": [],
        "positions_observation_available": False,
        "post_close_position_present": None,
        "post_close_remaining_quantity": "",
        "post_submit_account": None,
        "post_submit_account_cash": "",
        "post_submit_account_currency": "",
        "post_submit_account_observation_available": False,
        "post_submit_matching_recent_order": None,
        "post_submit_matching_recent_order_found": False,
        "post_submit_position_count": 0,
        "post_submit_position_symbols": [],
        "post_submit_positions": [],
        "post_submit_positions_observation_available": False,
        "post_submit_recent_all_order_count": 0,
        "post_submit_recent_all_order_query": empty_query,
        "post_submit_recent_all_orders": [],
        "post_submit_recent_closed_order_count": 0,
        "post_submit_recent_closed_order_query": empty_query,
        "post_submit_recent_closed_orders": [],
        "post_submit_recent_open_order_count": 0,
        "post_submit_recent_open_order_query": empty_query,
        "post_submit_recent_open_orders": [],
        "post_submit_recent_open_spy_order_count": 0,
        "post_submit_recent_order_query_metadata_complete": False,
        "post_submit_recent_order_query_metadata_missing_fields": [],
        "post_submit_unavailable_observations": [],
        "post_submit_unavailable_reasons": {},
        "pre_submit_recent_all_order_count": 0,
        "pre_submit_recent_all_order_query": empty_query,
        "pre_submit_recent_all_orders": [],
        "pre_submit_recent_closed_order_count": 0,
        "pre_submit_recent_closed_order_query": empty_query,
        "pre_submit_recent_closed_orders": [],
        "pre_submit_recent_open_order_count": 0,
        "pre_submit_recent_open_order_query": empty_query,
        "pre_submit_recent_open_orders": [],
        "pre_submit_recent_order_query_metadata_complete": False,
        "pre_submit_recent_order_query_metadata_missing_fields": [],
        "preview_only": not submit_requested,
        "profit_claim": "none",
        "proposed_order_request": None,
        "raw_reason": "",
        "raw_status": "",
        "recent_open_spy_order_count": 0,
        "redaction": "credentials_redacted",
        "requested_close_quantity": str(_PAPER_SPY_CLOSE_SUBMIT_EXPECTED_QUANTITY),
        "requested_i_mean_it": bool(i_mean_it_flag),
        "requested_submit": bool(submit_flag),
        "run_id": run_id,
        "side": "sell",
        "sizing_mode": "qty",
        "spy_position_observed": False,
        "spy_quantity": "",
        "state": _PAPER_SPY_CLOSE_SUBMIT_BLOCKED_STATE,
        "submitted": False,
        "submit_attempt_count": 0,
        "submit_attempted": False,
        "submit_requested": submit_requested,
        "symbol": "SPY",
        "time_in_force": "day",
        "unavailable_observations": [],
        "unavailable_reasons": {},
        "unexpected_position_symbols": [],
    }


def _paper_lab_spy_close_submit_source_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    records = _load_jsonl_records(str(payload["m354_run_log"]))
    record = _latest_m354_spy_close_preview_record(records)
    if not record:
        return payload

    return {
        **payload,
        "m354_artifact_available": True,
        "m354_broker_action_performed": record.get("broker_action_performed"),
        "m354_close_order_submitted": record.get("close_order_submitted"),
        "m354_event_type": record.get("event_type", ""),
        "m354_live_authorized": record.get("live_authorized"),
        "m354_mutated": record.get("mutated"),
        "m354_ok": record.get("ok") is True,
        "m354_requested_close_quantity": str(
            record.get("requested_close_quantity", "")
        ),
        "m354_run_id": record.get("run_id", ""),
        "m354_state": record.get("state", ""),
        "m354_submitted": record.get("submitted"),
    }


def _latest_m354_spy_close_preview_record(
    records: list[dict[str, object]],
) -> dict[str, object]:
    for record in reversed(records):
        if record.get("event_type") != "paper_lab_spy_close_preview_reviewed":
            continue
        if record.get("command") != "paper-lab-spy-close-preview":
            continue
        if record.get("symbol") == "SPY":
            return dict(record)

    return {}


def _paper_lab_spy_close_submit_should_observe(
    payload: Mapping[str, object],
) -> bool:
    return (
        payload.get("submit_requested") is True
        and _payload_mapping(payload.get("paper_profile_gate_result")).get("passed")
        is True
        and _payload_mapping(payload.get("halt_gate_result")).get("passed") is True
        and payload.get("m354_state") == _PAPER_SPY_CLOSE_SUBMIT_READY_M354_STATE
        and payload.get("m354_ok") is True
        and payload.get("m354_submitted") is False
        and payload.get("m354_mutated") is False
        and payload.get("m354_broker_action_performed") is False
        and payload.get("m354_close_order_submitted") is False
        and payload.get("m354_live_authorized") is False
        and str(payload.get("m354_requested_close_quantity", ""))
        == str(_PAPER_SPY_CLOSE_SUBMIT_EXPECTED_QUANTITY)
    )


def _attach_paper_lab_spy_close_submit_pre_submit_observation(
    config,
    payload: dict[str, object],
) -> tuple[dict[str, object], object | None]:
    from .execution.paper_lab_snapshot import (
        account_observation_payload,
        position_observation_payloads,
        position_symbols,
    )

    unavailable: list[str] = []
    unavailable_reasons: dict[str, object] = {}
    updated = {
        **payload,
        "unavailable_observations": unavailable,
        "unavailable_reasons": unavailable_reasons,
    }
    try:
        broker = _build_paper_broker(config.alpaca_paper)
    except Exception as exc:  # pragma: no cover - fake failure safety path
        redacted_message = _redact_config_secrets(str(exc), config)
        unavailable.extend(["account", "positions", "orders"])
        unavailable_reasons["broker"] = {
            "error_type": exc.__class__.__name__,
            "message": redacted_message,
        }
        return {
            **updated,
            "broker_error": True,
            "message": redacted_message,
        }, None

    try:
        account = account_observation_payload(broker.get_account())
        updated.update(
            {
                "account": account,
                "account_cash": account.get("cash", ""),
                "account_currency": account.get("currency", ""),
                "account_observation_available": True,
            }
        )
    except Exception as exc:  # pragma: no cover - fake failure safety path
        unavailable.append("account")
        unavailable_reasons["account"] = {
            "error_type": exc.__class__.__name__,
            "message": _redact_config_secrets(str(exc), config),
        }

    try:
        positions = position_observation_payloads(broker.get_positions())
        position = _position_for_symbol(list(positions), "SPY")
        updated.update(
            {
                "position_count": len(positions),
                "position_symbols": list(position_symbols(positions)),
                "positions": list(positions),
                "positions_observation_available": True,
                "spy_position_observed": bool(position),
                "spy_quantity": position.get("quantity", ""),
            }
        )
    except Exception as exc:  # pragma: no cover - fake failure safety path
        unavailable.append("positions")
        unavailable_reasons["positions"] = {
            "error_type": exc.__class__.__name__,
            "message": _redact_config_secrets(str(exc), config),
        }

    updated = _observe_spy_close_submit_order_sets(
        updated,
        broker,
        config,
        prefix="pre_submit",
        unavailable=unavailable,
        unavailable_reasons=unavailable_reasons,
    )
    order_sets = _paper_lab_spy_close_submit_order_sets(updated, "pre_submit")
    duplicate_matches = _orders_matching_client_order_id(
        order_sets,
        _PAPER_SPY_CLOSE_SUBMIT_CLIENT_ORDER_ID,
    )
    metadata_missing = _paper_lab_spy_close_submit_query_missing_fields(
        updated,
        "pre_submit",
    )
    return {
        **updated,
        "duplicate_m355_client_order_id_found": bool(duplicate_matches),
        "duplicate_m355_client_order_matches": duplicate_matches,
        "orders_observation_available": (
            _payload_mapping(updated.get("pre_submit_recent_open_order_query")).get(
                "recent_order_query_available"
            )
            is True
            and _payload_mapping(updated.get("pre_submit_recent_all_order_query")).get(
                "recent_order_query_available"
            )
            is True
            and _payload_mapping(
                updated.get("pre_submit_recent_closed_order_query")
            ).get("recent_order_query_available")
            is True
        ),
        "pre_submit_recent_order_query_metadata_complete": not metadata_missing,
        "pre_submit_recent_order_query_metadata_missing_fields": metadata_missing,
        "proposed_order_request": _paper_lab_spy_close_submit_request_payload(),
    }, broker


def _paper_lab_spy_close_submit_request_payload() -> dict[str, str]:
    request = _paper_order_request(
        "SPY",
        asset_class="equity",
        client_order_id=_PAPER_SPY_CLOSE_SUBMIT_CLIENT_ORDER_ID,
        quantity=_PAPER_SPY_CLOSE_SUBMIT_EXPECTED_QUANTITY,
        side="sell",
        time_in_force="day",
    )
    return _paper_order_request_payload(request)


def _observe_spy_close_submit_order_sets(
    payload: dict[str, object],
    broker,
    config,
    *,
    prefix: str,
    unavailable: list[str],
    unavailable_reasons: dict[str, object],
) -> dict[str, object]:
    updated = dict(payload)
    for status_filter, label in (
        ("open", "open"),
        ("all", "all"),
        ("closed", "closed"),
    ):
        updated = _observe_spy_close_submit_orders(
            updated,
            broker,
            config,
            prefix=prefix,
            label=label,
            status_filter=status_filter,
            unavailable=unavailable,
            unavailable_reasons=unavailable_reasons,
        )

    return updated


def _observe_spy_close_submit_orders(
    payload: dict[str, object],
    broker,
    config,
    *,
    prefix: str,
    label: str,
    status_filter: str,
    unavailable: list[str],
    unavailable_reasons: dict[str, object],
) -> dict[str, object]:
    from .execution.alpaca_client import AlpacaRecentOrderQuery
    from .execution.paper_lab_snapshot import (
        order_observation_payloads,
        recent_order_query_payload,
    )

    query = AlpacaRecentOrderQuery(
        status_filter=status_filter,
        symbol_filter="SPY",
    )
    query_key = f"{prefix}_recent_{label}_order_query"
    orders_key = f"{prefix}_recent_{label}_orders"
    count_key = f"{prefix}_recent_{label}_order_count"
    query_payload = {
        **recent_order_query_payload(query),
        "recent_order_query_attempted": True,
        "recent_order_query_available": False,
        "recent_order_query_returned_count": 0,
    }
    try:
        orders = order_observation_payloads(broker.get_recent_orders(query))
    except Exception as exc:  # pragma: no cover - fake failure safety path
        observation_name = f"{prefix}_{label}_orders"
        unavailable.append(observation_name)
        unavailable_reasons[observation_name] = {
            "error_type": exc.__class__.__name__,
            "message": _redact_config_secrets(str(exc), config),
        }
        return {
            **payload,
            query_key: query_payload,
            orders_key: [],
            count_key: 0,
        }

    complete_query_payload = {
        **query_payload,
        "recent_order_query_available": True,
        "recent_order_query_returned_count": len(orders),
    }
    return {
        **payload,
        query_key: complete_query_payload,
        orders_key: list(orders),
        count_key: len(orders),
    }


def _paper_lab_spy_close_submit_order_sets(
    payload: Mapping[str, object],
    prefix: str,
) -> tuple[Mapping[str, object], ...]:
    orders: list[Mapping[str, object]] = []
    for label in ("open", "all", "closed"):
        value = payload.get(f"{prefix}_recent_{label}_orders")
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            continue
        for order in value:
            if isinstance(order, Mapping):
                orders.append(order)

    return tuple(orders)


def _orders_matching_client_order_id(
    orders: Sequence[Mapping[str, object]],
    client_order_id: str,
) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for order in orders:
        if order.get("client_order_id") != client_order_id:
            continue
        identity = (
            str(order.get("order_id", "")),
            str(order.get("client_order_id", "")),
        )
        if identity in seen:
            continue
        seen.add(identity)
        matches.append(dict(order))

    return matches


def _paper_lab_spy_close_submit_query_missing_fields(
    payload: Mapping[str, object],
    prefix: str,
) -> list[str]:
    missing_fields: list[str] = []
    for label in ("open", "all", "closed"):
        query_payload = _payload_mapping(
            payload.get(f"{prefix}_recent_{label}_order_query")
        )
        if query_payload.get("recent_order_query_metadata_complete") is not True:
            missing_fields.append(f"{prefix}_{label}_order_query")
        for field in query_payload.get("recent_order_query_metadata_missing_fields", []):
            missing_fields.append(f"{prefix}_{label}.{field}")

    return missing_fields


def _finalize_paper_lab_spy_close_submit_contract(
    payload: dict[str, object],
) -> dict[str, object]:
    positions = payload.get("positions")
    position = _position_for_symbol(positions if isinstance(positions, list) else [], "SPY")
    observed_quantity = position.get("quantity", "")
    unexpected_position_symbols = tuple(
        str(item)
        for item in payload.get("position_symbols", [])
        if str(item) != "SPY"
    )
    unavailable = tuple(_payload_string_tuple(payload.get("unavailable_observations")))
    metadata_complete = (
        payload.get("pre_submit_recent_order_query_metadata_complete") is True
    )
    recent_open_order_count = (
        _int_payload_value(payload.get("pre_submit_recent_open_order_count"))
        if payload.get("orders_observation_available") is True
        else None
    )
    contract = build_spy_paper_close_submit_contract(
        m354_state=str(payload.get("m354_state", "")),
        m354_ok=payload.get("m354_ok") is True,
        m354_submitted=_payload_bool_or_none(payload.get("m354_submitted")),
        m354_mutated=_payload_bool_or_none(payload.get("m354_mutated")),
        m354_broker_action_performed=_payload_bool_or_none(
            payload.get("m354_broker_action_performed")
        ),
        m354_close_order_submitted=_payload_bool_or_none(
            payload.get("m354_close_order_submitted")
        ),
        m354_live_authorized=_payload_bool_or_none(
            payload.get("m354_live_authorized")
        ),
        m354_requested_close_quantity=payload.get("m354_requested_close_quantity"),
        observed_position_quantity=observed_quantity,
        account_observed=payload.get("account_observation_available") is True,
        positions_observed=payload.get("positions_observation_available") is True,
        orders_observed=payload.get("orders_observation_available") is True,
        recent_order_query_metadata_complete=metadata_complete,
        recent_open_order_count=recent_open_order_count,
        duplicate_client_order_id_found=(
            payload.get("duplicate_m355_client_order_id_found") is True
        ),
        profile_gate_passed=_payload_mapping(
            payload.get("paper_profile_gate_result")
        ).get("passed") is True,
        halt_not_set=_payload_mapping(payload.get("halt_gate_result")).get("passed")
        is True,
        submit_flag=payload.get("requested_submit") is True,
        i_mean_it_flag=payload.get("requested_i_mean_it") is True,
        unexpected_position_symbols=unexpected_position_symbols,
        unavailable_observations=unavailable,
    )
    contract_payload = contract.to_payload()
    gates = _payload_mapping(contract_payload.get("gates"))
    gates = {
        **gates,
        "profile_gate": payload["paper_profile_gate_result"],
        "halt_gate": payload["halt_gate_result"],
    }
    ready = all(_payload_mapping(gate).get("passed") is True for gate in gates.values())
    request_payload = (
        _paper_lab_spy_close_submit_request_payload()
        if _paper_lab_spy_close_submit_request_shape_available(payload)
        else payload.get("proposed_order_request")
    )
    return {
        **payload,
        **contract_payload,
        "blockers": _paper_lab_spy_close_submit_blockers(gates),
        "close_order_submitted": False,
        "error": "" if ready else _first_failed_spy_close_submit_gate(gates),
        "gates": gates,
        "live_authorized": False,
        "mutated": False,
        "observed_spy_quantity": observed_quantity,
        "ok": ready,
        "orders_observation_available": (
            payload.get("orders_observation_available") is True
        ),
        "paper_profile_gate_result": gates["profile_gate"],
        "preview_only": not ready,
        "proposed_order_request": request_payload,
        "recent_open_spy_order_count": (
            recent_open_order_count if recent_open_order_count is not None else 0
        ),
        "requested_close_quantity": str(_PAPER_SPY_CLOSE_SUBMIT_EXPECTED_QUANTITY),
        "state": (
            _PAPER_SPY_CLOSE_SUBMIT_READY_STATE
            if ready
            else _PAPER_SPY_CLOSE_SUBMIT_BLOCKED_STATE
        ),
        "submitted": False,
        "unexpected_position_symbols": list(unexpected_position_symbols),
    }


def _paper_lab_spy_close_submit_request_shape_available(
    payload: Mapping[str, object],
) -> bool:
    return (
        payload.get("m354_state") == _PAPER_SPY_CLOSE_SUBMIT_READY_M354_STATE
        and str(payload.get("m354_requested_close_quantity", ""))
        == str(_PAPER_SPY_CLOSE_SUBMIT_EXPECTED_QUANTITY)
    )


def _paper_lab_spy_close_submit_blockers(
    gates: Mapping[str, object],
) -> list[str]:
    blockers: list[str] = []
    for gate_name in _PAPER_SPY_CLOSE_SUBMIT_GATE_ORDER:
        gate_payload = _payload_mapping(gates.get(gate_name))
        if gate_payload.get("passed") is True:
            continue
        detail = str(gate_payload.get("detail", ""))
        blockers.append(f"{gate_name}_failed:{detail}")

    return blockers


def _first_failed_spy_close_submit_gate(
    gates: Mapping[str, object],
) -> str:
    for gate_name in _PAPER_SPY_CLOSE_SUBMIT_GATE_ORDER:
        gate = _payload_mapping(gates.get(gate_name))
        if gate.get("passed") is not True:
            return f"{gate_name}_failed"

    return ""


def _submit_paper_lab_spy_close_submit(
    config,
    payload: dict[str, object],
    *,
    broker,
    observe_post_submit: bool,
) -> dict[str, object]:
    request_payload = payload.get("proposed_order_request")
    if broker is None or not isinstance(request_payload, Mapping):
        return {
            **payload,
            "broker_error": True,
            "broker_result_classification": "ambiguous",
            "error": "paper_lab_spy_close_submit_failed",
            "message": "missing_spy_close_order_request",
            "ok": False,
            "preview_only": False,
            "submitted": False,
        }

    try:
        request = _paper_order_request(
            "SPY",
            asset_class="equity",
            client_order_id=_PAPER_SPY_CLOSE_SUBMIT_CLIENT_ORDER_ID,
            quantity=Decimal(str(request_payload["qty"])),
            side="sell",
            time_in_force="day",
        )
        from .risk.state import RiskVerdict
    except Exception as exc:
        redacted_message = _redact_config_secrets(str(exc), config)
        return {
            **payload,
            "broker_error": True,
            "broker_result_classification": "ambiguous",
            "error": "paper_lab_spy_close_submit_failed",
            "error_type": exc.__class__.__name__,
            "message": redacted_message,
            "ok": False,
            "preview_only": False,
            "redacted_exception_message": redacted_message,
            "submitted": False,
            "submit_attempt_count": 0,
            "submit_attempted": False,
        }

    submit_attempt_fields = {
        "broker_action_performed": True,
        "close_order_submitted": True,
        "mutated": True,
        "preview_only": False,
        "submitted": True,
        "submit_attempt_count": 1,
        "submit_attempted": True,
    }
    try:
        result = broker.submit_order_request(
            request,
            risk_verdict=RiskVerdict(
                allowed=True,
                reason="explicit_spy_paper_close_submit_m355",
                detail="quantity_close",
            ),
        )
    except Exception as exc:
        redacted_message = _redact_config_secrets(str(exc), config)
        from .execution.alpaca_translator import AlpacaTranslationError

        response_received = isinstance(exc, AlpacaTranslationError)
        ambiguous_payload = {
            **payload,
            **submit_attempt_fields,
            "accepted": None,
            "broker_error": True,
            "broker_response_parsed": False,
            "broker_response_received": response_received,
            "broker_result_classification": "ambiguous",
            "error": (
                "broker_response_parse_failed"
                if response_received
                else "paper_lab_spy_close_submit_failed"
            ),
            "error_type": exc.__class__.__name__,
            "filled": None,
            "message": redacted_message,
            "ok": False,
            "redacted_exception_message": redacted_message,
            "state": "ambiguous_after_single_submit_stop_no_retry",
            **_paper_submit_error_diagnostic_fields(exc),
        }
        return (
            _attach_paper_lab_spy_close_submit_post_submit_observation(
                ambiguous_payload,
                broker,
                config,
            )
            if observe_post_submit
            else ambiguous_payload
        )

    broker_result = _paper_order_broker_result_payload(result)
    receipt_metadata = _paper_order_broker_receipt_metadata_payload(result)
    accepted = bool(result.accepted)
    submitted_payload = {
        **payload,
        **submit_attempt_fields,
        "accepted": accepted,
        "broker_error": False,
        "broker_normalized_status": broker_result["normalized_status"],
        "broker_order_id": receipt_metadata["order_id"],
        "broker_order_id_available": bool(receipt_metadata["order_id"]),
        "broker_raw_reason": broker_result["raw_reason"],
        "broker_raw_status": broker_result["raw_status"],
        "broker_response_parsed": True,
        "broker_response_received": True,
        "broker_result": broker_result,
        "broker_result_classification": "accepted" if accepted else "rejected",
        "client_order_id": (
            receipt_metadata["client_order_id"]
            or _PAPER_SPY_CLOSE_SUBMIT_CLIENT_ORDER_ID
        ),
        "error": "" if accepted else "paper_lab_spy_close_submit_rejected",
        "filled": result.filled,
        "filled_average_price": receipt_metadata["filled_average_price"],
        "filled_quantity": receipt_metadata["filled_quantity"],
        "normalized_status": broker_result["normalized_status"],
        "ok": accepted,
        "raw_reason": broker_result["raw_reason"],
        "raw_status": broker_result["raw_status"],
        "state": (
            "close_submit_accepted_pending_reconciliation"
            if accepted
            else "close_submit_rejected_no_retry"
        ),
    }
    if observe_post_submit:
        submitted_payload = _attach_paper_lab_spy_close_submit_post_submit_observation(
            submitted_payload,
            broker,
            config,
        )

    return _finalize_paper_lab_spy_close_submit_post_state(submitted_payload)


def _attach_paper_lab_spy_close_submit_post_submit_observation(
    payload: dict[str, object],
    broker,
    config,
) -> dict[str, object]:
    from .execution.paper_lab_snapshot import (
        account_observation_payload,
        position_observation_payloads,
        position_symbols,
    )

    unavailable: list[str] = []
    unavailable_reasons: dict[str, object] = {}
    updated = {
        **payload,
        "post_submit_unavailable_observations": unavailable,
        "post_submit_unavailable_reasons": unavailable_reasons,
    }
    try:
        account = account_observation_payload(broker.get_account())
        updated.update(
            {
                "post_submit_account": account,
                "post_submit_account_cash": account.get("cash", ""),
                "post_submit_account_currency": account.get("currency", ""),
                "post_submit_account_observation_available": True,
            }
        )
    except Exception as exc:  # pragma: no cover - fake failure safety path
        unavailable.append("post_submit_account")
        unavailable_reasons["post_submit_account"] = {
            "error_type": exc.__class__.__name__,
            "message": _redact_config_secrets(str(exc), config),
        }

    try:
        positions = position_observation_payloads(broker.get_positions())
        position = _position_for_symbol(list(positions), "SPY")
        remaining_quantity = position.get("quantity", "0") if position else "0"
        remaining_decimal = _optional_decimal_value(remaining_quantity)
        updated.update(
            {
                "post_close_position_present": bool(position)
                and remaining_decimal not in (None, Decimal("0")),
                "post_close_remaining_quantity": remaining_quantity,
                "post_submit_position_count": len(positions),
                "post_submit_position_symbols": list(position_symbols(positions)),
                "post_submit_positions": list(positions),
                "post_submit_positions_observation_available": True,
            }
        )
    except Exception as exc:  # pragma: no cover - fake failure safety path
        unavailable.append("post_submit_positions")
        unavailable_reasons["post_submit_positions"] = {
            "error_type": exc.__class__.__name__,
            "message": _redact_config_secrets(str(exc), config),
        }

    updated = _observe_spy_close_submit_order_sets(
        updated,
        broker,
        config,
        prefix="post_submit",
        unavailable=unavailable,
        unavailable_reasons=unavailable_reasons,
    )
    metadata_missing = _paper_lab_spy_close_submit_query_missing_fields(
        updated,
        "post_submit",
    )
    order_sets = _paper_lab_spy_close_submit_order_sets(updated, "post_submit")
    matches = _orders_matching_client_order_id(
        order_sets,
        _PAPER_SPY_CLOSE_SUBMIT_CLIENT_ORDER_ID,
    )
    matching_order = matches[0] if matches else None
    return {
        **updated,
        "post_submit_matching_recent_order": matching_order,
        "post_submit_matching_recent_order_found": matching_order is not None,
        "post_submit_recent_order_query_metadata_complete": not metadata_missing,
        "post_submit_recent_order_query_metadata_missing_fields": metadata_missing,
        "post_submit_recent_open_spy_order_count": _int_payload_value(
            updated.get("post_submit_recent_open_order_count")
        ),
    }


def _finalize_paper_lab_spy_close_submit_post_state(
    payload: dict[str, object],
) -> dict[str, object]:
    if payload.get("broker_result_classification") == "ambiguous":
        return {
            **payload,
            "ok": False,
            "state": "ambiguous_after_single_submit_stop_no_retry",
        }
    if payload.get("accepted") is not True:
        return {
            **payload,
            "ok": False,
            "state": "close_submit_rejected_no_retry",
        }

    remaining_quantity = _optional_decimal_value(
        payload.get("post_close_remaining_quantity")
    )
    position_closed = (
        payload.get("post_close_position_present") is False
        or remaining_quantity == Decimal("0")
    )
    if payload.get("filled") is True and position_closed:
        return {
            **payload,
            "ok": True,
            "state": "close_fill_observed_position_closed",
        }

    return {
        **payload,
        "ok": True,
        "state": "close_submit_accepted_pending_reconciliation",
    }


def _run_paper_lab_revalidation_brief(
    run_log_path: str,
    output_format: str,
    *,
    run_id: str | None = None,
) -> int:
    from .execution.paper_lab_revalidation_brief import (
        build_paper_lab_revalidation_brief,
        render_paper_lab_revalidation_brief_text,
    )

    payload = build_paper_lab_revalidation_brief(run_log_path, run_id=run_id)
    if output_format == "json":
        print(_compact_json(payload))
    else:
        print(render_paper_lab_revalidation_brief_text(payload))

    return 0 if payload["usable_for_manual_review"] else 1


def _run_etf_sma_paper_preview_only(args: argparse.Namespace) -> int:
    from .execution.paper_lab_revalidation_brief import (
        build_paper_lab_revalidation_brief,
    )
    from .orchestration.etf_sma_paper_broker_preview import (
        EtfSmaPaperBrokerPreviewConfig,
        EtfSmaPaperBrokerPreviewWriteConfig,
        build_etf_sma_paper_broker_preview,
        render_etf_sma_paper_broker_preview_json,
        render_etf_sma_paper_broker_preview_text,
        write_etf_sma_paper_broker_preview,
    )

    resolved_run_id = _etf_sma_paper_preview_run_id(args.run_id)
    config = _load_runtime_config(profile=args.profile)
    if config.profile != "paper":
        payload = _etf_sma_paper_preview_profile_block_payload(resolved_run_id)
        print(
            _compact_json(payload)
            if args.output_format == "json"
            else _render_etf_sma_paper_preview_profile_block_text(payload)
        )
        return 2

    revalidation_payload = build_paper_lab_revalidation_brief(
        args.prior_snapshot_run_log,
        run_id=args.prior_snapshot_run_id,
    )
    source_record = _build_etf_sma_paper_preview_source_record(
        args.source_scenario
    )
    prior_snapshot = _etf_sma_snapshot_evidence_from_revalidation(
        revalidation_payload
    )
    preview = build_etf_sma_paper_broker_preview(
        source_record,
        prior_snapshot,
        EtfSmaPaperBrokerPreviewConfig(
            run_id=resolved_run_id,
            source_record_id=(
                "m347_etf_sma_preview_jsonl_record:"
                f"{args.source_scenario}"
            ),
        ),
    )

    if args.run_log:
        write_etf_sma_paper_broker_preview(
            preview,
            EtfSmaPaperBrokerPreviewWriteConfig(
                output_path=args.run_log,
                append=False,
                create_parent_dirs=True,
            ),
        )

    if args.output_format == "json":
        print(render_etf_sma_paper_broker_preview_json(preview))
    else:
        print(render_etf_sma_paper_broker_preview_text(preview))

    return 2 if preview.blocked else 0


def _build_etf_sma_paper_preview_source_record(source_scenario: str):
    from datetime import datetime, timedelta, timezone

    from .core.types import Bar
    from .orchestration.etf_sma_execution_preview_bridge import (
        EtfSmaExecutionPreviewConfig,
        build_etf_sma_execution_preview,
    )
    from .orchestration.etf_sma_preview_jsonl_artifact import (
        build_etf_sma_preview_jsonl_record,
    )
    from .signals.etf_sma_evaluator import (
        EtfSmaSignalConfig,
        evaluate_etf_sma_signal,
    )

    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    as_of = start + timedelta(days=199)
    closes_by_scenario = {
        "bullish": 150 * ("10",) + 50 * ("20",),
        "defensive": 200 * ("10",),
        "insufficient-history": 149 * ("10",) + 50 * ("20",),
    }
    closes = closes_by_scenario[source_scenario]
    bars = tuple(
        Bar(
            symbol="SPY",
            timestamp=start + timedelta(days=index),
            open=Decimal(close),
            high=Decimal(close),
            low=Decimal(close),
            close=Decimal(close),
            volume=Decimal("100"),
        )
        for index, close in enumerate(closes)
    )
    signal = evaluate_etf_sma_signal(
        bars,
        EtfSmaSignalConfig(as_of=as_of),
    )
    preview = build_etf_sma_execution_preview(
        signal,
        EtfSmaExecutionPreviewConfig(as_of=as_of),
    )
    return build_etf_sma_preview_jsonl_record(preview)


def _etf_sma_snapshot_evidence_from_revalidation(payload: Mapping[str, object]):
    from .orchestration.etf_sma_paper_broker_preview import (
        EtfSmaPaperSnapshotEvidence,
    )

    checklist = _payload_mapping(payload.get("fresh_snapshot_operator_checklist"))
    evidence = _payload_mapping(checklist.get("evidence"))
    positions = _payload_mapping(payload.get("positions"))
    recent_orders = _payload_mapping(payload.get("recent_orders"))
    return EtfSmaPaperSnapshotEvidence(
        prior_snapshot_run_id=str(payload.get("selected_run_id", "")),
        prior_snapshot_revalidation_state=str(payload.get("state", "")),
        fresh_snapshot_status=str(checklist.get("status", "")),
        usable_for_manual_review=payload.get("usable_for_manual_review") is True,
        snapshot_records_observed=evidence.get("snapshot_records_observed") is True,
        account_observation_available=(
            evidence.get("account_observation_available") is True
        ),
        positions_observation_available=(
            evidence.get("positions_observation_available") is True
        ),
        orders_observation_available=(
            evidence.get("orders_observation_available") is True
        ),
        position_count=_int_payload_value(positions.get("position_count")),
        position_symbols=_payload_string_tuple(positions.get("symbols")),
        recent_open_order_count=_int_payload_value(recent_orders.get("count")),
        recent_order_query_metadata_complete=(
            evidence.get("recent_order_query_metadata_complete") is True
        ),
        unavailable_observations=_payload_string_tuple(
            evidence.get("unavailable_observations")
        ),
        submitted=evidence.get("submitted") is True,
        mutated=evidence.get("mutated") is True,
        credentials_redacted_present=(
            evidence.get("credentials_redacted_present") is True
        ),
        live_profile_evidence=evidence.get("live_profile_evidence") is True,
        credential_leak_evidence=evidence.get("credential_leak_evidence") is True,
    )


def _etf_sma_paper_preview_run_id(run_id: str | None) -> str:
    return _paper_lab_run_id(run_id) if run_id else "m349_etf_sma_paper_preview_only"


def _etf_sma_paper_preview_profile_block_payload(
    run_id: str,
) -> dict[str, object]:
    return {
        "preview_version": "etf_sma_paper_broker_preview_v1",
        "record_type": "etf_sma_paper_broker_preview",
        "run_id": run_id,
        "preview_status": "blocked_before_broker_facing_preview",
        "blocked": True,
        "block_reason": "paper_profile_required",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_preview_performed": False,
        "local_payload_preview_performed": False,
        "next_action": "m350_operator_review_before_any_tiny_spy_paper_probe",
    }


def _render_etf_sma_paper_preview_profile_block_text(
    payload: Mapping[str, object],
) -> str:
    return "\n".join(
        (
            "ETF/SMA paper broker-facing preview",
            f"run_id: {payload.get('run_id', '')}",
            f"preview_status: {payload.get('preview_status', '')}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
            "broker_preview_performed: "
            f"{_bool_text(payload.get('broker_preview_performed'))}",
            "local_payload_preview_performed: "
            f"{_bool_text(payload.get('local_payload_preview_performed'))}",
            f"block_reason: {payload.get('block_reason', '')}",
            f"next_action: {payload.get('next_action', '')}",
        )
    )


def _run_etf_sma_m368_broker_preview_only(args: argparse.Namespace) -> int:
    from .errors import ValidationError
    from .execution.paper_lab_revalidation_brief import (
        build_paper_lab_revalidation_brief,
    )
    from .execution.etf_sma_paper_preview import (
        EtfSmaM368PaperPreviewConfig,
        EtfSmaM368PaperPreviewWriteConfig,
        build_etf_sma_m368_paper_preview,
        load_m368a_review_artifact_record,
        render_etf_sma_m368_paper_preview_json,
        render_etf_sma_m368_paper_preview_text,
        write_etf_sma_m368_paper_preview,
    )

    resolved_run_id = _etf_sma_m368_paper_preview_run_id(args.run_id)
    config = _load_runtime_config(profile=args.profile)
    if config.profile != "paper":
        payload = _etf_sma_m368_paper_preview_profile_block_payload(
            resolved_run_id,
            args.m368a_run_log,
        )
        print(
            _compact_json(payload)
            if args.output_format == "json"
            else _render_etf_sma_m368_paper_preview_block_text(payload)
        )
        return 2

    try:
        m368a_record = load_m368a_review_artifact_record(
            args.m368a_run_log,
            run_id=args.m368a_run_id,
        )
    except ValidationError as exc:
        payload = _etf_sma_m368_paper_preview_load_block_payload(
            resolved_run_id,
            args.m368a_run_log,
            str(exc),
        )
        print(
            _compact_json(payload)
            if args.output_format == "json"
            else _render_etf_sma_m368_paper_preview_block_text(payload)
        )
        return 2

    revalidation_payload = build_paper_lab_revalidation_brief(
        args.fresh_snapshot_run_log,
        run_id=args.fresh_snapshot_run_id,
    )
    fresh_snapshot = _etf_sma_m368_snapshot_summary_from_revalidation(
        revalidation_payload
    )
    preview = build_etf_sma_m368_paper_preview(
        m368a_record,
        fresh_snapshot,
        EtfSmaM368PaperPreviewConfig(
            run_id=resolved_run_id,
            source_m368a_artifact_path=args.m368a_run_log,
        ),
    )

    if args.run_log:
        write_etf_sma_m368_paper_preview(
            preview,
            EtfSmaM368PaperPreviewWriteConfig(
                output_path=args.run_log,
                append=False,
                create_parent_dirs=True,
            ),
        )

    if args.output_format == "json":
        print(render_etf_sma_m368_paper_preview_json(preview))
    else:
        print(render_etf_sma_m368_paper_preview_text(preview))

    return 0 if preview.decision == "ready_for_operator_review_before_tiny_spy_paper_submit" else 2


def _etf_sma_m368_snapshot_summary_from_revalidation(
    payload: Mapping[str, object],
):
    from .execution.etf_sma_paper_preview import (
        EtfSmaM368PaperSnapshotSummary,
    )

    checklist = _payload_mapping(payload.get("fresh_snapshot_operator_checklist"))
    evidence = _payload_mapping(checklist.get("evidence"))
    account = _payload_mapping(payload.get("account"))
    positions = _payload_mapping(payload.get("positions"))
    recent_orders = _payload_mapping(payload.get("recent_orders"))
    return EtfSmaM368PaperSnapshotSummary(
        snapshot_source="fresh_read_only_paper_snapshot_run_log",
        snapshot_evidence_id=str(payload.get("selected_run_id", "")),
        fresh_snapshot_status=str(checklist.get("status", "")),
        account_observation_available=(
            evidence.get("account_observation_available") is True
        ),
        positions_observation_available=(
            evidence.get("positions_observation_available") is True
        ),
        orders_observation_available=(
            evidence.get("orders_observation_available") is True
        ),
        cash=_optional_decimal_value(account.get("cash")),
        currency=str(account.get("currency")) if account.get("currency") else None,
        position_count=_int_payload_value(positions.get("position_count")),
        position_symbols=_payload_string_tuple(positions.get("symbols")),
        open_order_count=_int_payload_value(recent_orders.get("count")),
        recent_order_query_metadata_complete=(
            evidence.get("recent_order_query_metadata_complete") is True
        ),
        unavailable_observations=_payload_string_tuple(
            evidence.get("unavailable_observations")
        ),
        submitted=evidence.get("submitted") is True,
        mutated=evidence.get("mutated") is True,
    )


def _etf_sma_m368_paper_preview_run_id(run_id: str | None) -> str:
    return _paper_lab_run_id(run_id) if run_id else "m368_spy_etf_sma_broker_preview_only"


def _etf_sma_m368_paper_preview_profile_block_payload(
    run_id: str,
    source_path: str,
) -> dict[str, object]:
    return {
        "preview_version": "etf_sma_m368_paper_broker_preview_v1",
        "record_type": "etf_sma_m368_paper_broker_preview",
        "command": "etf-sma-m368-broker-preview-only",
        "run_id": run_id,
        "source_m368a_artifact_path": source_path,
        "decision": "blocked_before_operator_review_for_tiny_spy_paper_submit",
        "reason": "paper_profile_required",
        "blockers": ["paper_profile_required"],
        "required_next_milestone": (
            "M369 - Explicit operator review for tiny SPY paper submit"
        ),
        "submit_authorized": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_preview_performed": False,
        "local_payload_preview_performed": False,
    }


def _etf_sma_m368_paper_preview_load_block_payload(
    run_id: str,
    source_path: str,
    reason: str,
) -> dict[str, object]:
    return {
        **_etf_sma_m368_paper_preview_profile_block_payload(run_id, source_path),
        "reason": reason,
        "blockers": ["m368a_artifact_load_failed"],
    }


def _render_etf_sma_m368_paper_preview_block_text(
    payload: Mapping[str, object],
) -> str:
    return "\n".join(
        (
            "M368 SPY ETF/SMA paper broker-facing preview",
            f"run_id: {payload.get('run_id', '')}",
            f"source_m368a_artifact_path: {payload.get('source_m368a_artifact_path', '')}",
            f"decision: {payload.get('decision', '')}",
            f"reason: {payload.get('reason', '')}",
            f"blockers: {','.join(_payload_string_tuple(payload.get('blockers'))) or 'none'}",
            f"submit_authorized: {_bool_text(payload.get('submit_authorized'))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
            "broker_preview_performed: "
            f"{_bool_text(payload.get('broker_preview_performed'))}",
            f"required_next_milestone: {payload.get('required_next_milestone', '')}",
        )
    )


def _run_paper_close_preview(
    run_log_path: str,
    symbol: str,
    quantity: str,
    output_format: str,
    *,
    run_id: str | None = None,
    output_run_log: str | None = None,
    output_run_id: str | None = None,
) -> int:
    from .execution.paper_lab_revalidation_brief import (
        build_paper_lab_revalidation_brief,
    )

    revalidation_payload = build_paper_lab_revalidation_brief(
        run_log_path,
        run_id=run_id,
    )
    payload = _build_paper_close_preview_payload(
        revalidation_payload,
        symbol=symbol,
        quantity=quantity,
        source_run_log=run_log_path,
    )
    if output_run_log:
        resolved_output_run_id = _paper_lab_run_id(
            output_run_id
            or str(payload.get("source_selected_run_id", "")).strip()
            or None
        )
        payload["output_run_log"] = output_run_log
        payload["output_run_id"] = resolved_output_run_id
        if not _write_paper_close_preview_run_log(
            output_run_log,
            resolved_output_run_id,
            payload,
        ):
            return 1

    print(_render_paper_close_preview_payload(payload, output_format))
    return 0 if payload["ok"] else 2


def _build_paper_close_preview_payload(
    revalidation_payload: Mapping[str, object],
    *,
    symbol: str,
    quantity: str,
    source_run_log: str,
) -> dict[str, object]:
    checklist = _payload_mapping(
        revalidation_payload.get("fresh_snapshot_operator_checklist")
    )
    evidence = _payload_mapping(checklist.get("evidence"))
    contract = build_btcusd_paper_close_preview_contract(
        observed_position_quantity=evidence.get("btcusd_position_quantity"),
        requested_close_quantity=quantity,
        fresh_snapshot_status=str(checklist.get("status", "")),
        recent_order_query_metadata_complete=(
            evidence.get("recent_order_query_metadata_complete") is True
        ),
        source_mutated=_payload_bool_or_none(evidence.get("mutated")),
        source_submitted=_payload_bool_or_none(evidence.get("submitted")),
        symbol=symbol,
    )
    payload = contract.to_payload()
    payload.update(
        {
            "source_command": "paper-lab-revalidation-brief",
            "source_record_count": revalidation_payload.get("record_count", 0),
            "source_run_log": source_run_log,
            "source_selected_run_id": revalidation_payload.get(
                "selected_run_id",
                "",
            ),
            "source_state": revalidation_payload.get("state", ""),
        }
    )
    return payload


def _build_paper_lab_snapshot_payload(config) -> dict[str, object]:
    profile_gate = _paper_profile_gate(config)
    payload = _paper_lab_snapshot_base_payload(profile_gate)
    if not profile_gate["passed"]:
        return {
            **payload,
            "error": "profile_gate_failed",
            "unavailable_observations": [
                "account",
                "positions",
                "orders",
            ],
        }

    try:
        broker = _build_paper_broker(config.alpaca_paper)
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _paper_lab_snapshot_unavailable_payload(
            payload,
            "broker",
            exc,
            config,
        )

    payload = _observe_paper_lab_snapshot_account(payload, broker, config)
    payload = _observe_paper_lab_snapshot_positions(payload, broker, config)
    payload = _observe_paper_lab_snapshot_orders(payload, broker, config)
    ok = (
        payload["account_observation_available"]
        and payload["positions_observation_available"]
        and payload["orders_observation_available"]
    )
    return {
        **payload,
        "error": "" if ok else "paper_lab_snapshot_unavailable",
        "ok": ok,
    }


def _paper_lab_snapshot_base_payload(
    profile_gate: dict[str, object],
) -> dict[str, object]:
    from .execution.paper_lab_snapshot import empty_recent_order_query_payload

    return {
        "account": None,
        "account_observation_available": False,
        "command": "paper-lab-snapshot",
        "error": "",
        "gates": {"profile_gate": profile_gate},
        "mutated": False,
        "ok": False,
        "orders_observation_available": False,
        "position_count": 0,
        "position_symbols": [],
        "positions": [],
        "positions_observation_available": False,
        "recent_order_count": 0,
        "recent_order_query_attempted": False,
        "recent_order_query_available": False,
        "recent_order_query_returned_count": 0,
        **empty_recent_order_query_payload(),
        "recent_orders": [],
        "redaction": "credentials_redacted",
        "submitted": False,
        "unavailable_observations": [],
        "unavailable_reasons": {},
    }


def _observe_paper_lab_snapshot_account(
    payload: dict[str, object],
    broker,
    config,
) -> dict[str, object]:
    from .execution.paper_lab_snapshot import account_observation_payload

    try:
        account = broker.get_account()
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _paper_lab_snapshot_unavailable_payload(
            payload,
            "account",
            exc,
            config,
        )

    return {
        **payload,
        "account": account_observation_payload(account),
        "account_observation_available": True,
    }


def _observe_paper_lab_snapshot_positions(
    payload: dict[str, object],
    broker,
    config,
) -> dict[str, object]:
    from .execution.paper_lab_snapshot import (
        position_observation_payloads,
        position_symbols,
    )

    try:
        positions = position_observation_payloads(broker.get_positions())
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _paper_lab_snapshot_unavailable_payload(
            payload,
            "positions",
            exc,
            config,
        )

    return {
        **payload,
        "position_count": len(positions),
        "position_symbols": list(position_symbols(positions)),
        "positions": list(positions),
        "positions_observation_available": True,
    }


def _observe_paper_lab_snapshot_orders(
    payload: dict[str, object],
    broker,
    config,
) -> dict[str, object]:
    from .execution.alpaca_client import AlpacaRecentOrderQuery
    from .execution.paper_lab_snapshot import (
        order_observation_payloads,
        recent_order_query_payload,
    )

    query = AlpacaRecentOrderQuery()
    query_payload = {
        **payload,
        **recent_order_query_payload(query),
        "recent_order_query_attempted": True,
        "recent_order_query_available": False,
        "recent_order_query_returned_count": 0,
    }
    try:
        orders = order_observation_payloads(broker.get_recent_orders())
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _paper_lab_snapshot_unavailable_payload(
            query_payload,
            "orders",
            exc,
            config,
        )

    return {
        **query_payload,
        "orders_observation_available": True,
        "recent_order_query_available": True,
        "recent_order_query_returned_count": len(orders),
        "recent_order_count": len(orders),
        "recent_orders": list(orders),
    }


def _paper_lab_snapshot_unavailable_payload(
    payload: dict[str, object],
    observation_name: str,
    exc: Exception,
    config,
) -> dict[str, object]:
    unavailable_observations = list(payload.get("unavailable_observations", []))
    if observation_name not in unavailable_observations:
        unavailable_observations.append(observation_name)

    unavailable_reasons = dict(payload.get("unavailable_reasons", {}))
    unavailable_reasons[observation_name] = {
        "error_type": exc.__class__.__name__,
        "message": _redact_config_secrets(str(exc), config),
    }
    return {
        **payload,
        "error": "paper_lab_snapshot_unavailable",
        "ok": False,
        "unavailable_observations": unavailable_observations,
        "unavailable_reasons": unavailable_reasons,
    }


def _build_paper_lab_order_traceability_review_payload(
    config,
    *,
    symbol: str,
    source_order_run_log: str,
    source_snapshot_run_log: str,
) -> dict[str, object]:
    checked_symbol = symbol.strip().upper()
    profile_gate = _paper_profile_gate(config)
    payload = _paper_lab_order_traceability_base_payload(
        profile_gate,
        symbol=checked_symbol,
        source_order_run_log=source_order_run_log,
        source_snapshot_run_log=source_snapshot_run_log,
    )
    payload = _paper_lab_order_traceability_source_payload(payload)
    if not profile_gate["passed"]:
        return _finalize_paper_lab_order_traceability_review(
            {
                **payload,
                "error": "profile_gate_failed",
                "unavailable_observations": [
                    "account",
                    "positions",
                    "recent_open_orders",
                    "recent_all_orders",
                    "recent_closed_orders",
                ],
            }
        )

    try:
        broker = _build_paper_broker(config.alpaca_paper)
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _finalize_paper_lab_order_traceability_review(
            _paper_lab_order_traceability_unavailable_payload(
                payload,
                "broker",
                exc,
                config,
            )
        )

    payload = _observe_paper_lab_traceability_account(payload, broker, config)
    payload = _observe_paper_lab_traceability_positions(payload, broker, config)
    payload = _observe_paper_lab_traceability_orders(
        payload,
        broker,
        config,
        label="recent_open",
        status_filter="open",
    )
    payload = _observe_paper_lab_traceability_orders(
        payload,
        broker,
        config,
        label="recent_all",
        status_filter="all",
    )
    payload = _observe_paper_lab_traceability_orders(
        payload,
        broker,
        config,
        label="recent_closed",
        status_filter="closed",
    )
    return _finalize_paper_lab_order_traceability_review(payload)


def _paper_lab_order_traceability_base_payload(
    profile_gate: dict[str, object],
    *,
    symbol: str,
    source_order_run_log: str,
    source_snapshot_run_log: str,
) -> dict[str, object]:
    return {
        "account": None,
        "account_observation_available": False,
        "asset_class": "equity",
        "broker_order_id_exposed": False,
        "client_order_id_exposed": False,
        "command": "paper-lab-order-traceability-review",
        "error": "",
        "filled_spy_order": None,
        "filled_spy_order_found": False,
        "gates": {"profile_gate": profile_gate},
        "manual_review_required": True,
        "m351_correlation_basis": "none",
        "mutated": False,
        "not_live_authorized": True,
        "ok": False,
        "order_traceability_observation_available": False,
        "paper_lab_only": True,
        "position_count": 0,
        "position_symbols": [],
        "positions": [],
        "positions_observation_available": False,
        "profit_claim": "none",
        "recent_all_order_count": 0,
        "recent_all_order_query": _empty_traceability_order_query_payload(),
        "recent_all_orders": [],
        "recent_closed_order_count": 0,
        "recent_closed_order_query": _empty_traceability_order_query_payload(),
        "recent_closed_orders": [],
        "recent_filled_order_count": 0,
        "recent_open_order_count": 0,
        "recent_open_order_query": _empty_traceability_order_query_payload(),
        "recent_open_orders": [],
        "recent_order_query_metadata_complete": False,
        "recent_order_query_metadata_missing_fields": [],
        "redaction": "credentials_redacted",
        "recommended_next_operator_action": (
            "collect_read_only_traceability_before_cleanup_preview"
        ),
        "review_state": "blocked_from_spy_paper_cleanup_preview_milestone",
        "side": "buy",
        "source_m351_evidence_available": False,
        "source_m351_reference": {},
        "source_m351_run_log": source_order_run_log,
        "source_m352_evidence_available": False,
        "source_m352_reference": {},
        "source_m352_run_log": source_snapshot_run_log,
        "spy_average_price": "",
        "spy_position_observed": False,
        "spy_quantity": "",
        "submitted": False,
        "symbol": symbol,
        "traceability_gap": "not_evaluated",
        "unavailable_observations": [],
        "unavailable_reasons": {},
        "unexpected_open_orders": False,
        "unexpected_position_symbols": [],
    }


def _empty_traceability_order_query_payload() -> dict[str, object]:
    from .execution.paper_lab_snapshot import empty_recent_order_query_payload

    return {
        **empty_recent_order_query_payload(),
        "recent_order_query_attempted": False,
        "recent_order_query_available": False,
        "recent_order_query_returned_count": 0,
    }


def _paper_lab_order_traceability_source_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    m351_records = _load_jsonl_records(str(payload["source_m351_run_log"]))
    m352_records = _load_jsonl_records(str(payload["source_m352_run_log"]))
    m351_reference = _m351_order_reference(m351_records)
    m352_reference = _m352_snapshot_reference(m352_records, str(payload["symbol"]))
    return {
        **payload,
        "source_m351_evidence_available": bool(m351_reference),
        "source_m351_reference": m351_reference,
        "source_m352_evidence_available": bool(m352_reference),
        "source_m352_reference": m352_reference,
    }


def _load_jsonl_records(path: str) -> list[dict[str, object]]:
    from pathlib import Path

    try:
        return [
            json.loads(line)
            for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, json.JSONDecodeError):
        return []


def _m351_order_reference(records: list[dict[str, object]]) -> dict[str, object]:
    for record in reversed(records):
        if record.get("event_type") != "paper_order_receipt_observed":
            continue
        if record.get("symbol") != "SPY" or record.get("side") != "buy":
            continue
        return {
            "accepted": record.get("accepted"),
            "asset_class": record.get("asset_class"),
            "client_order_id": record.get("client_order_id"),
            "filled": record.get("filled"),
            "notional": record.get("notional"),
            "normalized_status": record.get("normalized_status"),
            "order_type": record.get("order_type"),
            "raw_status": record.get("raw_status"),
            "run_id": record.get("run_id"),
            "side": record.get("side"),
            "submitted": record.get("submitted"),
            "symbol": record.get("symbol"),
            "time_in_force": record.get("time_in_force"),
        }

    return {}


def _m352_snapshot_reference(
    records: list[dict[str, object]],
    symbol: str,
) -> dict[str, object]:
    positions_record = next(
        (
            record
            for record in reversed(records)
            if record.get("event_type") == "paper_lab_snapshot_positions_observed"
        ),
        {},
    )
    orders_record = next(
        (
            record
            for record in reversed(records)
            if record.get("event_type") == "paper_lab_snapshot_orders_observed"
        ),
        {},
    )
    if not positions_record and not orders_record:
        return {}

    positions = positions_record.get("positions")
    position = _position_for_symbol(
        positions if isinstance(positions, list) else [],
        symbol,
    )
    return {
        "mutated": positions_record.get("mutated", orders_record.get("mutated")),
        "recent_open_order_count": orders_record.get("recent_order_count"),
        "run_id": positions_record.get("run_id", orders_record.get("run_id")),
        "spy_average_price": position.get("average_price", ""),
        "spy_position_observed": bool(position),
        "spy_quantity": position.get("quantity", ""),
        "submitted": positions_record.get("submitted", orders_record.get("submitted")),
    }


def _observe_paper_lab_traceability_account(
    payload: dict[str, object],
    broker,
    config,
) -> dict[str, object]:
    from .execution.paper_lab_snapshot import account_observation_payload

    try:
        account = broker.get_account()
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _paper_lab_order_traceability_unavailable_payload(
            payload,
            "account",
            exc,
            config,
        )

    return {
        **payload,
        "account": account_observation_payload(account),
        "account_observation_available": True,
    }


def _observe_paper_lab_traceability_positions(
    payload: dict[str, object],
    broker,
    config,
) -> dict[str, object]:
    from .execution.paper_lab_snapshot import (
        position_observation_payloads,
        position_symbols,
    )

    try:
        positions = position_observation_payloads(broker.get_positions())
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _paper_lab_order_traceability_unavailable_payload(
            payload,
            "positions",
            exc,
            config,
        )

    return {
        **payload,
        "position_count": len(positions),
        "position_symbols": list(position_symbols(positions)),
        "positions": list(positions),
        "positions_observation_available": True,
    }


def _observe_paper_lab_traceability_orders(
    payload: dict[str, object],
    broker,
    config,
    *,
    label: str,
    status_filter: str,
) -> dict[str, object]:
    from .execution.alpaca_client import AlpacaRecentOrderQuery
    from .execution.paper_lab_snapshot import (
        order_observation_payloads,
        recent_order_query_payload,
    )

    query = AlpacaRecentOrderQuery(
        status_filter=status_filter,
        symbol_filter=str(payload["symbol"]),
        side_filter=str(payload["side"]),
    )
    query_payload = {
        **recent_order_query_payload(query),
        "recent_order_query_attempted": True,
        "recent_order_query_available": False,
        "recent_order_query_returned_count": 0,
    }
    try:
        orders = order_observation_payloads(broker.get_recent_orders(query))
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _paper_lab_order_traceability_unavailable_payload(
            {
                **payload,
                f"{label}_order_query": query_payload,
            },
            f"{label}_orders",
            exc,
            config,
        )

    complete_query_payload = {
        **query_payload,
        "recent_order_query_available": True,
        "recent_order_query_returned_count": len(orders),
    }
    return {
        **payload,
        f"{label}_order_count": len(orders),
        f"{label}_order_query": complete_query_payload,
        f"{label}_orders": list(orders),
    }


def _paper_lab_order_traceability_unavailable_payload(
    payload: dict[str, object],
    observation_name: str,
    exc: Exception,
    config,
) -> dict[str, object]:
    unavailable_observations = list(payload.get("unavailable_observations", []))
    if observation_name not in unavailable_observations:
        unavailable_observations.append(observation_name)

    unavailable_reasons = dict(payload.get("unavailable_reasons", {}))
    unavailable_reasons[observation_name] = {
        "error_type": exc.__class__.__name__,
        "message": _redact_config_secrets(str(exc), config),
    }
    return {
        **payload,
        "error": "paper_lab_order_traceability_unavailable",
        "unavailable_observations": unavailable_observations,
        "unavailable_reasons": unavailable_reasons,
    }


def _finalize_paper_lab_order_traceability_review(
    payload: dict[str, object],
) -> dict[str, object]:
    symbol = str(payload["symbol"])
    positions = payload.get("positions")
    position = _position_for_symbol(positions if isinstance(positions, list) else [], symbol)
    unexpected_position_symbols = [
        str(item)
        for item in payload.get("position_symbols", [])
        if str(item) != symbol
    ]
    recent_all_orders = payload.get("recent_all_orders")
    all_orders = recent_all_orders if isinstance(recent_all_orders, list) else []
    filled_orders = [
        order
        for order in all_orders
        if _is_filled_symbol_order(order, symbol)
    ]
    m351_reference = _payload_mapping(payload.get("source_m351_reference"))
    matched_order, match_basis = _matched_traceability_order(
        filled_orders,
        m351_reference,
        symbol,
    )
    all_order_queries_available = all(
        _payload_mapping(payload.get(f"{label}_order_query")).get(
            "recent_order_query_available"
        )
        is True
        for label in ("recent_open", "recent_all", "recent_closed")
    )
    metadata_missing_fields = _traceability_query_missing_fields(payload)
    metadata_complete = all_order_queries_available and not metadata_missing_fields
    observations_available = (
        payload.get("account_observation_available") is True
        and payload.get("positions_observation_available") is True
        and all_order_queries_available
    )
    open_order_count = _int_payload_value(payload.get("recent_open_order_count"))
    m352_reference = _payload_mapping(payload.get("source_m352_reference"))
    source_ready = (
        _m351_reference_is_usable(m351_reference)
        and m352_reference.get("mutated") is False
        and m352_reference.get("submitted") is False
        and m352_reference.get("spy_position_observed") is True
    )
    ready = (
        observations_available
        and source_ready
        and bool(position)
        and not unexpected_position_symbols
        and open_order_count == 0
        and metadata_complete
        and bool(matched_order)
    )
    review_state = (
        "ready_for_spy_paper_cleanup_preview_milestone"
        if ready
        else "blocked_from_spy_paper_cleanup_preview_milestone"
    )
    traceability_gap = _traceability_gap(
        matched_order=matched_order,
        source_ready=source_ready,
        position=position,
        unexpected_position_symbols=unexpected_position_symbols,
        open_order_count=open_order_count,
        metadata_complete=metadata_complete,
        observations_available=observations_available,
    )
    return {
        **payload,
        "broker_order_id_exposed": bool(matched_order.get("order_id")),
        "client_order_id_exposed": bool(matched_order.get("client_order_id")),
        "filled_spy_order": matched_order or None,
        "filled_spy_order_found": bool(matched_order),
        "m351_correlation_basis": match_basis,
        "ok": ready,
        "order_traceability_observation_available": observations_available,
        "recent_filled_order_count": len(filled_orders),
        "recent_order_query_metadata_complete": metadata_complete,
        "recent_order_query_metadata_missing_fields": metadata_missing_fields,
        "recommended_next_operator_action": (
            "design_spy_cleanup_close_preview_only_no_submit"
            if ready
            else "manual_review_traceability_gap_before_cleanup_preview"
        ),
        "review_state": review_state,
        "spy_average_price": position.get("average_price", ""),
        "spy_position_observed": bool(position),
        "spy_quantity": position.get("quantity", ""),
        "traceability_gap": traceability_gap,
        "unexpected_open_orders": open_order_count != 0,
        "unexpected_position_symbols": unexpected_position_symbols,
    }


def _build_paper_lab_spy_close_preview_payload(
    config,
    *,
    run_id: str,
    symbol: str,
    source_traceability_run_log: str,
) -> dict[str, object]:
    checked_symbol = symbol.strip().upper()
    profile_gate = _paper_profile_gate(config)
    payload = _paper_lab_spy_close_preview_base_payload(
        profile_gate,
        run_id=run_id,
        symbol=checked_symbol,
        source_traceability_run_log=source_traceability_run_log,
    )
    payload = _paper_lab_spy_close_preview_source_payload(payload)
    if not profile_gate["passed"]:
        return _finalize_paper_lab_spy_close_preview(
            {
                **payload,
                "error": "profile_gate_failed",
                "unavailable_observations": [
                    "account",
                    "positions",
                    "recent_open_orders",
                ],
            }
        )

    try:
        broker = _build_paper_broker(config.alpaca_paper)
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _finalize_paper_lab_spy_close_preview(
            _paper_lab_spy_close_preview_unavailable_payload(
                payload,
                "broker",
                exc,
                config,
            )
        )

    payload = _observe_paper_lab_spy_close_preview_account(payload, broker, config)
    payload = _observe_paper_lab_spy_close_preview_positions(payload, broker, config)
    payload = _observe_paper_lab_spy_close_preview_open_orders(
        payload,
        broker,
        config,
    )
    return _finalize_paper_lab_spy_close_preview(payload)


def _paper_lab_spy_close_preview_base_payload(
    profile_gate: dict[str, object],
    *,
    run_id: str,
    symbol: str,
    source_traceability_run_log: str,
) -> dict[str, object]:
    return {
        "account": None,
        "account_cash": "",
        "account_currency": "",
        "account_observation_available": False,
        "asset_class": "equity",
        "blockers": [],
        "broker_action_performed": False,
        "close_order_submitted": False,
        "command": "paper-lab-spy-close-preview",
        "error": "",
        "final_operator_instruction": _PAPER_SPY_CLOSE_PREVIEW_OPERATOR_INSTRUCTION,
        "fresh_observation_status": "",
        "gates": {"profile_gate": profile_gate},
        "live_authorized": False,
        "manual_review_required": True,
        "m351_client_order_id": "",
        "m351_correlation_basis": "none",
        "m353_evidence_available": False,
        "m353_ready": False,
        "m353_traceability_summary": {},
        "max_cleanup_quantity": "",
        "mutated": False,
        "not_live_authorized": True,
        "notional_quantity_validation_result": {},
        "ok": False,
        "open_order_blockers": [],
        "order_type": "market",
        "orders_observation_available": False,
        "paper_lab_only": True,
        "paper_profile_gate_result": profile_gate,
        "position_count": 0,
        "position_symbols": [],
        "positions": [],
        "positions_observation_available": False,
        "preview_only": True,
        "profit_claim": "none",
        "quantity": "",
        "recent_open_order_count": 0,
        "recent_open_order_query": _empty_traceability_order_query_payload(),
        "recent_open_orders": [],
        "recent_order_query_metadata_complete": False,
        "recent_order_query_metadata_missing_fields": [],
        "redaction": "credentials_redacted",
        "run_id": run_id,
        "side": "sell",
        "source_traceability_run_log": source_traceability_run_log,
        "stale_evidence_blockers": [],
        "state": "blocked_from_spy_paper_close_submit_milestone",
        "submitted": False,
        "symbol": symbol,
        "time_in_force": "day",
        "unavailable_observation_blockers": [],
        "unavailable_observations": [],
        "unavailable_reasons": {},
        "unexpected_position_blockers": [],
    }


def _paper_lab_spy_close_preview_source_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    records = _load_jsonl_records(str(payload["source_traceability_run_log"]))
    m353_record = _latest_m353_traceability_record(records, str(payload["symbol"]))
    if not m353_record:
        return payload

    summary = _m353_traceability_summary(m353_record)
    return {
        **payload,
        "m351_client_order_id": summary.get("m351_client_order_id", ""),
        "m351_correlation_basis": summary.get("m351_correlation_basis", "none"),
        "m353_evidence_available": True,
        "m353_ready": _m353_traceability_ready(m353_record),
        "m353_traceability_summary": summary,
    }


def _latest_m353_traceability_record(
    records: list[dict[str, object]],
    symbol: str,
) -> dict[str, object]:
    for record in reversed(records):
        if record.get("event_type") != "paper_lab_order_traceability_reviewed":
            continue
        if record.get("symbol") == symbol:
            return dict(record)

    return {}


def _m353_traceability_summary(
    record: Mapping[str, object],
) -> dict[str, object]:
    filled_order = _payload_mapping(record.get("filled_spy_order"))
    source_m351 = _payload_mapping(record.get("source_m351_reference"))
    client_order_id = str(
        filled_order.get("client_order_id")
        or source_m351.get("client_order_id")
        or ""
    )
    return {
        "filled_at": filled_order.get("filled_at", ""),
        "m351_client_order_id": client_order_id,
        "m351_correlation_basis": record.get("m351_correlation_basis", "none"),
        "mutated": record.get("mutated"),
        "recent_all_spy_buy_order_count": record.get("recent_all_order_count", 0),
        "recent_closed_spy_buy_order_count": record.get(
            "recent_closed_order_count",
            0,
        ),
        "recent_filled_spy_buy_order_count": record.get(
            "recent_filled_order_count",
            0,
        ),
        "recent_open_spy_buy_order_count": record.get("recent_open_order_count", 0),
        "review_state": record.get("review_state", ""),
        "run_id": record.get("run_id", ""),
        "spy_average_price": record.get("spy_average_price", ""),
        "spy_position_observed": record.get("spy_position_observed"),
        "spy_quantity": record.get("spy_quantity", ""),
        "submitted": record.get("submitted"),
        "traceability_gap": record.get("traceability_gap", ""),
    }


def _m353_traceability_ready(record: Mapping[str, object]) -> bool:
    return (
        record.get("ok") is True
        and record.get("review_state")
        == "ready_for_spy_paper_cleanup_preview_milestone"
        and record.get("mutated") is False
        and record.get("submitted") is False
        and record.get("symbol") == "SPY"
        and record.get("spy_position_observed") is True
        and record.get("order_traceability_observation_available") is True
        and record.get("recent_order_query_metadata_complete") is True
        and _int_payload_value(record.get("recent_open_order_count")) == 0
        and record.get("filled_spy_order_found") is True
    )


def _observe_paper_lab_spy_close_preview_account(
    payload: dict[str, object],
    broker,
    config,
) -> dict[str, object]:
    from .execution.paper_lab_snapshot import account_observation_payload

    try:
        account = account_observation_payload(broker.get_account())
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _paper_lab_spy_close_preview_unavailable_payload(
            payload,
            "account",
            exc,
            config,
        )

    return {
        **payload,
        "account": account,
        "account_cash": account.get("cash", ""),
        "account_currency": account.get("currency", ""),
        "account_observation_available": True,
    }


def _observe_paper_lab_spy_close_preview_positions(
    payload: dict[str, object],
    broker,
    config,
) -> dict[str, object]:
    from .execution.paper_lab_snapshot import (
        position_observation_payloads,
        position_symbols,
    )

    try:
        positions = position_observation_payloads(broker.get_positions())
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _paper_lab_spy_close_preview_unavailable_payload(
            payload,
            "positions",
            exc,
            config,
        )

    return {
        **payload,
        "position_count": len(positions),
        "position_symbols": list(position_symbols(positions)),
        "positions": list(positions),
        "positions_observation_available": True,
    }


def _observe_paper_lab_spy_close_preview_open_orders(
    payload: dict[str, object],
    broker,
    config,
) -> dict[str, object]:
    from .execution.alpaca_client import AlpacaRecentOrderQuery
    from .execution.paper_lab_snapshot import (
        order_observation_payloads,
        recent_order_query_payload,
    )

    query = AlpacaRecentOrderQuery(
        status_filter="open",
        symbol_filter=str(payload["symbol"]),
    )
    query_payload = {
        **recent_order_query_payload(query),
        "recent_order_query_attempted": True,
        "recent_order_query_available": False,
        "recent_order_query_returned_count": 0,
    }
    try:
        orders = order_observation_payloads(broker.get_recent_orders(query))
    except Exception as exc:  # pragma: no cover - fake failure safety path
        return _paper_lab_spy_close_preview_unavailable_payload(
            {
                **payload,
                "recent_open_order_query": query_payload,
            },
            "recent_open_orders",
            exc,
            config,
        )

    complete_query_payload = {
        **query_payload,
        "recent_order_query_available": True,
        "recent_order_query_returned_count": len(orders),
    }
    return {
        **payload,
        "orders_observation_available": True,
        "recent_open_order_count": len(orders),
        "recent_open_order_query": complete_query_payload,
        "recent_open_orders": list(orders),
        "recent_order_query_metadata_complete": complete_query_payload[
            "recent_order_query_metadata_complete"
        ],
        "recent_order_query_metadata_missing_fields": complete_query_payload[
            "recent_order_query_metadata_missing_fields"
        ],
    }


def _paper_lab_spy_close_preview_unavailable_payload(
    payload: dict[str, object],
    observation_name: str,
    exc: Exception,
    config,
) -> dict[str, object]:
    unavailable_observations = list(payload.get("unavailable_observations", []))
    if observation_name not in unavailable_observations:
        unavailable_observations.append(observation_name)

    unavailable_reasons = dict(payload.get("unavailable_reasons", {}))
    unavailable_reasons[observation_name] = {
        "error_type": exc.__class__.__name__,
        "message": _redact_config_secrets(str(exc), config),
    }
    return {
        **payload,
        "error": "paper_lab_spy_close_preview_unavailable",
        "unavailable_observations": unavailable_observations,
        "unavailable_reasons": unavailable_reasons,
    }


def _finalize_paper_lab_spy_close_preview(
    payload: dict[str, object],
) -> dict[str, object]:
    symbol = str(payload["symbol"])
    positions = payload.get("positions")
    position = _position_for_symbol(positions if isinstance(positions, list) else [], symbol)
    observed_quantity = position.get("quantity", "")
    observed_average_price = position.get("average_price", "")
    m353_summary = _payload_mapping(payload.get("m353_traceability_summary"))
    unexpected_position_symbols = tuple(
        str(item)
        for item in payload.get("position_symbols", [])
        if str(item) != symbol
    )
    unavailable_blockers = _spy_close_unavailable_blockers(payload, position)
    stale_blockers = _spy_close_stale_evidence_blockers(
        payload,
        m353_summary,
        observed_quantity=observed_quantity,
        observed_average_price=observed_average_price,
    )
    open_order_count = _int_payload_value(payload.get("recent_open_order_count"))
    open_order_blockers = (
        ["recent_open_spy_order_count_nonzero"]
        if payload.get("orders_observation_available") is True
        and open_order_count != 0
        else []
    )
    unexpected_position_blockers = [
        f"unexpected_position_symbols:{','.join(unexpected_position_symbols)}"
    ] if unexpected_position_symbols else []
    fresh_observation_status = (
        _PAPER_SPY_CLOSE_PREVIEW_REQUIRED_OBSERVATION_STATUS
        if not unavailable_blockers and observed_quantity
        else "fresh_read_only_spy_position_observation_blocked"
    )
    source_traceability_ready = (
        payload.get("m353_ready") is True and not stale_blockers
    )
    contract = build_spy_paper_close_preview_contract(
        observed_position_quantity=observed_quantity,
        requested_close_quantity=observed_quantity,
        fresh_observation_status=fresh_observation_status,
        recent_order_query_metadata_complete=(
            payload.get("recent_order_query_metadata_complete") is True
        ),
        source_mutated=_payload_bool_or_none(m353_summary.get("mutated")),
        source_submitted=_payload_bool_or_none(m353_summary.get("submitted")),
        source_traceability_ready=source_traceability_ready,
        recent_open_order_count=(
            open_order_count
            if payload.get("orders_observation_available") is True
            else None
        ),
        unexpected_position_symbols=unexpected_position_symbols,
        unavailable_observations=tuple(unavailable_blockers),
        symbol=symbol,
    )
    contract_payload = contract.to_payload()
    gates = {
        "profile_gate": payload["paper_profile_gate_result"],
        **_payload_mapping(contract_payload.get("gates")),
    }
    ready = (
        contract_payload["ok"] is True
        and _payload_mapping(gates.get("profile_gate")).get("passed") is True
    )
    preview_quantity = contract_payload["requested_close_quantity"] if ready else ""
    blockers = _spy_close_blockers(
        gates,
        stale_blockers=stale_blockers,
        open_order_blockers=open_order_blockers,
        unexpected_position_blockers=unexpected_position_blockers,
        unavailable_blockers=unavailable_blockers,
    )
    state = (
        "ready_for_separate_spy_paper_close_submit_milestone"
        if ready
        else "blocked_from_spy_paper_close_submit_milestone"
    )
    return {
        **payload,
        **contract_payload,
        "allowlist_result": gates.get("allowlist_gate", {}),
        "blockers": blockers,
        "close_preview_status": (
            "readiness_ready_review_only" if ready else "readiness_blocked_review_only"
        ),
        "fresh_observation_status": fresh_observation_status,
        "gates": gates,
        "live_authorized": False,
        "m351_client_order_id": m353_summary.get("m351_client_order_id", ""),
        "m351_correlation_basis": m353_summary.get(
            "m351_correlation_basis",
            "none",
        ),
        "max_cleanup_quantity": observed_quantity,
        "mutated": False,
        "notional_quantity_validation_result": _spy_close_quantity_validation(
            gates,
            observed_quantity=observed_quantity,
            validation_quantity=contract_payload["requested_close_quantity"],
        ),
        "ok": ready,
        "open_order_blockers": open_order_blockers,
        "paper_profile_gate_result": gates["profile_gate"],
        "preview_quantity": preview_quantity,
        "quantity": preview_quantity,
        "recent_open_order_count": open_order_count,
        "requested_close_quantity": preview_quantity,
        "remaining_quantity_after_preview": "0" if ready else "",
        "stale_evidence_blockers": stale_blockers,
        "state": state,
        "submitted": False,
        "unavailable_observation_blockers": unavailable_blockers,
        "unexpected_position_blockers": unexpected_position_blockers,
        "observed_spy_average_price": observed_average_price,
        "observed_spy_quantity": observed_quantity,
    }


def _spy_close_unavailable_blockers(
    payload: Mapping[str, object],
    position: Mapping[str, str],
) -> list[str]:
    blockers = list(_payload_string_tuple(payload.get("unavailable_observations")))
    if payload.get("account_observation_available") is not True:
        _append_unique(blockers, "account_observation_unavailable")
    if payload.get("positions_observation_available") is not True:
        _append_unique(blockers, "positions_observation_unavailable")
    if payload.get("orders_observation_available") is not True:
        _append_unique(blockers, "recent_open_orders_observation_unavailable")
    if payload.get("positions_observation_available") is True and not position:
        _append_unique(blockers, "spy_position_not_present")

    return blockers


def _spy_close_stale_evidence_blockers(
    payload: Mapping[str, object],
    m353_summary: Mapping[str, object],
    *,
    observed_quantity: str,
    observed_average_price: str,
) -> list[str]:
    if payload.get("m353_evidence_available") is not True:
        return ["m353_traceability_evidence_missing"]
    if payload.get("m353_ready") is not True:
        return ["m353_traceability_not_ready"]

    blockers: list[str] = []
    source_quantity = str(m353_summary.get("spy_quantity", ""))
    source_average_price = str(m353_summary.get("spy_average_price", ""))
    if observed_quantity and source_quantity and observed_quantity != source_quantity:
        blockers.append("observed_spy_quantity_changed_since_m353")
    if (
        observed_average_price
        and source_average_price
        and observed_average_price != source_average_price
    ):
        blockers.append("observed_spy_average_price_changed_since_m353")

    return blockers


def _spy_close_blockers(
    gates: Mapping[str, object],
    *,
    stale_blockers: list[str],
    open_order_blockers: list[str],
    unexpected_position_blockers: list[str],
    unavailable_blockers: list[str],
) -> list[str]:
    blockers = [
        *stale_blockers,
        *open_order_blockers,
        *unexpected_position_blockers,
        *unavailable_blockers,
    ]
    for gate_name, gate in gates.items():
        gate_payload = _payload_mapping(gate)
        if gate_payload.get("passed") is True:
            continue
        detail = str(gate_payload.get("detail", ""))
        _append_unique(blockers, f"{gate_name}_failed:{detail}")

    return blockers


def _spy_close_quantity_validation(
    gates: Mapping[str, object],
    *,
    observed_quantity: str,
    validation_quantity: str,
) -> dict[str, object]:
    quantity_gate = _payload_mapping(gates.get("quantity_gate"))
    within_gate = _payload_mapping(
        gates.get("close_quantity_within_observed_position_gate")
    )
    no_shorting_gate = _payload_mapping(gates.get("no_shorting_gate"))
    return {
        "notional_used": False,
        "observed_quantity": observed_quantity,
        "quantity_positive": quantity_gate.get("passed") is True,
        "quantity_within_observed_position": within_gate.get("passed") is True,
        "requested_quantity": validation_quantity,
        "sizing_mode": "quantity",
        "would_short": no_shorting_gate.get("passed") is not True,
    }


def _append_unique(items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def _position_for_symbol(
    positions: list[object],
    symbol: str,
) -> dict[str, str]:
    for position in positions:
        if not isinstance(position, dict):
            continue
        if position.get("symbol") == symbol:
            return {
                "average_price": str(position.get("average_price", "")),
                "quantity": str(position.get("quantity", "")),
                "symbol": symbol,
            }

    return {}


def _is_filled_symbol_order(order: object, symbol: str) -> bool:
    if not isinstance(order, dict):
        return False
    return (
        order.get("symbol") == symbol
        and order.get("side") == "buy"
        and order.get("normalized_status") == "filled"
    )


def _matched_traceability_order(
    filled_orders: list[object],
    m351_reference: Mapping[str, object],
    symbol: str,
) -> tuple[dict[str, object], str]:
    m351_client_order_id = str(m351_reference.get("client_order_id") or "")
    for order in filled_orders:
        if not isinstance(order, dict):
            continue
        if m351_client_order_id and order.get("client_order_id") == m351_client_order_id:
            return dict(order), "client_order_id"

    for order in filled_orders:
        if not isinstance(order, dict):
            continue
        if order.get("symbol") == symbol and order.get("side") == "buy":
            return dict(order), "symbol_side_filled_status"

    return {}, "none"


def _m351_reference_is_usable(reference: Mapping[str, object]) -> bool:
    return (
        reference.get("submitted") is True
        and reference.get("accepted") is True
        and reference.get("symbol") == "SPY"
        and reference.get("side") == "buy"
        and reference.get("notional") == "25.00"
    )


def _traceability_query_missing_fields(
    payload: Mapping[str, object],
) -> list[str]:
    missing_fields: list[str] = []
    for label in ("recent_open", "recent_all", "recent_closed"):
        query_payload = _payload_mapping(payload.get(f"{label}_order_query"))
        if query_payload.get("recent_order_query_metadata_complete") is not True:
            missing_fields.append(f"{label}_order_query")
        for field in query_payload.get("recent_order_query_metadata_missing_fields", []):
            missing_fields.append(f"{label}.{field}")

    return missing_fields


def _traceability_gap(
    *,
    matched_order: Mapping[str, object],
    source_ready: bool,
    position: Mapping[str, str],
    unexpected_position_symbols: list[str],
    open_order_count: int | None,
    metadata_complete: bool,
    observations_available: bool,
) -> str:
    if matched_order:
        return ""
    if not source_ready:
        return "source_m351_or_m352_evidence_unavailable"
    if not observations_available:
        return "read_only_observations_unavailable"
    if not position:
        return "spy_position_not_present"
    if unexpected_position_symbols:
        return "unexpected_non_spy_positions_observed"
    if open_order_count != 0:
        return "recent_open_orders_not_zero"
    if not metadata_complete:
        return "recent_order_query_metadata_incomplete"
    return "filled_spy_order_not_found"


def _paper_post_submit_observation(broker, config) -> dict[str, object]:
    try:
        account = broker.get_account()
        positions = broker.get_positions()
    except Exception as exc:  # pragma: no cover - fake failure safety path
        redacted_message = _redact_config_secrets(str(exc), config)
        return {
            "post_submit_observation_error": (
                "paper_order_post_submit_observation_failed"
            ),
            "post_submit_observation_error_type": exc.__class__.__name__,
            "post_submit_observation_message": redacted_message,
        }

    position_rows = [
        {
            "average_price": _decimal_text(position.average_price),
            "quantity": _decimal_text(position.quantity),
            "symbol": position.symbol,
        }
        for position in sorted(positions, key=lambda item: item.symbol)
    ]
    return {
        "post_submit_account": {
            "cash": _decimal_text(account.cash),
            "currency": account.currency,
        },
        "post_submit_position_count": len(position_rows),
        "post_submit_positions": position_rows,
    }


def _run_paper_order_probe(config, args: argparse.Namespace) -> int:
    run_log_path = args.run_log
    resolved_run_id = _paper_lab_run_id(args.run_id) if run_log_path else ""
    if run_log_path and not _ensure_paper_lab_run_log(run_log_path):
        return 1

    payload = _build_paper_order_probe_payload(config, args)
    if run_log_path and not _write_paper_order_initial_run_log(
        run_log_path,
        resolved_run_id,
        payload,
        config,
    ):
        return 1

    if payload["ok"] and payload["submit_requested"]:
        payload = _submit_paper_order_probe(
            config,
            payload,
            observe_post_submit=bool(run_log_path),
        )
        if run_log_path and not _write_paper_order_submit_run_log(
            run_log_path,
            resolved_run_id,
            payload,
            config,
        ):
            print(_render_paper_order_probe_payload(payload, args.output_format))
            return 1
    print(_render_paper_order_probe_payload(payload, args.output_format))
    if payload.get("broker_error"):
        return 1

    return 0 if payload["ok"] else 2


def _run_paper_close_probe(config, args: argparse.Namespace) -> int:
    run_log_path = args.run_log
    resolved_run_id = _paper_lab_run_id(args.run_id) if run_log_path else ""
    if run_log_path and not _ensure_paper_lab_run_log(run_log_path):
        return 1

    broker = None
    payload = _build_paper_close_probe_payload(config, args)
    if payload["ok"] and payload["submit_requested"]:
        payload, broker = _attach_paper_close_pre_submit_observation(
            config,
            payload,
        )

    if run_log_path and not _write_paper_order_initial_run_log(
        run_log_path,
        resolved_run_id,
        payload,
        config,
    ):
        return 1

    if payload["ok"] and payload["submit_requested"]:
        payload = _submit_paper_close_probe(
            config,
            payload,
            broker=broker,
            observe_post_submit=bool(run_log_path),
        )
        if run_log_path and not _write_paper_order_submit_run_log(
            run_log_path,
            resolved_run_id,
            payload,
            config,
        ):
            print(_render_paper_close_probe_payload(payload, args.output_format))
            return 1

    print(_render_paper_close_probe_payload(payload, args.output_format))
    if payload.get("broker_error"):
        return 1

    return 0 if payload["ok"] else 2


def _build_paper_close_probe_payload(
    config,
    args: argparse.Namespace,
) -> dict[str, object]:
    asset_class = args.asset_class.strip().lower()
    symbol = args.symbol.strip().upper()
    side = args.side.strip().lower()
    quantity, quantity_error = _positive_decimal(args.quantity, "quantity")
    max_quantity, max_quantity_error = _positive_decimal(
        args.max_quantity,
        "max_quantity",
    )
    quantity_within_max = (
        quantity is not None
        and max_quantity is not None
        and quantity <= max_quantity
    )
    submit_requested = bool(args.submit and args.i_mean_it)

    profile_gate = _paper_profile_gate(config)
    halt_gate = _gate(
        _paper_halt_not_set(),
        "halt_not_set",
        "ALGOTRADER_PAPER_HALT=1",
    )
    gates = {
        "profile_gate": profile_gate,
        "halt_gate": halt_gate,
        "asset_class_gate": _gate(
            asset_class == _PAPER_ORDER_ASSET_CLASS_CRYPTO,
            "crypto",
            "asset_class_must_be_crypto",
        ),
        "symbol_gate": _gate(
            symbol == "BTCUSD",
            "symbol=BTCUSD",
            "symbol_must_be_BTCUSD",
        ),
        "side_gate": _gate(side == "sell", "sell_only", "side_must_be_sell"),
        "quantity_gate": _gate(
            quantity is not None,
            "quantity_positive",
            quantity_error or "quantity_required",
        ),
        "max_quantity_gate": _gate(
            max_quantity is not None,
            "max_quantity_positive",
            max_quantity_error or "max_quantity_required",
        ),
        "quantity_within_max_gate": _gate(
            quantity_within_max,
            "quantity_within_max_quantity",
            "quantity_exceeds_max_quantity",
        ),
        "submit_confirmation_gate": _paper_close_submit_confirmation_gate(
            submit_flag=bool(args.submit),
            i_mean_it_flag=bool(args.i_mean_it),
        ),
        "pre_submit_observation_gate": _gate(
            True,
            "pending_pre_submit_observation" if submit_requested else "not_requested",
            "pre_submit_observation_required",
        ),
        "observed_position_gate": _gate(
            True,
            "pending_pre_submit_observation" if submit_requested else "not_requested",
            "observed_BTCUSD_position_required",
        ),
        "observed_position_quantity_gate": _gate(
            True,
            "pending_pre_submit_observation" if submit_requested else "not_requested",
            "observed_BTCUSD_quantity_must_equal_max_quantity",
        ),
        "close_quantity_within_observed_position_gate": _gate(
            True,
            "pending_pre_submit_observation" if submit_requested else "not_requested",
            "requested_close_quantity_exceeds_observed_position",
        ),
        "no_shorting_gate": _gate(
            True,
            "pending_pre_submit_observation" if submit_requested else "not_requested",
            "requested_close_quantity_would_short_BTCUSD",
        ),
        "recent_order_query_metadata_gate": _gate(
            True,
            "pending_pre_submit_observation" if submit_requested else "not_requested",
            "recent_order_query_metadata_must_be_complete",
        ),
        "recent_open_order_gate": _gate(
            True,
            "pending_pre_submit_observation" if submit_requested else "not_requested",
            "recent_open_orders_must_be_zero",
        ),
    }
    ok = all(bool(gate["passed"]) for gate in gates.values())

    request_payload = None
    if (
        asset_class == _PAPER_ORDER_ASSET_CLASS_CRYPTO
        and symbol == "BTCUSD"
        and side == "sell"
        and quantity is not None
    ):
        try:
            request = _paper_order_request(
                symbol,
                asset_class=asset_class,
                client_order_id=_paper_close_probe_client_order_id(args.run_id),
                quantity=quantity,
                side=side,
                time_in_force="gtc",
            )
            request_payload = _paper_order_request_payload(request)
        except ValueError:
            request_payload = None

    return {
        "accepted": None,
        "asset_class": asset_class,
        "broker_normalized_status": "",
        "broker_raw_reason": "",
        "broker_raw_status": "",
        "broker_response_parsed": False,
        "broker_response_received": False,
        "broker_result_classification": "not_submitted",
        "command": "paper-close-probe",
        "error": "" if ok else _first_failed_close_gate(gates),
        "filled": None,
        "gates": gates,
        "max_notional": "",
        "max_quantity": (
            _decimal_text(max_quantity)
            if max_quantity is not None
            else args.max_quantity
        ),
        "min_notional": "",
        "mutated": False,
        "normalized_status": "",
        "notional": "",
        "ok": ok,
        "order_type": "market",
        "preview_only": not submit_requested,
        "proposed_order_request": request_payload,
        "raw_reason": "",
        "raw_status": "",
        "redaction": "credentials_redacted",
        "requested_i_mean_it": bool(args.i_mean_it),
        "requested_notional": "",
        "requested_qty": _decimal_text(quantity) if quantity is not None else "",
        "requested_quantity": _decimal_text(quantity) if quantity is not None else "",
        "requested_submit": bool(args.submit),
        "side": side,
        "sizing_mode": "qty",
        "submitted": False,
        "submission_disabled_reason": "",
        "submit_attempted": False,
        "submit_requested": submit_requested,
        "symbol": symbol,
        "time_in_force": "gtc",
    }


def _attach_paper_close_pre_submit_observation(
    config,
    payload: dict[str, object],
) -> tuple[dict[str, object], object | None]:
    from .execution.alpaca_client import AlpacaRecentOrderQuery
    from .execution.paper_lab_snapshot import (
        account_observation_payload,
        empty_recent_order_query_payload,
        order_observation_payloads,
        position_observation_payloads,
        recent_order_query_payload,
    )

    unavailable: list[str] = []
    unavailable_reasons: dict[str, object] = {}
    observation: dict[str, object] = {
        "account": None,
        "account_observation_available": False,
        "orders_observation_available": False,
        "position_count": 0,
        "position_symbols": [],
        "positions": [],
        "positions_observation_available": False,
        "pre_submit_position_count": 0,
        "recent_order_count": 0,
        "recent_order_query_attempted": False,
        "recent_order_query_available": False,
        "recent_order_query_returned_count": 0,
        **empty_recent_order_query_payload(),
        "recent_orders": [],
        "target_position_average_price": "",
        "target_position_observed": False,
        "target_position_quantity": "",
        "unavailable_observations": unavailable,
        "unavailable_reasons": unavailable_reasons,
    }

    try:
        broker = _build_paper_broker(config.alpaca_paper)
    except Exception as exc:  # pragma: no cover - fake failure safety path
        redacted_message = _redact_config_secrets(str(exc), config)
        unavailable.extend(["account", "positions", "orders"])
        unavailable_reasons["broker"] = {
            "error_type": exc.__class__.__name__,
            "message": redacted_message,
        }
        return _paper_close_observation_blocked_payload(
            payload,
            observation,
            broker_error=True,
            message=redacted_message,
        ), None

    try:
        account = broker.get_account()
        observation.update(
            {
                "account": account_observation_payload(account),
                "account_observation_available": True,
            }
        )
    except Exception as exc:  # pragma: no cover - fake failure safety path
        unavailable.append("account")
        unavailable_reasons["account"] = {
            "error_type": exc.__class__.__name__,
            "message": _redact_config_secrets(str(exc), config),
        }

    try:
        positions = position_observation_payloads(broker.get_positions())
        target_position = next(
            (position for position in positions if position["symbol"] == "BTCUSD"),
            None,
        )
        observation.update(
            {
                "position_count": len(positions),
                "position_symbols": [position["symbol"] for position in positions],
                "positions": list(positions),
                "positions_observation_available": True,
                "pre_submit_position_count": len(positions),
                "target_position_average_price": (
                    target_position["average_price"] if target_position else ""
                ),
                "target_position_observed": target_position is not None,
                "target_position_quantity": (
                    target_position["quantity"] if target_position else ""
                ),
            }
        )
    except Exception as exc:  # pragma: no cover - fake failure safety path
        unavailable.append("positions")
        unavailable_reasons["positions"] = {
            "error_type": exc.__class__.__name__,
            "message": _redact_config_secrets(str(exc), config),
        }

    query = AlpacaRecentOrderQuery()
    query_payload = {
        **recent_order_query_payload(query),
        "recent_order_query_attempted": True,
        "recent_order_query_available": False,
        "recent_order_query_returned_count": 0,
    }
    observation.update(query_payload)
    try:
        orders = order_observation_payloads(broker.get_recent_orders())
        observation.update(
            {
                "orders_observation_available": True,
                "recent_order_count": len(orders),
                "recent_order_query_available": True,
                "recent_order_query_returned_count": len(orders),
                "recent_orders": list(orders),
            }
        )
    except Exception as exc:  # pragma: no cover - fake failure safety path
        unavailable.append("orders")
        unavailable_reasons["orders"] = {
            "error_type": exc.__class__.__name__,
            "message": _redact_config_secrets(str(exc), config),
        }

    observed_quantity = _optional_decimal_value(
        observation.get("target_position_quantity")
    )
    requested_quantity = _optional_decimal_value(payload.get("requested_quantity"))
    max_quantity = _optional_decimal_value(payload.get("max_quantity"))
    observations_available = (
        observation["account_observation_available"]
        and observation["positions_observation_available"]
        and observation["orders_observation_available"]
        and not unavailable
    )
    observed_matches_max = (
        observed_quantity is not None
        and max_quantity is not None
        and observed_quantity == max_quantity
    )
    within_observed = (
        requested_quantity is not None
        and observed_quantity is not None
        and requested_quantity <= observed_quantity
    )
    gates = dict(payload["gates"])
    gates.update(
        {
            "pre_submit_observation_gate": _gate(
                bool(observations_available),
                "account_positions_orders_observed",
                "account_positions_orders_must_be_observed",
            ),
            "observed_position_gate": _gate(
                bool(observation["target_position_observed"]),
                "BTCUSD_position_observed",
                "BTCUSD_position_required",
            ),
            "observed_position_quantity_gate": _gate(
                observed_matches_max,
                "observed_BTCUSD_quantity_equals_max_quantity",
                "observed_BTCUSD_quantity_must_equal_max_quantity",
            ),
            "close_quantity_within_observed_position_gate": _gate(
                within_observed,
                "requested_close_quantity_within_observed_position",
                "requested_close_quantity_exceeds_observed_position",
            ),
            "no_shorting_gate": _gate(
                within_observed,
                "no_shorting_requested",
                "requested_close_quantity_would_short_BTCUSD",
            ),
            "recent_order_query_metadata_gate": _gate(
                observation.get("recent_order_query_metadata_complete") is True,
                "recent_order_query_metadata_complete",
                "recent_order_query_metadata_must_be_complete",
            ),
            "recent_open_order_gate": _gate(
                observation.get("recent_order_count") == 0,
                "recent_open_orders_zero",
                "recent_open_orders_must_be_zero",
            ),
        }
    )
    ok = all(bool(gate["passed"]) for gate in gates.values())
    return {
        **payload,
        **observation,
        "broker_error": False,
        "error": "" if ok else _first_failed_close_gate(gates),
        "gates": gates,
        "ok": ok,
        "preview_only": not ok,
        "submitted": False,
    }, broker


def _paper_close_observation_blocked_payload(
    payload: dict[str, object],
    observation: dict[str, object],
    *,
    broker_error: bool,
    message: str = "",
) -> dict[str, object]:
    gates = dict(payload["gates"])
    gates.update(
        {
            "pre_submit_observation_gate": _gate(
                False,
                "account_positions_orders_observed",
                "account_positions_orders_must_be_observed",
            ),
            "observed_position_gate": _gate(
                False,
                "BTCUSD_position_observed",
                "BTCUSD_position_required",
            ),
            "observed_position_quantity_gate": _gate(
                False,
                "observed_BTCUSD_quantity_equals_max_quantity",
                "observed_BTCUSD_quantity_must_equal_max_quantity",
            ),
            "close_quantity_within_observed_position_gate": _gate(
                False,
                "requested_close_quantity_within_observed_position",
                "requested_close_quantity_exceeds_observed_position",
            ),
            "no_shorting_gate": _gate(
                False,
                "no_shorting_requested",
                "requested_close_quantity_would_short_BTCUSD",
            ),
            "recent_order_query_metadata_gate": _gate(
                False,
                "recent_order_query_metadata_complete",
                "recent_order_query_metadata_must_be_complete",
            ),
            "recent_open_order_gate": _gate(
                False,
                "recent_open_orders_zero",
                "recent_open_orders_must_be_zero",
            ),
        }
    )
    return {
        **payload,
        **observation,
        "broker_error": broker_error,
        "error": "pre_submit_observation_gate_failed",
        "gates": gates,
        "message": message,
        "ok": False,
        "preview_only": True,
        "submitted": False,
    }


def _submit_paper_close_probe(
    config,
    payload: dict[str, object],
    *,
    broker,
    observe_post_submit: bool = False,
) -> dict[str, object]:
    request_payload = payload.get("proposed_order_request")
    if broker is None or not isinstance(request_payload, dict):
        return {
            **payload,
            "broker_error": True,
            "broker_result_classification": "ambiguous",
            "error": "paper_close_probe_submit_failed",
            "message": "missing_close_order_request",
            "ok": False,
            "preview_only": False,
            "submitted": False,
        }

    try:
        request = _paper_order_request(
            str(request_payload["symbol"]),
            asset_class=str(payload.get("asset_class", "crypto")),
            client_order_id=str(
                request_payload.get(
                    "client_order_id",
                    _paper_close_probe_client_order_id(None),
                )
            ),
            quantity=Decimal(str(request_payload["qty"])),
            side="sell",
            time_in_force=str(request_payload.get("time_in_force", "gtc")),
        )
        from .risk.state import RiskVerdict
    except Exception as exc:
        redacted_message = _redact_config_secrets(str(exc), config)
        return {
            **payload,
            "broker_error": True,
            "broker_result_classification": "ambiguous",
            "error": "paper_close_probe_submit_failed",
            "error_type": exc.__class__.__name__,
            "message": redacted_message,
            "ok": False,
            "preview_only": False,
            "redacted_exception_message": redacted_message,
            "submitted": False,
            "submit_attempted": False,
        }

    try:
        result = broker.submit_order_request(
            request,
            risk_verdict=RiskVerdict(
                allowed=True,
                reason="explicit_btcusd_paper_close_probe",
                detail="quantity_close",
            ),
        )
    except Exception as exc:
        redacted_message = _redact_config_secrets(str(exc), config)
        from .execution.alpaca_translator import AlpacaTranslationError

        if isinstance(exc, AlpacaTranslationError):
            post_submit_observation = (
                _paper_post_submit_observation(broker, config)
                if observe_post_submit
                else {}
            )
            return {
                **payload,
                "accepted": None,
                "broker_error": True,
                "broker_response_parsed": False,
                "broker_response_received": True,
                "broker_result_classification": "ambiguous",
                "error": "broker_response_parse_failed",
                "error_type": exc.__class__.__name__,
                "filled": None,
                "message": redacted_message,
                "ok": False,
                "preview_only": False,
                "redacted_exception_message": redacted_message,
                "submitted": True,
                "submit_attempted": True,
                **post_submit_observation,
            }

        return {
            **payload,
            "accepted": None,
            "broker_error": True,
            "broker_response_parsed": False,
            "broker_response_received": False,
            "broker_result_classification": "ambiguous",
            "error": "paper_close_probe_submit_failed",
            "error_type": exc.__class__.__name__,
            "filled": None,
            "message": redacted_message,
            "ok": False,
            "preview_only": False,
            "redacted_exception_message": redacted_message,
            "submitted": None,
            "submit_attempted": True,
            **_paper_submit_error_diagnostic_fields(exc),
        }

    post_submit_observation = (
        _paper_post_submit_observation(broker, config)
        if observe_post_submit
        else {}
    )
    broker_result = _paper_order_broker_result_payload(result)
    return {
        **payload,
        "accepted": result.accepted,
        "broker_normalized_status": broker_result["normalized_status"],
        "broker_raw_reason": broker_result["raw_reason"],
        "broker_raw_status": broker_result["raw_status"],
        "broker_response_parsed": True,
        "broker_response_received": True,
        "broker_result": broker_result,
        "broker_result_classification": (
            "accepted" if result.accepted else "rejected"
        ),
        "error": "" if result.accepted else "paper_close_probe_rejected",
        "filled": result.filled,
        "mutated": True,
        "normalized_status": broker_result["normalized_status"],
        "ok": result.accepted,
        "preview_only": False,
        "raw_reason": broker_result["raw_reason"],
        "raw_status": broker_result["raw_status"],
        "submitted": True,
        "submit_attempted": True,
        **post_submit_observation,
    }


def _build_paper_order_probe_payload(
    config,
    args: argparse.Namespace,
) -> dict[str, object]:
    policy = paper_order_policy_for_asset_class(args.asset_class)
    symbol = args.symbol.strip().upper()
    side = args.side.strip().lower()
    has_qty_arg = args.qty is not None
    has_notional_arg = args.notional is not None
    quantity, quantity_error = (
        _positive_whole_decimal(args.qty, "qty")
        if has_qty_arg
        else (None, "")
    )
    notional, notional_error = (
        _positive_decimal(args.notional, "notional")
        if has_notional_arg
        else (None, "")
    )
    max_notional, max_notional_error = _positive_decimal(
        args.max_notional,
        "max_notional",
    )
    sizing_mode = _paper_order_sizing_mode(has_qty_arg, has_notional_arg)
    submit_requested = bool(args.submit and args.i_mean_it)

    profile_gate = _paper_profile_gate(config)
    halt_gate = _gate(
        _paper_halt_not_set(),
        "halt_not_set",
        "ALGOTRADER_PAPER_HALT=1",
    )
    allowlist_gate = _gate(
        policy.allows_symbol(symbol),
        policy.allowlist_detail(symbol),
        "symbol_not_allowlisted",
    )
    side_gate = _gate(side == "buy", "buy_only", "side_must_be_buy")
    sizing_gate = _gate(
        sizing_mode in policy.allowed_sizing_modes,
        sizing_mode,
        policy.sizing_failure_detail(),
    )
    quantity_passes = sizing_mode != "qty" or quantity is not None
    if quantity_passes and sizing_mode == "qty" and policy.required_qty is not None:
        quantity_passes = quantity == policy.required_qty
    quantity_gate = _gate(
        quantity_passes,
        policy.quantity_detail(sizing_mode),
        policy.quantity_failure_detail(quantity_error),
    )
    notional_value_gate = _gate(
        sizing_mode != "notional" or notional is not None,
        "positive_notional",
        notional_error or "invalid_notional",
    )
    notional_min_gate = _gate(
        sizing_mode != "notional"
        or policy.min_notional is None
        or (notional is not None and notional >= policy.min_notional),
        policy.notional_minimum_detail(),
        policy.notional_minimum_failure_detail(),
    )
    notional_cap_gate = _gate(
        max_notional is not None
        and (
            policy.max_notional_cap is None
            or max_notional <= policy.max_notional_cap
        ),
        policy.notional_cap_detail(),
        max_notional_error or "max_notional_cap_exceeded",
    )
    if notional_cap_gate["passed"] and sizing_mode == "notional":
        notional_cap_gate = _gate(
            notional is not None and max_notional is not None and notional <= max_notional,
            "notional_within_max_notional",
            "notional_exceeds_max_notional",
        )
    submit_confirmation_gate = _gate(
        _paper_order_submit_confirmation_passes(
            submit_flag=bool(args.submit),
            i_mean_it_flag=bool(args.i_mean_it),
            sizing_mode=sizing_mode,
            policy=policy,
        ),
        _paper_order_submit_confirmation_detail(
            submit_flag=bool(args.submit),
            i_mean_it_flag=bool(args.i_mean_it),
            sizing_mode=sizing_mode,
            policy=policy,
        ),
        _paper_order_submit_confirmation_failure_detail(
            submit_flag=bool(args.submit),
            i_mean_it_flag=bool(args.i_mean_it),
            sizing_mode=sizing_mode,
            policy=policy,
        ),
    )
    gates = {
        "profile_gate": profile_gate,
        "halt_gate": halt_gate,
        "allowlist_gate": allowlist_gate,
        "side_gate": side_gate,
        "sizing_gate": sizing_gate,
        "quantity_gate": quantity_gate,
        "notional_value_gate": notional_value_gate,
        "notional_min_gate": notional_min_gate,
        "notional_cap_gate": notional_cap_gate,
        "submit_confirmation_gate": submit_confirmation_gate,
    }
    ok = all(bool(gate["passed"]) for gate in gates.values())

    request_payload = None
    if (
        symbol
        and side == "buy"
        and sizing_mode in policy.allowed_sizing_modes
        and (sizing_mode != "qty" or quantity_passes)
    ):
        try:
            request = _paper_order_request(
                symbol,
                asset_class=policy.asset_class,
                client_order_id=_paper_order_client_order_id(args.run_id),
                quantity=quantity if sizing_mode == "qty" else None,
                notional=notional if sizing_mode == "notional" else None,
                time_in_force=policy.time_in_force,
            )
            request_payload = _paper_order_request_payload(request)
        except ValueError:
            request_payload = None

    return {
        "asset_class": policy.asset_class,
        "command": "paper-order-probe",
        "error": "" if ok else _first_failed_gate(gates),
        "gates": gates,
        "max_notional": (
            _decimal_text(max_notional) if max_notional is not None else args.max_notional
        ),
        "ok": ok,
        "preview_only": not submit_requested or not policy.submit_enabled,
        "proposed_order_request": request_payload,
        "requested_i_mean_it": bool(args.i_mean_it),
        "requested_notional": _decimal_text(notional) if notional is not None else "",
        "requested_qty": _decimal_text(quantity) if quantity is not None else "",
        "requested_submit": bool(args.submit),
        "sizing_mode": sizing_mode,
        "accepted": None,
        "broker_normalized_status": "",
        "broker_raw_reason": "",
        "broker_raw_status": "",
        "broker_response_parsed": False,
        "broker_response_received": False,
        "filled": None,
        "market_session_note": policy.market_session_note,
        "min_notional": (
            _decimal_text(policy.min_notional) if policy.min_notional is not None else ""
        ),
        "normalized_status": "",
        "notional": _decimal_text(notional) if notional is not None else "",
        "order_type": "market",
        "raw_reason": "",
        "raw_status": "",
        "side": side,
        "submitted": False,
        "submission_disabled_reason": _paper_order_submission_disabled_reason(
            policy,
            sizing_mode,
        ),
        "submit_attempted": False,
        "submit_requested": submit_requested,
        "symbol": symbol,
        "time_in_force": policy.time_in_force,
    }


def _submit_paper_order_probe(
    config,
    payload: dict[str, object],
    *,
    observe_post_submit: bool = False,
) -> dict[str, object]:
    if payload.get("asset_class") not in {
        _PAPER_ORDER_ASSET_CLASS_EQUITY,
        _PAPER_ORDER_ASSET_CLASS_CRYPTO,
    }:
        return {
            **payload,
            "error": "paper_order_probe_submit_disabled",
            "message": str(payload.get("submission_disabled_reason", "")),
            "ok": False,
            "preview_only": True,
            "submitted": False,
            "submit_attempted": False,
        }

    request_payload = payload.get("proposed_order_request")
    if not isinstance(request_payload, dict):
        return {
            **payload,
            "broker_error": True,
            "error": "paper_order_probe_submit_failed",
            "message": "missing_notional_order_request",
            "ok": False,
            "preview_only": False,
            "submitted": False,
        }

    try:
        request = _paper_order_request(
            str(request_payload["symbol"]),
            asset_class=str(payload.get("asset_class", "equity")),
            client_order_id=str(
                request_payload.get(
                    "client_order_id",
                    _PAPER_ORDER_PROBE_CLIENT_ORDER_ID,
                )
            ),
            notional=Decimal(str(request_payload["notional"])),
            time_in_force=str(request_payload.get("time_in_force", "day")),
        )
        broker = _build_paper_broker(config.alpaca_paper)

        from .risk.state import RiskVerdict
    except Exception as exc:
        redacted_message = _redact_config_secrets(str(exc), config)
        return {
            **payload,
            "broker_error": True,
            "error": "paper_order_probe_submit_failed",
            "error_type": exc.__class__.__name__,
            "message": redacted_message,
            "redacted_exception_message": redacted_message,
            "ok": False,
            "preview_only": False,
            "submitted": False,
            "submit_attempted": False,
        }

    try:
        result = broker.submit_order_request(
            request,
            risk_verdict=RiskVerdict.allow(order_notional=request.notional),
        )
    except Exception as exc:
        redacted_message = _redact_config_secrets(str(exc), config)
        from .execution.alpaca_translator import AlpacaTranslationError

        if isinstance(exc, AlpacaTranslationError):
            post_submit_observation = (
                _paper_post_submit_observation(broker, config)
                if observe_post_submit
                else {}
            )
            return {
                **payload,
                "accepted": None,
                "broker_error": True,
                "broker_response_parsed": False,
                "broker_response_received": True,
                "error": "broker_response_parse_failed",
                "error_type": exc.__class__.__name__,
                "filled": None,
                "message": redacted_message,
                "ok": False,
                "preview_only": False,
                "redacted_exception_message": redacted_message,
                "submitted": True,
                "submit_attempted": True,
                **post_submit_observation,
            }

        return {
            **payload,
            "accepted": None,
            "broker_error": True,
            "broker_response_parsed": False,
            "broker_response_received": False,
            "error": "paper_order_probe_submit_failed",
            "error_type": exc.__class__.__name__,
            "filled": None,
            "message": redacted_message,
            "ok": False,
            "preview_only": False,
            "redacted_exception_message": redacted_message,
            "submitted": None,
            "submit_attempted": True,
            **_paper_submit_error_diagnostic_fields(exc),
        }

    post_submit_observation = (
        _paper_post_submit_observation(broker, config)
        if observe_post_submit
        else {}
    )
    broker_result = _paper_order_broker_result_payload(result)
    return {
        **payload,
        "accepted": result.accepted,
        "broker_normalized_status": broker_result["normalized_status"],
        "broker_raw_reason": broker_result["raw_reason"],
        "broker_raw_status": broker_result["raw_status"],
        "broker_response_parsed": True,
        "broker_response_received": True,
        "broker_result": broker_result,
        "error": "" if result.accepted else "paper_order_probe_rejected",
        "filled": result.filled,
        "normalized_status": broker_result["normalized_status"],
        "ok": result.accepted,
        "preview_only": False,
        "raw_reason": broker_result["raw_reason"],
        "raw_status": broker_result["raw_status"],
        "submitted": True,
        "submit_attempted": True,
        **post_submit_observation,
    }


def _paper_order_broker_result_payload(result) -> dict[str, object]:  # noqa: ANN001
    from .execution.alpaca_mapper import broker_order_result_receipt_metadata

    metadata = broker_order_result_receipt_metadata(result)
    normalized_status = metadata["normalized_status"]
    raw_reason = metadata["raw_reason"]
    raw_status = metadata["raw_status"]
    return {
        "accepted": result.accepted,
        "normalized_status": normalized_status,
        "raw_reason": raw_reason,
        "raw_status": raw_status,
        "reason": result.reason,
    }


def _paper_order_broker_receipt_metadata_payload(result) -> dict[str, str]:  # noqa: ANN001
    from .execution.alpaca_mapper import broker_order_result_receipt_metadata

    metadata = broker_order_result_receipt_metadata(result)
    return {
        "client_order_id": metadata.get("client_order_id", ""),
        "filled_average_price": metadata.get("filled_average_price", ""),
        "filled_quantity": metadata.get("filled_quantity", ""),
        "order_id": metadata.get("order_id", ""),
        "quantity": metadata.get("quantity", ""),
    }


def _paper_order_request(
    symbol: str,
    *,
    asset_class: str = "equity",
    client_order_id: str = _PAPER_ORDER_PROBE_CLIENT_ORDER_ID,
    quantity: Decimal | None = None,
    notional: Decimal | None = None,
    side: str = "buy",
    time_in_force: str = "day",
):
    from .execution.alpaca_client import AlpacaOrderRequest

    return AlpacaOrderRequest(
        client_order_id=client_order_id,
        symbol=symbol,
        side=side,
        asset_class=asset_class,
        qty=quantity,
        notional=notional,
        order_type="market",
        time_in_force=time_in_force,
    )


def _paper_order_request_payload(request) -> dict[str, str]:
    return {
        "asset_class": request.asset_class,
        "client_order_id": request.client_order_id,
        "limit_price": "",
        "notional": (
            _decimal_text(request.notional) if request.notional is not None else ""
        ),
        "order_type": request.order_type,
        "qty": _decimal_text(request.qty) if request.qty is not None else "",
        "request_model": "AlpacaOrderRequest",
        "side": request.side,
        "symbol": request.symbol,
        "time_in_force": request.time_in_force,
    }


def _paper_order_client_order_id(run_id: str | None) -> str:
    if run_id is None or not str(run_id).strip():
        return _PAPER_ORDER_PROBE_CLIENT_ORDER_ID

    safe_run_id = _paper_lab_run_id(run_id)[:_PAPER_ORDER_PROBE_CLIENT_ORDER_ID_RUN_ID_LENGTH]
    safe_run_id = safe_run_id.strip("._:-")
    if not safe_run_id:
        return _PAPER_ORDER_PROBE_CLIENT_ORDER_ID

    return f"{_PAPER_ORDER_PROBE_CLIENT_ORDER_ID_PREFIX}-{safe_run_id}"


def _paper_close_probe_client_order_id(run_id: str | None) -> str:
    safe_run_id = (
        _paper_lab_run_id(run_id)[:_PAPER_ORDER_PROBE_CLIENT_ORDER_ID_RUN_ID_LENGTH]
        if run_id is not None and str(run_id).strip()
        else "manual"
    )
    safe_run_id = safe_run_id.strip("._:-") or "manual"
    return f"{_PAPER_CLOSE_PROBE_CLIENT_ORDER_ID_PREFIX}-{safe_run_id}"


def _paper_profile_gate(config) -> dict[str, object]:
    from .config import ConfigValidationError, require_paper_profile

    try:
        require_paper_profile(config.alpaca_paper)
    except ConfigValidationError as exc:
        return _gate(False, "paper_profile_ready", _redact_config_secrets(str(exc), config))

    return _gate(True, "paper_profile_ready", "")


def _build_paper_broker(paper_config):
    from .execution.alpaca_adapter import AlpacaClientAdapter
    from .execution.alpaca_broker import AlpacaPaperBroker
    from .execution.alpaca_sdk_client import AlpacaSdkClient

    client = AlpacaSdkClient(paper_config)
    adapter = AlpacaClientAdapter(client)
    return AlpacaPaperBroker(adapter=adapter, config=paper_config)


def _paper_halt_not_set() -> bool:
    import os

    return os.environ.get("ALGOTRADER_PAPER_HALT") != "1"


def _paper_order_sizing_mode(has_qty_arg: bool, has_notional_arg: bool) -> str:
    if has_qty_arg and has_notional_arg:
        return "both_qty_and_notional"
    if not has_qty_arg and not has_notional_arg:
        return "missing_qty_or_notional"
    if has_notional_arg:
        return "notional"

    return "qty"


def _paper_order_submit_confirmation_passes(
    *,
    submit_flag: bool,
    i_mean_it_flag: bool,
    sizing_mode: str,
    policy,
) -> bool:
    if policy.asset_class == _PAPER_ORDER_ASSET_CLASS_OPTION:
        return False
    if not submit_flag and not i_mean_it_flag:
        return True
    if submit_flag and i_mean_it_flag and not policy.submit_enabled:
        return False
    if submit_flag and i_mean_it_flag and sizing_mode == "notional":
        return True

    return False


def _paper_order_submit_confirmation_detail(
    *,
    submit_flag: bool,
    i_mean_it_flag: bool,
    sizing_mode: str,
    policy,
) -> str:
    if policy.asset_class == _PAPER_ORDER_ASSET_CLASS_OPTION:
        return ""
    if not submit_flag and not i_mean_it_flag:
        return "preview_only_no_submission_requested"
    if submit_flag and i_mean_it_flag and not policy.submit_enabled:
        return ""
    if submit_flag and i_mean_it_flag and sizing_mode == "notional":
        return "explicit_notional_submit_confirmed"

    return ""


def _paper_order_submit_confirmation_failure_detail(
    *,
    submit_flag: bool,
    i_mean_it_flag: bool,
    sizing_mode: str,
    policy,
) -> str:
    if policy.asset_class == _PAPER_ORDER_ASSET_CLASS_OPTION:
        return policy.submit_disabled_reason
    if submit_flag and i_mean_it_flag and not policy.submit_enabled:
        return policy.submit_disabled_reason
    if submit_flag and i_mean_it_flag and sizing_mode == "qty":
        return _PAPER_ORDER_PROBE_QTY_DISABLED_REASON

    return "submit_requires_submit_and_i_mean_it"


def _paper_close_submit_confirmation_gate(
    *,
    submit_flag: bool,
    i_mean_it_flag: bool,
) -> dict[str, object]:
    if not submit_flag and not i_mean_it_flag:
        return _gate(
            True,
            "preview_only_no_submission_requested",
            "",
        )
    if submit_flag and i_mean_it_flag:
        return _gate(
            True,
            "explicit_close_submit_confirmed",
            "",
        )

    return _gate(
        False,
        "",
        "submit_requires_submit_and_i_mean_it",
    )


def _paper_order_submission_disabled_reason(policy, sizing_mode: str) -> str:
    if not policy.submit_enabled:
        return policy.submit_disabled_reason
    if sizing_mode == "qty":
        return _PAPER_ORDER_PROBE_QTY_DISABLED_REASON

    return ""


def _positive_decimal(
    raw_value: str,
    field_name: str,
) -> tuple[Decimal | None, str]:
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, ValueError):
        return None, f"{field_name}_must_be_decimal"

    if value <= 0:
        return None, f"{field_name}_must_be_positive"

    return value, ""


def _optional_decimal_value(raw_value: object) -> Decimal | None:
    if raw_value in (None, ""):
        return None
    try:
        return Decimal(str(raw_value))
    except (InvalidOperation, ValueError):
        return None


def _positive_whole_decimal(
    raw_value: str,
    field_name: str,
) -> tuple[Decimal | None, str]:
    value, error = _positive_decimal(raw_value, field_name)
    if value is None:
        return None, error

    if value != value.to_integral_value():
        return None, f"{field_name}_must_be_whole_shares"

    return value, ""


def _gate(
    passed: bool,
    detail: str,
    failure_detail: str,
) -> dict[str, object]:
    return {
        "detail": detail if passed else failure_detail,
        "passed": passed,
    }


def _first_failed_gate(gates: dict[str, dict[str, object]]) -> str:
    for gate_name in _PAPER_SAFETY_GATE_ORDER:
        gate = gates[gate_name]
        if not gate["passed"]:
            return f"{gate_name}_failed"

    return ""


def _first_failed_close_gate(gates: dict[str, dict[str, object]]) -> str:
    for gate_name in _PAPER_CLOSE_PROBE_GATE_ORDER:
        gate = gates[gate_name]
        if not gate["passed"]:
            return f"{gate_name}_failed"

    return ""


def _render_paper_account_payload(
    payload: dict[str, object],
    output_format: str,
) -> str:
    if output_format == "json":
        return _compact_json(payload)

    lines = [
        "Paper account smoke",
        f"ok: {_bool_text(payload['ok'])}",
        f"submitted: {_bool_text(payload['submitted'])}",
    ]
    if payload.get("error"):
        lines.append(f"error: {payload['error']}")
    if payload.get("message"):
        lines.append(f"message: {payload['message']}")
    lines.extend(_gate_lines(payload["gates"]))
    account = payload.get("account")
    if isinstance(account, dict):
        lines.append(f"account_cash: {account['cash']} {account['currency']}")
    lines.append(f"position_count: {payload['position_count']}")
    for position in payload["positions"]:
        lines.append(
            "position: "
            f"{position['symbol']} qty={position['quantity']} "
            f"average_price={position['average_price']}"
        )
    return "\n".join(lines)


def _render_paper_lab_snapshot_payload(
    payload: dict[str, object],
    output_format: str,
) -> str:
    if output_format == "json":
        return _compact_json(payload)

    lines = [
        "Paper lab snapshot",
        f"ok: {_bool_text(payload['ok'])}",
        f"submitted: {_bool_text(payload['submitted'])}",
        f"mutated: {_bool_text(payload['mutated'])}",
    ]
    if payload.get("error"):
        lines.append(f"error: {payload['error']}")
    lines.extend(_gate_lines(payload["gates"]))
    lines.append(
        "account_observation_available: "
        f"{_bool_text(payload['account_observation_available'])}"
    )
    lines.append(
        "positions_observation_available: "
        f"{_bool_text(payload['positions_observation_available'])}"
    )
    lines.append(
        "orders_observation_available: "
        f"{_bool_text(payload['orders_observation_available'])}"
    )
    lines.append(
        "recent_order_query_attempted: "
        f"{_bool_text(payload['recent_order_query_attempted'])}"
    )
    lines.append(
        "recent_order_query_available: "
        f"{_bool_text(payload['recent_order_query_available'])}"
    )
    lines.append(f"recent_order_query_limit: {payload['recent_order_query_limit']}")
    lines.append(
        "recent_order_query_status_filter: "
        f"{payload['recent_order_query_status_filter']}"
    )
    lines.append(
        "recent_order_query_asset_class_filter: "
        f"{payload['recent_order_query_asset_class_filter']}"
    )
    lines.append(
        "recent_order_query_symbol_filter: "
        f"{payload['recent_order_query_symbol_filter']}"
    )
    lines.append(
        "recent_order_query_side_filter: "
        f"{payload['recent_order_query_side_filter']}"
    )
    lines.append(f"recent_order_query_after: {payload['recent_order_query_after']}")
    lines.append(f"recent_order_query_until: {payload['recent_order_query_until']}")
    lines.append(f"recent_order_query_sort: {payload['recent_order_query_sort']}")
    lines.append(
        "recent_order_query_direction: "
        f"{payload['recent_order_query_direction']}"
    )
    lines.append(
        "recent_order_query_nested: "
        f"{_optional_bool_text(payload['recent_order_query_nested'])}"
    )
    lines.append(
        "recent_order_query_source: "
        f"{payload['recent_order_query_source']}"
    )
    lines.append(
        "recent_order_query_contract_version: "
        f"{payload['recent_order_query_contract_version']}"
    )
    lines.append(
        "recent_order_query_returned_count: "
        f"{payload['recent_order_query_returned_count']}"
    )
    lines.append(
        "recent_order_query_metadata_complete: "
        f"{_bool_text(payload['recent_order_query_metadata_complete'])}"
    )
    lines.append(
        "recent_order_query_metadata_missing_fields: "
        f"{','.join(payload['recent_order_query_metadata_missing_fields'])}"
    )
    account = payload.get("account")
    if isinstance(account, dict):
        lines.append(f"account_cash: {account['cash']} {account['currency']}")
    lines.append(f"position_count: {payload['position_count']}")
    lines.append(f"position_symbols: {','.join(payload['position_symbols'])}")
    lines.append(f"recent_order_count: {payload['recent_order_count']}")
    for order in payload["recent_orders"]:
        lines.append(
            "recent_order: "
            f"{order['symbol']} {order['side']} "
            f"{order['normalized_status']} qty={order['quantity']} "
            f"notional={order['notional']}"
        )
    if payload.get("unavailable_observations"):
        lines.append(
            "unavailable_observations: "
            f"{','.join(payload['unavailable_observations'])}"
        )
    return "\n".join(lines)


def _render_paper_lab_order_traceability_review_payload(
    payload: dict[str, object],
    output_format: str,
) -> str:
    if output_format == "json":
        return _compact_json(payload)

    lines = [
        "Paper lab order traceability review",
        f"review_state: {payload['review_state']}",
        f"ok: {_bool_text(payload['ok'])}",
        f"submitted: {_bool_text(payload['submitted'])}",
        f"mutated: {_bool_text(payload['mutated'])}",
        f"symbol: {payload['symbol']}",
    ]
    if payload.get("error"):
        lines.append(f"error: {payload['error']}")
    lines.extend(_gate_lines(payload["gates"]))
    lines.append(
        "account_observation_available: "
        f"{_bool_text(payload['account_observation_available'])}"
    )
    lines.append(
        "positions_observation_available: "
        f"{_bool_text(payload['positions_observation_available'])}"
    )
    lines.append(
        "order_traceability_observation_available: "
        f"{_bool_text(payload['order_traceability_observation_available'])}"
    )
    lines.append(
        "source_m351_evidence_available: "
        f"{_bool_text(payload['source_m351_evidence_available'])}"
    )
    lines.append(
        "source_m352_evidence_available: "
        f"{_bool_text(payload['source_m352_evidence_available'])}"
    )
    lines.append(
        f"spy_position_observed: {_bool_text(payload['spy_position_observed'])}"
    )
    lines.append(f"spy_quantity: {payload['spy_quantity']}")
    lines.append(f"spy_average_price: {payload['spy_average_price']}")
    lines.append(f"recent_open_order_count: {payload['recent_open_order_count']}")
    lines.append(f"recent_all_order_count: {payload['recent_all_order_count']}")
    lines.append(f"recent_closed_order_count: {payload['recent_closed_order_count']}")
    lines.append(f"recent_filled_order_count: {payload['recent_filled_order_count']}")
    lines.append(
        "recent_order_query_metadata_complete: "
        f"{_bool_text(payload['recent_order_query_metadata_complete'])}"
    )
    lines.append(
        "recent_order_query_metadata_missing_fields: "
        f"{','.join(payload['recent_order_query_metadata_missing_fields'])}"
    )
    lines.append(
        f"filled_spy_order_found: {_bool_text(payload['filled_spy_order_found'])}"
    )
    lines.append(
        f"broker_order_id_exposed: {_bool_text(payload['broker_order_id_exposed'])}"
    )
    lines.append(
        f"client_order_id_exposed: {_bool_text(payload['client_order_id_exposed'])}"
    )
    lines.append(f"m351_correlation_basis: {payload['m351_correlation_basis']}")
    if payload.get("traceability_gap"):
        lines.append(f"traceability_gap: {payload['traceability_gap']}")
    if payload.get("unavailable_observations"):
        lines.append(
            "unavailable_observations: "
            f"{','.join(payload['unavailable_observations'])}"
        )
    lines.append(
        "recommended_next_operator_action: "
        f"{payload['recommended_next_operator_action']}"
    )
    return "\n".join(lines)


def _render_paper_lab_spy_close_preview_payload(
    payload: dict[str, object],
    output_format: str,
) -> str:
    if output_format == "json":
        return _compact_json(payload)

    m353_summary = _payload_mapping(payload.get("m353_traceability_summary"))
    lines = [
        "SPY paper cleanup close preview",
        f"run_id: {payload['run_id']}",
        f"state: {payload['state']}",
        f"ok: {_bool_text(payload['ok'])}",
        f"mutated: {_bool_text(payload['mutated'])}",
        f"submitted: {_bool_text(payload['submitted'])}",
        "broker_action_performed: "
        f"{_bool_text(payload['broker_action_performed'])}",
        f"close_order_submitted: {_bool_text(payload['close_order_submitted'])}",
        f"live_authorized: {_bool_text(payload['live_authorized'])}",
        f"asset_class: {payload['asset_class']}",
        f"symbol: {payload['symbol']}",
        f"side: {payload['side']}",
        f"order_type: {payload['order_type']}",
        f"time_in_force: {payload['time_in_force']}",
        f"quantity: {payload['quantity']}",
        f"observed_spy_quantity: {payload['observed_spy_quantity']}",
        f"observed_spy_average_price: {payload['observed_spy_average_price']}",
        f"account_cash: {payload['account_cash']} {payload['account_currency']}".strip(),
        f"recent_open_order_count: {payload['recent_open_order_count']}",
        f"m353_evidence_available: {_bool_text(payload['m353_evidence_available'])}",
        f"m353_ready: {_bool_text(payload['m353_ready'])}",
        f"m353_state: {m353_summary.get('review_state', '')}",
        (
            "m353_recent_all_spy_buy_order_count: "
            f"{m353_summary.get('recent_all_spy_buy_order_count', 0)}"
        ),
        (
            "m353_recent_closed_spy_buy_order_count: "
            f"{m353_summary.get('recent_closed_spy_buy_order_count', 0)}"
        ),
        (
            "m353_recent_filled_spy_buy_order_count: "
            f"{m353_summary.get('recent_filled_spy_buy_order_count', 0)}"
        ),
        f"m351_correlation_basis: {payload['m351_correlation_basis']}",
        f"m351_client_order_id: {payload['m351_client_order_id']}",
        f"max_cleanup_quantity: {payload['max_cleanup_quantity']}",
        "stale_evidence_blockers: "
        f"{','.join(payload['stale_evidence_blockers']) or 'none'}",
        "open_order_blockers: "
        f"{','.join(payload['open_order_blockers']) or 'none'}",
        "unexpected_position_blockers: "
        f"{','.join(payload['unexpected_position_blockers']) or 'none'}",
        "unavailable_observation_blockers: "
        f"{','.join(payload['unavailable_observation_blockers']) or 'none'}",
        f"blockers: {','.join(payload['blockers']) or 'none'}",
        f"final_operator_instruction: {payload['final_operator_instruction']}",
    ]
    return "\n".join(lines)


def _render_paper_close_preview_payload(
    payload: dict[str, object],
    output_format: str,
) -> str:
    if output_format == "json":
        return _compact_json(payload)

    lines = [
        "Paper close preview",
        f"command: {payload['command']}",
        f"ok: {_bool_text(payload['ok'])}",
        f"preview_only: {_bool_text(payload['preview_only'])}",
        f"submitted: {_optional_bool_text(payload['submitted'])}",
        f"mutated: {_optional_bool_text(payload['mutated'])}",
        f"paper_lab_only: {_bool_text(payload['paper_lab_only'])}",
        f"not_live_authorized: {_bool_text(payload['not_live_authorized'])}",
        f"profit_claim: {payload['profit_claim']}",
        f"manual_review_required: {_bool_text(payload['manual_review_required'])}",
        f"asset_class: {payload['asset_class']}",
        f"symbol: {payload['symbol']}",
        f"side: {payload['side']}",
        f"order_type: {payload['order_type']}",
        f"time_in_force: {payload['time_in_force']}",
        f"observed_position_quantity: {payload['observed_position_quantity']}",
        f"requested_close_quantity: {payload['requested_close_quantity']}",
        (
            "remaining_quantity_after_preview: "
            f"{payload['remaining_quantity_after_preview']}"
        ),
        (
            "close_quantity_within_observed_position: "
            f"{_bool_text(payload['close_quantity_within_observed_position'])}"
        ),
        f"no_shorting_gate: {payload['no_shorting_gate']}",
        f"fresh_snapshot_required: {_bool_text(payload['fresh_snapshot_required'])}",
        f"fresh_snapshot_status: {payload['fresh_snapshot_status']}",
        (
            "recent_order_query_metadata_complete: "
            f"{_bool_text(payload['recent_order_query_metadata_complete'])}"
        ),
        f"submission_disabled_reason: {payload['submission_disabled_reason']}",
        (
            "recommended_next_operator_action: "
            f"{payload['recommended_next_operator_action']}"
        ),
    ]
    if payload.get("output_run_log"):
        lines.append(f"output_run_log: {payload['output_run_log']}")
        lines.append(f"output_run_id: {payload['output_run_id']}")
    lines.extend(_close_preview_gate_lines(payload["gates"]))
    return "\n".join(lines)


def _render_paper_order_probe_payload(
    payload: dict[str, object],
    output_format: str,
) -> str:
    if output_format == "json":
        return _compact_json(payload)

    lines = [
        "Paper order probe",
        f"asset_class: {payload['asset_class']}",
        f"ok: {_bool_text(payload['ok'])}",
        f"preview_only: {_bool_text(payload['preview_only'])}",
        f"submit_requested: {_bool_text(payload['submit_requested'])}",
        f"submit_attempted: {_bool_text(payload['submit_attempted'])}",
        "broker_response_received: "
        f"{_bool_text(payload['broker_response_received'])}",
        "broker_response_parsed: "
        f"{_bool_text(payload['broker_response_parsed'])}",
        f"submitted: {_bool_text(payload['submitted'])}",
        f"accepted: {_optional_bool_text(payload['accepted'])}",
        f"filled: {_optional_bool_text(payload['filled'])}",
    ]
    if payload.get("market_session_note"):
        lines.append(f"market_session_note: {payload['market_session_note']}")
    if payload.get("error"):
        lines.append(f"error: {payload['error']}")
    lines.extend(_gate_lines(payload["gates"]))
    request = payload.get("proposed_order_request")
    if isinstance(request, dict):
        lines.extend(
            [
                f"request_model: {request['request_model']}",
                f"symbol: {request['symbol']}",
                f"side: {request['side']}",
                f"qty: {request['qty']}",
                f"notional: {request['notional']}",
                f"order_type: {request['order_type']}",
                f"time_in_force: {request['time_in_force']}",
                f"client_order_id: {request['client_order_id']}",
            ]
        )
    lines.append(f"requested_notional: {payload['requested_notional']}")
    if payload.get("min_notional"):
        lines.append(f"min_notional: {payload['min_notional']}")
    lines.append(f"max_notional: {payload['max_notional']}")
    if payload.get("broker_result"):
        broker_result = payload["broker_result"]
        lines.append(f"broker_accepted: {_bool_text(broker_result['accepted'])}")
        lines.append(f"broker_reason: {broker_result['reason']}")
        lines.append(f"broker_normalized_status: {broker_result['normalized_status']}")
        lines.append(f"broker_raw_status: {broker_result['raw_status']}")
        lines.append(f"broker_raw_reason: {broker_result['raw_reason']}")
    if payload.get("message"):
        lines.append(f"message: {payload['message']}")
    if payload.get("submission_disabled_reason"):
        lines.append(
            f"submission_disabled_reason: {payload['submission_disabled_reason']}"
        )
    return "\n".join(lines)


def _render_paper_close_probe_payload(
    payload: dict[str, object],
    output_format: str,
) -> str:
    if output_format == "json":
        return _compact_json(payload)

    lines = [
        "Paper close probe",
        f"ok: {_bool_text(payload['ok'])}",
        f"preview_only: {_bool_text(payload['preview_only'])}",
        f"submit_requested: {_bool_text(payload['submit_requested'])}",
        f"submit_attempted: {_bool_text(payload['submit_attempted'])}",
        "broker_response_received: "
        f"{_bool_text(payload['broker_response_received'])}",
        "broker_response_parsed: "
        f"{_bool_text(payload['broker_response_parsed'])}",
        f"submitted: {_optional_bool_text(payload['submitted'])}",
        f"accepted: {_optional_bool_text(payload['accepted'])}",
        f"filled: {_optional_bool_text(payload['filled'])}",
        f"classification: {payload['broker_result_classification']}",
        f"asset_class: {payload['asset_class']}",
        f"symbol: {payload['symbol']}",
        f"side: {payload['side']}",
        f"quantity: {payload['requested_quantity']}",
        f"max_quantity: {payload['max_quantity']}",
        f"order_type: {payload['order_type']}",
        f"time_in_force: {payload['time_in_force']}",
    ]
    if payload.get("target_position_observed") is not None:
        lines.append(
            "target_position_observed: "
            f"{_bool_text(bool(payload['target_position_observed']))}"
        )
    if payload.get("target_position_quantity"):
        lines.append(
            f"target_position_quantity: {payload['target_position_quantity']}"
        )
    if payload.get("recent_order_count") is not None:
        lines.append(f"recent_order_count: {payload['recent_order_count']}")
    if payload.get("error"):
        lines.append(f"error: {payload['error']}")
    lines.extend(_close_probe_gate_lines(payload["gates"]))
    request = payload.get("proposed_order_request")
    if isinstance(request, dict):
        lines.extend(
            [
                f"request_model: {request['request_model']}",
                f"client_order_id: {request['client_order_id']}",
            ]
        )
    if payload.get("broker_result"):
        broker_result = payload["broker_result"]
        lines.append(f"broker_accepted: {_bool_text(broker_result['accepted'])}")
        lines.append(f"broker_reason: {broker_result['reason']}")
        lines.append(f"broker_normalized_status: {broker_result['normalized_status']}")
        lines.append(f"broker_raw_status: {broker_result['raw_status']}")
        lines.append(f"broker_raw_reason: {broker_result['raw_reason']}")
    if payload.get("message"):
        lines.append(f"message: {payload['message']}")
    return "\n".join(lines)


def _render_paper_lab_spy_close_submit_payload(
    payload: dict[str, object],
    output_format: str,
) -> str:
    if output_format == "json":
        return _compact_json(payload)

    lines = [
        "Paper lab SPY close submit",
        f"state: {payload['state']}",
        f"ok: {_bool_text(payload['ok'])}",
        f"paper_only: {_bool_text(payload['paper_only'])}",
        f"live_authorized: {_bool_text(payload['live_authorized'])}",
        f"submitted: {_optional_bool_text(payload['submitted'])}",
        f"broker_action_performed: {_bool_text(payload['broker_action_performed'])}",
        f"close_order_submitted: {_bool_text(payload['close_order_submitted'])}",
        f"submit_attempt_count: {payload['submit_attempt_count']}",
        f"client_order_id: {payload['client_order_id']}",
        f"asset_class: {payload['asset_class']}",
        f"symbol: {payload['symbol']}",
        f"side: {payload['side']}",
        f"quantity: {payload['requested_close_quantity']}",
        f"order_type: {payload['order_type']}",
        f"time_in_force: {payload['time_in_force']}",
        f"m354_state: {payload['m354_state']}",
        f"m354_requested_close_quantity: {payload['m354_requested_close_quantity']}",
        f"account_observed: {_bool_text(payload['account_observation_available'])}",
        f"positions_observed: {_bool_text(payload['positions_observation_available'])}",
        f"orders_observed: {_bool_text(payload['orders_observation_available'])}",
        f"spy_quantity: {payload['spy_quantity']}",
        f"recent_open_spy_order_count: {payload['recent_open_spy_order_count']}",
        "duplicate_m355_client_order_id_found: "
        f"{_bool_text(payload['duplicate_m355_client_order_id_found'])}",
        f"classification: {payload['broker_result_classification']}",
        f"accepted: {_optional_bool_text(payload['accepted'])}",
        f"filled: {_optional_bool_text(payload['filled'])}",
        f"normalized_status: {payload['normalized_status']}",
        f"raw_status: {payload['raw_status']}",
        f"broker_order_id: {payload['broker_order_id']}",
        f"filled_quantity: {payload['filled_quantity']}",
        f"filled_average_price: {payload['filled_average_price']}",
        f"post_submit_cash: {payload['post_submit_account_cash']}",
        f"post_close_remaining_quantity: {payload['post_close_remaining_quantity']}",
        "post_submit_recent_open_spy_order_count: "
        f"{payload['post_submit_recent_open_spy_order_count']}",
    ]
    if payload.get("error"):
        lines.append(f"error: {payload['error']}")
    lines.extend(_spy_close_submit_gate_lines(payload["gates"]))
    if payload.get("message"):
        lines.append(f"message: {payload['message']}")
    return "\n".join(lines)


def _spy_close_submit_gate_lines(gates: object) -> list[str]:
    if not isinstance(gates, dict):
        return []

    lines: list[str] = []
    for gate_name in _PAPER_SPY_CLOSE_SUBMIT_GATE_ORDER:
        if gate_name not in gates:
            continue
        gate = gates[gate_name]
        state = "passed" if gate["passed"] else "blocked"
        lines.append(f"{gate_name}: {state} - {gate['detail']}")
    return lines


def _close_probe_gate_lines(gates: object) -> list[str]:
    if not isinstance(gates, dict):
        return []

    lines: list[str] = []
    for gate_name in _PAPER_CLOSE_PROBE_GATE_ORDER:
        if gate_name not in gates:
            continue
        gate = gates[gate_name]
        state = "passed" if gate["passed"] else "blocked"
        lines.append(f"{gate_name}: {state} - {gate['detail']}")
    return lines


def _close_preview_gate_lines(gates: object) -> list[str]:
    if not isinstance(gates, dict):
        return []

    lines: list[str] = []
    for gate_name in _PAPER_CLOSE_PREVIEW_GATE_ORDER:
        if gate_name not in gates:
            continue
        gate = gates[gate_name]
        state = "passed" if gate["passed"] else "blocked"
        lines.append(f"{gate_name}: {state} - {gate['detail']}")
    return lines


def _gate_lines(gates: object) -> list[str]:
    if not isinstance(gates, dict):
        return []

    lines: list[str] = []
    for gate_name in _PAPER_SAFETY_GATE_ORDER:
        if gate_name not in gates:
            continue
        gate = gates[gate_name]
        state = "passed" if gate["passed"] else "blocked"
        lines.append(f"{gate_name}: {state} - {gate['detail']}")
    return lines


def _compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _decimal_text(value: Decimal) -> str:
    return str(value)


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"


def _optional_bool_text(value: object) -> str:
    if value is None:
        return "unknown"

    return _bool_text(value)


def _payload_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value

    return {}


def _payload_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()

    return tuple(str(item) for item in value if str(item))


def _int_payload_value(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _payload_bool_or_none(value: object) -> bool | None:
    if value is True:
        return True
    if value is False:
        return False
    return None


def _redact_config_secrets(message: str, config) -> str:
    redacted = message
    for value in _paper_lab_sensitive_values(config):
        if value:
            redacted = redacted.replace(value, "<redacted>")
    return redacted


def _paper_submit_error_diagnostic_fields(exc: Exception) -> dict[str, object]:
    diagnostics = getattr(exc, "diagnostics", None)
    if not isinstance(diagnostics, Mapping):
        return {}

    fields: dict[str, object] = {}
    for source_key, target_key in (
        ("submit_stage", "submit_error_stage"),
        ("exception_class", "submit_error_exception_class"),
        ("status_code", "submit_error_status_code"),
        ("alpaca_error_code", "submit_error_code"),
        ("sanitized_message", "submit_error_message"),
    ):
        value = diagnostics.get(source_key)
        if value not in (None, ""):
            fields[target_key] = value

    request_shape = diagnostics.get("request_shape")
    if isinstance(request_shape, Mapping):
        fields["submit_error_request_shape"] = {
            "asset_class": str(request_shape.get("asset_class", "")),
            "symbol": str(request_shape.get("symbol", "")),
            "side": str(request_shape.get("side", "")),
            "order_type": str(request_shape.get("order_type", "")),
            "time_in_force": str(request_shape.get("time_in_force", "")),
            "sizing_mode": str(request_shape.get("sizing_mode", "")),
        }

    return fields


def _paper_lab_sensitive_values(config) -> tuple[str | None, ...]:
    return (
        config.alpaca_paper.alpaca_api_key,
        config.alpaca_paper.alpaca_secret_key,
        config.alpaca_paper.alpaca_paper_base_url,
    )


def _paper_lab_run_id(run_id: str | None) -> str:
    from .execution.paper_lab_observation_log import resolve_run_id

    return resolve_run_id(run_id)


def _ensure_paper_lab_run_log(run_log_path: str) -> bool:
    from .execution.paper_lab_observation_log import (
        PaperLabRunLogError,
        ensure_run_log_path,
    )

    try:
        ensure_run_log_path(run_log_path)
    except PaperLabRunLogError as exc:
        print(str(exc), file=sys.stderr)
        return False

    return True


def _write_paper_account_run_log(
    run_log_path: str,
    run_id: str,
    payload: dict[str, object],
    config,
) -> bool:
    from .execution.paper_lab_observation_log import make_account_smoke_events

    events = make_account_smoke_events(
        run_id=run_id,
        payload=payload,
        secret_values=_paper_lab_sensitive_values(config),
    )
    return _append_paper_lab_run_log(run_log_path, events)


def _write_paper_lab_snapshot_run_log(
    run_log_path: str,
    run_id: str,
    payload: dict[str, object],
    config,
) -> bool:
    from .execution.paper_lab_observation_log import make_paper_lab_snapshot_events

    events = make_paper_lab_snapshot_events(
        run_id=run_id,
        payload=payload,
        secret_values=_paper_lab_sensitive_values(config),
    )
    return _append_paper_lab_run_log(run_log_path, events)


def _write_paper_lab_order_traceability_review_run_log(
    run_log_path: str,
    run_id: str,
    payload: dict[str, object],
    config,
) -> bool:
    from .execution.paper_lab_observation_log import (
        make_paper_lab_order_traceability_review_events,
    )

    events = make_paper_lab_order_traceability_review_events(
        run_id=run_id,
        payload=payload,
        secret_values=_paper_lab_sensitive_values(config),
    )
    return _append_paper_lab_run_log(run_log_path, events)


def _write_paper_lab_spy_close_preview_run_log(
    run_log_path: str,
    run_id: str,
    payload: dict[str, object],
    config,
) -> bool:
    from .execution.paper_lab_observation_log import (
        make_paper_lab_spy_close_preview_events,
    )

    events = make_paper_lab_spy_close_preview_events(
        run_id=run_id,
        payload=payload,
        secret_values=_paper_lab_sensitive_values(config),
    )
    return _append_paper_lab_run_log(run_log_path, events)


def _write_paper_lab_spy_close_submit_run_log(
    run_log_path: str,
    run_id: str,
    payload: dict[str, object],
    config,
) -> bool:
    from .execution.paper_lab_observation_log import (
        make_paper_lab_spy_close_submit_events,
    )

    events = make_paper_lab_spy_close_submit_events(
        run_id=run_id,
        payload=payload,
        secret_values=_paper_lab_sensitive_values(config),
    )
    return _append_paper_lab_run_log(run_log_path, events)


def _write_paper_close_preview_run_log(
    run_log_path: str,
    run_id: str,
    payload: dict[str, object],
) -> bool:
    from .execution.paper_lab_observation_log import make_paper_close_preview_events

    events = make_paper_close_preview_events(
        run_id=run_id,
        payload=payload,
    )
    return _append_paper_lab_run_log(run_log_path, events)


def _write_paper_order_initial_run_log(
    run_log_path: str,
    run_id: str,
    payload: dict[str, object],
    config,
) -> bool:
    from .execution.paper_lab_observation_log import make_order_probe_initial_events

    events = make_order_probe_initial_events(
        run_id=run_id,
        payload=payload,
        secret_values=_paper_lab_sensitive_values(config),
    )
    return _append_paper_lab_run_log(run_log_path, events)


def _write_paper_order_submit_run_log(
    run_log_path: str,
    run_id: str,
    payload: dict[str, object],
    config,
) -> bool:
    from .execution.paper_lab_observation_log import make_order_probe_submit_events

    events = make_order_probe_submit_events(
        run_id=run_id,
        payload=payload,
        secret_values=_paper_lab_sensitive_values(config),
    )
    return _append_paper_lab_run_log(run_log_path, events)


def _append_paper_lab_run_log(
    run_log_path: str,
    events: tuple[dict[str, object], ...],
) -> bool:
    from .execution.paper_lab_observation_log import (
        PaperLabRunLogError,
        append_jsonl_records,
    )

    try:
        append_jsonl_records(run_log_path, events)
    except PaperLabRunLogError as exc:
        print(str(exc), file=sys.stderr)
        return False

    return True


def _run_advisory_operating_brief_preview(output_format: str) -> int:
    from .research.advisory_operating_brief_cli import (
        render_advisory_operating_brief_preview,
    )

    print(render_advisory_operating_brief_preview(output_format), end="")
    return 0


def _run_advisory_operating_brief_content_bundle_preview(
    output_format: str,
    *,
    include_risk_authority: bool = False,
    include_research_queue: bool = False,
    include_sma_research_observation: bool = False,
    include_sma_research_summary_observation: bool = False,
    include_research_return_observation: bool = False,
    include_research_return_summary_observation: bool = False,
    include_research_data_source_readiness: bool = False,
    include_research_data_source_readiness_summary: bool = False,
    include_diagnostic_issues: bool = False,
    include_advisory_sections: bool = False,
) -> int:
    from .research.advisory_operating_brief_content_bundle_cli import (
        render_advisory_operating_brief_content_bundle_preview,
    )

    print(
        render_advisory_operating_brief_content_bundle_preview(
            output_format,
            include_risk_authority=include_risk_authority,
            include_research_queue=include_research_queue,
            include_sma_research_observation=include_sma_research_observation,
            include_sma_research_summary_observation=(
                include_sma_research_summary_observation
            ),
            include_research_return_observation=include_research_return_observation,
            include_research_return_summary_observation=(
                include_research_return_summary_observation
            ),
            include_research_data_source_readiness=(
                include_research_data_source_readiness
            ),
            include_research_data_source_readiness_summary=(
                include_research_data_source_readiness_summary
            ),
            include_diagnostic_issues=include_diagnostic_issues,
            include_advisory_sections=include_advisory_sections,
        ),
        end="",
    )
    return 0


def _run_advisory_operating_brief_package_preview(output_format: str) -> int:
    from .research.advisory_operating_brief_package_cli import (
        render_advisory_operating_brief_package_preview,
    )

    print(render_advisory_operating_brief_package_preview(output_format), end="")
    return 0


def _run_advisory_operating_brief_mvp_preview(output_format: str) -> int:
    from .research.advisory_operating_brief_mvp_report import (
        render_synthetic_advisory_operating_brief_mvp_report,
    )

    print(
        render_synthetic_advisory_operating_brief_mvp_report(output_format),
        end="",
    )
    return 0


def _load_runtime_config(profile: str | None):
    from .config import load_config

    return load_config(profile=profile)


def _preview_output_format(argv: tuple[str, ...]) -> str | None:
    return _preview_command_output_format(
        argv,
        "advisory-operating-brief-preview",
    )


def _content_bundle_preview_output_format(argv: tuple[str, ...]) -> str | None:
    options = _content_bundle_preview_options(argv)
    if options is None:
        return None

    return options[0]


def _package_preview_output_format(argv: tuple[str, ...]) -> str | None:
    return _preview_command_output_format(
        argv,
        "advisory-operating-brief-package-preview",
    )


def _mvp_preview_output_format(argv: tuple[str, ...]) -> str | None:
    return _preview_command_output_format(
        argv,
        "advisory-operating-brief-mvp-preview",
    )


def _content_bundle_preview_options(
    argv: tuple[str, ...],
) -> tuple[str, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool] | None:
    return _preview_command_options(
        argv,
        "advisory-operating-brief-content-bundle-preview",
        allowed_flags=(
            "--include-risk-authority",
            "--include-research-queue",
            "--include-sma-research-observation",
            "--include-sma-research-summary-observation",
            "--include-research-return-observation",
            "--include-research-return-summary-observation",
            "--include-research-data-source-readiness",
            "--include-research-data-source-readiness-summary",
            "--include-diagnostic-issues",
            "--include-advisory-sections",
        ),
    )


def _preview_command_output_format(
    argv: tuple[str, ...],
    command: str,
) -> str | None:
    options = _preview_command_options(argv, command)
    if options is None:
        return None

    return options[0]


def _preview_command_options(
    argv: tuple[str, ...],
    command: str,
    *,
    allowed_flags: tuple[str, ...] = (),
) -> tuple[str, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool] | None:
    if command not in argv:
        return None

    command_index = argv.index(command)
    if not _only_ignored_runtime_options(argv[:command_index]):
        return None

    preview_args = argv[command_index + 1 :]
    output_format = "text"
    include_risk_authority = False
    include_research_queue = False
    include_sma_research_observation = False
    include_sma_research_summary_observation = False
    include_research_return_observation = False
    include_research_return_summary_observation = False
    include_research_data_source_readiness = False
    include_research_data_source_readiness_summary = False
    include_diagnostic_issues = False
    include_advisory_sections = False
    saw_format = False
    index = 0
    while index < len(preview_args):
        argument = preview_args[index]
        if argument == "--format":
            if saw_format or index + 1 >= len(preview_args):
                return None
            candidate_format = preview_args[index + 1]
            if candidate_format not in _PREVIEW_FORMATS:
                return None
            output_format = candidate_format
            saw_format = True
            index += 2
        elif argument in allowed_flags:
            if argument == "--include-risk-authority":
                if include_risk_authority:
                    return None
                include_risk_authority = True
            if argument == "--include-research-queue":
                if include_research_queue:
                    return None
                include_research_queue = True
            if argument == "--include-sma-research-observation":
                if include_sma_research_observation:
                    return None
                include_sma_research_observation = True
            if argument == "--include-sma-research-summary-observation":
                if include_sma_research_summary_observation:
                    return None
                include_sma_research_summary_observation = True
            if argument == "--include-research-return-observation":
                if include_research_return_observation:
                    return None
                include_research_return_observation = True
            if argument == "--include-research-return-summary-observation":
                if include_research_return_summary_observation:
                    return None
                include_research_return_summary_observation = True
            if argument == "--include-research-data-source-readiness":
                if include_research_data_source_readiness:
                    return None
                include_research_data_source_readiness = True
            if argument == "--include-research-data-source-readiness-summary":
                if include_research_data_source_readiness_summary:
                    return None
                include_research_data_source_readiness_summary = True
            if argument == "--include-diagnostic-issues":
                if include_diagnostic_issues:
                    return None
                include_diagnostic_issues = True
            if argument == "--include-advisory-sections":
                if include_advisory_sections:
                    return None
                include_advisory_sections = True
            index += 1
        else:
            return None

    return (
        output_format,
        include_risk_authority,
        include_research_queue,
        include_sma_research_observation,
        include_sma_research_summary_observation,
        include_research_return_observation,
        include_research_return_summary_observation,
        include_research_data_source_readiness,
        include_research_data_source_readiness_summary,
        include_diagnostic_issues,
        include_advisory_sections,
    )


def _only_ignored_runtime_options(argv: tuple[str, ...]) -> bool:
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument in ("--profile", "--log-level"):
            index += 2
        elif argument.startswith("--profile=") or argument.startswith("--log-level="):
            index += 1
        else:
            return False

    return index == len(argv)


def _add_hidden_option(
    parser: argparse.ArgumentParser,
    *args,
    **kwargs,
) -> argparse.Action:
    action = parser.add_argument(*args, **kwargs)
    parser._actions.remove(action)
    for group in parser._action_groups:
        if action in group._group_actions:
            group._group_actions.remove(action)
    return action


def _add_paper_lab_run_log_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--run-log",
        default=None,
        help="Append deterministic paper-lab observation JSONL records to PATH.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run/session id to include in paper-lab observation records.",
    )
