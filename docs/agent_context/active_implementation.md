# Active implementation handoff

## Milestone and checkout

V5.69 Monthly Relative-Momentum Confirmation is implemented, replayed, and
verified. It is a completed offline research candidate with route
`continue_local_research`; it does not qualify for `preview_review` and creates
no shadow, paper, broker, order, or live authority.

- Sole implementation writer: current Codex task.
- Branch: `codex/v5.62-nexustrade-source-data-unblock`.
- Clean takeover HEAD: `5d20201c350acb9d7ce043645ca3cc07ed521e36`.
- V5.69 outcome-blind preregistration commit:
  `d1b4e3e5f22bcd364c63dc24e6536c89977a9a37`.
- Takeover staged, unstaged, and untracked sets were empty.
- No reset, clean, stash, restore, rebase, branch switch, or extra worktree was
  used.
- One explicitly requested read-only research agent produced a decision memo;
  it changed no files and did not share writer authority.

## Frozen V5.69 thesis

Protocol:
`docs/design/v5_69_nexustrade_monthly_relative_momentum_confirmation.md`
(`a83ade6896ec7b6703af3afc51f922d0e7f98376a230f71a8c7957bf138690e5`).

The candidate uses the exact V5.64 source-rule eligibility set and SPY
SMA50/200 regime. At each source-rule rebalance it calculates fixed
126-observed-session stock and SPY returns, retains eligible stocks with
strictly positive return that strictly exceeds SPY, ranks by descending excess
return with canonical symbol-order ties, selects at most five, and equal
weights the selected set. No selection means cash.

The V5.64 30-calendar-day-since-last-filled-buy OR filled-sell state,
next-session adjusted-close fills, continuous chronology, four cost cases,
comparators, and portfolio accounting remain unchanged. V5.65-V5.68 signals,
outcomes, volatility rules, attributions, and symbol-removal ideas are excluded.
No parameter search occurred.

## Canonical input and provenance

- Provider: Tiingo EOD local canonical import.
- Field: `adjClose` mapped to `adjusted_close`.
- Semantics: split/dividend-adjusted EOD price; adjusted OHLCV is not claimed.
- Symbols: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST,
  and SPY; deterministic `BRK-B->BRK-B` mapping.
- Coverage: 2019-01-02 through 2025-03-28, 1,569 common observed Tiingo SPY
  sessions and 18,828 rows.
- Training: 2021-12-31 through 2024-03-24.
- OOS boundary: 2024-03-24 through 2025-03-28; first observed OOS session
  2024-03-25, 254 sessions.
- Canonical CSV:
  `d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575`.
- Canonical manifest:
  `e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1`.

Observed Tiingo SPY dates are the session reference; no separate official
exchange-calendar claim is made. Authentic NexusTrade replay remains gated on
candidate-specific bar mode, slippage, and 365-day clock semantics. The source
29.64% table versus 29.41% chart discrepancy remains preserved and unused.

## V5.69 decision evidence

The frozen V5.64 parent reproduced exactly before V5.69 output. Selection
integrity passed:

- 229 OOS desired-target sessions differ from the parent;
- 12 OOS selection decisions;
- all 11 stocks selected at least once OOS;
- maximum selected count five; and
- zero count, nonpositive-momentum, SPY-relative, ranking, or equal-weight
  violations.

Moderate-friction full-OOS metrics:

- V5.69 return `0.177788532572316363402867516`, drawdown
  `0.1661807211451763258225628051`, Sharpe
  `0.7690004111468448006479270327`, turnover
  `13.74397606780400165706202713`.
- Frozen V5.64 parent return `0.216081928040488296986127071`, drawdown
  `0.1542831596611372101415857540`, Sharpe
  `1.014004230219840814526456983`, turnover
  `11.72946592903657074232868409`.
- Parent-relative return `-0.038293395468171933583259555`, drawdown delta
  `0.0118975614840391156809770511`, Sharpe delta
  `-0.2450038190729960138785299503`, turnover delta
  `2.01451013876743091473334304`.
- Fold return deltas versus parent: `-0.041732992572060867139336199`,
  `0.046845131929549318820478123`, and
  `-0.0311700812227324338638562678`.

The cost gate passed. The full SPY-window gate, static-equal-weight cross-asset
gate, and independent selection-value gate failed. V5.69 returned more than
SPY over full OOS but exceeded the fixed drawdown tolerance and failed the
third fold. It beat static equal weight only in fold two. Maximum contribution
share was `0.2917944607997642803766314656`, within the 0.50 cap.

Decision: freeze and close the exact V5.69 thesis. Do not tune the 126-session
lookback, five-name count, thresholds, state, symbols, fills, costs,
comparators, or gates. Do not use constituent outcomes for symbol removal.

## Generated artifacts

Ignored output root:
`runs/v5_69_nexustrade_monthly_relative_momentum_confirmation`.

- `preregistration.json`:
  `e9ff888fec75ffd236cd7f76f529aaeea62a62790072b3e7cb4c3748bd324a01`
- `relative_momentum_results.json`:
  `0641574bb28fa91a3428c8bb96ba416c24644abf9df51e56b19000548d9887a5`
- `relative_momentum_summary.md`:
  `88103b67f8427d356fa8ea2a2994a0e1d4a1c674b6063a05b12f3d096b1fb4ba`
- `manifest.json`:
  `98cd391c1fe5a33a2e2a4033149423c06d4d4f6e105921d7f7d14fdab32f3d0c`

A second canonical replay was byte-identical.

## Verification

- Fast V5.69 contract/safety tests: 8 passed, 1 deselected.
- Canonical V5.69 replay test: 1 passed, 8 deselected.
- V5.69/V5.64/dependency/import suite: 67 passed.
- `scripts/verify_offline.ps1 -Full -Shards 8`: PASS.
  - safety guards: 109 passed;
  - canonical collection: 10,225 node IDs across 510 files;
  - execution: 10,220 passed, 5 skipped, 0 failures, 0 errors;
  - every shard exit zero with no timeout;
  - collection and execution equivalence: PASS.

The first four-shard invocation exceeded its 30-minute host wrapper timeout;
the detached exact workers were allowed to complete without interruption. An
authoritative documented eight-shard rerun then completed successfully and
supersedes the lost wrapper summary.

## Safety and credentials

Boolean-only preflight was false for paper/live profile and every broker,
NexusTrade, and Tiingo process alias. An unloaded `.env` Tiingo credential was
not read or needed. No credential value was requested, printed, persisted, or
placed in a command or artifact.

No network, NexusTrade mutation, broker/account/order/position access, paper
mutation, receipt, reconciliation, or live activity occurred. Reconciliation
and broker receipts are not applicable. Live remains unauthorized.

V5.57 safeguards remain unchanged: $25 entry-order notional, $60 aggregate
marked SPY entry exposure, one broker order per secure cycle, and two sleeve
intents per UTC day. No third sleeve exists.

## Tracked implementation slice

- `docs/design/v5_69_nexustrade_monthly_relative_momentum_confirmation.md`
  (already committed separately before implementation/output)
- `docs/OPERATOR_RUNBOOK.md`
- `docs/agent_context/active_implementation.md`
- `docs/deterministic_core.md`
- `scripts/run_nexustrade_monthly_relative_momentum_confirmation.ps1`
- `src/algotrader/research/nexustrade_monthly_relative_momentum_confirmation.py`
- `tests/unit/test_nexustrade_monthly_relative_momentum_confirmation.py`

## Tightened alpha decision and next milestone

Stop searching the consumed 2024-03-25 through 2025-03-28 OOS window. V5.64
is the strongest completed stock-alpha incumbent, but it is not promotion
eligible: its SPY-window, fold, and composite-value failures remain material.

The only permitted next stock-alpha milestone is one outcome-blind,
preregistered forward confirmation of the exact frozen V5.64 composite on a
genuinely uninspected Tiingo extension after 2025-03-28. Commit the protocol,
fixed terminal date, three chronological folds, hashes, unchanged V5.64
mechanics, costs, comparators, and gates before acquiring or inspecting the
extension. Carry existing holdings, pending fills, and filled-event state
continuously into the extension.

All gates must pass. A pass may support only a later no-submit shadow review.
A failure closes the stock-filter family. Forbid all parameter, lookback,
threshold, weighting, symbol, constituent-removal, overlay, stop, leverage,
short, comparator, fold, endpoint, and gate variants. No other same-window
candidate or attribution is justified.
