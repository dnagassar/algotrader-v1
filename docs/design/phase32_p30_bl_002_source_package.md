# Phase 32 Step 3 — P30-BL-002 Source Package Collection and Normalization

## Purpose

This document normalizes scout-supplied candidate source material for
`P30-BL-002`, "Threshold sanity check for `indicator_value`", before any
formal review.

This is source collection, normalization, deduplication, triage, and gap
identification only. It is not formal source review, validation, approval,
promotion, production readiness, implementation readiness, or threshold
justification. It does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, bind a signal definition, approve a threshold, or
authorize evaluator implementation.

All Claude, Perplexity, and Gemini/browser scout-report material is treated as
candidate-only discovery material. Scout claims, source rankings, arXiv
preprints, vendor papers, blogs, and AI-generated summaries are not validation
evidence. Later review must verify primary sources directly.

## Prior State

`P30-BL-001`, "Simple scalar threshold indicator definition", has been
dispositioned as mechanics-only. It remains non-validated, unapproved, not
production-ready, not implementation-ready, and not threshold-justified. It
does not provide dataset-specific validation, production threshold rationale,
predictive evidence, profitability evidence, robustness evidence, a validated
research artifact, a validated signal definition, or evaluator implementation
readiness.

`P30-BL-002` is only a sourcing target for dataset-specific threshold or
validation evidence. Phase 32 Step 1 selected dataset-specific threshold or
validation evidence sourcing as the next research route. Phase 32 Step 2
defined the source-package sourcing plan and minimum review-readiness
criteria. Step 2 did not collect, review, approve, validate, or implement
anything.

An earlier Step 3 pass recorded an incomplete source package because the scout
reports were not available in that prompt. This revision replaces that
incomplete collection result using the supplied Claude, Perplexity, and
Gemini/browser `.docx` scout reports:

- `C:\Users\danie\Desktop\old_systems\claude report.docx`
- `C:\Users\danie\Downloads\Trading Signal Validation Source Search.docx`
- `C:\Users\danie\Downloads\We are supporting a Python algo_trader project tha.docx`

## Source Package Status

Package status:

- collected: yes, from the three supplied scout reports
- partial: yes, because primary sources have not been independently verified
- incomplete: yes, for validation purposes
- insufficient to validate or approve a threshold: yes
- ready for formal review intake only: maybe, for selected candidate sources
  after primary-source provenance, versions, links, and reproducibility claims
  are checked directly

The package contains 23 normalized candidate entries. Several candidates are
useful only as methodology references, negative controls, point-in-time
infrastructure references, or out-of-scope material. No entry is validated,
approved, reviewed, promoted, production-ready, or implementation-ready.

## Normalization Method

Inputs checked in this phase:

- the current Phase 32 Step 3 prompt and file references
- the three supplied scout-report `.docx` files
- existing allowed planning documents for `P30-BL-002`, Phase 32, and the
  research backlog

Candidate sections and candidate tables were extracted from the scout reports.
Sources were deduplicated by title, link, and described source identity. The
main overlap was "Interpretable Hypothesis-Driven Trading", which appeared in
both Claude and Perplexity. The Gemini/browser report also included a long
unexpanded link list; those bibliography-only links were not promoted into
normalized entries unless the report provided candidate-level metadata.

Each source below is classified as candidate-only and not validated.
Preliminary routing categories are:

- Category A: strong candidate for formal review intake
- Category B: useful methodology or validation-design reference only
- Category C: negative-control or falsification benchmark
- Category D: point-in-time or no-lookahead data infrastructure reference
- Category E: interesting but too complex or out of current scope
- Category F: reject or replacement-needed material

These categories are collection triage only. They do not approve evidence,
thresholds, artifacts, signal definitions, or implementation.

## Normalized Source Entries

### P30-BL-002-S01

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S01` |
| original scout id(s) | Claude `P30-BL-002-C01` |
| title/reference | "Revisiting the Profitability of Market Timing with Moving Averages" |
| link or citation text | <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2743119>; published version reported at <https://onlinelibrary.wiley.com/doi/10.1111/irfi.12132> |
| author/source | Valeriy Zakamulin; SSRN working paper and International Review of Finance |
| date/version | SSRN August 25, 2016; journal version 2018, per scout report |
| source type | Peer-reviewed academic replication/critique study with reported R code and data |
| scout-report origin | Claude |
| dataset scope | Long historical equity index series; scout says it replicates Glabadanidis on the same dataset |
| asset class/universe | US broad equity index / S&P composite-style series |
| timeframe | Long-horizon monthly and daily series across multiple decades; exact range requires source verification |
| point-in-time assumptions | Scout says corrected signal timing removes a lookahead convention; exact timestamp convention must be checked |
| data quality assumptions | Corporate actions, index composition, and total-return handling are not normalized from the scout report |
| explicit input definition | Price versus moving average and moving-average crossover rules with explicit window lengths |
| threshold or parameter rationale | Threshold is price or moving-average crossover; parameter windows are tested as part of the critique |
| validation design | Replication with corrected timing, benchmark comparison, and statistical tests |
| no-lookahead controls | Central candidate value is the documented correction of lookahead-biased timing |
| reproducibility notes | Scout reports R code and data; must verify availability, license, exact version, and determinism |
| robustness or out-of-sample evidence | Subperiod and moving-average window checks reported by scout; result described as null once lookahead is removed |
| limitations | Narrow US index focus; stylized transaction costs; null/negative result; not production threshold evidence |
| non-claims | Does not validate a profitable edge, production threshold, or implementation readiness |
| future binding notes | Could be reviewed as a negative-control or no-lookahead benchmark for threshold timing mechanics |
| unresolved gaps | Verify source, code/data access, exact dataset, exact timing correction, cost assumptions, and reproducibility |
| preliminary routing category | Category C |
| preliminary routing note | High-priority negative-control intake candidate, not positive validation evidence |

### P30-BL-002-S02

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S02` |
| original scout id(s) | Claude `P30-BL-002-C02` |
| title/reference | "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns" |
| link or citation text | <https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1992.tb04681.x>; PDF reported at <https://finance.martinsewell.com/stylized-facts/distribution/BrockLakonishokLeBaron1992.pdf> |
| author/source | William Brock, Josef Lakonishok, Blake LeBaron; Journal of Finance |
| date/version | 1992 |
| source type | Peer-reviewed empirical finance paper |
| scout-report origin | Claude |
| dataset scope | Dow Jones Industrial Average daily series, 1897-1986, per scout report |
| asset class/universe | Single US equity index |
| timeframe | Approximately 90 years of daily data |
| point-in-time assumptions | Signals are described as prior-bar rules; exact execution timing and index data handling need review |
| data quality assumptions | No modern survivorship, corporate-action, or vendor snapshot notes in scout material |
| explicit input definition | Moving-average crossover and trading-range-break rules with parameter grids |
| threshold or parameter rationale | Explicit moving-average and band thresholds are enumerated |
| validation design | Conditional returns compared with random walk, AR(1), GARCH-M, and EGARCH bootstrap nulls |
| no-lookahead controls | Prior-bar signal use is claimed by scout; formal review must verify |
| reproducibility notes | Dataset and rule definitions are reported as fully specified and widely reimplemented |
| robustness or out-of-sample evidence | Bootstrap null comparison only; no modern walk-forward or holdout design |
| limitations | In-sample by modern standards; later data-snooping critiques; dated transaction-cost treatment |
| non-claims | Does not establish production threshold validity or implementation readiness |
| future binding notes | Could support historical rule-specification review or a baseline replication target |
| unresolved gaps | No true out-of-sample window; no direct P30 threshold rationale; primary-source details need verification |
| preliminary routing category | Category B |
| preliminary routing note | Useful specification baseline, but weak as validation evidence |

### P30-BL-002-S03

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S03` |
| original scout id(s) | Claude `P30-BL-002-C03` |
| title/reference | "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap" |
| link or citation text | <https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00163>; PDF reported at <https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Sullivan_Timmermann_White.pdf> |
| author/source | Ryan Sullivan, Allan Timmermann, Halbert White; Journal of Finance |
| date/version | 1999 |
| source type | Peer-reviewed empirical paper applying White's Reality Check |
| scout-report origin | Claude |
| dataset scope | Daily DJIA data, 1897-1996, with explicit post-1986 out-of-sample extension, per scout report |
| asset class/universe | DJIA; related work reportedly extends to S&P 500 and S&P 500 futures |
| timeframe | Daily data over about 100 years, with about 10 years out-of-sample |
| point-in-time assumptions | Prior-bar rules and post-selection out-of-sample period are reported; exact mechanics need review |
| data quality assumptions | Data vendor, index construction, costs, and corporate-action handling need verification |
| explicit input definition | 7,846 filter, moving-average, support/resistance, channel, and OBV rules with parameters |
| threshold or parameter rationale | Full threshold and parameter universe is central to the test |
| validation design | White's Reality Check bootstrap with in-sample selection and separate OOS evaluation |
| no-lookahead controls | Rules use prior-bar signals and OOS period is strictly post-selection, per scout report |
| reproducibility notes | Rule definitions are reported as tabulated; original software details may be proprietary |
| robustness or out-of-sample evidence | Explicit OOS test; scout says best in-sample rule does not survive OOS |
| limitations | Single-index focus, daily frequency, proprietary or nontrivial original implementation |
| non-claims | Negative-control evidence only; does not support a production threshold |
| future binding notes | Strong candidate for negative-control/falsification review before any threshold promotion |
| unresolved gaps | Verify source, rule tables, exact sample dates, OOS design, costs, and reproducibility path |
| preliminary routing category | Category C |
| preliminary routing note | Strong formal review intake candidate as a negative-control benchmark |

### P30-BL-002-S04

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S04` |
| original scout id(s) | Claude `P30-BL-002-C10` |
| title/reference | "Evidence-Based Technical Analysis: Applying the Scientific Method and Statistical Inference to Trading Signals" |
| link or citation text | <https://onlinelibrary.wiley.com/doi/book/10.1002/9781118268315> |
| author/source | David R. Aronson; John Wiley & Sons |
| date/version | 2006 |
| source type | Methodology textbook with empirical case study |
| scout-report origin | Claude |
| dataset scope | S&P 500 daily series case study, per scout report |
| asset class/universe | US equity index |
| timeframe | Multi-decade daily data, reportedly 1980s-2000s |
| point-in-time assumptions | Signal timing is reportedly described; source must be checked directly |
| data quality assumptions | Book-format source; dataset sourcing and correction details require review |
| explicit input definition | Thousands of moving-average, channel, momentum, and oscillator rule variants |
| threshold or parameter rationale | Full enumeration of threshold and parameter grids |
| validation design | White's Reality Check and Monte Carlo permutation methods |
| no-lookahead controls | Scout reports detrended trade returns and signal timing handling |
| reproducibility notes | Pseudocode is reported; no code-shipping package in scout material |
| robustness or out-of-sample evidence | Multiple-testing-corrected null result reported; no source package verified here |
| limitations | Book chapter, dated methods, data/rule tables may need rederivation |
| non-claims | Does not validate this project's threshold or authorize implementation |
| future binding notes | Could support methodology/negative-control review for multiple-testing correction |
| unresolved gaps | Verify exact rule set, data, code availability, and modern relevance |
| preliminary routing category | Category C |
| preliminary routing note | Useful falsification/multiple-testing reference, not a direct threshold source |

### P30-BL-002-S05

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S05` |
| original scout id(s) | Gemini/browser `C1-TSMOM-2012` |
| title/reference | "Time Series Momentum" |
| link or citation text | <https://elmwealth.com/wp-content/uploads/2017/06/timeseriesmomentum.pdf>; related journal link reported by scout |
| author/source | Tobias J. Moskowitz, Yao Hua Ooi, Lasse H. Pedersen; Journal of Financial Economics |
| date/version | Original paper 2012; redistributed PDF circa 2017 per scout report |
| source type | Peer-reviewed academic paper |
| scout-report origin | Gemini/browser |
| dataset scope | 58 liquid futures/forwards and related tests across major global asset classes, per scout report |
| asset class/universe | Futures across equities, bonds, commodities, and currencies; additional stock/index tests |
| timeframe | Monthly formation and holding periods over several decades, reportedly through 2009 |
| point-in-time assumptions | Uses lagged returns; explicit point-in-time vendor snapshot controls are not described in scout material |
| data quality assumptions | Futures roll methodology, transaction costs, and data-source specifics need review |
| explicit input definition | Past excess returns over 1- to 12-month lookbacks and sign of cumulative return |
| threshold or parameter rationale | Deterministic zero threshold on lagged return sign; lookback windows varied systematically |
| validation design | Historical multi-asset backtests, factor regressions, and cross-asset comparisons |
| no-lookahead controls | Lagged return construction should be time ordered; formal review must verify exact rebalance timing |
| reproducibility notes | Rules are specified but public code was not identified by scout report |
| robustness or out-of-sample evidence | Cross-asset, cross-lookback, and subperiod checks are reported |
| limitations | Not a step-by-step notebook; simplified frictions; no direct simple `indicator_value` binding |
| non-claims | Does not validate a production threshold or implementation for this project |
| future binding notes | Could be reviewed as a dataset-specific simple threshold-rule candidate |
| unresolved gaps | Verify dataset, roll/cost assumptions, code availability, and exact timestamp semantics |
| preliminary routing category | Category A |
| preliminary routing note | Strong direct candidate for intake if primary source details verify cleanly |

### P30-BL-002-S06

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S06` |
| original scout id(s) | Perplexity `C-001` |
| title/reference | "A novel approach to trading strategy parameter optimization using double out-of-sample data and walk-forward techniques" |
| link or citation text | <https://arxiv.org/html/2602.10785v1>; <https://github.com/tmr-crypto/wf_optim_crypto_analysis> |
| author/source | Tomasz Mroziewicz and Robert Slepaczuk; University of Warsaw / arXiv, per scout report |
| date/version | February 11, 2026, per scout report |
| source type | arXiv preprint with reported open-source code repository |
| scout-report origin | Perplexity |
| dataset scope | Intraday crypto data at 1- to 60-minute frequencies; BTC training plus ETH/BNB OOS validation, per scout report |
| asset class/universe | Cryptocurrency microstructure; BTC, ETH, BNB |
| timeframe | 19-month training period and 21-month isolated OOS period |
| point-in-time assumptions | Scout reports DVC pipeline physically segregates chronological data |
| data quality assumptions | Exchange/source, missing candles, liquidity, fees, and survivorship assumptions require verification |
| explicit input definition | EMA crossover configurations and walk-forward window parameters |
| threshold or parameter rationale | Tests 81 training/testing duration combinations; threshold focus is mostly parameter-window robustness |
| validation design | Double out-of-sample walk-forward optimization; top parameters tested once on unseen data |
| no-lookahead controls | DVC DAG and bounded data generation are claimed; must verify code and pipeline |
| reproducibility notes | Scout reports conda environment, DVC commands, and modular scripts |
| robustness or out-of-sample evidence | OOS decay and transaction-cost failure point are reported by scout |
| limitations | arXiv preprint; crypto-only; EMA logic may be mechanics-heavy; R tooling in analysis layer; not proof of edge |
| non-claims | Candidate infrastructure only; no production threshold or profitability claim accepted |
| future binding notes | Could support validation-architecture review if repository is verified and reproducible offline |
| unresolved gaps | Verify arXiv version, code license, data access, deterministic rerun, cost handling, and offline-safety |
| preliminary routing category | Category D |
| preliminary routing note | Strong infrastructure candidate, but preprint status blocks use as validation evidence |

### P30-BL-002-S07

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S07` |
| original scout id(s) | Claude `P30-BL-002-C07`; Perplexity `C-002` |
| title/reference | "Interpretable Hypothesis-Driven Trading: A Rigorous Walk-Forward Validation Framework for Market Microstructure Signals" |
| link or citation text | <https://arxiv.org/abs/2512.12924>; <https://arxiv.org/html/2512.12924v1>; ResearchGate link also reported by Perplexity |
| author/source | Gagan Deep, Akash Deep, William Lamptey; Texas Tech University / arXiv, per Perplexity |
| date/version | v1, December 2025, per scout reports |
| source type | arXiv preprint with claimed mathematical specifications and open-source implementation |
| scout-report origin | Claude and Perplexity |
| dataset scope | US equity microstructure and daily data; 100 US equities in Perplexity, 10-year span in both reports |
| asset class/universe | US equities; SPY benchmark mentioned by Claude |
| timeframe | 2015-2024 with 34 independent OOS windows, per Perplexity |
| point-in-time assumptions | Strict information-set discipline is claimed; exact feature availability must be verified |
| data quality assumptions | Transaction costs/slippage and position constraints are reported; raw data provenance is not verified |
| explicit input definition | Five hypothesis-driven microstructure signal tuples with interpretable thresholds |
| threshold or parameter rationale | Thresholds mapped to confidence, target-return, stop-loss, imbalance, and volume-multiplier constraints |
| validation design | Rolling walk-forward validation across 34 OOS periods |
| no-lookahead controls | Strict retrospective feature, confidence, and allocation constraints are claimed |
| reproducibility notes | Mathematical tuples and open-source implementation are claimed, not verified |
| robustness or out-of-sample evidence | Reports non-significant aggregate p-value and modest effects, which is useful as honest OOS decay context |
| limitations | arXiv preprint; RL selection layer and possible natural-language layer are too complex for hot path; code claim needs verification |
| non-claims | Not validation evidence; does not authorize ML, RL, LLM, or implementation behavior |
| future binding notes | Could be reviewed as a validation-design template, with ML/RL parts quarantined |
| unresolved gaps | Verify source, code, data, exact rules, determinism, and absence of LLM/hot-path dependency |
| preliminary routing category | Category E |
| preliminary routing note | Methodologically interesting, but preprint/RL complexity prevents direct simple-threshold intake |

### P30-BL-002-S08

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S08` |
| original scout id(s) | Gemini/browser `C3-FCT-PIT-DB-POINTINTIME` |
| title/reference | "Accurately Backtesting Financial Models Through Point-in-Time Consensus Estimates" |
| link or citation text | <https://www.insight.factset.com/hubfs/Resources%20Section/White%20Papers/ID11996_point_in_time.pdf> |
| author/source | FactSet Research Systems Inc. |
| date/version | Date not normalized by scout report; Phase 32 Step 4 did not verify an explicit publication date in the primary PDF |
| source type | Vendor white paper on point-in-time data and backtesting methodology |
| scout-report origin | Gemini/browser |
| dataset scope | FactSet point-in-time estimates and fundamentals snapshots for global equities |
| asset class/universe | Global listed equities covered by FactSet |
| timeframe | Daily snapshots; exact sample windows depend on use case |
| point-in-time assumptions | Daily frozen snapshots at local midnight are described by scout report |
| data quality assumptions | Vendor-specific restatement and snapshot handling; proprietary database access required |
| explicit input definition | Consensus estimates and fundamentals used in factor or screening rules |
| threshold or parameter rationale | Discusses top/bottom quantiles, estimate-revision thresholds, and valuation screens in PIT context |
| validation design | Backtests using only data available at each date; infrastructure focus rather than one rule |
| no-lookahead controls | Core topic is avoiding lookahead through point-in-time snapshots |
| reproducibility notes | Reproducible only with FactSet access and exact query logic; no open code |
| robustness or out-of-sample evidence | Data integrity reference, not strategy robustness evidence |
| limitations | Vendor paper, proprietary data, no directly reviewable simple threshold artifact |
| non-claims | Does not validate a signal, edge, threshold, or production use |
| future binding notes | Strong methodology anchor for `as_of` and snapshot semantics |
| unresolved gaps | Verify version/date, exact examples, license/access constraints, and applicability to local data |
| preliminary routing category | Category D |
| preliminary routing note | Strong point-in-time infrastructure candidate, not direct threshold validation |

### P30-BL-002-S09

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S09` |
| original scout id(s) | Gemini/browser `C4-SMALLCAP-SSRN-PIT` |
| title/reference | "Small-Cap Stock Trading Strategies for Retail" |
| link or citation text | <https://papers.ssrn.com/sol3/Delivery.cfm/5921742.pdf?abstractid=5921742&mirid=1> |
| author/source | SSRN authors not normalized by scout report |
| date/version | Mid-2020s per scout report; exact date needs verification |
| source type | SSRN strategy white paper / empirical study |
| scout-report origin | Gemini/browser |
| dataset scope | Small-cap equities with universe, delisting, and point-in-time checks, per scout report |
| asset class/universe | Publicly traded small-cap stocks; region likely US but unverified |
| timeframe | Multi-year historical sample; exact dates unavailable in scout report |
| point-in-time assumptions | Scout reports checklist requiring delisting inclusion and PIT verification |
| data quality assumptions | Delistings, universe definition, and data handling are highlighted but not verified |
| explicit input definition | Factor-like valuation, momentum, liquidity, and screening inputs; exact formulas not normalized |
| threshold or parameter rationale | Market-cap, liquidity, price, volume, and rank cutoffs appear threshold-shaped |
| validation design | Portfolio simulation/backtest implied by scout report; specifics need source review |
| no-lookahead controls | PIT and delisting checklist are promising, but must be verified directly |
| reproducibility notes | No public code or raw data identified by scout report |
| robustness or out-of-sample evidence | Not normalized; scout says details require full reading |
| limitations | Author/date ambiguity, possible proprietary data, retail-strategy framing, and possible return-seeking claims |
| non-claims | Candidate methodology only; no profitability or production claim accepted |
| future binding notes | Could support data-quality checklist review if source details verify |
| unresolved gaps | Verify authors, date, exact universe, data access, rules, costs, OOS design, and non-claims |
| preliminary routing category | Category D |
| preliminary routing note | Useful data-quality/PIT candidate, but provenance and reproducibility are weak |

### P30-BL-002-S10

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S10` |
| original scout id(s) | Claude `P30-BL-002-C04` |
| title/reference | "Backtesting" |
| link or citation text | <https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF> |
| author/source | Campbell R. Harvey and Yan Liu; Journal of Portfolio Management |
| date/version | Fall 2015 |
| source type | Peer-reviewed methodology paper |
| scout-report origin | Claude |
| dataset scope | Methodology paper; examples tied to factor literature rather than one source package |
| asset class/universe | Cross-sectional equity factors in examples; generally asset-agnostic |
| timeframe | Not a single dataset-specific timeframe |
| point-in-time assumptions | Not a primary focus; post-hoc selection bias rather than feature timing |
| data quality assumptions | Not source-specific for a trading dataset |
| explicit input definition | Uses Sharpe ratio, t-statistic, and performance metrics rather than indicator values |
| threshold or parameter rationale | Provides statistical hurdles such as haircut Sharpe/profit hurdle |
| validation design | Multiple-testing adjustment with Bonferroni, Holm, and BHY-style controls |
| no-lookahead controls | Complementary to no-lookahead; not a PIT data source |
| reproducibility notes | Formulas and reported open-source R implementations require verification |
| robustness or out-of-sample evidence | Statistical methodology rather than empirical OOS for a simple threshold |
| limitations | Not dataset-specific; number-of-trials assumption is difficult |
| non-claims | Does not validate this project or a production threshold |
| future binding notes | Useful for review methodology if performance claims later appear |
| unresolved gaps | Need direct formula/code verification and project-specific trial-count policy |
| preliminary routing category | Category B |
| preliminary routing note | Useful validation-design reference only |

### P30-BL-002-S11

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S11` |
| original scout id(s) | Claude `P30-BL-002-C05` |
| title/reference | "The Probability of Backtest Overfitting" |
| link or citation text | <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253>; R package reported at <https://cran.r-project.org/web/packages/pbo/vignettes/pbo.html> |
| author/source | David H. Bailey, Jonathan M. Borwein, Marcos Lopez de Prado, Qiji Jim Zhu |
| date/version | SSRN September 2013; revised July 2015, per scout report |
| source type | Quantitative methodology paper with reported open-source implementation |
| scout-report origin | Claude |
| dataset scope | Methodology demonstrated on simulated/example backtest matrices |
| asset class/universe | Asset-agnostic |
| timeframe | Not tied to one market timeframe |
| point-in-time assumptions | Time-block partitioning matters; not a direct PIT data reference |
| data quality assumptions | Requires a complete tested-configuration matrix; no specific market data assumptions |
| explicit input definition | Matrix of candidate configurations by periods of returns |
| threshold or parameter rationale | PBO quantifies whether chosen threshold/parameter settings are likely overfit |
| validation design | Combinatorially Symmetric Cross-Validation with PBO diagnostics |
| no-lookahead controls | Time-block combinations preserve temporal structure only if data are prepared correctly |
| reproducibility notes | R `pbo` package reported; implementation must be verified |
| robustness or out-of-sample evidence | Produces OOS overfitting diagnostics but not a market-specific signal result |
| limitations | Not dataset-specific; assumptions about period blocks; needs all tested configurations |
| non-claims | Does not validate a threshold or profitable signal |
| future binding notes | Useful methodology anchor for threshold-parameter overfitting review |
| unresolved gaps | Verify package, formulas, assumptions, and project-appropriate input matrix definition |
| preliminary routing category | Category B |
| preliminary routing note | Methodology-only, but highly relevant for later validation design |

### P30-BL-002-S12

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S12` |
| original scout id(s) | Claude `P30-BL-002-C06` |
| title/reference | "Backtest Overfitting in the Machine Learning Era: A Comparison of Out-of-Sample Testing Methods in a Synthetic Controlled Environment" |
| link or citation text | <https://www.sciencedirect.com/science/article/abs/pii/S0950705124011110> |
| author/source | Arian et al.; Knowledge-Based Systems / Elsevier, per scout report |
| date/version | 2024 |
| source type | Peer-reviewed empirical methodology paper |
| scout-report origin | Claude |
| dataset scope | Synthetic financial time series with controlled regimes |
| asset class/universe | Synthetic equity-like return processes |
| timeframe | Configurable simulation windows |
| point-in-time assumptions | Purging and embargoing are compared; not a real PIT dataset |
| data quality assumptions | Simulation assumptions replace real data-quality controls |
| explicit input definition | Cross-validation methods and model families, not one threshold indicator |
| threshold or parameter rationale | Compares how validation method affects threshold/hyperparameter selection |
| validation design | K-fold, purged K-fold, walk-forward, and CPCV comparison |
| no-lookahead controls | Purging and embargoing explicitly implemented in the comparison |
| reproducibility notes | Synthetic setup described; code availability not normalized from scout report |
| robustness or out-of-sample evidence | PBO and deflated Sharpe diagnostics across methods are reported |
| limitations | Synthetic only; not dataset-specific evidence for real assets |
| non-claims | Does not validate a market threshold or implementation |
| future binding notes | Useful for validation-method selection questions |
| unresolved gaps | Verify source, simulation code, exact assumptions, and relevance to simple thresholds |
| preliminary routing category | Category B |
| preliminary routing note | Methodology-only reference; not a direct candidate artifact |

### P30-BL-002-S13

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S13` |
| original scout id(s) | Perplexity `C-003` |
| title/reference | "Does Meta Labeling Add to Signal Efficacy? (Triple Barrier Method)" |
| link or citation text | <https://hudsonthames.org/does-meta-labeling-add-to-signal-efficacy-triple-barrier-method/> |
| author/source | Ashutosh Singh and Jacques Joubert; Hudson & Thames |
| date/version | Undated in scout report; references Lopez de Prado 2018 |
| source type | Technical research notebook / benchmark implementation study |
| scout-report origin | Perplexity |
| dataset scope | E-mini S&P 500 tick data transformed into dollar, volume, and tick bars |
| asset class/universe | S&P 500 E-mini futures |
| timeframe | Continuous tick-data slice; exact dates not normalized |
| point-in-time assumptions | Event timestamps and trailing 50-day volatility are reported; verify exact lagging |
| data quality assumptions | Tick cleaning, rollover, contract selection, and missing data are unresolved |
| explicit input definition | CUSUM filters, 50-day daily volatility, triple-barrier horizontal bounds |
| threshold or parameter rationale | Dynamic barriers use point-in-time volatility multiplied by scalar parameters |
| validation design | Meta-labeling with primary signal and secondary random forest trade/no-trade adviser |
| no-lookahead controls | Lagged features and chronological sequencing are claimed |
| reproducibility notes | MlFinLab implementation is reported; license and version require verification |
| robustness or out-of-sample evidence | Bar-type comparisons and normality diagnostics are reported, not simple threshold OOS proof |
| limitations | Tick-level complexity, event sampling, ML secondary model, and calibration sensitivity |
| non-claims | Does not authorize ML, production thresholds, or actionability |
| future binding notes | Could inform volatility-scaled threshold review, with ML parts quarantined |
| unresolved gaps | Verify code, data access, license, exact dates, and deterministic offline reproducibility |
| preliminary routing category | Category E |
| preliminary routing note | Powerful but likely too complex for the simple advisory evaluator scope |

### P30-BL-002-S14

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S14` |
| original scout id(s) | Claude `P30-BL-002-C08`; Perplexity works-cited-only mention |
| title/reference | "The GT-Score: A Robust Objective Function for Reducing Overfitting in Data-Driven Trading Strategies" |
| link or citation text | <https://arxiv.org/abs/2602.00080>; <https://arxiv.org/html/2602.00080>; code repo reported at <https://github.com/shep-analytics/gt_score> |
| author/source | arXiv preprint; authors not normalized by scout report |
| date/version | 2026, per scout report |
| source type | arXiv preprint with supplementary code claim |
| scout-report origin | Claude |
| dataset scope | Top 50 S&P 500 companies by market cap, daily OHLCV via yFinance, Jan 2010-Dec 2024 |
| asset class/universe | US large-cap equities |
| timeframe | 2010-2024 daily |
| point-in-time assumptions | Walk-forward splits are reported; yFinance is not point-in-time |
| data quality assumptions | yFinance revisions, survivorship, and current-top-50 universe are major unresolved issues |
| explicit input definition | RSI thresholds, MACD parameters, and another named strategy |
| threshold or parameter rationale | Optimized RSI thresholds and MACD parameters are central |
| validation design | Walk-forward validation with nine sequential splits and Monte Carlo seeds |
| no-lookahead controls | Walk-forward structure claimed; source/code must verify timing |
| reproducibility notes | GitHub and processed results claimed; not verified |
| robustness or out-of-sample evidence | OOS paired tests and PBO/DSR concepts reported |
| limitations | arXiv-only, yFinance/PIT weakness, survivorship risk, small effects |
| non-claims | Not validation evidence and not production threshold support |
| future binding notes | Could be intake candidate for reproducible threshold optimization after PIT defects are addressed |
| unresolved gaps | Verify authors, code, data, universe construction, PIT controls, and offline determinism |
| preliminary routing category | Category E |
| preliminary routing note | Close shape to P30-BL-002, but preprint/data-quality gaps are material |

### P30-BL-002-S15

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S15` |
| original scout id(s) | Perplexity `C-006` |
| title/reference | "A Volume-Price-Adjusted MACD Trading Strategy with Sensitivity Calibration for U.S. Equity Indices" |
| link or citation text | <https://arxiv.org/html/2604.26063v1> |
| author/source | Luyun Lin, Lixing Lin, Zhen Zhang; arXiv, per scout report |
| date/version | April 2026 |
| source type | Academic preprint |
| scout-report origin | Perplexity |
| dataset scope | Daily equity index vectors with close, volume, and intraday volatility fields |
| asset class/universe | S&P 500, Nasdaq-100, and DJIA, per scout report |
| timeframe | In-sample 2018-2022; OOS 2023-February 2026 |
| point-in-time assumptions | Single chronological split; no point-in-time vendor controls normalized |
| data quality assumptions | Index data source, corporate actions, volume construction, and missing data unresolved |
| explicit input definition | Adjusted price metric combining price, volume, intraday structure, and relative volatility |
| threshold or parameter rationale | Sensitivity parameter replaces static MACD crossover threshold |
| validation design | Fixed block calibration/test split |
| no-lookahead controls | Temporal boundary at 2022/2023 is claimed |
| reproducibility notes | Mathematical formulas reported; code not normalized |
| robustness or out-of-sample evidence | Scout reports selectivity/sample-size tradeoff; limited by one OOS block |
| limitations | Preprint; fixed-block overfit risk; not enough PIT or walk-forward detail |
| non-claims | Does not approve MACD, thresholds, or production implementation |
| future binding notes | Could be reviewed as a simple-ish threshold-parameter candidate if source verifies |
| unresolved gaps | Verify source, code/data, exact formula, costs, parameter selection, and OOS significance |
| preliminary routing category | Category E |
| preliminary routing note | Interesting but weakly supported and preprint-only |

### P30-BL-002-S16

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S16` |
| original scout id(s) | Gemini/browser `C2-BACKTEST-SSRN-2019` |
| title/reference | "Backtesting" / parameterized moving-average threshold rules |
| link or citation text | <https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID3374195_code895233.pdf?abstractid=3374195> |
| author/source | Scout report says author visible on PDF front page but did not normalize it reliably |
| date/version | Late 2010s per scout report; exact date unknown |
| source type | Methodological white paper/tutorial on backtesting |
| scout-report origin | Gemini/browser |
| dataset scope | Equity index or large-cap examples; exact dataset not normalized |
| asset class/universe | Primarily equity index or large-cap equity examples, per scout report |
| timeframe | Daily price data over multi-year windows, exact dates unknown |
| point-in-time assumptions | Moving averages are lagged; no named PIT vendor or snapshot control |
| data quality assumptions | Data source, survivorship, costs, and corporate actions unknown |
| explicit input definition | Fast/slow moving-average windows and crossovers |
| threshold or parameter rationale | Parameter grid for fast/slow windows, with overfitting discussion |
| validation design | Grid search and train/evaluation discussion; exact design unclear |
| no-lookahead controls | General time-ordering discussion only |
| reproducibility notes | Formula and parameter grids appear reproducible, but source metadata is weak |
| robustness or out-of-sample evidence | Parameter-sensitivity examples rather than strong OOS evidence |
| limitations | Vague author/date, methodology-heavy, no strict PIT details |
| non-claims | Not a validated source for any production threshold |
| future binding notes | Could be used only after provenance is repaired and source is verified |
| unresolved gaps | Author, date, source identity, dataset, source type, and code/data access are too vague |
| preliminary routing category | Category F |
| preliminary routing note | Replacement or provenance repair needed before review intake |

### P30-BL-002-S17

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S17` |
| original scout id(s) | Gemini/browser `C5-BTB-MINTRADES-2025` |
| title/reference | "Minimum Trades for a Valid Backtest? Calculator + Research" |
| link or citation text | <https://www.backtestbase.com/education/how-many-trades-for-backtest> |
| author/source | BacktestBase research/education team |
| date/version | 2025-01-29, per scout report |
| source type | Methodology article / educational research note |
| scout-report origin | Gemini/browser |
| dataset scope | Not tied to a named dataset |
| asset class/universe | General; not asset-specific |
| timeframe | General backtest-length guidance such as multi-year regimes |
| point-in-time assumptions | No source-specific PIT control |
| data quality assumptions | Not source-specific |
| explicit input definition | Trade count, Sharpe, drawdown, expectancy; no indicator definition |
| threshold or parameter rationale | Heuristic sample-size thresholds such as 30, 100, and 200-500 trades |
| validation design | General overfitting/sample-size guidance |
| no-lookahead controls | High-level only |
| reproducibility notes | No code/data package; heuristics can be codified but not validated here |
| robustness or out-of-sample evidence | General OOS caution; not dataset-specific evidence |
| limitations | Blog/educational source, heuristic thresholds, no dataset |
| non-claims | Does not validate any trading threshold |
| future binding notes | May inform checklist language only, not artifact binding |
| unresolved gaps | Needs stronger primary methodology source or replacement |
| preliminary routing category | Category F |
| preliminary routing note | Reject as validation evidence; optional checklist note only |

### P30-BL-002-S18

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S18` |
| original scout id(s) | Perplexity `C-007` |
| title/reference | "Revisiting Equity Strategies with Financial Machine Learning" |
| link or citation text | <https://ethz.ch/content/dam/ethz/special-interest/mtec/chair-of-entrepreneurial-risks-dam/documents/dissertation/master%20thesis/Thesis-Schneider_final_.pdf> |
| author/source | Luca Schneider; ETH Zurich Master Thesis |
| date/version | September 2019 |
| source type | Institutional academic thesis / financial machine learning benchmark |
| scout-report origin | Perplexity |
| dataset scope | Russell 1000 feature matrices with many quantitative and qualitative features |
| asset class/universe | Russell 1000 equities |
| timeframe | Long-term historical data constrained by feature availability; exact windows need review |
| point-in-time assumptions | Purging and embargoing are reported as central |
| data quality assumptions | Feature availability and preprocessing rules are key but not fully normalized |
| explicit input definition | SUE, residual momentum, long lookbacks, and high-dimensional features |
| threshold or parameter rationale | Feature pruning thresholds such as Spearman correlation > 0.88 and Cramer's V threshold |
| validation design | Combinatorial Purged Cross-Validation |
| no-lookahead controls | Purging and embargoing address overlapping-return leakage |
| reproducibility notes | Statistical coefficients and algorithms reported; code/data availability unresolved |
| robustness or out-of-sample evidence | Robustness under transaction costs is claimed by scout |
| limitations | ML-heavy, dense feature dependencies, not a simple threshold evaluator |
| non-claims | Does not authorize ML or production threshold behavior |
| future binding notes | Useful methodology reference for CPCV/preprocessing review |
| unresolved gaps | Verify thesis, data access, code, exact features, and complexity boundary |
| preliminary routing category | Category B |
| preliminary routing note | Good methodology/PIT validation design reference, not direct signal evidence |

### P30-BL-002-S19

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S19` |
| original scout id(s) | Perplexity `C-004` |
| title/reference | "Taming the Black Swan: A Momentum-Gated Hierarchical Optimisation Framework for Asymmetric Alpha Generation" |
| link or citation text | <https://arxiv.org/html/2604.09060>; <https://arxiv.org/pdf/2604.09060> |
| author/source | Arya Chakraborty and Randhir Singh; arXiv, per scout report |
| date/version | April 2026 |
| source type | Academic preprint with optimization framework |
| scout-report origin | Perplexity |
| dataset scope | Pre-adjusted US equity log-return data with liquidity and financial viability filters |
| asset class/universe | S&P large/mid/small-cap suites and Nasdaq-100, per scout report |
| timeframe | 20-year walk-forward analysis with crisis regimes |
| point-in-time assumptions | Skip-month constraint reported; exact universe timing needs verification |
| data quality assumptions | Survivorship, liquidity, positive-income, and adjustment assumptions require review |
| explicit input definition | Volatility-adjusted momentum and minimax correlation filter |
| threshold or parameter rationale | Portfolio-level correlation threshold / minimax dependency constraint |
| validation design | Nested annual universe selection and monthly optimization loops |
| no-lookahead controls | Skip-month constraint is reported |
| reproducibility notes | Mathematical formulas reported; code availability only indicated by scout |
| robustness or out-of-sample evidence | Stress-regime capital preservation claimed; must not be accepted without review |
| limitations | Nonlinear optimizer, portfolio-level focus, high complexity, preprint status |
| non-claims | Not a simple signal threshold validation and not production-ready |
| future binding notes | Could be reviewed later for portfolio validation, outside current scope |
| unresolved gaps | Verify source, code, data, solver determinism, exact formulas, and review relevance |
| preliminary routing category | Category E |
| preliminary routing note | Too complex and portfolio-focused for current P30-BL-002 scope |

### P30-BL-002-S20

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S20` |
| original scout id(s) | Perplexity `C-005` |
| title/reference | "Machine Learning Analytics for Blockchain-Based Financial Markets: A Confidence-Threshold Framework for Cryptocurrency Price Direction Prediction" |
| link or citation text | <https://www.mdpi.com/2076-3417/15/20/11145> |
| author/source | Oleksandr Kuznetsov et al.; MDPI Applied Sciences, per scout report |
| date/version | October 17, 2025 |
| source type | Peer-reviewed academic paper, per scout report |
| scout-report origin | Perplexity |
| dataset scope | 802,967 transaction observations across 11 cryptocurrency trading pairs |
| asset class/universe | Cryptocurrency markets |
| timeframe | October 2023-October 2024 |
| point-in-time assumptions | Chronological partitions are reported; exact feature timing needs verification |
| data quality assumptions | Exchange/source, missing trades, liquidity, and fee assumptions unresolved |
| explicit input definition | MLP probability vectors from standardized closing prices |
| threshold or parameter rationale | Confidence threshold stepped by 0.01, with coverage ratio around 11.99 percent reported |
| validation design | Threshold-to-coverage mapping on partitioned data |
| no-lookahead controls | Temporal partitions are claimed but not verified |
| reproducibility notes | Network topology and training limits described; code/data not normalized |
| robustness or out-of-sample evidence | Shows coverage collapse under high thresholds, but one-year window limits robustness |
| limitations | MLP black box, one-year crypto sample, overfitting risk, not simple-threshold aligned |
| non-claims | Does not authorize ML, probability scoring, direction, confidence, or production use |
| future binding notes | Could be used only as an out-of-scope example of confidence-threshold tradeoffs |
| unresolved gaps | Verify paper, data, code, chronological splits, and whether title/link metadata match |
| preliminary routing category | Category E |
| preliminary routing note | Too ML-heavy and short-windowed for direct intake |

### P30-BL-002-S21

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S21` |
| original scout id(s) | Gemini/browser `C6-JL-TSCROSS-ARXIV-2023` |
| title/reference | "Jointly Learning Time-Series and Cross-Sectional Strategies" |
| link or citation text | <https://arxiv.org/pdf/2302.10175.pdf> |
| author/source | Academic authors; arXiv preprint |
| date/version | arXiv 2023-02, per scout report |
| source type | Research preprint combining ML with TSMOM/CSMOM baselines |
| scout-report origin | Gemini/browser |
| dataset scope | Large panel of assets for time-series and cross-sectional momentum baselines |
| asset class/universe | Futures and/or equities, exact setup requires source verification |
| timeframe | Multi-year daily or monthly historical data, exact dates unresolved |
| point-in-time assumptions | Time-ordered splits and lagged returns are reported |
| data quality assumptions | Dataset access, preprocessing, and survivorship assumptions unresolved |
| explicit input definition | TSMOM, CSMOM, and neural-network price-history features |
| threshold or parameter rationale | Return sign and ranking thresholds in baselines; learned model is not simple-threshold |
| validation design | Train/validation/test splits with OOS comparisons against baselines |
| no-lookahead controls | Lagged features and time splits are claimed |
| reproducibility notes | Model details may be described; code availability not normalized |
| robustness or out-of-sample evidence | OOS comparisons across strategies reported by scout |
| limitations | ML focus, complex learned features, weak fit for simple advisory evaluator |
| non-claims | Not validation evidence and not implementation approval |
| future binding notes | Could provide context for baseline/OOS design only |
| unresolved gaps | Verify source, exact data, code, model complexity, and baseline separability |
| preliminary routing category | Category E |
| preliminary routing note | Interesting but too complex and preprint-based |

### P30-BL-002-S22

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S22` |
| original scout id(s) | Claude `P30-BL-002-C09` |
| title/reference | "Implementation Risk in Portfolio Backtesting: A Previously Unquantified Source of Error" |
| link or citation text | <https://arxiv.org/abs/2603.20319>; <https://arxiv.org/pdf/2603.20319> |
| author/source | arXiv preprint; authors not normalized by scout report |
| date/version | 2026, per scout report |
| source type | arXiv benchmark study |
| scout-report origin | Claude |
| dataset scope | 180 S&P 500 constituents over five years, stratified into buckets, per scout report |
| asset class/universe | US equities, S&P 500 subset |
| timeframe | Five years; exact dates need verification |
| point-in-time assumptions | Data and signal logic held fixed across engines, per scout report |
| data quality assumptions | Corporate actions, constituent timing, cost-model assumptions need verification |
| explicit input definition | 15 benchmark strategies including SMA momentum and cross-sectional momentum |
| threshold or parameter rationale | Threshold relevance is indirect through benchmark rule parameters |
| validation design | Cross-engine comparison with transaction-cost regimes |
| no-lookahead controls | Not the primary topic; held-fixed design must be checked |
| reproducibility notes | Benchmark suite described as reusable; code availability not verified |
| robustness or out-of-sample evidence | Engine agreement and divergence under costs are reported, not signal validation |
| limitations | Preprint; engine-risk focus; short window; not threshold-specific |
| non-claims | Does not validate a signal or threshold |
| future binding notes | Could inform future backtester determinism review outside P30-BL-002 validation |
| unresolved gaps | Verify source, engine list, code/data, exact dates, and relevance |
| preliminary routing category | Category E |
| preliminary routing note | Useful later for implementation-risk review, not current threshold sourcing |

### P30-BL-002-S23

| Field | Normalized entry |
| --- | --- |
| normalized source id | `P30-BL-002-S23` |
| original scout id(s) | Perplexity `C-008` |
| title/reference | "When the Rules Change: Adaptive Signal Extraction via Kalman Filtering and Markov-Switching Regimes" |
| link or citation text | <https://arxiv.org/html/2601.05716v2> |
| author/source | Sungwoo Kang; Korea University / arXiv, per scout report |
| date/version | February 25, 2026 |
| source type | Academic preprint / empirical microstructure research |
| scout-report origin | Perplexity |
| dataset scope | 2,788,940 daily observations across 2,439 Korean stocks, per scout report |
| asset class/universe | Korean stock market by investor type |
| timeframe | 2020-2024 |
| point-in-time assumptions | Kalman filtering uses iterative updates; exact state timing needs review |
| data quality assumptions | Order-flow data access, investor classification, and cleaning assumptions unresolved |
| explicit input definition | Jensen-Shannon Divergence, order-flow vectors, Kalman filters, Markov switching |
| threshold or parameter rationale | Dynamic threshold sensitivity across regimes and investor types |
| validation design | Strategy performance matrix plus information-theoretic validation, per scout |
| no-lookahead controls | PIT-like state updating is claimed but not verified |
| reproducibility notes | Summary statistics and variable definitions reported; no open data/code normalized |
| robustness or out-of-sample evidence | Regime-dependent OOS evidence claimed; must not be accepted without review |
| limitations | Complex Bayesian/state-space machinery and unavailable inputs; not simple-threshold aligned |
| non-claims | Does not authorize adaptive regime model implementation |
| future binding notes | Could be a later regime-threshold research lead only |
| unresolved gaps | Verify source, data availability, code, exact state update timing, and feasibility |
| preliminary routing category | Category E |
| preliminary routing note | Too complex and data-dependent for current scope |

## Deduplicated Candidate Summary

| Normalized id | Title | Category | Likely usefulness | Main gap | Formal review intake candidate |
| --- | --- | --- | --- | --- | --- |
| `P30-BL-002-S01` | Revisiting the Profitability of Market Timing with Moving Averages | C | Negative-control MA timing benchmark | Verify code/data and exact timing correction | Yes |
| `P30-BL-002-S02` | Simple Technical Trading Rules and the Stochastic Properties of Stock Returns | B | Canonical rule specification | No modern OOS/PIT design | Maybe |
| `P30-BL-002-S03` | Data-Snooping, Technical Trading Rule Performance, and the Bootstrap | C | Multiple-testing and OOS negative-control benchmark | Verify implementation path | Yes |
| `P30-BL-002-S04` | Evidence-Based Technical Analysis | C | Large rule-universe falsification reference | Book/data/code details need reconstruction | Maybe |
| `P30-BL-002-S05` | Time Series Momentum | A | Direct dataset-specific simple threshold-rule candidate | No public code/PIT vendor detail from scout | Yes |
| `P30-BL-002-S06` | Double OOS crypto walk-forward optimization | D | DVC/walk-forward infrastructure candidate | arXiv/code/data verification; crypto scope | Maybe |
| `P30-BL-002-S07` | Interpretable Hypothesis-Driven Trading | E | Walk-forward template with honest OOS decay | arXiv, RL complexity, possible LLM/NLP layer | No |
| `P30-BL-002-S08` | FactSet point-in-time backtesting white paper | D | PIT snapshot semantics | Vendor/proprietary and not direct threshold evidence | Maybe |
| `P30-BL-002-S09` | Small-Cap Stock Trading Strategies for Retail | D | PIT/delisting checklist candidate | Weak provenance and no public code/data | Maybe |
| `P30-BL-002-S10` | Harvey and Liu, Backtesting | B | Multiple-testing methodology | Not dataset-specific threshold evidence | Maybe |
| `P30-BL-002-S11` | Probability of Backtest Overfitting | B | PBO/CSCV methodology | Not dataset-specific | Maybe |
| `P30-BL-002-S12` | Backtest Overfitting in the ML Era | B | CV-method comparison | Synthetic data only | Maybe |
| `P30-BL-002-S13` | Triple Barrier meta-labeling notebook | E | Volatility-scaled threshold concept | Tick/ML complexity and license/data gaps | No |
| `P30-BL-002-S14` | GT-Score | E | Close shape to RSI/MACD threshold testing | arXiv, yFinance, survivorship, PIT gaps | Maybe |
| `P30-BL-002-S15` | Volume-Price-Adjusted MACD | E | Explicit indicator threshold parameter | arXiv and weak fixed-block validation | Maybe |
| `P30-BL-002-S16` | Generic SSRN Backtesting paper | F | Possible parameter-grid mechanics | Unclear author/date/provenance | No |
| `P30-BL-002-S17` | BacktestBase minimum trades | F | Checklist heuristics | Blog, non-dataset-specific, heuristic | No |
| `P30-BL-002-S18` | Revisiting Equity Strategies with Financial ML | B | CPCV/purging/embargo methodology | ML-heavy and not simple threshold | Maybe |
| `P30-BL-002-S19` | Taming the Black Swan / AEGIS | E | Portfolio threshold/correlation idea | Optimizer complexity and portfolio scope | No |
| `P30-BL-002-S20` | Crypto confidence-threshold MLP | E | Coverage/threshold tradeoff example | MLP black box and one-year crypto window | No |
| `P30-BL-002-S21` | Jointly Learning Time-Series and Cross-Sectional Strategies | E | Baseline/OOS design context | ML-heavy arXiv preprint | No |
| `P30-BL-002-S22` | Implementation Risk in Portfolio Backtesting | E | Later backtester determinism context | Engine-risk focus, not signal evidence | No |
| `P30-BL-002-S23` | Kalman / Markov-switching adaptive signals | E | Regime-dependent threshold lead | Too complex and data-dependent | No |

Deduplication notes:

- `P30-BL-002-S07` combines Claude `P30-BL-002-C07` and Perplexity `C-002`.
- Perplexity works-cited references to GT-Score were treated as supporting
  origin context for `P30-BL-002-S14`, but the normalized entry relies on the
  Claude candidate detail.
- Gemini/browser bibliography-only links were not normalized when no
  candidate-level fields were supplied.

## Package-Level Gap Analysis

| Requirement | Current package status | Gap consequence |
| --- | --- | --- |
| source provenance | Present as scout-provided links for 23 entries | Primary-source metadata, versions, authors, code links, and access dates still require direct verification |
| dataset scope | Present for many entries, absent or weak for methodology-only sources | Formal review must separate direct dataset-specific candidates from methodology-only references |
| asset universe | Present for most direct candidates | Several entries remain vague, proprietary, synthetic, or asset-agnostic |
| timeframe | Present for many entries, weak for several | Exact sample windows and split boundaries must be verified |
| point-in-time assumptions | Strong in PIT/DVC/CPCV candidates, weak in older and preprint entries | No-lookahead cannot be accepted from scout claims alone |
| data quality assumptions | Partial | Corporate actions, survivorship, roll logic, missing data, exchange quality, and universe timing are often unresolved |
| explicit input definition | Strong for MA, momentum, TSMOM, MACD, RSI, triple-barrier, and some ML entries | Several inputs are too complex or too model-dependent for simple advisory evaluation |
| threshold or parameter rationale | Present across many entries | Rationale ranges from explicit rule thresholds to methodology-only statistics and portfolio constraints |
| validation design | Present in many entries | Designs vary widely: OOS, walk-forward, CPCV, bootstrap, fixed block, synthetic, and educational heuristics |
| no-lookahead controls | Promising but unverified | Formal review must verify feature timing, label timing, split timing, and preprocessing timing directly |
| reproducibility | Mixed | Some entries claim code/data; many are proprietary, book-only, blog-only, or preprint-code-unverified |
| robustness or OOS evidence | Mixed | Strong negative controls exist; many sources have limited, synthetic, fixed-block, or unverified OOS evidence |
| limitations | Recorded at package level and source level | Source-specific review must refine each limitation from primary text |
| non-claims | Recorded at package and source level | No entry can be used for profitability, actionability, or implementation readiness |
| future binding notes | Recorded conservatively | No binding is allowed before formal review and exact validated artifacts exist |
| unresolved gaps | Material but visible | Package can guide review triage, but does not validate P30-BL-002 |

## Candidate Strength Classification

Source-package readiness classification: partial but needs additional sourcing.

The package is stronger than the prior incomplete Step 3 record because it now
contains normalized candidate entries from the supplied scout reports. It is
still not strong enough to validate a threshold, approve `P30-BL-002`, or make
anything implementation-ready. Scout reports must be checked against primary
sources before formal review can rely on any entry.

Most promising intake candidates:

- `P30-BL-002-S01`: negative-control moving-average timing critique
- `P30-BL-002-S03`: data-snooping / OOS negative-control benchmark
- `P30-BL-002-S05`: direct time-series momentum threshold-rule candidate
- `P30-BL-002-S08`: point-in-time snapshot methodology anchor

Most useful methodology-only anchors:

- `P30-BL-002-S10`
- `P30-BL-002-S11`
- `P30-BL-002-S12`
- `P30-BL-002-S18`

Most likely reject or quarantine entries:

- `P30-BL-002-S16`
- `P30-BL-002-S17`
- `P30-BL-002-S19`
- `P30-BL-002-S20`
- `P30-BL-002-S21`
- `P30-BL-002-S22`
- `P30-BL-002-S23`

This classification is not validation. It is only source-package readiness
triage.

## Recommended Routing

Phase 32 Step 4 adds a docs-only primary-source verification gate in
[`phase32_p30_bl_002_primary_source_verification_gate.md`](phase32_p30_bl_002_primary_source_verification_gate.md).
That gate verifies selected source identities and intake eligibility only. It
does not formally review, approve, validate, promote, or implement any source.

Recommended safest next route after the verification gate: limited formal
review intake for selected candidates plus additional verification of unresolved
source details.

Suggested review intake shortlist, still candidate-only:

1. `P30-BL-002-S03` for threshold-rule data-snooping and OOS negative control.
2. `P30-BL-002-S01` for lookahead-bias correction in moving-average timing.
3. `P30-BL-002-S05` for a direct simple zero-threshold momentum rule across a
   broad dataset.
4. `P30-BL-002-S08` for point-in-time and no-lookahead infrastructure
   semantics.
5. `P30-BL-002-S10` and `P30-BL-002-S11` only as validation-design references.

Phase 32 Step 4 narrows the first four as follows: `P30-BL-002-S05`,
`P30-BL-002-S03`, and `P30-BL-002-S01` are eligible for limited formal review
intake only; `P30-BL-002-S08` is maybe eligible for methodology-only PIT review
intake and is not a direct threshold-source candidate.

Do not start implementation from this package. Do not create a
`ValidatedResearchArtifact` or `ValidatedSignalDefinition`. Do not approve any
production threshold or advisory signal behavior.

## Explicit Non-Claims

This phase does not validate a signal, threshold, edge, profitability,
robustness, or implementation readiness.

This phase does not approve a production threshold or config value. It does
not prove that `indicator_value` is predictive, profitable, robust, actionable,
or suitable for live or paper trading.

This phase does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, bind a signal definition to an artifact, formally
review `P30-BL-002`, promote `P30-BL-002`, or make it implementation-ready.

This phase does not add a real signal evaluator, signal computation, scoring,
ranking, direction, confidence, probability, actionability, broker behavior,
Alpaca behavior, runtime behavior, scheduler behavior, persistence, ML, or LLM
trading-path behavior.

## Remaining Blockers

Evaluator implementation remains blocked until later phases resolve all of the
following:

- primary sources are verified directly
- source versions, authors, access paths, and code/data availability are
  checked
- dataset scope, asset universe, timeframe, and data quality assumptions are
  explicit for any source selected for formal review
- point-in-time and no-lookahead assumptions are audited from primary source
  material
- exact input definitions and comparator semantics are reviewed
- threshold or parameter rationale is dataset-specific or conservatively
  classified as methodology-only
- validation design and robustness/out-of-sample evidence are reviewed
- reproducibility notes are concrete enough for deterministic rerun or are
  recorded as blockers
- limitations and non-claims are source-specific and accepted by review
- formal review against the Phase 30 evidence standard is complete
- all review gaps needed for promotion are resolved
- an exact `ValidatedResearchArtifact` exists
- an exact `ValidatedSignalDefinition` exists and binds to the accepted
  artifact
- threshold/config provenance is explicit and reviewed
- implementation scope is explicitly approved
- production evaluator tests are scoped and ready to be written
- the implementation phase remains narrow, deterministic, offline-safe,
  broker-isolated, credential-free, and outside the LLM trading hot path

## Verification

Verification after the revised Phase 32 Step 3:

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
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_p30_bl_002_source_package.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated
