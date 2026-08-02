# V5.77 SPY inverse-variance data receipt

## Admission

The exact adjusted-close SPY contract is admitted after protocol commit
`1a9ad74` and before any V5.77 engine, variance calculation, or outcome
existed.

- Protocol SHA-256:
  `3b6ecd43ecef4e6f86bcc5279a179d8e559e89b14f883da9c1a59d7eb8dc4803`.
- Imported V5.72 combined-data SHA-256:
  `5a4d8c0fea3ca879011239067f76c6375012f30835e0d579f329f018176b77e2`.
- Imported V5.72 manifest SHA-256:
  `82c1edc7192b9f63b057a4846a0d0540958d9939f6dbabddd793899ca797f0ab`.
- Imported V5.72 receipt SHA-256:
  `827ed0bdeece4bb373eb29517c2c0cf1dd383a89f64be958d1cf1357e22c807c`.
- Imported normalized SPY SHA-256:
  `ac5fc6752e7aedd8e922782dbd780e53cbac52a0fb8a38f50742e6c803a31a77`.

## Provenance, semantics, and coverage

- Provider: authenticated Tiingo End-of-Day GET-only HTTPS API.
- Documentation: <https://www.tiingo.com/documentation/end-of-day>.
- Field: `adjClose` normalized to `adjusted_close`.
- Semantics: provider split- and dividend-adjusted closing price.
- Identity mapping: `SPY->SPY`.
- SPY is selected only from the pinned V5.72 bytes.
- Manual CSV, hand normalization, synthetic histories, broker data, adjusted-
  OHLCV claims, point-in-time-vintage claims, and execution-price claims: none.

SPY has exactly 5,458 unique sessions from `2004-11-18` through
`2026-07-31`, with no missing, duplicate, invalid, nonpositive, stale,
intersected, forward-filled, or substituted row.

| Window | Sessions | First | Last |
| --- | ---: | --- | --- |
| calibration date slice | 3,043 | 2004-12-01 | 2016-12-30 |
| calibration calendar months | 145 | 2004-12 | 2016-12 |
| calibration/state warm-up | 3,154 | 2004-11-18 | 2017-05-31 |
| full OOS | 2,304 | 2017-06-01 | 2026-07-31 |
| fold 1 | 754 | 2017-06-01 | 2020-05-29 |
| fold 2 | 756 | 2020-06-01 | 2023-05-31 |
| fold 3 | 794 | 2023-06-01 | 2026-07-31 |

The folds total exactly 2,304 sessions and partition OOS. No return, variance,
median, target weight, metric, gate, fitting, or parameter choice was computed
during admission.

## Credential, network, and safety receipt

- Worktree `.env`: false; primary-checkout `.env`: true.
- Process paper profile loaded: false.
- Process credential alias loaded: false.
- New credential lookup or network request for V5.77: false.
- The imported V5.72 receipt binds its original authenticated Tiingo GET-only
  acquisition and credential non-disclosure evidence.
- Broker credential lookup, account/order/position access, broker mutation,
  paper mutation, and live activity for V5.77: false.

## Computation gate

The V5.77 engine must pin this receipt, protocol, V5.72 data, manifest and
receipt, and normalized SPY. It must prove exact identity and session/window
coverage before reading prices. Any mismatch blocks.
