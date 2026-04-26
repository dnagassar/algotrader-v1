# Deterministic Trading Core

This project currently implements a small local trading core for paper-trading
experiments. The core is intentionally deterministic: functions take explicit
inputs and return structured results without reaching out to brokers, schedulers,
model services, or external state.

## Current Flow

1. A signal rule compares market inputs and may produce a `ProposedOrder`.
2. The risk engine validates the proposed order against portfolio state, cash,
   quote data, and conservative risk settings.
3. The paper execution simulator fills marketable orders using the current quote.
4. Filled orders are applied to immutable portfolio state.
5. Portfolio valuation marks long positions with current quote data.
6. Orchestration helpers return structured results for no-signal, rejected,
   open, filled, and error cases.

## Boundaries

- Signal generation only creates `ProposedOrder` objects or returns `None`.
- Risk checks do not execute orders.
- Execution simulation does not mutate portfolio state.
- Portfolio state transitions are pure functions.
- Valuation requires explicit current quotes and does not guess missing prices.
- Orchestration composes the deterministic pieces but is not a scheduler or
  runtime loop.

## Not Included Yet

- Broker API wiring
- Live trading
- Runtime scheduling
- CLI wiring for a runtime trading loop
- LangGraph
- ML models
- LLM logic in signals, risk, execution, screener, portfolio, or feature code

## One-Shot CLI Demo

Run `python -m algotrader demo-core` to execute the deterministic flow once with
fixed sample inputs. This is a demonstration command only; it is not a scheduler,
broker integration, or live trading loop.
