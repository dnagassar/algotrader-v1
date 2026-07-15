# V5.22 Preregistered Crypto Strategy Tournament

## Status

This contract was frozen in source and tests before the long-history market-data
fetch. It is a research-only, no-submit tournament. It does not modify the
legacy crypto evidence battery, reopen the rejected ADA 24-hour repair, or
authorize paper/live execution.

- Schema: `v5_22_crypto_preregistered_tournament_v1`
- Factory: `v5_22_crypto_preregistered_candidate_factory_v1`
- Gate policy: `v5_22_crypto_preregistered_gate_policy_v1`
- Preregistration fingerprint:
  `1475d35634750a7f00832f0a540fbaac3e28e7ed82ac7dbd8ef2d60e08f09097`
- Dynamic optimization: disabled
- Post-hoc retuning: disabled
- Candidate-set mutation: disabled

## Frozen Candidate Set

The tournament contains exactly 12 candidates: four symbols (`BTCUSD`,
`ETHUSD`, `SOLUSD`, and `ADAUSD`) crossed with three elapsed-time rules:

- `trend_momentum_72h`
- `breakout_168h`
- `moving_average_regime_24h_168h`

Candidate IDs use `crypto:tournament_v1:{symbol}:{strategy_id}`. The closed
`crypto:ADAUSD:trend_momentum_24h_repair` candidate is deliberately absent.
Each candidate has a canonical SHA-256 fingerprint over its identity,
parameters, one-hour/four-hour mappings, causal execution semantics, and
factory version.

## Data And Temporal Contract

- One canonical, non-fixture `1Hour` CSV supplies all four symbols.
- The CSV must be cryptographically bound to the guarded refresh packet: its
  resolved output path and SHA-256, source, symbols, timeframe, fixed window,
  row counts, and no-mutation safety fields must match.
- Every symbol must share one duplicate-free, consecutive UTC timestamp grid.
- At least 4,320 complete hourly bars per symbol are required; up to 8,760 are
  used.
- The selected range is a trailing complete multiple of 24 hours ending at a
  completed UTC four-hour boundary.
- At least 2,592 earlier hours are discovery/warmup only.
- The final 1,728 hours are untouched OOS evidence, divided into four fixed,
  non-overlapping 432-hour folds.
- Four-hour robustness bars are aggregated locally from complete UTC-aligned
  groups of the same one-hour source bytes. They are not fetched separately.
- Signals have a one-bar lag. Portfolio state starts in cash at the OOS
  boundary and remains continuous across fold boundaries.
- At least 95% of hourly rows for every symbol must have positive reported
  volume. Quote-only/zero-volume bars remain observable but cannot dominate the
  fill-oriented evidence sample.

## Cost And Benchmark Contract

- Base cost: 25 bps taker fee plus 15 bps slippage per full exposure
  transition, 40 bps total.
- Stress cost: 50 bps fee plus 30 bps slippage, 80 bps total.
- Transition costs are applied to post-return notional at the bar close where
  the next exposure is established.
- Benchmarks are cash, same-symbol buy-and-hold, and an equal-weight basket
  entered once at the OOS boundary and then held without free hourly
  rebalancing.
- Exposure transitions and completed round trips are reported separately.

## No-Submit Shadow Gate

A candidate is eligible only for `eligible_for_no_submit_shadow_evaluation`
when every condition passes:

- one-hour aggregate OOS returns are positive under base and stress costs
- it strictly beats cash, same-symbol buy-and-hold, and the equal-weight basket
  under both cost cases
- base OOS drawdown is no more than 20% and no worse than either risky benchmark
- at least three of four OOS folds are positive
- no fold contributes more than 50% of total positive OOS profit
- the full frozen sample contains at least 30 completed round trips
- untouched OOS contains at least 20 exposure transitions
- the four-hour robustness evaluation is also positive, beats all benchmarks
  under both cost cases, and passes the drawdown gates

Qualifiers rank by stress return, base return, worst-fold return, lower
drawdown, lower turnover, and candidate ID. A pass is not paper planning,
broker execution, capital allocation, or a profit claim.

## Isolated One-Year Backfill

The existing guarded adapter can retrieve the fixed one-year window without
changing its network boundary. Use isolated generated paths so the prior
operator-input history is not overwritten:

```powershell
.\scripts\refresh_multi_symbol_crypto_history.ps1 `
  -Mode market_data_fetch `
  -Symbols "BTCUSD,ETHUSD,SOLUSD,ADAUSD" `
  -Start "2025-07-15T00:00:00Z" `
  -End "2026-07-15T00:00:00Z" `
  -AsOfTimestamp "2026-07-15T00:00:00Z" `
  -Timeframe "1Hour" `
  -Loc "us" `
  -OutputPath "runs\crypto_strategy_tournament\v1\input\crypto_1h_1y.csv" `
  -PacketPath "runs\crypto_strategy_tournament\v1\refresh\refresh_packet.json" `
  -RawResponsePath "runs\crypto_strategy_tournament\v1\refresh\raw_crypto_bars.json" `
  -MarketDataFetchAuthorized `
  -Format json
```

The fetch is an exact-destination, read-only market-data operation and still
requires the paper-profile credential and endpoint preflight plus exact
operator authorization. It exposes no trading mutation.

After the generated CSV passes intake, run the credential-free tournament:

```powershell
.\scripts\run_crypto_preregistered_tournament.ps1 `
  -InputPath "runs\crypto_strategy_tournament\v1\input\crypto_1h_1y.csv" `
  -RefreshPacketPath "runs\crypto_strategy_tournament\v1\refresh\refresh_packet.json" `
  -OutputRoot "runs\crypto_strategy_tournament\v1\latest" `
  -AsOfTimestamp "2026-07-15T00:00:00Z" `
  -Format text
```

All outputs under `runs/` are generated evidence, never authority, and remain
untracked.
