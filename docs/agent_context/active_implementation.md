# Active Implementation

## Ownership and takeover

- Writer: Codex, sole implementation writer for this working tree.
- Working tree:
  `C:\Users\danie\.codex\worktrees\c029\algo_trader`.
- Branch: `codex/v5.62-nexustrade-source-data-unblock`.
- Clean takeover HEAD:
  `c02561b7cb738a4e2d0f0e90b92895d748ab142e`.
- Branch, HEAD, status, staged diff, unstaged diff, untracked files, and the
  inherited handoff were inspected before any change.
- Takeover was clean: staged, unstaged, and untracked sets were empty.
- No reset, clean, stash, restore, rebase, switch, new branch, or new worktree
  occurred.
- Codex remained the only writer. No subagent was used.
- Dirty-file owner before the final local commit: Codex owns exactly the files
  listed under "Tracked implementation slice."
- Next action after this handoff update: run final hygiene checks, stage the
  coherent implementation slice, commit locally, and verify clean status.

## Decision

V5.66 completed the preregistered attribution-only diagnostic of the frozen
V5.65 NexusTrade high-volatility defense. The result is
`classification_primary` under the fixed moderate-cost full-OOS rule.

The fixed four paths were:

- `P`: frozen V5.64 parent
  `nexustrade_monthly_independent_spy_sma_50_200_regime_filter`;
- `A`: frozen V5.65 actual
  `nexustrade_monthly_independent_spy_sma_50_200_high_volatility_defense`;
- `D`: delayed, stateless-parent diagnostic; and
- `I`: immediate volatility-transition, stateless-parent diagnostic.

`D` and `I` are diagnostic counterfactuals, not candidates. `I` moves only a
volatility-gate target transition to the current signal close; ordinary frozen
parent rebalance targets retain their next-session-close timing. Fold one,
which contained no OOS high-volatility session, is the zero-effect control:
all four paths have identical return, drawdown, turnover, trades, and zero
divergence there.

No candidate, route, preview, shadow, paper promotion, broker path, or live path
was created. V5.64 and V5.65 remain frozen.

## Outcome-blind preregistration

- Protocol:
  `v5_66_nexustrade_high_volatility_attribution_v1`.
- Tracked protocol:
  `docs/design/v5_66_nexustrade_high_volatility_attribution.md`.
- Final protocol SHA-256:
  `2a2d03030b2ec74ca3a0682ca94163ea5b28218c1b452b4f10664fc182733227`.
- Outcome-blind commits, both before canonical diagnostic output:
  - `a91bc91ed0576399a04b364c5b6fb23b98ed32e7` - preregistration;
  - `6f890d45cec5b1684def0584f96c7f9a499dcb69` - fixed `1e-24`
    reconciliation/tie tolerance.
- Parameter search performed: `false`.
- Reconciliation tolerance: `1e-24`.
- Additive return identity:
  `(I-P) + (D-I) + (A-D) = A-P`.
- Every return and constituent-contribution decomposition passed within the
  fixed tolerance across all four cost cases and all reporting windows.

Pinned frozen inputs:

- V5.64 protocol SHA-256:
  `f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0`.
- V5.64 engine SHA-256:
  `66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5`.
- V5.65 protocol SHA-256:
  `1b614cb9d9e310704a0f8adcda224a4c540054a70af2731bcd3ec9c9b44db0c5`.
- V5.65 engine SHA-256:
  `fbc37e7c5cda052951c9406c7666cf346fa6d814edbf41d9842c80f4c2516a3c`.
- V5.65 preregistration artifact SHA-256:
  `8ab8fb25edf1ccb9803465fbc568b4b5348776c472b58c447a189ee677723190`.
- V5.65 result SHA-256:
  `e30c9c6f9d90f0d87c33607c71d1ec3e7c0055a245b88d06a469bfbc33709611`.
- V5.65 summary SHA-256:
  `1ff76c5c3fcb840794fbcd2e501f7300976f34557dd9aad3dcea35ebdd3f936e`.
- V5.65 manifest SHA-256:
  `99c52a97d2f8d6ef88df844356dbd38e88859d2804c4db9cf166ae55cad48814`.
- Frozen result reproduction passed every V5.64/V5.65 metric field, all eight
  full target hashes, all eight OOS target hashes, and overlay integrity.

## Canonical data and chronology

- Provider/provenance: Tiingo EOD, already acquired and validated by V5.63.
- Canonical field: `adjusted_close` from Tiingo `adjClose`.
- Adjustment semantics: split-and-dividend-adjusted EOD price.
- Adjusted OHLCV claimed: `false`.
- Symbols:
  `AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST, SPY`.
- Deterministic mapping: `BRK-B->BRK-B`.
- Coverage: `2019-01-02` through `2025-03-28`.
- Sessions per symbol: `1,569`; total rows: `18,828`.
- Missing/unexpected sessions and weekend rows: none.
- Session reference limitation: observed Tiingo SPY EOD dates, not an
  independently represented exchange calendar.
- Canonical CSV:
  `runs/operator_input/multi_etf_adjusted_daily_canonical.csv`.
- Canonical CSV SHA-256:
  `d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575`.
- V5.63 manifest SHA-256:
  `e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1`.
- Training: `2021-12-31` through `2024-03-24`.
- Untouched OOS: `2024-03-24` through `2025-03-28`; first observed session
  `2024-03-25`; `254` sessions.
- Continuous-state folds:
  - fold one `2024-03-25` through `2024-07-24`, `84` sessions;
  - fold two `2024-07-25` through `2024-11-21`, `85` sessions;
  - fold three `2024-11-22` through `2025-03-28`, `85` sessions.
- V5.66 network data acquisition: `false`; only the validated local input was
  read.

## Moderate-cost attribution evidence

Full OOS total returns:

- `P`: `0.216081928040488296986127071`.
- `A`: `0.167041852685457898451176029`.
- `D`: `0.116515111490536446106923363`.
- `I`: `0.144804220490674712181326511`.
- Net harm `P-A`: `0.049040075355030398534951042`.

Exact signed effects from V5.65's perspective:

- Classification `I-P`:
  `-0.071277707549813584804800560`.
- Next-session execution delay `D-I`:
  `-0.028289109000138266074403148`.
- Stateful carry `A-D`:
  `0.050526741194921452344252666`.
- Total `A-P`:
  `-0.049040075355030398534951042`.
- Reconciliation residual: exactly zero at the recorded decimal precision.

Positive-harm classification uses magnitudes. Classification accounts for
`1.453458361019873718340725277` of net harm before offsetting benefits and is
the unique preregistered primary driver. Execution delay is additional harm;
stateful carry offsets rather than causes full-OOS return harm.

Session mechanics:

- OOS high-volatility sessions: `38`.
- Parent-risk-on/high-volatility forced-cash sessions: `38`.
- Actual-versus-parent target-divergence sessions: `163`.
- Stateful-carry `A`-versus-`D` target divergences: `125`.
- `D`-versus-`I` posttrade timing divergences: `19`.
- Thus the 163 target divergences split into 38 direct cash-gate sessions and
  125 subsequent stateful 30-day filled-event carry sessions.
- OOS volatility transitions: five signal dates, each with an exact scheduled
  next-session fill record in the transition ledger.

Turnover and costs:

- OOS one-way turnover `P/A/D/I`:
  `11.72946592903657074232868409` /
  `15.70416390432810190672866051` /
  `14.32993387899970262982266998` /
  `14.32993387899970262982266998`.
- `A-P` turnover increment:
  `3.97469797529153116439997642`.
- Stateful `A-D` turnover increment:
  `1.37423002532839927690599053`.
- OOS trade counts `P/A/D/I`: `117/121/135/135`.
- Source-fee-only to moderate return degradation `P/A/D/I`:
  `0.005720874982004894178230310` /
  `0.007356670031043610797317176` /
  `0.006420187398890437404610968` /
  `0.006582855489325920216386431`.

Fold evidence:

- Fold one: no high-volatility or divergence session; total effect and every
  component are zero; all path returns are
  `0.139010185844455840847480965`; all maximum drawdowns are
  `0.1028816547447382668989194429`.
- Fold two return effects classification/delay/state/total:
  `-0.077770079511010181267658740` /
  `0.016549075482118369381189935` /
  `0.009681755963349674358971778` /
  `-0.051539248065542137527497027`.
- Fold two maximum drawdown `P/A/D/I`:
  `0.0876811122686090139848287740` /
  `0.0942877628564643970350360156` /
  `0.0971677823108617477171365579` /
  `0.1106532358047517508206632325`.
  Classification caused the fold-two return harm; delay and state partially
  recovered it, while A still worsened drawdown versus P.
- Fold three return effects classification/delay/state/total:
  `0.0085160724886560835111341067` /
  `-0.0367334402939371793587441627` /
  `0.0322948173689390070220863946` /
  `0.0040774495636579111744763386`.
- Fold three maximum drawdown `P/A/D/I`:
  `0.1365827540765017539390053280` /
  `0.1712215937752765950195728575` /
  `0.1524352992808904442033569239` /
  `0.1176338688111769290784097618`.
  Immediate classification reduced fold-three drawdown, but next-session
  timing and then stateful carry worsened the realized A drawdown.

Constituent attribution is explicitly arithmetic gross contribution, not the
compounded portfolio decomposition. Aggregate classification/delay/state/total
effects are
`-0.06208723238735183035768468881` /
`-0.02481525245590856795131473973` /
`0.04688984401616241291147816002` /
`-0.04001264082709798539752126857`, with zero residual. Largest absolute
total effects were META `+0.04994657904708298255037370177`, JPM
`-0.04228162477138028125350490685`, BRK-B
`-0.03979012118086521403130689640`, GOOGL
`+0.02991155505871637058210980714`, and GS
`-0.02704367879576899002913430983`.

## Artifact evidence

Ignored output root:
`runs/v5_66_nexustrade_high_volatility_attribution`.

- `preregistration.json` SHA-256:
  `73b201b6ff79a2a684ad1b251f1f09efda61704d8151d59c051498baf9eb5325`.
- `attribution_results.json` SHA-256:
  `f5e1340bf3c659f4e7c96602215bf5e92249747b7562748b2335fe1b5a2d3c0c`.
- `attribution_summary.md` SHA-256:
  `5d0b19f4e93d2866e3c935ad8133c2f65eb63e51aa96760f3e25664a2c0ff0cc`.
- `manifest.json` SHA-256:
  `4aecd02b8a43712a28c95dc0625ad6051a8b3068e68ea4761fe9da79e041ed3c`.
- Two final canonical replays were byte-identical for all four artifacts.

External performance remains `untrusted_external_evidence`. The `29.64%`
table versus `29.41%` chart discrepancy remains preserved. Source metrics were
not used for decomposition, classification, ranking, routing, or promotion.
The authentic V5.58 route remains hard-gated on candidate-specific historical
bar/data mode, slippage, and 365-day clock evidence; V5.66 infers none of them.

## Credential and safety audit

- Boolean-only preflight before verification:
  - `APP_PROFILE` loaded: `false`;
  - `APP_PROFILE=paper`: `false`;
  - `APP_PROFILE=live`: `false`;
  - Alpaca/broker credential or endpoint aliases loaded: `false`;
  - `TIINGO_API_KEY` loaded: `false`;
  - NexusTrade credential aliases loaded: `false`.
- Credential value requested, inspected, printed, returned, copied, or
  persisted: `false`.
- NexusTrade access or mutation: none.
- Market-data network access: none.
- Broker account/order/position access: none.
- Broker mutation: none.
- Paper mutation: none.
- Receipt status: not applicable.
- Reconciliation status: not required; no broker operation occurred.
- Paper promotion: `false`.
- Live authorization: `false`; live broker, order, trading, and capital activity
  remain prohibited.
- V5.57 sleeve ownership, reconciliation, auditing, and caps are unchanged:
  - `$25.00` maximum entry-order notional;
  - `$60.00` maximum aggregate marked SPY entry exposure;
  - one broker order per secure cycle;
  - two sleeve intents per UTC day.
- No third sleeve was added.

## Verification

Focused V5.66 tests:

`python -m pytest tests\unit\test_nexustrade_high_volatility_attribution.py -q`

- `7 passed` in `19.85s` on the final implementation.

Broader frozen-engine and safety regression:

`python -m pytest tests\unit\test_nexustrade_high_volatility_attribution.py tests\unit\test_nexustrade_monthly_high_volatility_defense.py tests\unit\test_nexustrade_monthly_independent_replication.py tests\unit\test_volatility_regime_evidence.py tests\unit\test_volatility_filtered_spy_sma_backtest.py tests\unit\test_dependency_direction.py tests\unit\test_import_safety.py -q`

- `90 passed` in `71.44s`.

Mandatory offline verification:

- `./scripts/verify_offline.ps1` equivalent Windows invocation
  `.\scripts\verify_offline.ps1`.
- Result: `PASS`.
- `109 passed` in `99.35s`.
- The script explicitly skipped the full default suite.

Full default verification:

- `python -m pytest`.
- `10,194 passed`, `5 skipped` in `2,034.86s` (`33:54`).
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
- `scripts/run_nexustrade_high_volatility_attribution.ps1`
- `src/algotrader/research/nexustrade_high_volatility_attribution.py`
- `tests/unit/test_nexustrade_high_volatility_attribution.py`

The tracked preregistration design was committed before outcomes:

- `docs/design/v5_66_nexustrade_high_volatility_attribution.md`

## Next milestone

Freeze V5.65 as a failed repair hypothesis and V5.66 as explanatory evidence.
Do not tune the volatility lookback, quantiles, thresholds, immediate/delayed
timing, state semantics, or gates from these inspected outcomes. Do not
register `D` or `I` as a candidate and do not implement a no-submit shadow.

No further NexusTrade implementation is decision-justified from the current
evidence. A later V5.67 may begin only with a new outcome-blind protocol for an
independently motivated strategy family or overlay whose thesis and fixed
parameters do not come from optimizing V5.65/V5.66. The authentic route may
resume only if new candidate-specific authoritative evidence supplies the
historical bar/data mode, slippage, and 365-day clock. Until one of those
conditions occurs, close this lane rather than fabricating, hand-normalizing,
or tuning around the demonstrated result.
