# V5.82 Crypto Tournament V2 receipt checkpoint

## Decision

- Classification: `receipt_checkpoint_current_hard_time_gate`.
- Candidate evaluations exposed: 0.
- Rankings or preferences exposed: 0.
- Selected candidate: none; empty zero-property placeholder only.
- Terminal scoring performed: false.
- Paper or broker eligible: false.
- Live authorized: false.

V5.82 advances one current-clock, receipt-only data checkpoint. It does not
score, rank, prefer, tune, combine, promote, or execute a candidate. The hard
scoring boundary remains `2026-08-13T00:00:00Z`, conditional on the authentic
receipt for the final `2026-08-12T23:00:00Z` bar. Scheduler publication grace
makes `2026-08-13T00:05:00Z` the earliest normal terminal attempt.

## Takeover and writer ownership

- Worktree: `C:\Users\danie\.codex\worktrees\c029\algo_trader`.
- Branch: `codex/v5.62-nexustrade-source-data-unblock`.
- Clean takeover HEAD:
  `d8292d240a2e127095a6e5988c3aa33f1926790b`.
- Branch, HEAD, status, staged/unstaged diffs, untracked files, `AGENTS.md`, and
  the active handoff were inspected before change.
- No reset, clean, stash, restore, rebase, branch switch, or worktree creation.
- Exactly one implementation writer was retained.

## Exact receipt and coverage

A write-free readiness check identified the next completed-hour window. One
authorized network cycle then used the opaque Windows credential reference
through the guarded market-data-only adapter. Its receipt records:

- source `alpaca_market_data_crypto_bars_v1beta3`;
- exact symbols `BTCUSD`, `ETHUSD`, and `SOLUSD`;
- `1Hour` / `us`;
- request as-of `2026-08-02T15:00:00Z`;
- inclusive window `2026-08-02T14:00:00Z..2026-08-02T14:00:00Z`;
- 1 row per symbol, 3 accepted/new rows, zero exact duplicates, and no missing
  symbol;
- authorized, non-live endpoint, data-intake-only true;
- strategy evidence evaluation performed false.

After admission:

- embargo is complete at 24/24 hours per symbol through
  `2026-07-15T23:00:00Z`;
- OOS is 423/672 hours per symbol, 1,269 rows total, through
  `2026-08-02T14:00:00Z`;
- 249 hours per symbol and 747 rows total remain;
- receipt count is 4;
- next missing hour is `2026-08-02T15:00:00Z`, classified
  `waiting_for_calendar_hour` at the checkpoint clock;
- preregistration fingerprint remains
  `2ed9489543d8d21ab00d9f2f4000927b8012decf39882cb721cb2d1ce0b9376b`;
- state fingerprint is
  `24cf78a8d15703db243e34ec097c0535c6b48776c1aca3dc250f3948d841756a`.

Artifact SHA-256 bindings:

- refresh delta:
  `51aae51e7f7126d7ddb0f6dd5874d70151757a63d1261b1caef00c61b06534b9`;
- raw response:
  `0777fe2d1fea2f31338221a7347705411c3cfed4b187fb62946bf5846d579c69`;
- refresh packet / admitted receipt:
  `fcec87911b26467542bf56977eeced53a6b707a9545bb424ce36b2bba9d13230`;
- accrued OOS:
  `08a7a7b20911ee1d6225af494a12c2ddf1929c685fda3508f980347597bb3848`;
- frozen state:
  `4eddbe31d87b2f0dfa03669bac9be8ca7f9a0745db0ba16889c9a448646bd315`;
- receipt ledger:
  `6fc2baf0727049b885341ee01147002f89dd562d3ce63bb1e57049e1b75afbcb`;
- operating packet:
  `6c648c4923f93632d96106097ef797ff29aab21655b7642931a73c75f2fdb8b0`.

All seven hashes were reconciled again after the full test run. Generated
`runs/` files remain ignored evidence, never authority. No raw price, return,
metric, signal, target, score, rank, preference, or portfolio outcome was
inspected.

Alpaca documents the historical endpoint and explicit symbol, start/end, and
timeframe parameters at
<https://docs.alpaca.markets/us/reference/cryptobars-1>. It also documents
that zero-volume bars can use quote midpoint prices, so these inputs are
research market data rather than fill evidence:
<https://docs.alpaca.markets/us/v1.1/docs/historical-crypto-data-1>.

## Safety receipt

- Paper profile before offline verification: false.
- Broker credential aliases before offline verification: false.
- Network/integration test escapes: false.
- Opaque credential reference resolved inside the trusted adapter: true.
- Credential value exposed, printed, persisted, or placed in a command: false.
- Network-enabled acquisition cycles in V5.82: 1.
- Broker/account/order/position reads: 0.
- Broker or paper mutations: 0.
- Live endpoint touches or live activity: 0.
- Scheduler mutation: 0; the disabled old-worktree task remains unchanged.

V5.57 caps remain unchanged: $25 entry-order notional, $60 aggregate marked
SPY entry exposure, one broker order per secure cycle, and two sleeve intents
per UTC day. Receipt/reconciliation, auditing, sleeve ownership, and live
prohibitions are unchanged. No third sleeve or execution route was created.

## Verification

- Focused Crypto V2, dependency, and import suite: 166 passed.
- Offline verifier: PASS, 109 passed; full default suite explicitly skipped.
- Bounded full suite: 10,312 canonical tests across 520 files; 10,307 passed,
  5 skipped, 0 failures, and 0 errors.
- Eight-shard collection equivalence: PASS.
- Eight-shard execution equivalence: PASS.
- No source or test file changed.

## Limitation and next action

This is a governance/reproducibility seal, not local confidentiality. Raw bars
are readable, private evaluators are importable, and receipts are local hashes
rather than provider-signed trusted-time attestations.

Continue current-clock receipt-only accrual after the next hour completes. Do
not pass a future `as_of`, inspect raw OOS outcomes, call private evaluators,
rank, prefer, or tune. At or after `2026-08-13T00:05:00Z`, admit the authentic
terminal receipt and permit the existing one-shot scorer. A passing winner is
eligible only for the preregistered no-submit shadow and grants no paper or
live authority.
