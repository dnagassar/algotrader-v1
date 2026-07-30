# Active Implementation

## Ownership and takeover

- Writer: Codex, sole implementation writer for this working tree.
- Working tree:
  `C:\Users\danie\.codex\worktrees\c029\algo_trader`.
- Branch: `codex/v5.62-nexustrade-source-data-unblock`.
- Takeover HEAD:
  `f9a1a4c7e7c0c2dabd56463ea47834df2c8f64d9`.
- The branch, HEAD, status, staged diff, unstaged diff, untracked files, and this
  handoff were inspected before any change.
- Takeover was clean: staged, unstaged, and untracked sets were empty.
- No reset, clean, stash, restore, rebase, branch switch, new branch, or new
  worktree occurred.
- Codex remained the only writer. No subagent was used.
- Dirty-file owner before the final local commit: Codex owns exactly the files
  listed under "Tracked implementation slice."
- Next action after this handoff update: run final hygiene checks, stage the
  coherent slice, commit locally, and verify a clean status.

## Decision

V5.64 implemented and replayed an explicitly independent, assumption-disclosed
replication of the NexusTrade Monthly Equal-Weight Dynamic Stock Filter. It is
not an authentic replay of the March 2025 NexusTrade historical run and does
not inherit the source's metrics or lineage.

Both the standalone and genuine SPY SMA50/200 risk-regime composite route to
`continue_local_research`. Neither cleared every preregistered baseline,
walk-forward, portfolio, and drawdown gate. No `preview_review` route or
no-submit shadow design was produced.

The authentic V5.58 route remains at the demonstrated source-evidence hard
gate: candidate-specific material still does not state the historical
bar/data mode, slippage assumption, or whether the 365-day minimum uses
calendar days or observed trading sessions.

## Preregistration and claim boundary

- Protocol:
  `v5_64_nexustrade_monthly_independent_replication_v1`.
- Tracked protocol:
  `docs/design/v5_64_nexustrade_monthly_independent_replication.md`.
- Final tracked protocol SHA-256:
  `f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0`.
- Outcome-blind preregistration commits:
  - `787d22f` - preregister independent replication;
  - `97893f5` - clarify the self-referential manifest-hash contract;
  - `1229383a7bb8302ef38fd475f12cf7b802c19b47` - correct contradictory
    cost-gate wording.
- All three commits preceded outcome computation.

Preserved source rules:

- Stock universe:
  `AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST`.
- Equal weights among eligible stocks.
- A stock is eligible when at least one and at most two conditions are true:
  - adjusted close is above SMA30;
  - adjusted close divided by its 365-session rolling minimum is at most
    `1.05`;
  - stock RSI14 is below `28` and SPY RSI14 is above `33`.
- Constant sort value `1`, descending; it does not alter the eligible set.
- Rebalance eligibility preserves the stateful condition of at least 30
  calendar days since the last filled buy OR last filled sell. It does not use
  the repository's first-session-of-calendar-month helper.

Disclosed independent assumptions:

- Tiingo daily `adjusted_close` is the sole price field.
- "365 day minimum" is interpreted as 365 observed sessions.
- RSI14 uses the repository-consistent simple rolling gain/loss arithmetic.
- Signals use information through a session's close and fill at the next
  observed session's adjusted close.
- A missing prior filled buy or sell satisfies its elapsed-time condition.
- Weights drift between filled rebalance events.
- Source fee assumption: `1` basis point per traded notional.
- Independent base slippage assumption: `0` basis points.
- Cost scenarios:
  - zero: `0` fee / `0` slippage basis points;
  - source-fee-only: `1` / `0`;
  - low: `1` / `1`;
  - moderate: `1` / `4`.
- Initial equity is frozen at `$10,000`.

Chronology:

- Source training interval:
  `2021-12-31` through `2024-03-24`.
- Untouched OOS interval:
  `2024-03-24` through `2025-03-28`.
- First observed OOS session: `2024-03-25`.
- OOS sessions: `254`.
- Walk-forward windows, with no state reset at their boundaries:
  - `2024-03-25` through `2024-07-24`: `84` sessions;
  - `2024-07-25` through `2024-11-21`: `85` sessions;
  - `2024-11-22` through `2025-03-28`: `85` sessions.

Comparators and composite:

- SPY comparator: repository-supported `spy_sma_50_200_baseline`.
- Cross-asset comparator: static equal-weight buy-and-hold of the eleven-stock
  universe.
- Genuine composite:
  `nexustrade_monthly_independent_spy_sma_50_200_regime_filter`.
- Parent: `spy_sma_50_200_baseline`.
- Role: `risk_regime_filter`.
- The exact standalone eligible set is held only while SPY SMA50 is above
  SMA200 and is otherwise cash.
- Overlay-induced fills affect the composite's own filled-event state.
- OOS target weights differed from the standalone on `238` sessions, from
  `2024-03-25` through `2025-03-28`; parent-metadata-only is `false`.

## Canonical adjusted-data evidence

Provider and adjustment contract:

- Provider: Tiingo EOD.
- Provider documentation:
  `https://www.tiingo.com/documentation/end-of-day`.
- Provider symbology documentation:
  `https://www.tiingo.com/documentation/general`.
- Canonical price field: `adjusted_close`.
- Provider source field: `adjClose`.
- Tiingo documents CRSP-style split-and-dividend adjustment semantics for its
  EOD adjusted prices.
- Raw provider `open`, `high`, `low`, `close`, and `volume` are preserved.
- Adjusted OHLCV claimed: `false`.
- `BRK-B` canonical-to-provider mapping: `BRK-B->BRK-B`.
- Session reference: observed Tiingo SPY EOD dates, not an independently
  represented official exchange calendar.

Exact input contract:

- Coverage and warm-up:
  `2019-01-02` through `2025-03-28`.
- Symbols: all eleven stocks plus SPY.
- Observed sessions per symbol: `1,569`.
- Pretraining sessions per symbol: `756`.
- Training sessions per symbol: `559`.
- OOS sessions per symbol: `254`.
- All symbols match the observed SPY session set.
- Missing or unexpected sessions: none.
- Weekend rows: none.
- Combined local CSV:
  `runs/operator_input/multi_etf_adjusted_daily_canonical.csv`.
- Combined rows: `18,828`.
- Combined CSV SHA-256:
  `d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575`.
- V5.63 data manifest:
  `runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json`.
- V5.63 manifest SHA-256:
  `e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1`.
- V5.64 validates both hashes and the final tracked protocol hash before
  computing any result.

No network acquisition was needed in V5.64. The canonical input was the
previously acquired deterministic local Tiingo artifact.

## Replay outcomes

Standalone:
`nexustrade_monthly_independent_daily_close_365_session`.

- Source-fee-only training:
  - total return `0.290512330640418985960933144`;
  - maximum drawdown `0.3877013774011843371759739934`;
  - Sharpe `0.4358980959593545253496739767`;
  - trades `248`;
  - turnover `28.05158773908067965579651043`.
- Source-fee-only OOS:
  - total return `0.157936481260720201747758286`;
  - maximum drawdown `0.1369641692255930030752423095`;
  - Sharpe `0.8295698321507958917284069448`;
  - trades `125`;
  - turnover `8.645265315858123645596831452`.
- Source-fee-only fold returns:
  `0.066660182883622713991724952`,
  `0.098282714893710126692817777`,
  `-0.0115732177508758881450909113`.
- Moderate-cost OOS:
  - total return `0.15393809547224208128327251`;
  - maximum drawdown `0.1372230993945879997990740272`;
  - Sharpe `0.8089943227069184619212207479`.
- Moderate-cost fold returns:
  `0.065852640117436223202258853`,
  `0.096794786931809247221311157`,
  `-0.0129026902469634218061178671`.
- Cost gate: passed.
- Source-fee-only SPY return edge: `0.078307787347870890176243613`.
- Moderate-cost SPY return edge: `0.074309401559392769711757837`.
- Cost degradation: `0.003998385788478120464485776`.
- SPY baseline gate: failed in all four required windows. Representative
  failures include full-OOS drawdown delta `0.03661` above the allowed `0.01`,
  fold-two return delta `-0.00198`, and fold-two Sharpe delta `-0.68196`.
- Cross-asset gate: failed. Moderate OOS return was
  `0.15393809547224208128327251` versus static equal-weight
  `0.185406109534062356979258751`; folds one and two also lost to the static
  basket.
- Breadth/concentration subgates passed: `11` symbols held, `9` positive
  contributors, maximum absolute contribution share approximately `0.2002`.
- Route: `continue_local_research`.

Composite:
`nexustrade_monthly_independent_spy_sma_50_200_regime_filter`.

- Source-fee-only training:
  - total return `0.59476307025619301464245999`;
  - maximum drawdown `0.1943764886074641993354466680`;
  - Sharpe `1.326145026728890315954027233`;
  - trades `193`;
  - turnover `13.74206322626763735778694624`.
- Source-fee-only OOS:
  - total return `0.221802803022493191164357381`;
  - maximum drawdown `0.1538286550596086030202139121`;
  - Sharpe `1.041384072176297492978233560`;
  - trades `117`;
  - turnover `11.72946592903657074232868409`.
- Source-fee-only fold returns:
  `0.141097709462859849909448836`,
  `0.157895363036824477726733459`,
  `-0.0752827295335290642152499261`.
- Moderate-cost OOS:
  - total return `0.216081928040488296986127071`;
  - maximum drawdown `0.1542831596611372101415857540`;
  - Sharpe `1.014004230219840814526456983`.
- Moderate-cost fold returns:
  `0.139010185844455840847480965`,
  `0.156941101972361738937882036`,
  `-0.0771651722541292969480332419`.
- Cost gate: passed.
- Source-fee-only SPY return edge: `0.142174109109643879592842708`.
- Moderate-cost SPY return edge: `0.136453234127638985414612398`.
- Cost degradation: `0.005720874982004894178230310`.
- SPY baseline gate: failed in all four required windows. Full-OOS drawdown
  delta was `0.05347`; fold-one and fold-two drawdown deltas were `0.04886`
  and `0.02699`; fold-three return delta was `-0.01719`.
- Cross-asset gate: failed only in fold two, where composite return
  `0.156941101972361738937882036` was below static equal-weight
  `0.16925` (rounded).
- Breadth/concentration subgates passed: `11` symbols held, `8` positive
  contributors, maximum absolute contribution share approximately `0.373`.
- Composite-value gate: failed. OOS moderate-cost return and Sharpe improved
  over standalone by approximately `0.06214` and `0.205`, but maximum
  drawdown worsened by `0.01706`, above the allowed `0.01`.
- Route: `continue_local_research`.

Comparator OOS metrics:

- SPY SMA50/200 baseline, source-fee-only and moderate:
  - total return `0.079628693912849311571514673`;
  - maximum drawdown `0.1003540371658083083740175581`;
  - Sharpe `0.5708824619318484630556141473`.
- Static equal-weight eleven-stock basket, moderate:
  - total return `0.185406109534062356979258751`;
  - maximum drawdown `0.1581265630478511304556469519`;
  - Sharpe `0.8047084327666832178980889690`.

## Generated artifact evidence

Ignored output root:
`runs/v5_64_nexustrade_monthly_independent_replication`.

- `preregistration.json` SHA-256:
  `4c54d6c14de2579d1671a8257be6750bd49a586296d041fea95a3fe40e376e3c`.
- `replication_results.json` SHA-256:
  `ca9f0177b0b42a3ec888b13799fdd3d39c5c5ae9caacedd2245a0292b42396da`.
- `replication_summary.md` SHA-256:
  `af3b527db055c4568db7125047dad97ba9492fa55d5bbf2c3a6b6cc9002f41df`.
- `manifest.json` SHA-256:
  `96338ea291f40ea7d9a1ea4a0d45dd17ed5a60c856333150655701f64841dcf6`.
- Two final offline replays were byte-identical for all four artifacts.

The preregistration artifact is written before price loading or result
computation. External performance remains `untrusted_external_evidence`; the
source's `29.64%` table versus `29.41%` chart discrepancy is preserved and no
external metric controls ranking, gates, or routing.

## Credential and safety audit

- Preflight before offline verification:
  - `APP_PROFILE` loaded: `false`;
  - `APP_PROFILE=paper`: `false`;
  - `APP_PROFILE=live`: `false`;
  - broker credential/endpoint aliases loaded: `false`;
  - process `TIINGO_API_KEY` loaded: `false`.
- V5.64 wrapper sensitive-variable preflight: all aliases `false`.
- Tiingo credential read or loaded in V5.64: `false`.
- Credential value inspected, printed, returned, copied, or persisted:
  `false`.
- Market-data network access in V5.64: `false`.
- NexusTrade network or mutation access in V5.64: `false`.
- Broker account/order/position access: `false`.
- Broker mutation: none.
- Paper mutation: none.
- Receipt status: not applicable.
- Reconciliation status: not required; no broker operation occurred.
- Paper promotion: `false`.
- Live authorization: `false`.
- Live broker, orders, trading, and capital remain prohibited.
- V5.57 sleeve ownership, reconciliation, auditing, and caps are unchanged:
  - `$25.00` maximum entry-order notional;
  - `$60.00` maximum aggregate marked SPY entry exposure;
  - one broker order per secure cycle;
  - two sleeve intents per UTC day.
- No third sleeve was added.

## Verification

Focused implementation, dependency, and import verification:

`python -m pytest tests\unit\test_nexustrade_monthly_independent_replication.py tests\unit\test_dependency_direction.py tests\unit\test_import_safety.py`

- `58 passed` in `57.04s`.

Broader NexusTrade and routing regression verification:

`python -m pytest tests\unit\test_nexustrade_monthly_independent_replication.py tests\unit\test_nexustrade_monthly_adjusted_data_manifest.py tests\unit\test_nexustrade_strategy_intake.py tests\unit\test_strategy_challenger_factory.py tests\unit\test_preview_candidate_review.py tests\unit\test_dependency_direction.py tests\unit\test_import_safety.py`

- `123 passed` in `101.50s`.

Mandatory offline verification:

- `.\scripts\verify_offline.ps1`.
- Result: `PASS`.
- `109 passed` in `116.26s`.
- The script explicitly skipped the full default suite.

Full default verification:

- `python -m pytest`.
- `10,180 passed`, `5 skipped` in `3,396.80s` (`56:36`).
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
- `scripts/run_nexustrade_monthly_independent_replication.ps1`
- `src/algotrader/research/nexustrade_monthly_independent_replication.py`
- `tests/unit/test_nexustrade_monthly_independent_replication.py`

The tracked preregistration design was committed before outcome computation:

- `docs/design/v5_64_nexustrade_monthly_independent_replication.md`

## Next milestone

Freeze V5.64 as a failed promotion hypothesis. Do not tune this protocol after
outcome inspection and do not implement a no-submit shadow because no
`preview_review` route was earned.

If work continues without new authoritative source facts, the next milestone
must preregister a new, independently named hypothesis before inspecting its
outcomes. The most decision-relevant target is the observed failure mode:
fold-two static-basket underperformance and full/fold drawdown excess. It must
not claim source authenticity or reuse V5.64 results as promotion evidence.

The authentic route may resume only if candidate-specific authoritative public
material supplies the historical bar/data mode, slippage assumption, and
365-day clock. No operator contact with the source, manual CSV placement, or
credential action is required.
