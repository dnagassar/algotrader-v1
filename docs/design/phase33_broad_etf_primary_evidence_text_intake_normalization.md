# Phase 33 Step 13 - Broad ETF Primary Evidence Text Intake Normalization

## Purpose

This document normalizes externally collected primary-text availability
information for the broad-ETF simple moving-average evidence candidates.

Its purpose is to determine which sources appear ready for later limited
formal review, which sources require citation verification, which sources are
unresolved, and which sources should remain context only.

This phase preserves the distinction between source availability and evidence
approval. It does not approve evidence, methodology, parameters, data, ETF
universe, benchmark, cash proxy, reproduction, validation, implementation, or
trading use.

This phase adds no data, fixture, notebook, script, schema, test, source code,
evaluator, signal computation, signal scoring, broker behavior, OMS behavior,
runtime behavior, scheduler behavior, persistence behavior, portfolio
behavior, ledger behavior, reconciliation behavior, Alpaca behavior, ML
behavior, vectorbt behavior, QuantConnect behavior, notebook runtime behavior,
or LLM trading-path behavior.

## External Artifact Status

External artifact intake record:

- Artifact title: second Perplexity broad-ETF moving-average primary-text
  source-gathering report.
- Source/tool: external Perplexity research.
- Date reviewed in this phase: 2026-05-14.
- Files/links reviewed in this repository: none. The project received an
  external report summary; no raw report, source PDF, notebook, citation
  export, data file, or source text is added here.
- Source type: external-tool inference and scout research.
- Allowed status: scout, context, needs verification, or candidate evidence
  only after later primary-source verification.
- Repository placement: normalized into `docs/design` as a reviewed boundary
  document, not as raw external output.
- Normal pytest impact: none.

Phase 34 artifact-intake rules apply:

- The report is external-tool inference and scout material only.
- Reported abstracts, summaries, methodology descriptions, and performance
  claims are not project-verified facts.
- Reported links, titles, authors, dates, venues, DOI fields, SSRN fields,
  RePEc fields, and publisher fields require primary-page verification before
  formal review.
- Source claims must be extracted from the actual primary text, not from the
  Perplexity summary.
- No paper, methodology, parameter, evidence claim, data source, universe,
  benchmark, cash proxy, reproduction, validation, or implementation is
  approved by this intake record.

## Sources Assessed

This phase assesses the primary-text availability status of these candidates:

- `ETF-ACADEMIC-001`: "Testing Moving Average Trading Strategies on ETFs".
- `MA-PRACT-001`: Faber, "A Quantitative Approach to Tactical Asset
  Allocation".
- `MA-ACADEMIC-001 / unresolved`: "Simple Market Timing with Moving Averages"
  or related Zakamulin/SSRN-style papers.
- Related candidate: "Market Timing with Moving Averages".
- Related candidate: "Timing the Market with a Combination of Moving
  Averages".
- `MA-ACADEMIC-004`: "Simple and Effective Market Timing with Tactical Asset
  Allocation".
- Related candidate: "The Real-Life Performance of Market Timing with Moving
  Average and Time-Series Momentum Rules".

Source identity remains unresolved for any title that cannot be tied to an
exact primary page, author list, year, version, DOI, SSRN identifier, RePEc
record, publisher page, or official author/paper page.

## Source Status Table

Rows below are intake records only. They do not approve sources, evidence,
claims, methodology, parameters, data, universe, benchmark, cash proxy,
reproduction, validation, implementation, evaluator behavior, signal behavior,
or trading use.

| Source ID | Candidate title | Reported primary link type | Full text availability status | Citation verification status | Methodology details available from primary text? | Data/universe details available? | Bias/no-lookahead details available? | Cost/friction details available? | Current status | Follow-up required | Eligible for later limited formal review? yes/no/conditional |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ETF-ACADEMIC-001` | "Testing Moving Average Trading Strategies on ETFs" | Reported SSRN, RePEc, publisher, or working-paper references; not repo-verified | primary text appears available; citation needs verification | citation needs verification for exact title, authors, year, venue, DOI, SSRN, RePEc, and version | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | eligible for later limited formal review only after primary text and citation verification | Verify metadata; inspect full primary text; extract rules, universe, period, frequency, benchmark, cash proxy, return construction, costs, bias controls, limitations, and non-claims | conditional |
| `MA-PRACT-001` | Faber, "A Quantitative Approach to Tactical Asset Allocation" | Reported open PDF plus SSRN or author/official links; not repo-verified | primary text appears available; citation needs verification | citation needs verification for exact version, date, author page, SSRN page, and publication history | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | eligible for later limited formal review only after open PDF and citation verification | Verify open PDF and official citation path; inspect full primary text; extract moving-average rule, universe, period, frequency, benchmark, cash proxy, return construction, costs, robustness, limitations, and non-claims | conditional |
| `MA-ACADEMIC-001 / unresolved` | "Simple Market Timing with Moving Averages" | No exact primary-source match reported | primary text not yet available; source identity unresolved | source identity unresolved | No | No | No | No | not eligible for formal review yet | Resolve exact intended source or retire this label; do not substitute related papers without a separate source ID | no |
| `MA-ACADEMIC-001A` | "Market Timing with Moving Averages" | Reported related Zakamulin/SSRN-style or working-paper candidate; not repo-verified | primary text appears available only as a reported lead; citation needs verification | citation needs verification; exact source identity must be separated from `MA-ACADEMIC-001` | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | context only until exact citation is verified; possible separate candidate later | Verify exact title, authors, year, version, venue, DOI/SSRN identifier, and full text before assigning any evidence role | conditional |
| `MA-ACADEMIC-001B` | "Timing the Market with a Combination of Moving Averages" | Reported related Zakamulin/SSRN-style or working-paper candidate; not repo-verified | primary text appears available only as a reported lead; citation needs verification | citation needs verification; exact source identity must be separated from `MA-ACADEMIC-001` | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | context only until exact citation is verified; possible separate candidate later | Verify exact title, authors, year, version, venue, DOI/SSRN identifier, and full text before assigning any evidence role | conditional |
| `MA-ACADEMIC-004` | "Simple and Effective Market Timing with Tactical Asset Allocation" | Reported related academic or working-paper candidate; not repo-verified | primary text appears available only as a reported lead; citation needs verification | citation needs verification; exact source identity, author list, and version remain unverified | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | context only until exact citation is verified; possible later methodology-context review | Verify exact primary page and full text; extract rule, universe, benchmark, cash proxy, costs, robustness, bias controls, limitations, and non-claims | conditional |
| `MA-ACADEMIC-001C` | "The Real-Life Performance of Market Timing with Moving Average and Time-Series Momentum Rules" | Reported related SSRN-style, working-paper, or publisher candidate; not repo-verified | primary text appears available only as a reported lead; paywalled / access-limited if only a publisher page is reachable | citation needs verification; exact source identity and access path remain unverified | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | Conditional only; not extracted from repo-reviewed primary text | context only until exact citation and accessible primary text are verified | Verify exact citation and whether full primary text is open, paywalled / access-limited, or unavailable; track as a separate candidate if verified | conditional |
| `EXT-SCOUT-002` | Second Perplexity primary-text source-gathering report | External-tool report summary | primary text not yet available as project evidence; context only | citation needs verification for every reported source | No | No | No | No | context only; external-tool inference; not evidence | Use only to route source verification questions; do not extract claims from the report as evidence | no |

## Citation-Quality Cautions

The Perplexity report contains mixed citation quality. Some fields appear to
cite secondary, index, search-result, or unrelated pages rather than primary
paper pages.

Before formal review, the project must verify exact author, title, year,
venue, DOI, SSRN identifier, RePEc identifier, publisher page, author page,
version, and access date from primary pages.

Source claims must be extracted from actual primary text. Reported abstracts,
methodology summaries, performance claims, and relevance classifications in
the Perplexity report must not be accepted as true unless they are later
verified from the full primary source and recorded in a scoped review.

## Preliminary Review Readiness

Conservative readiness decision: pause until primary text and citation
verification is complete.

`MA-PRACT-001` may be eligible for later limited formal review if the reported
open PDF, SSRN page, author page, version, and citation metadata are verified.

`ETF-ACADEMIC-001` may be eligible for later limited formal review if the
reported SSRN working paper, official text, RePEc record, publisher page, or
equivalent primary source is accessible and citation metadata is verified.

`MA-ACADEMIC-001 / unresolved`, "Simple Market Timing with Moving Averages",
is not eligible for formal review until the exact intended source is resolved.

Related Zakamulin/SSRN-style papers should be tracked as separate candidates
only if exact citations and primary texts are verified. They must not be used
as substitutes for the unresolved `MA-ACADEMIC-001` label without explicit
renaming and source-identity cleanup.

## Required Follow-Up Before Formal Review

Before any formal review, the project must:

- verify exact title, authors, year, venue, DOI, SSRN identifiers, RePEc
  identifiers, publisher pages, author pages, versions, and access dates
- inspect full primary text
- record abstracts from primary sources only
- extract exact moving-average rules
- extract universe, period, frequency, benchmark, and cash proxy
- extract return construction and dividend, distribution, split, and other
  corporate-action treatment
- extract transaction costs, bid-ask spreads, slippage, turnover, fund
  expenses, taxes, rebalance timing, and other frictions
- extract out-of-sample, robustness, and parameter-sensitivity treatment
- extract lookahead, survivorship, point-in-time, data-snooping, overfitting,
  multiple-testing, restatement, and publication-lag controls
- record limitations and non-claims

Any missing item remains a blocker. Unknowns must not be inferred into
approval.

## Recommended Next Gate

Recommended next gate: pause until primary text and citation verification is
complete.

If later primary-text verification is completed outside this phase, the next
docs-only gate may be one of:

- limited formal review of Faber only
- limited formal review of `ETF-ACADEMIC-001` only
- combined limited formal review of one to two sources if both primary texts
  and citation metadata are verified

The conservative default remains no formal review from the Perplexity summary
alone.

## Relationship To Prior Gates

This intake normalization depends on and preserves these gates:

- Phase 33 Step 10, the broad-ETF moving-average evidence source package,
  defined evidence categories and review questions without collecting or
  approving sources.
- Phase 33 Step 11, the broad-ETF moving-average evidence intake plan,
  defined source priority, intake workflow, disposition vocabulary, rejection
  criteria, and Phase 34 relationships before any evidence review.
- Phase 33 Step 12, the broad-ETF evidence source collection normalization,
  converted the first Perplexity moving-average source list into project
  intake format and recommended pausing until full primary texts are
  available.
- Phase 34 Step 2, the external research artifact intake checklist, keeps
  Perplexity reports as scout/context/needs-verification material until
  primary-source checks are complete.
- Phase 34 Step 3, the notebook/prototype policy boundary, keeps notebooks,
  prototype scripts, hosted outputs, vectorbt, QuantConnect, spreadsheets,
  charts, copied snippets, and external reports exploratory unless later
  promoted through a deterministic path.

This phase does not weaken prior evidence, data, source, universe, benchmark,
cash proxy, storage, fixture, reproduction, validation, implementation, or
trading gates.

## Explicit Non-Goals

This phase does not perform or authorize:

- evidence approval
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
- no source-specific primary-text verification
- no verified citation metadata for the second Perplexity source list
- no resolved identity for "Simple Market Timing with Moving Averages"
- no verified separation between related Zakamulin/SSRN-style candidates and
  the unresolved `MA-ACADEMIC-001` label
- no reviewed practitioner-source classification
- no approved total-return versus price-return decision
- no approved dividend/reinvestment treatment
- no approved corporate-action handling policy
- no approved correction/revision policy
- no approved point-in-time/as-of policy
- no approved transaction cost, slippage, spread, rebalance, fund-expense, tax,
  or friction assumption
- no robustness or parameter-sensitivity review
- no benchmark/cash/risk-metric review
- no result-review template
- no promotion/rejection decision
- no trading implication or production threshold
