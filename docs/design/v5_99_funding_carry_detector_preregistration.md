# V5.99 perpetual funding carry detector preregistration

Status: frozen before any V5.99 return, metric, count, or route was computed.

Second structural hypothesis, after V5.98. Tests a payment that is **forced by
contract design** rather than by anyone's opinion about price.

## 1. The structural claim

A perpetual futures contract never expires, so exchanges use a *funding rate*
to keep it anchored to spot. At each funding timestamp, one side pays the
other. When the perpetual trades above spot — the usual state, because
leveraged long demand exceeds leveraged short demand — **longs pay shorts, by
contract, regardless of what price does next.**

A position that is short the perpetual and long the equivalent spot is
approximately delta-neutral: price direction largely cancels between the legs.
What remains is the funding stream plus whatever the basis does.

This is the purest forced-payer structure available with free data. Nobody
chooses to pay funding because they think it is a good trade; they pay it
because they hold a leveraged position through a timestamp and the contract
compels it.

## 2. The question that actually matters

Collecting funding is not automatically an edge. The honest question is:

> Is the funding stream **compensation for tail risk**, or a **genuine
> inefficiency**?

The carry trade's known failure mode is violent. In a sharp rally the short
perpetual leg loses fast, margin is called, and the position can be liquidated
before the spot leg can be sold — precisely when funding was most attractive.
Positive average carry with catastrophic drawdowns is a risk premium, not alpha,
and must not be reported as alpha.

The gates below therefore require **both** a positive cost-surviving carry
**and** a bounded drawdown. A strategy that earns steadily and then gives it all
back fails, by design.

## 3. Data contract

- Source: Binance public USD-margined futures and spot REST endpoints.
  Read-only, unauthenticated, GET-only, no credentials of any kind.
- **This adds a third external host to a repository deliberately limited to
  two.** The addition is recorded here rather than made silently. Same
  architecture as the existing adapters: destination-allowlisted, GET-only,
  receipt-bound, credential-free, with a dry-run mode that performs no network
  access.
- Series required per symbol:
  1. funding rate history (8-hour settlement timestamps),
  2. perpetual mark/close klines at 8-hour resolution,
  3. spot close klines at 8-hour resolution.
- Symbols, frozen: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`. These match the existing
  crypto universe and are the three most liquid perpetuals; illiquid
  perpetuals are excluded because delisted contracts would reintroduce exactly
  the survivorship problem V5.98 documented.
- Coverage: each symbol's full available history through `2026-07-31`, with the
  admitted panel being the common intersection across all three series and all
  three symbols. At least **3,000** common 8-hour intervals are required, or the
  milestone blocks.

## 4. Exact rule

For each symbol independently, at each funding timestamp `t`:

- **Signal:** the funding rate settled at `t`. It is known at `t` and is not a
  forecast.
- **Position:** if funding at `t` is strictly positive, hold short 1 unit of
  perpetual and long 1 unit of spot over the interval `t` to `t+1`. Otherwise
  hold nothing. No leverage, no sizing, no shorting of spot, no discretion.
- **Return over the interval:**
  `funding_received + spot_leg_return - perp_leg_return - costs`,
  where each leg return uses closes at `t` and `t+1`.
- **Costs:** entry and exit are charged whenever the position changes state, at
  **5 basis points** per leg per side for the decision case and **15 basis
  points** for stress. Crypto costs are materially worse than equity costs, so
  the stress case is load-bearing rather than decorative.
- **Portfolio:** equal-weight across the three symbols, rebalanced at each
  timestamp.

Selection uses only information available at `t`; every return is measured
strictly afterwards.

## 5. Frozen gates

**Primary.** Net annualised return, after decision costs, is strictly positive
across the full admitted panel.

**Secondary, all required:**

- **Cost robustness:** still positive at 15 basis points.
- **Tail bound — the gate that decides risk-premium versus edge:** maximum
  drawdown of the equal-weight carry portfolio is at most **0.15** at decision
  costs. This is deliberately tighter than the 0.20 ensemble ceiling because a
  delta-neutral carry claiming to be market-independent has no excuse for a
  large drawdown.
- **Regime consistency:** the panel is split into four equal consecutive
  quarters by interval count, fixed by index and not by any chosen date, and
  net return must be positive in at least **3 of 4**.
- **Not a single-symbol artifact:** net return is positive for at least **2 of
  3** symbols individually.
- **Integrity:** two complete replays byte-identical; funding applied only at
  settlement timestamps; no lookahead in signal or costs.

**Reported but not gated:** funding paid versus received, share of intervals
with positive funding, per-symbol returns and drawdowns, worst single-interval
loss, and basis behaviour during the worst drawdown.

## 6. Routes

A complete pass routes to
`structural_evidence_supports_forward_shadow_registration` and nothing further.
It is historical evidence, it is not validated alpha, and it authorises no
paper, broker, or live activity. Execution would additionally require
derivatives venue access this repository does not have and is not seeking.

Any failure routes to `close_detector_without_tuning`. The threshold, funding
sign rule, holding interval, cost assumptions, symbol set, and drawdown ceiling
may not be adjusted afterwards.

## 7. Honest expectations

The funding carry is a well-known, widely-run trade. Institutional desks and
funds run it at scale with better fees, better execution, and cross-venue
netting. The prior is therefore that any surviving return is thin and is
compensation for tail risk rather than inefficiency — which is exactly what the
drawdown gate is built to detect.

Two further limits, stated in advance:

- **Venue concentration.** Using one exchange means the result carries that
  exchange's idiosyncrasies. It is not a claim about perpetual funding
  everywhere.
- **No liquidation modelling.** This measures the carry as if margin were never
  called. Real execution faces margin calls precisely at the worst moments, so
  the true tail is **worse** than anything reported here. A pass would
  therefore be an upper bound on attractiveness, never a lower bound.

## 8. Safety

Read-only public market data. No credentials are requested, loaded, printed, or
persisted. No broker, account, order, or position access. No paper mutation. No
live activity. Live capital remains an operator hard gate untouched by this
document.
