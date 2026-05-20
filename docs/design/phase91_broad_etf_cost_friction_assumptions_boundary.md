# Phase 91 - Broad ETF Cost / Friction Assumptions Boundary

## Purpose

This document defines policy questions and readiness gates for future
transaction-cost, spread, slippage, liquidity, turnover, expense-ratio, tax,
and implementation-friction assumptions before broad ETF research can make
performance, comparability, strategy-readiness, or trading-readiness claims.

It is documentation-only. It exists to prevent synthetic or local-snapshot
replay results from being treated as economically meaningful without explicit
cost and friction assumptions, liquidity constraints, turnover treatment, and
implementation limits.

## Boundary

Phase 91 may define cost and friction interpretation rules only.

It does not approve:

- any cost model
- any spread assumption
- any slippage assumption
- any liquidity threshold
- any expense-ratio treatment
- any tax treatment
- any source
- any data
- any universe
- any benchmark
- any cash proxy
- any methodology
- any parameter set
- any evidence
- any return construction
- any no-lookahead protocol
- any strategy validation
- any trading use

No transaction-cost model, spread estimate, slippage estimate, liquidity rule,
turnover rule, rebalance rule, expense-ratio adjustment, tax treatment,
implementation-friction assumption, ETF ticker, source, data file, benchmark,
cash proxy, methodology, parameter, evidence package, strategy result, or
trading behavior becomes eligible for implementation or research claims.

## Cost And Friction Categories

Future broad ETF work must label cost and friction categories explicitly.
None of these categories is approved in this phase.

| Category | Future question | Phase 91 boundary |
| --- | --- | --- |
| Explicit commissions | Whether orders incur per-share, per-order, ticket, exchange, regulatory, or commission costs. | Not approved; zero-commission retail assumptions do not make execution costless or strategy-ready. |
| Bid/ask spread | Whether buys and sells cross the spread, trade at mid, use close labels, or use another executable-price convention. | Not approved; spread treatment requires later source, timing, quote availability, and fill-rule approval. |
| Slippage | Whether modeled fills differ from selected reference prices because of timing, volatility, order type, or market conditions. | Not approved; no slippage formula, constant, or dynamic rule is selected. |
| Market impact | Whether the strategy's own order size moves the execution price. | Not approved; requires later order-size, liquidity, participation-rate, and capacity assumptions. |
| Liquidity constraints | Whether instruments or trades are limited by volume, dollar volume, spread, stale quote, halt, or AUM rules. | Not approved; this phase selects no threshold and excludes no ETF. |
| Turnover | How much capital is traded over a period and which transitions count as buys, sells, exits, entries, or reallocations. | Not approved; turnover must be defined before cost-aware claims. |
| Rebalance frequency | Whether the strategy changes allocations daily, weekly, monthly, event-driven, or under another schedule. | Not approved; frequency changes cost exposure and comparability. |
| ETF expense ratios | Whether fund-level expenses are already reflected in price or NAV behavior and whether any separate treatment is needed. | Not approved; source and return-basis policy must be resolved first. |
| Dividend/distribution interaction | Whether distributions, reinvestment, ex-date/payment-date timing, and total-return construction interact with expenses and fees. | Not approved; double-counting and omission risks remain unresolved. |
| Borrow or short costs | Whether borrowing, locate fees, short rebates, hard-to-borrow treatment, or margin costs could matter if a later strategy ever shorts. | Out of scope for long-only assumptions here; not approved for any future short path. |
| Taxes | Whether taxable distributions, realized gains, holding periods, wash sales, or account type affect after-tax results. | Out of scope here and must be handled by a separate later tax policy before any after-tax claim. |
| Broker-specific fees | Whether a later operational broker context imposes fees, payment-for-order-flow effects, sweep terms, or account-level charges. | Future operational context only; not research approval, broker approval, or trading approval. |

These labels are assumptions taxonomy only. They do not prove economic
completeness, cost awareness, implementation readiness, or executable fills.

## Spread And Slippage Interpretation Risks

Close-to-close replay does not model executable prices. A close label can
describe an observation, but it does not prove that an order could have been
filled at that close, at the midpoint, or within the displayed spread.

Same-close signals do not imply executable fills. A future protocol must
separate the price used to compute a signal from the time and price at which an
action could be submitted and filled.

Next-open and next-close assumptions require explicit timing rules. A
next-open assumption would need open availability, order-entry timing, gap
treatment, auction behavior, missing-open handling, and fill convention. A
next-close assumption would need a decision cutoff, action timestamp,
missed-return treatment, and evidence that the close was not used before it
was knowable.

Stale quotes and wide spreads can distort ETF backtests. An ETF with stale or
thin quote activity may appear stable, low-risk, or profitable in a replay
while being difficult or costly to trade in practice.

Small-volume ETFs can produce unrealistic fill assumptions. Reported daily
price rows do not prove that meaningful order size could trade without market
impact, delayed fills, partial fills, or unfavorable execution.

Synthetic replay rows cannot estimate real spread or slippage. Synthetic
fixtures can test deterministic plumbing only. They cannot establish spread
distribution, quote depth, fill quality, liquidity, capacity, or transaction
costs for real ETFs.

## Liquidity-Readiness Questions

Future broad ETF research must answer liquidity questions before it can claim
cost-aware, comparable, or strategy-ready results. This phase selects no
thresholds and approves no exclusions.

Questions include:

- average share volume over the relevant lookback window
- average dollar volume over the relevant lookback window
- whether bid/ask spread observations are available from an approved source
- how ETF AUM is measured, dated, revised, and used, if used at all
- how trading halts are detected and handled
- how stale quotes are detected and handled
- how missing quotes are detected and handled
- how ETF sessions align when underlying markets have different hours,
  holidays, closures, or local-market timing
- whether ETF premium or discount to NAV matters for return interpretation or
  execution assumptions
- whether creation/redemption context is needed later for capacity or
  liquidity research

Creation/redemption mechanics are future research context only. They do not
approve ETF selection, capacity, execution quality, or liquidity thresholds.

## Turnover And Rebalance Implications

Turnover calculation must be explicit before any cost-aware or net-performance
claim. A future policy must state whether turnover is measured by traded
notional, one-way turnover, two-way turnover, portfolio weight change, gross
exposure change, or another rule.

Monthly, weekly, daily, and event-driven rebalance assumptions can create
materially different costs. A result using one rebalance schedule must not be
compared to another as if costs are identical.

Cash transitions and re-entry events generate trading friction. Moving from a
risk asset to cash, from cash back into risk assets, from one ETF to another,
or from partial exposure to full exposure can all create buys, sells, spreads,
slippage, and possible market impact.

Benchmark and cash comparisons require consistent cost treatment. If a
strategy result includes costs but a benchmark or cash comparison does not, or
the reverse, the comparison may be misleading unless explicitly labeled and
separately approved.

Frequent switching can make gross results misleading. A high gross return,
low drawdown, or attractive timing result is not economically meaningful until
turnover, rebalance frequency, implementation timing, and cost assumptions are
documented and approved.

## Expense-Ratio And Total-Return Interaction

ETF expense ratios may already be reflected in NAV or market-price behavior
depending on the source, field, and return basis. A separate expense deduction
could double-count fees if the selected series already incorporates fund
expenses through NAV or price behavior.

Vendor total-return data may handle distributions differently. A total-return
series may encode reinvestment assumptions, ex-date or payment-date choices,
corrections, fund expenses, and vendor methodology decisions that are not
obvious from the field name.

Price-return-only data excludes distributions. It may omit dividends,
capital-gain distributions, and other cash flows unless a later return
construction policy explicitly adds them.

Double-counting or omitting expenses and distributions must be avoided. A
future policy must document whether expenses, dividends, distributions,
reinvestment, and taxes are embedded in the source, calculated separately,
excluded, or explicitly out of scope.

Source and return-basis policy must be resolved before expense-treatment
claims. Phase 91 does not decide whether expense ratios should be modeled
separately, inferred from price behavior, ignored, or handled through a
vendor-provided total-return series.

## Future Approval Gates

Before any future broad ETF research may claim cost-aware results, a later
phase must document at minimum:

- cost model candidate remains candidate-only until separately approved
- spread and slippage assumption documented
- rebalance frequency documented
- turnover calculation documented
- liquidity screen or exclusion policy documented
- expense-ratio treatment documented
- benchmark and cash cost treatment documented
- return-basis interaction documented
- no-lookahead and action timing documented
- normal pytest remains synthetic, offline, credential-free, provider-free,
  broker-free, and independent of real market data

Passing these gates would still not by itself approve a cost model, friction
model, liquidity rule, source, data, universe, benchmark, cash proxy,
methodology, parameter, evidence, return construction, no-lookahead protocol,
strategy validation, implementation, or trading use. Any approval would need a
separate explicit phase.

## Relationship To Prior Phases

Phase 83 defined broad ETF source-path and local snapshot readiness criteria.
Local snapshot metadata may describe future file or source context, but it
does not provide executable prices, quote depth, spread observations, fill
quality, or liquidity proof.

Phase 88 defined local snapshot return-basis and as-of interpretation rules.
Return-basis and as-of rules are necessary for honest historical
interpretation, but they do not solve trading frictions, transaction costs,
turnover, executable fills, or implementation limits.

Phase 89 defined broad ETF universe, inception, and survivorship boundaries.
Universe liquidity must be resolved before any strategy-readiness claim
because an eligible historical instrument is not automatically liquid,
tradeable at modeled size, or free from stale quote and fill risks.

Phase 90 defined benchmark and cash timing boundaries. Benchmark and cash
comparability requires consistent cost assumptions, including whether costs
apply to the strategy, benchmark, cash transitions, rebalances, or all of
them.

Cost and friction policy remains separate from strategy validation. Even a
future documented cost model would not validate a strategy, approve
parameters, or authorize trading.

## Explicit Non-Claims

Phase 91 is:

- not cost model approval
- not friction approval
- not liquidity approval
- not source approval
- not data approval
- not universe approval
- not benchmark approval
- not cash proxy approval
- not methodology approval
- not parameter approval
- not evidence approval
- not return-construction approval
- not no-lookahead approval
- not strategy validation
- not trading readiness

It also adds no real data ingestion, no real market data, no real ETF tickers,
no benchmark comparison, no cash return series, no rate series, no
expense-ratio series, no spread series, no liquidity screen, no threshold, no
ranking, no scoring, no recommendation, no candidate discovery, no replay
metrics, no report rendering, no manifest-to-planning bridge, no signal or
evaluator behavior, no advisory integration, no governance behavior, no
broker, order, fill, portfolio, runtime, paper, live, or trading behavior, and
no LLM, network, API, provider, rate-series, or market-data call.

## Decision

Decision: cost and friction assumptions boundary only.

The project is not ready to select or use a cost model, spread assumption,
slippage assumption, liquidity threshold, turnover rule, rebalance-cost rule,
expense-ratio treatment, tax treatment, or implementation-friction assumption.
Future work may continue with a research-readiness checkpoint, but broad ETF
performance and comparability claims remain blocked until a later explicit
phase resolves the approval gates above.

## Remaining Blockers

- no approved source
- no approved data
- no approved local snapshot
- no approved ETF universe
- no approved ETF ticker
- no approved benchmark
- no approved cash proxy
- no approved cost model
- no approved spread assumption
- no approved slippage assumption
- no approved liquidity threshold
- no approved liquidity screen
- no approved turnover calculation
- no approved rebalance frequency
- no approved rebalance-cost treatment
- no approved expense-ratio treatment
- no approved distribution interaction policy
- no approved tax treatment
- no approved broker-fee treatment
- no approved methodology
- no approved parameter set
- no approved evidence
- no approved adjustment policy
- no approved return basis
- no approved return construction
- no approved no-lookahead/as-of policy
- no approved action timing
- no approved universe/benchmark/cash cost comparability policy
- no implementation-readiness claim
- no strategy-validation claim
- no trading-readiness claim
