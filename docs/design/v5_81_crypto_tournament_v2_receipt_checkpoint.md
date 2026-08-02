# V5.81 Crypto Tournament V2 receipt checkpoint

## Decision

- Classification: `receipt_checkpoint_current_hard_time_gate`.
- Candidate evaluations exposed: 0.
- Rankings or preferences exposed: 0.
- Selected candidate: none; empty zero-property placeholder only.
- Terminal scoring performed: false.
- Paper or broker eligible: false.
- Live authorized: false.

V5.81 advances one current-clock, receipt-only data checkpoint. It does not
score, rank, prefer, tune, combine, promote, or execute a candidate. The hard
scoring boundary remains `2026-08-13T00:00:00Z`, conditional on the authentic
receipt for the final `2026-08-12T23:00:00Z` bar. Scheduler publication grace
makes `2026-08-13T00:05:00Z` the earliest normal terminal attempt.

## Takeover and writer ownership

- Worktree: `C:\Users\danie\.codex\worktrees\c029\algo_trader`.
- Branch: `codex/v5.62-nexustrade-source-data-unblock`.
- Clean takeover HEAD:
  `e2fe8dffcab66c2330bc806933c7d4bcdd4de4c1`.
- Branch, HEAD, status, staged/unstaged diffs, untracked files, and the active
  handoff were inspected before change.
- No reset, clean, stash, restore, rebase, branch switch, or worktree creation.
- Exactly one implementation writer was retained.

## Exact receipt and coverage

A write-free readiness check identified the next completed-hour window. One
authorized network cycle then used the opaque Windows credential reference
through the guarded market-data-only adapter. Its receipt records:

- source `alpaca_market_data_crypto_bars_v1beta3`;
- exact symbols `BTCUSD`, `ETHUSD`, and `SOLUSD`;
- `1Hour` / `us`;
- request as-of `2026-08-02T14:00:00Z`;
- inclusive window `2026-08-02T12:00:00Z..2026-08-02T13:00:00Z`;
- 2 rows per symbol, 6 total, with no missing symbol;
- authorized, non-live endpoint, data-intake-only true;
- strategy evidence evaluation performed false.

After admission:

- embargo is complete at 24/24 hours per symbol through
  `2026-07-15T23:00:00Z`;
- OOS is 422/672 hours per symbol, 1,266 rows total, through
  `2026-08-02T13:00:00Z`;
- 250 hours per symbol and 750 rows total remain;
- receipt count is 3;
- next missing hour is `2026-08-02T14:00:00Z`, classified
  `waiting_for_calendar_hour` at the checkpoint clock;
- preregistration fingerprint remains
  `2ed9489543d8d21ab00d9f2f4000927b8012decf39882cb721cb2d1ce0b9376b`;
- state fingerprint is
  `1b84e722ab9fd5cfe98e37fb53cda7dd9f332cf6fd5114fa6f268b49c3d62f32`.

Artifact SHA-256 bindings:

- refresh delta:
  `011b088d13be58268d92645ac82a8bc97e6e2e27e958eec5a1dc69cc9c4f811c`;
- raw response:
  `1c6df5fa3b5c96f8365e099c58ddfaa9efe16b1ead2e8eddd9bcbf82277801c5`;
- refresh packet / admitted receipt:
  `5666f30f2c2c79ed9268c292e403c65721857fcccad91d5cc954c50ac7c3936a`;
- accrued OOS:
  `d283e88d51491fc38d8d4f193c8b8d6f22d1e22387f29bdb901e2eb360d42c44`;
- frozen state:
  `2cc6378ab82ba7bc2d66ac3c9d42f2e6389ccbb1b0e6bb783b5e7ac893805699`;
- receipt ledger:
  `13c7c7446302cd68984424c2578e897ca7063a6b6107b382971b6116ae14e4f1`;
- operating packet:
  `86e78da1d467485635e6e0806120d382905c613ab389490ed0d22b041808ae7c`.

Generated `runs/` files remain ignored evidence, never authority. No raw
price, return, metric, signal, target, score, rank, preference, or portfolio
outcome was inspected.

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
- Network-enabled acquisition cycles in V5.81: 1.
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
- Bounded full suite: 10,312 canonical tests across 520 files; 10,307
  passed, 5 skipped, 0 failures, and 0 errors.
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
