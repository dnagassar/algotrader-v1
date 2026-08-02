# V5.84 factor-momentum style terminal decision

## Decision

V5.84 is terminally closed without tuning. All three fixed candidates earned
positive absolute historical returns, but none passed the preregistered alpha,
SPY, style-baseline, and portfolio-level gates.

- Terminal route: `no_candidate_passed`.
- Passing candidates: 0 of 3.
- Shadow winner: none.
- Paper promotion: false.
- Live authorized: false.
- Profit guarantee: false.

The result does not say the candidates lost money. It says they did not add
sufficient value over simpler tradable comparators to justify advancement.

## Exact results at 5 bps

| Candidate | Annualized return | Sharpe | Max drawdown | Annualized one-way turnover | 80/20 composite Sharpe delta | Decision |
|---|---:|---:|---:|---:|---:|---|
| `style_factor_momentum_timeseries_12m` | 9.36% | 0.690 | 35.58% | 1.658 | -0.050 | close |
| `style_factor_momentum_cross_section_top2_12m` | 10.13% | 0.708 | 31.42% | 3.099 | -0.048 | close |
| `style_factor_momentum_ensemble_50_50` | 9.77% | 0.707 | 33.50% | 2.355 | -0.048 | close |

Comparator results under identical chronology and decision costs:

| Comparator | Annualized return | Sharpe | Max drawdown |
|---|---:|---:|---:|
| static equal style | 12.68% | 0.826 | 36.91% |
| rank-only top two | 13.10% | 0.845 | 31.42% |
| SPY buy and hold | 14.74% | 0.903 | 33.70% |
| monthly 60/40 SPY/IEF | 9.47% | 0.968 | 21.19% |
| SHY buy and hold | 1.39% | 0.984 | 5.71% |

Every candidate failed the static-style Sharpe edge, every SPY value route,
and portfolio composite Sharpe/value gates. All exceeded the 30% drawdown cap.
Candidate B also failed to add enough Sharpe or relative drawdown value over its
rank-only ablation. No rule, threshold, horizon, universe, or cost was changed
after outcome inspection.

## Data and causal integrity

Nine authenticated Tiingo EOD GETs admitted exact identity mappings for
`IWD,IWF,RSP,VBR,VIG,SPLV,SHY,SPY,IEF`. Provider `adjClose` was normalized as
split- and dividend-adjusted `adjusted_close`. The exact common panel contains
3,832 sessions and 34,488 rows from `2011-05-05` through `2026-07-31`.

Signals form after month-end close, trade at the next common close, and first
earn the following close-to-close return. Holdings drift between actions. The
initial cash-to-target transition and every later rebalance pay exact one-way
turnover costs. Earning-period holdings, asset contributions, and transaction
cost contributions are time-aligned and reconcile to compounded return. Two
fresh data-to-result pipelines produced identical persisted result and manifest
bytes.

## Bindings

- Protocol commit: `1a16754885f91b036bb9722ac1db60ffe6f7d264`.
- Protocol SHA-256: `3ec0d6359cb4280e24a60fab8a9c04a18ac727f231fb89bd3526a9f0c4aa8361`.
- Data boundary commit: `a774f3698ae9b0aa9eabd87311c35197aa9dad04`.
- Data receipt commit: `a686ae9c080cf9713b5cbbe5cc6268ef3fd009ce`.
- Data receipt SHA-256: `dd95e69f73c59bad79f183fc620d719424de3b00c54955ca6bd6e39000b3fc4e`.
- Engine commit: `aca347d93afebdd278e75e0f9f23d04d742efd3a`.
- Engine SHA-256: `4ec9d7df2fdeb07d73f13d3e7132f7dabf7c24f5d5e72e69d553636aedc03848`.
- Canonical data SHA-256: `c54d53450cd523677e9f72a7a3ba001295c738a7a388b37ff2a3d1f5bf361919`.
- Data manifest SHA-256: `ee0063bbb19f6c05b593b8519a0864d2224fe93061ca674f62412c736733d790`.
- Result SHA-256: `48944fdda451dc4fdbe4d5091fedd9d2993e35e3f916b85499dab81e644cc4cf`.
- Artifact manifest SHA-256: `90217675189b32883aff765092660e20f6a0ac81a56da25ff511407dfd95b219`.
- Summary SHA-256: `5b8ce3f540d2ac069004a6805c1e3341a137bead05e55174cdde9901cbba36ad`.

## Portfolio decision and next gate

A repository-wide scan found no prior non-sealed passing candidate. The best
closed building block remains V5.77 `spy_inverse_variance_long_cash_proxy`
(10.55% annualized, 0.946 Sharpe, 18.28% maximum drawdown), but its frozen SPY
return-capture and fold-consistency gates failed. It cannot be promoted or
retuned after the fact.

Launching a parameter search from these outcomes would create overfit rather
than alpha. The only already-preregistered untouched terminal decision remains
Crypto Tournament V2 after `2026-08-13T00:00:00Z`. Its unattended GET-only
receipt path is execution-proven and continues without manual waiting. A
separate new family is permitted only with independent rationale, an
outcome-blind protocol, and genuinely new evidence; historical reweighting of
these failures is not readiness.

## Verification

- Final combined changed-surface suite: 185 passed in 190.33 seconds.
- Offline verifier: PASS; all 109 safety-guard tests passed in 196.24 seconds.
- The required full default `python -m pytest` was attempted once and hit its
  3,604.6-second command timeout without emitting a failing test. This is not a
  pass; exhaustive default-suite completion remains a verification gate.
- `git diff --check` passed; only the intended orchestration module changed
  under `src`, and no untracked `src/tests` files existed.
## Safety

The V5.84 engine was offline, credential-free, broker-free, paper-mutation-free,
and live-free. Data acquisition used only the Tiingo market-data credential
inside the trusted adapter; the value was not printed or persisted. External
source performance remained untrusted and unused. V5.57 ownership,
reconciliation, audit, live prohibition, and caps remain unchanged: USD 25
entry-order notional, USD 60 aggregate marked SPY entry exposure, one broker
order per secure cycle, and two sleeve intents per UTC day.
