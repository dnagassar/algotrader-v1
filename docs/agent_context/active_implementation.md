# Active implementation handoff

## Milestone

V5.68 NexusTrade risk-balanced attribution is implemented and verified. The
result is diagnostic only: it does not create a candidate, route, preview,
shadow, paper action, or live action.

## Checkout and ownership

- Sole implementation writer: current Codex task.
- Branch: `codex/v5.62-nexustrade-source-data-unblock`.
- Takeover HEAD: `1c53ca1a0cce5837fc3ce5645bc8ba664dad88e9`.
- Preregistration commit: `f3f15f41b47f11d7e01d3085b027e628d97f8160`.
- The takeover was clean: no staged, unstaged, or untracked files.
- No reset, clean, stash, restore, rebase, switch, additional worktree, or
  subagent was used.

## Frozen protocol and inputs

- V5.68 protocol:
  `docs/design/v5_68_nexustrade_risk_balanced_attribution.md`
  (`d0d89a0807cf8db41cb7377a40b6af1342625b4ff32fc8e56f53b5f2d9ec5513`).
- V5.64 protocol:
  `f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0`.
- V5.64 engine:
  `66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5`.
- V5.67 protocol:
  `17f86b8eafd7e67e6816603cb1bf06fa96a734c7b7d9094d30e68ec85690505e`.
- V5.67 engine:
  `2c669051c6c3fc877cd86d482579ffa711e7d68724e5dffb117d32080aef1188`.
- V5.67 preregistration/result/summary/manifest:
  `6ee1e62efb4b20f94896b2e29fb022081b6c762f4c7da8de7f67f631bc747d6e`,
  `76de6eabe410c082b53ff123af31dccdf4704f78c3380bd6d6e8e8de24b2276f`,
  `99fac23b5cbeae076bb0249d6741e98ca95a433b11cad994ed92abd2bcf886f1`,
  `0bcf77f91d4b92a9d85f566e0e0c946fc19be4b56bd28982eeb741d23dee1519`.

The implementation validates those hashes and reproduces the frozen V5.67
result before attribution. It also validates 1,000 frozen metric fields and the
eight full-period plus eight OOS target hashes.

## Attribution contract

- `P`: frozen V5.64 parent equal-weight composite.
- `R`: pure inverse-volatility/capped sizing under the parent filled state;
  zero eligible names is cash, one through five names retain the parent's
  equal-weight full exposure, and six or more use the exact V5.67 target.
- `C`: exact V5.67 allocation under the parent filled state.
- `A`: frozen V5.67 actual path under its own filled state.
- Identity: `(R-P) + (C-R) + (A-C) = A-P`.

Return and per-stock gross-contribution identities pass at `1e-24` across all
four costs, training, OOS, and all three OOS folds.

## Decision evidence

Classification: `pure_sizing_primary`.

Moderate-cost full-OOS total returns:

- P: `0.216081928040488296986127071`
- R: `0.118738891463329553781714217`
- C: `0.096781606110768419788213151`
- A: `0.096781606110768419788213151`

The V5.67 harm versus P is `0.119300321929719877197913920`:

- Pure sizing, R-P: `-0.097343036577158743204412854`
  (`0.8159494878354458541175373418` of harm).
- One-to-four-name partial cash, C-R:
  `-0.021957285352561133993501066`
  (`0.1840505121645541458824626582` of harm).
- State carry, A-C: exactly zero.
- Identity residual: exactly zero.

OOS target divergences for R-P, C-R, and A-C are 184, 25, and 0. OOS
post-trade divergences are 185, 24, and 0. The 12 OOS signal dates contain
eight sizing changes and two one-to-four-name cash changes. State carry is
absent. The largest constituent contribution is TSLA, but constituent
attribution is explanatory evidence only and must not drive symbol removal or
tuning.

Decision: close the V5.67 inverse-volatility/capped-sizing lane. Do not tune its
lookback, cap, exposure, symbol set, or state implementation. Do not remove
TSLA or NVDA. Removing only the partial-cash rule could recover at most the
minority cash component and does not repair the primary sizing harm. No further
same-thesis candidate is justified from these inspected outcomes.

## Canonical data

- Provider: Tiingo EOD local import.
- Field: `adjClose` mapped to `adjusted_close`.
- Semantics: split/dividend-adjusted EOD price; adjusted OHLCV is not claimed.
- Symbols: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST,
  and SPY; BRK-B maps deterministically to BRK-B.
- Coverage: 2019-01-02 through 2025-03-28, 1,569 common observed Tiingo SPY
  sessions and 18,828 rows.
- Training: 2021-12-31 through 2024-03-24.
- Untouched OOS boundary: 2024-03-24 through 2025-03-28; first observed OOS
  session 2024-03-25, 254 sessions.
- Canonical CSV hash:
  `d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575`.
- Canonical manifest hash:
  `e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1`.

Sessions are observed Tiingo SPY dates, not a separately certified exchange
calendar. Authentic NexusTrade replay remains hard-gated by candidate-specific
historical bar mode, slippage, and 365-day clock semantics. External source
metrics remain untrusted; the 29.64% table versus 29.41% chart discrepancy is
preserved and unused.

## Generated artifacts

Ignored output root:
`runs/v5_68_nexustrade_risk_balanced_attribution`.

- `preregistration.json`:
  `e8f68e5acaba46379bc9b7dab873566419d5128bff1423ae40a74dcddaab9e8d`
- `attribution_results.json`:
  `1c96d6aed415ce6f57b48122a2ec445a45c901e72d0f0e1ab0865a2ad5039b27`
- `attribution_summary.md`:
  `9ef1781f72b99806a316a0d5b7c14df9702a51f644612502478ed5d9fa469992`
- `manifest.json`:
  `dfbe570bd8a1c33388ff970eca5a0af7a544aabbd14817ad764da3fdfffb2856`

A second canonical replay was byte-identical.

## Verification

- Focused non-canonical tests: 7 passed, 1 deselected.
- Canonical full attribution: 1 passed, 7 deselected.
- V5.68/V5.67/V5.64 plus dependency/import tests: 75 passed.
- `scripts/verify_offline.ps1 -Full -Shards 4`: PASS.
  - guards: 109 passed
  - canonical collection: 10,216 node IDs across 509 files
  - execution: 10,211 passed, 5 skipped, 0 failures, 0 errors
  - collection and execution equivalence: PASS

## Safety and credentials

Preflight process booleans were all false for paper/live profile, Alpaca/APCA
credential aliases and endpoint aliases, Tiingo aliases, and NexusTrade
aliases. No credential value was read, printed, persisted, or placed in a
command or artifact. No network, NexusTrade mutation, broker/account/order/
position access, paper mutation, receipt, reconciliation, or live activity
occurred. Reconciliation and broker receipts are not applicable.

V5.57 sleeve ownership and safeguards are unchanged: $25 entry-order notional,
$60 aggregate marked SPY entry exposure, one broker order per secure cycle,
and two sleeve intents per UTC day. No third sleeve exists. Live remains
unauthorized.

## Tracked slice

- `docs/design/v5_68_nexustrade_risk_balanced_attribution.md`
  (already committed in the preregistration commit)
- `docs/OPERATOR_RUNBOOK.md`
- `docs/agent_context/active_implementation.md`
- `docs/deterministic_core.md`
- `scripts/run_nexustrade_risk_balanced_attribution.ps1`
- `src/algotrader/research/nexustrade_risk_balanced_attribution.py`
- `tests/unit/test_nexustrade_risk_balanced_attribution.py`

## Next milestone

Do not advance another risk-balanced variant from V5.67 outcomes. A future
research milestone requires a genuinely independent thesis and a fresh,
outcome-blind preregistration before implementation or result inspection. The
authentic NexusTrade lane remains gated on the three missing candidate-specific
source semantics above.
