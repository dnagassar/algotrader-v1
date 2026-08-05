# V6.04 survivorship inflation, measured

The first number this program has produced about its own bias rather than about
a strategy. It answers one question: how much does building a universe from
securities that still exist overstate that universe's return?

**Answer, for single-country equity ETFs over 2019-2026: `0.005797` annualised,
about 0.58 percentage points a year. It is a lower bound.**

## What was compared

| | |
| --- | ---: |
| surviving single-country equity ETFs (the program's own universe) | 36 |
| dead country-equity ETFs recovered from the registry | 39 |
| admitted as genuine deaths with usable history | 27 |
| discarded | 12 |
| survivor-only mean annualised return | `0.108520479656` |
| mean including the dead | `0.102723933243` |
| **inflation** | **`0.005796546414`** |

The comparison is deliberately universe-level. Re-scoring V5.91, V5.92 or V5.98
on an expanded universe would violate their standing prohibitions and would
confound survivorship with everything else that changed. Comparing return
distributions isolates the bias without re-testing a hypothesis.

Dead funds contribute only the life they actually had. They are not extrapolated
forward and not assumed to go to zero — an ETF that closes liquidates at net
asset value, which is neither. Several closed while profitable: `FM` `+0.0361`,
`RWED` `+0.0331`, `FCAN` `+0.0161`. The worst was `SCIN` at `-0.1722`. That
spread is why the inflation is modest rather than dramatic.

## The three ways a "delisting" is not a death

Of 39 dead country-equity ETFs, 12 were refused, each for a reason confirmed in
the price data rather than assumed.

**Ticker reuse (2): `HAO`, `PPEM`.** The series on offer begins after the
security stopped trading, so it belongs to whoever holds the symbol now. `HAO`
delisted in 2019; its series begins 2024-01-26 under Haoxi Health Technology.
This is the `BBBY` splice, caught automatically.

**Still trading (9).** Form 25 is a *Notification of Removal from Listing*, and
an exchange transfer triggers one too. These nine trade 208 to 2,592 days past
their filing: `NORW` (+1,737), `UEVM` (+2,592), `FLRU` (+1,316), `PBEE`
(+1,126), `EMFQ`, `FAUS`, `FBZ`, `FINE`, `RFEU`. **A Form 25 does not mean a
security died**, and the registry cannot tell the difference on its own — only
the price series can.

**Too little history (1).** Not enough bars in the window to annualise.

## Why the first answer was wrong

The measurement first returned `0.002777`, less than half the corrected figure.
Verifying it exposed a defect in the registry's own episode logic.

An episode groups every Form 25 a CIK files within a year. Stage C stamped
**all** securities in an episode with the episode's *earliest* filing date. But
a sponsor winding down a range of funds files across months, and each fund stops
trading on its own date. So dead funds were truncated up to a year early, and
the continuation filter then rejected them as "not really dead".

`FRN` made it visible: Form 25 dated 2019-02-28, last trade 2020-02-14. After
the repair its date is 2020-02-26, which matches the price record.

| symbol | episode date | own date | last bar |
| --- | --- | --- | --- |
| `FRN`, `EWEM` | 2019-02-28 | 2020-02-26 | 2020-02-14 |
| `PPDM`, `RWDE`, `RWED` | 2019-10-18 | 2020-10-02 | 2020-09-29 |
| `HFXE`, `HFXJ` | 2020-02-11 | 2020-08-13 | 2020-08-05 |

Admitted deaths rose from 19 to 27 and the inflation roughly doubled. Each
symbol now carries `symbol_delisted_on`, the date of the Form 25 that named it.

## Why this is a lower bound, three times over

1. **Unpriced failures cannot enter.** V6.01 established that abrupt failures
   are absent from the price source entirely. For funds this bites less than for
   equities — a closing ETF liquidates in an orderly way and its history
   survives — but anything the vendor never served is invisible here.
2. **Deaths whose Form 25 went unmatched are excluded.** `FAUS` stopped trading
   2022-01-10 under a later filing that did not resolve, so it counts as a
   survivor. Every such miss removes a casualty from the dead pool.
3. **The window starts in 2019.** Exact attribution needs Form 25
   `primary_doc.xml`, which exists only for filings made through EDGAR's online
   form. Funds that died earlier are not counted, and the program's backtests
   run from 2000.

## What it means

**0.58 points a year is real but small**, and it does not rescue or condemn any
prior milestone. For context, V5.91 and V5.92 rejected their candidates by
margins far larger than this. Survivorship was never the reason those failed.

The more useful finding is the negative one: **a survivor-only ETF universe is
not badly biased**, because closing funds are not disproportionately
catastrophic. They are ordinary funds that failed to gather assets, and several
were profitable when they closed. This is materially unlike single-stock
survivorship, where the missing names include bankruptcies.

That also means the delisting registry, as applied to ETF universes, buys less
than the effort it cost. Its value is higher for equity universes, which this
program does not currently use.

## Safety

Read-only GETs to the already-allowlisted price host, following the V6.01
precedent: no canonical data written, no symbol allowlist modified, credential
loaded from the dotenv outside the checkout and never printed. The measurement
arithmetic lives in `algotrader.research.survivorship_inflation`, which is pure
and carries no network or credential path.
