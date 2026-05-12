# Phase 31 P30-BL-001 Source Package

## 1. Purpose And Status

Phase 31 Step 3 normalizes a source package for `P30-BL-001`,
"Simple scalar threshold indicator definition", using source-discovery material
from research-agent-assisted collection.

This is source normalization only. It is not formal candidate review,
validation, approval, production readiness, implementation readiness, or a
trading claim.

Current status:

- `P30-BL-001` is source-package-ready only.
- The sources below are collected and normalized for later review.
- No source has been accepted as a `ValidatedResearchArtifact`.
- No `ValidatedSignalDefinition` binds to this package.
- No production threshold value, comparator, or evaluator behavior is approved.
- No implementation scope is approved.

Agent handling:

- Codex, Perplexity, or similar tools may help discover and summarize sources.
- Research-agent output remains untrusted notes until checked against sources.
- This package records traceable source metadata and conservative relevance
  notes, not agent claims.
- Source access date for web sources in this package: 2026-05-12.

## 2. Normalized Source Table

Each entry uses the same normalized fields required before formal review. Review
suitability is a routing note only, not a review result.

### P30-BL-001-S01

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S01` |
| title | Python 3.11 documentation, "Built-in Types - Comparisons" |
| author/organization | Python Software Foundation |
| source type | Official software documentation |
| date/version if known | Python 3.11 documentation, accessed 2026-05-12 |
| URL/citation | <https://docs.python.org/3.11/library/stdtypes.html#comparisons> |
| category | threshold semantics |
| what it supports | The programming-language meaning of comparison operators, including `>=` as greater than or equal, for comparable values. |
| what it does not prove | It does not prove any market indicator, threshold value, signal direction, profitability, risk reduction, or trading suitability. |
| relevance to `indicator_value` | Useful only if a future evaluator compares an explicit scalar `indicator_value` against an explicit scalar threshold in Python. |
| relevance to threshold-style advisory evaluator | Useful for formalizing comparator semantics after, and only after, research and signal-definition support exist. |
| limitations | Language semantics source only; not finance research and not a signal-definition source. |
| review suitability | Tier A for comparator mechanics; not sufficient by itself for candidate validation. |

### P30-BL-001-S02

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S02` |
| title | Python 3.11 documentation, "decimal - Decimal fixed point and floating point arithmetic" |
| author/organization | Python Software Foundation |
| source type | Official software documentation |
| date/version if known | Python 3.11 documentation, accessed 2026-05-12 |
| URL/citation | <https://docs.python.org/3.11/library/decimal.html> |
| category | mechanical definition; reproducibility |
| what it supports | `Decimal` as an explicit decimal numeric representation with configurable arithmetic context and exact decimal construction from strings. |
| what it does not prove | It does not prove that `Decimal` is required for every indicator, that any threshold is correct, or that a signal has trading value. |
| relevance to `indicator_value` | Supports reviewing whether a future `indicator_value` should be represented as `Decimal` when exact decimal traceability is desired. |
| relevance to threshold-style advisory evaluator | Useful for input and threshold type rationale, not for strategy semantics. |
| limitations | Software numeric-type documentation only; no market-data, indicator, or threshold evidence. |
| review suitability | Tier A for value-type mechanics; not sufficient by itself for candidate validation. |

### P30-BL-001-S03

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S03` |
| title | TA-Lib C/C++ API Documentation |
| author/organization | TA-Lib Technical Analysis Library |
| source type | Open-source library documentation |
| date/version if known | Accessed 2026-05-12 |
| URL/citation | <https://ta-lib.org/api/> |
| category | mechanical definition; reproducibility |
| what it supports | Technical analysis functions can be treated as deterministic array-processing functions with explicit input arrays, output arrays, and calculation ranges. |
| what it does not prove | It does not prove any particular indicator formula is valid for this project, that an output should be named `indicator_value`, or that thresholds support trading. |
| relevance to `indicator_value` | Supports the idea that an indicator output can be an explicit scalar or series element produced from explicit inputs. |
| relevance to threshold-style advisory evaluator | Useful for mechanical input/output framing if a future reviewed artifact chooses a concrete indicator. |
| limitations | Library API documentation; not a research artifact, no dataset, no validation, and no production threshold rationale. |
| review suitability | Tier A/B for mechanical function-shape review; likely useful but not complete. |

### P30-BL-001-S04

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S04` |
| title | TA-Lib Python wrapper documentation, "Momentum Indicators" |
| author/organization | TA-Lib Python project |
| source type | Open-source library documentation |
| date/version if known | Accessed 2026-05-12 |
| URL/citation | <https://ta-lib.github.io/ta-lib-python/func_groups/momentum_indicators.html> |
| category | mechanical definition |
| what it supports | Examples of named momentum indicators such as `RSI`, `MOM`, and `ROC` producing numeric `real` outputs from explicit inputs and parameters. |
| what it does not prove | It does not prove that RSI, momentum, rate of change, or any threshold should be implemented or traded. |
| relevance to `indicator_value` | Supports the generic notion of a named scalar indicator output but does not define this project's exact input name. |
| relevance to threshold-style advisory evaluator | Useful as a mechanical source if formal review later narrows `indicator_value` to a specific indicator output. |
| limitations | Wrapper docs are implementation-oriented and do not provide dataset-specific validation, threshold rationale, or non-claims. |
| review suitability | Tier B supporting source; pair with stronger provenance before formal validation. |

### P30-BL-001-S05

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S05` |
| title | StockCharts ChartSchool, "Relative Strength Index (RSI)" |
| author/organization | StockCharts.com |
| source type | Educational technical-analysis reference |
| date/version if known | Accessed 2026-05-12 |
| URL/citation | <https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi> |
| category | mechanical definition; threshold semantics; non-claims |
| what it supports | A concrete example of a bounded oscillator with conventional overbought and oversold threshold terminology. |
| what it does not prove | It does not prove RSI should be used, that 70/30 or any other threshold is valid here, or that threshold crossings are profitable. |
| relevance to `indicator_value` | Useful only as an example that an indicator value can be bounded and compared with thresholds. |
| relevance to threshold-style advisory evaluator | May help reviewers discuss conventional threshold vocabulary while keeping production threshold selection blocked. |
| limitations | Vendor educational source; not primary research, not dataset-specific, and not sufficient for implementation approval. |
| review suitability | Tier B supporting source; formal review should avoid treating its conventional levels as validated thresholds. |

### P30-BL-001-S06

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S06` |
| title | scikit-learn User Guide, "Tuning the decision threshold for class prediction" |
| author/organization | scikit-learn developers |
| source type | Official software methodology documentation |
| date/version if known | scikit-learn 1.8.0 documentation, accessed 2026-05-12 |
| URL/citation | <https://scikit-learn.org/stable/modules/classification_threshold.html> |
| category | threshold semantics; cross-domain analogy |
| what it supports | A useful distinction between producing a score/probability-like value and applying a decision threshold to map that value to an output class. |
| what it does not prove | It does not prove a trading threshold, signal direction, actionability, or profitability. |
| relevance to `indicator_value` | Helps frame `indicator_value` as an input scalar separate from the later advisory condition produced by threshold comparison. |
| relevance to threshold-style advisory evaluator | Useful analogy for keeping scalar measurement separate from advisory output semantics. |
| limitations | Machine-learning classification context, not trading research and not a validated signal definition. |
| review suitability | Tier A/B for threshold semantics; likely useful as supporting methodology, not direct validation. |

### P30-BL-001-S07

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S07` |
| title | scikit-learn API Reference, `FixedThresholdClassifier` |
| author/organization | scikit-learn developers |
| source type | Official software API documentation |
| date/version if known | scikit-learn 1.8.0 documentation; class added in 1.5; accessed 2026-05-12 |
| URL/citation | <https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.FixedThresholdClassifier.html> |
| category | threshold semantics; reproducibility |
| what it supports | A constant threshold can be represented explicitly rather than tuned implicitly at runtime. |
| what it does not prove | It does not prove the correct threshold value, metric, signal semantics, or trading use. |
| relevance to `indicator_value` | Supports the idea that a future threshold should be explicit and traceable when comparing a scalar input. |
| relevance to threshold-style advisory evaluator | Useful as a cross-domain software analogy for fixed threshold provenance. |
| limitations | ML classifier API, not financial research and not a source for market thresholds. |
| review suitability | Tier B supporting source. |

### P30-BL-001-S08

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S08` |
| title | scikit-learn API Reference, `TimeSeriesSplit` |
| author/organization | scikit-learn developers |
| source type | Official software methodology documentation |
| date/version if known | scikit-learn 1.8.0 documentation, accessed 2026-05-12 |
| URL/citation | <https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html> |
| category | no-lookahead; reproducibility |
| what it supports | Time-ordered evaluation should avoid training on future observations and evaluating on earlier observations. |
| what it does not prove | It does not prove this package has a dataset, validation split, feature construction, or no-lookahead compliance. |
| relevance to `indicator_value` | Supports the requirement that any future observed scalar value must be timestamped and available no later than `as_of`. |
| relevance to threshold-style advisory evaluator | Useful for formal review questions around point-in-time data and future-data leakage. |
| limitations | Cross-domain ML validation source; not specific to financial indicators or production evaluator behavior. |
| review suitability | Tier A/B for no-lookahead methodology; supporting source only. |

### P30-BL-001-S09

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S09` |
| title | Reproducibility and Replicability in Science |
| author/organization | National Academies of Sciences, Engineering, and Medicine |
| source type | Consensus study report |
| date/version if known | 2019 |
| URL/citation | <https://www.ncbi.nlm.nih.gov/books/NBK547537/> |
| category | reproducibility; governance |
| what it supports | Reproducibility depends on clear data, code, methods, computational steps, and conditions of analysis. |
| what it does not prove | It does not prove any market signal, indicator, threshold, or backtest result. |
| relevance to `indicator_value` | Supports requiring exact input provenance, computation method, and regeneration path for any future concrete indicator value. |
| relevance to threshold-style advisory evaluator | Useful as a general evidence standard for repeatable research artifacts. |
| limitations | General science methodology source, not trading-specific and not a candidate artifact. |
| review suitability | Tier A/B for reproducibility criteria; supporting source only. |

### P30-BL-001-S10

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S10` |
| title | "The Probability of Backtest Overfitting" |
| author/organization | David H. Bailey, Jonathan Borwein, Marcos Lopez de Prado, Qiji Jim Zhu |
| source type | Research paper |
| date/version if known | SSRN posted 2013-09-16; last revised 2015-03-03 |
| URL/citation | <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253> |
| category | reproducibility; governance |
| what it supports | Backtest overfitting is a material research-risk category when selecting strategies from historical simulations. |
| what it does not prove | It does not prove a threshold, indicator, signal definition, or profitability claim for this project. |
| relevance to `indicator_value` | Indirect only; it informs future review caution if any candidate claims performance for a scalar threshold. |
| relevance to threshold-style advisory evaluator | Useful to keep threshold selection and performance claims out of this source package unless separately validated. |
| limitations | Backtesting methodology source, not a mechanical indicator definition and not a validation of `P30-BL-001`. |
| review suitability | Tier B supporting source for later performance-claim review; not central to mechanical normalization. |

### P30-BL-001-S11

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S11` |
| title | 17 CFR 4.41, "Advertising by commodity pool operators, commodity trading advisors, and the principals thereof" |
| author/organization | Legal Information Institute, citing the Code of Federal Regulations |
| source type | Regulatory text reference |
| date/version if known | Accessed 2026-05-12 |
| URL/citation | <https://www.law.cornell.edu/cfr/text/17/4.41> |
| category | non-claims; governance |
| what it supports | Hypothetical or simulated performance material requires prominent limitations and must not be presented as actual trading performance. |
| what it does not prove | It does not prove any indicator, threshold, signal, or strategy, and it is not legal advice for this project. |
| relevance to `indicator_value` | None mechanically; useful for non-claim language if future artifacts discuss simulated results. |
| relevance to threshold-style advisory evaluator | Supports conservative disclosure that advisory outputs are not actual trades, performance claims, or profit guarantees. |
| limitations | Regulatory disclosure source; not research evidence and not implementation guidance. |
| review suitability | Tier A/B for non-claim governance; supporting source only. |

### P30-BL-001-S12

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S12` |
| title | FINRA Investor Insights, "What Is Momentum Investing?" |
| author/organization | Financial Industry Regulatory Authority |
| source type | Investor education |
| date/version if known | 2025-08-12 |
| URL/citation | <https://www.finra.org/investors/insights/momentum-investing> |
| category | mechanical definition; non-claims; governance |
| what it supports | Technical indicators are described as based on price, volume, or open interest, and momentum indicators can be risky and give false signals. |
| what it does not prove | It does not prove a specific indicator definition, threshold value, or trading strategy. |
| relevance to `indicator_value` | Broadly supports that indicator values should derive from explicit market inputs, but not the placeholder name itself. |
| relevance to threshold-style advisory evaluator | Useful for non-claim framing: indicators can be inputs to analysis without becoming guaranteed or actionable trade decisions. |
| limitations | Investor education, not formal research, no exact formula, no dataset, and no validation procedure. |
| review suitability | Tier B supporting source. |

### P30-BL-001-S13

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S13` |
| title | CDC, "Adult BMI Categories" |
| author/organization | Centers for Disease Control and Prevention |
| source type | Public-health guidance |
| date/version if known | 2024-03-19 |
| URL/citation | <https://www.cdc.gov/bmi/adult-calculator/bmi-categories.html> |
| category | cross-domain analogy; threshold semantics; non-claims |
| what it supports | A scalar value can be mapped into named categories by explicit numeric ranges while remaining a screening measure rather than a complete decision. |
| what it does not prove | It does not prove anything about financial indicators, trading thresholds, profitability, or risk-adjusted returns. |
| relevance to `indicator_value` | Analogy only: a scalar input can have explicit range semantics. |
| relevance to threshold-style advisory evaluator | Useful for explaining why threshold categories should stay advisory and limited. |
| limitations | Health-domain analogy only; should not be reviewed as financial evidence. |
| review suitability | Tier C informational/cross-domain only. |

### P30-BL-001-S14

| Field | Normalized entry |
| --- | --- |
| source id | `P30-BL-001-S14` |
| title | EPA, "AirData Basic Information" |
| author/organization | United States Environmental Protection Agency |
| source type | Public environmental-data guidance |
| date/version if known | Accessed 2026-05-12 |
| URL/citation | <https://www.epa.gov/outdoor-air-quality-data/airdata-basic-information> |
| category | cross-domain analogy; threshold semantics; governance |
| what it supports | Air Quality Index values are grouped into named ranges, showing a public example of scalar threshold bands and category labels. |
| what it does not prove | It does not prove any trading indicator, threshold value, strategy, or performance claim. |
| relevance to `indicator_value` | Analogy only: scalar values can be mapped to bounded advisory categories. |
| relevance to threshold-style advisory evaluator | Useful only for vocabulary around range bands and advisory labeling. |
| limitations | Environmental-health domain; not finance research and not a candidate validation source. |
| review suitability | Tier C informational/cross-domain only. |

## 3. Source Tiering

Tiering below is a pre-review routing aid. It does not validate any source.

Tier A: likely useful for formal review:

- `P30-BL-001-S01`: comparator mechanics for `>=`.
- `P30-BL-001-S02`: `Decimal` and explicit numeric-value mechanics.
- `P30-BL-001-S03`: deterministic technical-analysis function shape.
- `P30-BL-001-S08`: no-lookahead/time-ordered methodology questions.
- `P30-BL-001-S09`: reproducibility and transparency standard.
- `P30-BL-001-S11`: non-claim and hypothetical-performance governance.

Tier B: useful supporting sources:

- `P30-BL-001-S04`: concrete technical-analysis wrapper examples.
- `P30-BL-001-S05`: threshold vocabulary example with clear limitations.
- `P30-BL-001-S06`: score/value versus threshold-decision separation.
- `P30-BL-001-S07`: explicit fixed-threshold analogy.
- `P30-BL-001-S10`: backtest-overfitting caution for later performance claims.
- `P30-BL-001-S12`: investor-education support for conservative non-claims.

Tier C: informational/cross-domain only:

- `P30-BL-001-S13`: BMI scalar-range analogy.
- `P30-BL-001-S14`: AQI scalar-range analogy.

Exclude or deprioritize:

- weak-provenance posts
- vendor-only performance claims
- social-media claims
- screenshot-only material
- sources without methodology
- sources that imply trading actionability without reproducible support
- sources that select thresholds without data, assumptions, and limitations

## 4. Candidate Source Grouping

Mechanical indicator definitions:

- `P30-BL-001-S03`
- `P30-BL-001-S04`
- `P30-BL-001-S05`
- `P30-BL-001-S12`

Scalar threshold semantics:

- `P30-BL-001-S01`
- `P30-BL-001-S05`
- `P30-BL-001-S06`
- `P30-BL-001-S07`
- `P30-BL-001-S13`
- `P30-BL-001-S14`

Deterministic/time/no-lookahead methodology:

- `P30-BL-001-S08`

Reproducibility/backtesting methodology:

- `P30-BL-001-S09`
- `P30-BL-001-S10`

Non-claims/disclosure/governance:

- `P30-BL-001-S05`
- `P30-BL-001-S10`
- `P30-BL-001-S11`
- `P30-BL-001-S12`
- `P30-BL-001-S13`

Cross-domain threshold analogies:

- `P30-BL-001-S06`
- `P30-BL-001-S07`
- `P30-BL-001-S13`
- `P30-BL-001-S14`

## 5. Preferred Formal-Review Candidates

Review these first because they map most directly to the current
`P30-BL-001` evidence questions without claiming trading support:

1. `P30-BL-001-S03` and `P30-BL-001-S04`: review mechanical indicator
   input/output shape before choosing any specific indicator.
2. `P30-BL-001-S01`: review exact comparator semantics for any future
   threshold condition.
3. `P30-BL-001-S02`: review whether `Decimal` remains the right value type for
   explicit scalar inputs and thresholds.
4. `P30-BL-001-S06` and `P30-BL-001-S07`: review threshold semantics as
   analogies only, especially the separation between a scalar value and a
   decision category.
5. `P30-BL-001-S08` and `P30-BL-001-S09`: review no-lookahead and
   reproducibility questions that any promoted artifact must answer.
6. `P30-BL-001-S11`: review non-claim language before any future material
   mentions hypothetical or simulated performance.

Do not validate these sources in this phase. Do not claim they justify a
threshold. Do not claim they support trading.

## 6. Known Gaps

Known blockers remain:

- no exact validated research artifact yet
- no exact validated signal definition
- no production threshold value/source
- no dataset-specific validation
- no point-in-time dataset window
- no asset universe
- no timeframe or bar-size selection
- no indicator formula accepted for project use
- no proof that `indicator_value` is the final input name
- no validated comparator choice
- no profitability claim
- no risk-adjusted-return claim
- no live-trading claim
- no risk approval
- no implementation approval

## 7. Routing To Next Phase

The next research phase should be formal review of the strongest subset using:

- `docs/design/phase30_research_validation_evidence_standard.md`
- `docs/design/phase30_research_artifact_candidate_review_template.md`

That review should decide whether `P30-BL-001` is reviewable, conditionally
reviewable with gaps, failed, or informational only. Even a favorable review
would still not approve a production evaluator, signal computation, feature
computation, strategy logic, scoring, ranking, direction, actionability, risk
approval, broker behavior, runtime behavior, persistence, ML, or LLM
trading-path behavior.
