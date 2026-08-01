# V5.70 Frozen V5.64 Forward Data Admission Receipt

## Boundary

This metadata-only receipt was created after the preregistered read-only Tiingo
fetch and before computing or inspecting any V5.70 return, target, trade,
contribution, ranking, or gate outcome. It admits one exact deterministic input
for the protocol in `docs/design/v5_70_v564_frozen_forward_confirmation.md`.

## Acquisition safety

- Network operation: twelve sequential HTTPS GETs to the adapter's exact
  `api.tiingo.com/tiingo/daily/{approved_symbol}/prices` allowlist.
- Credential provider: the trusted adapter loaded only `TIINGO_API_KEY` from
  the primary checkout's existing `.env`.
- Credential value printed: false.
- Credential value written: false.
- Broker credential lookup/access/mutation: false.
- Paper mutation: false.
- Live trading: false.

## Provenance and semantics

- Provider: Tiingo EOD.
- Request range: 2019-01-02 through 2026-06-30.
- Canonical field: `adjusted_close`, sourced from `adjClose`.
- Adjustment semantics: split/dividend-adjusted EOD price.
- Adjusted OHLCV claimed: false.
- Session reference: observed Tiingo SPY EOD dates.
- Independent exchange-calendar claim: false.
- Symbol set: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B,
  COST, SPY.
- BRK-B mapping: `BRK-B->BRK-B`.
- Valid symbols: 12.
- Blocked symbols: 0.

## Exact admitted coverage

- First common session: 2019-01-02.
- Last common session: 2026-06-30.
- Common session count: 1,883.
- Combined row count: 22,596.
- First forward session: 2025-03-31.
- Last forward session: 2026-06-30.
- Forward session count: 314.
- Fold 1 session count: 106.
- Fold 2 session count: 105.
- Fold 3 session count: 103.
- Folds cover every forward session exactly once: true.
- Historical row count matches frozen V5.63 prefix: true.
- Historical adjusted-close mismatches through 2025-03-28: 0.

## Admitted hashes

- Combined canonical CSV:
  `04344d4a60702dd936b183b20937a41b7f90e6813096a9120fc3b2e642d91688`.
- Canonical data manifest:
  `43ae5c6bdd5c6addc2bd7e3d863818229748cad5d0b28f3cad569676340cb1ca`.
- AAPL canonical CSV:
  `a7201c601979822b21bf2bcf60a8e2a2d4b13de1e4f9c6fa9f660dcb4fca362d`.
- MSFT canonical CSV:
  `fc617a5cb344cf8f83ebfae18a7483382eabba5ef1bef24ce2fa12f070c7b211`.
- GOOGL canonical CSV:
  `f0f05cb3af4e1307d00e5428cec2f813b42d24ee9420048ab44f9786aeb803c0`.
- AMZN canonical CSV:
  `fc3b354adcc891bc2dc0e50891a76ffe3973e2ff293418c929b2e55e8be21e03`.
- META canonical CSV:
  `f8ce9dacb47509a45350c1a71c05d81a1b1dc9542261a3e8ce1e5bc4345e6335`.
- NVDA canonical CSV:
  `35482ab85de71139aedcee327a5cff35ae765e05a46c44265fdad64d1cfd9ad7`.
- TSLA canonical CSV:
  `56f47d50a804eb127a5c22b7a719cd5e68f2cdf24d70e6055095c15f006a3a9f`.
- GS canonical CSV:
  `42404f02fcfda51a255442f0d0030121ba14898440fa0124e503149ea5513c4f`.
- JPM canonical CSV:
  `fe741fbe896ff5523a7de236484861894d01c100db34acff495e878a93d65d5e`.
- BRK-B canonical CSV:
  `8c8541ddee67fafa047fc63e3a8025c514668f5189137af146059c18849699c1`.
- COST canonical CSV:
  `2931df4253d712d63f4eb00ffc90e1bf0e298829c1b5db8017dc46891ca818ee`.
- SPY canonical CSV:
  `5626ba381d8c2a9026f47a6a1f9b76bae44778a891bd02afa2d251cfc6bc37cf`.

## Outcome exclusion

No price value, return, target, fill, trade, contribution, metric, comparison,
ranking, or gate outcome was inspected or recorded in this receipt. The next
step may implement and run only the exact V5.70 frozen confirmation.
