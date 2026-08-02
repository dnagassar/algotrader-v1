# V5.80 Crypto Tournament V2 pre-score readiness

## Terminal decision

- Classification: `pre_score_receipt_current_hard_time_gate`.
- Frozen candidate count: 9 across BTCUSD, ETHUSD, and SOLUSD.
- Candidate evaluations exposed: 0.
- Rankings exposed: 0.
- Selected candidate present: false.
- Terminal scoring performed: false.
- Paper or broker eligible: false.
- Live authorized: false.

V5.80 does not score, rank, prefer, tune, combine, or promote a candidate. It
restores receipt-bound OOS accrual through the latest completed hour available
at the acquisition boundary, repairs the secure acquisition wrapper, and
closes the easiest future-clock bypass at supported production CLIs.

The contractual scoring boundary remains `2026-08-13T00:00:00Z`, conditional
on an authentic receipt that includes the final `2026-08-12T23:00:00Z` bar.
The normal scheduler has a five-minute publication grace, so its earliest
ordinary terminal fetch/scoring attempt is `2026-08-13T00:05:00Z`.

## Takeover and writer ownership

- Worktree: `C:\Users\danie\.codex\worktrees\c029\algo_trader`.
- Branch: `codex/v5.62-nexustrade-source-data-unblock`.
- Clean takeover HEAD:
  `f3357c518409653db1646949944c3ef6efce2416`.
- No reset, clean, stash, restore, rebase, branch switch, or new worktree.
- Exactly one implementation writer was retained.
- Three bounded agents performed read-only time-gate, receipt, and test-gap
  audits and made no repository or external-state mutation.

## Discovery initialization provenance

The current worktree initially had no V2 generated state or default V1 source
files. The existing guarded V1 source and receipt in the user-owned primary
checkout were used through their original receipt-bound path; neither file was
copied, edited, normalized by hand, or made authoritative.

- Discovery CSV SHA-256:
  `65db4f1aa09b8c45a8d8fcaf9f4e2b965a7d5814c859fa3125416d7497908137`.
- Discovery receipt SHA-256:
  `33a6c09e47b86f11e3b28d6421293253b5571cfe5484e77a6b76057ea5dd1570`.
- Frozen preregistration fingerprint:
  `2ed9489543d8d21ab00d9f2f4000927b8012decf39882cb721cb2d1ce0b9376b`.
- Frozen discovery window:
  `2026-01-16T00:00:00Z..2026-07-14T23:00:00Z`.
- Frozen discovery rows: 12,960 normalized rows, 4,320 per symbol.
- Explicit isolated-gap imputations: 3 total, one per symbol.
- Frozen preregistration artifact SHA-256:
  `36c72d2b2014c6e4a407a81f84de7ccaa792b1cca3ad299c9343409ac0542b57`.
- Frozen discovery artifact SHA-256:
  `ecf4f99e92c8ba0a549c32236978b4a9a955d1305818a916f2051ddc5d5fbb1e`.

The first initialization attempt from the current working directory failed
closed on the receipt's exact output-path binding. Initialization succeeded
only by resolving the receipt in its original checkout while explicitly
writing generated V2 state to this worktree.

## Current receipt-bound coverage

One explicitly authorized, guarded, data-intake-only acquisition cycle ran at
`2026-08-02T12:00:00Z` for the exact inclusive window
`2026-07-15T00:00:00Z..2026-08-02T11:00:00Z` and only BTCUSD, ETHUSD, and
SOLUSD at 1Hour / `us`.

- Embargo: 24/24 raw hours per symbol; common frontier
  `2026-07-15T23:00:00Z`; complete.
- OOS: 420/672 raw hours per symbol; common frontier
  `2026-08-02T11:00:00Z`; 1,260 admitted rows.
- Remaining terminal window: 252 hours per symbol, 756 rows total.
- Refresh output SHA-256:
  `430bab008cca24173a1af5f678d6e48ea5b69032a064b38f24804f1f8febc031`.
- Refresh receipt SHA-256:
  `8887b8136c80cfa4ee87fad0fa710bec2893b89f1dd8fe1b7a25ba13e14807ec`.
- Accrued OOS artifact SHA-256:
  `5d608a0bb29e3ff0f5afd761a014a80a5a38cd5085b92499751df69b1fb51a0a`.
- Embargo artifact SHA-256:
  `fd75b29b5deee66c6129e44c185226632473fd99a997f1de8e0f4f07ccaaf9ed`.
- Frozen state artifact SHA-256:
  `f1929acee6688641d5c9a58ae2d2946208b18788684710a76b20d2e1be13273f`.
- Frozen state fingerprint:
  `c5d49fe9508711f7f7a2042e9ef47965b1702e81a4c9f75cb57a8f047ea5d592`.
- Receipt ledger SHA-256:
  `1e6fe6c27d4babd2d747417fddc8c3f935410561f36a4c58a974e90c1491b4d8`.

The acquisition receipt proves `data_intake_only=true`,
`strategy_evidence_evaluation_performed=false`, exact symbol/time/window
matching, a non-live endpoint, and no broker read, broker mutation, paper
submit, or live activity.

Alpaca's authoritative historical-bars reference identifies the endpoint as
`https://data.alpaca.markets/v1beta3/crypto/{loc}/bars` and supports explicit
symbol, start/end, and timeframe parameters:
<https://docs.alpaca.markets/us/reference/cryptobars-1>. Alpaca also documents
that a zero-volume crypto bar can use quote midpoint prices, so these bars are
market-data research inputs rather than executable fill evidence:
<https://docs.alpaca.markets/us/v1.1/docs/historical-crypto-data-1>.

## Outcome-blind implementation hardening

The supported Python CLI and scheduler previously accepted an arbitrary future
`as_of`. The receipt requirement still prevented scoring without fabricated
future inputs, but wall time was caller-controlled. V5.80 adds one shared UTC
operating-time validator at the production orchestration boundary:

- omitted `as_of` binds to current UTC;
- naive or malformed timestamps fail closed;
- explicit future timestamps fail before state or evaluation access;
- deterministic core functions retain injectable synthetic times for tests.

The PowerShell acquisition wrapper previously forwarded the two network flags
but omitted the secure provider, opaque non-secret reference, paper profile,
paper endpoint, and data endpoint required by the Python CLI. V5.80 now:

- forwards those exact public configuration values only in fetch mode;
- rejects blank secure parameters;
- rejects loaded ambient Alpaca credential aliases;
- rejects explicit secure-fetch parameters outside fetch mode;
- preserves the exact three-symbol, no-submit, no-account, no-order boundary.

## Limits of the seal

The seal is a governance and reproducibility boundary, not confidentiality
against a malicious local reader. Accrued raw bars remain readable, Python
private evaluators remain importable, and receipts are locally SHA-256-bound
rather than provider-signed trusted-time attestations. V5.80 blocks accidental
or supported-CLI future-time bypass; it does not claim to make local data or
Python computation inaccessible. No raw OOS inspection or private evaluator
call occurred in this milestone.

The installed Windows scheduler task remains disabled and references an older
worktree. V5.80 does not re-enable, rewrite, or register external scheduler
state. Current-hour receipt accrual must continue through explicit guarded
cycles until the terminal receipt exists.

## Safety receipt

- Secure credential reference available: true.
- Credential value exposed, printed, persisted, or placed in a command: false.
- Network-enabled acquisition cycles: 1.
- Broker/account/order/position reads: 0.
- Broker or paper mutations: 0.
- Live endpoint touches or live activity: 0.
- Candidate metrics, scores, rankings, preferences, or selected identity
  inspected: 0.
- V5.57 caps unchanged: $25 entry-order notional, $60 aggregate marked SPY
  entry exposure, one broker order per secure cycle, and two sleeve intents per
  UTC day.
- No third sleeve, execution adapter, paper promotion, or live authority was
  created.

## Verification

- Focused core/wrapper/scheduler suite: 49 passed.
- Expanded preregistration, OOS, wrapper, scheduler-repair, scheduler-task,
  shadow, dependency, and import suite: 166 passed.
- Offline safety verifier: PASS, 109 passed; full default suite explicitly
  skipped by that script.
- Bounded exact-node full default suite: 10,312 canonical tests across 520
  files; 10,307 passed, 5 skipped, 0 failures, 0 errors.
- Eight-shard collection equivalence: PASS.
- Eight-shard execution equivalence: PASS.
- Focused production-module compilation: PASS.
- Future production CLI timestamp rejection: observed before state access.
- Current waiting-hour fetch wrapper: accepted secure reference, performed no
  network fetch, and left candidate fields empty.

## Next authorized action

Continue current-clock, receipt-only accrual with ambient credential aliases
unloaded. Do not pass a future `as_of`, inspect raw OOS outcomes, import private
evaluators, rank candidates, or prefer a rule. At or after
`2026-08-13T00:05:00Z`, admit the authentic final receipt and allow the existing
one-shot terminal state machine to score. A passing result authorizes only the
already-preregistered no-submit shadow; it does not authorize paper or live
capital.
