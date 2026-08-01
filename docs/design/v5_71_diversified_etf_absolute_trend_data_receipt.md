# V5.71 Diversified ETF Absolute-Trend Data Receipt

## Admission decision

The isolated five-ETF Tiingo EOD snapshot is admitted for the exact V5.71
preregistered replay. This receipt records metadata only. It was prepared
without computing or inspecting a strategy return, target, trade, contribution,
metric, rank, gate, or route.

The outcome-blind protocol was committed first as `8958102` and has SHA-256
`afa4254ceac06f643fd51fd2df63364ce14a38f01ba8392e664d8e478bc57d17`.

## Provider and adjustment semantics

- Provider: authenticated Tiingo EOD read-only HTTPS API.
- Provider field: `adjClose` normalized to `adjusted_close`.
- Basis label: `adjusted_close_price_return`.
- Semantics admitted: Tiingo split/dividend-adjusted close under the existing
  repository adapter contract.
- Non-claims: adjusted OHLCV, executable fills, a point-in-time corporate-
  action vintage, and a separately constructed total-return series are not
  claimed.
- Requested and admitted dates: `2004-11-18` through `2026-07-31` inclusive.
- Symbol mapping is deterministic identity mapping for all five symbols.
- No manual CSV, hand-normalized observation, substitute, synthetic bar, or
  alternate provider was used.

## Canonical artifacts

- Combined canonical row count: `27,290`.
- Combined canonical SHA-256:
  `5e7a7da8519e37faa72787dc41c7e847e5749f74f9cd43dc8009cb2807b8e0ec`.
- Canonical manifest SHA-256:
  `627119a769e38053c32ab7709f88672ab6dba5db9725cb4b2545a7bad77b177e`.
- Common observed sessions: `5,458`.
- Common first session: `2004-11-18`.
- Common last session: `2026-07-31`.
- Valid symbols: `SPY,QQQ,IWM,TLT,GLD`.
- Missing, invalid, stale, or refresh-required symbols: none.

| Symbol | Rows | First | Last | Canonical SHA-256 |
| --- | ---: | --- | --- | --- |
| SPY | 5,458 | 2004-11-18 | 2026-07-31 | `9ba2d58f5c1c58096fd473eaad1ea370e6023c63b524a21d286e4d5effaef5fb` |
| QQQ | 5,458 | 2004-11-18 | 2026-07-31 | `8347790292da6048d954fec5276a2c80f6d4dbbfab1458c2cca3b41deb5d3713` |
| IWM | 5,458 | 2004-11-18 | 2026-07-31 | `30fcd9f37609089337a4454ca248d097851179e8fa646489af10b132746fae7d` |
| TLT | 5,458 | 2004-11-18 | 2026-07-31 | `5ce0e67de4c1be5e5e85b292444bc5aac0ce937587a7fc60ca00e402f67dbfae` |
| GLD | 5,458 | 2004-11-18 | 2026-07-31 | `1986eef43145ea6ae1f51cbc7decfb9d711bd740b18d207bd6ecc50a4e86f88e` |

## Chronology coverage

The common-session intersection covers every frozen window exactly:

| Window | Sessions | First | Last |
| --- | ---: | --- | --- |
| Warm-up | 198 | 2004-11-18 | 2005-08-31 |
| Training | 2,601 | 2005-09-01 | 2015-12-31 |
| Full OOS | 2,659 | 2016-01-04 | 2026-07-31 |
| OOS fold 1 | 878 | 2016-01-04 | 2019-06-28 |
| OOS fold 2 | 884 | 2019-07-01 | 2022-12-30 |
| OOS fold 3 | 897 | 2023-01-03 | 2026-07-31 |

The three folds total `2,659` sessions and exactly partition full OOS. The
snapshot includes 198 common warm-up sessions and ten required month-end
observations through `2005-08-31`.

These bytes are newly acquired into an isolated V5.71 path after protocol
commit. Some underlying historical market dates may have appeared in older,
different repository research; V5.71 therefore claims outcome-blind
candidate-specific evaluation, not that every underlying price date was
globally unseen by the repository.

## Credential and network boundary

- Worktree `.env` present: false.
- Primary-checkout `.env` present: true.
- Process Tiingo credential initially loaded: false.
- Process broker or NexusTrade credential initially loaded: false.
- Trusted adapter credential variable loaded: `TIINGO_API_KEY` only.
- Credential value printed: false.
- Credential value written: false.
- Network calls: exactly five sequential allowlisted HTTPS `GET` requests to
  `api.tiingo.com/tiingo/daily/{approved_symbol}/prices`.
- Broker credential lookup, broker/account/order/position access, and broker
  mutation: false.
- Paper submit or other paper mutation: false.
- NexusTrade access or mutation: false.
- Live trading or live-capital activity: false.

The raw provider responses, canonical CSVs, and manifest remain ignored
generated state under `runs/v5_71_diversified_etf_absolute_trend/`; they are
not authority and contain no credential value.

## Result-computation gate

The replay may proceed only after this receipt and the required manifest CLI
override correction are committed. The engine must pin the protocol, receipt,
combined canonical, manifest, and per-symbol hashes above before reading
prices. A mismatch produces `blocked`, never a performance route.
