# V5.92 vault volatility-managed triage data receipt

Status: outcome-blind. Written after acquisition and admission but before any
per-market target, return, metric, gate, count, or route was computed.

## Vault eligibility

All eighteen symbols were confirmed vault-eligible by
`algotrader.research.forward_shadow_vault` before the protocol was frozen. At
that scan the repository had touched 73 distinct symbols — 55 historically plus
the 18 spent by V5.91 — and none of the eighteen below were among them. These
are the last untouched single-country equity markets in the scanned candidate
set.

## Acquisition

- Provider: authenticated Tiingo End-of-Day, free tier, GET-only through the
  destination-allowlisted adapter.
- Field: `adjClose` normalized to `adjusted_close`; identity mappings only.
- Requests: eighteen, one per symbol, each requesting `2000-01-03` through
  `2026-07-31`.
- Every request returned `http_outcome_category=success` and
  `refresh_state=accepted_adjusted_spy_data_refresh`.
- All eighteen receipts record `token_value_recorded`,
  `market_data_token_value_printed`, and `market_data_token_value_written` as
  `false`; broker, account, order, position, paper-mutation, and live fields are
  `false`.

## Admitted panel

Launch dates span 2000 to 2012, so the intersection — not the request — defines
the scored window. INDA (2012-02-03) is the binding constraint.

- Common sessions: 3643, `2012-02-03` through
  `2026-07-31`.
- Frozen minimum required: 3000. Satisfied.
- Combined rows: 65574.
- Combined canonical CSV SHA-256:
  `9adafdd074bb93850204d0cd51f37eaae9a551ad50eb8f43c98440d2745a87ca`.
- Frozen protocol pin SHA-256: `156a609fde58a25dec43fa539edb7d9156079b28505f10a167daff7f416eea62`.

| Symbol | Rows acquired | First bar | Canonical SHA-256 |
| --- | ---: | --- | --- |
| `ARGT` | 3876 | 2011-03-03 | `a5ab7f01e4577a96…` |
| `ECH` | 4702 | 2007-11-20 | `17df5d176b3daa24…` |
| `EDEN` | 3649 | 2012-01-26 | `2d54ff18e495cdde…` |
| `EFNL` | 3649 | 2012-01-26 | `10d413a1202fe9ae…` |
| `EIDO` | 4083 | 2010-05-07 | `ed9ea34c39ef0ce2…` |
| `EIRL` | 4081 | 2010-05-11 | `24743db9c151b54e…` |
| `EIS` | 4615 | 2008-03-28 | `02c103b33bf1e37e…` |
| `ENZL` | 4001 | 2010-09-02 | `e3d5b22ecdbad0bb…` |
| `EPHE` | 3983 | 2010-09-29 | `0244f9c44e7876fb…` |
| `EPOL` | 4070 | 2010-05-26 | `8a49cecedfb3e3cf…` |
| `EPU` | 4304 | 2009-06-22 | `abbbc0bdcc614b92…` |
| `EWT` | 6564 | 2000-06-23 | `b25e59b8ca48c27c…` |
| `EZA` | 5907 | 2003-02-07 | `7059826ac2ce34b5…` |
| `GREK` | 3681 | 2011-12-08 | `ba20f8f1656e32c5…` |
| `INDA` | 3643 | 2012-02-03 | `5d061a4f5c180e05…` |
| `NORW` | 4263 | 2009-08-19 | `83d4e0bbd7c45ae8…` |
| `THD` | 4613 | 2008-04-01 | `1cc020d76fb11365…` |
| `TUR` | 4615 | 2008-03-28 | `b9d265e0d53ffcc4…` |

## Structural windows

Derived only from the admitted session grid, before any price-derived quantity
was computed.

- Panel: 3,643 common sessions.
- Warm-up: the first 61 sessions form no signal and are not scored.
- Scored window: 3,582 sessions, `2012-05-02` through `2026-07-31`.
- Monthly decisions per market: 170, `2012-06-01` through `2026-07-01`.
- Total decisions across eighteen markets: 3,060.
- Deterministic second half: 1,791 sessions from `2019-06-17`. This split is the
  midpoint index of the scored window, fixed by session count rather than by a
  date chosen after seeing data.

The entire scored window postdates 2008. Whatever this milestone concludes
cannot be an artifact of the pre-2008 regime that carried V5.91's apparent
edge, because no pre-2008 history exists in this panel.

## Trust

External source and tracker performance figures remain untrusted and control no
gate. Manual bars, hand normalization, synthetic history, back-extension,
broker data, and alternate providers were not used. A pass here is historical
breadth evidence, not validated alpha.
