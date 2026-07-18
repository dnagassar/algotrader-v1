# V5.29 Target-Scoped Independent Flat Collection

## Purpose

V5.29 closes the broker-origin gap between the pure V5.27 independent-flat
validator and the source-bound V5.27 capability producer. It adds one canonical
paper-only command boundary that reads the account, all positions, and all open
orders after a bounded probe's final exit fill.

The collector supports exactly BTCUSD, ETHUSD, and SOLUSD. It creates no order,
has no mutation callback, and grants no paper, capital, or live authority.

## Activation Boundary

The collector accepts only:

- an exact supported target symbol;
- a locally persisted lifecycle receipt for the same target;
- either the historical V5.10 BTCUSD lifecycle schema or the frozen V5.29
  target-lifecycle schema;
- a final exit order with status filled and a timezone-aware filled_at;
- an observation time at or after that broker-reported exit fill;
- explicit read and network switches;
- APP_PROFILE=paper;
- an exact Alpaca paper endpoint;
- paper credentials and an expected paper-account identifier; and
- no live-endpoint or network-test indicator.

Symbol and lifecycle validation occurs before environment-based client
construction. Missing authorization, a mismatched target, malformed lifecycle,
future exit timestamp, live endpoint, absent credentials, or expected-account
misconfiguration fails before any broker read.

## Broker Read Contract

The command performs exactly three read classes:

1. account status and identity;
2. account-wide positions; and
3. account-wide open orders.

A successful receipt requires:

- an ACTIVE account;
- explicit blocked=false, account_blocked=false, and
  trading_blocked=false;
- exact expected-account matching;
- zero positions across the entire account;
- zero open orders across the entire account;
- successful completion of all three reads;
- no ambiguity;
- no mutation; and
- no live endpoint.

The raw account identifier and account number exist only in process memory long
enough to verify the expected account and derive the domain-separated V5.27
account fingerprint. They are never persisted.

## Source And Chronology Binding

latest_status.json binds the exact lifecycle source SHA-256, selected symbol,
lifecycle schema, and exit fill timestamp. A successful
independent_flat_manifest.json binds:

- the sanitized receipt bytes;
- the operator-status bytes;
- the exact lifecycle source bytes; and
- the exact collector source bytes.

The emitted independent_flat_reconciliation.json remains the exact strict
V5.27 receipt schema consumed by capability production. It is therefore
compatible with the existing normalized capability and sealed-review contract.

A later failed or nonflat observation cannot leave an earlier mutable-latest
receipt active. Existing latest receipt and manifest files are moved intact to
the generated superseded/ directory under a status-fingerprint name. The
latest receipt path then remains absent until a newer successful read.

## Command

The command is intentionally unusable from a credential-free development
shell. After a winner-specific lifecycle has a confirmed filled exit, use an
isolated paper shell and run exactly:

    .\scripts\run_crypto_bounded_probe_independent_flat_operator.ps1
      -TargetSymbol <BTCUSD|ETHUSD|SOLUSD>
      -LifecyclePath <exact-lifecycle-result-path>
      -IndependentFlatReadAuthorized
      -AllowNetwork
      -AsOfTimestamp <CURRENT_UTC_TIMESTAMP>

The wrapper prints only boolean credential-presence state. It does not print
credential values or raw account identifiers.

## Authority Boundary

V5.29 authorizes no submit, cancel, replace, close, liquidation, capital
allocation, paper mutation, live endpoint, or live trading. The current
tournament remains in untouched-OOS accrual until its fixed calendar endpoint.
The next implementation milestone is the dormant exact-winner bounded lifecycle
operator that produces the lifecycle receipt consumed here.
