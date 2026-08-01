# Active implementation handoff

## V5.70 terminal outcome

The exact frozen V5.64 forward confirmation is complete. Terminal route:
`close_stock_filter_family`. The NexusTrade-inspired stock-filter family is
closed; no retry, repair, tuning, same-family candidate, preview, shadow,
paper promotion, or live authority remains.

## Checkout and chronology

- Branch: `codex/v5.62-nexustrade-source-data-unblock`.
- Clean takeover HEAD: `74ba4eca22356f43f7a106d5875906409c3e8896`.
- Protocol commit `bec4267` preceded data acquisition.
- Metadata-only receipt commit `6262e60` preceded forward replay.
- Protocol SHA: `7977ef62d5b1da7b658e57aad34e85f91438659d9c5c639726abb23ee10e8e37`.
- Receipt SHA: `9ad6db6e4cacf9e5accace6911052fb44f72fbe201609ce15fdbe8ba705a8ef9`.
- Exactly one writer; no reset, clean, stash, restore, rebase, switch, or new
  worktree.

## Admitted data

- Tiingo EOD `adjClose` to `adjusted_close`; split/dividend adjusted price;
  adjusted OHLCV not claimed.
- 12/12 symbols valid, `BRK-B->BRK-B`, zero blocked.
- 2019-01-02 through 2026-06-30; 1,883 common sessions; 22,596 rows.
- Fresh forward 2025-03-31 through 2026-06-30: 314 sessions.
- Fold counts 106/105/103 with exact full coverage.
- Historical adjusted-close prefix mismatch count: zero.
- Data SHA: `04344d4a60702dd936b183b20937a41b7f90e6813096a9120fc3b2e642d91688`.
- Manifest SHA: `43ae5c6bdd5c6addc2bd7e3d863818229748cad5d0b28f3cad569676340cb1ca`.

The trusted adapter loaded only `TIINGO_API_KEY` from the primary checkout's
existing `.env`; value printed/written false. Twelve allowlisted HTTPS GETs
succeeded. Broker/account/order/position access and mutation were false.

## Decision evidence

Frozen V5.64 preregistration/result/summary reproduced exactly. Composite
integrity passed with 105 target-difference sessions.

Moderate-friction composite:

- full forward return `0.052351627510281683703382537`, drawdown
  `0.1320323282336477364892538502`, Sharpe
  `0.2507882871646472557234913287`, turnover
  `12.10499437780069802271361865`;
- fold returns `0.0427262571478272947097422`,
  `0.111196594498479289946322917`, and
  `-0.0917620061625934073408801612`.

All gates did not pass. SPY baseline failed full forward and folds two/three.
Cost failed because both SPY edges were negative. Static equal weight failed
full forward and folds one/three. Composite value failed versus standalone:
return delta `-0.226555529570140695736317679`, Sharpe delta
`-0.9871735043873385949447073353`, and no metric improved.

The result is valid and terminal, not blocked. A second replay was
byte-identical.

## Artifacts

- preregistration `94f9f5bb19c426c0cbf042e780cf22c1431ee123278f80d5f8fec129c996d67a`
- result `095876c3729522211f480af92b1f08d745a12a58a649947ed46516230da72cb0`
- summary `1062c0555a9174dc55cd8506a9361809ecd6728ca95d598d88b525ec307003fa`
- manifest `452c518cce78324a4f67a3d271dbacdc012056e7527bbd6a68742ca2da18f846`

## Safety and next milestone

No NexusTrade access/mutation, broker access, paper mutation, receipt,
reconciliation, or live activity occurred. V5.57 caps remain $25 entry, $60
aggregate marked SPY exposure, one broker order per secure cycle, and two
sleeve intents per UTC day. No third sleeve; live unauthorized.

Next: stop this stock-filter lane. Any future alpha requires a materially new,
independently evidenced family with genuinely untouched data and a new
preregistration. Do not reuse V5.64-V5.70 outcomes for parameter or symbol
selection.
