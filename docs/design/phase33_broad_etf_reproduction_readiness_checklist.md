# Phase 33 Step 18 - Broad ETF Reproduction Readiness Checklist

## Purpose

This checklist records what must be true before broad-ETF moving-average
reproduction planning can begin.

It exists to prevent premature movement into code, data acquisition,
notebooks, schemas, backtests, evaluators, signal definitions, or trading-path
work. It does not approve reproduction, methodology, parameters, an ETF
universe, source, benchmark, cash proxy, validation, implementation, or
trading use.

## Current Evidence State

- Faber's "A Quantitative Approach to Tactical Asset Allocation" has been
  reviewed as practitioner/TAA context only. It can inform methodology,
  benchmark, cash, total-return, parameter-discipline, and timing questions,
  but it is not validated evidence and is not implementation-ready.
- `ETF-ACADEMIC-001`, Huang and Huang's "Testing moving average trading
  strategies on ETFs," has been reviewed as ETF-specific methodology and
  friction context only. It can inform ETF moving-average, ETF-versus-index,
  benchmark, open/close timing, transaction-cost, lag-length, and
  data-snooping questions, but it is not validated evidence and is not
  implementation-ready.
- The Phase 33 Step 17 synthesis supports only methodology questions and
  caution areas. It does not approve a rule, parameter, source, universe,
  benchmark, cash proxy, reproduction route, evaluator, or implementation.
- No evidence is validated.

## Readiness Gate Checklist

Status values:

- `blocked`: cannot move forward until material evidence or decision work is
  completed.
- `partial`: prior docs provide context, but no approval exists.
- `ready for next docs-only review`: enough context exists to write the next
  non-implementing boundary, but not to approve code or reproduction.

| Gate | Current status | Required evidence or decision | Forbidden before the gate clears | Future document or phase that could clear it |
| --- | --- | --- | --- | --- |
| Evidence gate | partial | Approved evidence review that promotes specific source claims under the project evidence standard. | `ValidatedResearchArtifact`, `ValidatedSignalDefinition`, validation claims, production threshold, evaluator work, or trading implication. | Approved evidence review or formal promotion/rejection boundary. |
| Methodology gate | partial | Explicit approved methodology statement covering rule family, cadence, timing, data semantics, limitations, and rejection criteria. | Methodology approval, reproduction protocol, schema, notebook, backtest, signal definition, evaluator, or implementation. | Methodology approval boundary after evidence and source choices are concrete. |
| Parameter-discipline gate | partial | Parameter-selection discipline, fixed candidate parameters or approved search protocol, and sensitivity-review rules that avoid hindsight selection. | Selecting or tuning a moving-average length, lookback, cadence, threshold, score, ranking, direction, confidence, or actionability. | Parameter-discipline and sensitivity-review boundary. |
| ETF universe gate | partial | Approved ETF universe with inclusion, exclusion, inception, closure, ticker-change, asset-class, liquidity, and survivorship rules. | Universe approval, ticker list finalization, data acquisition, fixture creation, schema design, reproduction, or backtest. | Source/universe/benchmark approval boundary. |
| Data-source gate | partial | Approved data source with access path, adjustment semantics, coverage, reproducibility, deterministic replay plan, and source failure policy. | Source approval, downloads, API calls, ingestion, data files, fixtures, scripts, notebooks, or schema design. | Source/universe/benchmark approval boundary or data-source approval boundary. |
| Terms/license gate | partial | Explicit non-legal project decision on allowed private-repo use, caching, redistribution, derived outputs, fixture eligibility, and attribution needs. | Downloading, storing, caching, redistributing, committing, or deriving project data from third-party sources. | Terms/license approval and data-policy boundary. |
| Storage/fixture policy gate | partial | Approved final policy for raw data, local-only data, manifests, checksums, tiny synthetic fixtures, tiny derived fixtures, and normal pytest isolation. | Data files, PDFs, raw reports, fixtures, ingestion, notebooks, scripts, or normal-pytest dependency on external data. | Final data storage/fixture policy approval boundary. |
| Benchmark/cash proxy gate | partial | Approved benchmark, buy-and-hold comparison, cash/risk-free proxy, risk metric scope, and alignment with source and return construction. | Benchmark approval, cash proxy approval, result comparison, performance claim, reproduction, validation, or implementation. | Source/universe/benchmark approval boundary or benchmark/friction evidence review. |
| Return-construction gate | blocked | Explicit return construction: adjusted close versus total return, dividends, distributions, splits, corporate actions, expenses, missing values, and rebalance periods. | Schema design, data transformation, reproduction protocol, backtest, result table, or validation language. | Return-construction policy boundary. |
| No-lookahead/as-of gate | partial | Explicit signal-observation time, decision time, action time, fill convention, as-of availability, revision/correction policy, and measured-return window. | Backtest, reproduction, signal computation, evaluator behavior, result interpretation, or implementation. | No-lookahead/as-of protocol boundary. |
| Cost/friction gate | partial | Explicit assumptions for transaction costs, spreads, slippage, opening gaps, turnover, taxes, fund expenses, rebalance friction, and rejected simplifications. | Net-return claims, friction-adjusted results, reproduction, validation, benchmark comparison, or implementation. | Benchmark/friction evidence review or cost/friction assumption boundary. |
| Survivorship/inception/delisting gate | blocked | Policy for ETF inception dates, delistings, closures, mergers, ticker changes, fund substitutions, stale observations, and unavailable-history handling. | Universe finalization, data acquisition, result comparison, reproduction, schema design, backtest, or validation claims. | Universe/source approval boundary with survivorship policy. |
| Reproduction protocol gate | blocked | Approved protocol after source, universe, benchmark, return construction, timing, costs, survivorship, data policy, and result-review template are approved. | Reproduction approval, reproduction attempt, backtest, data acquisition, notebooks, scripts, schemas, or evaluator work. | Reproduction protocol planning boundary. |
| Result-review template gate | blocked | Template for reviewing outputs with required assumptions, limitations, non-claims, rejection criteria, residual gaps, and no trading-readiness language. | Result validation, promotion/rejection decision, production threshold, validated artifact, signal definition, or implementation routing. | Result-review template boundary. |
| Implementation-scope gate | blocked | Explicit implementation scope after validated evidence, validated signal definition, data policy, tests, and runtime isolation are approved. | Production code, evaluator implementation, signal computation, scoring, ranking, direction, confidence, actionability, broker/runtime behavior, or trading-path behavior. | Implementation readiness gate. |

## Required Non-Approval Status

- No source is approved.
- No ETF universe is approved.
- No benchmark or cash proxy is approved.
- No methodology is approved.
- No parameter is approved.
- No data policy is approved as final.
- No reproduction protocol is approved.
- No implementation is approved.

## Minimum Requirements Before Any Code Phase

Any future code phase remains blocked until all of the following exist as
explicit approvals or boundaries:

- approved source, universe, benchmark, and data policy
- approved deterministic fixture strategy or approved local-only data boundary
- explicit no-lookahead/as-of protocol
- explicit return construction
- explicit cost and friction assumptions
- explicit parameter-selection discipline
- result-review template
- clear test scope that keeps normal `python -m pytest` offline,
  deterministic, credential-free, and independent of providers, brokers,
  accounts, subscriptions, wall-clock state, network state, notebooks,
  prototype runtimes, and external data files

## Recommended Next Routing

Recommended next route: pause Phase 33 before code until source, data policy,
universe, benchmark, and cash-proxy choices can be made concrete.

The current evidence is useful for methodology questions and caution areas,
but it is not sufficient to approve reproduction, implementation, data,
methodology, parameters, universe, source, benchmark, or cash proxy. If Phase
33 resumes with concrete owner/source constraints, the next docs-only gate can
be a source/universe/benchmark approval boundary. A reproduction protocol
planning boundary should not occur before those approvals.

## Explicit Non-Goals

This phase does not perform or authorize:

- reproduction approval
- methodology approval
- parameter approval
- universe approval
- source approval
- benchmark approval
- data acquisition
- data download
- data ingestion
- data files
- raw reports added
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
- no reproduction protocol
- no promotion/rejection decision
- no trading implication or production threshold
