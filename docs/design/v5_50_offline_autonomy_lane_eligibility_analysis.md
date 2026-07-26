# V5.50 Offline Autonomy Lane Eligibility Analysis

## Status

- Status: **analysis complete. Requested milestone is BLOCKED — not by an
  operator gate, but because no eligible lane exists.**
- Base commit: `8406aef` (V5.48 promoted, V5.49 closed).
- Requested work: broaden offline autonomy to a second lane, i.e. bring a
  second lane's next-action under `EXECUTION_AUTO_OFFLINE` so the offline
  executor can do more than one thing.
- Finding: **no second lane is currently eligible.** Bringing any of the
  five remaining lanes under auto-offline execution today would require
  fabricating its inputs.

This document records the analysis so the conclusion is auditable and the
decision is not re-derived from scratch later.

## The Eligibility Criterion

V5.48 made the crypto readiness lane auto-executable. Working backwards from
why that succeeded, an action qualifies for `EXECUTION_AUTO_OFFLINE` only if
**all** of the following hold:

1. **Input self-containment.** The producing command's inputs are entirely
   contained in the repository and its frozen constants. No network, no
   broker, no operator-supplied path, no external data.
2. **A fixed, fully-defaulted argv.** The command runs with an exact
   allowlisted argument vector and no operator-substituted placeholder.
3. **Import purity.** The launcher path loads no broker, credential, or
   network module and reads no protected environment variable.
4. **Determinism.** Repeated runs produce identical evidence.
5. **Canonical target binding.** The artifact it writes is exactly the
   canonical packet the lane reads.

Criterion 1 is the binding one. Criteria 2-5 are engineering work that can
always be done. Criterion 1 is a property of the problem, not of the code —
if an artifact is a function of real-world data, no amount of wiring makes
it self-contained.

The crypto readiness replay satisfies criterion 1 uniquely: it is a pure
function of frozen constants (`DEFAULT_DECISION_START`,
`DEFAULT_CYCLE_COUNT`, all broker/paper flags false) and takes no external
input whatsoever. That is exactly the same property that caused V5.49 to be
closed — the replay attests nothing about the outside world. **The reason
this lane could be automated and the reason its freshness was meaningless
are the same fact.**

## Lane-By-Lane Assessment

Registry surveyed at `8406aef`: six lanes.

| Lane | Blocking input | Verdict |
|---|---|---|
| `crypto_supervised_readiness_trial` | none — pure function of constants | **already auto-offline (V5.48)** |
| `spy_market_data_soak` | live market-data fetch | ineligible |
| `spy_offline_daily_cycle` | operator-supplied adjusted SPY bars CSV + validation clock | ineligible |
| `crypto_forward_shadow_cycle` | tournament terminal / market-data window | ineligible |
| `crypto_bounded_paper_probe_review` | V5.25 terminal evidence | ineligible |
| `crypto_capability_production` | V5.25 terminal evidence | ineligible |

### `spy_market_data_soak`

Absent-state action is
`run_authorized_read_only_market_data_refresh_to_seed_soak`, gated
`network_market_data_fetch`. Fails criterion 1 by definition: the artifact
*is* fetched market data. Not automatable offline at any effort level.

### `spy_offline_daily_cycle`

The closest candidate, and the only lane besides readiness whose action is
already `offline_runnable=True`. Classified `offline_operator_input` with
command `etf-sma-offline-daily-cycle-run` and two required operator inputs:

- `--validated-at` — a timezone-aware daily chain clock;
- `--daily-bars-csv` — a local adjusted SPY daily-bars CSV.

The CSV is the blocker. Following the chain upstream does not remove it:
`local-daily-bars-intake` exists to canonicalize a bars CSV, but its own
root input `--input-csv` is documented as **"Operator-supplied local
daily-bars CSV to intake."** The pipeline canonicalizes operator-supplied
data; it does not originate data. Real adjusted SPY bars must enter the
system from outside, either from an operator or from a market-data fetch.

The only CSVs committed to the repository are
`tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_{199,200_bearish,200_bullish}.csv`
— synthetic scenario fixtures built to exercise the SMA matrix. Wiring
those in as a default production input would fabricate market data and
produce a lane that reports nominal on invented evidence. That is the
false-green pattern this project has repaired repeatedly and is not an
acceptable route to automation.

### `crypto_forward_shadow_cycle`, `crypto_bounded_paper_probe_review`, `crypto_capability_production`

All three report gate `no_offline_command_available` on both absent and
stale. Producer modules do exist and are local-only by construction —
`crypto_tournament_v2_bounded_paper_probe_capability_producer.py` states it
reads only local artifacts and contacts no broker or network — so at first
glance these look like V5.48-shaped wiring jobs.

They are not. Their inputs do not exist:

- Capability production "can begin only after frozen V5.25 terminal evidence
  names the exact winner" (module docstring), and both probe lanes' waiting
  actions are `await_v5_25_terminal_evidence` / `await_v5_25_terminal_winner`.
- No V5.25 terminal evidence exists anywhere in the checkout. The only
  matching tracked path is the design document
  `docs/design/v5_25_crypto_tournament_v2_forward_shadow_state.md`.
- `runs/crypto_strategy_tournament/` does not exist locally at all.

Producing that terminal evidence requires running the tournament, which
requires market data. So all three lanes are transitively blocked on the
same external input as the SPY lanes.

## What This Means Structurally

The offline executor can only ever auto-execute actions whose inputs are
self-contained. The system contains **exactly one** such action, and it is
already wired.

Therefore **offline autonomy cannot be broadened by wiring.** It can only be
broadened by giving the system a safe, authorized way to *acquire* external
inputs — which is the market-data and paper track that sits behind the
operator gate.

The two tracks presented as alternatives after the V5.49 closure are
therefore not independent: **broadening offline autonomy is gated on the
market-data/paper track**, not parallel to it. That is the substantive
correction this analysis produces.

## Options

Each is a different milestone shape and needs an explicit operator decision.

1. **Accept the ceiling and stop here.** Record that offline autonomy is
   complete at one action and that further breadth requires external input.
   Cost: nothing. This is the honest default if the market-data track is not
   ready to start.
2. **Authorize the market-data intake path** so the SPY lanes can be fed
   without an operator in the loop each cycle, then revisit
   `spy_offline_daily_cycle`. This is the only route that broadens autonomy
   over *existing* lanes. It crosses the network gate and needs its own
   frozen contract and undivided review.
3. **Add a new self-contained lane.** Rather than automating an existing
   lane, add one whose producer is genuinely self-contained *and* whose
   output varies with something real — for example an offline
   determinism/regression canary over the repository itself. Unlike V5.49's
   rejected freshness field, such a lane's evidence would vary with actual
   code changes, so it would attest something. This genuinely broadens what
   the executor does without touching the network gate, but it observes the
   system rather than the market, so it advances self-observation rather
   than trading capability. It also invents new scope and should not be
   started without an explicit decision.

Recommendation: **option 1 or option 3**, depending on whether
self-observation is worth a milestone right now. Option 2 is the only path
that advances trading capability, but it is the market-data track under
another name and should be started deliberately as that, not as an autonomy
milestone.

## Enforcement

No new tests are added by this analysis. Silent expansion of auto-offline
execution is already prevented by the V5.48 invariants, which pin
`AUTONOMY_EXECUTOR_ALLOWLIST` to exactly the two readiness tokens mapped to
`("crypto-readiness-replay",)` and enforce exact two-way
producer/classification/allowlist closure. Any future attempt to add an
auto-offline action must change those pinned sets deliberately, at which
point criterion 1 above should be demanded as evidence.

## Next Action

Operator decision between options 1, 2, and 3. No implementation is
authorized by this document.
