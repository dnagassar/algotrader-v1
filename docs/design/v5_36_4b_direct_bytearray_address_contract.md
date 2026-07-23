# V5.36.4b Direct Bytearray Address Contract

## Frozen Status And Chronology

This contract is frozen before production replaces the retained exported
buffer view. Its commit must be an ancestor of the production correction.

- Milestone: `V5.36.4b — direct bytearray address repair`
- Exact independently reviewed V5.36.3 base:
  `cabf7e7c1e5958d68cec49c40c1d39a2dc8e5382`
- Frozen V5.36.4 stage-diagnostic contract:
  `b5207d921ebdf49124f6b5a0742ea581fa2b05ef`
- Frozen V5.36.4a lifetime contract:
  `df38bfe78929ce0c6ed6df9ba605bd2aef84e897`

All earlier grants and attempts remain terminal, and real credential-record
state remains unknown.

## Rejected Mechanism

Credential-free synthetic proof showed that assigning `None` to the temporary
pointer, structure, and `ctypes.from_buffer` view does not release the
bytearray export deterministically. The ctypes ownership graph continues to
block `bytearray.clear()` until garbage collection. Explicitly clearing the
structure field or its exposed ownership dictionary also failed to release the
export.

No production commit contains that ineffective mechanism. V5.36.4b prohibits
depending on garbage collection or manipulating undocumented ctypes ownership
state.

## Authorized Direct-Address Boundary

Production may replace `ctypes.from_buffer` with CPython's
`PyByteArray_AsString` C API to obtain the address of the existing non-empty
`bytearray`. The record argument itself remains strongly referenced throughout
the one native call, so the address remains valid. The boundary must:

1. use the original mutable record as the sole native blob source;
2. create no record copy and no exported buffer view;
3. validate that the returned address is a non-zero integer before native
   library loading or invocation;
4. preserve exact record length, structure layout, target, flags, persistence,
   username, and one-call behavior;
5. release temporary address, pointer, and structure references in `finally`;
6. allow immediate overwrite and clear without garbage collection on every
   success and failure path; and
7. map address-API setup or address-resolution failure only to
   `credential_writer_native_setup_failed`.

No other Python implementation is authorized for production by this contract.
An unavailable CPython bytearray-address API must fail closed; it must not copy,
fall back to an exported view, use a subprocess, or access a file.

## Required Credential-Free Proof

Tests use only synthetic bytearrays and fake native libraries. They must prove:

- the native pointer observes the exact synthetic record bytes before the fake
  call returns;
- fake success and each fixed failure path make at most one fake call;
- immediate overwrite and clear succeeds without `gc.collect()`;
- setup and invocation classifications survive mandatory zeroization;
- unknown integer results retain the fixed unknown-native classification;
- no raw code, exception text, record bytes, sentinel, path, or length leaks;
- the source contains no `ctypes.from_buffer` record binding or record-copy
  fallback; and
- all V5.36 through V5.36.4a safety, source, prompt, and no-effect contracts
  remain intact.

## Prohibited Effects And Post-Review Gate

Implementation and review may not access Credential Manager, prompt for real
material, reuse a grant, inspect a credential, operate Task Scheduler, access a
network or broker, mutate paper state, perform an order action, or affect
trading.

After focused and full offline verification, the exact final commit requires
independent review. Only a later explicit operator authorization may create
fresh one-hour grants. No provisioning attempt is authorized by this repair.
