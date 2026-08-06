# V6.04 survivorship inflation, measured

The first number this program has produced about its own bias rather than about
a strategy. It answers one question: how much does building a universe from
securities that still exist overstate that universe's return?

**Answer: between `0.0057` and `0.0368` annualised — 0.6 to 3.7 percentage
points a year — depending on how the average is constructed. All are lower
bounds. See the sensitivity below before quoting any single figure.**

> **Correction.** This note originally reported `0.005797` as *the* answer and
> concluded a survivor-only ETF universe "is not badly biased". A sensitivity
> across constructions, run after an independent reviewer declined to interrogate
> the weighting, shows that figure is the **lowest of every construction tried**
> and that the conclusion drawn from it was not supported. The body below has
> been corrected; the original framing is preserved in git history.

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

## Sensitivity: the answer depends on the construction, by 6.5x

Constructions and history filters were fixed in
`algotrader.research.survivorship_inflation` and its tests **before** being run,
so this is disclosure rather than selection.

| construction | inflation |
| --- | ---: |
| equal-weighted mean of annualised returns | `+0.005694` |
| ...requiring at least 1 year of history | `+0.011619` |
| ...requiring at least 2 years of history | `+0.013526` |
| length-weighted mean of annualised returns | `+0.008489` |
| terminal wealth, dead funds liquidating to cash | `+0.036822` |

Window 2019-01-01 to 2026-08-05 (7.59 years), 62 symbols admitted of which 27
are dead, 13 discarded.

**Why the equal-weighted figure is the lowest.** Annualising a short life
magnifies whatever happened in it. `XINA` lived 0.41 years and annualises to
`+0.6104`; `CNHX` `+0.3616` over 1.01 years; `BCNA` `+0.2184` over 0.80. Under
equal weighting those extreme positives enter the dead pool at full weight and
pull its mean up, masking the bias. Requiring two years of history roughly
doubles the measured inflation, which is the signature of exactly that effect.

This was anticipated as a weakness but the direction was guessed wrong: the
concern was that short-lived failures would drag the dead pool down. They lift
it instead.

**The terminal-wealth construction is the one that answers the portfolio
question.** Buy every fund equally at the window's start, hold, and let the dead
liquidate at net asset value into cash. Every symbol is then carried to the same
end date, so lifespans are comparable and no annualisation artefact arises. It
gives `+0.036822` — about **3.7 points a year**.

## What it means

**The honest statement is a range, 0.6 to 3.7 points a year, and the
construction matters more than anything else measured here.** Anyone quoting a
single number must say which construction produced it.

Under the most economically meaningful construction the effect is **not small**.
3.7 points a year compounds to roughly a quarter of terminal wealth over this
window, which is enough to matter to any universe-level claim this program
makes.

The earlier conclusion — that a survivor-only ETF universe "is not badly biased"
and that the registry "buys less than it cost" — **is withdrawn**. It rested on
the single lowest construction. Closing funds still are not disproportionately
catastrophic in the way delisted single stocks are, but that observation does
not license the conclusion that was drawn from it.

What survives unchanged: this does not rescue or condemn V5.91 or V5.92, which
rejected their candidates by margins far larger than even 3.7 points.

## Safety

Read-only GETs to the already-allowlisted price host, following the V6.01
precedent: no canonical data written, no symbol allowlist modified, credential
loaded from the dotenv outside the checkout and never printed. The measurement
arithmetic lives in `algotrader.research.survivorship_inflation`, which is pure
and carries no network or credential path.
