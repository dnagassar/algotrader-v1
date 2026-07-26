# V5.48 Crypto Readiness Replay Reachability Contract

## Status And Scope

- Milestone: `V5.48 — crypto readiness replay reachability`.
- Contract state: **frozen design candidate; independent review required before
  implementation**.
- The first contract commit,
  `74aa69e70d22529b717723c4ebb61943e7b98473`, was rejected in independent
  review. This corrected contract closes its three P1 gaps: canonical target
  binding, truthful standing-authority semantics, and proof of the exact
  central CLI launcher rather than only its replay-module dependency.
- Base commit:
  `31b400d95e19dfc88b1a9d4d4269406ef7e152d4`, verified equal to
  `origin/main` before this document was written.
- Contract branch:
  `codex/v5.48-readiness-replay-reachability-contract`.
- Accepted prerequisite: V5.47 at
  `b4ca92594063a706bbcd13a9d18232d54c829ff2`, promoted within the
  `origin/main` history used as this contract's base.
- This commit is **contract-only**. It changes no source, test, script,
  authority, broker, paper, or live behavior.
- The subsequent implementation, if this contract is independently accepted,
  may wire only the already-proven import-pure
  `crypto-readiness-replay` command into the existing offline autonomy
  supervisor/planner/executor chain.
- This is not strategy-profit evidence, broker-observation evidence, paper
  mutation, order authority, or live-trading authority.

## Checkout Evidence And Preflight

The contract was derived from the current checkout rather than from a prior
report:

- `HEAD` and `origin/main` both resolved to
  `31b400d95e19dfc88b1a9d4d4269406ef7e152d4`.
- Staged, unstaged, and untracked state was empty before the contract branch
  was created.
- Presence-only checks for `APP_PROFILE` and the checked Alpaca/APCA credential
  aliases were all false. No value was requested or printed.
- No test, network request, broker call, paper action, or live action was run
  to derive this contract. Inspection was static and credential-free.

The following current-checkout facts are load-bearing:

| Surface | Current fact at the base |
| --- | --- |
| Supervisor lane | `crypto_supervised_readiness_trial` reads `crypto_supervised_readiness_trial/latest/readiness_packet.json`. |
| Accepted state | `trial_classification="accepted"` normalizes to `nominal`. |
| Absent recommendation | `run_supervised_readiness_trial_to_seed_r1_evidence`. |
| Stale recommendation | `rerun_supervised_readiness_trial`. |
| Current absent/stale classification | Both are `EXECUTION_OPERATOR_GATED`, `offline_runnable=False`, gate `no_offline_command_available`. That gate detail became stale after V5.47. |
| Current freshness | `max_age_hours=0`; staleness is disabled. The V5.47 root packet carries `decision_start` but no `generated_at` or `as_of`. |
| Replay command | `python -m algotrader.cli crypto-readiness-replay` is fully defaulted and writes the exact root packet the lane reads. |
| Replay default argv | The executable argv after the interpreter/module prefix is exactly `("crypto-readiness-replay",)`. |
| Replay-module safety | V5.47 proves the module closure rooted at `crypto_readiness_replay.py` is import-pure, broker-free, credential-free, profile-free, network-free, deterministic, and paper/live-mutation-free. It does **not** by itself prove the larger `python -m algotrader.cli ...` launcher closure. |
| Replay parser | It exposes only `--output-root`, `--decision-start`, `--cycle-count`, and `--format`; broker and receipt flags are absent. |
| Global parser caveat | The root parser currently accepts `--profile` before every subcommand, including replay, even though replay dispatch occurs before runtime-profile loading. V5.48 must reject an explicitly supplied profile option for this command rather than merely ignore it. |
| Canonical-target caveat | The exact allowlist argv carries no `--output-root`. The child therefore writes relative to its working directory at `runs/crypto_supervised_readiness_trial/latest`. A plan built from another `--lanes-root` or readiness `--lane` override would otherwise observe one path and mutate a different path. |
| Launcher caveat | The exact process eagerly imports `algotrader.cli`, whose only non-stdlib top-level import is `algotrader.execution.paper_order_policy`. That module currently imports only `dataclasses` and `decimal`, but this eager dependency and package initialization are outside V5.47's named static replay-module tuple and require V5.48 launcher evidence. |
| Authority | `AGENTS.md` grants all collaborators standing authority to run scoped offline verification and repository work. `--apply`, preflight, canonical-target validation, and the exact allowlist are safety controls; missing operator authority is not the action's gate. |
| Current executor allowlist | Only `rerun_offline_daily_cycle_chain -> ("etf-sma-offline-daily-cycle-rerun-m446",)`. |
| Current reachability defect | `rerun_offline_daily_cycle_chain` is classified and allowlisted but is not emitted by any `LaneSpec.next_actions` entry. |
| Empty-lab aggregate | When every lane is absent, the supervisor truthfully emits `ALL_LANES_ABSENT_ACTION`, leaves its recommended lane empty, requires evidence by default, and separately retains every per-lane absent recommendation. |
| Planner selection caveat | The planner currently chooses the first severity-ranked `offline_runnable` action. In an empty lab that is the operator-input SPY seed, even after crypto replay becomes the only canonical `EXECUTION_AUTO_OFFLINE` action. |

## Capability To Be Added

After accepted implementation, an absent crypto supervised-readiness root
packet will produce a planner action and executor ledger that reach exactly:

```python
("crypto-readiness-replay",)
```

The executor remains dry-run by default. With `--apply`, a clean preflight, a
canonical plan/report, and a verified repository root/cwd, it may spawn the
existing V5.47 CLI command. The command may create or atomically replace only:

```text
<verified repository root>/runs/crypto_supervised_readiness_trial/latest/
```

The root packet governing eligibility is exactly:

```text
<verified repository root>/runs/crypto_supervised_readiness_trial/latest/readiness_packet.json
```

No other `lanes_root`, lane override, output root, cwd-relative root, or plan-
supplied path is executable. The command performs no broker or paper-account
mutation.

The existing stale token is bound to the same replay argv so the classification
and allowlist do not drift if an honest freshness contract later makes the
state age-reachable. V5.48 itself does **not** invent that freshness contract
and does not claim that a real V5.47 packet currently becomes stale.

## Frozen Action Tokens

V5.48 preserves the two existing, semantically distinct lane tokens:

```text
absent -> run_supervised_readiness_trial_to_seed_r1_evidence
stale  -> rerun_supervised_readiness_trial
```

They must not be collapsed. Absence means no root packet exists. Staleness
would mean an accepted root packet exists but has exceeded an independently
defined freshness bound. Keeping separate tokens preserves that distinction
and follows the accepted V5.46 decision.

No new readiness token is needed. The implementation updates the
classifications of these exact existing tokens.

## ActionClass Contract

Both readiness tokens become `ActionClass` records with the following exact
shape:

```python
ActionClass(
    execution_class=EXECUTION_AUTO_OFFLINE,
    offline_runnable=True,
    gate="",
    gate_detail=(
        "standing offline authority applies; execution remains controlled by "
        "the exact allowlist, canonical-target validation, preflight, and the "
        "explicit executor --apply switch."
    ),
    command="python -m algotrader.cli crypto-readiness-replay",
    required_operator_inputs=(),
    preconditions=(
        "executor credential/profile/network preflight passes",
        "crypto-readiness-replay import-purity and parser guards pass",
    ),
)
```

The exact prose may be line-wrapped, but the semantic fields, empty gate,
execution class, empty operator-input tuple, exact command, and preconditions
are frozen.

`ActionClass.__post_init__` must define gates truthfully:

- `EXECUTION_AUTO_OFFLINE`: `gate == ""`; the action has standing authority,
  a non-empty exact command, no required operator input, and remains controlled
  by executor safety checks and `--apply`.
- `EXECUTION_OFFLINE_OPERATOR_INPUT`: non-empty
  `operator_supplied_inputs` gate and non-empty required inputs.
- `EXECUTION_OPERATOR_GATED`: non-empty gate naming the real blocker.
- `EXECUTION_NOOP`: `gate == ""`.

`_GATE_UNATTENDED_EXECUTION` must be removed if no truthful use remains.
No `EXECUTION_AUTO_OFFLINE` action, rendered plan, ledger, test, or design text
may claim that operator authority is missing. The explicit `--apply` switch is
a control signal, not an authority grant.

The obsolete non-emittable classification
`rerun_offline_daily_cycle_chain` must be removed from
`AUTONOMY_ACTION_CLASSIFICATION`. The underlying M446 CLI command remains
manually available; removing a dead autonomy classification neither deletes
that command nor grants new authority.

After implementation:

```python
producer_tokens = {
    token
    for lane in AUTONOMY_SUPERVISOR_LANES
    for token in lane.next_actions.values()
} | {ALL_LANES_ABSENT_ACTION}

assert set(AUTONOMY_ACTION_CLASSIFICATION) == producer_tokens
```

This replaces the one-way "every producer is classified" test with exact
two-way registry closure. A classification may neither be missing nor exist as
an unreachable promise.

## Exact Executor Allowlist

Remove the dead M446 autonomy entry. Add exactly these two entries:

```python
AUTONOMY_EXECUTOR_ALLOWLIST = {
    "run_supervised_readiness_trial_to_seed_r1_evidence": (
        "crypto-readiness-replay",
    ),
    "rerun_supervised_readiness_trial": (
        "crypto-readiness-replay",
    ),
}
```

Both values must be exact immutable tuples with one item. No output path,
decision time, cycle count, format, profile, broker, receipt, credential,
network, paper, or live option may enter either argv.

The following equality is frozen:

```python
auto_offline_tokens = {
    token
    for token, classified in AUTONOMY_ACTION_CLASSIFICATION.items()
    if classified.execution_class == EXECUTION_AUTO_OFFLINE
}

assert set(AUTONOMY_EXECUTOR_ALLOWLIST) == auto_offline_tokens
```

Together with exact producer/classification closure, this proves both
reachability directions:

1. Every allowlisted token is emitted by the supervisor registry and classified
   `EXECUTION_AUTO_OFFLINE`.
2. Every emitted token classified `EXECUTION_AUTO_OFFLINE` is allowlisted.

`_execute` must retain its defence-in-depth token and exact-argv equality
checks.

## Canonical Repository Target Contract

The fixed argv is safe only when the lane path observed by the supervisor and
the path written by the child are the same canonical repository path. V5.48
therefore freezes one target:

```python
CANONICAL_LANES_ROOT_RELPATH = Path("runs")
CANONICAL_READINESS_PACKET_RELPATH = Path(
    "runs/crypto_supervised_readiness_trial/latest/readiness_packet.json"
)
CANONICAL_REPLAY_ARGV = ("crypto-readiness-replay",)
```

The repository root is derived from the executing source checkout, not from
free-form plan text. Before an absent readiness action can remain
`EXECUTION_AUTO_OFFLINE`, the planner must prove all of the following:

1. the derived repository root is a real Git checkout/worktree containing
   `.git` and this checkout's `src/algotrader/cli.py`;
2. the process cwd resolves to that exact repository root;
3. the report's `lanes_root`, resolved against that cwd, is exactly
   `<repository root>/runs`;
4. the readiness lane's `artifact_path`, resolved without symlink/path escape,
   is exactly the canonical packet path;
5. its lane id, normalized state, action token, classification, command, and
   target agree;
6. no readiness lane override redirects the observed packet to a different
   path.

`_plan_lane` must copy the supervisor lane summary's existing
`artifact_path` into the corresponding plan action as a required observation
field. This is not an output argument and must never be appended to argv. It
lets the executor compare:

- the top-level plan/report `lanes_root`;
- the readiness action's observed `artifact_path`;
- the executor's `AutonomySupervisorConfig` and its existing
  `lane_artifact_overrides`;
- the freshly re-derived supervisor lane summary;
- the module-derived canonical repository packet.

No separate free-form `execution_target` or output-path propagation is
introduced.

A noncanonical report must fail closed during planning with `ValidationError`;
it must not merely retain `offline_runnable=true` and hope the executor catches
it.

The executor independently repeats the canonical-root, cwd, `lanes_root`,
readiness artifact-path, token/state/class/command, and exact-argv checks. It
must not trust a serialized `autonomy_next_plan` merely because its fields are
well typed.

When `plan_report` is supplied, the executor must re-derive the current
supervisor report and plan from its `AutonomySupervisorConfig`, then require the
supplied source to agree with that canonical derivation on at least:

- `run_id`;
- `as_of`;
- resolved `lanes_root`;
- readiness lane id, normalized state, artifact path, action token,
  execution class, `offline_runnable`, command, and gate;
- selected next action;
- eligible readiness action set.

Any mismatch fails before `_partition_actions`, before the runner is selected,
and before a subprocess is spawned. This applies to both supplied supervisor
reports and supplied next-plan records.

The production subprocess launcher must set `cwd` to the same verified
repository root used by those checks. It must never propagate or synthesize an
`--output-root`; canonical identity comes from the fixed cwd plus fixed argv,
not from hidden output-path substitution.

Negative planner, executor, CLI, and self-refresh tests must cover:

- arbitrary relative and absolute `--lanes-root`;
- a readiness `--lane` override outside the canonical target;
- a symlink/path-escape target;
- plan/config and report/config mismatch;
- tampered readiness action/artifact/command/argv fields;
- invocation from a cwd other than the verified repository root;
- a source tree without the expected Git worktree marker.

Every negative case must prove the runner/subprocess call count is zero. A
self-refresh negative must raise/refuse before outcome classification and
therefore emit no `refreshed` or `converged=true` claim.

## Supervisor And Planner Agreement

### Per-lane recommendations

No `AUTONOMY_SUPERVISOR_LANES` token is renamed or remapped. In particular:

- absent crypto readiness remains
  `run_supervised_readiness_trial_to_seed_r1_evidence`;
- stale crypto readiness remains `rerun_supervised_readiness_trial`;
- nominal remains `r1_deterministic_readiness_proven_continue`;
- blocked/unknown/attention states remain operator-review actions.

No other lane gains crypto replay as a remedy.

### Whole-system empty-lab recommendation

`ALL_LANES_ABSENT_ACTION`,
`recommended_next_action_lane=""`, `evidence_required=true`, and the
`system_no_lane_evidence` blocker remain unchanged for the all-absent report.
The aggregate token describes a whole-system condition; it must not be
silently replaced by one arbitrary lane token or made executable.

The plan must preserve both levels explicitly:

- `supervisor_recommended_action == ALL_LANES_ABSENT_ACTION`;
- `supervisor_recommended_action_lane == ""`;
- the crypto lane action is
  `run_supervised_readiness_trial_to_seed_r1_evidence`;
- `next_offline_action_lane == "crypto_supervised_readiness_trial"`;
- `next_offline_action["recommended_action"] ==
  "run_supervised_readiness_trial_to_seed_r1_evidence"`.

Those fields are complementary, not contradictory: the supervisor reports the
whole-system condition while the planner selects the highest-leverage safe
per-lane step.

### Selection priority

The planner must prefer severity-ranked `EXECUTION_AUTO_OFFLINE` actions over
severity-ranked `EXECUTION_OFFLINE_OPERATOR_INPUT` actions. It may fall back to
an operator-input offline action only when no canonical auto-offline action
exists.

Conceptually:

```python
next_offline = _highest_priority_action(
    actions,
    lambda action: action["execution_class"] == EXECUTION_AUTO_OFFLINE,
)
if next_offline is None:
    next_offline = _highest_priority_action(
        actions,
        lambda action: action["offline_runnable"] is True,
    )
```

This preserves `next_offline_action`'s existing broad meaning while ensuring it
does not point at an operator-input task when an immediately executable safe
action exists.

The invariant remains:

```text
plan_class == offline_action_available
if and only if
next_offline_action is not None and next_offline_action_lane is non-empty
```

## Absent Versus Stale Reachability Boundary

### Absent is end-to-end reachable

Absence is a real current state. With an empty readiness root:

1. the supervisor emits the readiness lane's absent token;
2. the planner proves its artifact is the canonical repository packet and
   classifies it `EXECUTION_AUTO_OFFLINE`;
3. planner selection prefers it over the SPY operator-input seed;
4. the executor re-derives the canonical report/plan and resolves the exact
   allowlisted argv;
5. dry-run reports one eligible action and executes nothing;
6. apply runs the exact replay argv after preflight;
7. accepted V5.47 output creates the exact root packet the lane reads;
8. re-observation sees the readiness lane as nominal.

### Stale is structurally bound but currently dormant

The current lane sets `max_age_hours=0`, and the V5.47 packet does not expose a
generation timestamp. Therefore a real current packet cannot honestly
normalize to `stale`.

V5.48 must not:

- use the fixed `decision_start` as generation freshness;
- use filesystem mtime as an unauthenticated freshness claim;
- add wall-clock reads to the import-pure replay;
- add a hidden environment or argv timestamp;
- enable `max_age_hours` without a command that can genuinely advance the
  freshness basis;
- claim manual end-to-end stale refresh evidence.

The stale token is nevertheless classified and allowlisted because it is an
existing frozen producer token and V5.46 explicitly reserved the same eventual
argv for it. Its V5.48 evidence is limited to:

- exact registry membership;
- exact `ActionClass`;
- exact allowlist mapping;
- planner classification from a deliberately constructed canonical stale lane
  summary, without apply execution or a refresh claim;
- the two-way producer/classification/allowlist set invariants.

An implementation report must call that proof **structural stale-token
binding**, not current runtime stale reachability.

Enabling real age-based staleness requires a later, separately frozen contract
that defines an authenticated freshness field and proves replay advances it
without sacrificing deterministic import purity. This is an unresolved design
risk, not a reason to weaken V5.48's absent-state capability.

## CLI Exactness And Fail-Closed Options

The allowlist invokes the central parser with only
`crypto-readiness-replay`. Its existing defaults remain exact:

```text
output_root   = runs/crypto_supervised_readiness_trial/latest
decision_start = 2026-07-19T12:00:00+00:00
cycle_count   = 24
format        = text
```

No new replay argument is added.

The parser/handler tests must prove:

- the exact allowlist tuple parses to the replay subcommand and the four
  existing defaults;
- exact dispatch forwards those defaults and `write_artifacts=True`;
- accepted output exits `0`;
- fail-closed output exits `2`;
- `--broker-observed-readiness` is rejected;
- `--allow-alpaca-paper-read` is rejected;
- `--receipt-root` is rejected;
- credential-looking options are rejected;
- a root-level `--profile` or `--profile=...` supplied for replay is refused
  before `run_crypto_readiness_replay` is called, including `dev`, `paper`, and
  `live`.

The global parser may continue to define `--profile` for other commands. The
replay handler must use the already-recorded argv or parsed value to detect that
the option was explicitly supplied and return a validation-style nonzero exit.
It must not load a profile to decide.

## Exact Executable Launcher Proof

V5.47's replay-module closure proof is a necessary prerequisite but is not
sufficient to allowlist:

```text
python -m algotrader.cli crypto-readiness-replay
```

The exact launcher also imports `algotrader.cli`, the package initializers, and
the central CLI's eager `paper_order_policy` dependency before it reaches the
lazy replay handler. V5.48 acceptance requires all of the following.

### Static/eager import classification

- Parse `algotrader.cli` and prove its module-level imports are stdlib plus only
  `algotrader.execution.paper_order_policy`.
- Prove `paper_order_policy.py` and its static closure are stdlib-only
  (`dataclasses`, `decimal` at the current base), with no network, broker SDK,
  credential, profile, environment, LLM/agent, mutation, or dynamic-load
  surface.
- Include `algotrader/__init__.py`, `algotrader/execution/__init__.py`, and the
  latter's eager first-party imports in the launcher audit. Lazy
  `execution.__getattr__` broker imports must not execute.
- Parse the selected `build_parser` replay branch, `main` dispatch path before
  the replay branch, and `_run_crypto_readiness_replay`; their executed imports
  and calls may reach only the standard library, replay module/core, parsing,
  rendering, and local artifact work.
- Synthetic negative tests must prove the scanner notices a forbidden eager
  import, dynamic load, protected environment read, broker module, mutation
  call, and LLM/agent SDK import.

This is path-specific classification, not a false claim that every dormant
handler in the large central CLI is part of replay's executed closure.

### Fresh exact-process evidence

Spawn a fresh process with the exact production command:

```text
<sys.executable> -m algotrader.cli crypto-readiness-replay
```

from the verified canonical repository cwd and with the same protected keys
removed as the executor's sanitized child environment. A temporary test
harness loaded before `algotrader.cli` (for example an isolated
`sitecustomize` prepended to the test-only `PYTHONPATH`) must:

- trap access, containment checks, or iteration over protected profile,
  credential, endpoint, and network-test keys;
- record the post-run `sys.modules` set outside the repository `runs/` tree;
- leave production source and argv unchanged.

The declared test-only path prepend is instrumentation, not production
launcher behavior. Apart from that prepend and an audit-output destination,
the environment must match the executor's sanitized child environment.

The parent test must assert:

- child exit `0`;
- exact V5.47 text dispatch output;
- an accepted canonical root packet;
- no protected environment access;
- no forbidden network, broker SDK, credential/config, profile/interlock,
  broker adapter, paper-client composition-root, LLM, or agent module in the
  post-run module record.

A companion fresh-process `runpy.run_module("algotrader.cli",
run_name="__main__")` check may make post-`SystemExit` module inspection easier,
but it supplements rather than replaces the exact `python -m` process.

If this exact central-launcher proof cannot be made reliable, implementation
must stop and return for a separately reviewed dedicated pure-launcher design.
It must not silently treat the V5.47 replay-module tuple as proof of the
central CLI launcher.

## Executor Safety Contract

V5.39 executor safety remains unchanged and applies before replay:

- dry-run spawns no subprocess;
- apply refuses under `APP_PROFILE=paper` or `APP_PROFILE=live`;
- apply refuses when any executor credential/network-test key is present;
- refusal reports names only, never values;
- the child environment strips all credential/profile keys;
- `_execute` rechecks the action token and exact argv;
- no caller-supplied path, timestamp, token, or option is interpolated;
- nonzero child exit is recorded and propagates as unsuccessful execution;
- zero executions keep `all_executions_succeeded=None`;
- the action ledger fixes all broker/paper/live mutation booleans false.

V5.48 must not weaken the source-scan that excludes network, broker SDK,
credential, and mutation surfaces from the executor. It must retain the V5.47
module-closure, fresh-process import, raising-environment, parser-negative, and
source-provenance tests for replay, and add the distinct exact-launcher proof
above.

## No LLM Or Agent In The Hot Path

The executable chain is fixed Python control flow:

```text
LaneSpec
  -> autonomy supervisor
  -> ActionClass lookup
  -> exact executor allowlist
  -> python -m algotrader.cli crypto-readiness-replay
  -> import-pure deterministic replay core
```

No LLM, agent, prompt, model output, free-form text, tool routing, or dynamic
code generation may select, alter, approve, or execute the action. Tests must
scan the implementation modules, replay module closure, and exact launcher
path for newly introduced LLM/agent SDK imports and dynamic command
construction.

## Safety And Authority Invariants

The implementation must preserve all of the following:

- `paper_lab_only=true`;
- `not_live_authorized=true`;
- `live_authorized=false`;
- `profit_claim=none`;
- no network access;
- no broker access or observation;
- no credential access or disclosure;
- no paper profile entry;
- no order submit, cancel, replace, close, or liquidation;
- no broker or paper-account mutation;
- no real-capital activity;
- no LLM/agent in the trading or execution hot path.

Local deterministic artifact writes under `runs/` are the only intended side
effect. They are generated state, never authority.

Paper quantity/notional caps are not applicable because this command performs
no paper action. Receipt/reconciliation are not applicable because it performs
no broker operation. No paper or live authority is created or expanded.

## Frozen Implementation Scope

An accepted V5.48 implementation may modify only the minimum files needed for
this contract:

- `src/algotrader/execution/autonomy_next_plan.py`;
- `src/algotrader/execution/autonomy_offline_executor.py`;
- `src/algotrader/cli.py` only for replay-specific profile-option refusal if
  the existing handler does not already enforce it;
- `tests/unit/test_autonomy_next_plan.py`;
- `tests/unit/test_autonomy_offline_executor.py`;
- `tests/unit/test_autonomy_self_refresh_cycle.py`;
- `tests/unit/test_crypto_readiness_replay.py`;
- `tests/unit/test_dependency_direction.py` only for a narrowly scoped
  reachability/hot-path guard when needed;
- existing V5.38/V5.39 design text whose "executor is inert" statements become
  stale after implementation;
- `docs/agent_context/active_implementation.md`.

It must not modify:

- `AGENTS.md`;
- V5.47 replay/core/adapter behavior;
- V5.47 parser options or default values;
- readiness artifact schemas or publication protocol;
- other supervisor lane recommendations;
- paper/live interlocks, cap enforcement, reconciliation, or auditing;
- broker, network, credential-provider, order, paper, or live modules.

If implementation requires a file outside the allowed list, it must stop and
return to contract review rather than expand scope silently.

The implementation must specifically correct stale authority/M446 prose in:

- `autonomy_next_plan.py`'s module text and removed M446 action detail;
- `autonomy_offline_executor.py`'s allowlist comments;
- `docs/design/v5_38_offline_autonomy_next_action_planner.md`;
- `docs/design/v5_39_gated_offline_autonomy_executor.md`;
- focused tests whose names/comments currently describe M446 as the sole
  verified allowlisted command or `unattended_execution_authority` as the
  missing gate.

Historical audit documents may remain historically accurate when clearly
dated; current operational documentation must not.

## Tests And Acceptance Criteria

### Registry closure

1. `producer_tokens` includes every lane `next_actions` value plus
   `ALL_LANES_ABSENT_ACTION`.
2. `set(AUTONOMY_ACTION_CLASSIFICATION) == producer_tokens`.
3. The two readiness tokens have the exact `ActionClass` semantics above.
4. `rerun_offline_daily_cycle_chain` is absent from classification and
   allowlist registries.
5. Every `EXECUTION_AUTO_OFFLINE` token is allowlisted.
6. Every allowlisted token is a producer and is `EXECUTION_AUTO_OFFLINE`.
7. Both readiness tokens map to exactly `("crypto-readiness-replay",)`.
8. Every `EXECUTION_AUTO_OFFLINE` action has `gate == ""`, no required
   operator inputs, and no text claiming missing operator authority.
9. `EXECUTION_OFFLINE_OPERATOR_INPUT` and `EXECUTION_OPERATOR_GATED` retain
   real non-empty gates.

### Supervisor/planner

10. An all-absent report preserves the aggregate empty-lab token and empty
   aggregate lane while its crypto lane carries the absent readiness token.
11. From the canonical repository root and canonical `runs`, the all-absent
   next plan preserves those supervisor fields and selects the
   crypto readiness lane/action as `next_offline_action`.
12. The SPY operator-input seed remains in `offline_runnable_lanes`, but does
    not outrank the crypto `EXECUTION_AUTO_OFFLINE` action.
13. When no auto-offline action exists, the planner still falls back to an
    operator-input offline action.
14. A constructed canonical stale readiness summary selects the stale
    readiness token and exact replay command, clearly labeled
    structural/dormant; it is not executed.
15. Every noncanonical `lanes_root`, readiness override, artifact path, cwd,
    or repository root fails during planning.
16. Unknown tokens and unknown normalized states continue to fail closed.

### Executor

17. A canonical empty-lab plan partitions to exactly one eligible action:
    `crypto_supervised_readiness_trial`,
    `run_supervised_readiness_trial_to_seed_r1_evidence`,
    `["crypto-readiness-replay"]`.
18. Dry-run invokes no runner and reports `execution_count=0` and
    `all_executions_succeeded=None`.
19. Apply invokes the injected runner once with the exact tuple and sanitized
    environment.
20. The exact-argv defence rejects token/argv drift.
21. The executor re-derives and compares a supplied plan/report; any
    plan/config/report mismatch fails before runner selection.
22. Arbitrary/noncanonical `lanes_root`, readiness override, artifact path,
    cwd/root, symlink escape, or output-target mismatch produces zero
    executions.
23. Loaded paper/live profile, credential, or network-test state refuses apply
    without exposing any value.
24. Child nonzero exits remain failures; zero-execution ledgers never claim
    success.

### Replay CLI and closure

25. Exact parser defaults and forwarding remain as frozen above.
26. Broker, receipt, paper-read, credential-looking, and explicit profile
    options fail closed before replay execution.
27. Accepted replay still exits `0`; fail-closed replay exits `2`.
28. V5.47 replay-**module** import-purity, dependency-closure,
    raising-environment, artifact atomicity, parser-negative, and provenance
    tests continue to pass.
29. The separate exact central-launcher static/eager-import classification,
    protected-environment fresh process, exact dispatch, canonical artifact,
    and post-run forbidden-`sys.modules` tests pass.
30. No source scan finds a new network, broker, credential, mutation, LLM,
    agent, dynamic-import, or dynamic-command surface in the hot path.

### Self-refresh truthfulness

31. In an isolated Git worktree at its own canonical repository root, with
    empty canonical `runs`, dry-run reports one eligible crypto action but no
    execution and does not claim refresh.
32. Apply with an injected successful runner records one execution.
33. A real isolated apply that invokes V5.47 produces an accepted root packet;
    re-observation sees the readiness lane nominal and the cycle reports a
    genuine severity reduction from `no_lane_evidence`.
34. A child failure or failed preflight never reports `refreshed` or
    `converged`.
35. Every canonical-target refusal has zero runner calls and no refresh or
    convergence claim.
36. No test claims a real stale refresh under `max_age_hours=0`.

## Required Manual Evidence

The implementation report must include one isolated, credential-free,
network-free run from a fresh temporary Git worktree at the implementation
commit. The shell cwd must be that worktree's verified repository root and its
canonical `runs/` must have no pre-existing lane artifacts. Generated `runs/`
output must remain ignored and untracked. A random temporary `--lanes-root` is
not valid manual evidence because the fixed child argv cannot write there.

First, dry-run:

```powershell
python -m algotrader.cli autonomy-apply-plan `
  --run-id v5_48_absent_dry_run `
  --as-of 2026-07-26T12:00:00Z `
  --lanes-root runs `
  --format json
```

Required evidence:

- exit `1` because eligible work is pending;
- `dry_run=true`;
- `eligible_count=1`;
- `execution_count=0`;
- only the crypto absent token is eligible;
- exact argv is `["crypto-readiness-replay"]`;
- resolved plan `lanes_root` and readiness artifact path equal that worktree's
  canonical `runs` and packet path;
- all broker/paper/live safety booleans are false.

Then apply from the same isolated checkout after repeating presence-only
preflight:

```powershell
python -m algotrader.cli autonomy-apply-plan `
  --run-id v5_48_absent_apply `
  --as-of 2026-07-26T12:00:00Z `
  --lanes-root runs `
  --apply `
  --format json
```

Required evidence:

- exit `0`;
- `eligible_count=1`;
- `execution_count=1`;
- exact executed argv is `["crypto-readiness-replay"]`;
- child exit is `0` and `all_executions_succeeded=true`;
- the resulting
  `runs/crypto_supervised_readiness_trial/latest/readiness_packet.json`
  validates and has `trial_classification="accepted"`;
- packet and ledger safety fields show no credential, network, broker, paper,
  or live action;
- no credential value appears anywhere in output.

A second dry-run must show the crypto action is no longer eligible after the
accepted packet exists. Other operator-input or gated lane work may remain; it
must not be misreported as executable.

The report must also include a negative direct CLI check showing an explicit
replay `--profile` option returns nonzero before replay execution, and the
existing broker/receipt option rejection evidence. It must include at least
one noncanonical `--lanes-root`, one noncanonical readiness `--lane` override,
one mismatched supplied plan/report, and one non-repository cwd/root negative;
each must prove zero runner calls and no refresh claim.

The exact fresh-process launcher proof must use the same canonical worktree and
the literal process command
`python -m algotrader.cli crypto-readiness-replay`, with protected environment
traps and a post-run forbidden-module audit as specified above.

## Required Verification

At minimum:

```powershell
python -m pytest tests/unit/test_autonomy_supervisor.py
python -m pytest tests/unit/test_autonomy_next_plan.py
python -m pytest tests/unit/test_autonomy_offline_executor.py
python -m pytest tests/unit/test_autonomy_self_refresh_cycle.py
python -m pytest tests/unit/test_crypto_readiness_replay.py
python -m pytest tests/unit/test_dependency_direction.py
.\scripts\verify_offline.ps1
python -m pytest
git diff --check
git status --short
git diff --name-only HEAD -- src
git ls-files --others --exclude-standard src tests
```

The full default suite is required if `verify_offline.ps1` reports that it
skipped it.

## Implementation Report Requirements

The report must state:

- credential/profile preflight by presence only;
- files changed;
- exact action tokens, classes, command string, and allowlist tuples;
- producer/classification/allowlist equality evidence;
- all-absent aggregate and per-lane planner fields;
- focused, dependency, offline-verifier, and full-suite results;
- manual dry-run and apply-plan evidence;
- canonical cwd/root/lanes-root/readiness-target evidence and all negative
  refusal cases;
- exact central-launcher eager-import, protected-environment, dispatch, and
  post-run module evidence;
- generated artifact validation;
- network/broker access: none;
- paper mutations: none;
- effective paper size/notional caps: not applicable;
- broker receipt/reconciliation: not applicable;
- `live_authorized=false`;
- `git diff --check`;
- `git status --short`;
- tracked `src` changes and untracked `src`/`tests` files;
- no real stale reachability claim;
- recommended next milestone.

## Stop Conditions

Stop implementation before staging or committing if:

- V5.47 import purity, parser negatives, artifact validation, or provenance
  regress;
- the implementation treats V5.47's replay-module closure as proof of the
  central CLI launcher without the additional V5.48 evidence;
- the exact allowlist argv gains any argument;
- a profile, credential, broker, receipt, paper, or live flag reaches replay;
- a caller-supplied value is interpolated into executor argv;
- the dead M446 allowlist promise remains;
- an `EXECUTION_AUTO_OFFLINE` action declares missing operator authority or a
  non-empty authority gate;
- classification/producer/allowlist closure fails in either direction;
- planner or executor accepts a noncanonical root, cwd, lanes root, readiness
  override, artifact target, or mismatched plan/report;
- empty-lab aggregate reporting is weakened;
- planner selection still points at operator-input work while the crypto
  auto-offline action is executable;
- default tests load a profile or credential;
- a network, broker, paper, or live action occurs;
- a credential value could be logged or persisted;
- implementation claims real stale refresh without a separately accepted
  freshness contract;
- scope cannot be isolated from unrelated work.

## Out Of Scope

- No real freshness timestamp or `max_age_hours` change.
- No broker observation or receipt consumption.
- No market-data fetch.
- No paper submit, cancel, replace, close, or liquidation.
- No live access or real-capital activity.
- No strategy, risk, sizing, order, portfolio, or profitability change.
- No Task Scheduler or recurring automation.
- No retention or garbage collection for immutable readiness generations.
- No promotion or merge in the implementation slice without a separate
  accepted review and operator sequencing decision.

## Next Action

Independently review this contract against the same base checkout. Review must
specifically challenge:

1. removal of the dead M446 classification/allowlist entry;
2. exact two-way producer/classification/allowlist closure;
3. standing-authority `ActionClass` semantics and auto-offline planner
   priority over operator-input work;
4. the empty-lab aggregate/per-lane distinction;
5. canonical planner/executor/root/cwd/target validation;
6. exact central-launcher purity and post-run import evidence;
7. replay-specific explicit-profile refusal;
8. the honest boundary between active absent reachability and dormant
   stale-token binding.

Do not begin V5.48 implementation until that review accepts the contract.
