# Phase 88 - Local Snapshot Return-Basis / As-Of Boundary

## Purpose

This document defines how future local snapshot metadata may be interpreted
with respect to return basis, adjustment policy, observation dates,
acquisition dates, as-of dates, and no-lookahead timing.

It is documentation-only. It exists to prevent adjusted, vendor revised, or
otherwise hindsight-shaped data from being treated as point-in-time
decision-safe merely because a local metadata record exists.

## Decision Boundary

Phase 88 may define interpretation rules only.

It does not approve:

- any source
- any data
- any universe
- any benchmark
- any cash proxy
- any methodology
- any parameter set
- any evidence
- any strategy validation
- any trading use

No local snapshot is approved. No source candidate is approved. No data file is
read, acquired, ingested, rendered, hashed, checked, transformed, compared,
ranked, scored, recommended, or made eligible for normal pytest.

## Manifest Date Semantics

Future local snapshot metadata may contain several date fields. These fields
are descriptive metadata only, and none proves point-in-time tradability or
no-lookahead safety by itself.

| Field | Intended metadata meaning | Boundary limit |
| --- | --- | --- |
| `acquisition_date` | The date the local snapshot was obtained, exported, copied, or otherwise captured into the local environment. | It is not a decision date, an observation date, a publication date, or evidence that the data was available historically at any earlier decision timestamp. A later acquisition can preserve a local artifact, but it can also encode hindsight and vendor corrections. |
| `observation_start_date` | The first labeled market, series, or event date described by rows in the snapshot. | It describes the label on the data, not when the row became knowable, complete, corrected, adjusted, or tradable. |
| `observation_end_date` | The last labeled market, series, or event date described by rows in the snapshot. | It is not proof that every observation between start and end exists, is usable, is current, is final, or was available by any decision timestamp. |
| `as_of_date` | The declared metadata cutoff, source state, extraction state, or documented reference state for the manifest. | It is not necessarily market availability, provider publication time, exchange dissemination time, corporate-action availability, or revision cutoff. It must not be treated as a no-lookahead guarantee. |

Observation dates describe the dates the data claims to represent.
`acquisition_date` describes when the local snapshot was obtained. `as_of_date`
describes the declared metadata cutoff or source state. These concepts must
remain separate from decision timestamps and action timestamps.

## Adjustment Policy Interpretation

`adjustment_policy` is descriptive metadata. It is not source approval, data
approval, return-construction approval, or no-lookahead approval.

| Policy | Metadata-level meaning | Why not automatically approved | Lookahead and revision risks | Proof required before research use |
| --- | --- | --- | --- | --- |
| `unknown` | The manifest does not know or does not assert how values were adjusted. | Unknown adjustment semantics cannot support economic return claims. | Values may be raw, split-adjusted, dividend-adjusted, total-return-like, corrected, revised, or mixed without disclosure. | Treat as unknown or block use; obtain source documentation, field definitions, sample-row checks, correction policy, and explicit limitations before any research consumption. |
| `raw_close` | Values are described as unadjusted close-like prices. | Raw close can be split-discontinuous and excludes distributions. | Splits, symbol changes, stale prices, missing sessions, and corrections can distort returns; dividends and distributions are absent. | Split/corporate-action policy, raw-field definition, calendar and missing-data policy, and a documented decision/action timing rule. |
| `adjusted_close` | Values are described as vendor or source adjusted close-like prices. | Adjusted close may encode provider assumptions that are not transparent or point-in-time safe. | Historical values can change after later splits, distributions, corrections, restatements, or vendor methodology changes. | Source-specific adjustment documentation, revision policy, corporate-action timing, reproducible snapshot hashes outside normal pytest, and no-lookahead tests. |
| `split_adjusted` | Values are described as adjusted for splits but not necessarily distributions. | Split adjustment alone does not define dividend, distribution, or total-return treatment. | Split factors may be corrected later; other corporate actions may remain unhandled; comparisons can silently mix return bases. | Split-factor source, effective-date handling, correction policy, dividend/distribution exclusion statement, and comparable return-basis documentation. |
| `total_return_vendor` | Values are described as a vendor- or source-supplied total-return series. | A total-return label does not reveal methodology, reinvestment convention, fees, taxes, revision policy, or availability timing. | Vendor total-return histories may be backfilled, restated, corrected, or calculated with information unavailable at the decision timestamp. | Field definition, methodology document, distribution timing, reinvestment assumption, revision history, availability rules, license/offline-use approval, and deterministic tests. |
| `explicit_total_return_construction` | Metadata says total return would be constructed from documented inputs and rules. | A manifest cannot prove that the required fields, formulas, or timing assumptions are correct or approved. | Distribution ex-date/payment-date choice, reinvestment timing, missing distributions, splits, corrections, stale rows, and future-known events can introduce lookahead. | Approved construction spec, source fields, corporate-action timing rules, cash/reinvestment treatment, examples, tests, and separate return-construction approval. |

## Return Basis Interpretation

`return_basis` is descriptive metadata, not validation. It records the claimed
economic basis of future return interpretation only if a later phase approves
the surrounding source, fields, methodology, timing, and tests.

| Basis | Metadata-level meaning | Boundary interpretation |
| --- | --- | --- |
| `unknown` | The manifest does not know or does not assert the return basis. | Blocks any claim that returns are economically complete, comparable, validated, total return, or decision-safe. |
| `price_return` | Returns would be interpreted as price-only changes. | Price return is not total return. It generally excludes dividends and distributions and needs split, missing-data, stale-price, and action-timing rules before use. |
| `adjusted_price_return` | Returns would be interpreted from adjusted price-like values. | Adjusted price returns may include vendor or source corporate-action assumptions. They require documented adjustment semantics, revision handling, and no-lookahead tests before use. |
| `total_return` | Returns would be interpreted as including price change plus distributions under a selected convention. | Total return needs explicit source or construction rules, distribution timing, reinvestment policy, correction policy, and approval before any research claim. |

Unknown return basis must remain blocking for any claim that returns are
economically complete. A price-return path must not be relabeled as total
return. An adjusted-price path must not be assumed point-in-time safe. A
total-return label must not stand in for source or construction proof.

## No-Lookahead Implications

Future local snapshot research must keep timing concepts separate:

- observation date versus decision timestamp
- decision timestamp versus action timestamp
- action timestamp versus measured return window
- acquisition date versus historical availability
- as-of date versus provider publication or revision cutoff

At minimum, later policy must resolve:

- same-close ambiguity: using a close to decide and act at that same close is
  unapproved unless a later boundary proves availability and feasible action
  timing without lookahead
- next-open assumptions: require explicit open availability, holiday handling,
  gap treatment, and fill assumptions before use
- next-close assumptions: require explicit lag, missed-return treatment, and
  holding-window rules before use
- adjusted-data revision risk: adjusted histories can change after later
  corporate actions, corrections, or vendor methodology updates
- dividend, split, distribution, and other corporate-action timing: ex-date,
  record-date, payment-date, announcement-date, effective-date, and
  reinvestment conventions must be documented before use
- stale or missing data: missing sessions, stale observations, inactive
  instruments, and gaps must have deterministic handling
- holiday and calendar alignment: source calendars, market sessions, rebalance
  dates, benchmark dates, and cash series dates must align by availability
- vendor correction and revision risk: corrected rows and revised histories
  must be tracked by acquisition and revision policy, not treated as original
  observations
- source acquisition after the fact: a file acquired later may contain values,
  adjustments, corrections, or memberships that were unavailable at the
  historical decision time
- local snapshot status: a local file is not automatically a point-in-time
  dataset merely because it is stored locally or described by a manifest

Local snapshots are reproducibility aids only until a later phase separately
approves source rights, data semantics, revision treatment, as-of rules, and
research use.

## Future Approval Gates

Before future local snapshot data can be used in broad ETF research, the
project must have later gates showing at minimum:

- source candidate remains candidate-only until separately approved
- manifest exists and validates metadata only
- adjustment policy is understood or explicitly treated as unknown
- return basis is selected and documented
- no-lookahead/as-of rules are selected and tested
- action timing is selected and documented
- corporate-action and dividend handling is resolved or explicitly out of
  scope
- universe, inception, and survivorship policy is resolved
- benchmark and cash timing is resolved if used
- normal pytest remains synthetic, offline, credential-free, provider-free,
  broker-free, and independent of local data

Passing these gates would still not by itself approve a source, data,
evidence, strategy validation, implementation, or trading use. Any approval
would need a separate explicit phase.

## Relationship To `LocalSnapshotManifest`

`LocalSnapshotManifest` stores metadata only.

It does not:

- prove file contents
- hash files during normal pytest
- read or validate rows
- check paths
- approve local snapshots
- make snapshots normal-pytest inputs
- prove source rights
- prove data quality
- prove adjustment or return-basis semantics
- prove no-lookahead safety
- prove evidence readiness
- prove replay readiness

The manifest should not be linked into planning or replay as proof of data
readiness yet. At most, it can remain a metadata-only description that helps a
future approval review ask sharper questions.

## Explicit Non-Claims

Phase 88 is:

- not source approval
- not data approval
- not return-construction approval
- not no-lookahead approval
- not universe approval
- not benchmark approval
- not cash proxy approval
- not methodology approval
- not parameter approval
- not evidence approval
- not strategy validation
- not trading readiness

It also adds no real data ingestion, no real market data, no real ETF tickers,
no benchmark comparison, no ranking, no scoring, no recommendation, no
candidate discovery, no replay metrics, no report rendering, no manifest to
planning bridge, no signal or evaluator behavior, no advisory integration, no
governance behavior, no broker, order, fill, portfolio, runtime, paper, live,
or trading behavior, and no LLM, network, API, provider, or market-data call.

## Decision

Decision: interpretation boundary only.

Future local snapshot metadata may be used to describe dates, adjustment
policy, and return basis, but it must not be treated as proof that local data
is source-approved, data-approved, point-in-time safe, no-lookahead safe,
economically complete, replay-ready, evidence-ready, validated, or trading
ready.

## Remaining Blockers

- no approved source
- no approved data
- no approved local snapshot
- no approved storage rule for raw third-party market data
- no approved ETF universe
- no approved benchmark
- no approved cash proxy
- no approved methodology
- no approved parameter set
- no approved evidence
- no approved adjustment policy
- no approved return basis
- no approved total-return construction
- no approved no-lookahead/as-of policy
- no approved action timing
- no approved corporate-action or dividend handling
- no approved inception/survivorship policy
- no approved benchmark/cash timing
- no manifest-to-planning bridge
- no implementation-readiness claim
- no strategy-validation claim
- no trading-readiness claim
