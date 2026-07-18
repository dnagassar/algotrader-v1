# V5.27 Crypto Tournament V2 Capability Production And Replay

## Decision

V5.27 implements the candidate-deferred operational-evidence path selected by
V5.26. It materially improves end-to-end research-to-paper autonomy, but it
does not add strategy-return evidence and does not authorize a paper or live
trade.

The producer may evaluate operational evidence only after a sealed V5.25
terminal export names the exact tournament-v2 winner. Before then it publishes
only `candidate_deferred_pending_terminal_winner`. A malformed or irrelevant
capability input cannot change that classification.

## Frozen Identity And Authority

- V5.26 preregistration fingerprint:
  `3b82ebcaf3c80b9c1fbda5797623b2e616dfef0a3ed38d2cc52c0b1d3151efb5`
- V5.27 bounded-probe safety-policy fingerprint:
  `c0abbc047f7bdf01f19d46e06d3824acd980016b4bd992d78dd4994db6d2c407`
- Frozen symbol set: BTCUSD, ETHUSD, and SOLUSD.
- Maximum notional and principal: USD 10.
- Durable restart-latched loss halt: USD 2.
- Long/cash only; one position, open order, entry, and exit; one cancel per
  order; zero replacements; maximum duration 168 hours.

Every production status, capability, review, manifest, pointer, and replay
result keeps network, broker mutation, paper mutation, capital allocation, and
live authority false. `eligible_for_operator_review_only` is not trading
authorization.

## Candidate-Deferred Flow

1. Recover and validate V5.25 state.
2. If no terminal winner exists, publish a diagnostic-only immutable
   production and stop.
3. If the terminal outcome is a quality or economic rejection, publish the
   terminal diagnostic and stop.
4. Only for the exact accepted winner, resolve all required source bytes.
5. Validate venue, bounded-policy, lifecycle/flat, and durable-kill evidence as
   one all-or-nothing bundle.
6. Run the V5.26 review against the derived capabilities.
7. Publish immutable fingerprint-addressed artifacts and an atomic latest
   pointer.
8. Replay a pinned production or review from its captured source bytes and
   trusted current UTC before it can support a later operator review.

No symbol argument, fallback candidate, ranking rescue, or hand-authored
capability path exists.

## Safety Certification

The offline bounded-probe safety module combines a pure evaluator with a
durable local SQLite control store. It is default-paused and has no broker,
credential, network, or order-submission import. Its focused certification
covers:

- the exact USD 1–10 entry envelope;
- cash, margin, and account-state gates;
- stale/future market data and broker snapshots;
- unexpected state and broker ambiguity;
- the durable USD 2 loss latch and restart behavior;
- atomic entry admission and attempt claiming;
- restart-persistent entry, cancel, and exit attempt budgets;
- risk-reducing cancel/exit paths while entry is halted; and
- an all-false authority contract.

The certification receipt hashes the supplied kernel, certifier, and focused
test. The running certifier binds the kernel and certifier hashes to the
implementations loaded by the process; the focused-test hash is bound to the
canonical repository test bytes but the certifier does not execute or import
that test. Supplying benign implementation bytes while executing different code
cannot produce eligibility. Capability production likewise runtime-binds its
loaded safety roles. It binds account-binding, flat-reconciliation, venue,
lifecycle, and producer roles to the canonical local bytes hashed when the
producer module was imported before admitting their evidence.

## Venue Provenance

Venue orderability requires one coherent V5.1 paper-read packet:

- `manifest.json`;
- `crypto_universe.json`;
- `crypto_orderability_metadata.json`;
- `crypto_router_input_manifest.json`;
- the exact runtime visibility receipt; and
- the exact V5.1 refresh, visibility-wrapper, and supervisor source bytes.

Manifest artifact hashes, packet identities, read-only safety fields, router
paths, candidate records, and nested runtime metadata are cross-validated. The
runtime selected symbol must equal the tournament winner. Membership in a broad
eligible-symbol list is insufficient. Both the runtime observation and V5.1
refresh must independently be no more than 24 hours old; the older timestamp
controls capability age.

The orderability record's advertised minimum notional, size, and trade
increment must exactly equal both its broker-observed fields and the runtime
visibility fields. Optional price and quantity increments may be absent only
when both required string fields are identically empty; a present value must be
positive. A nonempty alternate `min_order_notional` must equal the cross-bound
primary minimum. A derived minimum order value above USD 10 blocks the probe
envelope.

V5.28 adds an optional exact BTCUSD, ETHUSD, or SOLUSD target to the read-only
visibility operator and both wrappers. It validates the target before client
construction, uses it as the sole supervisor preference, and leaves selection
empty when the target is absent. Operational venue normalization now requires
the runtime target and selected symbol to match the terminal winner and emits
explicit target-scope fields for independent sealed-review validation.

## Lifecycle And Flat Provenance

The legacy V5.8 submit/cancel and V5.10 fill/exit producers are BTCUSD-only.
They can never certify ETHUSD or SOLUSD, even if a caller edits their symbol
fields.

BTC lifecycle normalization requires a locally hash-coherent chain:

- V5.6 paper OMS dry run;
- V5.7 submit approval packet;
- V5.8 result and manifest;
- V5.9 fill approval packet and manifest;
- V5.10 result and manifest; and
- exact V5.6–V5.10 producer source bytes.

V5.8 hashes its result and both inputs. V5.9 independently hashes its packet
and the exact V5.8 result. V5.10 hashes its result; its legacy input references
are path-only, so V5.27 closes that gap by requiring the V5.9 hash chain,
matching summaries, paths, and derived prior-certification identity. The
normalized record labels this honestly as a local hash-coherent legacy
reconstruction, not externally signed broker attestation.

The V5.8 receipt must prove one submit and one cancel, zero filled quantity,
no residual position, and no residual open order. The V5.9 approval packet and
manifest must match the canonical writer's exact schemas, artifact paths,
hashes, sizes, labels, prior-certification identity, operator phrase, and
all-false authority fields. The positive integration fixture invokes that
canonical writer and consumes its persisted bytes through V5.10; a hand-built
lookalike is not sufficient. V5.10 must prove exactly one entry and one exit,
both finally filled with positive quantities that exactly match their nested
final-order records.

V5.6, V5.7, V5.8, V5.9, and V5.10 timestamps must be timezone-aware,
normalized to UTC, non-future, and chronologically ordered. The V5.9 manifest
timestamp must equal its approval packet. The earliest antecedent controls
lifecycle freshness; a newer result cannot launder an older or future-dated
precursor.

Within V5.10, the run timestamp must precede the entry submission, entry fill,
exit submission, and exit fill in that order. The broker-reported exit
`filled_at` is the final mutation timestamp. Independent flat evidence must be
observed at or after that timestamp, not merely after the V5.10 run timestamp.

The current historical mutable-latest chain does not retain the exact V5.6
bytes named by V5.8. Strict production validation therefore rejects it. This is
evidence integrity doing its job, not a request to weaken the gate.

Independent flat reconciliation is produced by a pure validator from already
collected account, position, and open-order observations. It requires an active
expected paper account, completed read attestations, zero account-wide
positions and open orders, no ambiguity, no mutation, and no live endpoint.
Raw account identifiers are replaced by a domain-separated SHA-256 binding in
normalized capability and flat outputs. Both lifecycle receipts and the fresh
flat receipt must resolve to the same binding. Historical lifecycle account
observations must be active and carry all three explicit false block flags. A
flat receipt expires after 15 minutes.

The flat builder requires all three account block flags explicitly present and
false. It validates already-collected observations and does not itself prove
their broker origin. A later mutation review therefore still requires the
canonical target-scoped read-only collection path and exact operator-gated
observation; a hand-authored flat receipt is not readiness evidence.

The sealed V5.26 review does not trust normalized lifecycle or venue claims by
assertion. It independently re-derives selected-symbol venue semantics,
account-binding equality, and final-mutation-to-flat ordering from the captured
upstreams. Unexpected authority-, permission-, credential-, occurrence-,
performance-, attempt-, or endpoint-shaped fields fail closed.

## Immutable Publication And Replay

Production and review publication use an exclusive local lock, immutable
fingerprint-addressed generations, exact artifact manifests, and a latest
pointer written last. Loaders reject mixed mutable/immutable layouts, unsafe
paths, links/reparse points, duplicate JSON keys, noncanonical JSON, invalid
UTF-8, status/manifest/pointer drift, authority-field injection, and Windows
path aliases such as alternate data streams or reserved device names.

Malformed or blocked inputs are never copied into immutable `resolved_sources`
snapshots. A fully validated eligible bundle retains exact raw lifecycle source
bytes because pinned replay must re-execute their provenance checks. Those
ignored local artifacts can contain noncredential broker/account/order
identifiers; keep them under `runs/`, do not publish or attach them, and use the
sanitized normalized outputs for reporting.

Replay reconstructs the production from captured raw sources, re-executes the
review with trusted current UTC, and requires exact historical fingerprints.
Recomputed outer hashes cannot hide source, packet, or duplicate-key tampering.

## Operator Commands

Run from a credential-free development shell, never the paper shell:

```powershell
.\scripts\run_crypto_tournament_v2_capability_pipeline.ps1
```

The command rejects paper/live profiles, Alpaca credential aliases,
network-test switches, and live endpoint indicators before Python starts. It
performs no network or broker operation. It refreshes the source-bound safety
certification and publishes from existing local venue, lifecycle, and flat
evidence; it does not fetch or create those observations. Until V5.25 seals an
accepted winner, the expected classification is
`candidate_deferred_pending_terminal_winner`.

After an eligible capability production is reviewed by V5.26, replay that
exact immutable review publication only with its pinned outer review
fingerprint:

```powershell
.\scripts\replay_crypto_tournament_v2_bounded_paper_probe_review.ps1 `
  -ExpectedPublicationFingerprint <64-character-fingerprint>
```

Pinned replay resolves the outer review generation directly without trusting
its mutable latest pointer. It revalidates the review manifest, captured
sources, embedded capability pointer, trusted current UTC, and exact historical
fingerprints. It remains non-authorizing.

## Verified Baseline And V5.28 Continuation

The real 2026-07-17 offline run certified BTCUSD, ETHUSD, and SOLUSD safety and
published the correct candidate-deferred generation with every authority field
false. This increases operational autonomy and trustworthiness; it does not
change the strategy-evidence clock or live-capital readiness.

V5.28 now provides target-scoped, no-submit, read-only visibility for each
frozen symbol and binds a future operational venue capability to exactly that
target. V5.29 adds canonical, exact-target independent-flat collection after a
filled exit, including account-wide flatness, source-byte binding, sanitized
account identity, and stale-receipt supersession. The remaining evidence
milestone is the terminal-winner-specific bounded lifecycle operator; the
legacy lifecycle chain is BTCUSD-only and cannot certify an ETHUSD or SOLUSD
winner. Additional LLM APIs, retrieval services, QuantConnect integration, or
a new strategy tournament do not address that evidence dependency.
