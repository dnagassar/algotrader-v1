# Phase 33 Step 11 - Broad ETF Moving-Average Evidence Intake Plan

## Purpose

This document defines how moving-average evidence will be collected and
reviewed later for the broad-ETF simple moving-average research candidate.

The plan exists to prevent ad hoc evidence selection, source shopping, and
cherry-picking before any future methodology review, reproduction protocol,
validation route, signal-definition discussion, evaluator work, or
implementation planning.

It does not approve evidence, methodology, moving-average parameters, source
data, an ETF universe, a benchmark, a cash proxy, validation, reproduction, a
signal definition, an evaluator, implementation, profitability, production
readiness, or trading use.

This phase adds no data, fixture, notebook, script, schema, test, source code,
evaluator, signal computation, signal scoring, broker behavior, OMS behavior,
runtime behavior, scheduler behavior, persistence behavior, portfolio behavior,
ledger behavior, reconciliation behavior, Alpaca behavior, ML behavior,
vectorbt behavior, QuantConnect behavior, notebook runtime behavior, or LLM
trading-path behavior.

## Intake Scope

Future evidence intake should cover these categories from Phase 33 Step 10:

- academic moving-average papers
- practitioner trend-following references
- ETF-specific references
- benchmark and buy-and-hold references
- transaction-cost and friction references
- data-adjustment and total-return caveat references
- no-lookahead and backtest-bias references
- robustness and parameter-sensitivity references

These categories are collection and classification targets only. They do not
approve any paper, source, claim, parameter, ETF universe, data source,
benchmark, cash proxy, cost assumption, methodology, validation route, or
implementation route.

## Source Priority

Future intake should prefer sources in this order:

1. Primary academic papers and official publications.
2. Official methodology documentation.
3. Reputable practitioner research.
4. Official data or source documentation.
5. Secondary summaries.
6. Blogs or marketing materials as context only.
7. LLM summaries never as evidence.

Lower-priority sources may help locate primary sources or frame questions, but
they must not override primary documentation or become project evidence without
later formal review.

## Intake Workflow

Each candidate source should move through the same intake workflow:

1. Identify the candidate source without treating it as accepted evidence.
2. Record the citation, stable link, version, access date, and any retrieval
   caveats available at intake time.
3. Classify the source type, such as academic paper, official methodology
   documentation, practitioner research, official source documentation,
   secondary summary, blog, marketing material, notebook output, external
   scout report, or LLM-generated summary.
4. Summarize the exact claim being reviewed in narrow language.
5. Separate reviewed evidence, project inference, and remaining uncertainty.
6. Identify the methodology, universe, period, frequency, and benchmark or
   comparison used by the source.
7. Identify any lookahead, point-in-time, survivorship, multiple-testing,
   overfitting, data-snooping, restatement, publication-lag, and
   corporate-action controls stated by the source.
8. Identify transaction cost, bid-ask spread, slippage, turnover, fund expense,
   tax, rebalance timing, and other friction assumptions.
9. Assess relevance and transferability to broad ETFs without claiming that the
   transfer is valid.
10. Record limitations, non-claims, unresolved questions, and conflicts with
    other sources or project constraints.
11. Assign one cautious disposition label.

Intake records must preserve negative, mixed, missing, or uncertain findings.
They must not collapse unresolved evidence into a single favorable narrative.

## Disposition Vocabulary

Only these cautious disposition labels should be used during intake:

| Disposition | Meaning |
| --- | --- |
| review candidate | The source is worth later review, but no claim has been accepted. |
| methodology context | The source may help frame methodology questions later. |
| benchmark/context | The source may help frame benchmark or buy-and-hold comparison questions later. |
| bias-control context | The source may help frame no-lookahead, survivorship, point-in-time, overfitting, or data-snooping questions later. |
| friction/cost context | The source may help frame transaction cost, spread, slippage, turnover, expense, tax, or rebalance-friction questions later. |
| rejected / unsupported | The source is rejected or downgraded because intake found unsupported, vague, conflicting, or out-of-scope material. |
| requires primary-source verification | The source cannot be used until a primary source or official documentation is found and reviewed. |
| eligible for later formal review | The source has enough citation and scope detail to be reviewed later, but it is still not approved evidence. |

No disposition approves methodology, parameters, data, a universe, benchmark,
cash proxy, validation, reproduction, signal behavior, evaluator behavior,
implementation, production readiness, or trading use.

## Evidence Rejection Criteria

Reject or downgrade a source when any of the following applies:

- no primary citation is available
- the claim is unsupported or vague
- a performance claim lacks data or provenance
- the universe, date range, or frequency is unclear
- lookahead, survivorship, data-snooping, restatement, or other bias concerns
  are unaddressed
- parameter choice appears cherry-picked or optimized after seeing results
- the source is marketing-only
- the source implies implementation readiness, trading readiness, or production
  readiness
- the source conflicts with project constraints, including deterministic,
  offline-safe, credential-free normal pytest and broker/runtime/trading-path
  isolation

Downgraded sources may remain context only when useful for question discovery,
but they must not be used as evidence.

## Evidence Review Sequence

Recommended later review order:

1. Methodology and core moving-average references.
2. Bias, no-lookahead, point-in-time, survivorship, and backtest-bias
   references.
3. ETF-specific or broad-market trend references.
4. Benchmark, cash proxy, and friction references.
5. Robustness and parameter-sensitivity references.

This sequence is only a review-order recommendation. It does not approve
review, evidence, methodology, parameters, sources, data, universe, benchmark,
cash proxy, reproduction, validation, or implementation.

## Required Intake Table

Future intake records should use this table before any formal evidence review:

| Source ID | Citation / reference | Source type | Claim reviewed | Universe / data | Period / frequency | Methodology relevance | Bias controls | Costs/frictions | ETF transferability | Limitations | Disposition | Follow-up needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD exact claim; not accepted | TBD | TBD | TBD | TBD | TBD | TBD; not approved | TBD | review candidate | TBD |

Adding a row to this table is intake only. It is not source approval, evidence
approval, methodology approval, universe approval, benchmark approval, cash
proxy approval, parameter approval, data approval, reproduction approval,
validation approval, evaluator approval, signal approval, or implementation
approval.

## Relationship To Phase 34

This intake plan depends on Phase 34 boundaries as advisory-input controls:

- Phase 34 Step 1 keeps external research integration advisory only. External
  reports, platform outputs, public data notes, spreadsheets, copied snippets,
  and ad hoc analysis cannot become source of truth through intake.
- Phase 34 Step 2 provides the external artifact intake checklist. Future
  externally produced research artifacts should be normalized with metadata,
  evidence labels, review questions, routing outcomes, repository placement,
  and explicit non-goals before they can influence project decisions.
- Phase 34 Step 3 keeps notebooks, prototype scripts, vectorbt experiments,
  QuantConnect outputs, spreadsheets, CSV extracts, charts, external reports,
  and copied snippets exploratory only until later deterministic review.
- LLM outputs and notebook results remain advisory unless their underlying
  claims are normalized into reviewed documentation, tied to traceable primary
  sources, checked against project constraints, and later reproduced through a
  scoped deterministic project-local protocol.

Phase 34 artifacts cannot directly approve evidence, source data, notebooks,
dependencies, reproduction, validation, `ValidatedResearchArtifact`,
`ValidatedSignalDefinition`, evaluator behavior, production thresholds, or
trading implications.

## Recommended Next Gate

Recommended next docs-only gate: first limited methodology evidence review.

That gate should occur only after specific candidate sources have been
collected externally and recorded through this intake plan. It should review
limited methodology claims first, preserve rejected and uncertain evidence, and
avoid approving evidence, parameters, universe, benchmark, cash proxy, data
source, reproduction, validation, signal definition, evaluator behavior,
implementation, or trading use.

If specific sources are not available, the safer route is to pause until
candidate citations and links are collected outside the project.

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
- no source-specific intake records
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
