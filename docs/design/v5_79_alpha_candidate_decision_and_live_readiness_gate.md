# V5.79 alpha-candidate decision and live-readiness gate

## Terminal decision

- Validated alpha candidates: **0**.
- Execution-adapter candidates: **0**.
- New untouched no-submit shadow routes: **0**.
- Paper-promotion routes: **0**.
- Live-capital ready: **false**.
- Live authorized: **false**.
- Classification:
  `hard_gate_no_validated_alpha_and_live_authority_false`.

This is not a claim that every tested rule lost money. Several candidates had
positive returns, useful drawdown control, and reproducible portfolio effects.
It is the narrower and more important conclusion that none cleared every
outcome-blind alpha, fold, cost, baseline, and portfolio gate. A failed gate is
not repaired, reweighted, or relabeled as validation.

## Tight research shortlist

These are the strongest *research findings*, ordered by decision quality rather
than external/source performance. Every route remains closed.

| Rank | Exact candidate | OOS annual return | Sharpe | Max drawdown | Integrity | Portfolio | Terminal blocker |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 1 | V5.77 `spy_inverse_variance_long_cash_proxy` | 10.55% | 0.946 | 18.28% | pass | pass | lagged SPY by 4.42 points annually and did not win two folds |
| 2 | V5.75 `faber_global_asset_relative_strength_top2_12m_proxy` | 9.60% | 0.758 | 23.76% | pass | fail | static Sharpe edge was 0.094, SPY return/Sharpe gate failed, composite Sharpe fell |
| 3 | V5.71 `diversified_etf_absolute_trend` | 7.86% | 0.888 | 16.28% | pass | not admitted | static equal-weight and SPY value gates failed |

V5.77 is the clearest building block: it exceeded SPY Sharpe by 0.102,
improved SPY drawdown by 15.42 points (45.77% relatively), used 55 distinct
bounded OOS target weights, and improved the static-core composite Sharpe by
0.035 while reducing composite drawdown by 3.01 points. It remains closed
because return capture and fold consistency were explicitly required before
outcome inspection.

V5.75 is the clearest cross-asset ranking building block: all five assets were
held, all common integrity gates passed, annualized return exceeded its static
five-proxy comparator by 2.39 points, and drawdown improved by 2.70 points. It
remains closed because it did not clear the preregistered static Sharpe edge,
SPY value gate, or composite Sharpe gate.

V5.71 is the clearest independent defensive-trend building block. It passed
viability, cost, diversification, and replay integrity and improved SPY
drawdown by 17.42 points, but it failed both fixed value comparators and is
already terminally closed.

“Building block” is descriptive research language only. It does not authorize
mixing failed candidates after seeing outcomes. A combined rule would be a new
hypothesis requiring primary rationale, preregistration, untouched future data,
and its own decision gates.

## Exact terminal tournament ledger

| Milestone | Candidate/family | Terminal route | Key outcome |
| --- | --- | --- | --- |
| V5.64-V5.70 | NexusTrade-inspired monthly stock-filter family | `close_stock_filter_family` | frozen forward baseline, cross-asset, and composite gates failed |
| V5.71 | five-ETF absolute trend | `close_diversified_etf_absolute_trend` | comparator value gates failed |
| V5.72 | turn of month | `close_candidate` | candidate, common, and portfolio gates failed |
| V5.72 | nine-sector 6x6 momentum | `close_candidate` | static/SPY and portfolio Sharpe gates failed |
| V5.73 | global-equities dual momentum | `close_global_equities_dual_momentum_12m_proxy` | diversified baselines and portfolio Sharpe failed |
| V5.74 | VAA-G4 | `close_vigilant_asset_allocation_g4_13612w_proxy` | fold/common, baseline, and portfolio return gates failed |
| V5.75 | global top-two relative strength | `close_faber_global_asset_relative_strength_top2_12m_proxy` | candidate-specific and portfolio Sharpe gates failed |
| V5.76 | Halloween SPY/BIL | `close_halloween_spy_bil_seasonal_proxy` | common Sharpe, balanced baseline, post-2021, and portfolio Sharpe failed |
| V5.77 | SPY inverse variance | `close_spy_inverse_variance_long_cash_proxy` | return-capture and fold-consistency gates failed |
| V5.78 | static QUAL quality sleeve | `close_static_qual_quality_sleeve_proxy` | PBUS/SPY, common Sharpe, and portfolio gates failed |

The sealed Crypto Tournament V2 is not part of this ledger because outcome
inspection remains forbidden before `2026-08-13T00:00:00Z`. No partial
ranking, preference, or inferred outcome exists.

## Evidence bindings

| Milestone | Protocol SHA-256 | Receipt SHA-256 | Result SHA-256 | Manifest SHA-256 |
| --- | --- | --- | --- | --- |
| V5.71 | `afa4254ceac06f643fd51fd2df63364ce14a38f01ba8392e664d8e478bc57d17` | `ca782882cb499ea2e956fc36658df4f76f88fff06b4a69b293ced4a70c213525` | `8ff0b4af228e4c08f65011b5f250a063efe888b2859f89d4d968d3ab710edb75` | `a7fee42cbf02df5ebeeda6f13fc42fca6b68b5d7d1bcd5480b9c5d8a88e704fd` |
| V5.72 | `eb3061e74f5444746d19480fc9283f3189b86ebb395369e9ee19a33f3dd8d768` | `827ed0bdeece4bb373eb29517c2c0cf1dd383a89f64be958d1cf1357e22c807c` | `08c9b96bdac4af19e6cd858d0f87d589e4c57cdc22548d804141780cfda86602` | `d1f25159214719ae7fdf1a03f5cc6fbda767bffea6b8d2cc25dab05f24c7b15e` |
| V5.73 | `27de22520bccd1ac61063717ec718ed0bda6aef6ed8233d21846e60450a642d0` | `0c5c2126ad954efffc5eba7c7bf9500f7b53747f1d3febce44e1e845a1a08818` | `877bafd093a2cf68c4947f17591ff5f0a415815ddeea2b11d6c819205d7ddbd4` | `887ed0d41571b0fd129d8ce67db6689ad072ab893095174220f235a40613294a` |
| V5.74 | `cc40b38875e828b4ef0bc4662eaa5e84755989521f1e623dade320c95c06dcf5` | `59595161f75c4b5e85a261d281cb722d596f95869e2b943940da010ce925b37f` | `3e0ca77f299438d1a0af982560f76cabbbc0c7b473471787a9906373ee89520d` | `dfd36192903bc4d6fe24838aa805d3ccd6541964a427dd42b81e9efaf95b3235` |
| V5.75 | `e00516cdcb6aa6df228387dc171906d0259c11a001ecc9b3beb8ec4d55d4eb5e` | `5e99265971996f1821f384bb8121a8b8252b73bdef27b3bd9b215bceeff4f2e7` | `ca5f32f1f1298f521b4af49f474fbe20a999621eed99827fa55cf73fe717b5c8` | `001b938f78e64eb71520532c3f42a34f4e3e46c7e439262f30f81a428c9614f8` |
| V5.76 | `e306ef9f20803778f86857521977578b02aa7af13ca7033baa09dbdbd4cfdf82` | `f08edaf8f93adc040afbfbc6583741ae7c6518358961194790f8e5a01772a3ad` | `03b4992d60013b6398aa67613952f484aad63f46cb1ed9a60db88f7b98bd1afa` | `9081a641d9d0baf626164cbd3782fee29c11febcc03083bc3a35ed7916d45a25` |
| V5.77 | `3b6ecd43ecef4e6f86bcc5279a179d8e559e89b14f883da9c1a59d7eb8dc4803` | `a8c0d33a1779abc535066e9417319454f90e5b0258f63766bb8ae6e2d133d059` | `5036dc5d15dd5805190fd0040554e150c0eadd02a497b73cef0a1500df6fd2d9` | `e204b963a2866f7211fc58a586e9c124d237267eae763981dc19d673291ec9f7` |
| V5.78 | `1b7ff237b84c287dc5815eb918baec458735bb41a14f04d98baa98d754efa4bf` | `4479281634535e9e8ebfee473ca6e37905073a7c9cef6ab44557a29ede7f9f8a` | `047ba65af51a88397b49fc3510d13a3720b42923d6caf6c51ddaba9a3ec21bab` | `ecb186a17a70953e51d155a4f28394f17f4dc7cb9a3e0f1fa5e7b2978ea850bd` |

Generated run bytes remain ignored evidence; the tracked protocols and receipts
are authority. Every terminal replay was offline, deterministic, credential-
free, network-free, broker-free, paper-mutation-free, and live-free.

## Source and data trust

Primary research authorities:

- McConnell and Xu, turn of month:
  <https://business.purdue.edu/faculty/mcconnell/publications/Equity-Returns-at-the-Turn-of-the-Month.pdf>
- Moskowitz and Grinblatt, industry momentum:
  <https://doi.org/10.1111/0022-1082.00146>
- Antonacci, global equities momentum:
  <https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2042750>
- Keller and Keuning, VAA:
  <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3002624>
- Faber, relative strength:
  <https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id1585517.pdf>
- Bouman and Jacobsen, Halloween:
  <https://doi.org/10.1257/000282802762024683>
- Moreira and Muir, volatility management:
  <https://doi.org/10.1111/jofi.12513>
- Asness, Frazzini, and Pedersen, quality:
  <https://doi.org/10.1007/s11142-018-9470-2>

Canonical daily data is Tiingo EOD `adjClose -> adjusted_close`, with provider
split/dividend-adjusted-close semantics:
<https://www.tiingo.com/documentation/end-of-day>. External performance
numbers—including NexusTrade, source papers, and fund pages—were untrusted and
unused in ranking, gates, or promotion.

## Live-capital readiness gates

| Gate | State | Required evidence |
| --- | --- | --- |
| validated alpha | blocked | at least one exact preregistered candidate must pass every terminal gate |
| untouched future shadow | absent | must begin only after a valid terminal selection; no backfill |
| strategy registration/adapter | absent | deterministic decision-time adapter and scheduler bound to passing evidence |
| target-to-order translation | absent | candidate-owned sleeve, finite caps, venue/orderability, partial-fill policy |
| paper qualification | absent | lifecycle receipts, independent reconciliation, recovery, monitoring, kill/loss proof |
| aggregate portfolio risk | incomplete | daily loss, drawdown, reserve, correlated-exposure and sleeve interaction proof |
| existing order state | blocked | M376 SPY order remains nonterminal and forbids overlapping SPY submission |
| alert delivery | incomplete | durable delivery and escalation proof remains false |
| coordinated recovery | incomplete | sleeve-ledger restore/restart proof is absent |
| live authority | hard false | operator gate; current repository is not live-authorized |

Adjusted closes are research total-return marks, not executable fills. Existing
V5.57 safety ownership and caps remain unchanged and do not transfer to any
research candidate: $25 entry-order notional, $60 aggregate marked SPY entry
exposure, one broker order per secure cycle, and two sleeve intents per UTC
day. No third sleeve exists.

## Next milestone

Do not tune or combine these closed candidates. The nearest preregistered
untouched decision is Crypto Tournament V2 at
`2026-08-13T00:00:00Z`, after its full receipt-bound OOS window closes.
Until then, only completeness/receipt accrual is valid. A separate new alpha
family is permitted only with new primary rationale, an outcome-blind protocol,
and untouched data; it cannot reuse this ledger to select parameters.
