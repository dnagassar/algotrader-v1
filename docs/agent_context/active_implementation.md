# Active implementation handoff

## Standing operating decision

The V5.85 operating posture is unchanged: the SPY SMA 50/200 and RSI(14)
paper lanes operate in real-paper no-submit visibility mode with enabled
Windows tasks, sleeves reconcile, and canonical adjusted SPY data refreshes
at 20:10 ET. Crypto Tournament V2 remains preserved with its unattended
collector operator-disabled; do not resume it without a new explicit operator
request. Validated alpha remains zero, no profitability claim is made, and
live capital remains prohibited behind a separate operator hard gate.

## Checkout and writer ownership

- Writer checkout: `C:\Users\danie\.codex\worktrees\c029\algo_trader`.
- Branch: `claude/v5.90-forward-shadow-infrastructure`, branched from the
  V5.89 closure tip after that merged to `main`.
- Exactly one implementation writer at a time.

## V5.90 forward-shadow infrastructure (built)

Implements Route 2 of the V5.89 diagnosis — the only route that can produce
evidence this program has not already contaminated.

- `src/algotrader/research/forward_shadow_registry.py`: strategy-agnostic
  registry and append-only observation ledger.
- `tests/unit/test_forward_shadow_registry.py`: seventeen tests.
- `scripts/run_forward_shadow.ps1`: credential-fail-closed CLI wrapper.
- `docs/design/v5_90_forward_shadow_infrastructure.md`: contract, operating
  instructions, and honest limitations.

Three properties are enforced mechanically, not by convention:

1. Gates, universe, costs, and the required observation count are hashed into
   an immutable `registration_fingerprint`; editing any of them afterward
   makes every later load fail closed.
2. Backfill is impossible — an observation is admissible only inside
   `registration_date < session <= recorded_at`, with strictly increasing
   sessions.
3. Peeking early cannot produce a verdict — before the frozen observation
   count is reached the status payload omits every metric and gate outcome
   entirely, with no override.

The ledger is hash-chained from the registration fingerprint, so editing,
reordering, or truncating it is detected. Policy fingerprint:
`62f48951559bbc91193cca0a9d3309e9f06ddf7770ea414d735cc7cc59fefed3`.

**No hypothesis is registered.** Choosing what to shadow is an operator
decision, and the tempting candidate — the V5.89
`no_canary_g4_always_offensive` ablation — is outcome-contaminated as a
historical claim. Registering it as a *forward* hypothesis is legitimate
because the forward window is untouched, but that is a deliberate on-record
choice, not a side effect of building the tool.

## Repository consolidation (done)

`origin/main` was fast-forwarded `600bf72..6035d68` after
`verify_offline.ps1 -Full -Shards 8` returned PASS at that tip. This
consolidated roughly thirty previously local-only lane commits spanning
V5.53 through V5.88. Local `main` and `origin/main` now agree at `6035d68`,
and every `codex/*` lane tip is an ancestor of `origin/main`. The push was a
clean fast-forward; no force, no history rewrite, no lost work. Older
`antigravity/*`, `relay/*`, and legacy `claude/*` branches remain
deliberately unmerged and untouched.

## V5.89 Keller Bold Asset Allocation (closed)

Operator-directed final alpha push, executed under the standing constraints:
no credential exposure, no paid services, no live capital.

- `docs/design/v5_89_final_alpha_push_plan.md` and
  `..._preregistration.md` (`e77eede`): frozen plan and protocol.
- `7dc2439`: HYG and TIP added to the adjusted-EOD allowlist across both
  execution modules, the refresh script, and their contract tests.
- `scripts/refresh_v589_baa_data.ps1`: seventeen exact GET-only Tiingo EOD
  requests through the existing adapter.
- `src/algotrader/research/baa_data_manifest.py`: outcome-blind admission.
- `src/algotrader/research/baa_tournament.py`,
  `tests/unit/test_baa_tournament.py`,
  `scripts/run_v589_baa_tournament.ps1` (`722363a`): frozen replay engine,
  thirteen tests, credential-fail-closed wrapper — all committed *before*
  the reveal, closing the disclosure gap V5.88 had to carry.
- `docs/design/v5_89_keller_bold_asset_allocation_terminal_decision.md` and
  `..._data_receipt.md`: closure and outcome-blind data evidence.

Route: `no_candidate_passed`. Both BAA-G4 and BAA-G12 failed all five gate
groups. The decisive finding is mechanistic: the canary defensive overlay
fired in 22 of 47 months and, versus an otherwise identical no-canary
ablation, cost the aggressive variant 18.14 annualized points and 0.821
Sharpe while buying no meaningful drawdown relief.

## Program diagnosis

`docs/design/v5_89_alpha_program_terminal_diagnosis.md` records the
program-level conclusion across sixteen tested families: zero validated alpha,
with a single dominant structural cause — every tested family is a
diversification or defense rule, and every scoreable OOS window is dominated
by an exceptional concentrated US-equity advance that the frozen SPY value
route requires candidates to match. The recommendation is to stop enumerating
published families and instead build forward-shadow infrastructure so one
registered hypothesis can accumulate uncontaminated evidence. Restating the
objective away from "beat SPY" is available but is an explicit operator
decision, not a retrofit.

## Verification

- Credential preflight: zero ambient credential-bearing environment
  variables before every offline run.
- `verify_offline.ps1 -Full -Shards 8` at `6035d68`: PASS
  (`bounded_full_suite=PASS`, offline guards 109 passed); `src`, `tests`, and
  `scripts` at that tip were byte-identical to what was pushed.
- Allowlist contract suites after the HYG/TIP change: 113 passed.
- `tests/unit/test_baa_tournament.py`: 13 passed.
- Tournament wrapper exited 0; two full replays byte-identical.
- `verify_offline.ps1 -Full -Shards 8` at the V5.89 tip `f3b81c3`: PASS
  (10,421 collected, 10,416 passed, 5 skipped, 0 failures, 0 errors, all
  eight shards exit 0, collection and execution equivalence PASS). `main` was
  fast-forwarded to `f3b81c3` and pushed on that evidence.
- `tests/unit/test_forward_shadow_registry.py`: 17 passed.
- Architecture and safety invariants after V5.90: 69 passed
  (dependency direction, broker mutation surface, network guard).
- The V5.90 forward-shadow wrapper was confirmed to exit 2 with
  `blocked_unsafe_environment` under a credential-bearing environment without
  echoing the sentinel value.

## Safety and trust

- Seventeen market-data requests were GET-only, destination-allowlisted, and
  recorded `token_value_recorded`, `market_data_token_value_printed`, and
  `market_data_token_value_written` as `false`. The credential was loaded only
  inside the trusted adapter boundary from a dotenv outside this checkout and
  was never read, printed, or persisted by any tool.
- No broker, account, order, or position access; no paper mutation; no live
  activity; no paid service.
- External source and tracker performance figures remained untrusted and
  controlled no rank, gate, or route.
- Existing caps, receipts, reconciliation, sleeve ownership, and live
  prohibitions are unchanged.

## Exact next action

The infrastructure is built and unused, which is the correct resting state.
The next action is an operator decision, not an implementation task: choose
whether to register a first forward-shadow hypothesis and, if so, which one.
Registering it means committing to wait out the frozen window — roughly six
months at 126 sessions — without a readable verdict, by design.

If a hypothesis is registered, wire one
`append_forward_shadow_observation` call per completed trading session into
the existing EOD refresh cadence, with targets computed causally from data
through the prior session.

Do not reopen, re-tune, combine, or rescue any closed candidate, and do not
promote any control or ablation on its historical numbers. The sealed Crypto
Tournament V2 reveal remains preregistered for `2026-08-13T00:00:00Z`. Live
capital remains a separate operator hard gate.
