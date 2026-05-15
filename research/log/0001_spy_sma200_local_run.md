# SPY SMA-200 Local Research Run

Advisory only: this local report is not validated evidence, not approved, and not a trading recommendation. It must not be used as production signal/evaluator behavior or a trading workflow.

## Data Source
- Source name: alpaca_market_data
- Source type: vendor_snapshot
- CSV file: SPY_daily.csv
- File SHA-256: 76d9f5b94cbb5d6076b53cf53f18fb29b71c3482e6f4cfe010f06d52fd482e08
- Snapshot fingerprint: 6122513f46958fab3f9f3da9f43a93bb45137cd3b6589823ba694804c8354d3c
- Date range: 2024-01-02 to 2026-05-15
- Row count: 595
- Adjustment policy: unknown

## Assumptions
- Initial equity: 10000
- Fee bps: 0
- Slippage bps: 0

## Rule
- Exposure = 1 when adjusted_close > trailing 200-day SMA.
- Exposure = 0 otherwise.
- First 199 bars are exposure 0.
- The trailing SMA is computed from the 200 adjusted_close values through the current bar.
- Backtest applies exposure to next day return through previous-exposure convention.

## Metrics
- Starting equity: 10000
- Ending equity: 11780.04822259226312846208555
- Total return: 0.178004822259226312846208555
- Max drawdown: 0.0992659922312691421999402464
- Exposure ratio: 0.5747899159663865546218487395
- Turnover: 7

## Limitations
- Local snapshot only.
- Source not approved.
- No benchmark comparison yet.
- No parameter sweep.
- No transaction-cost realism unless assumptions are explicitly set.
- Not validated evidence.
- Not a trading recommendation.
- Not production signal/evaluator behavior.

## Verdict
- Advisory only / not validated / not approved.
