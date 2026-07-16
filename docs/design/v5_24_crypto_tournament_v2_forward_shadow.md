# V5.24 Tournament V2 Single-Winner Forward Shadow

## Decision And Bottleneck

Tournament v2 is now collecting real untouched OOS data, so its remaining
delay is evidentiary and calendar-bound rather than an implementation failure.
The next principal implementation bottleneck was downstream: even a sealed
winner could only request a new forward-shadow milestone, and no frozen
activation contract existed.

V5.24 removes that future stop before any winner is known. It does not score
the current OOS window, expose interim candidate metrics, or create trading
authority.

## Frozen Contract

- Schema: `v5_24_crypto_tournament_v2_forward_shadow_v1`
- Policy: `v5_24_crypto_tournament_v2_forward_shadow_policy_v1`
- Preregistration fingerprint:
  `7ff152e69bd00eb8da9376d1f2be15194fbd04ed6a420151e30c3c46bec82436`
- Source tournament fingerprint:
  `2ed9489543d8d21ab00d9f2f4000927b8012decf39882cb721cb2d1ce0b9376b`
- Candidate scope: exactly one hash-bound terminal tournament-v2 winner
- Window: 168 new one-hour observations beginning at the first complete UTC
  hour not earlier than both terminal closure and the v2 OOS endpoint
- Checkpoints: 24, 72, and 168 hours
- Early stopping, window extension, parameter mutation, and post-selection
  gate changes: disabled

The contract requires the sealed terminal packet SHA-256, terminal evidence
fingerprint, state fingerprint, exact terminal classification, and exact
candidate ID/fingerprint from the frozen nine-candidate v2 manifest. A delayed
terminal evaluation moves the shadow start forward to the next complete hour;
it never backfills post-selection evidence from a partially observed hour.

## Evidence Scope

The future shadow must produce a causal hourly target log, hypothetical
position and transition log, 40 bps base-cost and 80 bps stress-cost results,
cash and same-symbol buy-and-hold comparisons, drawdowns, transitions, round
trips, and decision-log completeness. The guarded provider receipt, output
hash, selected symbol, raw coverage, volume coverage, and isolated-gap policy
remain mandatory.

Completion can mean only
`evidence_complete_for_bounded_paper_probe_review`. It does not authorize the
probe itself and is not a profitability claim.

## Current Verified Classification

At the locked baseline, tournament v2 is `collecting_untouched_oos` and has no
selected candidate. V5.24 therefore correctly emits
`waiting_for_tournament_terminal`, an empty activation fingerprint, no shadow
window, and the next action
`continue_receipt_bound_tournament_v2_oos_accrual`.

## Authority Boundary

The implementation imports only research and validation code. Its wrapper
fails if a paper profile or broker credential is loaded. It performs no
network access, market-data fetch, broker read, broker mutation, paper
planning, submit, cancel, replace, close, liquidation, capital allocation, or
live action. Generated readiness artifacts remain ignored under `runs/`.
