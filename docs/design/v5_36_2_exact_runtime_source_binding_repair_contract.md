# V5.36.2 Exact Runtime-Source Binding Repair Contract

## Frozen Status And Chronology

This contract is frozen before V5.36.2 implementation. Its commit must be an
ancestor of every V5.36.2 production-code commit.

- Milestone: `V5.36.2 — exact runtime-source binding repair`
- Implementation-owner classification: `implemented` or `blocked`; final
  disposition remains with an independent reviewer
- Exact reviewed V5.36.1 base:
  `b2d35ff603cabdc05a12412cee2f32e550b584ac`
- Exact base tree: `225688307e35a6d8ebf20fc4ddc63bb56582346c`
- V5.36.1 contract commit:
  `6b7766e9b3529761a4edb5e952129c315f855284`
- V5.36.1 diagnostic implementation commit:
  `b9de6d53810a417317662703cc6c55817d1df9fd`

The reviewed V5.36 and V5.36.1 branches and worktrees are immutable. The two
V5.36.1 provisioning grants and attempts are terminal generated state. They
must not be copied, renewed, retried, consumed again, or treated as native
diagnostic evidence. No credential record is assumed to exist.

## Observed Defect

The provisioning wrapper changed its working directory to the requested
deployment root, then invoked bare
`python -m algotrader.execution.v536_credential_provisioning`. Because the
repository uses a `src` layout, Python resolved an older editable installation
from the reviewed V5.36 worktree instead of the V5.36.1 module in the requested
deployment. Both one-attempt grants therefore returned the old generic
`credential_writer_failed` classification.

The authorization commit/tree and Git provenance described the requested
working tree, but they were not bound to the imported module's path or bytes.
This allowed a clean, correctly hashed deployment to attest source that was
not executing. The V5.36.1 diagnostic classification path was never reached.

## Required Production Boundary

The production PowerShell wrapper must launch one repository-owned Python
entry point by absolute path in isolated Python mode. That entry point may add
only the exact deployment `src` directory ahead of ambient package locations,
must import the provisioning module from that directory, and must reject any
other resolved module path with a fixed sanitized classification.

Before authorization consumption, Windows identity lookup, no-echo prompting,
opaque material creation, native library loading, or Credential Manager access,
the executing provisioning module must:

1. resolve the deployment root without trusting the caller's working directory;
2. require its own `__file__` to equal the exact expected deployment path;
3. obtain clean Git commit, tree, and source-bundle provenance for that root;
4. require the source-bundle manifest to contain the provisioning module and
   the repository-owned launcher;
5. hash its executing source bytes and match the manifest digest; and
6. pass that same provenance object to the existing authorization commit/tree
   checks before material acquisition.

Missing, ambiguous, malformed, dirty, unreadable, outside-root, wrong-path, or
digest-mismatched runtime identity must fail closed. Public output may contain
only a fixed classification. It must not contain filesystem paths, exception
text, source contents, raw error codes, usernames, account identities,
credential references, or credential values.

## Preserved Credential And Process Boundary

Only non-secret launcher path, authorization-artifact path, and explicit write
gate may cross the PowerShell-to-Python process boundary. No credential value
may enter argv, environment variables, pipeline input, files, receipts, logs,
or exceptions. The launcher must not accept secret parameters or read stdin.

The V5.36.1 `WindowsCredWriteNativeBoundary`, fixed sanitized error mapping,
successful credential-record layout, target, flags, persistence, username,
record bytes, receipt, one-use material, and zeroization behavior remain
unchanged. This milestone must not infer or implement a native adapter fix.

## Required Credential-Free Proof

Default tests must never prompt, load a native credential DLL, or access
Credential Manager. They must prove:

1. a deliberately conflicting ambient/editable `algotrader` package is not
   imported by the repository-owned launcher;
2. the exact deployment provisioning module executes through the production
   PowerShell wrapper;
3. wrong module path, missing manifest binding, wrong source digest, dirty
   provenance, and provenance-loader exceptions fail before material, identity,
   writer, native, subprocess-child, network, scheduler, or broker effects;
4. runtime failure output is fixed and contains no path, exception, or secret
   sentinel;
5. wrapper and launcher work when the deployment path contains spaces and the
   caller uses a non-default working directory;
6. only non-secret configuration crosses the process boundary;
7. the launcher is included in source provenance and changes the bundle digest;
8. all V5.36.1 native-failure tests remain intact; and
9. existing dependency-direction, credential, network, broker-mutation,
   no-submit, provenance, identity, atomic-persistence, dispatcher, and task
   suites remain intact.

## Prohibited Effects

During implementation and review, do not:

- read, enumerate, create, replace, rename, or delete any credential;
- prompt for or access real credential/account values;
- reuse either terminal V5.36.1 grant;
- register, enable, start, disable, query, or delete a scheduled task;
- access a network, market-data service, broker, paper endpoint, or live endpoint;
- submit, cancel, replace, close, or liquidate an order;
- modify reviewed V5.36/V5.36.1 branches or worktrees; or
- weaken credential, dependency, network, broker, mutation, no-submit, source,
  or live-prohibition guards.

## Verification And Post-Review Gate

The implementation owner must run focused wrapper/runtime-source tests,
affected V5.35/V5.36/V5.36.1 safety suites, standalone dependency direction,
and `scripts\verify_offline.ps1 -Full` on the exact final clean commit. The
handoff records boolean-only preflight, exact commands, commits, trees, counts,
elapsed times, dirty-file ownership, external-effect status, residual risks,
and independent-review route.

Only after an independent reviewer passes the exact final V5.36.2 commit may
the operator authorize two fresh, non-reusable, one-hour provisioning grants
and one new attempt per family. Any result remains terminal for its grant. No
Task Scheduler, network, broker, paper, canary, or trading action follows from
this repair, and no implementation owner may merge or self-approve it.
