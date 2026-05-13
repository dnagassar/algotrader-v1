# Phase 32 Step 4 - P30-BL-002 Primary Source Verification Gate

## Purpose

This phase verifies primary-source identity and formal-review intake eligibility
for selected high-value `P30-BL-002` candidates before any formal review begins.
It checks provenance, title, author/source, date/version, primary links, dataset
claims, code/data availability, and whether the selected candidates are safe to
route into a later review queue.

This phase is a verification gate only. It does not review, approve, validate,
promote, implement, or mark `P30-BL-002` as implementation-ready.

## Prior state

- `P30-BL-001` is mechanics-only dispositioned. It is not validated, approved,
  promoted, threshold-justified, or implementation-ready.
- `P30-BL-002` remains a sourcing handle only.
- Phase 32 Step 3 normalized `P30-BL-002-S01` through `P30-BL-002-S23` from the
  supplied scout reports.
- The Step 3 package is partial, candidate-only, unreviewed, unvalidated,
  unapproved, and not implementation-ready.
- Step 3 classified the package as requiring additional primary-source
  verification before any formal review can rely on the selected entries.

## Verification scope

This gate checks only the selected high-value Step 3 leads:

| Lead | Normalized source id | Gate role |
| --- | --- | --- |
| Negative-control moving-average timing | `P30-BL-002-S01` | Lookahead and moving-average timing negative-control candidate |
| Data-snooping / out-of-sample negative control | `P30-BL-002-S03` | Data-snooping and technical-rule universe negative-control candidate |
| Time-series momentum | `P30-BL-002-S05` | Direct time-series momentum source candidate |
| Point-in-time snapshot methodology | `P30-BL-002-S08` | Point-in-time methodology-only infrastructure candidate |

## Verification method

Primary sources were preferred over scout summaries. The supplied DOCX
verification report was used as a local verification input for the
time-series-momentum source and as non-authoritative context for the remaining
leads. Scout reports were treated only as candidate-discovery material.

The gate checked primary or near-primary source pages where available:

- SSRN primary page for Valeriy Zakamulin,
  "Revisiting the Profitability of Market Timing with Moving Averages":
  <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2743119>
- SSRN primary page for Ryan Sullivan, Allan Timmermann, and Halbert White,
  "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap":
  <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=160330>
- American Finance Association issue page for the Journal of Finance
  publication details of the Sullivan, Timmermann, and White article:
  <https://afajof.org/issue/volume-54-issue-5/>
- ScienceDirect primary article page for Moskowitz, Ooi, and Pedersen,
  "Time series momentum":
  <https://www.sciencedirect.com/science/article/pii/S0304405X11002613>
- NYU/Stern author-hosted PDF for Moskowitz, Ooi, and Pedersen:
  <https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf>
- FactSet PDF for "Accurately Backtesting Financial Models Through
  Point-in-Time Consensus Estimates":
  <https://www.insight.factset.com/hubfs/Resources%20Section/White%20Papers/ID11996_point_in_time.pdf>

## Verified source entries

### P30-BL-002-S01 - Revisiting the Profitability of Market Timing with Moving Averages

- Normalized source id: `P30-BL-002-S01`.
- Title: "Revisiting the Profitability of Market Timing with Moving Averages".
- Primary-source link or citation: SSRN abstract page at
  <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2743119>; SSRN DOI
  `10.2139/ssrn.2743119`. The publisher DOI
  `10.1111/irfi.12132` remains a formal-review citation check because the
  Wiley page was not accessible during this gate.
- Author/source: Valeriy Zakamulin, University of Agder - School of Business
  and Law; SSRN working-paper record.
- Date/version: SSRN page reports 10 pages posted March 8, 2016, last revised
  September 15, 2016, and date written August 25, 2016.
- Source type: Academic working paper / published-article candidate.
- Verified dataset scope: The primary SSRN abstract states that the paper
  reexamines the same dataset and trading rules as Glabadanidis, "Market Timing
  With Moving Averages" (2015). Exact source data, vendors, and sample dates
  remain formal-review checks.
- Verified asset class/universe: Moving-average timing in a stock-market /
  index-timing setting, based on the cited Glabadanidis study. Exact universe
  remains a formal-review check.
- Verified timeframe: Not fully verified from the abstract-level gate. The
  publication/version dates are verified; sample windows still require full-text
  review.
- Verified input/indicator definition: Moving-average market-timing strategy;
  formal review must extract exact windows, crossover conventions, and signal
  timing.
- Verified threshold/parameter relevance: Relevant as a moving-average
  threshold/timing negative-control candidate, especially where signal timing
  can introduce lookahead.
- Verified validation design: The primary abstract reports re-simulation
  without lookahead bias and comparison against buy-and-hold. This gate does
  not accept or validate the result.
- Verified point-in-time or no-lookahead controls: The primary abstract directly
  frames the contribution as removing lookahead-biased simulation. Exact
  timestamp and execution conventions remain formal-review checks.
- Verified reproducibility/code/data availability: The SSRN abstract reports
  supplied R code for reproducing reported results. Actual code access, license,
  data files, deterministic rerun feasibility, and archival path remain
  unresolved.
- Verified robustness or out-of-sample evidence: Not accepted by this gate.
  Any subperiod, cost, or robustness claims remain unreviewed until the full
  source and code are inspected.
- Unverified or questionable scout claims: Exact dataset, daily/monthly split,
  total-return handling, transaction-cost treatment, journal version details,
  and code/data accessibility were not fully verified here.
- Limitations: The verified facts are mostly abstract-level plus provenance.
  Source is best treated as a negative-control candidate, not positive
  threshold evidence.
- Non-claims: This gate does not claim the moving-average strategy is
  predictive, profitable, robust, production-ready, or implementation-ready.
- Formal review intake eligibility: Yes, limited to negative-control and
  no-lookahead/timing review intake.
- Remaining formal-review checks: Retrieve and archive the accessible full
  text, verify journal citation details, inspect R code/data access and license,
  extract exact dataset/sample/rule timing, reproduce the timing correction, and
  classify any result only under the Phase 30 evidence standard.

### P30-BL-002-S03 - Data-Snooping, Technical Trading Rule Performance, and the Bootstrap

- Normalized source id: `P30-BL-002-S03`.
- Title: "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap".
- Primary-source link or citation: SSRN abstract page at
  <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=160330>; Journal of
  Finance issue page at <https://afajof.org/issue/volume-54-issue-5/>; DOI
  `10.1111/0022-1082.00163`.
- Author/source: Ryan Sullivan, Allan Timmermann, and Halbert White; Journal of
  Finance / American Finance Association publication record; SSRN record.
- Date/version: SSRN posted May 18, 1999, with a prior UCSD discussion-paper
  version posted March 8, 1998; Journal of Finance volume 54, issue 5,
  October 1999, pages 1647-1691.
- Source type: Peer-reviewed empirical finance paper and working-paper record.
- Verified dataset scope: The primary abstract states that the paper expands
  the Brock, Lakonishok, and LeBaron rule universe and applies rules to 100
  years of daily Dow Jones Industrial Average data.
- Verified asset class/universe: Dow Jones Industrial Average; technical
  trading-rule universe.
- Verified timeframe: 100 years of daily DJIA data is verified at abstract
  level. Exact start/end dates and any separate out-of-sample window remain
  formal-review checks.
- Verified input/indicator definition: Simple technical trading rules,
  including an expanded universe of rules relative to Brock, Lakonishok, and
  LeBaron. Full rule tables must be reviewed before any binding claim.
- Verified threshold/parameter relevance: Strong methodology relevance because
  the rule universe and multiple-comparison/data-snooping adjustment are the
  subject of the source.
- Verified validation design: Uses White's Reality Check bootstrap methodology
  to evaluate technical trading rules while quantifying data-snooping bias.
- Verified point-in-time or no-lookahead controls: Not specifically verified
  by this gate beyond the historical daily-rule framing. Exact signal timing,
  sample splits, and data availability assumptions remain formal-review checks.
- Verified reproducibility/code/data availability: SSRN states "Not Available
  for Download"; no open code or packaged dataset was verified here.
- Verified robustness or out-of-sample evidence: The source is verified as a
  data-snooping methodology and technical-rule universe negative-control
  candidate. Any out-of-sample result remains unaccepted until full-text review.
- Unverified or questionable scout claims: The Step 3 claim of a strict
  post-selection out-of-sample extension was not fully verified by this gate.
  Rule count, exact sample dates, transaction costs, and implementation details
  require full-text inspection.
- Limitations: Single-index historical focus; no verified public code/package;
  methodology relevance is strong but not implementation-ready.
- Non-claims: This gate does not claim any technical rule, threshold, or model
  is predictive, profitable, robust, production-ready, or implementation-ready.
- Formal review intake eligibility: Yes, limited to negative-control /
  data-snooping methodology review intake.
- Remaining formal-review checks: Archive full article access, extract all rule
  families and parameter grids, verify exact sample periods and any OOS split,
  document costs and bootstrap assumptions, decide whether the source is
  methodology-only or dataset-specific, and assess deterministic reproducibility.

### P30-BL-002-S05 - Time Series Momentum

- Normalized source id: `P30-BL-002-S05`.
- Title: "Time series momentum" / "Time Series Momentum".
- Primary-source link or citation: ScienceDirect article page at
  <https://www.sciencedirect.com/science/article/pii/S0304405X11002613>;
  DOI `10.1016/j.jfineco.2011.11.003`; NYU/Stern author-hosted PDF at
  <https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf>.
- Author/source: Tobias J. Moskowitz, Yao Hua Ooi, and Lasse Heje Pedersen;
  Journal of Financial Economics, Elsevier.
- Date/version: ScienceDirect article page reports Journal of Financial
  Economics volume 104, issue 2, May 2012, pages 228-250, with copyright 2011.
  The supplied DOCX verification report records received/revised/accepted and
  online availability dates from the article metadata.
- Source type: Peer-reviewed academic paper.
- Verified dataset scope: The supplied verification report records 58 liquid
  futures and forward contracts across commodities, currencies, developed
  equity index futures, and developed government bond futures, with data from
  January 1965 through December 2009 and primary evaluation from 1985 onward.
- Verified asset class/universe: Futures/forwards across equity index,
  currency, commodity, and bond markets.
- Verified timeframe: Monthly formation and holding rules over the paper's
  historical sample; exact instrument-level starts and availability remain
  formal-review checks.
- Verified input/indicator definition: Lagged own excess returns; a sign-based
  trading variant uses cumulative excess return over a selected lookback and
  applies the sign of that lagged return. The supplied report records lookback
  and holding grids including 1, 3, 6, 9, 12, 24, 36, and 48 months.
- Verified threshold/parameter relevance: Relevant to deterministic zero
  threshold on lagged-return sign and to lookback/holding parameter provenance.
- Verified validation design: The source uses pooled regressions, asset-class
  decomposition, factor regressions, and parameter comparisons. This gate does
  not accept or validate the reported evidence.
- Verified point-in-time or no-lookahead controls: The supplied verification
  report records lag-only signal construction and lagged volatility estimates
  intended to avoid lookahead in volatility estimation. Database-level PIT
  snapshot semantics are not the paper's focus.
- Verified reproducibility/code/data availability: The primary paper documents
  data sources and methodology but does not provide a formal code repository or
  turnkey downloadable dataset in the PDF itself.
- Verified robustness or out-of-sample evidence: The supplied report records
  cross-asset, contract-maturity, volatility-scaling, parameter, and subperiod
  checks. This gate treats those as formal-review targets, not accepted evidence.
- Unverified or questionable scout claims: Any claim that this source provides
  ready-to-run code, a complete public dataset, PIT database engineering, broker
  execution logic, or live-trading validation is unsupported.
- Limitations: Futures roll mechanics, data-vendor reproducibility, transaction
  costs, margin/leverage constraints, and exact factor timing require formal
  review. It is an academic source, not an implementation package.
- Non-claims: This gate does not claim that time-series momentum is currently
  predictive, profitable, robust, production-ready, or implementation-ready.
- Formal review intake eligibility: Yes, limited to formal review intake as a
  direct time-series-momentum source candidate.
- Remaining formal-review checks: Reconstruct roll rules and contract
  selection, verify reproducible point-in-time futures data, rederive the
  volatility estimator, reproduce core statistics under deterministic local
  constraints, document transaction-cost and leverage assumptions, and map any
  candidate signal definition only after review.

### P30-BL-002-S08 - Accurately Backtesting Financial Models Through Point-in-Time Consensus Estimates

- Normalized source id: `P30-BL-002-S08`.
- Title: "Accurately Backtesting Financial Models Through Point-in-Time
  Consensus Estimates". This corrects the Step 3 normalized title
  "Accurately Backtesting Financial Models Using Point-in-Time Data".
- Primary-source link or citation: FactSet PDF at
  <https://www.insight.factset.com/hubfs/Resources%20Section/White%20Papers/ID11996_point_in_time.pdf>.
- Author/source: Annabel Hudson, Richard Dutheil, and Juliana Germain;
  FactSet.
- Date/version: No explicit publication date was verified in the PDF during
  this gate. The PDF states that the point-in-time database is not available
  before December 2009 and describes consensus methodology as of
  September 9, 2017.
- Source type: Vendor white paper / methodology document.
- Verified dataset scope: FactSet point-in-time consensus estimates database;
  consensus data snapshots for each covered company, including estimate items,
  statistics, consensus windows, and related FactSet estimate fields.
- Verified asset class/universe: FactSet Estimates universe / listed equities
  covered by the vendor database; exact licensed universe depends on access.
- Verified timeframe: History begins as of December 2009 for the PIT database,
  according to the PDF. The paper also shows examples over a seven-year study
  window for FY1 Sales differences.
- Verified input/indicator definition: Consensus estimates and related fields,
  including annual/quarterly/semiannual rolling fiscal periods, EPS, EBIT,
  EBITDA, free cash flow, net debt, net income, sales, rating, target price, and
  estimate statistics.
- Verified threshold/parameter relevance: Methodology-only relevance to
  `as_of`, input-timestamp, and snapshot semantics; not a signal-threshold
  source.
- Verified validation design: Vendor methodology compares traditional FactSet
  Estimates data modes with a point-in-time database and explains why later
  corrections, deletions, currency changes, and local-time cutoffs can alter
  historical backtests.
- Verified point-in-time or no-lookahead controls: The PDF describes daily
  local-midnight company snapshots and excludes data entered after that
  snapshot from that date's consensus calculation.
- Verified reproducibility/code/data availability: Proprietary FactSet access is
  required. The PDF lists FQL and Screening function identifiers but does not
  provide open data or open code.
- Verified robustness or out-of-sample evidence: Not strategy robustness
  evidence. This is infrastructure/methodology evidence only.
- Unverified or questionable scout claims: The Step 3 title was inaccurate; no
  explicit PDF publication date was verified; any claim that the white paper
  validates a trading signal, threshold, edge, or open reproducible artifact is
  unsupported.
- Limitations: Vendor/proprietary source, no open dataset, no direct simple
  threshold artifact, and no strategy-level formal review value except as a
  PIT/no-lookahead methodology anchor.
- Non-claims: This gate does not claim that any FactSet-derived signal is
  predictive, profitable, robust, production-ready, or implementation-ready.
- Formal review intake eligibility: Maybe, limited to methodology-only review
  intake for point-in-time snapshot semantics; no for direct threshold-source
  intake.
- Remaining formal-review checks: Verify publication/version date, license and
  access restrictions, exact FQL semantics, timezone/cutoff behavior under local
  data constraints, and applicability to any future offline point-in-time store.

## Intake eligibility summary

| Normalized id | Title | Verification result | Intake eligibility | Main reason | Remaining gap |
| --- | --- | --- | --- | --- | --- |
| `P30-BL-002-S01` | Revisiting the Profitability of Market Timing with Moving Averages | Primary SSRN identity and core lookahead claim verified | Yes, limited negative-control intake | Directly relevant to MA timing and lookahead simulation risk | Full text, code/data access, exact dataset, and timing conventions |
| `P30-BL-002-S03` | Data-Snooping, Technical Trading Rule Performance, and the Bootstrap | Primary SSRN identity plus Journal of Finance publication details verified | Yes, limited negative-control intake | Directly relevant to data snooping across technical-rule universes | Full text, exact rule tables, sample dates, OOS details, and reproducibility |
| `P30-BL-002-S05` | Time Series Momentum | Primary article identity and supplied source report verify detailed TSM provenance | Yes, limited direct-source intake | Direct TSM source with dataset, parameters, and no-lookahead methodology to review | Roll rules, data reconstruction, reproducibility, costs, and local PIT alignment |
| `P30-BL-002-S08` | Accurately Backtesting Financial Models Through Point-in-Time Consensus Estimates | Primary FactSet PDF verified; Step 3 title corrected | Maybe, methodology-only intake | Useful for `as_of`/PIT snapshot semantics | Publication date, license/access, exact FQL behavior, and local applicability |

## Routing decision

Proceed to limited formal review intake for selected candidates only, with
strict scope boundaries:

- `P30-BL-002-S05` may proceed as the strongest direct time-series-momentum
  formal-review intake candidate.
- `P30-BL-002-S03` may proceed as a data-snooping and technical-rule-universe
  negative-control intake candidate.
- `P30-BL-002-S01` may proceed as a moving-average timing and lookahead
  negative-control intake candidate.
- `P30-BL-002-S08` may proceed only as a methodology-only PIT/no-lookahead
  infrastructure reference, not as a threshold or signal artifact.

Perform additional verification before any formal review relies on unverified
details, especially source PDFs, exact sample windows, code/data availability,
license/access constraints, transaction-cost assumptions, and deterministic
reproducibility. Quarantine scout-only claims that are not backed by primary
sources. Continue additional sourcing for a more open and directly reproducible
PIT-snapshot source if `P30-BL-002-S08` proves too proprietary for review needs.

This routing decision does not approve, validate, promote, or implement any
source.

Phase 32 Step 5 records the next documentation-only intake plan in
[`phase32_p30_bl_002_limited_formal_review_intake_plan.md`](phase32_p30_bl_002_limited_formal_review_intake_plan.md).
That plan uses this gate as the source of truth for selected candidates, places
negative-control review before candidate-evidence review, and defines evidence
requirements without performing formal review.

Phase 32 Step 6 records the S01-only formal review in
[`phase32_p30_bl_002_s01_formal_review.md`](phase32_p30_bl_002_s01_formal_review.md).
It uses this gate's S01 identity and scope findings, passes S01 only for
limited negative-control/no-lookahead use, and keeps all validation,
threshold-approval, signal-definition, and implementation routes blocked.

Phase 32 Step 7 records the S03-only formal review in
[`phase32_p30_bl_002_s03_formal_review.md`](phase32_p30_bl_002_s03_formal_review.md).
It uses this gate's S03 identity and scope findings, passes S03 only for
limited negative-control/data-snooping/OOS guardrail use, and keeps all
validation, threshold-approval, signal-definition, and implementation routes
blocked.

Phase 32 Step 8 records the S08-only formal review in
[`phase32_p30_bl_002_s08_formal_review.md`](phase32_p30_bl_002_s08_formal_review.md).
It uses this gate's S08 identity and scope findings, passes S08 only for
methodology-only PIT review material, and keeps all validation,
threshold-approval, signal-definition, implementation, and trading-readiness
routes blocked.

## Explicit non-claims

This phase does not validate a signal, threshold, edge, profitability,
robustness, production threshold, config value, or implementation readiness.

This phase does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, bind a signal definition to an artifact, formally
review `P30-BL-002`, promote `P30-BL-002`, or make it implementation-ready.

This phase does not add a real signal evaluator, signal computation, scoring,
ranking, direction, confidence, probability, actionability, broker behavior,
Alpaca behavior, runtime behavior, scheduler behavior, persistence, ML, or LLM
trading-path behavior.

## Remaining blockers

Evaluator implementation remains blocked by all of the following:

- no formal review beyond S01's limited negative-control/no-lookahead review,
  S03's limited negative-control/data-snooping/OOS guardrail review, and S08's
  methodology-only PIT review
- no `P30-BL-002-S05` formal review
- the `P30-BL-002-S08` review is methodology-only and does not provide
  dataset-specific reproduction, threshold approval, signal validation,
  artifact promotion, signal-definition support, or implementation readiness
- no `ValidatedResearchArtifact`
- no `ValidatedSignalDefinition`
- no approved threshold/config provenance
- no implementation scope approval
- no evaluator tests
- no accepted point-in-time/no-lookahead review for any proposed dataset and
  input definition
- no deterministic reproducibility path for any candidate source

## Verification

Verification after Phase 32 Step 4:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified
existing docs

git status --short
 M docs/design/phase30_research_artifact_candidate_backlog.md
 M docs/design/phase31_research_track_next_action_plan.md
 M docs/design/phase32_dataset_specific_validation_candidate_selection.md
 M docs/design/phase32_p30_bl_002_source_package.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_p30_bl_002_primary_source_verification_gate.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated
