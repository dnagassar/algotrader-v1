# V5.87 Keller flexible asset allocation data receipt

## Admission and supersession

This corrected nine-symbol panel supersedes the unscored SPY/DBC availability
proxy snapshot committed in ed6681f. Late primary-source verification identified
the paper's explicit VTI/GSG ETF mapping. Protocol correction b353509 and the
tested allowlist commit e0e003b preceded both exact authenticated requests. No
V5.87 engine outcome, return, factor rank, metric, gate, or route existed
before this corrected admission.

- Corrected protocol SHA-256:
  e6c4de107bb23a00287c495cbd8585de5ef83551aec8801b4a670ce8121a15db.
- Corrected outcome-blind manifest SHA-256:
  a639488f3798db02896ef7807002771e77cd9b497d53a5f770df1ca2e5e47d01.
- Corrected combined canonical SHA-256:
  5094981d3c24aa6d018123b6aad20ce9e70583ed09ff6df23778c64ec65c2502.
- The earlier manifest/data hashes are revoked for V5.87 computation.

## Provenance and semantics

- Provider: authenticated Tiingo End-of-Day GET-only HTTPS API.
- Field: adjClose normalized to adjusted_close.
- Semantics: provider split- and dividend-adjusted closing price.
- Candidate identity mappings: VTI,VEA,VWO,SHY,BND,GSG,VNQ.
- Baseline identity mappings: SPY,IEF.
- Existing VEA,VWO,SHY,BND,VNQ,SPY,IEF evidence is pinned to the V5.72,
  V5.74, and V5.75 receipts.
- VTI and GSG were each requested exactly once for 2007-07-26 through
  2026-07-31 using the destination-allowlisted adapter and the secure existing
  Tiingo .env loader.
- Manual bars, hand normalization, synthetic histories, broker data, alternate
  providers, symbol substitutes, adjusted-OHLCV claims, point-in-time-vintage
  claims, and executable-price claims: none.

New acquisition evidence:

| Symbol | Rows | Canonical SHA-256 | Raw SHA-256 | Refresh-manifest SHA-256 |
| --- | ---: | --- | --- | --- |
| VTI | 4,784 | e8af3a7ea965e72861210be889b390b046684c1f82fff14f94274b453df1af47 | 061fb27a600247a62fd4e1fc82668b82195acd08e59ff8968f80435c73cea073 | d4e16d8830f0c9776e5601bdcd8c1973d711e369aa0372261e335ddf08d185ab |
| GSG | 4,784 | 07526ff3446ff63a5cf903e5a07857ac8215141495be08dabe6f551f380da87b | d6a2ba99f26dbe50c3d0c1978000605aa5937ea9a3fdf4b71f01f16846e59157 | 7f243f132a16305e44f78a0200e19b8bbf90a56bea17a88b622668a19730e1c4 |

Both receipts report GET only, destination allowlist enforced, exact endpoints,
success, no broker access, and no credential value printed, written, or
recorded.

## Corrected canonical coverage and hashes

All nine symbols contain the identical 4,784 unique common sessions from
2007-07-26 through 2026-07-31. The combined file contains 43,056 rows.

| Symbol | Source-file SHA-256 | Normalized-symbol SHA-256 |
| --- | --- | --- |
| VTI | e8af3a7ea965e72861210be889b390b046684c1f82fff14f94274b453df1af47 | 23a02cba06fedc7578b46cf11d92d61d52b40818f3efef30019cc609f4398bcd |
| VEA | 24d02932eb937d422ed8ec8a9c0642dc85bafcb0e7e85dc270616ffe3041d305 | 1fb3f30816778dc8d7c2e1958632086825db8931ecdae1458fe731d1933d69ae |
| VWO | bf64f49465efdf0e7206022f25a7b1fd7268339055f2163456f156894e9a9b2b | 514daeec6bfc5f2387b111acc774362998a38f259a2e3d4b69637dee19d1e8da |
| SHY | e51bfc3a5088e6d9a12f8694f19d642e0a3725550655045c3e4af6e88b08c764 | e10a40f0624d070ac7442960982b5b7b980b52944dc50990eeaca43a621b54b3 |
| BND | 2d531b6655b8fd06d08ccb8b56b83442235cc503b6763771fe94eacf85676182 | b852b06d5656eed2c4f9a6c0b86f0067b793197aaf416c66b348b807eabfc2ed |
| GSG | 07526ff3446ff63a5cf903e5a07857ac8215141495be08dabe6f551f380da87b | e661ec4eed0e1a6164de51f77f1e15a7efc032bb27e6a5adb5c6ef9e64300d0f |
| VNQ | 3ea541bde00148955b1f5185a0650921b4bf0ef25defc2ce921565d1a3b11d68 | 5e989e8b95f586d9f30a0c2d6c33cf4445841e2c0fcf7de6cf1327967c7485b3 |
| SPY | 5a4d8c0fea3ca879011239067f76c6375012f30835e0d579f329f018176b77e2 | 7970105553ae50b9a5bac6a33a8d9fcb790cbf3c6263ca3ee92956a4f1e81e4e |
| IEF | 091989173cb245146cfa2ffb88dcdf3e4f728a4e2ab753e191221b518596e56f | 77a65cb0a46e569de42c40ac0a70621e4105980ef0548c75a4c1554f43268388 |

Missing, duplicate, invalid, nonpositive, stale, substituted, or
session-mismatched rows: none.

## Frozen chronology

| Window | Sessions | First | Last |
| --- | ---: | --- | --- |
| warm-up/reference | 1,390 | 2007-07-26 | 2013-01-31 |
| full post-publication OOS | 3,394 | 2013-02-01 | 2026-07-31 |
| fold 1 | 1,112 | 2013-02-01 | 2017-06-30 |
| fold 2 | 1,135 | 2017-07-03 | 2022-01-03 |
| fold 3 | 1,147 | 2022-01-04 | 2026-07-31 |

The folds exactly partition OOS. Warm-up exceeds four calendar months. The
January 31, 2013 signal supplies the first adjusted-close action on February 1.
No outcome or candidate rank was computed.

## Credential, network, and safety

- Writer-worktree .env: false; primary-checkout .env: true.
- Ambient paper/live profile and broker credential aliases: false/zero.
- Trusted adapter loaded only TIINGO_API_KEY for each of two sequential GETs.
- Credential value requested from operator, printed, returned, persisted, or
  put in a command/artifact: false.
- Network: exactly two allowlisted Tiingo HTTPS GETs.
- Broker/account/order/position access, broker mutation, paper mutation,
  NexusTrade mutation, and live activity: false.
- Candidate metrics or ranking performed: false.

Generated evidence remains ignored under
runs/v5_87_keller_flexible_asset_allocation and contains no credential value.

## Computation gate

The engine must pin this corrected receipt, corrected protocol, corrected
combined file, and corrected manifest. Any use of the superseded SPY/DBC
snapshot, a hash mismatch, chronology mismatch, or causal-lag failure blocks.