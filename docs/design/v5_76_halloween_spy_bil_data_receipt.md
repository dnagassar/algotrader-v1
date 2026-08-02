# V5.76 Halloween SPY/BIL data receipt

## Admission

The exact two-symbol adjusted-close contract is admitted after protocol commit
`8d0c96e` and before any V5.76 engine or outcome existed.

- Protocol SHA-256:
  `e306ef9f20803778f86857521977578b02aa7af13ca7033baa09dbdbd4cfdf82`.
- Imported V5.72 combined-data SHA-256:
  `5a4d8c0fea3ca879011239067f76c6375012f30835e0d579f329f018176b77e2`.
- Imported V5.72 manifest SHA-256:
  `82c1edc7192b9f63b057a4846a0d0540958d9939f6dbabddd793899ca797f0ab`.
- Imported V5.73 receipt SHA-256:
  `0c5c2126ad954efffc5eba7c7bf9500f7b53747f1d3febce44e1e845a1a08818`.
- Imported normalized SPY SHA-256:
  `ac5fc6752e7aedd8e922782dbd780e53cbac52a0fb8a38f50742e6c803a31a77`.
- Imported BIL canonical SHA-256:
  `8d45ab5e0a0ebeeb8447b2e12b368f631b91fe97bd3b3fdc736bda391b8753c5`.

## Provenance, semantics, and coverage

- Provider: authenticated Tiingo End-of-Day GET-only HTTPS API.
- Documentation: <https://www.tiingo.com/documentation/end-of-day>.
- Field: `adjClose` normalized to `adjusted_close`.
- Semantics: provider split- and dividend-adjusted closing price.
- Identity mappings: `SPY->SPY` and `BIL->BIL`.
- SPY is selected only from the pinned V5.72 bytes and BIL is imported only
  from the pinned V5.73 canonical bytes.
- Manual CSV, hand normalization, synthetic histories, broker data, adjusted-
  OHLCV claims, point-in-time-vintage claims, and execution-price claims: none.

SPY and BIL contain exactly the same 4,822 unique common sessions from
`2007-06-01` through `2026-07-31`. There is no missing, duplicate, invalid,
nonpositive, stale, intersected, forward-filled, or substituted row.

| Window | Sessions | First | Last |
| --- | ---: | --- | --- |
| reference/state warm-up | 148 | 2007-06-01 | 2007-12-31 |
| full OOS | 4,674 | 2008-01-02 | 2026-07-31 |
| fold 1 | 1,511 | 2008-01-02 | 2013-12-31 |
| fold 2 | 1,510 | 2014-01-02 | 2019-12-31 |
| fold 3 | 1,653 | 2020-01-02 | 2026-07-31 |
| post-2021 publication slice | 1,400 | 2021-01-04 | 2026-07-31 |

The three folds total exactly 4,674 sessions and partition OOS. No return,
metric, gate, holding outcome, fitting, or parameter choice was computed during
admission.

## Credential, network, and safety receipt

- Worktree `.env`: false; primary-checkout `.env`: true.
- Process paper profile loaded: false.
- Process credential alias loaded: false.
- New credential lookup or network request for V5.76: false.
- The imported V5.72/V5.73 receipts bind their original authenticated Tiingo
  GET-only acquisition and non-disclosure evidence.
- Broker credential lookup, account/order/position access, broker mutation,
  paper mutation, and live activity for V5.76: false.

## Computation gate

The V5.76 engine must pin this receipt, protocol, V5.72 data and manifest,
normalized SPY, V5.73 receipt, and canonical BIL. It must prove exact symbol,
session, and window equality before reading prices. Any mismatch blocks.
