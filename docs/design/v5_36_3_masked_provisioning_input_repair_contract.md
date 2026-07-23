# V5.36.3 Masked Provisioning Input Repair Contract

## Frozen Status And Chronology

This contract is frozen before V5.36.3 implementation. Its commit must be an
ancestor of every V5.36.3 production-code commit.

- Milestone: `V5.36.3 — constant-width masked provisioning input repair`
- Implementation-owner classification: `implemented` or `blocked`; final
  disposition remains with an independent reviewer
- Exact independently reviewed V5.36.2 base:
  `707117b8c9bf5da54f04214d3ad61b13c48c35d8`
- Exact base tree: `8a6115b5c3a491536560ceb33e20ba7edca32279`
- V5.36.2 contract commit:
  `84a3910b449f0fd4510eb8027ba4cb0c2d0aa922`
- V5.36.2 implementation commit:
  `3d39df4e6007320e73216aba0671dc0330988d4d`

The reviewed V5.36, V5.36.1, and V5.36.2 branches and worktrees are immutable.
The two V5.36.2 provisioning grants generated at
`2026-07-23T16:22:07Z` are terminal generated state. They must not be used,
copied, extended, regenerated in place, retried, or treated as V5.36.3
evidence. Their ignored artifacts remain unchanged. No credential record is
assumed to exist.

## Operator Need And Security Decision

The reviewed V5.36.2 prompt deliberately echoes nothing. That prevents secret
characters from entering stdout, stderr, terminal transcripts, logs, or
receipts, but it gives the operator no visual confirmation that input was
received.

V5.36.3 may display a constant-width occupancy marker. Each prompt displays
exactly one `*` after the field becomes non-empty, regardless of the number of
characters entered. Backspace removes the marker only when the field becomes
empty. Enter completes the field and writes one newline. Credential
characters and credential length must never be echoed.

The only newly accepted disclosure is the boolean fact that the current field
is empty or non-empty. The marker is not credential material and must not be
persisted in a receipt. Keystroke timing, console recording, shoulder surfing,
clipboard handling, terminal compromise, process-memory inspection, and the
operator's local secret source remain outside the repository boundary.

## Required Production Boundary

The production prompt must:

1. use a Windows-compatible direct console character reader that does not
   enable terminal echo;
2. expose its character reader and fixed-output writer as explicit injected
   boundaries for credential-free tests;
3. accept only printable ASCII credential characters already permitted by the
   existing opaque material validator;
4. enforce the existing maximum field size without unbounded buffering;
5. support Enter and Backspace while keeping the visible marker
   constant-width;
6. ignore Windows extended-key pairs without adding them to material;
7. convert interruption, EOF, unavailable console input, malformed characters,
   and console I/O failure into fixed sanitized classifications;
8. clear mutable temporary character containers on every success and failure
   path; and
9. return material only to the existing one-use opaque provisioning boundary.

Failure must occur before native credential library loading, writer
construction, or Credential Manager access whenever input cannot be acquired
safely. No fallback to visible `input`, `Read-Host`, pipeline input, redirected
stdin, command arguments, environment variables, files, clipboard APIs, GUI
automation, or subprocess helpers is permitted.

## Preserved V5.36.2 Boundary

The exact-runtime launcher, isolated Python invocation, module-path and digest
binding, clean Git provenance, authorization schema, principal binding,
one-hour grant limit, matched credential family, native `CredWriteW` adapter,
sanitized native error mapping, credential-record layout, one-use material,
zeroization, successful receipt, and single-attempt governance remain
unchanged.

The V5.36.3 contract must join the production source-bundle manifest so the
final prompt behavior is bound to the exact deployment commit, tree, launcher,
module, and contract. No ambient or editable package resolution is permitted.

## Required Credential-Free Proof

Default tests must never prompt a human, load a credential DLL, or access
Windows Credential Manager. They must prove:

1. multiple secret characters produce exactly one occupancy marker;
2. no secret sentinel or secret length appears in captured stdout/stderr;
3. Backspace preserves the marker while the field remains non-empty and
   removes it only when the field becomes empty;
4. empty, overlong, non-printable, interrupted, EOF, extended-key, reader
   failure, and writer failure paths are fixed and sanitized;
5. the injected prompt supplies the existing opaque material without exposing
   key, secret, or expected-account values;
6. unavailable or failed prompting causes zero native, writer, Credential
   Manager, scheduler, network, broker, or mutation effects;
7. the exact production wrapper still executes the deployment module from
   paths containing spaces and non-default working directories;
8. the deliberately conflicting editable-installation proof remains intact;
9. source provenance includes this contract and the changed prompt module; and
10. existing dependency-direction, credential, network, broker-mutation,
    no-submit, runtime-source, provenance, identity, atomic-persistence,
    dispatcher, and Task Scheduler suites remain intact.

## Prohibited Effects

During implementation and review, do not:

- prompt for, read, enumerate, create, replace, rename, or delete a real
  credential;
- use or retry either terminal V5.36.2 grant;
- register, enable, start, disable, query, or delete a scheduled task;
- access a network, market-data service, broker, paper endpoint, or live
  endpoint;
- submit, cancel, replace, close, or liquidate an order;
- modify reviewed V5.36, V5.36.1, or V5.36.2 branches or worktrees; or
- weaken credential, dependency, network, broker, mutation, no-submit, source,
  or live-prohibition guards.

## Verification And Post-Review Gate

The implementation owner must run focused masked-input, provisioning-wrapper,
and runtime-source tests; affected V5.35/V5.36/V5.36.1/V5.36.2 safety suites;
standalone dependency direction; and
`scripts\verify_offline.ps1 -Full` on the exact final clean commit.

The handoff records boolean-only preflight, exact commands, commits, trees,
counts, elapsed times, dirty-file ownership, external-effect status, residual
risks, and the independent-review route. Only after an independent reviewer
passes the exact final V5.36.3 commit may the operator authorize two fresh,
non-reusable, one-hour provisioning grants and one new attempt per family.
Any result remains terminal for its grant.

No Task Scheduler, network, broker, paper, canary, or trading action follows
from this repair. The implementation owner must not merge or self-accept.
