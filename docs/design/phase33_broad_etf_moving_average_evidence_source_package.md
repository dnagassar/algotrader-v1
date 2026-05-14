# Phase 33 Step 10 - Broad ETF Moving-Average Evidence Source Package

## Purpose

This document prepares a documentation-only evidence/source package for the
broad-ETF simple moving-average trend-following candidate.

Its purpose is to identify evidence sources to review before any future
methodology review, reproduction protocol, validation route, implementation
planning, signal-definition discussion, or evaluator work.

It does not approve evidence, methodology, moving-average parameters, source
data, an ETF universe, a benchmark, a cash proxy, reproduction, validation,
implementation, or trading use.

This phase adds no data, fixture, notebook, script, schema, test, source code,
evaluator, signal computation, signal scoring, trading-path behavior, broker
behavior, runtime behavior, scheduler behavior, persistence behavior,
portfolio behavior, ledger behavior, reconciliation behavior, Alpaca behavior,
ML behavior, vectorbt behavior, QuantConnect behavior, notebook runtime
behavior, or LLM trading-path behavior.

## Candidate Restatement

Broad-ETF simple moving-average trend-following remains a research candidate
for review and planning only.

The candidate is not validated, implemented, trading-ready, production-ready,
or actionable. It has no approved source data, ETF universe, benchmark, cash
proxy, moving-average parameter, methodology, reproduction protocol,
validation route, signal definition, evaluator, production threshold, or
implementation path.

## Evidence Categories To Collect

Future evidence collection should cover these categories before any
methodology review or reproduction planning:

- academic papers on moving-average trend-following
- practitioner references on time-series trend-following
- ETF-specific trend-following or tactical allocation references if available
- benchmark and buy-and-hold comparison references
- transaction-cost, spread, slippage, fund-expense, tax, and other friction
  references
- data-adjustment, adjusted-close, dividend, distribution, split,
  corporate-action, and total-return caveat references
- no-lookahead, point-in-time, survivorship-bias, data-snooping, overfitting,
  and backtest-bias references
- robustness, out-of-sample, holdout, walk-forward, and parameter-sensitivity
  references

These categories are source-intake targets only. Listing a category does not
approve a paper, claim, parameter, universe, data source, benchmark, cost
assumption, or methodology.

## Evidence-Quality Standards

Any future evidence review must follow these standards:

- primary sources are preferred over summaries, excerpts, search snippets, or
  agent-generated notes
- academic papers should be cited from the paper, journal, working-paper page,
  author page, publisher page, DOI page, or official preprint location when
  available
- practitioner sources must be labeled as practitioner or secondary unless
  they provide primary data, code, or exact methodology documentation that can
  be independently reviewed
- blog posts, marketing pages, strategy explainers, fund literature, and
  vendor content may provide context only unless a later review explicitly
  establishes stronger evidence quality
- LLM summaries, external-agent summaries, and unattributed paraphrases are
  not evidence
- exact claims must be cited to exact sources
- every claim must separate reviewed evidence, project inference, and
  remaining uncertainty
- performance claims require reproducible data, methodology, costs, benchmark
  handling, and no-lookahead controls before they can be trusted
- source claims must record date, version, access date, scope, and limitations
  when those details affect interpretation
- contradictions between sources must be preserved rather than smoothed into a
  single unsupported conclusion

Evidence quality can support routing only. It cannot by itself approve a
methodology, moving-average parameter, source, ETF universe, benchmark, cash
proxy, data acquisition, reproduction, validation, signal definition,
evaluator, or implementation.

## Review Questions

Each collected source should answer, or explicitly fail to answer, these
questions:

- What exact moving-average rule is being discussed?
- What asset class, instrument set, or universe is studied?
- What date range and observation frequency are used?
- Are returns price-only, adjusted-price, total-return, excess-return, or
  another construction?
- How are dividends, distributions, splits, mergers, ticker changes, fund
  closures, and other corporate actions handled?
- What benchmark is used?
- Is the comparison buy-and-hold, cash, T-bill, risk-free, equal-weighted,
  cap-weighted, or something else?
- Are transaction costs, bid-ask spreads, slippage, taxes, fund expenses,
  turnover, and rebalance frictions included?
- Is there out-of-sample, holdout, walk-forward, robustness, or
  parameter-sensitivity evidence?
- Are parameter choices justified before results, or optimized after the fact?
- What lookahead, survivorship, multiple-testing, data-snooping,
  restatement/revision, publication-lag, and point-in-time risks are
  addressed?
- What limitations are stated by the source?
- What evidence, if any, can transfer to broad ETFs?
- What evidence cannot transfer to broad ETFs?
- What questions remain unresolved before methodology review or reproduction
  protocol planning?

Unanswered questions remain blockers. A source should not be treated as
validation merely because it discusses a familiar moving-average rule.

## Candidate Evidence Intake Table

The table below is a starter intake skeleton. Rows are collection targets, not
reviewed evidence.

| Source ID | Citation / reference | Source type | Strategy / rule studied | Universe | Period / frequency | Key claim | Evidence quality | Bias controls | Costs/frictions | Relevance to broad ETFs | Limitations | Candidate status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MA-ACADEMIC-001 | TBD academic paper on moving-average trend-following | Academic paper | TBD | TBD | TBD | TBD | To assess | TBD | TBD | TBD | TBD | To collect; not reviewed; not approved |
| MA-PRACT-001 | TBD practitioner time-series trend-following reference | Practitioner / secondary unless source details prove otherwise | TBD | TBD | TBD | TBD | To assess | TBD | TBD | TBD | TBD | To collect; not reviewed; not approved |
| MA-ETF-001 | TBD ETF-specific trend-following or tactical allocation reference, if available | Academic, practitioner, or issuer/vendor context depending on source | TBD | TBD | TBD | TBD | To assess | TBD | TBD | TBD | TBD | To collect; not reviewed; not approved |
| MA-BENCH-001 | TBD benchmark or buy-and-hold comparison reference | Benchmark/methodology reference | TBD | TBD | TBD | TBD | To assess | TBD | TBD | TBD | TBD | To collect; not reviewed; not approved |
| MA-FRICTION-001 | TBD transaction-cost, spread, slippage, expense, or turnover reference | Methodology / friction reference | TBD | TBD | TBD | TBD | To assess | TBD | TBD | TBD | TBD | To collect; not reviewed; not approved |
| MA-DATA-001 | TBD adjusted-price, dividend, split, corporate-action, or total-return reference | Data-methodology reference | TBD | TBD | TBD | TBD | To assess | TBD | TBD | TBD | TBD | To collect; not reviewed; not approved |
| MA-BIAS-001 | TBD no-lookahead, point-in-time, survivorship, or backtest-bias reference | Methodology / bias-control reference | TBD | TBD | TBD | TBD | To assess | TBD | TBD | TBD | TBD | To collect; not reviewed; not approved |
| MA-ROBUST-001 | TBD robustness, out-of-sample, holdout, or parameter-sensitivity reference | Methodology / robustness reference | TBD | TBD | TBD | TBD | To assess | TBD | TBD | TBD | TBD | To collect; not reviewed; not approved |

Adding a source to this table later must not be treated as approval. A later
review must record citation details, evidence quality, limitations, bias
controls, costs/frictions, and non-claims before any source can influence
methodology routing.

## Non-Claims

This package does not prove:

- profitability
- strategy generalization
- ETF universe validity
- benchmark or cash-proxy validity
- source-data validity
- moving-average parameter validity
- methodology validity
- production threshold validity
- live or paper readiness
- `ValidatedResearchArtifact` eligibility
- `ValidatedSignalDefinition` eligibility
- implementation approval
- evaluator readiness
- trading readiness

It also does not show that any evidence source is sufficient, reproducible,
current, licensed, bias-controlled, or transferable to broad ETFs.

## Relationship To Prior Phase 33 Gates

This evidence/source package depends on prior Phase 33 gates only as
non-approving context:

- Phase 33 Step 2 created the broad-ETF moving-average source package and kept
  the candidate review/planning only.
- Phase 33 Step 4 recorded the public-source documentation sweep and
  separated primary documentation, secondary documentation, inference, and
  external scout research.
- Phase 33 Step 7 recorded terms/license constraints for candidate source
  categories without approving any source.
- Phase 33 Step 8 recorded the final non-approving source shortlist decision
  boundary for future planning only.
- Phase 33 Step 5 recorded methodology and no-lookahead/as-of requirements
  without approving methodology, parameters, data, universe, benchmark, or
  reproduction.
- Phase 33 Step 6 recorded candidate-only ETF universe and benchmark/cash
  proxy shortlists without approving any universe, benchmark, or cash proxy.
- Phase 33 Step 9 recorded future data storage and fixture policy
  requirements while preserving normal `python -m pytest` as offline,
  deterministic, credential-free, and free of data-provider, broker, runtime,
  and trading-path dependencies.

This Step 10 package does not weaken any prior gate. Public-source routing,
terms review, shortlist labels, methodology boundaries, universe/benchmark
shortlists, and storage/fixture policy remain non-approving.

## Recommended Next Gate

Recommended next docs-only gate: moving-average evidence intake plan.

That gate should define how specific sources will be collected, cited,
classified, and reviewed against the questions in this package. It must not
approve evidence, methodology, parameters, source data, ETF universe,
benchmark, cash proxy, storage policy, fixtures, data acquisition,
reproduction, validation, signal definition, evaluator behavior, or
implementation.

Later gates remain ordered and conditional:

- methodology evidence review only after source intake is traceable
- reproduction protocol boundary only after source, universe, benchmark/cash
  proxy, methodology, and data policy choices are explicitly approved
- result-review template only after a protocol is approved

No next gate may create data files, fixtures, notebooks, scripts, schemas,
backtests, reproduction outputs, evaluator behavior, signal behavior, or
trading-path behavior unless a later phase explicitly scopes that narrower
work.

## Explicit Non-Goals

This phase does not perform or authorize:

- evidence approval
- methodology approval
- moving-average parameter approval
- universe approval
- source approval
- benchmark approval
- cash proxy approval
- data acquisition
- data download
- data ingestion
- data files
- fixtures
- schema, code, notebook, or script
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
- no approved ETF universe
- no selected/approved data source
- no approved benchmark/cash proxy
- no approved methodology or parameters
- no approved final data storage/fixture policy
- no approved evidence review
- no acquired data
- no project-local deterministic reproduction
- no no-lookahead audit
- no production threshold/config provenance
- no implementation-scope approval
- no evaluator tests
- no reviewed evidence intake plan
- no collected primary evidence package
- no reviewed practitioner-source classification
- no approved total-return versus price-return decision
- no approved dividend/reinvestment treatment
- no approved corporate-action handling policy
- no approved correction/revision policy
- no approved point-in-time/as-of policy
- no approved transaction cost, slippage, spread, rebalance, fund-expense, tax,
  or friction assumption
- no robustness or parameter-sensitivity review
- no result-review template
- no promotion/rejection decision
- no trading implication or production threshold
