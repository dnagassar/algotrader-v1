# V5.36.1 Credential-Writer Diagnostic Repair Contract

## Frozen Status And Chronology

This contract is frozen before V5.36.1 implementation. Its commit must be an
ancestor of every V5.36.1 production-code commit.

- Milestone: `V5.36.1 — credential-writer diagnostic repair`
- Classification available to the implementation owner: `implemented` or
  `blocked`; operational disposition remains outside the implementation owner
- Exact base: independently accepted V5.36 commit
  `34816b760a2d2a7cf1eefd219a86fd98a628b979`
- Exact base tree: `262e0f5c8749ff9346fd729917a63bbe6c15c21f`
- Accepted V5.36 contract commit:
  `7da4ed68386135d68e204498148b83c6464c0ffd`
- Accepted V5.36 implementation commit:
  `208c1edc7adf8c09c0db09b6fac2f1fb2e6a7c1a`

The accepted V5.36 branch is immutable. The failed, time-limited provisioning
grants and the accepted canary authorization remain generated state and must
not be copied, edited, renewed, consumed, or treated as successful evidence by
this repair.

## Trigger And Scope

Two separately authorized, interactive, no-echo attempts acquired material and
returned the sanitized `credential_writer_failed` classification. The accepted
wrapper maps both native setup/call exceptions and unrecognized false returns
from `CredWriteW` to that classification, so the observations do not prove that
`CredWriteW` was invoked. No credential record is assumed to exist. No
credential value, account identity, Windows error code, task effect, network
request, broker request, or trading effect was exposed or persisted.

The host checks available without credential access show the intended
interactive principal, a running Credential Manager service, a matching
64-bit process/OS ABI, a correct 80-byte `CREDENTIALW` layout, and generic
credential persistence capability through `CRED_PERSIST_ENTERPRISE`. Those
checks do not identify the native failure category.

V5.36.1 is authorized only to make the native failure category safely
diagnosable and offline-verifiable. It must not infer a fix from the generic
failure and must not change successful credential-record contents, target
naming, persistence, secret input, zeroization, or write timing before a fresh,
separately authorized operator attempt identifies the exact category.

## Required Diagnostic Boundary

The production writer must call `CredWriteW` through one explicit injectable
native boundary. The boundary returns success or a Windows error code without
receiving any logging, receipt, persistence, exception-formatting, scheduler,
network, or broker capability.

The production adapter must convert supported errors into fixed classifications:

- access denied;
- invalid parameter or protected-field conflict;
- invalid flags;
- unavailable credential set or logon session;
- bad username;
- missing target when a preserve operation is requested; and
- unknown native failure.

Raw numeric error codes, operating-system messages, target metadata, usernames,
credential values, account identities, blobs, structure dumps, and exception
representations must not appear in stdout/stderr, logs, receipts, persisted
state, or public exception text. Unknown codes remain a single generic
fail-closed classification.

The native boundary must be dependency-injected for default tests. Those tests
must never load `Advapi32.dll`, call Credential Manager, prompt for real input,
or depend on a Windows credential set.

## Required Offline Proof

Credential-free tests must prove:

1. native success preserves the existing receipt and zeroization behavior;
2. each supported Windows error maps to exactly one sanitized classification;
3. an unknown error maps to the generic classification;
4. a native-boundary exception maps to the generic classification;
5. no raw error code, OS message, sentinel key, sentinel secret, sentinel
   account identity, target blob, argv alias, environment alias, temporary
   file, or persisted secret appears in any observable output;
6. authorization, time, source, principal, and credential-family failures
   occur before material creation or native invocation;
7. the provisioner remains write-only and cannot read, enumerate, delete, or
   rename credentials;
8. no Task Scheduler, process-runner, network, broker, paper, order, or live
   boundary is reachable; and
9. accepted V5.36 credential, dispatcher, task, provenance, dependency,
   network, broker-mutation, and no-submit suites remain intact.

## Post-Implementation Gate

Implementation and independent review remain credential-free. After an
independent reviewer approves the exact V5.36.1 commit, the prior grants remain
invalid for further use. The operator may then authorize fresh one-hour grants
for the two exact V5.36 production references and perform a new interactive
attempt.

That attempt may report only its fixed sanitized classification and non-secret
receipt fields. If it identifies a host/session category, remediation remains
an operator action. If it identifies an adapter parameter category, any
behavioral correction requires a new frozen repair contract and independent
review before another credential write. No blind retry is authorized.

## Prohibited Effects

During implementation and review, do not:

- read, enumerate, create, replace, rename, or delete any credential;
- access real credential or account values;
- register, enable, start, disable, or delete a scheduled task;
- access a network, market-data service, broker, or paper endpoint;
- submit, cancel, replace, close, or liquidate an order;
- modify the accepted V5.36 worktree or branch; or
- weaken any credential, dependency, network, broker, mutation, no-submit, or
  live-prohibition guard.

## Verification And Handoff

The implementation owner must run the focused V5.36.1 provisioning tests,
affected accepted V5.36 safety suites, standalone dependency-direction suite,
and `scripts\verify_offline.ps1 -Full` on the exact final clean commit. The
handoff records exact commands, commits, trees, counts, elapsed times,
boolean-only preflight, external-effect status, residual risks, and the fresh
operator authorization required after independent review.

The verified branch may be pushed for independent review only. The
implementation owner must not merge, self-approve, provision, activate, or
consume any canary authorization.
