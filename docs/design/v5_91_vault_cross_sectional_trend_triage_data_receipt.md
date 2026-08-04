# V5.91 vault cross-sectional trend triage data receipt

Status: outcome-blind. Written after acquisition and admission but before any
per-market target, return, metric, gate, count, or route was computed. No
performance quantity appears here.

## Vault eligibility

Every symbol below was confirmed vault-eligible by
`algotrader.research.forward_shadow_vault` **before** the protocol was frozen:
no acquisition receipt, canonical artifact, or data manifest in this repository
referenced any of them. EWJ was excluded because the same scan flagged it as
already acquired during V5.88. At scan time the repository had touched 55
distinct symbols; none of the eighteen below were among them.

## Acquisition

- Provider: authenticated Tiingo End-of-Day, free tier, through the
  repository's GET-only destination-allowlisted adapter.
- Field: `adjClose` normalized to `adjusted_close`; provider split- and
  dividend-adjusted close only. Not an executable price.
- Requests: eighteen, one per symbol, each requesting `1996-04-01` through
  `2026-07-31`, identity symbol mappings only.
- Every request returned `http_outcome_category=success` and
  `refresh_state=accepted_adjusted_spy_data_refresh`.
- Credential handling: only `TIINGO_API_KEY` was loaded, inside the trusted
  adapter boundary, from a dotenv outside this checkout. All eighteen receipts
  record `token_value_recorded`, `market_data_token_value_printed`, and
  `market_data_token_value_written` as `false`.
- Broker, account, order, position, paper-mutation, and live fields are `false`
  in all eighteen receipts.

## Admitted panel

Launch dates differ across the universe, so the request window is not the
scored window. Sixteen markets carry history from 1996-04-01; EWY begins
2000-05-12 and EWZ begins 2000-07-14. The admitted panel is therefore the exact
common-session intersection, as the frozen protocol requires.

- Common sessions: 6550, `2000-07-14` through
  `2026-07-31`.
- Frozen minimum required: 5000 sessions. Satisfied.
- Combined rows: 117900.
- Combined canonical CSV SHA-256:
  `af28aa4d21084d62b0936b5127a8e43624482bea2c511db7cdafb8d25c637ca6`.
- Frozen protocol pin SHA-256:
  `a1d9c90face12c565dc2b434aaa8ad5ea59754fec29c90bba761279a72938f12`.

| Symbol | Rows requested | First bar | Canonical SHA-256 | Raw response SHA-256 |
| --- | ---: | --- | --- | --- |
| `EWA` | 7632 | 1996-04-01 | `3806bd46e9112c01…` | `52184f8718fba5d9…` |
| `EWC` | 7632 | 1996-04-01 | `f25f2b0b966b0cec…` | `0ed3aeff913efb07…` |
| `EWD` | 7632 | 1996-04-01 | `b936eff6dbc89583…` | `bf4ceaae744aafcd…` |
| `EWG` | 7632 | 1996-04-01 | `1569eee127b3feb6…` | `91571fbb8c1c5c5f…` |
| `EWH` | 7632 | 1996-04-01 | `57be6eb6b7b2f9aa…` | `629bdf0400b7b090…` |
| `EWI` | 7632 | 1996-04-01 | `41a415e11223bc33…` | `a481551b1a2eb884…` |
| `EWK` | 7632 | 1996-04-01 | `c383942fd5a493ab…` | `9585a66d6d0808ce…` |
| `EWL` | 7632 | 1996-04-01 | `9715b8025a4323cd…` | `15c11e788d9fb43a…` |
| `EWM` | 7632 | 1996-04-01 | `8e6081789bb3d71c…` | `37372407e8d4bb2b…` |
| `EWN` | 7632 | 1996-04-01 | `57595d0e1abd16b6…` | `1ce9a9730a4399f7…` |
| `EWO` | 7632 | 1996-04-01 | `62ab8d06b52611ea…` | `c388542d9d48b113…` |
| `EWP` | 7632 | 1996-04-01 | `d61660a1b62f04d4…` | `d953bfa48661e8bc…` |
| `EWQ` | 7632 | 1996-04-01 | `c0568972157336f4…` | `9ffbd3871dac546c…` |
| `EWS` | 7632 | 1996-04-01 | `e17afbe5f6f35560…` | `86d36dc7853f4b2b…` |
| `EWU` | 7632 | 1996-04-01 | `12e0131c0d31daca…` | `ebb5773fa4b3bdc0…` |
| `EWW` | 7632 | 1996-04-01 | `e1070479ca65519c…` | `da5ad4624c55e474…` |
| `EWY` | 6593 | 2000-05-12 | `78ad369d12021615…` | `ba45a0b141dbdfc4…` |
| `EWZ` | 6550 | 2000-07-14 | `d0d971a65e133758…` | `6e119a21fada70fd…` |

## Structural windows

Derived only from the admitted session grid, before any price-derived quantity
was computed.

- Panel: 6,550 common sessions.
- Warm-up: the first 200 sessions form no signal and are not scored.
- Scored window: 6,350 sessions, `2001-05-01` through `2026-07-31`.
- Monthly decisions per market: 303, `2001-05-01` through `2026-07-01`.
- Total decisions across the eighteen markets: 5,454.
- Post-2007 consistency sub-window: 223 decisions per market, beginning
  `2008-01-02`.

For scale, the entire V5.89 milestone rested on 47 decisions in one market, and
a six-month forward shadow of a monthly rule would yield six. Breadth is the
reason this triage exists.

## Trust

External source and tracker performance figures remain untrusted and are not
used for ranking, gates, or promotion. Manual bars, hand normalization,
synthetic history, back-extension, broker data, and alternate providers were
not used. This receipt grants no shadow, paper, broker, or live authority, and
a pass here is a historical breadth result, not validated alpha.
