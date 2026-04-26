"""Command-line interface for the deterministic paper-trading core."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone

from .config import PROFILE_NAMES, load_config
from .logging_setup import configure_logging, get_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="algotrader")
    parser.add_argument(
        "--profile",
        choices=PROFILE_NAMES,
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
    subparsers.add_parser(
        "demo-core",
        help="Run one deterministic local trading-flow demo.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config(profile=args.profile)
    log_level = args.log_level or config.log_level
    configure_logging(log_level=log_level)

    logger = get_logger(__name__)
    command = args.command or "config"

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
        _run_demo_core()
        return 0

    parser.error(f"unsupported command: {command}")
    return 2


def _run_demo_core() -> None:
    from .core.types import Bar, Quote
    from .orchestration.signal_trade_flow import generate_evaluate_and_execute
    from .portfolio.state import Account, PortfolioState

    timestamp = datetime(2026, 4, 25, tzinfo=timezone.utc)
    previous_bar = Bar("MSFT", timestamp, "99", "101", "98", "100", "1000")
    quote = Quote("MSFT", timestamp, bid="101.00", ask="101.01")
    portfolio = PortfolioState(account=Account("1000"))

    result = generate_evaluate_and_execute(
        previous_bar=previous_bar,
        quote=quote,
        portfolio=portfolio,
    )

    print("Deterministic core demo")
    print(f"signal: {'generated' if result.order else 'none'}")
    print(f"risk: {_risk_summary(result)}")
    print(f"execution: {_execution_summary(result)}")

    if result.portfolio is not None:
        print(f"cash: {result.portfolio.account.cash}")

    if result.valuation is not None:
        print(f"valuation: {result.valuation.total_market_value}")
        print(f"unrealized_pnl: {result.valuation.total_unrealized_pnl}")
    else:
        print("valuation: unavailable")


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
