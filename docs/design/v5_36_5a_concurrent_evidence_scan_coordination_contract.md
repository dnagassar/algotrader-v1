# V5.36.5a Concurrent Evidence Scan Coordination Contract

## Status And Scope

- Milestone:
  `V5.36.5a — concurrent immutable-evidence scan coordination`.
- Parent repair:
  `V5.36.5 — external canary authorization path repair`.
- Accepted implementation base:
  `dddea20e19c7b30834e8e3d547567ce1e53bba91`.
- This contract authorizes offline implementation and verification only.
- It grants no credential read, Task Scheduler operation, network access,
  broker access, paper mutation, order operation, canary activation, retry,
  additional window, or trading effect.

## Deterministic Defect Evidence

The existing concurrent-execution safety test admits one execution and returns
immutable no-op receipts for all duplicate invocations. The admitted execution
persists role evidence and then scans the complete canary output tree for
forbidden tokens and temporary files.

Every immutable JSON write correctly uses an atomic same-directory temporary
file followed by `os.replace`. A duplicate no-op receipt can therefore create
its repository-owned atomic temporary file while the admitted execution is
enumerating the output tree. The scanner then returns
`blocked_secret_persistence_detected` even though the temporary file belongs
to an active fixed-schema duplicate receipt and contains no credential
material.

The test passes in isolation when scheduling lets the admitted execution scan
before duplicate persistence, but fails repeatably in the full host-canary
file. The admitted execution remains unique and the duplicate invocations
perform no credential, process, network, broker, scheduler-mutation, paper, or
order effect.

## Required Coordination

V5.36.5a must coordinate V5.36 immutable evidence writes and the structural
secret scan with one process-wide reentrant lock:

1. every call through the V5.36 `_write_json_immutable` wrapper must hold the
   lock for the complete atomic write;
2. `_structural_secret_leak_scan` must hold the same lock for its complete
   traversal and content scan;
3. the lock must be in-memory only and create no lock file or persisted
   artifact;
4. the scanner must retain its existing bounded size, extension, forbidden
   token, dot-file, and `.tmp` checks unchanged;
5. a temporary file that exists when the scanner owns the lock remains a
   terminal `secret_persistence_detected` result; and
6. immutable duplicate receipts must still be persisted and the durable
   execution count must remain exactly one.

The coordination removes only overlap with an active repository-owned atomic
write. It does not ignore, delete, rename, age out, or retry any temporary
artifact.

## Security Invariants

The repair must not:

- suppress or filter temporary files from the structural scan;
- retry a failed scan or delete evidence to obtain a pass;
- weaken immutable-write existence checks, flush, `fsync`, or atomic replace;
- change the single durable execution claim or duplicate no-op semantics;
- permit a duplicate credential read, subprocess, network request, broker
  request, scheduler mutation, paper mutation, or order action;
- change pending, blocked, disarm, post-run attestation, source, task,
  authorization, account-flatness, or no-submit validation; or
- add cross-process authority, manual execution, retry, another window, paper
  mutation, or live trading.

The scheduled task retains `IgnoreNew`, and the durable SQLite claim remains
the cross-process external-effect fence. The in-memory lock coordinates only
the evidence writers and scanner within one process; it does not grant or
claim a new inter-process execution mechanism.

## Verification Contract

Credential-free tests must prove:

1. one concurrent invocation returns
   `canary_reads_complete_pending_terminal_attestation`;
2. all other concurrent invocations return
   `duplicate_canary_execution_no_op`;
3. every duplicate receipt is persisted immutably;
4. process, network, broker, scheduler-disarm, and durable execution counts
   remain exactly one where required;
5. an actual pre-existing temporary or forbidden-token artifact still blocks;
6. all V5.36.5 path, authorization, task, host-canary, wrapper, provenance,
   dependency, network, broker-mutation, and no-submit regressions pass; and
7. the full offline verifier remains credential-free, scheduler-free,
   network-free, broker-free, mutation-free, order-free, and trading-free.

## Review And Operator Route

An independent reviewer must inspect the exact clean V5.36.5/V5.36.5a
implementation commit. The terminal canary authorization remains unusable.
Only after accepted review may the operator create and approve one fresh
single-window artifact with new times. No operational action follows from this
contract or its implementation.
