# V5.87 Keller flexible asset allocation data receipt

## Admission

The exact eight-symbol adjusted-close panel is admitted after protocol commit
3a18c20 and before a V5.87 engine or candidate return, rank, metric, gate, or
route existed.

- Protocol SHA-256:
  298320df3d095b0ae30d81f574e06a4c03bfc4f513e6f82caa0d9d66719e2d90.
- Outcome-blind manifest SHA-256:
  2f00c94c04882e895896f3a725b4b02041a17fe0439802c733a6d8d3a406ad64.
- Combined canonical SHA-256:
  26380bb6fa6576820d7424ada95ac953d2463d4db168ddce50f0d8d6ce6f719b.

## Provenance and semantics

- Provider: authenticated Tiingo End-of-Day evidence already admitted by
  V5.72, V5.74, and V5.75.
- Field: adjClose normalized to adjusted_close.
- Semantics: provider split- and dividend-adjusted closing price.
- Identity mappings: SPY,VEA,VWO,SHY,BND,DBC,VNQ,IEF.
- Source-receipt hashes:
  - V5.72:
    827ed0bdeece4bb373eb29517c2c0cf1dd383a89f64be958d1cf1357e22c807c;
  - V5.74:
    59595161f75c4b5e85a261d281cb722d596f95869e2b943940da010ce925b37f;
  - V5.75:
    5e99265971996f1821f384bb8121a8b8252b73bdef27b3bd9b215bceeff4f2e7.
- Network requests, refreshes, manual bars, hand normalization, synthetic
  histories, broker data, adjusted-OHLCV claims, point-in-time-vintage claims,
  and executable-price claims in V5.87: none.

## Coverage and exact hashes

All eight symbols contain the identical 4,784 unique common sessions from
2007-07-26 through 2026-07-31. The combined file contains 38,272 rows.

| Symbol | Source-file SHA-256 | Normalized-symbol SHA-256 |
| --- | --- | --- |
| SPY | 5a4d8c0fea3ca879011239067f76c6375012f30835e0d579f329f018176b77e2 | 7970105553ae50b9a5bac6a33a8d9fcb790cbf3c6263ca3ee92956a4f1e81e4e |
| VEA | 24d02932eb937d422ed8ec8a9c0642dc85bafcb0e7e85dc270616ffe3041d305 | 1fb3f30816778dc8d7c2e1958632086825db8931ecdae1458fe731d1933d69ae |
| VWO | bf64f49465efdf0e7206022f25a7b1fd7268339055f2163456f156894e9a9b2b | 514daeec6bfc5f2387b111acc774362998a38f259a2e3d4b69637dee19d1e8da |
| SHY | e51bfc3a5088e6d9a12f8694f19d642e0a3725550655045c3e4af6e88b08c764 | e10a40f0624d070ac7442960982b5b7b980b52944dc50990eeaca43a621b54b3 |
| BND | 2d531b6655b8fd06d08ccb8b56b83442235cc503b6763771fe94eacf85676182 | b852b06d5656eed2c4f9a6c0b86f0067b793197aaf416c66b348b807eabfc2ed |
| DBC | 8720fa2256e971ae5004b5fb92d095d699d122fe68d51f37d61a9665cb8054b1 | c362cac1a2875c8e08c63cade28426297e681dcd7ab65882634d72f689e5167e |
| VNQ | 3ea541bde00148955b1f5185a0650921b4bf0ef25defc2ce921565d1a3b11d68 | 5e989e8b95f586d9f30a0c2d6c33cf4445841e2c0fcf7de6cf1327967c7485b3 |
| IEF | 091989173cb245146cfa2ffb88dcdf3e4f728a4e2ab753e191221b518596e56f | 77a65cb0a46e569de42c40ac0a70621e4105980ef0548c75a4c1554f43268388 |

SPY is selected from the pinned V5.72 multi-symbol file; its normalized hash
binds the exact selected series. Missing, duplicate, invalid, nonpositive,
stale, substituted, or session-mismatched rows: none.

## Frozen chronology coverage

| Window | Sessions | First | Last |
| --- | ---: | --- | --- |
| warm-up/reference | 1,390 | 2007-07-26 | 2013-01-31 |
| full post-publication OOS | 3,394 | 2013-02-01 | 2026-07-31 |
| fold 1 | 1,112 | 2013-02-01 | 2017-06-30 |
| fold 2 | 1,135 | 2017-07-03 | 2022-01-03 |
| fold 3 | 1,147 | 2022-01-04 | 2026-07-31 |

The folds are disjoint and total 3,394 sessions. Warm-up exceeds four complete
month-end intervals. The January 31, 2013 month-end signal can supply the exact
first action on February 1. No outcome or candidate rank was computed.

## Safety

- Paper/live profile loaded during assembly: false.
- Broker credential alias loaded: false.
- Tiingo credential loaded or accessed during V5.87 assembly: false.
- Network, broker/account/order/position access, broker mutation, paper
  mutation, NexusTrade mutation, and live activity: false.
- Candidate outcome metrics computed or candidate ranking performed: false.

Generated canonical and manifest bytes remain ignored under
runs/v5_87_keller_flexible_asset_allocation. They contain no credentials and
are evidence, not authority.

## Computation gate

The V5.87 engine must pin this receipt, protocol, combined file, and manifest
before reading prices; validate exact daily/session/window identities; and
prove the monthly causal lag before any result. A mismatch blocks.