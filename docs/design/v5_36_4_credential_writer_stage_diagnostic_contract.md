# V5.36.4 Credential-Writer Stage Diagnostic Contract

## Frozen Status And Chronology

This contract is frozen before V5.36.4 implementation. Its commit must be an
ancestor of every V5.36.4 production-code commit.

- Milestone: `V5.36.4 — credential-writer stage diagnostic repair`
- Implementation-owner classification: `implemented` or `blocked`; final
  disposition remains with an independent reviewer
- Exact independently reviewed V5.36.3 base:
  `cabf7e7c1e5958d68cec49c40c1d39a2dc8e5382`
- Exact base tree: `39100141f9b0f3154c6048ec91376709a3134884`
- V5.36.3 contract commit:
  `8ff9e307920886d6d2dd5ff29636655505ca4575`
- V5.36.3 masked-input implementation commit:
  `65e94cb16f15a2ff13052480102c13475e6f05ff`

The reviewed V5.36, V5.36.1, V5.36.2, and V5.36.3 branches and worktrees are
immutable. All earlier provisioning grants and attempts are terminal generated
state. They must not be copied, extended, regenerated in place, retried, or
treated as credential-record evidence. No credential record is assumed to
exist.

## Trigger And Evidence Boundary

The post-review V5.36.3 market-data launch had no visible interactive console
and was terminated as ambiguous without retry. The separately authorized
paper-observation attempt displayed the constant-width marker for all three
required fields and returned the fixed `credential_writer_failed`
classification.

That paper result proves only that exact runtime-source binding, authorization,
time, principal, family, and masked material acquisition reached the writer
boundary. The current writer still maps native-library setup exceptions,
`CredWriteW` invocation exceptions, and false native returns with unrecognized
error codes to the same generic classification. The result therefore does not
prove that `CredWriteW` was invoked and does not authorize a behavioral fix.

V5.36.4 is limited to making those three failure stages distinguishable
without exposing native details. It does not change successful record bytes,
target naming, flags, persistence, username, prompt behavior, material
lifetime, zeroization, authorization, source binding, or write timing.

## Required Diagnostic Boundary

The production native boundary must retain one `CredWriteW` call and return
only success or a native error code. It must convert production exceptions
into these fixed classifications:

- `credential_writer_native_setup_failed` when native-library loading,
  symbol/signature binding, credential-structure construction, or pre-call
  native preparation fails;
- `credential_writer_native_invocation_failed` when the bound `CredWriteW`
  call raises before a valid return is obtained; and
- `credential_writer_unknown_native_failure` when `CredWriteW` returns false
  with an integer error code outside the existing supported mapping.

The existing supported mappings for access denied, invalid parameter, invalid
flags, missing preserved target, unavailable logon session, and bad username
remain unchanged. A malformed injected result, an unexpected adapter
exception, or an unapproved injected classification remains the generic
`credential_writer_failed` fail-closed result.

Only the two approved stage exceptions may cross from the native boundary to
the sanitizing writer. Raw numeric codes, operating-system messages, exception
text, paths, structure contents, target metadata, usernames, references,
credential values, account identities, and blobs must never enter public
output, persisted state, receipts, or exception representations.

The native-library loader and last-error reader must be injectable for default
tests. Production defaults may resolve only the existing Windows native
library and error reader. Injected tests must exercise the production boundary
with fake callables and must never load `Advapi32.dll`, invoke Credential
Manager, or depend on a Windows credential set.

## Required Credential-Free Proof

Default tests must prove:

1. native setup failure maps only to
   `credential_writer_native_setup_failed` and performs zero native calls;
2. native invocation exception maps only to
   `credential_writer_native_invocation_failed` after exactly one fake call;
3. each existing supported integer code retains its fixed classification;
4. an unrecognized integer code maps only to
   `credential_writer_unknown_native_failure`;
5. malformed native results and arbitrary injected exceptions remain
   `credential_writer_failed`;
6. no raw error code, exception text, credential sentinel, account sentinel,
   record bytes, target metadata, or credential length appears in output;
7. success preserves the V5.36.3 record layout, receipt, one-use material,
   zeroization, constant-width prompt, exact-runtime, and source-binding
   behavior;
8. authorization, time, source, principal, family, and masked-input failures
   still occur before writer construction or native access;
9. the provisioner remains write-only and has no credential read, enumeration,
   deletion, rename, Task Scheduler, network, broker, paper-mutation, order, or
   live capability; and
10. existing dependency-direction, credential, network, broker-mutation,
    no-submit, provenance, identity, atomic-persistence, dispatcher, and task
    suites remain intact.

## Prohibited Effects

During implementation and review, do not:

- prompt for, read, enumerate, create, replace, rename, or delete a real
  credential;
- access real credential or account values;
- reuse or retry any terminal provisioning grant;
- register, enable, start, disable, query, or delete a scheduled task;
- access a network, market-data service, broker, paper endpoint, or live
  endpoint;
- submit, cancel, replace, close, or liquidate an order;
- modify reviewed V5.36/V5.36.1/V5.36.2/V5.36.3 branches or worktrees; or
- weaken credential, dependency, network, broker, mutation, no-submit, source,
  prompt, or live-prohibition guards.

## Verification And Post-Review Gate

The implementation owner must run focused production-boundary and provisioning
tests, affected V5.35/V5.36/V5.36.1/V5.36.2/V5.36.3 safety suites, standalone
dependency direction, and `scripts\verify_offline.ps1 -Full` on the exact final
clean commit. The handoff records boolean-only preflight, exact commands,
commits, trees, counts, elapsed times, dirty-file ownership, external-effect
status, residual risks, and the independent-review route.

Only after an independent reviewer passes the exact final V5.36.4 commit may
the operator authorize two fresh, separate, non-reusable, one-hour grants and
one new attempt per family. Any result is terminal for its grant. A newly
identified adapter defect requires another frozen repair contract and review
before correction or retry.

No Task Scheduler, network, broker, paper, canary, or trading action follows
from this diagnostic repair. The implementation owner must not merge,
self-approve, provision, or activate.
