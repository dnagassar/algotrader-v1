# V6.02 EDGAR delisting pipeline

Infrastructure, not a research milestone. It exists to answer the question
V6.01 left open: a ticker is not a security identifier, so what is?

## Why

The V6.01 probe found that Tiingo silently reuses symbols. `SHLD` returns a
series beginning 2023 for a company delisted in 2018. `BBBY` returns one
unbroken series, with no gap, spanning two unrelated corporations across a
bankruptcy. A missing ticker fails loudly; a reused ticker does not fail at all,
which is worse.

Fixing that needs a permanent identifier and a delisting date. SEC CIK is
permanent and never reused; Form 25 gives the date.

## The chain, and what each step actually yields

| Step | Source | Yields |
| --- | --- | --- |
| 1 | `form.idx` per quarter | every Form 25 / 25-NSE filing: CIK, company, date |
| 2 | `submissions/CIK##########.json` | that CIK's filing history |
| 3 | last periodic report filed **at or before** delisting | the document to trust |
| 4 | cover-page inline XBRL | `dei:TradingSymbol`, `dei:SecurityExchangeName` |

Step 3 is the load-bearing one. A shell can keep filing after delisting and a
successor can reuse the ticker, so only a report the company filed **while still
listed** can attest to the symbol it traded under. `select_symbol_source_filing`
enforces that and is pinned by test.

Two dead ends were checked and ruled out rather than assumed:

- **Form 25 itself carries no ticker.** The full `primary_doc.xml` for SVB
  Financial contains exchange CIK, issuer CIK, entity name, file number,
  address, `descriptionClassSecurity` ("Common stock and preferred stock") and
  a rule provision. No symbol.
- **The XBRL `companyfacts` API does not expose `dei:TradingSymbol`.** For both
  SVB Financial and Twitter the only `dei` concepts present are
  `EntityCommonStockSharesOutstanding` and `EntityPublicFloat`.

EDGAR also drops the ticker from `submissions` once a company delists: SVB
Financial returns `tickers: []`, `exchanges: []`.

## Correction issued by V6.03

**The "3 of 7, systematic by filer type" finding below was wrong, and the cause
was a defect in this milestone's own parser, not a limit of EDGAR.**

`_SYMBOL_TAG` matched the character immediately following the fact's opening
tag. Issuers routinely wrap the value in presentation markup —
`<b>BLUA</b>`, `<span>COE</span>` — so for those filings the next character is
`<` and the match failed. SVB Financial happened to tag a bare `>SIVB<` and
passed, which is why the misses appeared to sort by filer type.

Re-run against the same seven documents with the repaired parser, recovery is
**6 of 7**. Banco Santander Mexico (`BSMX`), 51Talk (`COE`) and BlueRiver
(`BLUA`, `BLUA.U`) all resolve; two of those are foreign private issuers and one
is the SPAC. Only BONSO Electronics still fails, and inspection confirms its
20-F carries no `dei:TradingSymbol` at all — a real absence.

There was no filer-type effect. A sample of seven was read as a coverage story
when it was measuring the parser. See
`v6_03_full_history_delisting_registry.md`; the defect is pinned by tests in
`tests/unit/test_delisting_registry.py`.

## Verified end to end

One quarter, 2023 QTR2: **554** Form 25 / 25-NSE filings enumerated. On a
seven-company sample, as re-measured after the correction above:

| CIK | Delisted | Symbols | Source |
| --- | --- | --- | --- |
| 0000719739 | 2023-05-02 | `SIVB`, `SIVBP` | cover-page XBRL |
| 0001091587 | 2023-05-12 | `ABB` | cover-page XBRL |
| 0001851908 | 2023-06-26 | `BSAQ`, `BSAQWS`, `BSAQU` | cover-page XBRL |
| 0001831006 | 2023-04-10 | `BLUA`, `BLUA.U` | cover-page XBRL |
| 0001698287 | 2023-04-24 | `BSMX` | cover-page XBRL |
| 0001659494 | 2023-06-01 | `COE` | cover-page XBRL |
| 0000846546 | 2023-06-23 | — | not tagged in filing |

SVB Financial — the case that motivated the whole exercise, and the one Tiingo
serves as a 404 — resolves correctly to `SIVB` and `SIVBP`.

## Coverage limits, stated rather than smoothed over

Seven is far too small a sample to put a number on, and a full-history run is
needed before any recovery rate is quoted. That run is V6.03.

**Pre-2019 delistings are largely unrecoverable by construction.** Cover-page
inline XBRL phased in from 2019, so earlier delistings yield a CIK and a date
but usually no symbol. `TICKER_TAGGING_ERA_START` marks the boundary and such
records are kept and flagged, never dropped and never guessed.

**The price-side hole from V6.01 remains.** Companies that failed abruptly —
`SIVB`, `FRC`, `LEH` — are absent from Tiingo entirely. This pipeline can now
name them and date them; it cannot conjure prices that the vendor does not
serve. Any universe built from this is survivorship-**reduced**, not
survivorship-free, and still carries an upward bias of unknown size.

## What it produces

`price_admission_window` returns the only window in which a ticker's price
series can be trusted: everything through the delisting date, nothing after.
Applied to `BBBY` that severs the bankruptcy splice; applied to `SHLD` it
discards the record outright, since Tiingo's coverage never reaches back before
the 2018 delisting.

## Safety

A fourth external destination, both hosts SEC, recorded here rather than added
silently. GET only. **No credentials** — EDGAR is public and the adapter has no
code path that can read an environment variable, dotenv, or credential store,
asserted by AST parse rather than string match. SEC's fair-access policy
requires a User-Agent carrying contact information, so one is mandatory and
validated; the operator's contact address is sent to SEC because SEC requires
it of every caller. Archive paths are refused if they traverse directories.
Dry-run mode performs zero network calls, proven by injecting a function that
raises if called. No broker, account, order, or position access; no paper
mutation; no live activity.
