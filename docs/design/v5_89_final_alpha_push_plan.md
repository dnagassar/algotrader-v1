# V5.89 final alpha push plan

Status: operator-directed final push to find a validated alpha candidate,
authorized 2026-08-03 with three hard constraints: no credential exposure, no
new paid services, and no live capital. Everything else in this plan operates
inside the existing research discipline: outcome-blind preregistration, exact
published rules, frozen gates, atomic reveal, and no tuning after reveal.

## Where the search stands

The V5.79 ledger plus V5.84 and V5.86-V5.88 terminally closed every tested
family: NexusTrade stock filters, five-ETF absolute trend, turn of month,
nine-sector momentum, GEM dual momentum, VAA-G4, Faber global relative
strength, Halloween SPY/BIL, SPY inverse variance, static QUAL, factor
momentum styles, Clare risk parity trend, Keller FAA, and Butler Exhibit 3/4.
Zero candidates passed; validated alpha is zero.

The recurring terminal blocker is the SPY value route: since 2014 SPY compounded
near 13.7% annualized with a 0.83 Sharpe, and diversified or defensive
allocation rules published before 2014 have not kept within a point of that
return. The honest remaining search space is therefore published,
exactly-specified rules that (a) concentrate in high-momentum growth assets
while risk is on, (b) have a mechanical crash-avoidance overlay, and (c) were
published recently enough that their aggressive posture is a frozen author
choice rather than our tuning.

## The chosen family

V5.89 tests Keller and Keuning's Bold Asset Allocation (BAA, SSRN 4166845,
listed July 2022) in its two published variants as one atomic candidate pair:

- `baa_g4_aggressive_proxy` (top-1 of a four-asset offensive universe);
- `baa_g12_balanced_proxy` (top-6 of a twelve-asset offensive universe).

Rationale: it is the strongest untested member of the Keller family (VAA-G4
and FAA are already closed), its offensive universe includes QQQ, its exact
rules are public and independently transcribed, its post-publication window
2022-09 through 2026-07 contains both a bear regime and a growth bull, and its
full data footprint is free-tier Tiingo EOD through the repository's existing
GET-only allowlisted adapter. Its true OOS window is short (47 action months);
that weakness is frozen into the preregistration and folds, and any pass
routes only to a no-submit forward shadow, never directly to paper or live.

## Constraint compliance

- No credential exposure: data acquisition uses the existing refresh adapter;
  only the child adapter loads `TIINGO_API_KEY` from `.env`; wrappers fail
  closed on credential-bearing ambient environments and print booleans only.
- No new paid services: Tiingo free-tier EOD (already provisioned) and free
  public author/tracker publications are the only external inputs.
- No live capital: the tournament is offline research; a full pass earns at
  most a fingerprinted current-clock no-submit shadow. Paper promotion and
  live authority remain separate operator hard gates.

## Sequence

1. Consolidate: fast-forward `main` to the verified V5.88 closure tip and push
   `origin/main` (full offline verifier is the gate).
2. Freeze `docs/design/v5_89_keller_bold_asset_allocation_preregistration.md`
   before any data request or scoring; commit.
3. Acquire the seventeen-symbol canonical panel
   (SPY, QQQ, IWM, VGK, EWJ, EEM, VNQ, DBC, GLD, TLT, HYG, LQD, EFA, AGG,
   TIP, BIL, IEF; 2007-07-26 through 2026-07-31) via exact one-shot requests;
   build the outcome-blind combined canonical CSV, manifest, and receipt;
   commit the admission.
4. Implement the frozen replay engine and focused tests mirroring the V5.88
   architecture; commit before reveal where the session allows.
5. Run the tournament once; record the terminal decision without tuning;
   update the single mutable handoff; push.

## If V5.89 closes without a pass

The preordered successor is Keller's Hybrid Asset Allocation (HAA, author
publication February 2023,
<https://indexswingtrader.blogspot.com/2023/02/introducing-hybrid-asset-allocation-haa.html>),
the last major untested exactly-specified aggressive family. If HAA also
closes, the honest terminal statement of this program is that no published
tactical family cleared SPY-relative validation gates on its post-publication
window, and the remaining preregistered decision is the sealed Crypto
Tournament V2 reveal at 2026-08-13T00:00:00Z. Combining or tuning closed
candidates remains forbidden; any new hypothesis needs new primary rationale
and untouched data.
