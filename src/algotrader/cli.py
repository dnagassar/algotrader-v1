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
_PAPER_ORDER_PROBE_DISABLED_REASON = (
    "submission_disabled_until_true_notional_cap_is_supported"
)
_PAPER_ORDER_PROBE_CLIENT_ORDER_ID = "paper-order-probe-preview-only"
_PAPER_SAFETY_GATE_ORDER = (
    "profile_gate",
    "halt_gate",
    "allowlist_gate",
    "side_gate",
    "quantity_gate",
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
    paper_order_probe_parser = subparsers.add_parser(
        "paper-order-probe",
        help="Preview a guarded Alpaca paper order request without submitting.",
    )
    paper_order_probe_parser.add_argument("--symbol", required=True)
    paper_order_probe_parser.add_argument("--side", required=True)
    paper_order_probe_parser.add_argument("--qty", required=True)
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
        return _run_paper_account_smoke(config, args.output_format)
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


def _run_paper_account_smoke(config, output_format: str) -> int:
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
    print(_render_paper_account_payload(payload, output_format))
    return 0


def _run_paper_order_probe(config, args: argparse.Namespace) -> int:
    payload = _build_paper_order_probe_payload(config, args)
    print(_render_paper_order_probe_payload(payload, args.output_format))
    return 0 if payload["ok"] else 2


def _build_paper_order_probe_payload(
    config,
    args: argparse.Namespace,
) -> dict[str, object]:
    symbol = args.symbol.strip().upper()
    side = args.side.strip().lower()
    quantity, quantity_error = _positive_whole_decimal(args.qty, "qty")
    max_notional, max_notional_error = _positive_decimal(
        args.max_notional,
        "max_notional",
    )
    submit_requested = bool(args.submit or args.i_mean_it)

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
    quantity_gate = _gate(
        quantity is not None,
        "positive_whole_share_quantity",
        quantity_error or "invalid_quantity",
    )
    notional_cap_gate = _gate(
        max_notional is not None
        and max_notional <= _PAPER_ORDER_PROBE_MAX_NOTIONAL_CAP,
        f"max_notional_cap={_decimal_text(_PAPER_ORDER_PROBE_MAX_NOTIONAL_CAP)}",
        max_notional_error or "max_notional_cap_exceeded",
    )
    submit_confirmation_gate = _gate(
        not submit_requested,
        "preview_only_no_submission_requested",
        _PAPER_ORDER_PROBE_DISABLED_REASON,
    )
    gates = {
        "profile_gate": profile_gate,
        "halt_gate": halt_gate,
        "allowlist_gate": allowlist_gate,
        "side_gate": side_gate,
        "quantity_gate": quantity_gate,
        "notional_cap_gate": notional_cap_gate,
        "submit_confirmation_gate": submit_confirmation_gate,
    }
    ok = all(bool(gate["passed"]) for gate in gates.values())

    request_payload = None
    if symbol and side == "buy" and quantity is not None:
        request_payload = _paper_order_request_payload(symbol, quantity)

    return {
        "command": "paper-order-probe",
        "error": "" if ok else _first_failed_gate(gates),
        "gates": gates,
        "max_notional": (
            _decimal_text(max_notional) if max_notional is not None else args.max_notional
        ),
        "ok": ok,
        "preview_only": True,
        "proposed_order_request": request_payload,
        "requested_submit": bool(args.submit),
        "requested_i_mean_it": bool(args.i_mean_it),
        "submitted": False,
        "submission_disabled_reason": _PAPER_ORDER_PROBE_DISABLED_REASON,
    }


def _paper_order_request_payload(symbol: str, quantity: Decimal) -> dict[str, str]:
    from .execution.alpaca_client import AlpacaOrderRequest

    request = AlpacaOrderRequest(
        client_order_id=_PAPER_ORDER_PROBE_CLIENT_ORDER_ID,
        symbol=symbol,
        side="buy",
        qty=quantity,
        order_type="market",
        time_in_force="day",
    )
    return {
        "client_order_id": request.client_order_id,
        "limit_price": "",
        "order_type": request.order_type,
        "qty": _decimal_text(request.qty),
        "request_model": "AlpacaOrderRequest",
        "side": request.side,
        "symbol": request.symbol,
        "time_in_force": request.time_in_force,
    }


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
        f"submitted: {_bool_text(payload['submitted'])}",
    ]
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
                f"order_type: {request['order_type']}",
                f"time_in_force: {request['time_in_force']}",
                f"client_order_id: {request['client_order_id']}",
            ]
        )
    lines.append(f"max_notional: {payload['max_notional']}")
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


def _redact_config_secrets(message: str, config) -> str:
    redacted = message
    for value in (
        config.alpaca_paper.alpaca_api_key,
        config.alpaca_paper.alpaca_secret_key,
    ):
        if value:
            redacted = redacted.replace(value, "<redacted>")
    return redacted


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
