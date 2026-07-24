# V5.36 Credential Provisioning And Windows Task Boundary

## Decision

V5.36 uses Windows Credential Manager as the production non-plaintext store,
with strict non-secret references of the form already defined by V5.35. The
scheduled child receives only an absolute path to a non-secret authorization
artifact. It resolves both credential records itself through the same provider
used by the production dispatcher. Secret values do not cross a process
boundary in arguments or environment variables and are not copied into alias
variables.

The bounded commissioning task uses Task Scheduler `InteractiveToken`, least
privilege, a one-time UTC trigger, no on-demand start, no restart, a 15-minute
execution limit, and `IgnoreNew`. This deliberately proves a scheduled
operator-session canary without storing a Windows logon password. It does not
claim logged-off service-account operation; that is a later, separately
reviewed host-hardening milestone.

## Trust And Threat Boundary

Trusted inputs are limited to:

- a separately reviewed, immutable V5.36 canary authorization artifact;
- a clean deployment at its exact 40-character commit and tree hashes;
- the named Windows principal and that same principal's credential vault;
- the native Windows Credential Manager read/write APIs;
- Task Scheduler reads and the four explicit mutations: register disabled,
  arm once, disable, and post-expiry cleanup; and
- injected market-data GET and paper read-only HTTP boundaries.

Untrusted or non-authorizing inputs include free-form chat, repository branch
names, environment credentials, profile aliases, relative paths, task
templates from an older milestone, stdout/stderr, existing task definitions,
and any authorization containing placeholders. Neither prose nor a command
switch can broaden the hashed artifact.

The design addresses disclosure by keeping secrets inside opaque, one-use
leases; escalation by exact principal, provider, family, endpoint, source, and
task-action checks; replay by a durable SQLite single-use claim committed
before external effects; and persistence by immutable receipts containing only
public references and hashes. Every production exception is reduced to a
sanitized classification. A bounded structural scan rejects secret-field
names, credential environment aliases, unexpected dot/temporary files, and
oversized output before commissioning can complete.

The design does not protect against a fully compromised Windows account,
administrator, Python runtime, broker, operating system, or native credential
API. It also cannot prove the current Task Scheduler result code while the task
is still executing. A credential-free post-run attestation therefore provides
the only terminal commissioning decision.

## Separate Credential-Write Gate

The supplied V5.36 canary authority permits credential reads but does not
authorize credential creation or replacement. Provisioning requires its own
strict `v5_36_windows_credential_provisioning_authorization_v1` artifact. That
artifact binds exactly one credential reference and family, Windows principal,
source commit and tree, a validity interval no longer than one hour, an
explicit credential-write grant, false task/network/broker grants, operator
approval, and its canonical SHA-256.

The operator-only provisioner accepts no secret parameter, environment
variable, pipeline value, or file. Python collects key, secret, and (for the
paper-observation family) expected account identity using non-echoing
interactive input. V5.36.3 displays one constant-width `*` only to indicate
that the current field is non-empty; it never displays a credential character
or credential length. Mutable buffers are assembled directly into the native
generic credential record, passed to `CredWriteW`, and zeroized. The output is
only a sanitized non-secret receipt. Default tests inject fake console and
writer boundaries and never call the Windows vault.

Market-data and paper-observation records are separate families. A market-data
record must not contain an account identity. A paper-observation record must
contain the expected account identity. Cross-family references, missing
account binding, extra account binding, malformed payloads, denial, expiry, or
source/principal mismatch fail before any other boundary.

### V5.36.1 diagnostic amendment

The two initial interactive attempts produced only
`credential_writer_failed`. That result does not establish whether native API
setup failed or `CredWriteW` returned false. V5.36.1 therefore places the
unchanged native write call behind an injected boundary and maps only supported
Windows error codes to fixed, sanitized categories: denied, invalid parameter,
invalid flags, unavailable logon session, bad username, and missing preserved
target. Native setup exceptions, unknown codes, and malformed boundary results
remain `credential_writer_failed`.

The diagnostic exposes neither raw error numbers nor operating-system text and
does not change the target, credential fields, persistence, flags, record
bytes, input path, or zeroization behavior. Implementation and review perform
no credential operation. The observed generic failures authorize no retry and
identify no adapter correction. After independent review, diagnosis requires
fresh one-hour provisioning grants and a new explicit operator action. Any
behavioral correction identified by that attempt requires a separately frozen
contract and review.

### V5.36.2 exact runtime-source amendment

The first post-review V5.36.1 attempts exposed an ambient editable-installation
hazard: bare `python -m` executed the older V5.36 module while Git provenance
described the requested V5.36.1 worktree. V5.36.2 replaces that launch with an
absolute repository-owned entry point under Python isolated mode. The entry
point places only the exact deployment `src` directory first, verifies the
imported module path, and passes the launcher-derived deployment root into the
provisioner.

Before authorization loading, identity lookup, prompting, material creation,
or native access, the provisioner now binds its own resolved source path and
normalized SHA-256 to the clean source-bundle manifest. The same provenance is
then used for authorization commit/tree checks. Missing launcher/module
bindings, ambient modules, dirty source, or digest mismatch produce only fixed
sanitized classifications. No credential-record or native-write behavior is
changed by this amendment.

### V5.36.3 constant-width masked-input amendment

V5.36.3 replaces the visually blank prompt with a direct Windows console
reader that keeps terminal echo disabled. The prompt displays exactly one `*`
while a field is non-empty, independent of its length, and erases that marker
only when Backspace returns the field to empty. The only disclosed state is
empty versus non-empty.

The console reader and fixed-output writer are injected boundaries in default
tests. Empty, malformed, overlong, interrupted, unavailable, or failed console
input returns a fixed sanitized classification before the credential writer is
constructed. No visible-input, redirected-stdin, environment, file, clipboard,
GUI, or subprocess fallback exists. Native record layout, `CredWriteW`
behavior, runtime-source binding, authorization, and single-attempt gates are
unchanged.

### V5.36.4 credential-writer stage diagnostic amendment

The post-review V5.36.3 paper-observation attempt completed all three masked
fields and returned `credential_writer_failed`. That result proves only that
the request reached the writer boundary; it does not prove that `CredWriteW`
was invoked or that a credential record exists.

V5.36.4 preserves the existing supported Windows error mappings and adds three
fixed distinctions. Native setup or pre-call construction failure reports
`credential_writer_native_setup_failed`; an exception from the bound
`CredWriteW` call reports `credential_writer_native_invocation_failed`; and a
false native return with an unrecognized integer code reports
`credential_writer_unknown_native_failure`. Raw codes, OS messages, exception
text, structure contents, and credential material remain prohibited from
output.

The production library loader and last-error reader are injected in default
tests. Those tests use fake callables, never load `Advapi32.dll`, and never
access Credential Manager. Successful record layout, target, persistence,
prompt behavior, exact-runtime binding, authorization, zeroization, and
single-attempt governance are unchanged. A newly identified adapter defect
still requires a later frozen repair and independent review before correction
or retry.

### V5.36.4a native buffer-view lifetime amendment

Credential-free fake-native testing then reproduced a retained
`ctypes.from_buffer` export. The export prevented mandatory record clearing
after the native boundary returned or raised, causing `BufferError` to mask
the underlying result as generic `credential_writer_failed`.

V5.36.4a required deterministic release of only the temporary credential
pointer, structure, and buffer view before one-use material cleanup. It
prohibited copying the record, adding a native call, changing record bytes or
structure fields, depending on garbage collection, or broadening credential
authority. The prior real credential-record state remains unknown.

### V5.36.4b direct bytearray address amendment

Synthetic proof then showed that dropping Python references did not release
the `ctypes.from_buffer` export without garbage collection. That mechanism was
rejected before a production commit.

V5.36.4b instead uses CPython's `PyByteArray_AsString` API to obtain the
address of the original non-empty mutable record without copying it or
creating an exported buffer. The record argument remains strongly referenced
for the exact one native call. Address resolution fails as sanitized native
setup failure, and immediate overwrite and clear must succeed without garbage
collection after every return or exception. No fallback is permitted.

### V5.36.5 external authorization path amendment

The first post-provisioning canary preview returned
`blocked_task_path_escape` before any Task Scheduler, credential, network, or
broker boundary. The operator-owned authorization artifact correctly lived
outside generated output under the local operator-grant directory, but the
task builder incorrectly applied repository-root containment to that
separately trusted artifact as well as to the repository-owned wrapper.

V5.36.5 keeps the wrapper and working directory strictly contained within the
exact deployment root. It separately requires the authorization artifact to
be an absolute, existing, non-symlink regular file, resolves it strictly, and
places only that exact resolved path in the task arguments. The authorization
file may therefore remain outside the deployment root. Its schema, payload
hash, source, principal, credential-reference, endpoint, timing, and
authorization gates are still revalidated at each lifecycle boundary.

The blocked authorization and window remain terminal. This amendment performs
no Task Scheduler, credential, network, or broker operation and authorizes no
retry. A fresh canary requires independent review of the exact repair commit
and a new operator authorization with new times.

### V5.36.5a concurrent evidence scan coordination amendment

Broader credential-free verification exposed an order-dependent evidence race.
Duplicate no-op executions persist fixed immutable receipts using atomic
same-directory temporary files. One such active write could overlap the
admitted execution's structural leak scan, causing the scanner to classify the
repository-owned temporary file as residual secret persistence.

V5.36.5a serializes V5.36 immutable evidence writes and the structural scan
with one in-memory reentrant lock. The scanner's token, size, dot-file, and
`.tmp` rules remain unchanged: any temporary file present while the scanner
owns the lock still blocks. Duplicate invocations remain durable no-ops, and
the SQLite claim remains the external-effect fence with exactly one admitted
execution.

## Canary Authorization Gate

The exact schema is `v5_36_scheduled_canary_authorization_v1`. It rejects
unknown or missing fields and binds:

- authorization ID and canonical SHA-256;
- task identity `\crypto-tournament-v2-oos-scheduler`;
- an hour-aligned closed-window start and end;
- scheduled start exactly five minutes after window close;
- automatic-disarm deadline after start and no later than 55 minutes after it;
- matching Windows principal and credential-vault owner;
- task logon type `InteractiveToken`;
- absolute deployment root, exact source commit, and exact source tree;
- provider `windows-credential-manager`;
- one `alpaca-market-data` reference and one
  `alpaca-paper-observation` reference;
- exact market and paper endpoints;
- true read/task/network/operator grants; and
- false submit, cancel, replace, close, liquidation, paper-mutation, live,
  retry, and additional-window grants.

`<EXACT_CLOSED_WINDOW>`, `<NON_SECRET_REFERENCE>`,
`<VERIFIED_V5_36_COMMIT>`, `<EXACT_UTC_TIME>`, `TBD`, `TODO`, and similar
markers are always invalid. The artifact path itself must be absolute and not
a link. The runner cannot generate or approve this artifact.

## Transactional Lifecycle

The lifecycle is deliberately split so an independent reviewer and operator
can stop at each boundary:

1. `preview` validates the public artifact and renders a hash of the exact
   disabled task definition. It performs no task, vault, or network operation.
2. `install-disabled` commits an install claim, registers a new disabled task
   from XML supplied over stdin (no temporary file), reads it back, and binds
   the result. An already existing identity is rejected.
3. `attest-disabled` performs a read-only comparison of task identity,
   principal, logon type, action, arguments, working directory, trigger,
   disabled state, and restrictive settings.
4. `arm-exact-window` commits an arm claim, revalidates source/time/task and
   both credential records, then enables only the exact one-time trigger and
   task. It never calls `Start-ScheduledTask`.
5. `execute` commits the unique execution claim before reading the scheduler,
   vault, creating a process, constructing a client, or reaching a network.
   The exact `RealCommandDispatcher` then performs the accepted-window
   market-data GET and paper observation. Duplicate claims persist immutable
   no-op evidence with zero external access.
6. `disarm` runs in guaranteed cleanup after the first attempt, regardless of
   outcome. It is idempotent and constructs neither an identity resolver nor a
   credential provider. Failure blocks commissioning.
7. `post-run-attest` is credential-free. It requires the exact successful
   terminal result, matching last-run time, task and trigger disabled, no next
   run, one durable execution, valid cross-hashed evidence, flat paper state,
   and zero mutation facts. Any failure persists a blocked receipt and moves
   durable state to `blocked`.

No operation automatically retries an ambiguous result. No state transition
permits a second window. The task action contains only the wrapper mode,
absolute authorization path, and non-secret authorization switches.

## Evidence Contribution

V5.36 contributes the production-host bridge that V5.35 intentionally lacked.
V5.35 proved the secure read-only dispatcher and 24-cycle burn-in offline;
V5.36 binds that dispatcher to a real Windows principal, vault-reference
resolution point, immutable deployment, exact scheduled task action, one
durable admission, guaranteed disarm, and terminal host evidence.

The resulting packet is commissioning evidence for one bounded read-only
attempt only. It does not establish long-running unattended reliability,
logged-off execution, mutation authority, strategy performance, paper-trading
readiness, or live readiness.

## Operator Route After Independent Review

Before any host effect, an independent agent must review the final clean commit
and classify the implementation separately. If that review passes, the
operator must resolve the exact closed window, non-secret references, Windows
principal/vault owner, immutable deployment root, final commit/tree, and
disarm deadline in a hashed authorization artifact. Secrets must never be sent
through chat or placed in that artifact.

If the two exact credential records do not already exist, stop and obtain a
separate credential-provisioning authorization for each family. Provision from
an interactive console owned by the exact task principal; never from a remote
transcript, redirected stdin, credential-bearing environment, or repository
file. Then close that console and return to a credential-free shell for
preview and task review.

Registration, disabled attestation, arming, and execution are distinct gates.
Do not combine them in a script, enable the task early, invoke it manually, or
repeat a failed/ambiguous attempt. After the first attempt, run the
credential-free post-run attestation. A blocked result is terminal for that
authorization.
