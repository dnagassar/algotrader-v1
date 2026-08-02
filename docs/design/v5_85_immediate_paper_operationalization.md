# V5.85 Immediate Paper Operationalization Decision

Date: 2026-08-02

## Decision

The system's existing SPY paper lanes are operational without waiting for
Crypto Tournament V2, NexusTrade evidence, or any new research dataset.

The enabled operating strategies are:

- `spy_sma_50_200_training_wheel`, the operational baseline; and
- `spy_rsi_14_mean_reversion_paper`, the second bounded paper candidate.

Both produced healthy real-paper, no-submit `hold` receipts from the stable
primary checkout used by Windows Task Scheduler. A hold is a valid strategy
decision; no order was forced. Both scheduled tasks are enabled for the next
NYSE session and retain the secure two-pass mutation boundary.

This is paper operational readiness, not validated alpha, profitability, or
live-capital readiness. No external performance claim controls this decision.

## Scope and checkout integrity

- Writer checkout:
  `C:\Users\danie\.codex\worktrees\c029\algo_trader`.
- Existing branch:
  `codex/v5.62-nexustrade-source-data-unblock`.
- Clean continuation HEAD before this slice:
  `e128c5e71f6c7c08743425e6dd843ae5b9aaa43b`.
- No reset, clean, stash, restore, rebase, branch switch, or new worktree.
- Exactly one writer was preserved; bounded subagents inspected read-only.
- The stable scheduler checkout
  `C:\Users\danie\Desktop\algo_trader` remained source-clean and was not
  edited.

Crypto Tournament V2 remains preserved but its unattended collector is
operator-disabled. It is not an operational dependency and no new research
data is required for either SPY paper lane.

## Research boundary

No NexusTrade strategy adapter was added in this slice because the authentic
candidate-specific source data mode and slippage assumption remain unresolved.
Nothing was inferred or fabricated to make that route pass. Its external
performance remains untrusted and unused; the preserved `29.64%` table versus
`29.41%` chart discrepancy does not influence strategy ranking, paper
operation, or promotion. Optional source research and Crypto Tournament V2
can proceed independently without blocking the two existing SPY paper lanes.
## Necessary data, not speculative data

Only the data required by the already-implemented SPY operating lanes was
refreshed.

- Provider: Tiingo EOD through the repository's existing fixed-host, read-only
  market-data adapter.
- Symbol: SPY.
- Provider field: `adjClose`.
- Local semantic field: `adjusted_close`.
- Adjustment semantics: split-and-dividend adjusted; not an executable fill
  price and not adjusted OHLCV.
- Coverage: 1,905 sessions, `2019-01-02..2026-07-31`.
- Refresh delta: 336 new rows, 9 unchanged overlap rows, 0 revisions.
- Canonical path:
  `runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv`.
- Canonical SHA-256:
  `0ec56ce757a71945da587452f8a4c20b5fdd37e58af9aeab83cd935a92ad1dd9`.
- Raw response SHA-256:
  `ad42d6c908b9475def4f5499565bc1b4aa6e3f7b2401c1985ffb62d66a4e8c07`.
- Network activity: one Tiingo GET for this refresh.
- Tiingo `.env` present: true.
- Tiingo token available inside the trusted acquisition boundary: true.
- Token value printed, returned, or persisted: false.
- Broker/order/account access through the Tiingo adapter: false.

The stable scheduler checkout independently has canonical SPY data through
`2026-07-31`; its observed SHA-256 was
`16d77ae402d3ee761ca6ca63c80b0c8f6253369c02c8cd77ee501d909c2d3a90`.

## Historical M376 gate

V5.85 adds a one-purpose read-only adapter and wrapper. The adapter:

- accepts only the opaque Windows Credential Manager paper-observation
  reference;
- rejects ambient profile, credential, expected-account, and endpoint aliases;
- constructs only the fixed Alpaca paper endpoint;
- binds observations to the expected account without persisting its value;
- reads account status, positions, a bounded current open-SPY order set, and
  the historical order by exact ID;
- applies the unchanged strict identity, quantity, and terminal-state
  classifier; and
- exposes no submit, cancel, replace, close, liquidation, or live method.

A read-only audit found that the first draft's exact-ID response did not prove
the absence of a different open SPY order. That draft was not committed and
its result was discarded. The corrected implementation performs a real
bounded open-SPY read and has a regression test proving that another open SPY
order keeps the result blocked.

The corrected production receipt established:

- expected account match: true;
- exact historical order found: true;
- exact identity match: true;
- terminal decision: `m376_terminal_filled`;
- bounded current open-SPY read: performed;
- current open-SPY count: zero;
- M376-derived next-submit block: false;
- stage-accurate account/open-order read reporting: true;
- paper submit: false;
- broker mutation: false; and
- live authorization: false.

Corrected receipt SHA-256:

`217764341cb5083914b4550578450d1dc94122f4e46bb9636dd7ce7d4ecbe10f`

Append-only reconciliation ledger SHA-256 after the corrected record:

`8d9d9426315466709624cb4987ee402749138e889ff2fa5e8fbe53a0b8d9260c`

This closes only the inherited historical M376 gate. Every secure cycle still
reads current open orders independently and fails closed on any unsafe state.

## Strategy and sleeve evidence

The current writer checkout first exposed a sleeve-to-broker quantity mismatch
after the data refresh. The documented one-time no-submit sleeve adoption
assigned the existing SPY quantity to its owning SMA sleeve. It changed only
the local durable sleeve ledger and performed no broker mutation. A subsequent
normal no-submit cycle proved the persistent sleeve/broker match.

Writer-checkout sanitized receipt hashes:

- adoption receipt:
  `0030d24fc82c26c2ddb7dbed546123ba878bcd366e49d2233a9ed66b08183374`;
- normal post-adoption SMA receipt:
  `5fb45ae5547e0eb0cee300ac0ccd35b694d1f03c2ea0531fa62d53d0940ce2b7`.

The exact stable primary checkout used by Task Scheduler then produced:

- SMA: `healthy_no_action`, `hold`, selected strategy correct, sleeve match
  true, broker read true, no blockers, submit/mutation/live false; receipt
  SHA-256
  `7927312d2c744c1759e1b57042cfa202cd7a6effc56978285dada65e29464057`.
- RSI: `healthy_no_action`, `hold`, selected strategy correct, sleeve match
  true, broker read true, no blockers, submit/mutation/live false; receipt
  SHA-256
  `ff9abb6aa4f19cd9549e4b66a3a11af1e9003d4af812c924a31ccf49c0327e4d`.

No order was warranted by either signal and no paper order was submitted.

## Scheduler state

Read-only host inspection established:

- `algo-trader-secure-spy-paper-cycle`: present, enabled, Ready, last result
  0, next trigger `2026-08-03T09:31:00-04:00`;
- `algo-trader-secure-spy-rsi-paper-cycle`: present, enabled, Ready, last
  result 0, next trigger `2026-08-03T09:38:00-04:00`; and
- `spy-eod-market-data-refresh`: present, enabled, Ready, last result 0, next
  trigger `2026-08-03T20:10:00-04:00`.

The strategy tasks invoke the stable primary checkout with paper mutation
explicitly enabled, but an order is possible only inside the NYSE window when
the strategy is actionable and every fresh account, endpoint, data, open-order,
position, sleeve, cap, journal, readiness, receipt, and reconciliation gate
passes. Task installation does not authorize live mode.

## Safety result

- Ambient offline-test profile/credential alias count: zero.
- Credential values requested from the operator: false.
- Credential values printed, returned, persisted, or placed in commands: false.
- Read-only paper account/order/position access: performed through the secure
  provider boundary.
- Paper broker submission, cancel, replace, close, or liquidation: none.
- Local sleeve-ledger adoption: performed and reconciled.
- Live endpoint access or live activity: none.
- Live authorized: false.
- Source/external metrics trusted for ranking or promotion: false.
- Profit guaranteed or claimed: false.

Unchanged finite paper caps:

- USD 25 maximum entry-order notional;
- USD 60 maximum aggregate marked SPY entry exposure;
- one broker order per secure cycle; and
- two strategy-sleeve intents per UTC day.

## Verification

- Corrected M376 focused suite: 8 passed.
- Final affected lifecycle/dependency/import suite: 89 passed in 60.10
  seconds.
- Canonical `scripts/verify_offline.ps1 -Full -Shards 8`: PASS in 1,476.3
  seconds.
- Offline safety guards: 109 passed.
- Full default corpus: 10,351 collected; 10,346 passed; 5 skipped; zero
  failures and zero errors.
- Eight shard exits: all zero; collection and execution equivalence: PASS.
- `git diff --check`: PASS in the verifier.
- Exact final source diff and untracked `src/tests` hygiene are rechecked
  immediately before commit.

## Limit and next milestone

The system can now operate its two existing bounded paper strategies without
waiting for speculative research data. It still has zero independently
validated alpha and therefore cannot honestly be called profitable or
live-capital ready. Live capital remains a separate operator hard gate.

The next milestone is operational observation, not parameter hunting: allow
the enabled tasks to run on the next NYSE session, inspect their sanitized
receipts and terminal reconciliation, and accumulate forward paper evidence.
Optional research can proceed independently without blocking the operating
paper system.