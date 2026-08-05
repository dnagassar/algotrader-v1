# V6.01 delisted-ticker coverage probe

A feasibility probe, not a research milestone: does the existing free Tiingo
tier serve price history for securities that no longer trade? If it does, the
survivorship wall that blocked small-cap structural work comes down at zero
cost. No canonical panel was written and no research data was admitted.

## Result: partial, with a trap that is worse than the gap

### Acquisitions and take-privates are served correctly

| Ticker | Bars | Coverage | Last close | Event |
| --- | ---: | --- | ---: | --- |
| TWTR | 2,260 | 2013-11-07 .. 2022-10-28 | `53.70` | taken private 2022-10 |
| XLNX | 535 | 2020-01-02 .. 2022-02-14 | `194.92` | acquired 2022-02 |
| ATVI | 448 | 2022-01-03 .. 2023-10-13 | `94.42` | acquired 2023-10 |
| VMW | 476 | 2022-01-03 .. 2023-11-22 | `142.48` | acquired 2023-11 |

Each series terminates on the correct date at a plausible deal price. This
slice of the survivorship problem is genuinely solved for free.

### Catastrophic failures are missing

`SIVB` (Silicon Valley Bank) and `FRC` (First Republic) both return **HTTP 404**.
`LEH` (Lehman Brothers) returns 200 with null coverage. These are precisely the
observations survivorship bias is *about* — the ones that went to zero — and
their absence biases any study upward.

### Ticker reuse silently splices unrelated companies

This is the dangerous finding, because it produces data that looks valid.

- `SHLD` returns 723 bars beginning **2023-09-13**. Sears Holdings traded from
  2005 to 2018. Every bar returned belongs to a different company that later
  took the symbol. A request for Sears yields zero Sears data and no error.
- `BBBY` returns 2,911 bars from 2015-01-02 through 2026-07-31 with **no
  multi-month gap anywhere**. Bed Bath & Beyond went bankrupt in 2023 and the
  ticker was subsequently taken over by a different corporate entity. One
  unbroken series therefore spans two unrelated companies across a bankruptcy,
  with nothing in the data to signal it.

A missing ticker fails loudly. A reused ticker fails silently, and a
survivorship study built on symbols alone would ingest Frankenstein series
without any check firing.

## What this means practically

A ticker is not a security identifier. Any survivorship-free universe needs a
**permanent identifier** and a **delisting date**, and prices must be truncated
at that date rather than trusted to the end of the series.

That combination is buildable for free:

1. SEC EDGAR Form 25 filings give delisting dates keyed to CIK, which is
   permanent and never reused.
2. Tiingo supplies the prices.
3. Each ticker's history is admitted only up to its delisting date, and any
   symbol whose Tiingo coverage does not reach back before that date is
   discarded as a reuse case rather than patched.

The residual hole is real and must be disclosed in any study that uses this
pipeline: bankruptcies that ceased trading abruptly are absent from the price
source entirely, so the universe would be survivorship-*reduced*, not
survivorship-free, and results would still carry an upward bias of unknown size.

## Safety

Read-only GET requests to the already-allowlisted `api.tiingo.com`. The
credential was loaded from the existing dotenv and never printed, logged, or
persisted. No canonical data was written, no research panel was admitted, and
no allowlist was modified.
