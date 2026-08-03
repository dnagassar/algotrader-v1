# V5.88 Butler Exhibit 3/4 source-family data receipt

## Admission boundary

This outcome-blind receipt admits the exact ten-ETF universe disclosed by the
author for the Adaptive Asset Allocation research implementation, plus SPY as
the preregistered external baseline. The data-admission implementation and its
tests were committed at b4d6aee before this combined panel was built. No
candidate return, rank, metric, gate, or route was computed during acquisition
or admission.

- Frozen protocol v2 SHA-256:
  fecab8bc4233afc71fd95324c913a0380b72607e14232f2e20663327b27fa0ff.
- Outcome-blind manifest SHA-256:
  58a9efafd610db5ba11272d32dac4cc9fe8681be8a832a8a3b89fd320cc81b56.
- Combined canonical panel SHA-256:
  157c1b2ba18e440730c65e38173ab836aeb8805806a1ecbb45be28b6d90206d0.

## Provenance and semantics

- Provider: authenticated Tiingo End-of-Day HTTPS API.
- Network method for the five newly required histories: GET only.
- Provider field: adjClose, normalized to adjusted_close.
- Semantics: provider split- and dividend-adjusted closing price.
- Exact candidate identity mappings:
  DBC,EEM,EWJ,GLD,ICF,IEF,RWX,TLT,VGK,VTI.
- Baseline identity mapping: SPY; IEF is also reused by the frozen 60/40
  baseline.
- Adjusted OHLCV, point-in-time vintage, and executable-price claims: false.
- Manual bars, hand normalization, synthetic histories, broker data, alternate
  providers, symbol substitutes, and inferred source execution assumptions:
  none.

Five candidate-specific histories were requested once each for the exact
2007-07-26..2026-07-31 contract:

| Symbol | Rows | Canonical SHA-256 | Raw-response SHA-256 | Refresh-log SHA-256 |
| --- | ---: | --- | --- | --- |
| EEM | 4,784 | 91399fabb12e98237f6cf245b8a3212b9f8ed046dfb53b75d44ffd6d712aa698 | 39a28911a912dbf545324760612de123f518b63f6e9e5c77c8bbc93a5c392207 | 513bd730d72960c64220f82faea6ade2590b6269449b76e0a3dc93b15535f0ba |
| EWJ | 4,784 | b6686f3ff8510c80b721a839f2488a656986c705a72c58cfa4c3d41548632eba | 0cfe38bc81f4152d0b3b8da5b8e5b085da93536bc09b50d8a12a27f86c3f3d01 | c7c10f624d27728df9f325de96b765b4faa33b9cf95ad61d576fa1734f4cf9d2 |
| ICF | 4,784 | 87edf99724c815051ce0b5fbeebc69300c18f3f7e2364be9d716bab61020f0c2 | 6aa8dfe2560ae8e6c5a40977b2672221414f7fbdb55141c49ee183c4abb2cfbf | a42bf38ff50abb01176c096c7c778b3fd26ac615950487262c3e4272535e8556 |
| RWX | 4,784 | da397276843490828bb7d0bc1d9a467f84b95f3f4998f3e855eaec19aa6bdc50 | f41ff68985cf50fa4639b20af21804ba2cdfa90431d4d6b629916f1755646554 | 388bc760208c2c150951b35774307ceb3b578e1a3e39a893316f6ee2d75475d6 |
| VGK | 4,784 | 6238676b6bface8c8154ab414d7028ab312a1ac94f23f761f4ecd91e0b6c412f | f368ea42889510781d030c53ea7f48e1127617d98d48335175074e7d9ffca691 | 87cba5e33cf1024c58ed954086d140499d555e6990344d96b6dc965f17e8da0f |

Six existing canonical histories were reused only after exact source-file and
tracked-receipt hash validation:

| Symbols | Prior receipt | Receipt SHA-256 |
| --- | --- | --- |
| GLD, TLT, SPY | v5_71_diversified_etf_absolute_trend_data_receipt.md | ca782882cb499ea2e956fc36658df4f76f88fff06b4a69b293ced4a70c213525 |
| IEF | v5_74_vigilant_asset_allocation_g4_data_receipt.md | 59595161f75c4b5e85a261d281cb722d596f95869e2b943940da010ce925b37f |
| DBC | v5_75_faber_global_relative_strength_data_receipt.md | 5e99265971996f1821f384bb8121a8b8252b73bdef27b3bd9b215bceeff4f2e7 |
| VTI | v5_87_keller_flexible_asset_allocation_data_receipt.md | c338615d6079557b3a5d98dd0414cef7a15f03e06812841af5ddadb63f30fa60 |

## Canonical panel

All eleven symbols have the identical 4,784 unique common sessions from
2007-07-26 through 2026-07-31. The combined panel contains 52,624 data
rows in frozen symbol order.

| Symbol | Source-file SHA-256 | Normalized symbol/date/adjusted-close SHA-256 |
| --- | --- | --- |
| DBC | 8720fa2256e971ae5004b5fb92d095d699d122fe68d51f37d61a9665cb8054b1 | c362cac1a2875c8e08c63cade28426297e681dcd7ab65882634d72f689e5167e |
| EEM | 91399fabb12e98237f6cf245b8a3212b9f8ed046dfb53b75d44ffd6d712aa698 | 05444deb28669180ea03cd1270b5abb963e871929515b237b22c1b4582bf39e1 |
| EWJ | b6686f3ff8510c80b721a839f2488a656986c705a72c58cfa4c3d41548632eba | eb51734695fa65b39f528d839427a707c5c8b55880ab60bd68aa9e6e4f36fc30 |
| GLD | 1986eef43145ea6ae1f51cbc7decfb9d711bd740b18d207bd6ecc50a4e86f88e | c4578a7452b478cd97cf8685d6f7325f3e22e64b4ac3d34d3aac41d0a25caa6e |
| ICF | 87edf99724c815051ce0b5fbeebc69300c18f3f7e2364be9d716bab61020f0c2 | 4b3bf5b36df7f5fa87537f74be97ec27a8667d19b24329f18b1405442c979a06 |
| IEF | 091989173cb245146cfa2ffb88dcdf3e4f728a4e2ab753e191221b518596e56f | 77a65cb0a46e569de42c40ac0a70621e4105980ef0548c75a4c1554f43268388 |
| RWX | da397276843490828bb7d0bc1d9a467f84b95f3f4998f3e855eaec19aa6bdc50 | a958c730740ab6dc690edca2442517284e21fab767701baa5f9af36f10a09f6a |
| TLT | 5ce0e67de4c1be5e5e85b292444bc5aac0ce937587a7fc60ca00e402f67dbfae | 9c5b15dff1c6b234a8d03e21d5216ca0482be432efc4c0c5be1242c3cd60d022 |
| VGK | 6238676b6bface8c8154ab414d7028ab312a1ac94f23f761f4ecd91e0b6c412f | 4eca5a2f1fda35c7733040cb29c6b9fa34222cf36de38f7d8aa3d60aa04f8722 |
| VTI | e8af3a7ea965e72861210be889b390b046684c1f82fff14f94274b453df1af47 | 23a02cba06fedc7578b46cf11d92d61d52b40818f3efef30019cc609f4398bcd |
| SPY | 9ba2d58f5c1c58096fd473eaad1ea370e6023c63b524a21d286e4d5effaef5fb | 7970105553ae50b9a5bac6a33a8d9fcb790cbf3c6263ca3ee92956a4f1e81e4e |

Missing, duplicate, invalid, nonpositive, stale, substituted, or
session-mismatched admitted rows: none.

## Frozen chronology

| Window | Sessions | First | Last |
| --- | ---: | --- | --- |
| warm-up/reference | 1,682 | 2007-07-26 | 2014-03-31 |
| full mapped OOS | 3,102 | 2014-04-01 | 2026-07-31 |
| fold 1 | 1,028 | 2014-04-01 | 2018-04-30 |
| fold 2 | 1,029 | 2018-05-01 | 2022-05-31 |
| fold 3 | 1,045 | 2022-06-01 | 2026-07-31 |

The folds exactly partition OOS. Warm-up exceeds the frozen six-month momentum
and 60-session volatility requirements. There are 148 expected monthly action
sessions split 49/49/50 across the folds. No candidate outcome or ranking was
computed.

## Credentials, network, and safety

- Writer-worktree .env present: false.
- Primary-checkout .env present: true.
- Ambient paper/live profile loaded before offline work: false/false.
- Ambient broker or Tiingo credential alias count before offline tests: zero.
- Trusted child adapter loaded only TIINGO_API_KEY for each of five sequential
  authenticated requests.
- Credential value requested from the operator, printed, returned, logged,
  persisted, or placed in a command/artifact: false.
- Network: exactly five destination-allowlisted Tiingo HTTPS GETs.
- Broker/account/order/position access, broker mutation, paper mutation, and
  live activity: false.
- Candidate metrics, ranking, or promotion performed: false.
- External source performance remains untrusted and cannot control ranking or
  promotion.
- Live authorized: false.

Generated panel and acquisition evidence remain ignored under
runs/v5_88_butler_exhibit3_4_source_family and contain no credential value.

## Computation gate

The replay engine must pin this receipt, protocol v2, combined panel, and
manifest. Any byte drift, chronology mismatch, noncausal signal/action timing,
renormalization of Exhibit 4 residual cash, or replacement of the frozen
translation blocks scoring.