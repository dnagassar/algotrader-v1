# V5.28 Target-Scoped Read-Only Crypto Venue Visibility

## Purpose

V5.28 closes the venue-observation gap identified by V5.27. A future accepted
BTCUSD, ETHUSD, or SOLUSD winner can now request one exact symbol from the
existing paper-read visibility path and retain that symbol's full allowlisted
asset metadata without falling back to another eligible asset.

This is an operational-evidence capability only. It adds no strategy evidence,
paper mutation, live authority, capital allocation, or profit claim.

## Exact Target Contract

The Python visibility operator accepts an optional `target_symbol`.

- Omitted or empty preserves the existing general visibility preference.
- A nonempty value must be exactly `BTCUSD`, `ETHUSD`, or `SOLUSD`.
- Case folding, whitespace trimming, slash normalization, aliases, and arbitrary
  symbols are rejected.
- Validation occurs before environment resolution, SDK client construction, or
  any broker asset read.
- A valid target becomes the supervisor's sole preferred symbol.
- If the target is absent from the observed eligible assets, selection remains
  empty. BTCUSD or ETHUSD cannot rescue a missing SOLUSD target.

Receipts expose `target_symbol` and `target_scoped`. General untargeted
visibility remains useful for observation, but V5.27 venue capability
normalization now requires `target_scoped=true` and an exact match between the
target, runtime selected symbol, terminal winner, and normalized venue subject.
The sealed V5.26 review independently verifies the normalized target binding.

## Wrapper Contract

`scripts/run_crypto_paper_visibility_cycle.ps1` accepts `-TargetSymbol`,
performs the same case-sensitive allowlist check before invoking Python, prints
only the target value, and forwards it as `--target-symbol`.

`scripts/run_crypto_universe_refresh.ps1` accepts the same parameter only with
`-Mode paper_read_only`. It rejects invalid, nonexact, or silently unused
targets before invoking the visibility wrapper. In the gated paper-read path it
threads the target into the visibility command and normalizes the resulting
local artifact as before.

A fresh real paper-read still requires the existing paper profile, paper
credentials, exact paper endpoint, explicit `-PaperReadOnlyAuthorized` switch,
and exact operator authorization for that read. V5.28 itself performs no real
broker read.

## Safety Properties

- no order construction or submit path;
- no cancel, replace, close, or liquidation path;
- no paper mutation or capital authority;
- no live endpoint or live credential authorization;
- credential values remain excluded from receipts and console output;
- invalid targets fail before SDK/Python broker-facing setup;
- target absence fails closed with no symbol fallback;
- source-bound capability and pinned replay contracts remain intact.

## Verification

The focused V5.28 plus V5.27 consumer matrix covers the Python operator, both
PowerShell wrappers, SOLUSD positive selection, missing-target no-fallback,
invalid-target pre-client rejection, capability production, sealed review,
pinned replay, and dependency direction.

- Focused target-scope and consumer matrix: `186 passed in 70.22s`.
- Offline verifier: PASS, including `97 passed in 198.74s`.
- Bounded exact-node full suite: 9,283 tests with collection and execution
  equivalence; `9,279 passed`, `4 skipped`, zero failures/errors.

No network request, market-data fetch, broker/account read, broker mutation,
paper mutation, live endpoint, or capital action is part of the offline
verification path.
