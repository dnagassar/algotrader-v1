# V5.73 global-equities dual-momentum data receipt

## Admission

The exact four-symbol adjusted-close contract is admitted after the protocol
commit `4b6b802` and before an engine or candidate outcome existed.

- Protocol SHA-256:
  `27de22520bccd1ac61063717ec718ed0bda6aef6ed8233d21846e60450a642d0`.
- Imported V5.72 combined-data SHA-256:
  `5a4d8c0fea3ca879011239067f76c6375012f30835e0d579f329f018176b77e2`.
- Imported V5.72 manifest SHA-256:
  `82c1edc7192b9f63b057a4846a0d0540958d9939f6dbabddd793899ca797f0ab`.
- Imported normalized SPY symbol SHA-256:
  `ac5fc6752e7aedd8e922782dbd780e53cbac52a0fb8a38f50742e6c803a31a77`.

## Provider and semantics

- Provider: authenticated Tiingo End-of-Day read-only HTTPS API.
- Documentation: <https://www.tiingo.com/documentation/end-of-day>.
- Provider field: `adjClose`, normalized to `adjusted_close`.
- Admitted semantics: provider split- and dividend-adjusted close.
- Identity mappings: `SPY->SPY`, `VEU->VEU`, `BIL->BIL`, `AGG->AGG`.
- No manual CSV, hand normalization, synthetic bar, broker data, adjusted-
  OHLCV claim, execution-price claim, or point-in-time vintage claim exists.

SPY is read from the exact V5.72 14-symbol combined file only after its data,
manifest, and normalized-symbol hashes validate. VEU, BIL, and AGG were newly
acquired into the isolated V5.73 path after protocol freeze.

| Symbol | Rows | First | Last | Source-file SHA-256 |
| --- | ---: | --- | --- | --- |
| SPY | 4,822 selected | 2007-06-01 | 2026-07-31 | V5.72 combined file pinned above |
| VEU | 4,822 | 2007-06-01 | 2026-07-31 | `8c5ca3ee9d5d9a696c87cbd7d61b13c33b4a2010fe56becc08aeab11971cb5b4` |
| BIL | 4,822 | 2007-06-01 | 2026-07-31 | `8d45ab5e0a0ebeeb8447b2e12b368f631b91fe97bd3b3fdc736bda391b8753c5` |
| AGG | 4,822 | 2007-06-01 | 2026-07-31 | `1140e1fd5a23a0919cff020e4f53e041d415bcde179a88146bd0aced4b86fc7a` |

The exact four-symbol session sequences are identical: 4,822 unique common
sessions from `2007-06-01` through `2026-07-31`, with no missing, duplicate,
invalid, nonpositive, stale, or substituted observation.

## Frozen chronology coverage

| Window | Sessions | First | Last |
| --- | ---: | --- | --- |
| reference and warm-up | 1,407 | 2007-06-01 | 2012-12-31 |
| full OOS | 3,415 | 2013-01-02 | 2026-07-31 |
| fold 1 | 1,133 | 2013-01-02 | 2017-06-30 |
| fold 2 | 1,135 | 2017-07-03 | 2022-01-03 |
| fold 3 | 1,147 | 2022-01-04 | 2026-07-31 |

The folds are disjoint and total exactly 3,415 sessions. Warm-up contains more
than the required twelve complete month-end intervals. No fitting, parameter
selection, performance calculation, or ranking occurred during admission.

## Credential, network, and safety receipt

- Worktree `.env` present: false.
- Primary-checkout `.env` present: true.
- Process paper profile initially loaded: false.
- Process credential alias initially loaded: false.
- Trusted child adapter loaded only `TIINGO_API_KEY`.
- Credential value printed or written: false.
- Network operations: exactly three sequential allowlisted HTTPS `GET`
  requests to `api.tiingo.com/tiingo/daily/{approved_symbol}/prices`.
- Destination allowlist and GET method enforcement: true for all three.
- Broker credential lookup, broker/account/order/position access, broker
  mutation, paper mutation, and live activity: false.
- Candidate return, metric, ranking, gate, and route computed: false.

Generated raw responses, normalized files, canonical files, and provider
receipts remain ignored under `runs/v5_73_global_equities_dual_momentum/`.
They contain no credential value and are evidence bytes, not authority.

## Computation gate

The engine must pin this receipt, the protocol, V5.72 imported data and
manifest, normalized SPY, and all three new canonical files before reading
prices. It must verify exact four-symbol session equality and all frozen window
counts. A mismatch blocks rather than produces a result.
