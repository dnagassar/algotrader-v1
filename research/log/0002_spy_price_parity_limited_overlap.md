# SPY Price Parity Limited Overlap Smoke Check

Advisory parity check only. Price-return basis only. Not validation. Not trading advice.

## Scope

- Local source: matched local SPY close-price subset derived from `.data\research_snapshots\SPY_daily.csv`
- External reference: manually supplied SPY reference CSV normalized to `date,close`
- Compared window: 2026-04-15 through 2026-05-15
- Row count: 23 local rows, 23 reference rows
- Basis: close-price return only
- Feed caveat: local snapshot was IEX-based; external reference appears broader/consolidated

## Result

| year | local_price_return | reference_price_return | difference_bps |
| ---: | ---: | ---: | ---: |
| 2026 | 0.0562343694 | 0.0560476612 | 1.8671 |

## Interpretation

This is a limited recent close-price parity smoke check only.

The matched-window difference was 1.8671 bps, which is small enough to support a narrow sanity check that recent local close prices are broadly aligned with the external reference over this short window.

This is not full-sample parity for the 2024-01-02 through 2026-05-15 SPY research snapshot.
