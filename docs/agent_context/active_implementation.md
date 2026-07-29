# Active Implementation

## Ownership

- Writer: Codex, sole implementation writer for this working tree.
- Branch: `codex/v5.59-nexustrade-authentic-composite`.
- Base HEAD: `021b55c10d17757d8ec865bf37de2e39f91da8e1`, the committed
  V5.58 NexusTrade research-intake milestone.
- V5.59 reached a demonstrated source-evidence hard gate. No production code,
  test, safety-contract, or paper-runtime file was changed.

## Takeover

- The checkout began detached at the exact expected V5.58 commit.
- Staged, unstaged, and untracked sets were empty.
- `APP_PROFILE_is_paper=false` and `APP_PROFILE_is_live=false`.
- All checked Alpaca and NexusTrade credential aliases were unloaded. Only
  boolean presence was inspected; no value was requested or exposed.
- A new feature branch was created only after that clean takeover.

## Authentic-source discovery

Safe read-only discovery covered authoritative public NexusTrade material:

- the public Strategy Library and exact-rule previews;
- the public marketplace and shared-portfolio detail pages;
- official NexusTrade documentation and founder-authored strategy/backtest
  articles;
- the public Aurora agent trace for SOXL single- and dual-filter research; and
- official developer/API documentation.

No user-controlled export was present. The browser session was not signed in,
no already-authorized NexusTrade connector/provider was installed, and no
OAuth or key-backed connection was opened. API/MCP documentation confirms that
non-public records require account-authorized OAuth or an API key. No key,
token, account identifier, login, subscription, purchase, write, or NexusTrade
backtest action was requested or attempted.

The strongest public paired evidence was the Aurora SOXL trace. It publishes
exact standalone and composite rules:

- standalone: SOXL price above its 20-day SMA; and
- paired: the same SOXL signal AND SPY above its 50-day SMA, with the same
  SOXL trend/position-loss exits and sizing variants.

It reports several regime results, but does not publish the exact trade counts,
explicit fee/slippage assumptions, or data mode. The same named regimes were
used iteratively to revise the strategy, so the public record also does not
establish an untouched chronological OOS designation. It therefore cannot
authorize a local adapter or composite replay.

## Machine-demonstrated intake gate

An ignored generated capture records one authentic, exact-rule, single-symbol
candidate from the official GPT o1 TQQQ retrospective:

`runs/v5_59_nexustrade_authentic_candidate_gate/gpt_o1_tqqq_partial_capture.json`

The exact published rules are:

- buy `$2,500` of TQQQ when SMA(50) is above SMA(200) and at least seven days
  have passed since the last filled TQQQ buy; and
- sell 100 percent of TQQQ when its 14-day rate of change is above 15.

The source explicitly reports a `2024-10-15` through `2025-07-12` retrospective
backtest and an approximately `-40%` return. It does not report enough evidence
to complete the V5.58 schema without invention.

The credential-free V5.58 wrapper completed and wrote:

`runs/v5_59_nexustrade_authentic_candidate_gate/intake/nexustrade_intake_report.json`

The input SHA-256 is
`e55c13fd22ff7e66cadc3016834d3b15c4092a298eeb318b5d443643de8bf1ed`.
The result is:

- `eligible_candidate_count=0`;
- `local_replay_status=not_run_no_eligible_candidates`;
- route `repair_intake_blockers`;
- source metrics not used for ranking or promotion; and
- paper promotion, broker access, broker mutation, network access from the
  intake, and live mutation all fixed false.

Exact blockers:

- `source_data_mode_missing`;
- `source_out_of_sample_validation_missing`;
- `source_cost_assumptions_missing`;
- `source_trade_count_missing`;
- `source_summary_metrics_missing`;
- `local_timeframe_adapter_required`; and
- `local_strategy_family_adapter_required`.

Because the candidate is not blocked solely by local-adapter needs, V5.59 did
not implement an adapter. Because no eligible standalone candidate exists,
V5.59 did not create or merely label a paired variant. No synthetic fills,
costs, trade counts, validation designations, metrics, rules, or backtest
periods were invented.

The configured canonical input
`runs/operator_input/multi_etf_adjusted_daily_canonical.csv` is also absent in
this worktree. The only tracked CSV files are three synthetic SPY unit-test
fixtures, which are not current canonical multi-asset research data. Local
chronological OOS, walk-forward, cost, baseline, cross-asset, standalone, and
paired-composite evaluation therefore did not run.

## Safety and unchanged operating contract

- Offline repository research only.
- Public NexusTrade network reads occurred only during acquisition discovery.
- The repository intake itself attempted no network access.
- No broker or broker credential provider was accessed.
- No paper submit, cancel, replace, close, liquidate, or other mutation
  occurred; there is no paper receipt or reconciliation event for V5.59.
- V5.57 sleeve ownership, reconciliation, auditing, and finite limits remain
  unchanged: `$25.00` maximum entry-order notional, `$60.00` maximum aggregate
  marked SPY entry exposure, one broker order per secure cycle, and two sleeve
  intents per UTC session day.
- No third paper sleeve was added.
- Live mode, live broker access, live orders, and live capital remain
  prohibited and unauthorized.
- No `preview_review` route was produced.

## Verification

- Focused V5.58 intake suite: 19 passed.
- Dependency-direction suite: 44 passed.
- Mandatory `scripts/verify_offline.ps1`: 109 passed; result `PASS`.
- Full default suite, required because the script skipped it: 10,162 passed
  and 5 skipped in 3,026.01 seconds; zero failures and zero errors.
- Verification remained credential-free, network-free, and broker-free.
- Final `git diff --check` passed.
- `git diff --name-only HEAD -- src` was empty.
- `git ls-files --others --exclude-standard src tests` was empty.
- Immediately before commit, `git status --short` contained only the staged
  handoff file.

## Files and generated state

Tracked change:

- `docs/agent_context/active_implementation.md` only.

Ignored generated evidence:

- `runs/v5_59_nexustrade_authentic_candidate_gate/`.

There are no production `src` changes and no untracked `src` or `tests` files.

## Next milestone

Resume only after both of these inputs are available without credential
disclosure:

1. a user-controlled NexusTrade export or an already-secure authenticated
   read-only provider record containing exact rules plus explicit start/end
   dates, data mode, untouched OOS or walk-forward method, fee and slippage
   assumptions, nonzero trade count, and total-return/max-drawdown/Sharpe
   metrics; and
2. current canonical daily bars for every required candidate, parent, baseline,
   and cross-asset symbol.

Re-run V5.58 first. Implement the smallest new family adapter only if the
authentic candidate is then blocked solely by `needs_local_adapter`. Any
lineage variant must combine the source candidate and its parent as an actual
composite signal and must be evaluated under identical local chronological OOS,
walk-forward, cost-sensitivity, baseline, and cross-asset gates. Only a locally
produced `preview_review` route may proceed to a later no-submit shadow design.
