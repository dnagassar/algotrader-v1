"""Local deterministic reconciliation between expected and broker state."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from algotrader.execution.broker_base import Broker
from algotrader.portfolio.state import Account, PortfolioState, Position
from algotrader.portfolio.valuation import (
    PortfolioValuation,
    QuoteInput,
    value_portfolio,
)


@dataclass(frozen=True, slots=True)
class ReconciliationMismatch:
    kind: str
    expected: str
    actual: str
    symbol: str | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    ok: bool
    mismatches: tuple[ReconciliationMismatch, ...]
    expected_portfolio: PortfolioState
    broker_portfolio: PortfolioState
    expected_valuation: PortfolioValuation | None = None
    broker_valuation: PortfolioValuation | None = None
    available: bool = True
    broker_error: str = ""


def reconcile_portfolio(
    expected_portfolio: PortfolioState,
    broker: Broker,
    quotes: QuoteInput | None = None,
) -> ReconciliationReport:
    """Compare expected portfolio state against broker-reported local state."""

    try:
        broker_account = broker.get_account()
        broker_positions = broker.get_positions()
    except Exception as exc:
        return _unavailable_report(expected_portfolio, exc)

    broker_portfolio = PortfolioState(
        account=broker_account,
        positions=broker_positions,
        risk=expected_portfolio.risk,
        timestamp=expected_portfolio.timestamp,
    )

    mismatches = [
        *_cash_mismatches(expected_portfolio.account, broker_portfolio.account),
        *_position_mismatches(expected_portfolio.positions, broker_portfolio.positions),
    ]

    expected_valuation = None
    broker_valuation = None
    if quotes is not None:
        expected_valuation = value_portfolio(expected_portfolio, quotes)
        broker_valuation = value_portfolio(broker_portfolio, quotes)
        mismatches.extend(
            _valuation_mismatches(expected_valuation, broker_valuation)
        )

    return ReconciliationReport(
        ok=not mismatches,
        mismatches=tuple(mismatches),
        expected_portfolio=expected_portfolio,
        broker_portfolio=broker_portfolio,
        expected_valuation=expected_valuation,
        broker_valuation=broker_valuation,
    )


def _unavailable_report(
    expected_portfolio: PortfolioState,
    exc: Exception,
) -> ReconciliationReport:
    broker_portfolio = PortfolioState(
        account=Account("0", expected_portfolio.account.currency),
        positions=(),
        risk=expected_portfolio.risk,
        timestamp=expected_portfolio.timestamp,
    )
    return ReconciliationReport(
        ok=False,
        mismatches=(),
        expected_portfolio=expected_portfolio,
        broker_portfolio=broker_portfolio,
        available=False,
        broker_error=f"{exc.__class__.__name__}: broker call failed",
    )


def _cash_mismatches(
    expected: Account,
    actual: Account,
) -> tuple[ReconciliationMismatch, ...]:
    if expected.cash == actual.cash and expected.currency == actual.currency:
        return ()

    return (
        ReconciliationMismatch(
            kind="cash_mismatch",
            expected=f"{expected.cash} {expected.currency}",
            actual=f"{actual.cash} {actual.currency}",
        ),
    )


def _position_mismatches(
    expected_positions: tuple[Position, ...],
    actual_positions: tuple[Position, ...],
) -> tuple[ReconciliationMismatch, ...]:
    mismatches: list[ReconciliationMismatch] = []
    expected_by_symbol = _position_map(expected_positions)
    actual_by_symbol = _position_map(actual_positions)

    for symbol, expected in expected_by_symbol.items():
        actual = actual_by_symbol.get(symbol)
        if actual is None:
            mismatches.append(
                ReconciliationMismatch(
                    kind="missing_position",
                    symbol=symbol,
                    expected=str(expected.quantity),
                    actual="missing",
                )
            )
            continue

        if expected.quantity != actual.quantity:
            mismatches.append(
                ReconciliationMismatch(
                    kind="quantity_mismatch",
                    symbol=symbol,
                    expected=str(expected.quantity),
                    actual=str(actual.quantity),
                )
            )

    for symbol, actual in actual_by_symbol.items():
        if symbol not in expected_by_symbol:
            mismatches.append(
                ReconciliationMismatch(
                    kind="unexpected_position",
                    symbol=symbol,
                    expected="missing",
                    actual=str(actual.quantity),
                )
            )

    return tuple(mismatches)


def _valuation_mismatches(
    expected: PortfolioValuation,
    actual: PortfolioValuation,
) -> tuple[ReconciliationMismatch, ...]:
    mismatches: list[ReconciliationMismatch] = []

    if expected.total_market_value != actual.total_market_value:
        mismatches.append(
            _decimal_mismatch(
                "valuation_mismatch",
                expected.total_market_value,
                actual.total_market_value,
                "total_market_value",
            )
        )

    if expected.total_unrealized_pnl != actual.total_unrealized_pnl:
        mismatches.append(
            _decimal_mismatch(
                "unrealized_pnl_mismatch",
                expected.total_unrealized_pnl,
                actual.total_unrealized_pnl,
                "total_unrealized_pnl",
            )
        )

    return tuple(mismatches)


def _decimal_mismatch(
    kind: str,
    expected: Decimal,
    actual: Decimal,
    detail: str,
) -> ReconciliationMismatch:
    return ReconciliationMismatch(
        kind=kind,
        expected=str(expected),
        actual=str(actual),
        detail=detail,
    )


def _position_map(positions: tuple[Position, ...]) -> dict[str, Position]:
    return {position.symbol: position for position in positions if not position.is_flat}
