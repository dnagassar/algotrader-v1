# V6.03 full-history delisting registry

Infrastructure, not a research milestone. V6.02 proved the EDGAR chain on one
quarter by hand; this runs it across every quarter EDGAR publishes, which is
what turns a demonstration into a registry and what makes a recovery rate
measurable rather than anecdotal.

It also corrects V6.02's headline coverage finding, which was wrong.

## The V6.02 defect, and why it mattered more than the gap it described

V6.02 reported symbol recovery of **3 of 7** and concluded the misses were
systematic by filer type: "domestic operating companies resolved; foreign
filers and blank-check vehicles did not."

That conclusion was manufactured by a parser defect. `_SYMBOL_TAG` matched the
character immediately after a fact's opening tag:

```
name="dei:TradingSymbol"[^>]*>\s*([^<\s][^<]{0,19}?)\s*<
```

An inline-XBRL fact is an element, and issuers routinely wrap the visible value
in presentation markup:

```html
<ix:nonNumeric name="dei:TradingSymbol" ...><b>BLUA</b></ix:nonNumeric>
<ix:nonNumeric name="dei:TradingSymbol" ...><span>COE</span></ix:nonNumeric>
```

For those the next character is `<`, so the match failed and the record was
written as `unrecoverable`. SVB Financial happened to tag a bare `>SIVB<` and
passed. The three that "failed by filer type" all carried the tag — at byte
offsets 97,253, 175,660 and 2,692,937 of their respective documents.

Re-measured against the same seven documents with the repaired parser, recovery
is **6 of 7**. Both foreign private issuers resolve (`BSMX`, `COE`), the SPAC
resolves (`BLUA`, `BLUA.U`), and BlueRiver gains a unit class the old parser
could not have seen. Only BONSO Electronics still fails, and its 20-F genuinely
carries no `dei:TradingSymbol` anywhere.

There was no filer-type effect. A sample of seven was reporting the parser.

The repair reads the fact's element body, strips inner markup before and after
entity decoding, and drops layout spacers (`&#8203;`, `&#160;`). It also reads
the plain `<dei:TradingSymbol>` element form, and refuses tagged placeholders
(`None`, `N/A`) that are absences rather than symbols. Six regressions in
`tests/unit/test_delisting_registry.py` pin each shape, including a test that a
bare and a wrapped value must produce the same answer — the property whose
absence let the defect through.

**This belongs with the V5.97 double lag and the V5.99 basis desync**: the code
ran, produced a plausible number, and the number described the implementation
rather than the world. In all three the output was interrogated only because
something adjacent looked odd. Here it was the claim that a coverage gap sorted
neatly by filer type — too tidy a story for a sample of seven.

## Two shortcuts rejected on evidence

Stage B's cost is dominated by cover-page documents, which run from 0.6 MB to
30 MB. Two cheaper routes were tested and both were refused.

**Rendered cover pages (`R1.htm`) lose symbols.** The Financial Report
rendering is ~70 KB and carries `defref_dei_TradingSymbol`, a 20-400x saving.
But it collapses the share-class axis into columns: SVB's `R1.htm` shows `SIVB`
and two blank cells, silently dropping `SIVBP`. A registry whose purpose is
identity fidelity cannot source identity from an artifact that drops classes —
that is the V6.01 ticker-splice failure in a new place.

**HTTP `Range` is not supported.** `www.sec.gov` returns `200` with the full
body and no `Accept-Ranges`, whatever the request headers.

Neither was needed. The adapter already sends `Accept-Encoding: gzip` and SEC
serves it: SVB's 9.8 MB document transfers in **691 KB**, roughly 14x. The
faithful full fetch was already affordable, so no extra machinery was built.

## What runs

Two stages, resumable independently.

| Stage | Requests | Yields |
| --- | --- | --- |
| A | one per quarter | every Form 25 / 25-NSE filing: CIK, company, date |
| B | two per delisting episode | trading symbols and exchange from cover-page XBRL |

`src/algotrader/execution/edgar_delisting_pipeline.py` drives both;
`scripts/run_delisting_registry_full_history.ps1` wraps it;
`scripts/report_delisting_registry.py` reports offline from what was written.

Properties enforced by the code rather than by convention:

- All network access goes through `edgar_delisting_adapter.edgar_get`, so
  GET-only, two allowlisted SEC hosts, and no credentials hold in one place.
  A test asserts the pipeline imports no socket-capable module at all.
- Requests are paced below SEC's ten-per-second fair-access ceiling by a
  monotonic clock, and the config refuses an interval under 0.1 s.
- Both stages append JSONL and skip recorded work, so an interrupted run
  resumes. A quarter's completion marker is written *after* its rows, so an
  interruption re-fetches rather than recording a partial quarter as done.
- Payloads are hashed into a manifest and dropped. The full-index archive alone
  is several gigabytes; retaining it buys nothing that the sha256 does not.
- `dry_run` performs zero network access and plans the request set instead.

### Delisting episodes, not filings

A CIK files several Form 25s for one delisting — one per class, days apart —
and can delist, relist, and delist again years later. Filings for a CIK are
therefore grouped into episodes separated by more than a year, and each episode
is one record.

`delisted_on` is the **earliest** filing in its episode. That errs early twice
over: it bounds all of the episode's classes, and Rule 12d2-2 puts the
effective date ten days after the filing. Both errors truncate a price series
too early, which is the safe direction when the point is to sever a
ticker-reuse splice.

### Outcomes are distinguished, not collapsed

A record that yields no symbol says which kind of nothing it is:
`no_tag_in_source_filing`, `no_eligible_periodic_report`,
`source_filing_has_no_primary_document`, `submissions_window_insufficient`
(EDGAR pages filings beyond a thousand, which is not the same as absence), or
a fetch failure. Collapsing these into "unrecoverable" is how V6.02's coverage
story went unchallenged.

## Stage A results: the delisting population

135 quarters, 1993 QTR1 through 2026 QTR3. One quarter (2018 QTR4) hit a read
timeout, was left unmarked, and was picked up by a rerun — the resume path
working as designed rather than a claim about it.

| | |
| --- | ---: |
| quarters fetched | 135 |
| index bytes read | 4,224,626,447 |
| Form 25 / 25-NSE filings | 37,253 |
| delisting episodes | 15,191 |
| distinct CIKs | 11,773 |
| earliest episode | 1999-05-20 |
| latest episode | 2026-08-04 |
| episodes before 2019 | 9,543 |
| episodes from 2019 | 5,648 |

Roughly 2.45 Form 25 filings per delisting episode, which is why episodes and
not filings are the unit: counting filings would overstate the population by
about two and a half times.

**Coverage begins in 1999, not 2005.** Form 25 became an electronic form in late
2004 — the token first appears in bulk in 2004 QTR4 — but SEC retroactively
indexed earlier paper filings into the quarterly archive under the
`9999999997-` accession prefix, so 1999-2004 carries 888 episodes. 1993-1998
is genuinely empty. This was checked rather than assumed: the row parser reads
99.97% of lines in every era (only the ten header and separator lines fail), so
the zeros are absence of Form 25, not a parse failure on an older layout.

The annual run rate is stable at roughly 500-950 delistings a year from 2006
onward, with no visible trend break.

## Stage B results: symbol recovery

All 5,648 tagging-era episodes attempted. 10,416 requests, 13.2 GB, every one
GET against an allowlisted SEC host with no credentials.

| outcome | episodes |
| --- | ---: |
| resolved | 3,822 |
| no tag in source filing | 946 |
| no eligible periodic report | 728 |
| submissions window insufficient | 138 |
| source filing has no primary document | 8 |
| document unavailable | 6 |

**6,318 distinct symbols recovered.** `SIVB` — the case that motivated V6.01
and V6.02, and the one Tiingo serves as a 404 — is among them, as are `BBBY`
and `ATVI`.

### The headline rate is 0.6767, and quoting it alone would repeat V6.02's error

Recovery is governed almost entirely by whether the *source filing* predates
SEC's cover-page tagging mandate. The mandate attaches to the filing, not to
the delisting, so a company that delisted in early 2019 is described by a 2018
report that could not have carried the tag.

| source filing year | resolved / total | rate |
| --- | ---: | ---: |
| 2018 | 1 / 94 | 0.0106 |
| 2019 | 126 / 495 | 0.2545 |
| 2020 | 238 / 454 | 0.5242 |
| 2021 | 491 / 633 | 0.7757 |
| 2022 | 790 / 806 | 0.9801 |
| 2023 | 797 / 807 | 0.9876 |
| 2024 | 595 / 621 | 0.9581 |
| 2025 | 571 / 597 | 0.9564 |
| 2026 | 213 / 223 | 0.9552 |
| no source filing | 0 / 866 | — |

That curve reproduces the three-tier phase-in — large accelerated filers from
mid-2019, accelerated from mid-2020, everyone else from mid-2021 — without
having been told about it. It is the strongest evidence available that the
repaired parser reads what is actually in the filings.

Three numbers, each with its denominator:

- **0.6767** (3,822 / 5,648) — all tagging-era episodes. Dominated by the
  phase-in boundary; the right number only for "what fraction of post-2019
  delistings can be named".
- **0.7992** (3,822 / 4,782) — conditional on an eligible source filing
  existing at all.
- **0.9712** (2,966 / 3,054) — source filing from 2022 onward, the mature
  regime. This is the rate that applies going forward.

By filer type, once the era effect is removed there is no dramatic split:
10-Q sources 0.8303, 10-K 0.7444, 20-F 0.6712, 40-F 0.6667. Foreign private
issuers recover slightly less often, but the gap is a fraction of what V6.02
claimed and nothing like a categorical failure.

## Coverage limits

**Investment companies are structurally unrecoverable: 0 of 302.** Every one
failed as `no_eligible_periodic_report` or `submissions_window_insufficient`,
because closed-end funds and ETFs file N-CSR and N-PORT rather than the
10-K/10-Q/20-F/40-F that `select_symbol_source_filing` accepts. This is a real
gap with a known cause and a known fix — extend the accepted form list to the
investment-company reports and check whether they carry cover-page symbols —
and it is recorded rather than repaired here, because changing the source-filing
rule after seeing which bucket failed is exactly the tuning this program forbids
in research and should avoid in infrastructure too.

**Some failed banks are invisible to EDGAR entirely.** First Republic Bank and
Signature Bank have **zero** Form 25 filings in the full-history index. Both
were state-chartered banks without a holding company, so their securities were
registered under Exchange Act section 12(i) with their banking regulator rather
than the SEC, and EDGAR never sees them. SVB Financial appears because the
holding company was the registrant. Searching the index for "First Republic"
returns only unrelated predecessors — First Republic Bancorp's 2005 delisting
and First Republic Preferred Capital's in 2007 and 2012 — never the bank that
failed in 2023.

This matters more than its count. The institutions that vanish abruptly are
precisely the observations survivorship bias is about, and a subset of them are
missing from the *event* source, not merely from the price vendor. The registry
is therefore survivorship-reduced on two independent axes and complete on
neither.

**The price-side hole from V6.01 is unchanged and is still binding.** This
pipeline can now name and date 15,191 delisting episodes and attach 6,318
symbols. It cannot conjure prices the vendor does not serve. Any universe built
from this is survivorship-**reduced**, not survivorship-free, and still carries
an upward bias of unknown size.

**Pre-2019 episodes yield a CIK and a date but no symbol**, because cover-page
inline XBRL phased in from 2019. That is 9,543 of 15,191 episodes. They are
exported and flagged `not_attempted` rather than dropped or guessed.

## What was produced

`delisting_registry.jsonl`: 15,191 records, 3,822 carrying symbols, each with
the window in which a price series for that ticker can be trusted — through the
delisting date, never after. Applied to `BBBY` that severs the bankruptcy
splice; applied to `SHLD` it discards the post-2023 series outright.

Episode grouping is visible in the output: SVB Financial's CIK carries Form 25
filings in 2017-12 and 2023-05 and is correctly recorded as two distinct
delisting events, not one span.

## Safety

GET-only against `www.sec.gov` and `data.sec.gov`, both already recorded in
V6.02 as this repository's third and fourth external destinations. **No
credentials** — EDGAR is public and neither the adapter nor the pipeline has a
code path that can read an environment variable, dotenv, or credential store,
asserted by AST parse rather than string match. The operator's contact address
is sent to SEC because SEC's fair-access policy requires it of every caller.
Archive paths that traverse directories are refused. No broker, account, order,
or position access; no paper mutation; no live activity; no paid service.
