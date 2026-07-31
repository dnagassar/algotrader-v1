# Active Implementation

## Ownership and takeover

- Writer: Codex, sole implementation writer for this working tree.
- Working tree:
  `C:\Users\danie\.codex\worktrees\c029\algo_trader`.
- Branch: `codex/v5.62-nexustrade-source-data-unblock`.
- Takeover HEAD:
  `4ba261c88a4e1c5a52eb1e40a7af0c6853234b4a`.
- Branch, HEAD, status, staged diff, unstaged diff, untracked files, and this
  handoff were inspected before any change.
- Takeover was clean: staged, unstaged, and untracked sets were empty.
- No reset, clean, stash, restore, rebase, branch switch, new branch, or new
  worktree occurred.
- Codex remained the only writer. No subagent was used.
- The first full-suite attempt was interrupted externally and left no Python
  process. Status and HEAD were reverified before one clean full rerun.
- Dirty-file owner before the final local commit: Codex owns exactly the files
  listed under "Tracked implementation slice."
- Next action after this handoff update: run final hygiene checks, stage the
  coherent implementation slice, commit locally, and verify clean status.

## Decision

V5.65 implemented and replayed the separately preregistered, fixed
high-volatility defense for the frozen V5.64 SPY trend-regime composite.

The candidate routes to `continue_local_research`. It genuinely changed target
weights and forced the parent-risk-on portfolio to cash during 38 OOS
high-volatility sessions, but it did not repair drawdown or fold-two
underperformance:

- moderate-cost full-OOS return fell by
  `0.049040075355030398534951042` versus the frozen parent;
- moderate-cost full-OOS maximum drawdown worsened by
  `0.0169384341141393848779871026`;
- moderate-cost full-OOS Sharpe fell by
  `0.2148489431907056211091114236`;
- fold-two return remained below the static equal-weight comparator; and
- fold-two and fold-three drawdown both worsened versus the frozen parent.

The SPY baseline, cross-asset, and targeted parent-repair gates failed. The
cost gate passed. No `preview_review`, no-submit shadow, paper promotion,
broker path, or live path was produced.

V5.64 and V5.65 are both frozen. The authentic V5.58 route remains at the
demonstrated source-evidence hard gate for candidate-specific historical
bar/data mode, slippage, and the 365-day clock.

## Outcome-blind preregistration

- Protocol:
  `v5_65_nexustrade_monthly_independent_high_volatility_defense_v1`.
- Tracked protocol:
  `docs/design/v5_65_nexustrade_monthly_high_volatility_defense.md`.
- Final protocol SHA-256:
  `1b614cb9d9e310704a0f8adcda224a4c540054a70af2731bcd3ec9c9b44db0c5`.
- Outcome-blind commits:
  - `96aacf8` - preregister the V5.65 high-volatility defense;
  - `98359354ca5ada6b7aef5554bddf4a41e7166914` - pin the frozen
    parent protocol and engine dependencies.
- Both commits preceded canonical V5.65 outcome computation.

Frozen dependencies:

- V5.64 protocol SHA-256:
  `f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0`.
- V5.64 engine SHA-256:
  `66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5`.
- V5.64 protocol and engine altered by V5.65: `false`.

Fixed identity:

- Candidate:
  `nexustrade_monthly_independent_spy_sma_50_200_high_volatility_defense`.
- Frozen parent:
  `nexustrade_monthly_independent_spy_sma_50_200_regime_filter`.
- Parent strategy:
  `spy_sma_50_200_baseline`.
- Pairing role:
  `volatility_regime_filter`.
- Cross-asset comparator:
  `static_equal_weight_11_stock_buy_hold`.
- Parameter search performed: `false`.

Fixed volatility defense:

- SPY adjusted-close simple daily returns.
- 20-session sample realized volatility annualized by `sqrt(252)`.
- Expanding prior-only realized-volatility history.
- Nearest-rank `0.33` and `0.67` quantiles.
- At least 252 prior realized-volatility observations.
- Current and future observations excluded from current thresholds.
- `high_vol` when current realized volatility is at least the prior-only high
  threshold.
- `insufficient_history`, `low_vol`, and `normal_vol` do not force cash.
- Candidate holds the frozen V5.64 eligible target only while SPY SMA50 is
  above SMA200 and volatility is not `high_vol`; otherwise cash.
- Changed risk targets fill at the next observed adjusted close.
- Overlay fills update the candidate's own filled-buy/sell state.

The frozen V5.64 stock eligibility, 30-calendar-day filled-event rule, fill
timing, weight drift, chronology, comparators, metrics, and cost cases remain
unchanged.

## Canonical data evidence

- Provider: Tiingo EOD.
- Canonical field: `adjusted_close`, sourced from `adjClose`.
- Adjustment semantics: Tiingo-documented split-and-dividend-adjusted EOD
  prices.
- Adjusted OHLCV claimed: `false`.
- Symbols:
  `AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST, SPY`.
- `BRK-B` mapping: `BRK-B->BRK-B`.
- Coverage:
  `2019-01-02` through `2025-03-28`.
- Sessions per symbol: `1,569`.
- Total rows: `18,828`.
- Missing or unexpected sessions: none.
- Weekend rows: none.
- Session reference: observed Tiingo SPY EOD dates, not an independently
  represented exchange calendar.
- Canonical CSV:
  `runs/operator_input/multi_etf_adjusted_daily_canonical.csv`.
- Canonical CSV SHA-256:
  `d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575`.
- V5.63 manifest:
  `runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json`.
- V5.63 manifest SHA-256:
  `e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1`.
- V5.65 network acquisition: `false`; it used only the validated local input.

Chronology:

- Training:
  `2021-12-31` through `2024-03-24`.
- Untouched OOS:
  `2024-03-24` through `2025-03-28`.
- First observed OOS session:
  `2024-03-25`.
- OOS sessions:
  `254`.
- Fixed folds with no state reset:
  - `2024-03-25` through `2024-07-24`: `84` sessions;
  - `2024-07-25` through `2024-11-21`: `85` sessions;
  - `2024-11-22` through `2025-03-28`: `85` sessions.

## Candidate outcome

Source-fee-only:

- Training:
  - total return `0.613379009834834473216797252`;
  - maximum drawdown `0.1391320785633491817185399036`;
  - Sharpe `1.495569977134622109025696284`;
  - trades `180`;
  - turnover `11.13544257193430737681762847`.
- Full OOS:
  - total return `0.174398522716501509248493205`;
  - maximum drawdown `0.1703090312411216593141138433`;
  - Sharpe `0.8344721937814002335742297164`;
  - trades `121`;
  - turnover `15.70416390432810190672866051`;
  - invested-session percentage
    `85.82677165354330708661417323`.
- Fold returns:
  - fold one `0.141097709462859849909448836`;
  - fold two `0.107373878268983445942004959`;
  - fold three `-0.0706091597793318575586104458`.

Moderate friction:

- Full OOS:
  - total return `0.167041852685457898451176029`;
  - maximum drawdown `0.1712215937752765950195728566`;
  - Sharpe `0.7991552870291351934173455594`;
  - trades `121`;
  - turnover `15.70416390432810190672866051`.
- Fold returns:
  - fold one `0.139010185844455840847480965`;
  - fold two `0.105401853906819601410385009`;
  - fold three `-0.0730877226904713857735569033`.
- Fold maximum drawdowns:
  - fold one `0.1028816547447382668989194429`;
  - fold two `0.0942877628564643970350360156`;
  - fold three `0.1712215937752765950195728575`.

Genuine overlay evidence:

- OOS target-difference sessions versus frozen parent: `163`.
- First target-difference date: `2024-08-05`.
- Last target-difference date: `2025-03-28`.
- OOS high-volatility parent-risk-on forced-cash sessions: `38`.
- Fold one forced-cash sessions: `0`.
- Fold two forced-cash sessions: `20`.
- Fold three forced-cash sessions: `18`.
- Parent metadata only: `false`.

## Gate evidence

SPY baseline OOS gate: failed all four required source-fee-only windows.

- Full OOS:
  - return delta `0.094769828803652197676978532`;
  - drawdown delta `0.0699549940753133509400962852`;
  - Sharpe delta `0.2635897318495517705186155691`.
- Fold one drawdown delta:
  `0.0488605233607662506372784340`.
- Fold two:
  - return delta `0.007114071365574313753165205`;
  - drawdown delta `0.0327666431267225064028020916`;
  - Sharpe delta `-0.616526850927825547847433143`.
- Fold three:
  - return delta `-0.0125189998496133504820723764`;
  - drawdown delta `0.0699549940753133509400962858`.

Cost gate: passed.

- Source-fee-only OOS return:
  `0.174398522716501509248493205`.
- Moderate-cost OOS return:
  `0.167041852685457898451176029`.
- Source-fee-only SPY edge:
  `0.094769828803652197676978532`.
- Moderate-cost SPY edge:
  `0.087413158772608586879661356`.
- Return degradation:
  `0.007356670031043610797317176`.
- Edge broken by moderate cost: `false`.

Portfolio-level cross-asset gate: failed.

- Full-OOS moderate return versus static equal weight:
  `0.167041852685457898451176029` versus
  `0.185406109534062356979258751`, delta
  `-0.018364256848604458528082722`.
- Fold one delta:
  `0.025760872325082183373419601`, passed.
- Fold two delta:
  `-0.063850863637406597543220105`, failed.
- Fold three delta:
  `0.0162311482937646451437283320`, passed.
- Symbols held: `11`.
- Positive-contribution symbols: `7`.
- Maximum absolute contribution share:
  `0.2906150657890297683400113578`.

Targeted parent-repair gate: failed.

- Frozen-parent moderate OOS return:
  `0.216081928040488296986127071`.
- Frozen-parent moderate OOS maximum drawdown:
  `0.1542831596611372101415857540`.
- Frozen-parent moderate OOS Sharpe:
  `1.014004230219840814526456983`.
- Candidate-minus-parent:
  - return `-0.049040075355030398534951042`;
  - maximum drawdown `0.0169384341141393848779871026`;
  - Sharpe `-0.2148489431907056211091114236`.
- Fold one drawdown delta:
  `0.0000000000000000000000000000`, passed.
- Fold two drawdown delta:
  `0.0066066505878553830502072416`, failed.
- Fold three drawdown delta:
  `0.0346388396987748410805675295`, failed.

Final route: `continue_local_research`.

## Artifact evidence

Ignored output root:
`runs/v5_65_nexustrade_monthly_high_volatility_defense`.

- `preregistration.json` SHA-256:
  `8ab8fb25edf1ccb9803465fbc568b4b5348776c472b58c447a189ee677723190`.
- `defense_results.json` SHA-256:
  `e30c9c6f9d90f0d87c33607c71d1ec3e7c0055a245b88d06a469bfbc33709611`.
- `defense_summary.md` SHA-256:
  `1ff76c5c3fcb840794fbcd2e501f7300976f34557dd9aad3dcea35ebdd3f936e`.
- `manifest.json` SHA-256:
  `99c52a97d2f8d6ef88df844356dbd38e88859d2804c4db9cf166ae55cad48814`.
- Two canonical replays were byte-identical for all four artifacts.

External performance remains `untrusted_external_evidence`. The `29.64%`
table versus `29.41%` chart discrepancy remains preserved. Source metrics were
not used for ranking, gates, routing, or promotion.

## Credential and safety audit

- Preflight before implementation, replay, offline verification, and full
  pytest:
  - `APP_PROFILE` loaded: `false`;
  - `APP_PROFILE=paper`: `false`;
  - `APP_PROFILE=live`: `false`;
  - Alpaca/broker credential or endpoint aliases loaded: `false`;
  - `TIINGO_API_KEY` loaded: `false`;
  - NexusTrade credential aliases loaded: `false`.
- Credential value inspected, printed, returned, copied, or persisted:
  `false`.
- Market-data network access in V5.65: `false`.
- NexusTrade network or mutation access: `false`.
- Broker account/order/position access: `false`.
- Broker mutation: none.
- Paper mutation: none.
- Receipt status: not applicable.
- Reconciliation status: not required; no broker operation occurred.
- Paper promotion: `false`.
- No-submit shadow created: `false`.
- Live authorization: `false`.
- Live broker, orders, trading, and capital remain prohibited.
- V5.57 sleeve ownership, reconciliation, auditing, and caps are unchanged:
  - `$25.00` maximum entry-order notional;
  - `$60.00` maximum aggregate marked SPY entry exposure;
  - one broker order per secure cycle;
  - two sleeve intents per UTC day.
- No third sleeve was added.

## Verification

Focused implementation, dependency, and import verification after correction:

`python -m pytest tests\unit\test_nexustrade_monthly_high_volatility_defense.py tests\unit\test_dependency_direction.py tests\unit\test_import_safety.py`

- `56 passed` in `65.30s`.

Broader frozen-parent and shared-regime regression:

`python -m pytest tests\unit\test_nexustrade_monthly_high_volatility_defense.py tests\unit\test_nexustrade_monthly_independent_replication.py tests\unit\test_volatility_regime_evidence.py tests\unit\test_volatility_filtered_spy_sma_backtest.py tests\unit\test_dependency_direction.py tests\unit\test_import_safety.py`

- `83 passed` in `91.71s`.

Mandatory offline verification:

- `.\scripts\verify_offline.ps1`.
- Result: `PASS`.
- `109 passed` in `155.27s`.
- The script explicitly skipped the full default suite.

Full default verification:

- First launch: externally interrupted; process absence and repository state
  were verified before restarting.
- Clean full rerun: `python -m pytest`.
- `10,187 passed`, `5 skipped` in `2,147.52s` (`35:47`).
- Exit code: `0`.
- The five skips are credential-gated paper integration tests.

Final `git diff --check`, `git status --short`,
`git diff --name-only HEAD -- src`, and
`git ls-files --others --exclude-standard src tests` run after this handoff
update and immediately before staging/commit.

## Tracked implementation slice

- `docs/OPERATOR_RUNBOOK.md`
- `docs/agent_context/active_implementation.md`
- `docs/deterministic_core.md`
- `scripts/run_nexustrade_monthly_high_volatility_defense.ps1`
- `src/algotrader/research/nexustrade_monthly_high_volatility_defense.py`
- `tests/unit/test_nexustrade_monthly_high_volatility_defense.py`

The tracked preregistration design was committed before outcomes:

- `docs/design/v5_65_nexustrade_monthly_high_volatility_defense.md`

## Next milestone

Freeze V5.65 as a failed repair hypothesis. Do not tune its volatility
lookback, quantiles, threshold history, or gates after outcome inspection. Do
not implement a no-submit shadow because no `preview_review` route was earned.

The next decision-quality milestone should be an attribution-only V5.66
diagnostic, preregistered before computing its diagnostic outputs and creating
no candidate. It should decompose:

- the 38 high-volatility parent-risk-on forced-cash sessions;
- the 163 target-divergence sessions caused by the overlay and stateful
  filled-event carry;
- avoided versus missed constituent returns;
- turnover and cost increments;
- fold-two and fold-three drawdown path changes; and
- whether the harm came from the high-volatility classification itself,
  next-session execution, or the deliberately stateful rebalance interaction.

That diagnostic must remain offline, no-submit, and non-promotional. A new
candidate hypothesis should not be preregistered until the attribution is
complete. The authentic route may resume only if new candidate-specific
authoritative evidence supplies the historical bar/data mode, slippage, and
365-day clock.
