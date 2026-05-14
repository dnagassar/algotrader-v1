# Phase 33 Step 17 - Broad ETF Methodology Evidence Synthesis Boundary

## Purpose

This document synthesizes the limited methodology evidence reviewed so far for
the broad-ETF moving-average research candidate.

The synthesis covers Faber's "A Quantitative Approach to Tactical Asset
Allocation" and `ETF-ACADEMIC-001`, Huang and Huang's "Testing moving average
trading strategies on ETFs." It identifies common methodology lessons,
unresolved issues, and project constraints before any reproduction,
validation, signal-definition, evaluator, or implementation planning.

This phase does not approve evidence, methodology, parameters, data, ETF
universe, benchmark, cash proxy, reproduction, validation, implementation, or
trading use. It adds no production code, tests, dependency, lockfile, data,
fixture, PDF, raw report, notebook, script, schema, backtest, evaluator,
signal definition, broker behavior, runtime behavior, persistence behavior,
or trading-path behavior.

## Evidence Inputs

Reviewed inputs:

- Phase 33 Step 15, the Faber limited formal evidence review, treats
  `MA-PRACT-001` as methodology and practitioner/TAA context only. It is
  useful for broad asset-class trend-following, 10-month SMA framing,
  benchmark and cash-treatment questions, parameter-discipline questions,
  total-return assumptions, index-proxy cautions, and no-lookahead/action
  timing cautions. It is not validated evidence and is not implementation
  ready.
- Phase 33 Step 16, the `ETF-ACADEMIC-001` limited formal evidence review,
  treats Huang and Huang as ETF-specific methodology/context evidence only.
  It is useful for ETF moving-average crossover framing, ETF-versus-index
  transferability questions, standard close-only MA versus `QUIMA` timing
  context, buy-and-hold and risk-adjusted comparison framing, opening-gap
  friction, transaction-cost context, lag-length cautions, and data-snooping
  context. It is not validated evidence and is not implementation ready.

No input is promoted to validated evidence, methodology approval, parameter
approval, universe approval, data-source approval, benchmark approval,
reproduction approval, implementation approval, or trading readiness.

## Common Methodology Themes

The reviewed sources jointly support cautious review questions around:

- moving-average and trend-following rules as mechanical timing frameworks
- broad asset-class or ETF implementation relevance, with transfer limits
- monthly timing versus shorter-horizon, daily, open/close, and intraday
  timing questions
- benchmark, buy-and-hold, cash, and risk-free treatment as central design
  choices rather than incidental details
- total-return, adjusted-price, dividend, distribution, split, and
  corporate-action assumptions
- ETF-specific implementation friction, including opening gaps, spreads,
  costs, turnover, liquidity, fund expenses, and trade timing
- parameter discipline, sensitivity review, and safeguards against
  performance-hindsight selection
- no-lookahead and action-timing controls, including signal observation time,
  action time, fill convention, and data availability as of the decision time

These themes are methodology context only. They do not approve a rule,
parameter, cadence, source, universe, benchmark, cash proxy, reproduction
route, or evaluator.

## Areas Of Agreement

The reviewed sources are aligned on several cautious methodology questions:

- Moving-average rules require precise timing conventions before any
  reproduction can be meaningful.
- Benchmark choice materially affects interpretation of timing results.
- ETF implementation differs from index-only evidence and cannot be assumed
  equivalent.
- Cash, zero-return, Treasury bill, risk-free, or other cash-like handling
  must be explicit.
- Parameters cannot be selected or justified from performance hindsight.
- Costs, frictions, opening gaps, spreads, slippage, turnover, taxes, and
  fund expenses can materially alter interpretation.
- Return construction and adjusted-data semantics must be stated before any
  result is reviewed.
- No-lookahead handling must separate signal availability, decision time,
  action time, and measured return period.

## Areas Of Tension Or Uncertainty

The synthesis preserves these unresolved tensions:

- Faber's practitioner/TAA framing uses broad asset-class index proxies,
  while Huang and Huang focus on ETF-specific implementation findings.
- Index-proxy evidence cannot be treated as actual ETF implementation
  evidence without project-local source, universe, data, and timing controls.
- Faber's same-close/monthly timing discussion conflicts with the project's
  need for explicit as-of-safe action timing, while Huang and Huang's
  open/close and `QUIMA` framing highlights timing sensitivity without
  approving an execution rule.
- Faber's total-return assumption raises questions about whether later ETF
  data should use total-return, adjusted-close, adjusted-OHLC, or explicit
  dividend/distribution handling.
- Huang and Huang's ETF adjusted-data, sample-construction, survivorship, and
  transaction-cost details require deeper extraction before they can shape a
  project-local protocol.
- Performance claims in either source remain external claims, not
  project-local reproducibility evidence.
- The project still lacks an approved source, universe, benchmark, cash-proxy,
  data-storage, fixture, and final data policy for this candidate.

## What The Evidence Can Support

The reviewed evidence can support only cautious planning context:

- methodology context for broad moving-average and trend-following review
- benchmark, buy-and-hold, cash, and risk-free treatment context
- ETF implementation-friction context
- ETF-versus-index transferability caution context
- parameter-discipline and sensitivity-review context
- no-lookahead, signal-timing, action-timing, and open/close caution context
- future reproduction-planning questions, not reproduction approval
- future result-review template questions, not result validation

## What The Evidence Cannot Support

The reviewed evidence cannot support:

- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- methodology approval
- parameter approval
- ETF universe approval
- data-source approval
- benchmark or cash-proxy approval
- production threshold
- backtest approval
- reproduction approval
- result validation
- signal definition
- evaluator implementation
- live or paper trading readiness
- profitability claim
- generalization claim
- implementation-readiness or production-readiness claim

## Minimum Requirements Before Reproduction Planning

Before reproduction planning can be considered, the project needs all of the
following as explicit later approvals or boundaries:

- approved source and data policy
- approved ETF universe boundary
- approved benchmark and cash-proxy boundary
- explicit return-construction decision
- explicit total-return, adjusted-price, dividend, distribution, split, and
  corporate-action policy
- explicit timing and action convention
- explicit signal-observation, decision-time, action-time, fill, and return
  measurement convention
- explicit cost, spread, slippage, turnover, fund-expense, tax, rebalance, and
  friction assumptions
- explicit parameter-selection discipline and sensitivity-review plan
- explicit no-lookahead, point-in-time, as-of, revision, and correction
  protocol
- explicit survivorship, delisting, inception, closure, merger, ticker-change,
  and stale-observation policy
- result-review template with required non-claims and rejection criteria
- confirmation that normal `python -m pytest` remains offline,
  deterministic, credential-free, and independent of provider, broker,
  account, subscription, wall-clock, or network state

## Recommended Next Gate

Recommended next docs-only gate: broad ETF reproduction readiness checklist.

The checklist should list every unresolved gate that must be closed before
code, data acquisition, fixture approval, reproduction, validation,
signal-definition work, evaluator work, or implementation can be considered.
It should include source/data policy, ETF universe, benchmark/cash proxy,
return construction, timing, frictions, parameter discipline, no-lookahead,
data storage, fixture eligibility, result-review, and pytest safety checks.

Conservative alternatives remain:

- benchmark/friction evidence review
- ETF universe/source approval boundary
- pause until source, universe, benchmark, cash-proxy, and data policy are
  ready

No recommended gate approves evidence, methodology, parameters, data,
universe, benchmark, cash proxy, reproduction, validation, implementation, or
trading use.

## Explicit Non-Goals

This phase does not perform or authorize:

- evidence validation
- methodology approval
- parameter approval
- universe approval
- source approval
- benchmark approval
- cash proxy approval
- data acquisition
- data download
- data ingestion
- data files
- PDFs added
- fixtures
- schema, code, notebook, or script
- dependency or lockfile changes
- backtest
- reproduction
- evaluator or signal implementation
- signal computation
- signal scoring, ranking, direction, confidence, or actionability
- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- new contract type
- production threshold
- profitability claim
- production-readiness claim
- implementation-readiness claim
- trading implication
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, vectorbt, QuantConnect, notebook runtime, or LLM
  trading-path behavior

## Remaining Blockers

Evaluator implementation and any production route remain blocked by all of the
following:

- no `ValidatedResearchArtifact`
- no `ValidatedSignalDefinition`
- no approved evidence review
- no approved methodology or parameters
- no approved ETF universe
- no selected/approved data source
- no approved benchmark/cash proxy
- no approved final data storage/fixture policy
- no acquired data
- no project-local deterministic reproduction
- no no-lookahead audit
- no production threshold/config provenance
- no implementation-scope approval
- no evaluator tests
- no approved source identity for "Simple Market Timing with Moving Averages"
- no Zakamulin full-text review
- no approved total-return versus price-return decision
- no approved dividend/reinvestment treatment
- no approved corporate-action handling policy
- no approved correction/revision policy
- no approved point-in-time/as-of policy
- no approved transaction cost, slippage, spread, rebalance, fund-expense,
  tax, or friction assumption
- no approved survivorship, delisting, inception, closure, merger,
  ticker-change, or stale-observation policy
- no benchmark/cash/risk-metric approval
- no result-review template
- no reproduction readiness checklist
- no promotion/rejection decision
- no trading implication or production threshold
