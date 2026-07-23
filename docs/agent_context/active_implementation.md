# Active Implementation Checkpoint

## Classification

- Milestone: `V5.36.2 — exact runtime-source binding repair`.
- Classification: `implemented`.
- `operator_action_required: true`, deferred until independent review passes;
  only then may the operator authorize fresh one-hour diagnostic grants.
- Final disposition belongs to a different agent. This is not credential,
  canary, paper, activation, or operational-readiness evidence.

## Ownership And Repository State

- Sole implementation writer: Codex `/root`.
- Worktree:
  `C:\Users\danie\Desktop\algo_trader_worktrees\codex-v5.36.2-exact-runtime-source-binding`.
- Branch: `codex/v5.36.2-exact-runtime-source-binding`.
- Exact reviewed V5.36.1 base:
  `b2d35ff603cabdc05a12412cee2f32e550b584ac`.
- Base tree: `225688307e35a6d8ebf20fc4ddc63bb56582346c`.
- Standalone pre-implementation contract commit:
  `84a3910b449f0fd4510eb8027ba4cb0c2d0aa922`.
- Runtime-source implementation commit:
  `3d39df4e6007320e73216aba0671dc0330988d4d`.
- Implementation tree: `f654a338c6f2183582592acbb523739190ed293c`.
- The implementation worktree was clean for commit-bound verification. This
  handoff is the sole intended dirty file and must be committed before the
  exact-final clean-commit verification and review-only push.
- Reviewed V5.36/V5.36.1 worktrees and branches, the primary checkout, all
  preserved V5.34 refs/worktrees, candidate commits, and staged Antigravity
  work remain unchanged.

## Credential And External-Effect State

Boolean-only preflight was repeated before implementation and verification:

- `APP_PROFILE`: `false` (`paper`: `false`)
- `ALPACA_API_KEY`: `false`
- `ALPACA_API_KEY_ID`: `false`
- `ALPACA_API_SECRET_KEY`: `false`
- `ALPACA_SECRET_KEY`: `false`
- `APCA_API_KEY_ID`: `false`
- `APCA_API_SECRET_KEY`: `false`
- expected-paper-account aliases: `false`

No credential was read, enumerated, created, replaced, renamed, deleted, or
provisioned during implementation or review. No real prompt was opened. No
Task Scheduler read/mutation, market-data or broker request, paper mutation,
order action, canary operation, or live operation occurred.

The two prior V5.36.1 grants and attempts are terminal and cannot be reused or
treated as native diagnostic evidence. The runtime mismatch means no V5.36.1
native classification was obtained, and no credential record is assumed to
exist.

## Implemented Boundary

1. The PowerShell wrapper no longer invokes ambient `python -m`. It resolves
   one repository-owned launcher by absolute path and invokes Python with `-I`
   isolated mode and `-B` no-bytecode mode. Only the launcher path, absolute
   non-secret authorization path, and explicit write gate cross the process
   boundary.
2. The launcher derives its deployment root from its own resolved path, places
   that root's exact `src` directory first, imports the provisioning module,
   requires the imported `__file__` to equal the exact expected deployment
   path, and passes the launcher-derived root into the provisioner. Any import
   or path failure produces one fixed sanitized classification.
3. Before authorization loading, Windows identity lookup, prompting, material
   creation, native DLL loading, or Credential Manager access, the provisioner
   obtains clean Git commit/tree/source-bundle provenance and binds its exact
   module and launcher paths and normalized SHA-256 digests to the manifest.
4. The authorization's commit/tree are compared with that same bound
   provenance before Windows identity access. Existing checks repeat inside
   the provisioner before material acquisition.
5. Missing launcher/module bindings, dirty source, malformed provenance,
   wrong path, digest mismatch, and loader exceptions fail closed with fixed
   classifications containing no paths, exception text, raw errors, or secret
   sentinels.
6. Python bytecode creation is disabled so verification cannot dirty the
   deployment before Git provenance is evaluated.
7. Credential-free tests create a clean temporary deployment under a path with
   spaces, inject a conflicting ambient `algotrader` package, invoke the exact
   production PowerShell wrapper from an unrelated directory, and prove the
   deployment module executes before stopping at a missing non-secret artifact.
8. The launcher and V5.36.2 contract are bound into the production source
   provenance bundle. V5.36.1 native classifications, successful record
   structure, zeroization, redaction, and all existing safety controls remain
   unchanged.

## Changed Files

- `docs/agent_context/active_implementation.md`
- `docs/design/v5_36_2_exact_runtime_source_binding_repair_contract.md`
- `docs/design/v5_36_credential_provisioning_and_windows_task_boundary.md`
- `scripts/launch_v536_credential_provisioning.py`
- `scripts/provision_v536_windows_credential.ps1`
- `src/algotrader/execution/crypto_read_only_paper_observation_adapter.py`
- `src/algotrader/execution/v536_credential_provisioning.py`
- `tests/unit/test_v536_credential_provisioning.py`
- `tests/unit/test_v536_scripts.py`
- `tests/unit/test_v5_33_2_source_provenance.py`

## Verification Evidence

All completed results were offline and credential-free. Commit-bound evidence
ran on clean implementation commit
`3d39df4e6007320e73216aba0671dc0330988d4d` and tree
`f654a338c6f2183582592acbb523739190ed293c`.

### Focused Runtime-Source Suite

Command:

```powershell
python -m pytest tests/unit/test_v536_credential_provisioning.py tests/unit/test_v536_scripts.py tests/unit/test_v5_33_2_source_provenance.py -q
```

- Exit code: `0`
- Result: `56 passed`
- Pytest elapsed: `28.39s`
- Command wall time: `31.8s`

An earlier focused run stopped safely with `51 passed`, `1 failed` because the
temporary fixture generated untracked bytecode before provenance validation.
The production launcher was strengthened with `-B` and
`sys.dont_write_bytecode`; the exact rerun above passed.

### Affected V5.35/V5.36/V5.36.1/V5.36.2 Safety Suites

Command:

```powershell
python -m pytest tests/unit/test_v536_credential_provisioning.py tests/unit/test_v536_canary_authorization.py tests/unit/test_v536_windows_task.py tests/unit/test_v536_windows_host_canary.py tests/unit/test_v536_scripts.py tests/unit/test_v535_unattended_readonly.py tests/unit/test_v535_task_boundary.py tests/unit/test_v535_secure_dispatcher.py tests/unit/test_v535_secure_credential_provider.py tests/unit/test_v5_33_2_source_provenance.py tests/unit/test_default_pytest_network_guard.py tests/unit/test_broker_mutation_surface_invariant.py tests/unit/test_crypto_no_submit_operating_cycle.py -q
```

- Exit code: `0`
- Result: `239 passed`
- Pytest elapsed: `96.55s`
- Command wall time: `102.9s`

### Standalone Dependency Direction

Command: `python -m pytest tests/unit/test_dependency_direction.py -q`

- Exit code: `0`
- Result: `34 passed`
- Pytest elapsed: `10.18s`
- Command wall time: `13.4s`

### Full Offline Verifier

Command: `.\scripts\verify_offline.ps1 -Full`

- Exit code: `0`
- Guard phase: `99 passed` in `86.56s`
- Canonical collection: `9,785` nodes across `488` files
- Aggregate: `9,780 passed`, `5 skipped`, `0 failures`, `0 errors`
- Collection equivalence: `PASS`
- Execution equivalence: `PASS`
- Shard wall times: `1012.39s`, `978.14s`, `876.51s`, `936.40s`
- Command wall time: `1,306.7s`
- Overall result: `PASS`

The verifier's initial and final hygiene phases showed an empty status and
staging area, clean whitespace, no source paths changed from `HEAD`, no
untracked `src`/`tests` paths, and no tracked generated run paths. The handoff
commit still requires one exact-final standalone full verifier and explicit
Git hygiene checks before push.

## Residual Risks

- Real Windows Credential Manager behavior remains untested in V5.36.2. The
  prior attempts executed older code and cannot identify a native category.
- Credential-record state is unknown and was not queried because no credential
  read authority exists. A future grant remains terminal regardless of result.
- The launcher trusts the reviewed Python executable located on `PATH` but
  isolates package resolution and binds imported source bytes. Compromise of
  the interpreter, operating system, administrator account, or Git executable
  remains outside this repository boundary.
- No Task Scheduler, HTTPS, broker, paper, or canary behavior was exercised.
- Full verification remains slow due unrelated established suites; no coverage
  was removed or weakened in this repair.

## Exact Next Review And Operator Route

1. Commit this handoff, rerun the full verifier and required Git hygiene checks
   on the exact final clean commit, and push the unchanged branch for
   independent review only. Do not merge or self-approve.
2. The independent reviewer verifies contract chronology, isolated absolute
   launch, wrong-editable resistance, exact module/digest binding, pre-identity
   ordering, fixed redaction, source provenance, and final verification.
3. Only after that review passes may the operator authorize two new,
   non-reusable, one-hour grants and exactly one new attempt per credential
   family. The old grants remain terminal.
4. Report only sanitized classifications or non-secret receipts. Any native
   adapter correction requires another frozen contract and review. No task,
   network, broker, paper, canary, or trading action follows automatically.
