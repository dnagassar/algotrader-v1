# V5.35 Credential Provider And Threat Boundary

## Architecture Decision

V5.35 uses Windows Credential Manager generic credentials as its production
non-plaintext store. Operators provision records outside this repository and
refer to them with a non-secret identifier of the form:

```text
wincred:algotrader/v5.35/<credential-family>/<record-name>
```

The record blob is UTF-8 JSON with schema `v5_35_credential_record_v1`, one
exact family, one API key ID, one API secret, and (for paper observation) one
expected account identity. The key, secret, family, and account binding are
therefore read from one atomic operating-system credential record. V5.35 does
not search environment aliases, combine independently sourced values, read a
plaintext file, or accept credentials in command arguments.

`CredentialProvider` returns a one-use opaque lease. Its string and repr forms
are always redacted; a lease invokes one boundary callback and zeroizes its
mutable buffers on success or failure. Provider errors have fixed
classifications and never include target payloads, raw operating-system error
messages, or secret material.

## Cross-Process Boundary

`RealCommandDispatcher` receives only the provider name, credential reference,
exact paper profile, exact read-only market-data endpoint, and scheduler/window
configuration. Before creating a child it opens, validates, and immediately
zeroizes the referenced record. Provider unavailable, denied, malformed, or
family-mismatched records therefore produce zero child processes.

The child receives only the strict non-secret reference and independently
opens the same record at the read-only HTTP boundary. No secret is copied into
`argv`, a process environment, an environment alias, stdout/stderr, a receipt,
or persisted state. The dispatcher discards child stdout/stderr on failures and
returns a fixed sanitized classification.

The paper-observation boundary follows the same rule in-process: public gates
and exact endpoints are validated first, then the opaque lease is consumed
inside the private read-only SDK/HTTP adapter. The adapter exposes no submit,
cancel, replace, close, or liquidation method.

## Threat Boundary

V5.35 protects against:

- plaintext credentials in repository-controlled files or generated evidence;
- command-line and inherited-environment disclosure;
- key/secret mixing across aliases or credential families;
- accidental stringification through repr, exceptions, logs, or receipts;
- live, ambiguous, or noncanonical endpoint/profile selection;
- process/client/network creation after credential-provider failure;
- replay of a second same-window external read; and
- forged, incomplete, or cross-window evidence used to claim burn-in status.

Windows Credential Manager, the signed-in Windows account, the Python process
memory while a lease callback is executing, the Alpaca SDK, TLS, and the remote
read-only services remain trusted boundaries. V5.35 does not attempt to defend
against a compromised Windows account, process-memory inspection by an
administrator, a compromised SDK/runtime, or a compromised remote endpoint.

## Provisioning And Activation Gate

This milestone implements only the adapter and offline proof. It does not call
Credential Manager, provision a record, inspect a real record, register or
enable a task, or contact any endpoint. Real provisioning, ACL review,
credential rotation, task registration, task enabling, and first network use
remain separate operator actions outside V5.35.
