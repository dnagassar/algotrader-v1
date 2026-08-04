# V5.93 non-equity reversal triage data receipt

Status: outcome-blind. Written after acquisition and admission but before any
per-market target, return, metric, gate, count, or route was computed.

## Vault eligibility

All eighteen symbols were confirmed vault-eligible before the protocol was
frozen. At that scan the repository had touched 91 distinct symbols — 55
historically, plus 18 spent by V5.91 and 18 by V5.92 — and none of the eighteen
below were among them. This is the first triage outside equities.

## Acquisition

- Provider: authenticated Tiingo End-of-Day, free tier, GET-only through the
  destination-allowlisted adapter.
- Field: `adjClose` normalized to `adjusted_close`; identity mappings only.
- Requests: eighteen, one per symbol, each requesting `2005-01-03` through
  `2026-07-31`.
- Every request returned `http_outcome_category=success` and
  `refresh_state=accepted_adjusted_spy_data_refresh`.
- All eighteen receipts record `token_value_recorded`,
  `market_data_token_value_printed`, and `market_data_token_value_written` as
  `false`; broker, account, order, position, paper-mutation, and live fields are
  `false`.

## Admitted panel

Launch dates span 2005 to 2009; IGOV (2009-01-29) is the binding constraint, so
the intersection — not the request — defines the scored window.

- Common sessions: 4403, `2009-01-29` through
  `2026-07-31`.
- Frozen minimum required: 3000. Satisfied.
- Combined rows: 79254.
- Combined canonical CSV SHA-256:
  `953580d614bb3908620786e3fb9e8ee29dcdfab23dcf4cb19c2edaa0f99e1c06`.
- Frozen protocol pin SHA-256: `0cc32975be515949fe64f053cd63e5e1917eb1cd0429fdb6dd31a2e02694cd62`.

| Symbol | Rows acquired | First bar | Canonical SHA-256 |
| --- | ---: | --- | --- |
| `BWX` | 4730 | 2007-10-11 | `042699a781e0e16b…` |
| `DBA` | 4923 | 2007-01-05 | `45c7de2766268e29…` |
| `DBB` | 4923 | 2007-01-05 | `cb7fa9c47a7b26dc…` |
| `DBO` | 4923 | 2007-01-05 | `1a601651c7fc9585…` |
| `EMB` | 4682 | 2007-12-19 | `a1eb2e10eb84da64…` |
| `FXA` | 5056 | 2006-06-26 | `d561996a739ce88d…` |
| `FXB` | 5056 | 2006-06-26 | `db046cfe9fab6a21…` |
| `FXC` | 5056 | 2006-06-26 | `f591310eef6faf05…` |
| `FXE` | 5190 | 2005-12-12 | `abf20d4063fcdbb7…` |
| `FXF` | 5056 | 2006-06-26 | `175014bc4056951d…` |
| `FXY` | 4897 | 2007-02-13 | `3599044ae965742d…` |
| `IGOV` | 4403 | 2009-01-29 | `3172d644a5ba4028…` |
| `MBB` | 4875 | 2007-03-16 | `c850b272babca0a1…` |
| `MUB` | 4746 | 2007-09-10 | `3fc088973a9e6bd3…` |
| `PFF` | 4865 | 2007-03-30 | `cfb5c926d365725b…` |
| `SLV` | 5096 | 2006-04-28 | `9dc82da862adbc04…` |
| `UNG` | 4853 | 2007-04-18 | `0d7efb37f2715024…` |
| `USO` | 5109 | 2006-04-10 | `34dcf78f72dc4586…` |

## Structural windows

- Panel: 4,403 common sessions.
- Warm-up: the first 22 sessions form no signal and are not scored.
- Scored window: 4,381 sessions, `2009-03-03` through `2026-07-31`.
- Monthly decisions per market: 208, `2009-04-01` through `2026-07-01`.
- Total decisions across eighteen markets: 3,744.
- Deterministic second half: 2,191 sessions from `2017-11-09`, fixed by
  midpoint index rather than by a date chosen after seeing data.

## Instrument note

These are commodity-, currency-, and credit-tracking ETFs carrying roll and
financing costs; they are not the spot assets they reference. `USO` and `UNG` in
particular are structurally eroded by contango. That is a property of the
tradable instrument, which is what a tradable rule must be judged on, and no
attempt is made to model an untradable underlying instead.

## Trust

External performance figures remain untrusted and control no gate. Manual bars,
hand normalization, synthetic history, back-extension, broker data, and
alternate providers were not used. A pass here is historical breadth evidence,
not validated alpha.
