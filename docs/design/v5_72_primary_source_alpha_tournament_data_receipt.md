# V5.72 primary-source alpha tournament data receipt

## Admission decision

The exact V5.72 14-ETF Tiingo EOD adjusted-close snapshot is admitted. This
receipt was prepared after the protocol commit `f049e9c` and before a candidate
engine existed or any candidate return, metric, ranking, gate, or route was
computed or inspected.

- Frozen protocol SHA-256:
  `eb3061e74f5444746d19480fc9283f3189b86ebb395369e9ee19a33f3dd8d768`.
- Outcome-blind data-manifest SHA-256:
  `82c1edc7192b9f63b057a4846a0d0540958d9939f6dbabddd793899ca797f0ab`.
- Combined canonical SHA-256:
  `5a4d8c0fea3ca879011239067f76c6375012f30835e0d579f329f018176b77e2`.

## Provider, field, and adjustment semantics

- Provider: authenticated Tiingo End-of-Day read-only HTTPS API.
- Authoritative documentation:
  <https://www.tiingo.com/documentation/end-of-day>.
- Provider field: `adjClose`, normalized to `adjusted_close`.
- Admitted semantics: provider split- and dividend-adjusted closing price.
- Deterministic provider mapping: identity for every admitted symbol.
- Non-claims: adjusted OHLCV, an executable market-on-close fill, intraday
  timing, a point-in-time corporate-action vintage, or a survivorship-free
  stock constituent history.
- No manual CSV placement, hand normalization, synthetic observation, broker
  data, or substitute provider was used.

## Canonical coverage

- Symbols: `SPY,QQQ,IWM,TLT,GLD,XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY`.
- Exact common first session: `2004-11-18`.
- Exact common last session: `2026-07-31`.
- Common observed sessions per symbol: `5,458`.
- Combined rows: `76,412`.
- Duplicate, missing, invalid, nonpositive, stale, or mismatched-session
  symbols: none.

The previously admitted V5.71 five-ETF combined file and manifest were reused
only after exact SHA validation:

- prior combined SHA:
  `5e7a7da8519e37faa72787dc41c7e847e5749f74f9cd43dc8009cb2807b8e0ec`;
- prior manifest SHA:
  `627119a769e38053c32ab7709f88672ab6dba5db9725cb4b2545a7bad77b177e`.

The nine sector histories were newly acquired after the protocol commit.

| Symbol | Rows | First | Last | Source-file SHA-256 | Normalized-symbol SHA-256 |
| --- | ---: | --- | --- | --- | --- |
| SPY | 5,458 | 2004-11-18 | 2026-07-31 | `5e7a7da8519e37faa72787dc41c7e847e5749f74f9cd43dc8009cb2807b8e0ec` | `ac5fc6752e7aedd8e922782dbd780e53cbac52a0fb8a38f50742e6c803a31a77` |
| QQQ | 5,458 | 2004-11-18 | 2026-07-31 | `5e7a7da8519e37faa72787dc41c7e847e5749f74f9cd43dc8009cb2807b8e0ec` | `ade7fc4e14865cd68f78ccb3e12a06a00a1de705b28a0cc3a65bc80aca794b65` |
| IWM | 5,458 | 2004-11-18 | 2026-07-31 | `5e7a7da8519e37faa72787dc41c7e847e5749f74f9cd43dc8009cb2807b8e0ec` | `af6f2113ebd39e7253a3fe66940d3add604b3addec0791958250ebb8888dc328` |
| TLT | 5,458 | 2004-11-18 | 2026-07-31 | `5e7a7da8519e37faa72787dc41c7e847e5749f74f9cd43dc8009cb2807b8e0ec` | `8af91ca3b15463ad0c547abce5c02e2a9410bddf81b9a59421e4c5b6d7bb6864` |
| GLD | 5,458 | 2004-11-18 | 2026-07-31 | `5e7a7da8519e37faa72787dc41c7e847e5749f74f9cd43dc8009cb2807b8e0ec` | `71d930e59e63e84de37285af5e3ec3598969061c45f7c960ddb45c5980127bdb` |
| XLB | 5,458 | 2004-11-18 | 2026-07-31 | `5e58ca8d8cd60a7f70c39692aef14c2fa4971af1ef8223352e0d6f33eaf0012a` | `79c40509560211bec89de08d6558dda0d7d91613be7c9221af19d4752f332fa2` |
| XLE | 5,458 | 2004-11-18 | 2026-07-31 | `d8ede30bb4f2686e3cd3b0679f4e3bf97af7a124b2cc1b76d993bb15ff8985eb` | `6f5ddb915999d0cbe02e7e6430f537e3f2fb970582dae1de22f48ca2b90062ef` |
| XLF | 5,458 | 2004-11-18 | 2026-07-31 | `c462b4afebb8ff4f40cdab0083dc04293c770f0acdd5ac6b59bfb4c60143f1da` | `0e99d9c9b968892227b54b6dc3410c16c723dabb0e163088a0e0c91c5942d4b7` |
| XLI | 5,458 | 2004-11-18 | 2026-07-31 | `0206d10f5e051f2a93bb8de0860b57148f6555d3160c6c7f1c9b36dccacd3414` | `e06a357ca77f74bf9558633ee6348f8b46c5d57a0d90ba5c7a2940ee33b1c9e6` |
| XLK | 5,458 | 2004-11-18 | 2026-07-31 | `c578d45b723ca8c05fcfcd2da966b7cbda481cf49a85c2137f9e426817e1b3b6` | `78abb4d2099027176c4416a314d27793bf956999e5db5310016f6bf08983bf56` |
| XLP | 5,458 | 2004-11-18 | 2026-07-31 | `7151e36fde89c2239c71f4fc804e7099f785682967d874db28b43d4bae87de8f` | `3812afb938b5c8a068e69d48f09a636ae5ae9341d2408de5a7c04c995bc3ff0f` |
| XLU | 5,458 | 2004-11-18 | 2026-07-31 | `91079bf5530a3f413cda61bd9ecffe88fee08ae0f7b172b180f5a1b1ed2dfa92` | `71550d3b4b59f92ddb525ba28f118c949bfcb4ce6e8dd1f920fd7b91796e4035` |
| XLV | 5,458 | 2004-11-18 | 2026-07-31 | `6090ca7c438ec111fa2300c99859f9a1e305a77d7273cd233a1894d4f473f91c` | `5d4b57b413495107a2fef1cbddc6808f6c0c8176c2ea0a4bc50035be60e4bc42` |
| XLY | 5,458 | 2004-11-18 | 2026-07-31 | `077fd7ee5df8aa1f71bc941ae31952b7a8a04ada0a4b844ad6a2a194ad311dd2` | `e7d1929a5f66985733bdb966d4d5071c3737a1b07298d8bb4d17e04438f5b582` |

## Frozen chronology coverage

| Window | Sessions | First | Last |
| --- | ---: | --- | --- |
| reference and warm-up | 1,037 | 2004-11-18 | 2008-12-31 |
| full OOS | 4,421 | 2009-01-02 | 2026-07-31 |
| fold 1 | 1,510 | 2009-01-02 | 2014-12-31 |
| fold 2 | 1,511 | 2015-01-02 | 2020-12-31 |
| fold 3 | 1,400 | 2021-01-04 | 2026-07-31 |
| recent turn-of-month check | 647 | 2024-01-02 | 2026-07-31 |

The folds are nonoverlapping and total exactly 4,421 sessions. Reference data
provide more than the required six complete ranking months plus six formed
cohorts before OOS. No training, fitting, parameter selection, or outcome
selection occurred.

## Credential, network, and safety boundary

- Worktree `.env` present: false.
- Primary-checkout `.env` present: true.
- Process paper profile initially loaded: false.
- Process credential alias initially loaded: false.
- Trusted child-adapter credential loaded: `TIINGO_API_KEY` only.
- Credential value printed or written: false.
- Network operations: exactly nine sequential allowlisted HTTPS `GET` requests
  to `api.tiingo.com/tiingo/daily/{approved_symbol}/prices`.
- Every request reported destination allowlist match true and method `GET`.
- Broker credential lookup, broker/account/order/position access, broker
  mutation, paper mutation, and live activity: false.
- Manifest outcome metrics computed and candidate ranking performed: false.

Raw responses, normalized files, canonical files, and the manifest remain
ignored generated state under `runs/v5_72_primary_source_alpha_tournament/`.
They are data evidence, not authority, and contain no credential value.

## Result-computation gate

The candidate engine may read prices only after this receipt is committed. It
must pin the protocol, this receipt, the combined canonical data, and the
outcome-blind manifest hashes. Any mismatch blocks; it never produces a
performance route.
