# V5.89 alpha-program terminal diagnosis

This closes the operator-directed final push. It states what the accumulated
evidence supports, what it does not, and the only honest routes forward. It
introduces no new candidate and grants no authority.

## Result

Sixteen exactly-specified published rule families have now been tested under
outcome-blind preregistration: the NexusTrade monthly stock filters
(V5.64-V5.70), diversified ETF absolute trend (V5.71), turn of month and
nine-sector momentum (V5.72), GEM dual momentum (V5.73), VAA-G4 (V5.74),
Faber global relative strength (V5.75), Halloween (V5.76), SPY inverse
variance (V5.77), static QUAL quality (V5.78), factor momentum styles (V5.84),
Clare risk-parity trend (V5.86), Keller FAA (V5.87), Butler Exhibit 3/4
(V5.88), and Keller BAA-G4/G12 (V5.89).

**Validated alpha candidates: zero.** Every family closed at
`no_candidate_passed` or its family-specific equivalent, without tuning.

## The structural reason

The failures are not random and they are not mostly implementation defects.
Across families the terminal blocker is overwhelmingly the same pair of gates:
the SPY value route and the portfolio-level composite gate.

Every tested family is, by construction, a *diversification or defense* rule:
it spreads capital across asset classes, rotates into bonds or cash on a trend
or breadth signal, or caps risk contribution. Every OOS window available to us
ends 2026-07-31 and is dominated by an exceptional concentrated US-equity
advance — SPY compounded `0.137397873648` annualized at a `0.831767405652`
Sharpe over the V5.88 window (2014-04 onward) and `0.192940267748` at a
`1.171451580490` Sharpe over the V5.89 window (2022-09 onward).

The frozen SPY value route requires a candidate either to stay within one
point of SPY's return while adding 0.10 Sharpe and cutting drawdown 20%, or to
exceed SPY's return outright. A rule that holds bonds, commodities, or
international equity a material fraction of the time cannot do the first
during such an advance, and is not designed to do the second. V5.89 makes the
mechanism explicit and quantitative: removing *only* the canary defensive
overlay improved the aggressive variant's annualized return by 18.14 points
and its Sharpe by 0.821. The published crash-protection feature was the
dominant source of underperformance in the window we are able to score.

In short: the program has been repeatedly asking whether published tactical
allocation beats concentrated US equity over a historic US equity bull run.
The answer is a well-evidenced no. That is a real and useful finding. It is
not the same finding as "these rules do not work," and it must not be reported
as one.

## What the evidence does not support

- It does not support relaxing, re-weighting, or re-scoping any failed gate.
  Every gate was frozen before its reveal; changing one now would convert a
  falsified hypothesis into a manufactured pass. This is the specific failure
  mode the whole protocol exists to prevent.
- It does not support combining closed candidates. Their outcomes are known,
  so any blend selected on that knowledge is outcome-contaminated.
- It does not support promoting any control or ablation. The V5.89 ablation
  `no_canary_g4_always_offensive` returned `0.207342240987` annualized against
  SPY's `0.192940267748` — it beat SPY on return, though not on Sharpe
  (`1.063066618918` versus `1.171451580490`). That number was observed as a
  control inside a scored run. Treating it as a candidate now would be
  selecting a strategy because we saw its result, which is exactly the
  behaviour the ledger forbids. It is a hypothesis, not a finding.

## The three honest routes

1. **Stop the published-family search.** The supply of exactly-specified,
   pre-2023, free-data tactical families with an untouched post-publication
   window is now substantially exhausted. Continuing to enumerate them is
   likely to keep producing the same structural failure at real cost.

2. **Forward-validate one hypothesis on genuinely untouched data.** The only
   statistically clean way to use anything learned above is a
   *current-clock, no-submit, no-backfill forward shadow* that is fingerprinted
   before its first observation and scored only on data that did not exist when
   it was registered. This is slow by construction — meaningful evidence needs
   quarters, not days — but it is the only route that cannot be contaminated by
   what this program has already seen.

3. **Ask the operator to restate the objective, deliberately and on the
   record.** The SPY value route encodes a specific goal: beat concentrated US
   equity. If the operator's actual goal is instead risk-adjusted improvement
   over a balanced portfolio, several closed candidates were genuinely strong
   on that different question — V5.77 SPY inverse variance improved SPY Sharpe
   by 0.102 and drawdown by 15.42 points; V5.71 improved SPY drawdown by 17.42
   points. Changing the objective is legitimate *only* as an explicit,
   documented operator decision made in full view of these results, followed by
   a fresh preregistration and untouched validation data. It is not legitimate
   as a quiet retrofit, and no such change is made here.

## Recommendation

Route 1 combined with Route 2: stop enumerating published families, and spend
the next milestone building the forward-shadow infrastructure that would let a
single registered hypothesis accumulate uncontaminated evidence over time. If
the operator wants Route 3, that is a decision to make explicitly, not one this
document takes.

Validated alpha remains zero. Live capital remains a separate operator hard
gate and nothing in this program has moved it.
