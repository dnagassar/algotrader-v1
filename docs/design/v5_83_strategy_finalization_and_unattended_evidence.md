# V5.83 strategy finalization and unattended evidence path

## Decision

The strategy program is narrowed and finalized as follows:

- Validated alpha today: 0.
- Sole active alpha-finalization route: the frozen nine-candidate Crypto
  Tournament V2.
- Operational paper baseline: `spy_sma_50_200_training_wheel`, labeled
  `paper_lab_only`, `not_live_authorized`, and `profit_claim=none`; it is not
  validated alpha.
- Every V5.64-V5.78 stock/ETF candidate remains terminally closed. No failed
  rule is retuned, combined, rescued, or relabeled.
- Live-capital ready: false. Live authorized: false.

Crypto V2 is the selected shortest currently preregistered path that does not
fabricate data. Every approved Tiingo stock/ETF symbol has already been
consumed by a closed preregistered protocol, and no alternative route is
presently frozen and ready. A new family would require a new primary rationale,
outcome-blind protocol, allowlist/data contract, and untouched evidence; it is
not treated as a faster route without that prior work.

## Authentic timetable

- Crypto V2 terminal OOS closes after the authentic
  `2026-08-12T23:00:00Z` bar.
- Earliest normal terminal fetch/scoring attempt:
  `2026-08-13T00:05:00Z`.
- If no candidate passes every frozen gate, the route closes without rescue.
- If at least one candidate qualifies, frozen deterministic ranking selects at
  most one winner. Its V5.24/V5.25 shadow begins at the first complete hour,
  normally `2026-08-13T01:00:00Z`.
- The shadow requires 168 new hours with no backfill, so its earliest normal
  end is `2026-08-20T01:00:00Z`.
- Only a passing shadow may reach the preregistered V5.26 bounded-paper-probe
  review envelope; it grants no paper mutation authority. If separately
  evidence-cleared and authorized, the downstream envelope remains selected
  symbol only, long/cash, USD 10 maximum notional and principal, USD 2 durable
  loss halt, one position/open order/entry/exit, one cancel per order, zero
  replacements, and 168-hour maximum duration.

There is no honest current live-capital date. Genuine shadow and paper receipts,
independent flat reconciliation, aggregate risk, durable alert/recovery proof,
and a separate live-readiness review must all pass first. `AGENTS.md` and the
runtime interlock continue to prohibit live access and orders.

## Current authentic receipt

One current-clock, data-intake-only Alpaca crypto-bars cycle admitted the exact
`2026-08-02T19:00:00Z` hour for BTCUSD, ETHUSD, and SOLUSD at 1Hour / `us`.

- The successful automatic cycle admitted 4 rows per symbol; 12 accepted/new, zero exact duplicates, and no missing symbol.
- Embargo: 24/24 hours per symbol, complete.
- OOS: 428/672 hours per symbol through `2026-08-02T19:00:00Z`.
- Remaining: 244 hours per symbol, 732 rows total.
- Receipt count: 6; next missing hour: `2026-08-02T20:00:00Z`.
- Candidate evaluations/ranking: empty; selected candidate: none; terminal
  scoring: false.
- Preregistration fingerprint:
  `2ed9489543d8d21ab00d9f2f4000927b8012decf39882cb721cb2d1ce0b9376b`.
- State fingerprint:
  `56c03a5fe45557b8dd6ba80f26ff2d127fe4b29f2c7cf1abaf4ea3d3ecb9b660`.

Artifact SHA-256 bindings:

- delta `81c503665abeddde70580d660ab7833f5b22ab89bc2554911e46107584b3fe7a`;
- raw response `0c3a669a6e0d0bf355dc68793c7f998f778ed183747fde637f243b5d6d08c52c`;
- receipt `719c1d1585daaa55ad80e5c745c55aff0360b5dd84edc6ebacd0a521dd97a7d3`;
- accrued OOS `4cf4e249811a15af466ef07c186dfa0e45447cdada88d488c4726526461fadd4`;
- frozen state `f62efd9a1d21c76714d8efc0adc97f0795b85a7ee26b704329b120211248a188`;
- receipt ledger `2464c337d43dc34f494a8a4a13d58936ada80b6f2208b55a325447e4bd4f9bb8`;
- operating packet `671a5d4b60c52754d844ebbaa929ea65b18a416d938b6b4400fa55759d9324d7`.

No raw price, return, metric, signal, target, score, rank, preference, or
portfolio outcome was inspected.

## Unattended accrual commission

The old Windows task was disabled, last failed, and referenced the obsolete
`antigravity-current` worktree. Its checked-in replacement also launched a
general V5.35 market-data plus paper-observation wrapper instead of the exact
Crypto V2 accrual path.

V5.83 repairs and commissions the smaller receipt-only lane:

- task `\crypto-tournament-v2-oos-scheduler`;
- existing worktree only; no new worktree or branch;
- state `Ready`, task enabled true, trigger enabled true;
- hourly trigger at five minutes after the hour;
- next observed run time after commissioning: `2026-08-02T21:05:00Z`;
- least-privilege `InteractiveToken`, network-required, `IgnoreNew`, 15-minute
  execution limit;
- exact action: hardened `run_crypto_tournament_v2_forward_oos.ps1`, current
  clock, `market_data_fetch`, explicit market-data and network authorization;
- no paper-broker-read, submit, cancel, replace, close, liquidation, account,
  or live flag;
- no credential value in the task or command. The wrapper resolves only its
  opaque Windows Credential Manager reference inside the trusted adapter.

The source XML remains disabled by default. Registration creates a disabled
task unless explicit `-ActivateTask` accompanies `-RegisterTask`; activation
requires exactly the task and trigger disabled nodes before changing them.

This direct lane deliberately does not claim the older SQLite scheduler job
ledger. Concurrency/idempotency comes from Task Scheduler `IgnoreNew`, the V2
exclusive operating/state locks, immutable request/receipt validation, and the
append-only receipt ledger. The first automatic run completed at `2026-08-02T20:05:01Z` with Task Scheduler result `0`; the advanced receipt and state hashes above prove the scheduled-run outcome.

Because `InteractiveToken` is used, the workstation must remain signed in,
powered, and network-connected; the task cannot wake the machine.

## Remaining operational gates

- M376 SPY remains conservatively nonterminal; overlapping SPY submit stays
  blocked pending a canonical read-only terminal reconciliation. This does not
  block Crypto V2 market-data accrual.
- A tournament winner still needs a dormant winner-bound mutation adapter and
  candidate-owned crypto sleeve before any paper execution route.
- Fresh winner-scoped venue, lifecycle, fill/exit, independent-flat, durable
  alert/recovery, and aggregate-risk evidence remain absent.
- The existing V5.57 limits remain unchanged and do not transfer: USD 25 SPY
  entry-order notional, USD 60 aggregate marked SPY entry exposure, one broker
  order per secure cycle, and two SPY sleeve intents per UTC day.
- No third SPY sleeve, crypto capital allocation, live credential, live
  endpoint, or live authority is created.

## Safety and source trust

- Network operations in V5.83: one authenticated crypto market-data fetch.
- Broker/account/order/position reads: zero.
- Broker or paper mutations: zero.
- Live endpoint touches or live activity: zero.
- Credential values exposed, printed, persisted, or placed in commands: false.
- External performance remains untrusted and unused.

Alpaca's endpoint and request semantics are documented at
<https://docs.alpaca.markets/us/reference/cryptobars-1>. Zero-volume bars can
use quote midpoint prices, so the inputs remain research data rather than fill
evidence:
<https://docs.alpaca.markets/us/v1.1/docs/historical-crypto-data-1>.

## Next implementation milestone

The first automatic receipt is proven. Continue unattended authentic-hour
accrual through terminal close without hourly Git milestones or early scoring.
At or after `2026-08-13T00:00:00Z`, run the frozen terminal evaluation once. A
sealed winner must pass the accepted 168-hour no-submit shadow and fresh
winner-scoped paper qualification before any capital route. If no candidate
passes, close the route. Live capital remains a separate operator hard gate.
