# V5.36 Windows-Host Commissioning And Bounded Canary Acceptance Contract

## Frozen Status And Chronology

This contract is frozen before V5.36 implementation. Its commit must be an
ancestor of every V5.36 production-code commit.

- Milestone: `V5.36 — Windows-host commissioning and bounded scheduled read-only canary`
- Classification available to the implementation owner: `implemented` or
  `blocked`; never `activated`, `paper-proven`, or `live-ready`
- Exact base: verified V5.35 commit
  `18c25553156db515945134dae6a2b141a0d42327`
- V5.35 contract commit:
  `647a49bc4ada5aaecc952c90d84777e9dd00dfa8`
- Independent disposition remains outside the implementation owner

The operator-supplied authorization template contains unresolved placeholders:
`<EXACT_CLOSED_WINDOW>`, `<NON_SECRET_REFERENCE>`,
`<VERIFIED_V5_36_COMMIT>`, and `<EXACT_UTC_TIME>`. It authorizes implementation
of this boundary but is not executable authorization. V5.36 must reject every
placeholder, missing value, non-final commit, or ambiguous time before reading
a credential, mutating Task Scheduler, creating a client, or accessing a
network.

## Objective

V5.36 must bridge the offline-proven V5.35 boundary to one separately
authorized, exact Windows scheduled read-only canary. It must provide a secure
operator provisioning boundary, bind the Windows task principal to its
credential vault and immutable deployment, install and attest the task while
disabled, arm no more than one exact UTC window, disarm after the first attempt
regardless of outcome, and generate a post-run commissioning packet.

Implementation and default verification remain credential-free, network-free,
broker-free, and Task-Scheduler-mutation-free. Actual provisioning,
registration, arming, execution, and network reads remain hard operator gates
until one resolved authorization artifact names the exact final V5.36 commit,
window, non-secret references, endpoints, principal, deployment path, and
disarm deadline.

## Immutable Authorization Artifact

One canary authorization is valid only when a repository-defined schema binds:

- schema version and unique authorization ID;
- exact task identity `\crypto-tournament-v2-oos-scheduler`;
- exact closed UTC market-data window and scheduled start time;
- exact automatic-disarm deadline later than the scheduled start and before a
  second eligible hourly window;
- exact Windows principal identity and vault owner identity, which must match;
- exact absolute deployment root, source commit, and source tree;
- credential provider `windows-credential-manager` and two strict non-secret
  references for `alpaca-market-data` and `alpaca-paper-observation`;
- exact endpoints `https://data.alpaca.markets` and
  `https://paper-api.alpaca.markets`;
- explicit booleans authorizing only credential reads, task
  registration/arming/disarming, market-data reads, and paper observation;
- explicit false booleans for submit, cancel, replace, close, liquidation,
  paper mutation, live access, retry, and additional windows; and
- canonical artifact hash plus a separate operator approval marker.

Free-form prose, inferred defaults, wildcard values, placeholders, relative
paths, dirty or mismatched source, live endpoints, a deadline that permits a
second window, and unknown fields fail closed.

The artifact contains no secret values and no raw account identity. It may be
persisted. It cannot be created, approved, broadened, or rewritten by the
production runner.

## Credential Provisioning Boundary

V5.36 provides a Windows-compatible operator-only adapter that writes one
generic Windows Credential Manager record through the native API. The
production adapter must:

1. accept the target only as a strict non-secret V5.35 credential reference;
2. accept secret material only through an injected opaque input boundary, with
   a no-echo interactive implementation and credential-free fakes for tests;
3. write one exact `v5_35_credential_record_v1` family record atomically;
4. never accept secrets in command arguments, environment variables,
   repository files, authorization artifacts, logs, exceptions, stdout/stderr,
   temporary files, receipts, or persisted commissioning state;
5. zeroize mutable buffers and return only sanitized classifications; and
6. require a separate, resolved provisioning authorization before calling the
   native write API.

Provisioning one family does not authorize the other. A failed, denied,
malformed, mismatched, or ambiguous provisioning attempt has no scheduler,
client, broker, or network effect.

## Windows Principal And Deployment Binding

The task principal, credential-vault owner, and current Windows identity must
match the resolved authorization. V5.36 must not silently change logon type,
copy secrets between users, create environment aliases, or fall back to a
different vault.

The deployment root must be absolute, exist, be a clean Git worktree at the
authorized commit and tree, and contain the source-bundle files used by the
canary. The registered action must use the exact absolute wrapper path and
working directory; unresolved `%REPO_ROOT%`, relative paths, mutable branch
labels, or an action mismatch fail closed.

## Bounded Task Lifecycle

Task Scheduler is an explicit injected boundary. Default tests use a fake.
Production mutation is split into distinct operations:

1. `install-disabled`: register the exact task identity with a single one-time
   UTC trigger, least privileges, no on-demand start, no restart, no overlap,
   a bounded execution limit, and task/trigger disabled;
2. `attest-disabled`: read back and validate the principal, trigger, action,
   arguments, working directory, settings, disabled state, and authorization
   hash without mutation;
3. `arm-exact-window`: after revalidating the artifact, source, current time,
   credential references, principal, and disabled attestation, enable only the
   one-time trigger and task;
4. `disarm`: disable the trigger and task idempotently without reading
   credentials or using the network; and
5. `post-run-attest`: after the action exits, require the exact last-run time,
   terminal result, disabled state, and no second invocation.

Registration does not imply arming. Arming does not authorize a manual or
second start. The runner must consume a durable single-use authorization claim
before credentials or external reads. Duplicate, late, early, ambiguous, or
already-consumed invocations produce immutable no-op or blocked evidence and
perform zero external reads. Disarm is attempted in a guaranteed cleanup path
after the first invocation and remains available credential-free if the runner
crashes.

## Canary Execution And Evidence

The scheduled action must exercise the actual V5.35 production control flow
and `RealCommandDispatcher`. It may perform only:

- Windows Credential Manager reads for the two authorized references;
- HTTPS GET market-data reads for the exact authorized closed window; and
- paper account, positions, open/recent orders, and required asset reads.

No preview dispatcher may substitute for production. No submit, cancel,
replace, close, liquidation, paper mutation, live endpoint, ambiguous retry,
or additional window is authorized or exposed.

Because Task Scheduler cannot truthfully report the current action's terminal
result while that action is still running, V5.36 separates in-run task
identity/action evidence from post-run terminal attestation. A final
commissioning packet is valid only after a credential-free post-run reader
binds the exact completed task result and disabled state to the canary receipt.
The production runner must never forge a successful terminal result.

The packet must bind and validate:

- authorization artifact hash and single-use claim;
- source commit, tree, clean state, bundle, deployment path, and principal;
- exact task identity, trigger, action, scheduled start, observed start,
  terminal result, and disarm state;
- both provider/reference identities without secrets;
- exact market-data and paper endpoints and accepted window;
- V5.35 source, scheduler, market-data, broker, readiness, and decision receipt
  hashes;
- reconciled flat paper state and zero mutation/submission facts;
- bounded timing and no second invocation; and
- sanitized leak-scan results over argv, environment-name inventory,
  stdout/stderr, exceptions, logs, receipts, temporary paths, and persisted
  state without persisting or echoing the secrets being searched.

Missing, malformed, stale, failed, blocked, non-flat, mutation-bearing,
ambiguous, mismatched, or non-terminal evidence fails closed.

## Mandatory Offline Proof

The focused V5.36 suite must prove:

1. every placeholder or incomplete authorization is rejected before all
   credential, process, scheduler-mutation, client, broker, and network effects;
2. native credential provisioning receives material only through the opaque
   input seam, writes the exact family record, sanitizes failures, and never
   leaks sentinel secrets or creates a plaintext artifact;
3. wrong principal/vault owner, relative or dirty deployment, wrong source,
   wrong action, wrong trigger, or inaccessible provider fails closed;
4. install is disabled, attestation is read-only, and arming is impossible
   without a separately approved exact artifact;
5. concurrent or repeated invocation consumes one durable claim and permits at
   most one production read sequence;
6. early, late, expired, second-window, first-run-result ambiguity, read
   failure, non-flat state, disarm failure, or post-run mismatch produces a
   blocked commissioning result;
7. the actual production dispatcher and boundaries run for a complete offline
   canary simulation with persistent restart and post-run attestation; and
8. existing V5.35 dependency-direction, network, credential, broker-mutation,
   no-submit, provenance, identity, atomic-persistence, evidence, and burn-in
   suites remain intact.

## Verification And Handoff

The implementation owner must run focused V5.36 and affected V5.35 safety
suites, `python -m pytest tests/unit/test_dependency_direction.py`, and
`.\scripts\verify_offline.ps1 -Full` on the exact final commit with a clean
tree. The handoff records exact commands, commit, tree, exit codes, counts,
elapsed times, boolean-only credential presence, network/broker access,
scheduler mutation, credential provisioning, Git hygiene, residual risks, and
the exact next operator or independent-review action.

The verified branch may be pushed for independent review. Implementation must
not provision or read real credentials, register or arm a real task, access a
network or broker, execute the canary, merge itself, or claim operational proof.
