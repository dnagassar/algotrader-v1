# Project Checkpoint

## Current milestone

The project has a small, deterministic local trading core with a one-shot CLI
demo. The core can generate a simple signal, produce a proposed order, check
pre-trade risk, simulate paper execution, update portfolio state, and value the
resulting portfolio.

## Test status

Latest confirmed result before adding the scenario harness:

```text
42 passed in 0.31s
```

Command used:

```powershell
python -m pytest
```

## Current deterministic path

```text
Bar + Quote
  -> signal rule
  -> ProposedOrder/no signal
  -> RiskEngine.check()
  -> paper execution
  -> apply_fill()
  -> portfolio valuation
  -> structured result
```

## What exists now

- Project scaffold with `src/algotrader` package layout.
- CLI entry point with `config` and `demo-core` commands.
- Dev and paper configuration profiles.
- Structured JSON logging setup.
- Core domain models for bars, quotes, orders, acknowledgements, fills, and
  order status.
- Portfolio models for account, positions, portfolio state, and risk state.
- Pure portfolio state transition via `apply_fill()`.
- Deterministic paper execution simulator.
- Quote-based portfolio valuation.
- Pre-trade risk engine with conservative v1 checks.
- Simple deterministic signal rule.
- Signal-to-trade and order-to-trade orchestration helpers.
- Unit and smoke tests covering the deterministic core.
- Documentation for the deterministic core boundary.

## What is intentionally not included yet

- Broker API wiring.
- Live trading.
- Scheduler or runtime loop.
- OMS layer.
- LangGraph.
- ML models.
- LLM logic in risk, execution, signals, screener, portfolio, or feature
  calculation.

## Latest change

The most recent completed task added a deterministic scenario harness and
scenario selection for the one-shot CLI demo command:

```powershell
python -m algotrader demo-core --scenario approved_and_filled
```

The scenarios run the existing local core using fixed sample inputs and print a
readable summary of signal, risk, execution, cash, valuation, and unrealized
P&L.

## Next recommended step

Add a small deterministic scenario runner that can execute a fixed list of
sample bars and quotes against the existing local core, returning structured
scenario results. Keep it local and test-only/demo-oriented, with no scheduler,
broker wiring, live trading, LangGraph, ML, or LLM logic.

## Architectural rules

- Keep the trading path deterministic.
- Do not add LLM logic in risk, execution, signals, screener, portfolio, or
  feature calculation.
- Do not add broker API wiring until the local core is stable.
- Do not add a scheduler or runtime loop until the demo/scenario layer is
  stable.
