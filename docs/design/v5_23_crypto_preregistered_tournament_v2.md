# V5.23 Preregistered Crypto Tournament V2

## Status

This is the immutable research contract for a new BTC/ETH/SOL tournament.
The four-symbol v1 tournament remains closed at its terminal input-quality gate.
V2 does not reuse v1 candidate identities, OOS bytes, or promotion authority.

- Schema: `v5_23_crypto_tournament_v2_v1`
- Factory: `v5_23_crypto_tournament_v2_factory_v1`
- Policy: `v5_23_crypto_tournament_v2_policy_v1`
- Gap policy: `v5_23_crypto_tournament_v2_isolated_gap_policy_v1`
- Preregistration fingerprint:
  `afccc81d6592c5e56cf4ef968b3b778d1d6675b95551ddd98b355b75f4d19a36`
- Required freeze deadline: before `2026-07-16T00:00:00Z`
- Dynamic optimization, post-hoc retuning, candidate mutation, early promotion:
  disabled

## Frozen Universe And Candidates

The universe is exactly `BTCUSD`, `ETHUSD`, and `SOLUSD`. Nine candidates
cross those symbols with the three previously specified elapsed-time rules:

- `trend_momentum_72h`
- `breakout_168h`
- `moving_average_regime_24h_168h`

Candidate IDs begin `crypto:tournament_v2:` and have new fingerprints. ADA is
not a v2 candidate. Removing ADA from v1 after seeing the provider evidence is
forbidden; v2 is a separately authorized hypothesis family.

## Frozen Calendar

- Discovery source window: `2026-01-16T00:00:00Z` inclusive through
  `2026-07-15T00:00:00Z` exclusive, 4,320 expected hourly slots per symbol.
- Embargo: all 24 hours of `2026-07-15` UTC. Embargo bytes cannot enter
  discovery or OOS scoring.
- Untouched OOS: `2026-07-16T00:00:00Z` through
  `2026-08-12T23:00:00Z`, exactly 672 hourly slots per symbol.
- Terminal scoring release: no earlier than `2026-08-13T00:00:00Z`.
- Four fixed weekly folds contain 168 one-hour bars and 42 locally aggregated
  four-hour bars each.
- Completeness-only checkpoints occur at `2026-07-23T00:00:00Z`,
  `2026-07-30T00:00:00Z`, and `2026-08-06T00:00:00Z`.

Checkpoint packets may expose receipt identity, hashes, row counts, missing or
imputed timestamps, per-symbol frontiers, and safety flags. They may not expose
candidate targets, trades, returns, drawdowns, rankings, or selection. The
endpoint cannot be extended after a weak or incomplete result.

## Frozen Sparse-Bar Policy

The current authoritative provider snapshot contains sparse isolated omissions.
V2 fixes the repair rule before any future OOS scoring:

- raw coverage must be at least 99.5% per symbol
- raw positive-volume coverage must be at least 95% per symbol
- no more than one consecutive hourly slot may be missing
- the first and last OOS slots may not be missing
- an admitted isolated gap is filled with prior-close OHLC and zero volume
- every imputed timestamp is explicit and enters the derived-snapshot hash
- target exposure must remain unchanged on an imputed hour
- a four-hour bucket containing an imputation also cannot transition
- any policy violation blocks the fixed window and never extends it

The discovery snapshot and every OOS delta must remain bound to guarded refresh
receipts, resolved paths, output SHA-256 values, source identity, symbol set,
timeframe, and no-mutation safety fields.

## Costs, Benchmarks, And Gates

- Base cost: 25 bps fee plus 15 bps slippage, 40 bps per transition.
- Stress cost: 50 bps fee plus 30 bps slippage, 80 bps per transition.
- Signals are one-bar lagged and long-or-cash.
- Benchmarks are cash, same-symbol buy-and-hold, and an equal-weight
  BTC/ETH/SOL basket entered once at OOS start and allowed to drift.
- Base and stress returns must be positive and strictly beat every benchmark.
- Maximum OOS drawdown is 20% and cannot exceed either risky benchmark.
- At least three of four folds must be positive.
- No fold may contribute more than 50% of positive OOS profit.
- At least 30 full-sample completed round trips and 20 OOS transitions are
  required.
- The locally aggregated four-hour evaluation must pass the return, benchmark,
  and drawdown gates.
- Deterministic ranking may select at most one terminal winner.

## Authority Boundary

Successful initialization means only `research_ready_for_future_oos_accrual`.
A terminal pass means only `eligible_for_no_submit_shadow_evaluation`.

Paper planning, paper mutation, broker execution, live trading, capital
allocation, and profit claims remain unauthorized. A selected v2 winner must
complete a separately fingerprinted, single-winner untouched forward-shadow
contract before any paper consideration. Reusing the selection window for that
decision is prohibited.

Generated discovery, accrual, receipt, and evidence state belongs under
`runs/crypto_strategy_tournament/v2/` and is never authority or tracked source.
