# SPY SMA-200 Local Research Run

Advisory only: this local report is not validated evidence, not approved, and
not a trading recommendation. It must not be used as production
signal/evaluator behavior or a trading workflow.

## Data Source
- Source name: <source_name>
- Source type: <source_type>
- CSV file: <csv_file_name_only>
- File SHA-256: <file_sha256>
- Snapshot fingerprint: <snapshot_fingerprint>
- Date range: <start_date> to <end_date>
- Row count: <row_count>
- Adjustment policy: <adjustment_policy>

## Assumptions
- Initial equity: <initial_equity>
- Fee bps: <fee_bps>
- Slippage bps: <slippage_bps>

## Rule
- Exposure = 1 when adjusted_close > trailing 200-day SMA.
- Exposure = 0 otherwise.
- First 199 bars are exposure 0.
- The trailing SMA is computed from the 200 adjusted_close values through the current bar.
- Backtest applies exposure to next day return through previous-exposure convention.

## Metrics
- Starting equity: <starting_equity>
- Ending equity: <ending_equity>
- Total return: <total_return>
- Max drawdown: <max_drawdown>
- Exposure ratio: <exposure_ratio>
- Turnover: <turnover>

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
