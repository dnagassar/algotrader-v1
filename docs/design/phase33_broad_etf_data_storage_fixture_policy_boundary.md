# Phase 33 Step 9 - Broad ETF Data Storage / Fixture Policy Boundary

## Purpose

This document defines future data storage and fixture policy requirements for
the broad-ETF simple moving-average research candidate.

The purpose is to preserve normal `python -m pytest` as offline,
credential-free, deterministic, and safe while preventing raw third-party data
from entering the repository without explicit later approval.

This phase is documentation-only. It approves no source, data, ETF universe,
benchmark, cash proxy, methodology, parameter, reproduction, validation,
signal definition, evaluator, implementation, fixture, storage location, or
trading use.

It adds no data, fixture, notebook, script, schema, test, source code,
evaluator, signal computation, trading-path behavior, broker behavior, runtime
behavior, scheduler behavior, persistence behavior, portfolio behavior, ledger
behavior, reconciliation behavior, Alpaca behavior, ML behavior, vectorbt
behavior, QuantConnect behavior, notebook runtime behavior, or LLM
trading-path behavior.

## Current Boundary

No broad-ETF research data may be acquired, downloaded, ingested, stored,
snapshotted, reproduced, or validated under this phase.

No raw third-party price data may enter the repository under this phase.

No downloaded CSV/API snapshot may enter the repository under this phase.

No fixture for the broad-ETF moving-average candidate is created or approved
under this phase.

Normal `python -m pytest` must not call provider APIs, access the network,
read credentials, read local-only broad-ETF data, download data, ingest data,
or depend on external provider state.

## Data Categories

| Category | Handling rule |
| --- | --- |
| Raw third-party price data | Prohibited from the repository in this phase. Future use requires explicit source, terms/license, storage, provenance, redistribution, and pytest-eligibility approval. |
| Downloaded CSV/API snapshots | Prohibited from the repository in this phase. A future plan must record retrieval date, endpoint or page, fields, adjustment assumptions, checksum, storage location, and redistribution status before any snapshot exists. |
| ETF issuer metadata | Metadata/context only. Reviewed summaries may support docs, but copied pages, fact sheets, holdings files, distribution tables, or issuer exports are not approved as repo data or fixtures. |
| FRED cash/risk-free series | Cash/risk-free proxy candidate only. Future use requires final terms/API/citation/storage review and must not require network or credentials in normal pytest. |
| Manually entered metadata | May appear in reviewed docs only as cited context. It is not an approved dataset, fixture, validation input, benchmark, universe definition, or source of truth for implementation. |
| Tiny synthetic fixtures | Possible future repo fixtures only after scoped approval. They must be deterministic, small, redistribution-safe, explained by generation notes, and free of vendor rows. |
| Tiny derived fixtures | Possible future repo fixtures only if terms permit redistribution and the fixture cannot expose or reconstruct prohibited raw vendor data. They must not imply strategy validation. |
| Checksums/manifests | Possible future repo records for provenance, integrity, and snapshot identity. A checksum or manifest does not approve source use, redistribution, storage, reproduction, or validation. |
| Provenance records | Possible future repo docs or manifests that describe source identity, retrieval, terms status, limitations, and non-claims. Provenance alone does not make data trusted or pytest-eligible. |
| Charts/plots/results | Exploratory outputs only unless a later scoped phase approves reviewed placement. They must not be treated as validation evidence, reproduced results, source approval, or implementation guidance. |
| Notebooks/prototype outputs | Controlled by Phase 34. They cannot become canonical data, trusted fixtures, validated artifacts, or normal pytest inputs without this policy plus later scoped approval. |

## Storage Policy Options

These are possible future policies to compare later. This phase does not
approve a final storage policy.

| Option | Possible future use | Current status |
| --- | --- | --- |
| No raw third-party data in repo | Keep vendor/provider rows entirely out of Git and rely on approved synthetic or manifest-only fixtures for tests. | Compatible with current safety goals, but not approved as a final permanent policy. |
| Local-only ignored data directory | Store approved snapshots outside tracked files for manual research or gated reproduction only. | Not approved. Would require a later path, `.gitignore` policy, provenance rule, and pytest exclusion rule. |
| Small synthetic fixtures in repo | Test parser, alignment, date-handling, or calculation mechanics with invented values only. | Not approved for this candidate. Future approval must define generation notes and allowed test scope. |
| Small derived fixtures only if redistribution-safe | Store tiny non-raw derived examples only when source terms permit and values cannot reconstruct prohibited source data. | Not approved. Requires source-specific terms review and explicit redistribution status. |
| Checksum/provenance manifest in repo | Track snapshot identity, source metadata, hashes, limitations, and storage pointers without storing raw data. | Not approved as a final policy, but likely a required component of any later snapshot plan. |
| External archival outside repo | Preserve approved snapshots in a separate archive, storage bucket, or human-controlled location. | Not approved. Must remain outside normal pytest and document access, retention, and provenance. |
| Encrypted/private storage outside normal pytest | Hold sensitive or restricted research data outside Git and default tests. | Not approved. Must not require credentials, decryption, API keys, or private files for normal pytest. |

No option authorizes acquisition, download, ingestion, fixture creation,
backtesting, reproduction, validation, implementation, or trading-path use.

## Fixture Policy Requirements

Any future broad-ETF fixture proposal must satisfy all of these requirements
before it can be used by normal pytest:

- fixtures must be deterministic
- fixtures must be redistribution-safe
- fixtures must be small
- fixtures must not require credentials, network, provider APIs, broker APIs,
  external SDKs, or wall-clock provider state
- fixtures must not contain prohibited raw vendor or provider data
- fixtures must include provenance or a synthetic-generation explanation
- fixtures must record what they are allowed to test
- fixtures must record what they do not prove
- fixtures must not imply strategy validation, profitability, robustness,
  production readiness, implementation readiness, or trading readiness
- normal pytest may use only approved deterministic fixtures

For this candidate, no approved deterministic fixture currently exists.

## Provenance And Manifest Requirements

Any future snapshot or fixture plan must record at minimum:

- source
- retrieval date
- license/terms review status
- ticker/universe
- date range
- fields
- adjustment assumptions
- checksum/hash
- storage location
- redistribution status
- pytest eligibility
- limitations and non-claims

The provenance record must also state whether network access, credentials, API
keys, account state, subscriptions, manual page capture, notebooks, prototype
tools, hosted platforms, or external agents were involved.

If any required provenance field is missing, the data or fixture remains
ineligible for trust, reproduction, validation, implementation, and normal
pytest.

## Local-Only Data Boundary

Local-only data may exist outside the repository only after future explicit
approval.

Any future local-only data must:

- be ignored by Git
- be outside normal `python -m pytest`
- never be required for default tests
- have documented provenance
- have documented terms/license status
- have documented storage and retention expectations
- have documented limitations and non-claims
- avoid broker/runtime/trading-path dependencies
- avoid treating the local copy as validated evidence

Credentials, API keys, account state, subscriptions, private files, provider
sessions, and encrypted stores must never be required for normal pytest.

Local-only data may support only a later explicitly approved manual or
skipped-by-default workflow. It must not become a hidden dependency of docs,
tests, source code, evaluator behavior, signal computation, or trading-path
logic.

## Relationship To Phase 34

Phase 34 Step 1 keeps external research integrations advisory only.

Phase 34 Step 2 requires external artifact intake metadata before outside
research can influence project decisions.

Phase 34 Step 3 keeps notebooks, vectorbt prototypes, QuantConnect outputs,
spreadsheets, CSV extracts, charts, external platform reports, and copied
snippets exploratory only.

Those artifacts cannot become canonical data, trusted fixtures, source of
truth, validation evidence, or normal pytest inputs merely because they exist
or were useful during exploration. Notebook and prototype outputs need this
policy boundary plus later scoped approval before any repo placement, fixture
use, deterministic reproduction plan, or implementation route is considered.

## Terms And License Constraints

Phase 33 Step 7 remains the current terms/license boundary:

- Stooq has moderate terms uncertainty and is not approved.
- Yahoo Finance / yfinance / Yahoo API terms have high terms uncertainty and
  are not approved.
- Nasdaq Data Link is secondary/check only and remains dataset-specific.
- Alpha Vantage is secondary/check only and remains constrained by API-key,
  rate-limit, coverage, adjustment, and terms questions.
- FRED has low apparent terms risk pending final review, but only as a
  cash/risk-free proxy candidate.
- ETF issuer pages are metadata/context only.
- Broker historical data is context only and not a default project source.

No source is approved. Public availability, familiar client libraries,
manual downloads, exported CSVs, screenshots, notebooks, charts, or hosted
platform outputs do not approve local storage, private-repo archival,
redistribution, fixture creation, reproduction, validation, implementation, or
normal pytest use.

## Recommended Future Gates

Recommended later docs-only gates:

- moving-average evidence/source package
- broad ETF source approval boundary, only after refreshed source terms and
  storage constraints are reviewed
- fixture policy approval boundary, only if the project wants to approve exact
  synthetic, derived, manifest, or local-only fixture rules
- reproduction protocol boundary, only after source, universe, benchmark/cash
  proxy, methodology, and data policy choices are approved

Any later gate must keep normal pytest offline, credential-free,
deterministic, and free of broker/runtime/trading-path behavior unless a later
explicit phase scopes a separate skipped-by-default integration path.

## Explicit Non-Goals

This phase does not perform or authorize:

- source approval
- universe approval
- benchmark approval
- cash proxy approval
- methodology approval
- parameter approval
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
- no acquired data
- no project-local deterministic reproduction
- no no-lookahead audit
- no production threshold/config provenance
- no implementation-scope approval
- no evaluator tests
- no approved source-specific storage path
- no approved local-only data path
- no approved raw-data redistribution path
- no approved synthetic fixture plan
- no approved derived fixture plan
- no approved checksum/provenance manifest format
- no approved pytest-eligible fixture set
- no approved adjusted-price semantics
- no approved total-return versus price-return decision
- no approved dividend/reinvestment treatment
- no approved corporate-action handling policy
- no approved correction/revision policy
- no approved point-in-time/as-of policy
- no approved inactive-fund, delisting, merger, or ticker-change policy
- no approved benchmark/cash-proxy frequency alignment rule
- no approved cash-rate conversion or compounding rule
- no approved transaction cost, slippage, spread, rebalance, fund-expense, or
  friction assumption
- no result-review template
- no promotion/rejection decision
- no trading implication or production threshold
