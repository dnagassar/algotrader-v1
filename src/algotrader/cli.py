"""Command-line interface for the deterministic paper-trading core."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
import json
import sys

_PROFILE_NAMES = ("dev", "paper", "live")
_PREVIEW_FORMATS = ("text", "json")
_PAPER_ORDER_PROBE_SYMBOL_ALLOWLIST = ("SPY",)
_PAPER_ORDER_PROBE_MAX_NOTIONAL_CAP = Decimal("10")
_PAPER_ORDER_PROBE_QTY_DISABLED_REASON = (
    "qty_submission_disabled_until_quote_based_cap_is_supported"
)
_PAPER_ORDER_PROBE_CLIENT_ORDER_ID = "paper-order-probe-notional-1"
_PAPER_ORDER_PROBE_CLIENT_ORDER_ID_PREFIX = "paper-order-probe"
_PAPER_ORDER_PROBE_CLIENT_ORDER_ID_RUN_ID_LENGTH = 30
_PAPER_MARKET_SESSION_NOTE = (
    "Market DAY equity orders submitted after hours may be accepted or queued "
    "by the broker and may not fill until the next regular session."
)
_PAPER_SAFETY_GATE_ORDER = (
    "profile_gate",
    "halt_gate",
    "allowlist_gate",
    "side_gate",
    "sizing_gate",
    "quantity_gate",
    "notional_value_gate",
    "notional_cap_gate",
    "submit_confirmation_gate",
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
    paper_order_probe_parser = subparsers.add_parser(
        "paper-order-probe",
        help="Preview a guarded Alpaca paper order request without submitting.",
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
            "Request submission. Disabled until true notional-cap support exists."
        ),
    )
    paper_order_probe_parser.add_argument(
        "--i-mean-it",
        action="store_true",
        dest="i_mean_it",
        help=(
            "Acknowledge a future submit path. Disabled for this milestone."
        ),
    )
    _add_paper_lab_run_log_options(paper_order_probe_parser)
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
    if command == "paper-order-probe":
        return _run_paper_order_probe(config, args)

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


def _build_paper_order_probe_payload(
    config,
    args: argparse.Namespace,
) -> dict[str, object]:
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
        symbol in _PAPER_ORDER_PROBE_SYMBOL_ALLOWLIST,
        f"symbol={symbol} allowlist={','.join(_PAPER_ORDER_PROBE_SYMBOL_ALLOWLIST)}",
        "symbol_not_allowlisted",
    )
    side_gate = _gate(side == "buy", "buy_only", "side_must_be_buy")
    sizing_gate = _gate(
        sizing_mode in ("qty", "notional"),
        sizing_mode,
        "exactly_one_of_qty_or_notional_required",
    )
    quantity_gate = _gate(
        sizing_mode != "qty" or quantity is not None,
        "positive_whole_share_quantity",
        quantity_error or "invalid_quantity",
    )
    notional_value_gate = _gate(
        sizing_mode != "notional" or notional is not None,
        "positive_notional",
        notional_error or "invalid_notional",
    )
    notional_cap_gate = _gate(
        max_notional is not None
        and max_notional <= _PAPER_ORDER_PROBE_MAX_NOTIONAL_CAP,
        f"max_notional_cap={_decimal_text(_PAPER_ORDER_PROBE_MAX_NOTIONAL_CAP)}",
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
        ),
        _paper_order_submit_confirmation_detail(
            submit_flag=bool(args.submit),
            i_mean_it_flag=bool(args.i_mean_it),
            sizing_mode=sizing_mode,
        ),
        _paper_order_submit_confirmation_failure_detail(
            submit_flag=bool(args.submit),
            i_mean_it_flag=bool(args.i_mean_it),
            sizing_mode=sizing_mode,
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
        "notional_cap_gate": notional_cap_gate,
        "submit_confirmation_gate": submit_confirmation_gate,
    }
    ok = all(bool(gate["passed"]) for gate in gates.values())

    request_payload = None
    if symbol and side == "buy" and sizing_mode in ("qty", "notional"):
        try:
            request = _paper_order_request(
                symbol,
                client_order_id=_paper_order_client_order_id(args.run_id),
                quantity=quantity if sizing_mode == "qty" else None,
                notional=notional if sizing_mode == "notional" else None,
            )
            request_payload = _paper_order_request_payload(request)
        except ValueError:
            request_payload = None

    return {
        "command": "paper-order-probe",
        "error": "" if ok else _first_failed_gate(gates),
        "gates": gates,
        "max_notional": (
            _decimal_text(max_notional) if max_notional is not None else args.max_notional
        ),
        "ok": ok,
        "preview_only": not submit_requested,
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
        "market_session_note": _PAPER_MARKET_SESSION_NOTE,
        "submitted": False,
        "submission_disabled_reason": (
            _PAPER_ORDER_PROBE_QTY_DISABLED_REASON if sizing_mode == "qty" else ""
        ),
        "submit_attempted": False,
        "submit_requested": submit_requested,
    }


def _submit_paper_order_probe(
    config,
    payload: dict[str, object],
    *,
    observe_post_submit: bool = False,
) -> dict[str, object]:
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
            client_order_id=str(
                request_payload.get(
                    "client_order_id",
                    _PAPER_ORDER_PROBE_CLIENT_ORDER_ID,
                )
            ),
            notional=Decimal(str(request_payload["notional"])),
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
        "ok": result.accepted,
        "preview_only": False,
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


def _paper_order_request(
    symbol: str,
    *,
    client_order_id: str = _PAPER_ORDER_PROBE_CLIENT_ORDER_ID,
    quantity: Decimal | None = None,
    notional: Decimal | None = None,
):
    from .execution.alpaca_client import AlpacaOrderRequest

    return AlpacaOrderRequest(
        client_order_id=client_order_id,
        symbol=symbol,
        side="buy",
        qty=quantity,
        notional=notional,
        order_type="market",
        time_in_force="day",
    )


def _paper_order_request_payload(request) -> dict[str, str]:
    return {
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
) -> bool:
    if not submit_flag and not i_mean_it_flag:
        return True
    if submit_flag and i_mean_it_flag and sizing_mode == "notional":
        return True

    return False


def _paper_order_submit_confirmation_detail(
    *,
    submit_flag: bool,
    i_mean_it_flag: bool,
    sizing_mode: str,
) -> str:
    if not submit_flag and not i_mean_it_flag:
        return "preview_only_no_submission_requested"
    if submit_flag and i_mean_it_flag and sizing_mode == "notional":
        return "explicit_notional_submit_confirmed"

    return ""


def _paper_order_submit_confirmation_failure_detail(
    *,
    submit_flag: bool,
    i_mean_it_flag: bool,
    sizing_mode: str,
) -> str:
    if submit_flag and i_mean_it_flag and sizing_mode == "qty":
        return _PAPER_ORDER_PROBE_QTY_DISABLED_REASON

    return "submit_requires_submit_and_i_mean_it"


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


def _render_paper_order_probe_payload(
    payload: dict[str, object],
    output_format: str,
) -> str:
    if output_format == "json":
        return _compact_json(payload)

    lines = [
        "Paper order probe",
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


def _redact_config_secrets(message: str, config) -> str:
    redacted = message
    for value in _paper_lab_sensitive_values(config):
        if value:
            redacted = redacted.replace(value, "<redacted>")
    return redacted


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
