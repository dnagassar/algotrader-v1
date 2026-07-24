# V5.36.4a Native Buffer-View Lifetime Repair Contract

## Frozen Status And Chronology

This contract is frozen before the native buffer-view lifetime correction. Its
commit must be an ancestor of every production-code commit containing that
correction.

- Milestone: `V5.36.4a — native buffer-view lifetime repair`
- Implementation-owner classification: `implemented` or `blocked`; final
  disposition remains with an independent reviewer
- Exact independently reviewed V5.36.3 base:
  `cabf7e7c1e5958d68cec49c40c1d39a2dc8e5382`
- Exact base tree: `39100141f9b0f3154c6048ec91376709a3134884`
- Frozen V5.36.4 stage-diagnostic contract commit:
  `b5207d921ebdf49124f6b5a0742ea581fa2b05ef`

The reviewed V5.36 through V5.36.3 branches and worktrees remain immutable.
All provisioning grants and attempts remain terminal. No credential record is
assumed to exist.

## Newly Reproduced Defect

Credential-free tests exercised the production
`WindowsCredWriteNativeBoundary` with a fake native library and callable. The
boundary obtained a mutable `ctypes.from_buffer` view of the record and
returned success after exactly one fake call. The following mandatory
zeroization attempted to clear the original `bytearray` and raised:

`BufferError: Existing exports of data: object cannot be re-sized`

The same retained export masks setup and invocation classifications when an
exception traceback preserves the boundary frame. This explains a path by
which the provisioner can return generic `credential_writer_failed` after the
native boundary has been reached. It does not prove whether the post-review
paper attempt invoked `CredWriteW` or whether a record exists.

## Authorized Correction

The production boundary must deterministically release only its temporary
credential pointer, credential structure, and `ctypes.from_buffer` view before
control returns to one-use material cleanup on every success and failure path.

The correction must:

1. retain exactly one native call;
2. preserve the original mutable record as the only native blob source;
3. preserve target, flags, type, persistence, username, structure layout,
   record bytes, and error-code mapping;
4. perform no copy, retry, read, enumeration, deletion, rename, logging, or
   persistence outside the existing write;
5. preserve immediate overwrite-and-clear zeroization of the original record;
6. preserve the V5.36.4 fixed native setup, invocation, and unknown-result
   classifications; and
7. add no dependency on garbage collection timing.

## Required Credential-Free Proof

Injected tests must never load `Advapi32.dll` or access Credential Manager.
They must prove:

1. fake native success returns once, releases the view, and permits immediate
   overwrite and clear;
2. setup failure makes zero fake calls, releases any constructed view, and
   preserves `credential_writer_native_setup_failed`;
3. invocation failure makes exactly one fake call, releases the view, and
   preserves `credential_writer_native_invocation_failed`;
4. a false return with an unknown integer code releases the view and preserves
   `credential_writer_unknown_native_failure`;
5. one-use material is closed and cleared on all paths without a `BufferError`;
6. no raw exception, error code, secret sentinel, account sentinel, record
   bytes, reference, or credential length appears in output; and
7. existing prompt, authorization, runtime-source, provenance, dependency,
   credential, network, broker-mutation, no-submit, task, and live-prohibition
   suites remain intact.

## Prohibited Effects

During implementation and review, do not:

- access or mutate a real credential record;
- prompt for or access real credential/account values;
- reuse or retry any terminal grant;
- add a second native call or a native fallback;
- register, inspect, or mutate Task Scheduler;
- access a network, broker, paper endpoint, or live endpoint;
- perform an order operation or trading effect; or
- modify any reviewed V5.36 through V5.36.3 branch or worktree.

## Verification And Post-Review Gate

The implementation owner must run the focused V5.36.4/V5.36.4a suite,
affected safety suites, standalone dependency direction, and the full offline
verifier on the exact final clean commit. Independent review must cover the
temporary-view lifetime, exact one-call behavior, preserved structure layout,
zeroization, classification redaction, and source-bundle binding.

Only after independent review passes may the operator authorize fresh,
separate, non-reusable, one-hour grants and one new attempt per family. No
credential read, Task Scheduler, network, broker, paper, canary, or trading
authority follows from this repair.
