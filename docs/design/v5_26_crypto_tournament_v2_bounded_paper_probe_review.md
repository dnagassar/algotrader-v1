# V5.26 Crypto Tournament V2 Bounded Paper-Probe Review

## Purpose

V5.26 removes downstream design delay without claiming that tournament-v2 or
forward-shadow evidence already exists. It consumes one sealed V5.25 terminal
export and produces a default-denied operator review artifact. It cannot load
credentials, contact a network or broker, construct an execution intent or
plan, mutate paper state, allocate capital, or authorize live trading.

The frozen preregistration fingerprint is
`3b82ebcaf3c80b9c1fbda5797623b2e616dfef0a3ed38d2cc52c0b1d3151efb5`.

## Source Evidence Boundary

The review accepts only the V5.25 terminal-evidence exporter. That exporter
runs under the V5.25 state lock and recovery protocol, revalidates the frozen
state and every persisted artifact, regenerates normalization, decisions, and
metrics, and exports a path-free identity. The V5.26 consumer additionally
requires:

- The exact V5.24 preregistration, V5.25 state, and V5.25 packet schemas.
- One candidate exactly equal to a frozen tournament-v2 manifest candidate.
- Exactly one supported selected symbol: BTCUSD, ETHUSD, or SOLUSD.
- One contiguous 168-hour window and canonical checkpoint prefix.
- `terminal_scoring_performed=true` only for complete economic evidence.
- Exact terminal closure ordering: window end, closure, source export, review.
- Exact progress, quality, metric algebra, source hashes, and false authority.

A terminal input-quality outcome can close with a canonical incomplete
checkpoint prefix. It carries no strategy metrics and can never enter paper
review.

## Frozen Economic Gates

All eight gates are required and are evaluated directly from the frozen
manifest in manifest order:

1. Base-cost total return is strictly positive.
2. Stress-cost total return is strictly positive.
3. Base-cost excess return versus same-symbol buy-and-hold is strictly positive.
4. Stress-cost excess return versus same-symbol buy-and-hold is strictly positive.
5. Base-cost maximum drawdown is at most 20 percent.
6. Stress-cost maximum drawdown is at most 20 percent.
7. Base-cost drawdown is no worse than base-cost buy-and-hold drawdown.
8. Stress-cost drawdown is no worse than stress-cost buy-and-hold drawdown.

There is no post-result minimum transition or round-trip gate. Candidate
substitution, ranking, retuning, rescoring, rescue tuning, and window extension
are prohibited. An economic gate failure closes this activation path.

## Immutable Probe Envelope

The review-only envelope is:

- Exact selected symbol only, Alpaca crypto paper environment.
- Long or cash, cash-only, no leverage, margin, shorting, pyramiding, or
  cross-symbol exposure.
- Maximum notional and principal at risk: USD 10.
- Durable loss-halt threshold: USD 2.
- At most one position, one open order, one entry, and one exit.
- At most one cancel attempt per order and zero replacements.
- Maximum duration: 168 hours.

The loss halt is a control threshold, not a guarantee of realized loss because
slippage, gaps, and execution ambiguity remain possible.

## Operational Evidence Trust Boundary

Every required capability is selected-symbol-specific and must be fresh:

| Capability | Maximum age |
| --- | ---: |
| Venue orderability | 24 hours |
| Bounded order policy | 720 hours |
| Lifecycle plus independent flat reconciliation | 720 hours |
| Durable kill and USD 2 loss control | 168 hours |

The four evidence files are not trusted by assertion. Each must use the exact
V5.26 producer schema, policy fingerprint, and producer version; bind canonical
artifact bytes; resolve a separate producer-source file by SHA-256; match that
source's subject, time bounds, claims, authority, and fingerprint; expose the
preregistered upstream roles and schemas; and share one recomputed bundle
fingerprint. Missing, stale, cross-symbol, mixed-build, malformed, hand-created,
or source-unresolved evidence remains blocked. Every cited upstream JSON is
loaded from its fixed capability-kind/role path, its canonical bytes are
hashed, and a kind-specific validator derives the selected-symbol claims and
observation time. A digest string without the corresponding validated bytes is
not evidence.

When a capability has multiple upstreams, the earliest observation controls
its expiry. A fresh flat reconciliation therefore cannot extend stale lifecycle
mechanics. V5.27 supplies canonical local producers and source-bound replay for
the policy, lifecycle, flat, and kill schemas. The review independently
re-derives selected-symbol venue semantics, matching paper-account bindings,
and flat-at-or-after-final-exit-fill ordering from their normalized upstreams;
it does not trust those claims by assertion. Positive unit fixtures establish
validator behavior, not operational facts.

Current repository history does not satisfy all four capabilities for any
candidate. The durable crypto kill/loss certifier is executable offline, but no
genuine winner-scoped venue/lifecycle/flat bundle has been emitted. Positive
unit fixtures prove the validator contract only; they are not operational
evidence.

## Deterministic Outcomes

The only classifications are:

- `waiting_for_v5_25_terminal_evidence`
- `closed_by_terminal_shadow_input_quality_gate`
- `rejected_by_preregistered_strategy_gates`
- `blocked_by_operational_evidence`
- `eligible_for_operator_review_only`

Eligibility carries an absolute expiry equal to the earliest effective
capability expiry. A structural persisted-packet validator binds the full
packet except its review clock, including schema, candidate, terminal summary,
envelope, gates, capabilities, blockers, next action, approval state, and every
false authority field. Validation at a later trusted time fails after expiry.
That unkeyed structural check is not evidentiary replay and cannot authorize an
operation. Any future authorization consumer must rerun the review against the
snapshotted source bytes using trusted current UTC and match the exact review
fingerprint.

Even `eligible_for_operator_review_only` has approval state `not_authorized`.
Paper mutation still requires a separate exact operator authorization for a
future bounded probe. Live capital requires later paper evidence, a separate
live-readiness review, explicit capital allocation, live credentials and
endpoint controls, and exact operator authorization.

## Publication And Concurrency

Review publication holds a local process lock. Each complete packet is written
to an immutable fingerprint-addressed generation containing preregistration,
JSON review, Markdown review, terminal export when present, and—only after the
strategy gates pass—the evaluated capability files, producer sources, every
resolved upstream source, and a generation manifest. An atomic
`latest_manifest.json` pointer is written last. Exact retries deduplicate;
conflicting immutable bytes fail closed. Consumers must follow and validate
the pointer and generation manifest rather than infer readiness from file
existence. Persisted V5.26 packet validation is structural. V5.27 implements
the separate source-bound capability producer and pinned generation replay
consumer; replay remains non-authorizing. See
`docs/design/v5_27_crypto_tournament_v2_capability_production_and_replay.md`.

## Safety Classification

V5.26 materially improves end-to-end research-to-paper readiness because the
post-shadow decision contract is now preregistered and executable offline. It
does not add strategy evidence, broker connectivity, account visibility, paper
mutation, or live-capital readiness. The current project remains calendar- and
evidence-blocked, not implementation-authorized for trading.
