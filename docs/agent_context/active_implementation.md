# Active Implementation

## Ownership and takeover

- Writer: Codex, sole implementation writer in this working tree.
- Working tree:
  `C:\Users\danie\.codex\worktrees\c029\algo_trader`.
- Branch: `codex/v5.62-nexustrade-source-data-unblock`.
- Takeover HEAD:
  `3581ffd5af80de38673a234a05159ddaeee911e5`.
- Takeover inspection covered branch, HEAD, status, staged diff, unstaged diff,
  untracked files, and this handoff before any change.
- Takeover was clean: staged, unstaged, and untracked sets were empty.
- No reset, clean, stash, restore, rebase, switch, new branch, or new worktree
  occurred. The operator's requested simple existing-checkout workflow was
  preserved.
- No subagent was used. Codex remained the only writer.
- Outcome-blind protocol commit:
  `9c66983e0baa7439e957df83a25b72bd945310a4`.
- Dirty-file owner before the implementation commit: Codex owns the exact
  V5.67 files listed below and no unrelated work.

## Decision

V5.67 implemented and replayed one independently designed NexusTrade-inspired
risk-balanced candidate:

`nexustrade_monthly_independent_spy_sma_50_200_inverse_volatility_capped`.

It uses the frozen V5.64 eleven-stock filter and SPY SMA50/200 trend parent as
building blocks but makes no authentic NexusTrade replay or lineage claim. It
replaces equal weighting with 60-session inverse sample volatility,
deterministic capped proportional water-filling, a `0.20` per-name cap, and
maximum stock exposure `min(1, 0.20 * eligible_count)`. The failed V5.65 binary
high-volatility cash overlay is absent.

The canonical route is `continue_local_research`. The candidate passed frozen
parent reproduction, allocation integrity, cost sensitivity, concentration,
turnover, and every fold-drawdown subgate. It failed the full SPY baseline
gate, the portfolio-level static cross-asset gate, and the targeted parent
risk-balance gate. No threshold was changed and no same-thesis retry occurred.

No preview, shadow, paper promotion, broker route, third sleeve, or live path
was created.

## Outcome-blind preregistration

- Protocol ID:
  `v5_67_nexustrade_monthly_risk_balanced_allocation_v1`.
- Tracked protocol:
  `docs/design/v5_67_nexustrade_monthly_risk_balanced_allocation.md`.
- Protocol SHA-256:
  `17f86b8eafd7e67e6816603cb1bf06fa96a734c7b7d9094d30e68ec85690505e`.
- Preregistration commit before implementation or V5.67 outcome inspection:
  `9c66983e0baa7439e957df83a25b72bd945310a4`.
- Parameter search performed: `false`.
- Fixed volatility lookback: 60 simple adjusted-close returns from 61 prices.
- Fixed volatility statistic: sample standard deviation, denominator 59.
- Fixed maximum target weight: `0.20`.
- Fixed target stock exposure: `min(1, 0.20 * eligible_count)`.
- No volatility floor, annualization for weights, leverage, covariance model,
  shrinkage, or discretionary residual assignment.

Pinned frozen inputs:

- V5.64 protocol SHA-256:
  `f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0`.
- V5.64 engine SHA-256:
  `66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5`.
- V5.64 preregistration artifact SHA-256:
  `4c54d6c14de2579d1671a8257be6750bd49a586296d041fea95a3fe40e376e3c`.
- V5.64 result artifact SHA-256:
  `ca9f0177b0b42a3ec888b13799fdd3d39c5c5ae9caacedd2245a0292b42396da`.
- V5.64 summary artifact SHA-256:
  `af3b527db055c4568db7125047dad97ba9492fa55d5bbf2c3a6b6cc9002f41df`.
- V5.64 manifest artifact SHA-256:
  `96338ea291f40ea7d9a1ea4a0d45dd17ed5a60c856333150655701f64841dcf6`.
- V5.66 exclusion-boundary protocol SHA-256:
  `2a2d03030b2ec74ca3a0682ca94163ea5b28218c1b452b4f10664fc182733227`.
- Frozen V5.64 preregistration structured equality: passed.
- Frozen V5.64 result structured equality: passed.
- Frozen V5.64 summary text equality: passed.

## Canonical data and chronology

- Provider/provenance: Tiingo EOD, previously acquired and validated by V5.63.
- Canonical field: `adjusted_close` from Tiingo `adjClose`.
- Adjustment semantics: split-and-dividend-adjusted EOD price.
- Adjusted OHLCV claimed: `false`.
- Symbols:
  `AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST, SPY`.
- Deterministic class-share mapping: `BRK-B->BRK-B`.
- Coverage: `2019-01-02` through `2025-03-28`.
- Sessions per symbol: 1,569; total rows: 18,828.
- Missing/unexpected sessions and weekend rows: none.
- Session reference limitation: observed Tiingo SPY EOD dates, not an
  independently represented official exchange calendar.
- Canonical CSV:
  `runs/operator_input/multi_etf_adjusted_daily_canonical.csv`.
- Canonical CSV SHA-256:
  `d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575`.
- V5.63 manifest SHA-256:
  `e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1`.
- Training: `2021-12-31` through `2024-03-24`.
- Untouched OOS boundary: `2024-03-24` through `2025-03-28`; first observed
  session `2024-03-25`; 254 sessions.
- Continuous-state folds:
  - `2024-03-25` through `2024-07-24`, 84 sessions;
  - `2024-07-25` through `2024-11-21`, 85 sessions;
  - `2024-11-22` through `2025-03-28`, 85 sessions.
- V5.67 network data acquisition: `false`; only validated local inputs were
  read.

## Canonical V5.67 evidence

Moderate-cost full OOS:

- Candidate total return: `0.096781606110768419788213151`.
- Candidate maximum drawdown: `0.1478735763442904011077737735`.
- Candidate Sharpe ratio: `0.5114376714141200289454086450`.
- Candidate one-way turnover: `11.18728067817860285454479686`.
- Candidate trade count: 117.
- Candidate maximum absolute contribution share:
  `0.2639599520452363061570888890`.
- Frozen parent total return: `0.216081928040488296986127071`.
- Frozen parent maximum drawdown: `0.1542831596611372101415857540`.
- Frozen parent Sharpe ratio: `1.014004230219840814526456983`.
- Frozen parent one-way turnover: `11.72946592903657074232868409`.
- Frozen parent maximum absolute contribution share:
  `0.3730114389000650407684443910`.

Targeted parent comparison:

- Maximum-drawdown delta: `-0.0064095833168468090338119805`.
- Total-return delta: `-0.119300321929719877197913920`.
- Sharpe-ratio delta: `-0.5025665588057207855810483380`.
- One-way-turnover delta: `-0.54218525085796788778388723`.
- Fold drawdown deltas:
  `-0.0067991489641868343288413667`, `0`, and
  `-0.0110537731098603395736969907`; all no-worse subgates passed.
- Concentration requirement: passed.
- Full-OOS drawdown improvement of at least `0.01`: failed.
- Return delta of at least `-0.02`: failed.
- Nonnegative Sharpe delta: failed.
- Targeted risk-balance gate: failed.

Other fixed gates:

- Cost gate: passed. Source-fee OOS return
  `0.101702110762891420264894379`; moderate degradation
  `0.004920504652123000476681228`; moderate SPY edge
  `0.017152912197919108216698478`.
- SPY baseline gate: failed all four windows. Full-OOS return edge was positive
  but drawdown delta was `0.0470149534782633633333054451`; fold three also had
  negative return edge.
- Portfolio-level cross-asset gate: failed. Candidate lagged static equal
  weight in full OOS and folds one/two; it beat it only in fold three.
- Eleven symbols received nonzero OOS targets and eight had positive arithmetic
  gross contributions.
- Allocation integrity: passed.
- OOS target difference sessions versus frozen parent: 209.
- Maximum observed OOS target weight: exactly `0.20`.
- Partial-cash OOS sessions: 25.
- Cap violations: 0; exposure violations: 0.
- Final route: `continue_local_research`.

## Artifact evidence

Ignored output root:
`runs/v5_67_nexustrade_monthly_risk_balanced_allocation`.

- `preregistration.json` SHA-256:
  `6ee1e62efb4b20f94896b2e29fb022081b6c762f4c7da8de7f67f631bc747d6e`.
- `risk_balanced_results.json` SHA-256:
  `76de6eabe410c082b53ff123af31dccdf4704f78c3380bd6d6e8e8de24b2276f`.
- `risk_balanced_summary.md` SHA-256:
  `99fac23b5cbeae076bb0249d6741e98ca95a433b11cad994ed92abd2bcf886f1`.
- `manifest.json` SHA-256:
  `0bcf77f91d4b92a9d85f566e0e0c946fc19be4b56bd28982eeb741d23dee1519`.
- The second canonical replay was byte-identical for all four artifacts.

External performance remains `untrusted_external_evidence`. The `29.64%`
table versus `29.41%` chart discrepancy remains preserved. Source metrics did
not control ranking, gating, routing, or promotion. The authentic V5.58 route
remains hard-gated on candidate-specific historical bar/data mode, slippage,
and 365-day-clock evidence; V5.67 infers none of them.

## Credential and safety audit

- Boolean-only preflight before tests and replay:
  - `APP_PROFILE` loaded: `false`;
  - `APP_PROFILE=paper`: `false`;
  - broker/Alpaca credential and endpoint aliases loaded: `false`;
  - Tiingo credential aliases loaded: `false` in the process;
  - NexusTrade credential aliases loaded: `false`.
- An unloaded Tiingo key may remain in `.env`; V5.67 did not read `.env` or
  require the key because canonical data was already local.
- Credential value requested, inspected, printed, returned, copied, or
  persisted: `false`.
- NexusTrade access or mutation: none.
- Market-data network access: none.
- Broker account/order/position access: none.
- Broker mutation: none.
- Paper mutation: none.
- Receipt status: not applicable.
- Reconciliation status: not required; no broker operation occurred.
- Paper promotion: `false`.
- Live authorization: `false`; live broker, order, trading, and capital activity
  remain prohibited.
- V5.57 sleeve ownership, reconciliation, auditing, and caps are unchanged:
  - `$25.00` maximum entry-order notional;
  - `$60.00` maximum aggregate marked SPY entry exposure;
  - one broker order per secure cycle;
  - two sleeve intents per UTC day.
- No third sleeve was added.

## Verification

- Outcome-free focused subset after correcting three local assertion/order
  mismatches: `8 passed, 1 deselected` in `5.04s`.
- Canonical full-replay test: `1 passed, 8 deselected` in `14.58s`.
- Final focused V5.67, frozen V5.64 parent, dependency-direction, and
  import-safety regression: `67 passed` in `73.91s`.
- Mandatory `./scripts/verify_offline.ps1`: `PASS`; 109 guard tests passed in
  `116.36s`; full suite explicitly skipped.
- A monolithic `python -m pytest` attempt produced no failure output but hit its
  external 45-minute command timeout; it is not counted as a test result.
- The first exact-node eight-shard full runner completed 10,207 nodes and had
  one unrelated V5.36 PowerShell wrapper timeout under resource contention.
  That exact node passed alone in `26.59s`.
- Final repository-owned full verifier:
  `./scripts/verify_offline.ps1 -Full -Shards 4`.
  - canonical node IDs: 10,208 across 508 files;
  - collection equivalence: passed;
  - execution equivalence: passed;
  - 10,203 passed, 5 skipped, 0 failures, 0 errors;
  - all four shards completed without timeout;
  - final offline verification result: `PASS`;
  - wall time: `1,721.6s`.
- The five skips are the existing credential-gated integration tests.
- Final `git diff --check`, `git status --short`, exact source diff, and
  untracked `src/tests` hygiene are run after this handoff update and before
  staging/commit.

## Tracked implementation slice

- `docs/OPERATOR_RUNBOOK.md`
- `docs/agent_context/active_implementation.md`
- `docs/deterministic_core.md`
- `scripts/run_nexustrade_monthly_risk_balanced_allocation.ps1`
- `src/algotrader/research/nexustrade_monthly_risk_balanced_allocation.py`
- `tests/unit/test_nexustrade_monthly_risk_balanced_allocation.py`

The separately committed outcome-blind protocol is:

- `docs/design/v5_67_nexustrade_monthly_risk_balanced_allocation.md`

## Next milestone

Freeze V5.67 as a failed risk-balanced value hypothesis. Do not tune the
60-session lookback, `0.20` cap, water-fill rule, partial-cash exposure,
chronology, costs, or gates from these inspected outcomes, and do not create a
no-submit shadow.

A decision-justified V5.68 may be an attribution-only diagnostic that
decomposes the frozen V5.67 parent-relative return loss into pure
inverse-volatility sizing, the fewer-than-five partial-cash rule, and
candidate-owned filled-event state carry under the same chronology and costs.
That diagnostic must preregister exact counterfactuals and reconciliation
identities, create no candidate or route, and perform no parameter search. Any
later candidate requires a new independent thesis and a fresh outcome-blind
protocol rather than tuning V5.67.

Next implementation action after this handoff: run final Git hygiene, stage
only the exact tracked slice, commit it coherently, and verify a clean branch.
