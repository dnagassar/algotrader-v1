# Phase 33 Step 14 - Broad ETF Primary Citation Verification Normalization

## Purpose

This document normalizes primary citation metadata for high-priority
moving-average evidence candidates in the broad-ETF simple moving-average
research trail.

Its purpose is to resolve or quarantine ambiguous source identities, record
which citation records appear ready for later limited formal review, and keep
source-identity readiness separate from evidence approval.

This phase does not approve evidence, methodology, parameters, data, ETF
universe, benchmark, cash proxy, reproduction, validation, implementation, or
trading use. Citation readiness in this document only routes later review.

This phase adds no data, fixture, PDF, raw report, notebook, script, schema,
test, source code, evaluator, signal computation, signal scoring, broker
behavior, OMS behavior, runtime behavior, scheduler behavior, persistence
behavior, portfolio behavior, ledger behavior, reconciliation behavior,
Alpaca behavior, ML behavior, vectorbt behavior, QuantConnect behavior,
notebook runtime behavior, or LLM trading-path behavior.

## External Artifact Status

External artifact intake record:

- Artifact title: Perplexity broad-ETF moving-average primary-source
  verification report.
- Source/tool: external Perplexity research.
- Date reviewed in this phase: 2026-05-14.
- Files/links reviewed in this repository: none. The project received an
  external report summary; no raw report, PDF, citation export, data file,
  notebook, source text, or downloaded artifact is added here.
- Source type: external-tool inference and scout research.
- Allowed status: scout, context, needs verification, citation routing, or
  candidate evidence only after later primary-source review.
- Repository placement: normalized into `docs/design` as a reviewed boundary
  document, not as raw external output.
- Normal pytest impact: none.

Phase 34 artifact-intake rules apply:

- The report is external-tool inference and scout material only.
- Reported abstracts, summaries, methodology descriptions, and performance
  claims are not project-verified strategy evidence.
- Reported source identities, titles, authors, dates, venues, DOI fields,
  SSRN fields, RePEc fields, publisher fields, and access notes require
  primary-page or full-text verification before formal review.
- Abstracts and claims must be checked against primary pages and full text,
  not accepted from the Perplexity output.
- No paper, methodology, parameter, evidence claim, data source, universe,
  benchmark, cash proxy, reproduction, validation, or implementation is
  approved by this citation normalization.

## Citation Verification Table

Rows below normalize reported citation metadata only. The labels
`verified primary citation`, `citation partially verified`, and
`source identity unresolved` describe intake routing status from the external
verification report and supplied summary. They are not evidence approval,
methodology approval, source approval, data approval, or implementation
approval.

| Source ID | Verified title | Author(s) | Year | Venue | DOI / SSRN / RePEc / publisher identifier | Primary links reported | Full-text access status | Citation reliability | Identity status | Later limited formal review eligibility | Remaining follow-up |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `MA-PRACT-001` | "A Quantitative Approach to Tactical Asset Allocation" | Mebane T. Faber | 2007; exact version date to verify | SSRN / author-hosted paper; publication history to verify | SSRN ID 962461; DOI not reported in supplied summary | SSRN page and open author-hosted PDF reported | full text appears accessible | high, subject to repo-trail primary-page/PDF verification | verified primary citation | eligible for later limited formal review if the open PDF and SSRN metadata are verified in the repo trail | Verify exact title, author, year, version, venue/publication history, SSRN page, author-hosted PDF, access date, and whether the reviewed text is the intended version |
| `ETF-ACADEMIC-001` | "Testing moving average trading strategies on ETFs" | Jing-Zhi Huang; Zhijian (James) Huang | 2020; accepted/published version date to verify | Journal of Empirical Finance, volume 57, pages 16-32 | DOI 10.1016/j.jempfin.2019.10.002; RePEc handle RePEc:eee:empfin:v:57:y:2020:i:c:p:16-32; SSRN working paper link reported | Publisher page, DOI/RePEc records, and SSRN working-paper link reported | access-limited / paywalled for published full text; working-paper/full-text access must be confirmed | high for citation identity; access path remains conditional | verified primary citation | conditional pending full-text access | Confirm exact publisher record, DOI, RePEc page, SSRN working-paper identity, full-text availability, version alignment, access date, and whether an inspectable primary text can support later review |
| `MA-ACADEMIC-001 / unresolved` | "Simple Market Timing with Moving Averages" | Unknown | Unknown | Unknown | No verified standalone DOI, SSRN, RePEc, publisher, or official identifier reported | No exact primary link reported | not accessible as a verified standalone source | low / unresolved | source identity unresolved | not eligible for formal review yet | Do not review under this title; resolve exact intended source or retire/quarantine the label; do not substitute related Zakamulin papers without separate IDs |
| `ZAKAMULIN-2014` | "The Real-Life Performance of Market Timing with Moving Average and Time-Series Momentum Rules" | Valeriy Zakamulin, reported | 2014 | Journal of Asset Management, reported | DOI 10.1057/jam.2014.25; SSRN ID 2242795; RePEc page reported | Publisher, SSRN, and RePEc pages reported | conditional pending full-text access; published text may be access-limited / paywalled | medium-high for citation identity, subject to primary-page verification | citation partially verified | conditional pending full-text access | Verify exact title, author list, year, venue, DOI, SSRN page, RePEc page, full text, version alignment, access date, and whether it should become a separate formal review candidate |
| `ZAKAMULIN-2016` | "Market Timing with Moving Averages: Anatomy and Implications" | Valeriy Zakamulin, reported | 2016; exact version date to verify | SSRN / working-paper or publication venue to verify | SSRN, DOI, RePEc, or publisher identifiers not normalized from supplied summary | Related Zakamulin primary/SSRN-style candidate reported | conditional pending full-text access | partial; exact identifiers still need primary verification | citation partially verified | conditional pending full-text access | Verify exact title, author list, year, venue, DOI/SSRN/RePEc/publisher identifiers, full text, version alignment, access date, and whether it is distinct from other Zakamulin candidates |
| `ZAKAMULIN-OPTIONAL` | Other related Zakamulin SSRN moving-average papers | Zakamulin authorship reported; exact authors to verify per paper | Unknown | SSRN / working-paper or publication venue to verify | Identifiers not normalized from supplied summary | Related Zakamulin SSRN papers reported | unknown until exact primary texts are identified | partial / unresolved by individual paper | source identity unresolved | context only; not eligible for formal review yet | Track only as optional source-discovery leads; assign separate source IDs only after exact title, authors, year, identifiers, and full text are verified |

## Readiness Decisions

Conservative citation-readiness decisions:

- `MA-PRACT-001` is eligible for later limited formal review if the open PDF
  and SSRN metadata are verified in the repo trail.
- `ETF-ACADEMIC-001` is eligible only conditionally, because the published
  version appears restricted and working-paper or full-text access must be
  confirmed before review.
- `MA-ACADEMIC-001 / unresolved`, "Simple Market Timing with Moving Averages",
  remains unresolved and should not be reviewed under that title.
- `ZAKAMULIN-2014` may be a separate later review candidate if primary text
  access is confirmed and the DOI, SSRN, RePEc, venue, and version metadata
  are verified.
- `ZAKAMULIN-2016` may be a separate later review candidate if exact
  identifiers and primary text access are confirmed.
- Other related Zakamulin SSRN papers remain context only until each has a
  separate source identity, verified identifiers, and inspectable primary
  text.
- No source is approved as evidence or methodology.

## Citation-Quality Cautions

Citation normalization must preserve these cautions:

- Perplexity output may mix primary links with inferred statements.
- Abstracts and claims must be checked against primary pages and full text.
- Publication metadata must be recorded before review.
- Review must use full primary text, not summaries.
- Version differences between SSRN working papers, author PDFs, publisher
  pages, and journal articles must be recorded before relying on extracted
  methodology details.
- No performance claim is accepted until independently reviewed and later
  reproduced where applicable.
- No reported source identity approves a moving-average rule, parameter,
  ETF universe, benchmark, cash proxy, data source, return construction,
  costs/frictions, robustness treatment, or implementation route.

## Required Follow-Up Before Formal Review

Before any formal review, the project must:

- confirm full text access
- verify exact title, author, year, and venue identifiers
- obtain or inspect primary PDF or official full text
- record DOI, SSRN, RePEc, publisher, author-page, version, and access-date
  metadata where available
- extract exact moving-average rules
- extract universe, period, frequency, benchmark, and cash proxy
- extract return construction and dividend/corporate-action treatment
- extract costs and frictions
- extract out-of-sample, robustness, and parameter-sensitivity treatment
- extract lookahead, survivorship, and data-snooping controls
- record limitations and non-claims

Any missing item remains a blocker. Unknowns must not be inferred into
approval.

## Recommended Next Gate

Recommended next gate: limited formal review of Faber only, after the open
PDF and SSRN metadata are verified in the repo trail.

This is the conservative default because `MA-PRACT-001` appears to have
accessible full text, while `ETF-ACADEMIC-001`, `ZAKAMULIN-2014`, and
`ZAKAMULIN-2016` remain conditional pending primary full-text access and
version verification.

Alternative later gates remain conditional only:

- limited formal review of `ETF-ACADEMIC-001` only if full text is accessible
- limited formal review of `ZAKAMULIN-2014` only if full text is accessible
- combined limited formal review of one to two sources only if primary full
  texts are available
- pause until primary PDFs or official full texts are obtained

No recommended gate approves evidence, methodology, parameters, data,
universe, benchmark, cash proxy, reproduction, validation, implementation, or
trading use.

## Relationship To Prior Gates

This citation normalization depends on and preserves these gates:

- Phase 33 Step 10, the broad-ETF moving-average evidence source package,
  defined source categories, evidence-quality standards, and review questions
  without approving sources or claims.
- Phase 33 Step 11, the broad-ETF moving-average evidence intake plan,
  defined source priority, intake workflow, disposition vocabulary, rejection
  criteria, and Phase 34 relationships before any formal evidence review.
- Phase 33 Step 12, the broad-ETF evidence source collection normalization,
  converted a Perplexity moving-average source collection into project intake
  format and kept external-tool output as scout material only.
- Phase 33 Step 13, the primary evidence text intake normalization, recorded
  reported primary-text availability and unresolved citation-quality issues
  without conducting formal evidence review.
- Phase 34 Step 2, the external research artifact intake checklist, keeps
  Perplexity reports as scout/context/needs-verification material until
  primary-source checks are complete.
- Phase 34 Step 3, the notebook/prototype policy boundary, keeps notebooks,
  prototype scripts, hosted outputs, vectorbt, QuantConnect, spreadsheets,
  charts, copied snippets, and external reports exploratory unless later
  promoted through a deterministic project-local route.

This phase does not weaken prior evidence, source, data, universe, benchmark,
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
- no source-specific formal evidence review
- no primary full-text verification in the repo trail
- no approved source identity for "Simple Market Timing with Moving Averages"
- no verified version alignment between working papers, author PDFs,
  publisher records, and journal articles
- no extracted moving-average rule from reviewed primary text
- no extracted universe, period, frequency, benchmark, or cash proxy from
  reviewed primary text
- no approved total-return versus price-return decision
- no approved dividend/reinvestment treatment
- no approved corporate-action handling policy
- no approved correction/revision policy
- no approved point-in-time/as-of policy
- no approved transaction cost, slippage, spread, rebalance, fund-expense,
  tax, or friction assumption
- no robustness or parameter-sensitivity review
- no benchmark/cash/risk-metric review
- no result-review template
- no promotion/rejection decision
- no trading implication or production threshold
