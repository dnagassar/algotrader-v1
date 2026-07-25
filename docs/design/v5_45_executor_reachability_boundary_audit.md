# V5.45 Executor Reachability Boundary Audit

## Status And Scope

- Milestone: `V5.45 — read-only executor reachability boundary audit`.
- Parent milestones: `V5.39 — gated offline autonomy executor`
  (`docs/design/v5_39_gated_offline_autonomy_executor.md`), `V5.38 — offline
  autonomy next-action planner`, `V5.37 — offline cross-lane autonomy
  supervisor`, and `V5.44 — zero-execution outcome truthfulness`
  (`docs/design/v5_44_zero_execution_outcome_truthfulness_contract.md`),
  whose "Next Highest-Leverage Safe Action" defined this audit's exact
  charter.
- This is a **read-only audit**. It changes no executor, planner,
  supervisor, or CLI source file and no test file. It grants no
  implementation authority. It inspects and documents only.
- Base commit: `1394be0`, the accepted and pushed tip of
  `origin/claude/v5.44-zero-execution-truthfulness` — **not** `main`.
  `origin/main` was `135da69` at the time of this audit (verified by
  `git fetch` + `git rev-parse origin/main`); `V5.44` had not yet been
  merged to `main`. This audit was forked from `1394be0` per this
  milestone's explicit starting-commit instruction, audited from
  `claude/v5.45-executor-reachability-audit`.
- Outcome: **no source change is authorized by this audit.** No safe
  candidate for a newly-reachable offline action was found. See
  "Conclusion" below and the exact reasoning under "Candidates
  Considered And Rejected".
- Not strategy-profit, paper-order, broker-mutation, activation, or
  live-trading evidence. No credential was read, no network or broker
  call occurred, and no file outside `docs/` was modified while producing
  this audit.

## Method

Static, offline inspection of the three modules that make up the
observe -> classify -> act chain, their CLI wiring, and their tests. No
code executed with `apply=True`; no lane artifact was read (no `runs/`
tree exists in this worktree). Every claim below is either a direct file
citation or a re-derivation matching an existing, currently-passing test
in the repository (cited by name), not new evidence.

## The Reachability Chain

```
LaneSpec.next_actions[normalized_state]              (autonomy_supervisor.py)
  -> lane_summary["next_action"]                      (_summarize_lane)
  -> report["lanes"][i]["next_action"]                (build_autonomy_supervisor_report)
  -> action["recommended_action"]                     (autonomy_next_plan._plan_lane)
  -> classify_action(recommended_action)              (AUTONOMY_ACTION_CLASSIFICATION lookup)
  -> ActionClass.execution_class / .offline_runnable / .command
  -> plan["actions"][i]                               (build_autonomy_next_plan_from_report)
  -> _partition_actions(plan)                         (autonomy_offline_executor.py)
       - offline_runnable is not True         -> skipped (not_offline_runnable)
       - recommended_action not in ALLOWLIST  -> skipped (requires_operator_input /
                                                  not_allowlisted)
       - else                                 -> eligible, argv = ALLOWLIST[token]
  -> build_offline_execution_ledger()                 (executes only if apply=True
                                                        and preflight_ok)
```

Each arrow is a single, unambiguous function call; there is no second
path into `_partition_actions` and no second registry that can populate
`recommended_action`. `_plan_source`/`_supervisor_report` accept only
`autonomy_supervisor_report` or `autonomy_next_plan` records (rejecting
anything else with `ValidationError`), which closes the chain to exactly
one producer.

### 1. `AUTONOMY_EXECUTOR_ALLOWLIST` — every token

`src/algotrader/execution/autonomy_offline_executor.py:100-104`. Exactly
one entry:

| Token | argv |
| --- | --- |
| `rerun_offline_daily_cycle_chain` | `("etf-sma-offline-daily-cycle-rerun-m446",)` |

Proven exhaustive by `test_allowlist_is_the_verified_offline_command_only`
(`tests/unit/test_autonomy_offline_executor.py:100`).

### 2. Every lane `next_actions` producer — every emittable token

`AUTONOMY_SUPERVISOR_LANES` (`autonomy_supervisor.py:271-436`) has six
`LaneSpec` entries; each declares a complete `next_actions` map over all
seven normalized states (`blocked`, `unknown`, `attention_required`,
`stale`, `waiting`, `nominal`, `absent`). The default fallback
`"operator_review_lane_evidence"` (`LaneSpec.next_action`, line 264) is
therefore dead code for the current registry — every lane supplies all
seven keys — but remains a fail-closed net if a future lane omits one.
Plus one aggregate token when every lane is absent
(`ALL_LANES_ABSENT_ACTION`, line 96).

The 6 x 7 = 42 per-lane `(lane, state) -> token` dict entries are **not**
42 distinct tokens: 4 pairs of states collapse onto the same token
within their own lane (`spy_market_data_soak`,
`spy_offline_daily_cycle`, `crypto_supervised_readiness_trial`, and
`crypto_capability_production` each map both `attention_required` and
`unknown` to the identical `operator_review_*` token), leaving **38**
distinct tokens actually produced by the six `LaneSpec.next_actions`
maps. Adding the one aggregate token
(`ALL_LANES_ABSENT_ACTION`, emitted only when every lane is absent)
gives **39 distinct producer tokens** in total — the exact set a
supervisor report can ever place in `recommended_next_action`/
`next_action`. This was re-derived by direct enumeration in a
credential-free interpreter session (`set().union(*(lane.next_actions.values()
for lane in AUTONOMY_SUPERVISOR_LANES))`, cardinality 38, plus
`ALL_LANES_ABSENT_ACTION`, cardinality 39), not estimated by hand.

Full enumeration of the 39 distinct producer tokens, grouped by
`AUTONOMY_ACTION_CLASSIFICATION` bucket:

**`EXECUTION_NOOP`** (12 tokens; `offline_runnable=False`, no gate, nothing to run):
`unattended_market_data_soak_proven_continue_cadence`,
`continue_scheduled_read_only_market_data_refresh_cadence`,
`observe_hold_noop_continue_offline_daily_cycle`,
`await_next_offline_daily_cycle_input`,
`r1_deterministic_readiness_proven_continue`,
`await_supervised_readiness_trial_inputs`,
`continue_forward_shadow_cadence`,
`await_tournament_terminal_or_next_shadow_window`,
`continue_bounded_paper_probe_review_cadence`,
`await_v5_25_terminal_evidence`,
`continue_capability_production_cadence`,
`await_v5_25_terminal_winner`.

**`EXECUTION_OFFLINE_OPERATOR_INPUT`** (1 token; `offline_runnable=True`,
gate=`operator_supplied_inputs`, carries a `command` but is *not*
allowlist-eligible because its `execution_class` is not
`EXECUTION_AUTO_OFFLINE`):
`run_offline_daily_cycle_chain_to_seed_evidence` — the SPY offline daily
cycle *seed* command; requires an operator-supplied ISO-8601 clock and a
local adjusted SPY daily-bars CSV path that the frozen fixed-argv
allowlist model has no way to accept safely (see "Candidates
Considered", seed command).

**`EXECUTION_AUTO_OFFLINE`** (**0 of the 39 producer tokens** are
classified this way — this class is empty among what any lane can
actually emit). `AUTONOMY_ACTION_CLASSIFICATION` does contain exactly
one `EXECUTION_AUTO_OFFLINE` entry, `rerun_offline_daily_cycle_chain`
(`offline_runnable=True`, gate=`unattended_execution_authority`,
fully-defaulted `command` — the only class eligible for the allowlist
at all, and matching the sole allowlist entry by construction:
`AUTONOMY_ACTION_CLASSIFICATION` line 270-289 and
`AUTONOMY_EXECUTOR_ALLOWLIST` line 100-104 both key on this exact
string), but it exists only as a classification-registry entry, not as
a producer token: **no `LaneSpec.next_actions` map emits it, and it is
not one of the 39 producer tokens counted above.** It must not be
counted alongside the 39 emittable tokens — see Direction 1 below for
why that distinction is exactly the audit's finding.

**`EXECUTION_OPERATOR_GATED`** (26 tokens across 5 gate kinds; all
`offline_runnable=False`):
- `operator_supplied_inputs`: `operator_refresh_offline_daily_cycle_inputs`.
- `network_market_data_fetch`:
  `run_authorized_read_only_market_data_refresh_to_seed_soak`,
  `authorized_read_only_market_data_fetch_for_shadow_window`.
- `task_scheduler_health`:
  `operator_check_scheduled_market_data_refresh_task_health`.
- `operator_review` (13 tokens):
  `operator_review_latest_failed_market_data_session_read_only`,
  `operator_review_market_data_soak_evidence`,
  `operator_review_blocked_offline_daily_cycle_chain`,
  `operator_review_offline_daily_cycle_chain`,
  `operator_review_blocked_readiness_trial`,
  `operator_review_readiness_trial`,
  `operator_review_blocked_forward_shadow_cycle`,
  `operator_review_forward_shadow_cycle`,
  `operator_review_operational_evidence_blockers_read_only`,
  `operator_review_only_no_paper_mutation_authorized`,
  `operator_review_bounded_paper_probe_review`,
  `operator_review_blocked_capability_production`,
  `operator_review_capability_production`.
- `no_offline_command_available` (8 tokens plus the aggregate):
  `rerun_supervised_readiness_trial`,
  `run_supervised_readiness_trial_to_seed_r1_evidence`,
  `rerun_forward_shadow_status`,
  `run_forward_shadow_status_to_seed_evidence`,
  `rerun_bounded_paper_probe_review`,
  `run_bounded_paper_probe_review_to_seed_evidence`,
  `rerun_capability_production`,
  `run_capability_production_to_seed_evidence`,
  `all_lanes_absent_run_lane_commands_to_seed_evidence`
  (`ALL_LANES_ABSENT_ACTION`).

Total among the 39 producer tokens: 12 (`EXECUTION_NOOP`) + 1
(`EXECUTION_OFFLINE_OPERATOR_INPUT`) + 26 (`EXECUTION_OPERATOR_GATED`) +
0 (`EXECUTION_AUTO_OFFLINE`) = **39**, matching the distinct-token count
derived above (38 from the six `next_actions` maps, plus the one
aggregate `ALL_LANES_ABSENT_ACTION` token). The one
`EXECUTION_AUTO_OFFLINE` classification-registry entry
(`rerun_offline_daily_cycle_chain`) is deliberately excluded from this
39-token sum because it is not a producer token — that is the entire
substance of Direction 1, not a rounding choice.

Full coverage against `AUTONOMY_ACTION_CLASSIFICATION` (i.e. no token is
silently unclassified, which would fail closed to `operator_review`
anyway per `classify_action`'s explicit fallback) is proven by
`test_every_supervisor_action_is_classified`
(`tests/unit/test_autonomy_next_plan.py:121`).

### 3. Registry path, planner, executor, CLI, tests

- **Registry**: `AUTONOMY_SUPERVISOR_LANES` (`autonomy_supervisor.py:271`),
  a frozen tuple of 6 `LaneSpec` — the only registry in the codebase that
  can populate a lane's `next_action`.
- **Planner (consumer of the registry, producer of the plan)**:
  `autonomy_next_plan.py` — `classify_action`, `AUTONOMY_ACTION_CLASSIFICATION`
  (line 217), `build_autonomy_next_plan_from_report`.
- **Executor (consumer of the plan)**:
  `autonomy_offline_executor.py` — `_partition_actions`,
  `AUTONOMY_EXECUTOR_ALLOWLIST`, `build_offline_execution_ledger`.
- **CLI consumers**: `src/algotrader/cli.py` —
  `_run_autonomy_supervisor` (line 6013, `autonomy-supervisor-status`),
  `_run_autonomy_next_plan` (line 6068, `autonomy-next-plan`),
  `_run_autonomy_apply_plan` (line 6118, `autonomy-apply-plan` —
  the only CLI entry point that can reach `apply=True`), and
  `_run_autonomy_self_refresh_cycle` (line 6177, `autonomy-self-refresh-cycle`,
  which composes the same `build_offline_execution_ledger` call inside
  `autonomy_self_refresh_cycle.build_self_refresh_cycle`). No other CLI
  subcommand imports `autonomy_offline_executor` or
  `AUTONOMY_EXECUTOR_ALLOWLIST`.
- **Tests exercising this exact path**:
  `tests/unit/test_autonomy_supervisor.py`,
  `tests/unit/test_autonomy_next_plan.py`,
  `tests/unit/test_autonomy_offline_executor.py`,
  `tests/unit/test_autonomy_self_refresh_cycle.py`, and the CLI-level
  assertions inside `tests/unit/test_cli.py` (autonomy subcommand exit
  codes) plus `tests/unit/test_dependency_direction.py` (layering, not
  reachability, but load-bearing for the "no import surface expansion"
  argument below).

## Direction 1: Allowlist Token -> Emittable Lane Action

Claim: the sole allowlist token, `rerun_offline_daily_cycle_chain`, is
**not emitted by any lane in the current registry.**

Proof: intersect `{action for lane in AUTONOMY_SUPERVISOR_LANES for
action in lane.next_actions.values()} | {ALL_LANES_ABSENT_ACTION}` (the
39-token producer set enumerated above) against
`set(AUTONOMY_EXECUTOR_ALLOWLIST)` (`{"rerun_offline_daily_cycle_chain"}`).
The 39-token producer enumeration above contains no occurrence of that string —
the SPY offline daily cycle lane's `stale` state maps instead to
`operator_refresh_offline_daily_cycle_inputs` (`autonomy_supervisor.py:324`),
by explicit design: the code comment at lines 331-336 records that the
m446 rerun "is pinned to one historical dataset and writes a different
artifact" and therefore "can never cure staleness here". This is exactly
what `test_allowlisted_actions_are_unreachable_from_current_lane_registry`
(`tests/unit/test_autonomy_offline_executor.py:110`) asserts and what
currently passes. Direction 1 is confirmed: **zero** allowlist tokens are
reachable today.

## Direction 2: Every Emittable Action Token -> Allowlist Classification

Claim: of the 39 emittable (producer) tokens, **zero** are classified
`EXECUTION_AUTO_OFFLINE` (the only class the executor allowlist can ever
contain, since `_partition_actions` only forwards tokens with
`offline_runnable is True` to the allowlist check, and
`ActionClass.__post_init__` enforces `offline_runnable == (execution_class
in {EXECUTION_AUTO_OFFLINE, EXECUTION_OFFLINE_OPERATOR_INPUT})`). The one
`offline_runnable=True` producer token,
`run_offline_daily_cycle_chain_to_seed_evidence`, is
`EXECUTION_OFFLINE_OPERATOR_INPUT`, not `EXECUTION_AUTO_OFFLINE`, so it is
routed to `SKIP_REQUIRES_OPERATOR_INPUT` in `_partition_actions`
(line 274-278) regardless of whether it were ever added to the allowlist
dict — the execution-class gate, not just dict membership, keeps it out.
The remaining 38 producer tokens (12 `EXECUTION_NOOP` + 26
`EXECUTION_OPERATOR_GATED`) never reach `_partition_actions`'s allowlist
branch at all because `offline_runnable` is `False` for both classes.
The sole `EXECUTION_AUTO_OFFLINE` entry in the classification registry
(`rerun_offline_daily_cycle_chain`) is real, but — per Direction 1 — it
is not among the 39 tokens any lane can actually produce, so it never
reaches this comparison from the emitting side either.

So: of 39 emittable tokens, 0 are classified `EXECUTION_AUTO_OFFLINE`,
and the one token that is classified `EXECUTION_AUTO_OFFLINE` is not
emittable. Direction 2
confirms the same conclusion from the opposite side: **no emittable
token is currently allowlist-eligible**, and the one allowlist-eligible
token is not emittable. The reachability graph between "what the
registry can say" and "what the executor can run" is provably empty in
both directions, matching (and re-deriving independently of) the two
existing tests cited above.

## Candidates Considered And Rejected

Three candidate ways to close the gap were examined. None is safe to
implement without weakening an existing invariant, so none is adopted.

### Candidate A — point `spy_offline_daily_cycle`'s `stale` state at the m446 rerun

Rejected on the evidence already recorded in the source: the m446 rerun
reproduces one pinned historical dataset (fixed `sha256 408fd46...db69`,
fixed expected latest bar date `2026-06-08`) and writes the M447
manifest, never the `m444_offline_daily_cycle_run.jsonl` artifact this
lane actually reads (`autonomy_supervisor.py:331-336`). Wiring it to
`stale` would make the supervisor claim staleness was cured when the
underlying daily bars are exactly as stale as before — a truthfulness
regression of the same shape `V5.44` just closed, not a fix.

### Candidate B — allowlist the SPY seed command
(`run_offline_daily_cycle_chain_to_seed_evidence` /
`etf-sma-offline-daily-cycle-run`)

Rejected: this command's two required arguments
(`--validated-at`, `--daily-bars-csv`) are operator-supplied by design
(`AUTONOMY_ACTION_CLASSIFICATION` line 256-269, `required_operator_inputs`).
`AUTONOMY_EXECUTOR_ALLOWLIST` maps a token to a **fixed** `tuple[str, ...]`
argv with no parameter slots; the executor's own docstring and
`_execute`'s defence-in-depth check
(`AUTONOMY_EXECUTOR_ALLOWLIST[action.recommended_action] != action.argv`,
line 297-298) both assume the argv is a closed, static value. Accepting
a caller- or lane-artifact-supplied path/timestamp into that tuple would
turn "exact argv allowlisting" into "argv template plus untrusted
substitution" — a materially different and weaker guarantee, not a
bounded extension of the current one. `test_allowlist_is_the_verified_offline_command_only`
already asserts the seed command must never appear in any allowlist
argv; this audit found no way to lift that without the substitution
risk above.

### Candidate C — allowlist a crypto lane's offline-runnable command
(closest real candidate; rejected on import-surface grounds)

Every crypto lane's `stale`/`absent` remedy tokens
(`rerun_supervised_readiness_trial`,
`run_supervised_readiness_trial_to_seed_r1_evidence`, and the equivalent
pairs for the forward-shadow, bounded-paper-probe-review, and
capability-production lanes) are classified `EXECUTION_OPERATOR_GATED`
with gate `no_offline_command_available`. That gate reason is stated as
fact in `AUTONOMY_ACTION_CLASSIFICATION`'s comments, but a CLI command
does exist that reproduces the crypto readiness trial's exact artifact:
`crypto-readiness-verify` (`cli.py:4191-4196`, handler
`_run_crypto_readiness_verify` at `cli.py:13923`) takes **only defaulted
arguments** (`--output-root` defaults to
`runs/crypto_supervised_readiness_trial/latest`, `--cycle-count` defaults
to `24`) and calls
`run_crypto_supervised_readiness_trial(output_root=..., cycle_count=...,
write_artifacts=True)`
(`src/algotrader/execution/crypto_supervised_readiness_trial.py:51-272`),
which writes exactly `readiness_packet.json` at that root — the same
path `crypto_supervised_readiness_trial`'s `LaneSpec.artifact_relpath`
reads (`autonomy_supervisor.py:342`). With default arguments it never
attempts a broker read: `broker_observed_readiness=False` and
`allow_alpaca_paper_read=False` by default, and the one place inside the
trial that flips `broker_observed_readiness=True` for its own internal
scenario matrix simultaneously computes
`allow_alpaca_paper_read=(allow_alpaca_paper_read and
broker_observed_readiness)` (line 547-549 of that module), which stays
`False` under the CLI's defaults — so the trial's own broker-observation
scenario is itself simulated, not live, under the fully-defaulted
invocation. The trial is also decision-deterministic by construction
(`deterministic_rerun`/`equivalent` compares two independent in-process
replays and both use the same `DEFAULT_DECISION_START` and offline
fixture data), matching the "deterministic ledger evidence" bar.

This is disqualified anyway, on a *different* invariant than
determinism or default-argument safety: **import surface.** The
executor's own docstring requires every allowlisted command's producing
module to be "verified to import no network, broker, credential, or
profile surface" (`autonomy_offline_executor.py:11-14`), and the m446
module that is actually allowlisted satisfies this literally — its
import list (`etf_sma_offline_daily_cycle_rerun_m446.py:9-19`) is
`collections.abc`, `dataclasses`, `datetime`, `hashlib`, `json`,
`pathlib`, `tempfile`, `typing`, `algotrader.errors`, and its own sibling
`etf_sma_offline_daily_cycle_run` module — no broker, network, or
credential module anywhere in the chain.

`crypto-readiness-verify`'s import chain fails this bar. It imports
`crypto_supervised_readiness_trial`, which imports
`tomorrow_crypto_trader_demo`
(`crypto_supervised_readiness_trial.py:22-24`), which in turn imports
`algotrader.execution.alpaca_sdk_client`
(`tomorrow_crypto_trader_demo.py:26-28`), which imports
`algotrader.config.AlpacaPaperConfig` and `require_paper_profile`, and
`algotrader.execution.live_capital_interlock.require_live_capital_interlock`
(`alpaca_sdk_client.py:15-17`) — the profile-config and live-capital-
interlock surface, several layers upstream of any actual broker call.
None of these imports fire under `crypto-readiness-verify`'s default
arguments today, and none of them is itself unsafe to import in the
sense of executing code at import time — but "verified to import no ...
profile surface" is an import-graph property, not a runtime-behavior
property, and this chain fails it by construction. Allowlisting this
command would mean the executor's own docstring guarantee is no longer
true of everything on the allowlist, silently narrowing "verified
offline" from "this module cannot reach a broker/profile/credential
surface" to "this module's default arguments happen not to exercise the
broker/profile/credential surface it can reach" — a materially weaker
and harder-to-audit property (it depends on every future edit to
`tomorrow_crypto_trader_demo`'s defaults staying safe, not on the import
graph staying closed). That is precisely the kind of drift the
`no_offline_command_available` gate exists to prevent, even though its
current comment text ("no offline command reruns ...") is, read
literally, no longer accurate — a command exists; it just does not clear
the import-purity bar the executor requires. This audit leaves that
comment text as-is (no source change is authorized here) but records the
discrepancy for the next contract that touches this lane.

## Conclusion

No safe candidate exists today. Both reachability directions are
provably empty (re-deriving, not just re-reading,
`test_allowlisted_actions_are_unreachable_from_current_lane_registry`
and `test_every_supervisor_action_is_classified`), and the one
close-but-not-safe candidate (`crypto-readiness-verify`) fails the
executor's own import-purity invariant even though it passes every
other bar (fully-defaulted, deterministic, no broker call under default
arguments, writes the exact artifact its lane reads). No standalone
contract is frozen because there is nothing safe to freeze.

This audit changes no behavior: `AUTONOMY_EXECUTOR_ALLOWLIST` still has
exactly one entry, the executor is still provably inert under the
current lane registry
(`test_allowlisted_actions_are_unreachable_from_current_lane_registry`
still passes, unedited), and no import, subprocess, network, broker,
credential, or profile surface was added anywhere.

### Selected next milestone: V5.46

The only structurally sound way to create real reachability without
weakening an invariant is to add a **new**, narrowly-scoped CLI
subcommand whose producing module's full import graph is independently
verified free of `alpaca_sdk_client`/`alpaca_client`/
`live_capital_interlock`/`AlpacaPaperConfig`/`require_paper_profile` (or
any equivalent broker/profile/credential surface for a future broker),
is fully defaulted, is decision-deterministic, and writes exactly the
artifact its lane's `stale` or `absent` state reads — then classify that
new token `EXECUTION_AUTO_OFFLINE` and add it to the allowlist in one
frozen, reviewable contract. Reusing `crypto-readiness-verify` (or
`tomorrow_crypto_trader_demo`) as-is is not that path unless the broker
SDK import is first factored out of the module chain the trial depends
on — a change to production execution code, not something this
read-only audit is authorized to start.

This is recorded as the selected `V5.46` next milestone (see the
handoff, `docs/agent_context/active_implementation.md`): a
contract-first design for a new broker/profile/credential-import-free,
fully-defaulted, deterministic crypto readiness replay command that
writes exactly the `crypto_supervised_readiness_trial` lane's artifact.
The contract must be frozen and independently reviewed before any
source implementation or allowlist reachability change — this audit
does not start that implementation and grants it no authority beyond
naming it as the next step.

## Safety And External Effects

No credential value was read, enumerated, or exposed. No network,
broker, or market-data request occurred. No paper profile was entered
and no paper mutation occurred. No file under `src/` or `tests/` was
read for any purpose other than static inspection, and none was
modified. No subprocess was spawned by this audit itself (all argv
strings above are quoted from source, not executed). Preflight booleans
checked at the start of this session (`APP_PROFILE`, every listed Alpaca
credential alias, `ALGO_TRADER_ALLOW_NETWORK_TESTS`,
`RUN_ALPACA_PAPER_INTEGRATION_TESTS`) were all absent throughout.
Live-authorized state: `false`. Effective paper caps: not applicable (no
paper operation was attempted or is authorized by this document).
