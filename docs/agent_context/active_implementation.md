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
- Branch: `codex/v5.86-validated-alpha-search`.
- The V5.88 implementation session was interrupted after the data admission
  commit `7e9c672` with the engine, test, and wrapper files authored but
  uncommitted. A takeover writer verified the dirty files against the frozen
  v2 protocol, ran verification, executed the tournament, and completed the
  closure. No reset, clean, stash, restore, rebase, or branch switch was
  performed; the three dirty files were committed exactly as found.
- Exactly one implementation writer at a time.

## Implemented slice (V5.88)

- `src/algotrader/research/butler_source_family_tournament.py`: frozen
  offline replay of the preregistered Butler Exhibit 3/4 source family —
  hash-validated inputs, six-month average-rank selection, Exhibit 4
  60-return sample-volatility sizing with individual 20% cap and implicit
  cash, drifted one-way-turnover cost model at 0/5/15 bps, four controls,
  genuine 80/20 composite, frozen terminal gates, and double byte-identical
  replay.
- `tests/unit/test_butler_source_family_tournament.py`: ten tests covering
  preregistration freezing, tie ranks, selection and sizing, simulator lag
  and cost mechanics, real-data structure, tamper blocking, output-path
  containment, credential-bearing wrapper blocking, and full atomic replay.
- `scripts/run_v588_butler_source_family_tournament.ps1`: fail-closed wrapper
  that blocks on any credential-bearing environment variable.
- `docs/design/v5_88_butler_exhibit3_4_source_family_terminal_decision.md`:
  closure evidence.

## Outcome

Route: `no_candidate_passed`. Both candidates beat the static equal-ten
baseline and passed common viability; Exhibit 3 passed its closest-ablation
gate; but both failed the SPY value route and the portfolio-level composite
gate. The route is closed without tuning. Full evidence and pinned hashes are
in the terminal decision document; local run artifacts live under
`runs/v5_88_butler_exhibit3_4_source_family/evaluation/` (gitignored),
artifact manifest SHA-256
`a0427681bfde7216fe2595cf5a7786dd41f8711ed345bdfdbb6d3017f406fa3c`.

## Verification

- Credential preflight: zero ambient credential-bearing environment
  variables observed before offline tests and the tournament run.
- Focused suite `tests/unit/test_butler_source_family_tournament.py`:
  10 passed in 41.78 seconds, including the real-data structure test and the
  full atomic two-replay tournament test.
- The V5.88 change adds three new files and modifies no previously tracked
  source, test, or script file, so the existing suites' regression surface is
  unchanged; the full offline verifier was not rerun for this closure.
- Wrapper run exited 0 with
  `butler_source_family_tournament_status=completed`.

## Safety and trust

- The tournament and tests are offline; no network, NexusTrade, broker,
  account, order, or position access; no paper mutation; no live activity.
- No credential value was requested, printed, returned, or persisted.
- External source performance figures remained untrusted and controlled no
  rank, gate, or route.
- Existing caps, receipts, reconciliation, sleeve ownership, and live
  prohibitions are unchanged.

## Exact next action

Allow the enabled SMA and RSI paper tasks to keep running and accumulate
forward no-submit evidence. The three preordered source families (V5.86,
V5.87, V5.88) are all terminally closed without tuning; do not reopen,
re-tune, or rescue any of them. A fourth source family requires a new
outcome-blind preregistration before any data request or scoring. Live
capital remains a separate operator hard gate.
