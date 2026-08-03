# V5.87 Keller flexible asset allocation terminal decision

Status: terminally closed without tuning. The engine, protocol, receipt, data,
costs, chronology, comparators, and gates were committed at `ed84fcc` before
the first candidate-specific outcome reveal. No failed parameter was changed,
rescued, substituted, or relabeled.

## Immutable evidence

- Protocol: `v5_87_keller_faa_v3`.
- Canonical data SHA-256:
  `5094981d3c24aa6d018123b6aad20ce9e70583ed09ff6df23778c64ec65c2502`.
- Outcome-blind data manifest SHA-256:
  `e911031d7ab3f9bc9669643ed2ee19de369daa2c1a15492391a04e9231becd08`.
- Engine SHA-256:
  `cc28f363361f3cdc6bcd479d012c8ba1787328c0a723b51d8c71e5e62fab32e5`.
- Evaluation result SHA-256:
  `1f04a0667b24a2988e062d2990860756bf56b230af8f49be218161011168c1db`.
- Artifact manifest SHA-256:
  `2cb31c71f781aed5662adcaa7c659454dfea4950e77810aad9961f28856ccca1`.
- Two complete result and manifest replays were byte-identical.

## Decision-cost evidence

At 5 basis points per unit of one-way turnover, full post-publication OOS
annualized return was `0.030526139451`, Sharpe was `0.409765070988`, maximum
drawdown was `0.192241971122`, and total return was `0.499277739582`.
Fold total returns were `-0.088858649657`, `0.288059481201`, and
`0.277498554700`; fold Sharpes were `-0.266047510471`, `0.719692838605`, and
`0.642944012760`. Stress-cost annualized return remained positive at
`0.026757680784`, but stress Sharpe was only `0.364724983130`.

The candidate diverged from the return-only ablation on 115 monthly decisions
and from static equal seven on all 162 decisions. Distinctness did not create
incremental value:

- Versus the return-only ablation, annualized return delta was
  `-0.028862216176`, Sharpe delta was `-0.174863676693`, and drawdown improved
  by `0.024424444418`.
- Versus static equal seven, annualized return delta was `-0.027899349453`,
  Sharpe delta was `-0.178781546525`, and drawdown improved by
  `0.069170563246`.
- Versus SPY, annualized return delta was `-0.114848651206`, Sharpe delta was
  `-0.480484626258`, and drawdown improved by `0.144757433584`.
- The genuine 80% 60/40 parent plus 20% candidate composite reduced annualized
  return by `0.012291012286` and Sharpe by `0.030245423870`, while improving
  drawdown by `0.034479586379`.

Every terminal gate group failed: common viability, closest ablation, static
baseline, SPY value, and portfolio-level value. The exact route is
`no_candidate_passed`; the candidate is ineligible for shadow, paper, broker,
or live promotion.

## Trust and safety

All external performance figures remained untrusted and controlled no rank or
gate. The replay was offline and credential-free. Network, NexusTrade,
broker/account/order/position access, paper mutation, and live activity were
all false. Existing execution caps, reconciliation, receipts, sleeve ownership,
and live prohibitions were unchanged.
