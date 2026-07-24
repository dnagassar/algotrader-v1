# V5.36.5 External Canary Authorization Path Contract

## Status And Scope

- Milestone: `V5.36.5 — external canary authorization path repair`.
- Accepted implementation base:
  `dddea20e19c7b30834e8e3d547567ce1e53bba91`.
- Accepted base tree:
  `cb058c6a2b935bc821f9d26b18467b6a5cd8ca93`.
- The V5.36.4 credential-provisioning attempts are terminal successes.
- The canary authorization
  `v536-canary-20260724t0105z` is terminal and must not be edited, retried, or
  reused.
- This contract authorizes offline implementation and verification only. It
  grants no credential read, Task Scheduler operation, network access, broker
  access, paper mutation, order operation, canary activation, or trading
  effect.

## Terminal Defect Evidence

The first preview of the independently reviewed V5.36.4 deployment returned
the fixed classification `blocked_task_path_escape`. Preview stopped before
Task Scheduler construction, credential reads, network access, or broker
access.

The operator-owned authorization artifact was an absolute, existing,
non-symlink regular file under:

`%LOCALAPPDATA%\algo_trader\operator_grants`

The V5.36 runbook requires the immutable authorization artifact to live
outside generated output. The task builder nevertheless applied the
deployment-root containment rule to both:

1. the repository-owned task wrapper; and
2. the separately owned authorization artifact.

The second rule rejected the intended trust-boundary layout before preview
could render the disabled task definition.

## Required Boundary

V5.36.5 must preserve source containment for executable task components while
allowing the separately validated authorization artifact to remain outside
the deployment root.

`build_v536_task_spec` must:

1. require the deployment root to resolve successfully;
2. require the repository-owned PowerShell wrapper to resolve successfully
   and remain within the resolved deployment root;
3. require the authorization artifact path to be absolute;
4. reject a symlink authorization artifact;
5. require the authorization artifact to resolve strictly to an existing
   regular file;
6. allow that resolved regular file to be outside the deployment root;
7. place only that exact resolved authorization path in the scheduled task
   arguments;
8. preserve the deployment root as the scheduled task working directory; and
9. reduce all path validation failures to fixed sanitized classifications
   without exposing exception text.

The existing authorization loader remains responsible for strict UTF-8 JSON,
schema, placeholder, gate, principal, source, reference, endpoint, time, and
canonical-hash validation. Runtime source binding and task snapshot
attestation remain unchanged.

## Security Invariants

The repair must not:

- allow the executable wrapper or working directory to escape the deployment
  root;
- accept a relative, missing, directory, or symlink authorization path;
- introduce environment expansion, shell interpolation, secret arguments, or
  plaintext material;
- change task identity, principal, logon type, trigger, deadline,
  least-privilege settings, disabled installation, on-demand-start policy,
  restart policy, `IgnoreNew`, or the execution time limit;
- add `Start-ScheduledTask`, retry, a second window, or an additional task;
- weaken authorization hash, source provenance, current-principal,
  credential-family, endpoint, flat-paper-state, mutation, disarm, or
  post-run-attestation checks; or
- read or mutate real credentials, operate Task Scheduler, contact a network
  or broker, mutate paper state, perform an order action, activate a canary,
  or enable live trading during implementation or default verification.

The scheduled task remains bound to the authorization payload hash through
its registration source and to the exact resolved authorization path through
its immutable action arguments. Replacing or modifying the external artifact
cannot silently broaden authority because execution reloads and validates the
artifact and task attestation compares the registered definition against the
current validated authorization.

## Verification Contract

Credential-free unit tests must prove:

1. an existing regular authorization artifact outside the deployment root
   produces a valid task specification;
2. the exact resolved external artifact path appears in task arguments;
3. the wrapper and working directory remain inside the deployment root;
4. a relative, missing, directory, or symlink artifact fails closed;
5. a wrapper escape still returns `task_path_escape`;
6. task XML and snapshot invariants remain unchanged;
7. authorization, host-canary, wrapper, source-provenance, dependency, network,
   broker-mutation, and no-submit regressions remain green; and
8. the full offline verifier completes with no credential, scheduler, network,
   broker, paper, order, canary, or trading effect.

## Review And Operator Route

Implementation must be committed only after this contract is frozen. An
independent reviewer must inspect the exact clean implementation commit and
classify the repair.

Only after an accepted review may the operator authorize a fresh, immutable,
single-window canary artifact with new times. The terminal
`v536-canary-20260724t0105z` artifact cannot be moved, edited, rehashed,
retried, or reused. A future preview or lifecycle remains separately
operator-gated and must stop on its first terminal or ambiguous result.
