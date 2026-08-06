# Acceptance review request: V6.03a / V6.04

You are the **independent acceptance reviewer**. You did not write this work.
Your job is to decide whether these exact commits may be marked `accepted` and
merged to `main`. The author (Claude Code) is explicitly not permitted to make
that call about its own work.

## What to review

Repository `dnagassar/algotrader-v1`, PR #13, branch
`claude/full-history-delisting-registry-c1a4ef`, commits:

```
789342e  record V6.03a: registry symbols are over-attributed, join is blocked
be614dd  build exact per-security attribution for the delisting registry
fba4a65  add stage C: attribute delistings to the security that actually delisted
4823f88  add the pure survivorship inflation measurement
0b7779b  keep each ticker beside its fund, and refuse false deaths
f7381f0  measure survivorship inflation: 0.58 points a year, a lower bound
08cf351  record the Codex role takeover and the acceptance gap it leaves
```

## The claims being certified

1. Fund symbol recovery went from **0 of 302** to **214 of 302** delisting
   episodes, yielding **376 distinct dead-fund tickers**.
2. Survivorship inflation for single-country equity ETFs, 2019-2026, is
   **`0.005797` annualised** (36 survivors mean `0.108520`, adding 27 dead funds
   gives `0.102723`).
3. That figure is a **lower bound**.
4. The V6.03 registry was unsafe to join to a price universe, and now is safe.

## How to review this, specifically

**Do not accept on the strength of the author's narrative.** The design notes
and commit messages are well-argued and were written by the same process that
produced seven defects in this stretch, each of which had already produced a
confident, plausible number:

- a regex that matched only unwrapped values, which manufactured a
  "coverage fails by filer type" story that did not exist
- cover-page over-attribution that marked `AAPL` and `ABBV` as delisted
- a "sole candidate" shortcut that attributed the live ETF `CACG` to an
  unrelated delisting
- HTTP 429 read as "no data", producing an inflation of exactly `0.0`
- a cohort classifier that labelled an emerging-markets *bond* ETF as country
  equity
- Form 25 read as "death" when it also covers exchange transfers (`NORW`)
- episode date-stamping that truncated `FRN` a year early

Every one was caught by checking primary evidence, never by re-reading the
argument. Review the same way.

**Check against primary sources, not against this document.** Suggested:

- `PYTHONPATH=src python -m pytest tests/unit/test_delisting_registry.py
  tests/unit/test_edgar_delisting_pipeline.py
  tests/unit/test_survivorship_inflation.py tests/unit/test_dependency_direction.py -q`
  (author reports 141 passing)
- Re-derive claim 2 from the local artifacts rather than trusting the reported
  number: `runs/v6_04_attribution_smoke/stage_c_attributions.jsonl`,
  `runs/v6_04_attribution_smoke/country_equity_cohort.json`, and the price cache
  in the session scratchpad. These are gitignored, so they exist only on this
  machine.
- Spot-check attribution against EDGAR itself for two or three episodes.

## Where the author believes this is weakest

Stated so you can attack it directly, not so you can skip it.

1. **The equal-weighted mean of annualised returns is a questionable
   statistic.** `SCIN` contributes `-0.1722` from only `0.45` years of life,
   with the same weight as a fund with seven years. Annualising a five-month
   return is noisy, and short-lived funds are systematically the failures. This
   could materially move `0.005797` in either direction. A length-weighted or
   cumulative-return construction might be the more defensible measure. **This
   is the single most likely reason to reject the number as constructed.**
2. **Cohort membership is keyword classification hand-written by the author.**
   `GEO` and `EXCLUDE` term lists in the measurement decide which dead funds
   count as country equity. Different lists give a different answer, and the
   author tuned them after seeing an earlier cohort was contaminated.
3. **The 90-day continuation grace is arbitrary**, as is the 365-day episode
   gap. Neither was derived; both were chosen.
4. **Name matching uses substring containment** (`name in target or target in
   name`), which can over-match short fund names.
5. **The 2019+ window** comes from Form 25 `primary_doc.xml` availability, which
   is a filer split rather than a date split, so coverage inside the window is
   uneven in a way that is not characterised.

## What acceptance means here

Return one of:

- **accept** — claims are supported; may merge to `main`
- **accept with conditions** — list exactly what must change first
- **reject** — state which claim fails and the evidence

"Tests pass" is not sufficient evidence for claims 1 and 2; those are empirical
and need the artifacts re-read. If you cannot re-derive a number, say so rather
than accepting it.

If you accept, say explicitly which commits you accepted, so the acceptance is
bound to exact SHAs.
