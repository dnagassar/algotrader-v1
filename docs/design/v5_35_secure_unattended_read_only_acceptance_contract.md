# V5.35 Secure Unattended Read-Only Acceptance Contract

## Frozen Status And Chronology

This contract is frozen before V5.35 implementation. Its Git commit must be an
ancestor of every V5.35 production-code commit so that review can prove the
acceptance criteria preceded the implementation.

- Milestone: `V5.35 — secure unattended read-only execution boundary and production-path proof`
- Classification available to the implementation owner: `implemented` or
  `blocked`; never `accepted`, `activated`, `paper-proven`, or `live-ready`
- Exact base: `origin/main@9d40560052b2fb155586d5e978e25fd21f241cae`
- V5.34 disposition: `replace`
- Forbidden ancestry/application: commits `8d2cbcc` and `9a0adfc` must not be
  merged or cherry-picked
- Independent acceptance: a different agent owns final acceptance

## Objective

V5.35 must provide one coherent, offline-verifiable production boundary for
unattended read-only market-data collection and paper-account observation.
Runtime credential material must come from an operator-provisioned,
non-plaintext provider. Secret values must never enter repository files,
command arguments, logs, receipts, exceptions, temporary files, persisted
state, or duplicated environment aliases.

This milestone does not provision or access real credentials. It does not
authorize network access, broker access, paper mutation, task registration,
task enabling, order submission, cancellation, replacement, close,
liquidation, capital allocation, mode changes, or live behavior.

## Credential And Process Boundary

The implementation is acceptable only when all of the following are true:

1. A typed credential-provider abstraction isolates opaque key/secret material
   from orchestration and persistence.
2. The production provider is Windows-compatible and reads a non-plaintext,
   operator-provisioned credential reference at the final authorized I/O
   boundary. Default tests use dependency-injected credential-free fakes.
3. Credential key and secret come from one matched provider record and family;
   aliases may not be mixed, copied, or normalized into duplicate environment
   variables.
4. The exact paper profile and canonical paper endpoints are validated before
   credential resolution, process creation, client construction, or network
   access. Live or ambiguous endpoints fail closed.
5. Provider unavailable, access denied, malformed records, family mismatch,
   profile mismatch, endpoint mismatch, or any redaction uncertainty fail
   closed with sanitized typed errors and zero external effects.
6. Cross-process execution passes only a non-secret provider reference. The
   child resolves that reference through the same provider abstraction at the
   intended boundary. Raw secrets never appear in `argv` or inherited process
   environment.
7. `RealCommandDispatcher` remains the dispatcher exercised by production-path
   acceptance tests. `PreviewDispatcher` may not substitute for it. External
   I/O is injectable only at explicit credential-store, process-runner, clock,
   Task Scheduler, and read-only HTTP boundaries.

## Completed-Cycle Evidence Schema

Every admitted cycle must produce immutable, content-addressed evidence. A
completed cycle is valid only when its schema contains mandatory bindings for:

- source commit, source tree, clean-worktree state, and production bundle;
- exact scheduler task identity, task action, accepted UTC window, task state,
  and task result;
- market-data request, response, source, target window, and receipt hash;
- read-only paper-broker observation, account-match facts, flat-state facts,
  zero mutations/submissions, and receipt hash;
- readiness inputs, result, blockers, and receipt hash;
- final decision, status, and all referenced receipt hashes.

The validator must recompute canonical hashes and cross-check all referenced
identities, windows, source provenance, task action, market-data bindings,
broker bindings, readiness bindings, and decision bindings. Missing,
malformed, duplicate/ambiguous, stale, failed, blocked, mutation-bearing,
non-flat, or mismatched evidence fails closed.

## Transactional Same-Window Admission

Admission must be durable and transactional before any external effect. The
uniqueness key is the exact scheduler job identity plus accepted scheduler
window. Concurrent invocations must yield exactly one admitted owner and an
immutable no-op receipt for every duplicate. A JSON index written after an
observation is not an admission mechanism. Crash/restart behavior must preserve
the durable claim without allowing a second external effect.

## Burn-In Status Contract

`active` and `complete` are derived statuses and must fail closed. `complete`
requires exactly 24 contiguous valid scheduled cycles for the target windows,
with:

- exact scheduler task identity and action alignment;
- successful enabled task state and successful task result;
- bounded frontier lag and no stale window;
- valid source, scheduler, market-data, broker, readiness, and decision
  bindings for every window;
- zero missing, invalid, malformed, mismatched, failed, blocked, or duplicate
  admitted cycles;
- zero broker mutations, submissions, cancellations, replacements, closes,
  liquidations, or live behavior; and
- reconciled flat paper state for every cycle.

Any violation forces a non-active, non-complete blocked status with sanitized,
deterministic reasons.

## Mandatory Offline Proof

The V5.35 focused suite must prove:

1. unavailable, malformed, mismatched, or denied production credentials cause
   zero subprocesses, clients, network calls, broker calls, or side effects;
2. sentinel secrets never appear in arguments, environment aliases,
   stdout/stderr, exceptions, logs, receipts, temporary files, or state;
3. the exact production dispatcher receives sufficient non-secret
   configuration and resolves material only at the intended boundary;
4. a 24-cycle production-control-flow run survives persistent restart without
   preview-dispatch substitution;
5. concurrent same-window invocations admit one cycle and persist immutable
   no-op evidence for every duplicate;
6. missing or mismatched scheduler, market-data, or broker bindings fail
   closed; and
7. burn-in completion requires every condition in the preceding section.

Existing dependency-direction, default-network, credential, broker-mutation,
no-submit, provenance, identity, and atomic-persistence suites must remain
intact.

## Verification And Handoff

The implementation owner must run focused V5.35 and affected safety suites,
`python -m pytest tests/unit/test_dependency_direction.py`, and
`.\scripts\verify_offline.ps1 -Full` on the exact final commit with a clean
tree. The handoff records exact commands, commit, tree, exit codes, counts,
elapsed times, boolean-only credential presence, network/broker access, broker
mutation status, `git diff --check`, `git status --short`,
`git diff --name-only HEAD -- src`, and
`git ls-files --others --exclude-standard src tests`.

The verified branch may be pushed for independent review. It may not be
merged or self-accepted. `operator_action_required` remains `false` unless a
later, separately authorized operation reaches a real credential-provisioning
or task-activation gate; V5.35 verification must not cross either gate.
