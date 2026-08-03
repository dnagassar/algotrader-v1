# V5.89 Keller Bold Asset Allocation data receipt

Status: outcome-blind. This receipt was written after acquisition and admission
but before any V5.89 candidate target, return, metric, gate, rank, or route was
computed. No performance quantity appears here.

## Acquisition

- Provider: authenticated Tiingo End-of-Day, free tier, through the
  repository's GET-only destination-allowlisted adapter
  (`https://api.tiingo.com/tiingo/daily/{symbol}/prices`).
- Field: `adjClose` normalized to `adjusted_close`; provider split- and
  dividend-adjusted close only. Not an executable price and not adjusted OHLCV.
- Requests: seventeen, one per symbol, each
  `2007-07-26` through `2026-07-31`, identity symbol mappings only.
- Every request returned `http_outcome_category=success` and
  `refresh_state=accepted_adjusted_spy_data_refresh`.
- Credential handling: only `TIINGO_API_KEY` was loaded, inside the trusted
  adapter boundary, from a dotenv outside this checkout. For all seventeen
  receipts `token_value_recorded`, `market_data_token_value_printed`, and
  `market_data_token_value_written` are `false`; the recorded request header is
  `Token <redacted>`.
- Broker, account, order, position, paper-mutation, and live fields are `false`
  in all seventeen receipts.

## Admitted panel

- Symbols, canonical order:
  `SPY,QQQ,IWM,VGK,EWJ,EEM,VNQ,DBC,GLD,TLT,HYG,LQD,EFA,AGG,TIP,BIL,IEF`.
- Every symbol independently returned 4784 rows over the identical
  session sequence, so the common-session intersection is lossless.
- Common sessions: 4784, `2007-07-26` through
  `2026-07-31`.
- Combined rows: 81328.
- Combined canonical CSV SHA-256:
  `a8a2b4ceb6d5aa22001e8967d741e51bb6246985ade55f7ea9fc79b69d677543`.
- Frozen protocol pin SHA-256:
  `b000c85a4ce041a26cfe3eedace3439177456d2507d8a71c08ed8e0740262747`.

| Symbol | Rows | Canonical SHA-256 | Raw response SHA-256 |
| --- | ---: | --- | --- |
| `SPY` | 4784 | `383f2ddcd43d3d585c4d24be417b91776e10b582b41087db86d644e5d7fc9fef` | `e5a78e4ba70ec26502f0cdd4dc94f17d9ef18a8becc94c14ee18ade96f2e96d6` |
| `QQQ` | 4784 | `cd683b96bc2cd6ffb39bfc7ad9ee695268aa530add66f4dcc0040fa1f6e0b0e3` | `18b45d59462789755c23b932f5ecb37821102aa70c122d0a0f59e2a1252aaf9a` |
| `IWM` | 4784 | `c75a4065ce23430cee30ffef8b96da6aeccc70ad8b8f42f9cbaf9771c9fbd549` | `f0af66cf2b8d3778a223211c143fa0a6c119ceda00722bcf0fe71289bf5c391c` |
| `VGK` | 4784 | `6238676b6bface8c8154ab414d7028ab312a1ac94f23f761f4ecd91e0b6c412f` | `f368ea42889510781d030c53ea7f48e1127617d98d48335175074e7d9ffca691` |
| `EWJ` | 4784 | `b6686f3ff8510c80b721a839f2488a656986c705a72c58cfa4c3d41548632eba` | `0cfe38bc81f4152d0b3b8da5b8e5b085da93536bc09b50d8a12a27f86c3f3d01` |
| `EEM` | 4784 | `91399fabb12e98237f6cf245b8a3212b9f8ed046dfb53b75d44ffd6d712aa698` | `39a28911a912dbf545324760612de123f518b63f6e9e5c77c8bbc93a5c392207` |
| `VNQ` | 4784 | `3ea541bde00148955b1f5185a0650921b4bf0ef25defc2ce921565d1a3b11d68` | `73343d14e8286c08a3ed5659abe0337560c56ade922e572bd8961edaed3166d4` |
| `DBC` | 4784 | `8720fa2256e971ae5004b5fb92d095d699d122fe68d51f37d61a9665cb8054b1` | `5476ceb2660b462e77e003ee3a089b1e3e902631eca912b275ada0470ca47128` |
| `GLD` | 4784 | `7fee8321dfa858da976a1da6aeac83d1875e95a1f54abd47123931d0a04a764c` | `ee4b5257fed29fbbbc0af069f6bc25f32971002fbee48052325ce280756dacf6` |
| `TLT` | 4784 | `ec35809d72b44728d4776a750b698d7280319d227dce1579544793f07c7b4560` | `da7d94c93090ce725716d65dfd36c0695ae5234615a13d33344dd0015735295e` |
| `HYG` | 4784 | `04b0cbb73fc14817d4e3bfebed7227eb47925c4872db186bfd050feacb68805f` | `7f63adc011a8cb5b30e081749d7b3d2a71520de0898703ea77700cf9d1023d9c` |
| `LQD` | 4784 | `07e189cb7b9c6db2a7caedd7464e66d27d55d6ccd6ea0c4969553e50f9bc01d6` | `6efc5a3a44fb752f750ce7b459fc44ea8d413b8cdec7a85a818baafa6e854be9` |
| `EFA` | 4784 | `46ef2fb2ea993d93996326e194fb192e79c67463d2e34fe3221269516a093dad` | `d846679edf169ce9c2767a1b51e82d6fd7e98ced35b806864de3aa5171584f45` |
| `AGG` | 4784 | `42b9eb79269a140e354e15aa0f26b6c11bd778124a22d452ff2682c8e58eb21a` | `3c4dead828e7f715c3fa944a47bca87a37c5d128d8b7dfcd28238d1724e254e1` |
| `TIP` | 4784 | `e6c15c66c1550ba60a43099635dd325ccdf9cb8a40ef906abee49c48e6408989` | `eec3219a26c9a52b2835d4ef0779e8c84a2a830085cf026b6fe7c8902be90ef2` |
| `BIL` | 4784 | `716babf36b3851b17afcb28980e51c91fa2a8c82bf8df80ad498b15b853271cf` | `d71e66af701a7a3e62c77833f3817cee7a56424dc4808412243cea55cb52aad5` |
| `IEF` | 4784 | `091989173cb245146cfa2ffb88dcdf3e4f728a4e2ab753e191221b518596e56f` | `445f5f8a0f33b5837ba80bde621091410eb4b1dddead7f2d3947c938c3a5f1e7` |

## Structural windows

These are calendar and session-count facts derived only from the admitted
session grid, before any price-derived quantity was computed.

- Full grid: 4784 sessions.
- Post-publication OOS `2022-09-01`..`2026-07-31`: 981 sessions, 47 monthly
  actions.
- Fold 1 `2022-09-01`..`2023-12-31`: 334 sessions, 16 actions.
- Fold 2 `2024-01-01`..`2025-04-30`: 333 sessions, 16 actions.
- Fold 3 `2025-05-01`..`2026-07-31`: 314 sessions, 15 actions.
- The three folds exactly partition the OOS window (334 + 333 + 314 = 981) and
  the action counts match the frozen preregistration exactly.

## Trust

External source and tracker performance figures remain untrusted and are not
used for ranking, gates, or promotion. Manual bars, hand normalization,
synthetic history, source back-extension, broker data, and alternate providers
were not used. This receipt grants no shadow, paper, broker, or live authority.
