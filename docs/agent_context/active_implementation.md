# Active Implementation

## Ownership

- Writer: Codex orchestrator, sole writer for this working tree.
- Branch: `codex/v5.58-nexustrade-research-intake`.
- Base HEAD: `db853ff6986876e48d6ca8bea069473e380de246`, the
  committed V5.57 strategy-owned paper sleeves milestone.
- V5.58 is a coherent local feature slice. No dirty-file owner should remain
  after the commit.
- The separate V5.51 worktree at
  `.claude/worktrees/v551-readonly-market-data-contract` was not modified.

## Takeover and stale-claim audit

- Takeover inspection found V5.57 clean with empty staged, unstaged, and
  untracked sets.
- The inherited V5.57 safety and commissioning claims remain current.
- Its next action, to wait only for the first scheduled paper cycles, became
  stale when the operator authorized a parallel NexusTrade research lane.
- Recent V5.55 through V5.57 milestones added secure unattended paper
  operation, selectable RSI, and concurrent strategy-owned sleeves. V5.58
  therefore does not add another review packet or hardening-only artifact. It
  creates an executable external-candidate-to-local-replay path while paper
  data observation continues independently.

## New operational capability

`scripts/run_nexustrade_strategy_intake.ps1` consumes a bounded local JSON
capture of NexusTrade strategy definitions and source backtest metadata. The
wrapper requires a credential-free `dev` environment and rejects paper/live
profiles, all Alpaca aliases, and a loaded NexusTrade API key. It never
contacts NexusTrade or a broker.

The intake:

- accepts at most 50 candidates and 2 MiB of UTF-8 JSON;
- requires exact NexusTrade HTTPS provenance, source rules, structured
  parameters, source backtest dates/data mode/validation/costs/trade count/
  summary metrics, lineage, and pairing role;
- rejects credential-like fields or text without echoing values;
- rejects duplicate IDs, current operating IDs, and exact mechanical
  duplicates of the controlled local set;
- retains incomplete evidence as `needs_source_evidence`;
- retains intraday, unsupported, or not-yet-modeled mechanics as
  `needs_local_adapter`; and
- translates complete supported daily candidates into immutable
  `StrategyChallengerCandidate` values for the existing challenger factory.

Supported local adapters are SMA crossover, time-series momentum, the existing
20-percent drawdown filter, and ETF relative momentum. Source metrics are
always marked untrusted and are never used for ranking or promotion. Local
replay applies the existing chronological OOS, walk-forward, cost-sensitivity,
baseline, and cross-asset gates.

The compact report emits an explicit route for every candidate:
`repair_intake_blockers`, `await_or_repair_local_data`,
`continue_local_research`, `reject`, or `preview_review`. No route creates an
execution intent or grants paper promotion.

## Safety contract

- Offline research only; no broker, execution, risk, scheduler, network, or
  credential-provider imports.
- No NexusTrade API call or broker connection was performed.
- No paper submit, cancel, replace, close, liquidation, or other broker
  mutation occurred.
- No source metric participates in local ranking or promotion.
- `paper_promotion_allowed=false`, `broker_access_attempted=false`,
  `network_access_attempted=false`, `broker_mutation_performed=false`, and
  `live_mutation_performed=false`.
- V5.57 paper limits and sleeve reconciliation remain unchanged:
  `$25.00` maximum entry order notional, `$60.00` aggregate marked SPY entry
  exposure, one order per cycle, and two sleeve intents per UTC session day.
- Live mode and live capital remain prohibited and unauthorized.

## Verification

- Default-test preflight:
  - `APP_PROFILE_is_paper=false`;
  - `APP_PROFILE_is_live=false`;
  - all Alpaca credential aliases unloaded;
  - network and paper-integration test flags unloaded.
- New NexusTrade intake suite: 19 passed.
- Challenger/dependency/import regression suites: 74 passed.
- Existing external-intake boundary suites: 79 passed.
- Mandatory repository offline verification: 109 passed, result `PASS`.
- Full default suite: 10,163 passed and 4 skipped in 3,417.69 seconds; zero
  failures and zero errors.
- Syntax compile check passed.
- Final `git diff --check` and Git hygiene checks must be rerun after staging.

## Files

- `src/algotrader/research/nexustrade_strategy_intake.py`
- `scripts/run_nexustrade_strategy_intake.ps1`
- `tests/unit/test_nexustrade_strategy_intake.py`
- `docs/deterministic_core.md`
- `docs/OPERATOR_RUNBOOK.md`
- this sole mutable handoff.

## Next action

Obtain one real NexusTrade candidate capture with exact rules and source
backtest metadata through a user-controlled export or a separately authorized
read-only acquisition process. Do not place an API key in the intake JSON or
load one into the offline wrapper.

Run the intake against current canonical daily bars. Implement a new local
strategy-family adapter only for a candidate that is blocked solely by
`needs_local_adapter` and has complete source evidence. Compare standalone and
declared paired/lineage variants under the same local OOS and cost gates.
Advance only a locally produced `preview_review` route into a separate
no-submit shadow design; do not add a third paper sleeve from source-reported
performance.

The scheduled V5.57 SMA and RSI cycles remain an independent observation task.
Stop on any sleeve/broker mismatch, pending sleeve intent, ambiguous broker
state, or nonterminal reconciliation rather than editing the ledger or
bypassing readiness.
