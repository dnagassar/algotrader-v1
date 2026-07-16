# ETF/SMA Daily Operator Runbook

This document describes the canonical offline daily operator loop for running ETF/SMA trend filter evaluations and validating generated artifacts.

## Canonical Daily Command

The canonical entrypoint for running the daily evaluation, validating the bundle integrity, and producing the final status check report is:

```powershell
python -m algotrader.cli etf-sma-daily-offline-check --as-of-date YYYY-MM-DD --bars-csv <PATH_TO_CSV> --reconciliation-state-path <PATH_TO_JSONL>
```

### Required Inputs

* `--as-of-date`: The target evaluation date in `YYYY-MM-DD` format (e.g., `2026-06-05`). If omitted, it will default to the latest bar's date.
* `--bars-csv`: The path to the daily price bars CSV file (e.g. `tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv`).
* `--reconciliation-state-path`: The path to the latest local broker/ledger reconciliation JSONL file (e.g. `tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl`).

## Expected Outputs

All runs generate a deterministic daily bundle folder under the output root `runs/daily/<as_of_date>/` containing:

1. `cycle.jsonl`: The core signal/posture evaluation payload.
2. `brief.jsonl` / `brief.txt`: Operator action brief.
3. `gate.jsonl`: Gate acceptance decision state.
4. `dashboard.txt`: Compact operator console view.
5. `bundle_manifest.jsonl`: File paths, hashes, and sizes list.
6. `bundle_status.jsonl` / `bundle_status.txt`: Daily bundle status validation results.
7. `offline_check.jsonl` / `offline_check.txt`: Final unified check report.

Additionally, the command updates the ascending index:
* `runs/daily/daily_run_index.jsonl`: Lexicographically sorted run registry containing manifest file hashes.

## Command Status Semantics

The `etf-sma-daily-offline-check` command exits with:
* `0` if the check state evaluates to **ACCEPTED**.
* `1` (or non-zero) if the check state evaluates to **BLOCKED**.

### Accepted vs. Blocked Meanings

* **ACCEPTED**:
  * Signal evaluation completed without pipeline error.
  * No validation findings (no schema mismatches, credential leaks, or corrupted file hashes).
  * No active blockers (no terminal/non-terminal open orders or unexpected position symbols).
* **BLOCKED**:
  * Active blockers detected (e.g., an open order is present on Alpaca, or non-terminal orders exist in the reconciliation log).
  * Integrity or safety validation failed (e.g., manifest hash mismatch, missing bundle files, or validation rule failures).

## Artifact Validation Command

Verify that the output bundle matches the strict schema definition:

```powershell
python -m algotrader.cli validate-artifacts --input-root runs/daily/<as_of_date> --output runs/validation/artifact_validation_report.jsonl
```

## Canonical Soak Runner Command

To sequentially run the daily loop checks across a historical date range and compile a unified soak rollup:

```powershell
python -m algotrader.cli etf-sma-daily-soak --start-date YYYY-MM-DD --end-date YYYY-MM-DD --bars-csv <PATH_TO_CSV> --reconciliation-state-path <PATH_TO_JSONL>
```

### Required Inputs

* `--start-date`: The beginning of the historical range in `YYYY-MM-DD` format.
* `--end-date`: The end of the historical range in `YYYY-MM-DD` format.
* `--bars-csv`: The path to the daily price bars CSV file.
* `--reconciliation-state-path`: The path to the ledger reconciliation JSONL file.
* `--output-root` (Optional): Directory for runs and rollups (defaults to `runs/daily`).

### Expected Outputs

The soak runner generates:
1. Individual daily folders `runs/daily/<date>/` for each attempted date in the range.
2. `runs/daily/soak_rollup.jsonl`: Exactly one compact aggregate summary JSON record.
3. `runs/daily/soak_rollup.txt`: An ASCII table detailing each day's status, posture, decision, and findings.

## Canonical Soak Brief and Regression Command

To compile an operator brief summarizing a multi-day soak run and optionally perform regression comparison against a baseline soak rollup:

```powershell
python -m algotrader.cli etf-sma-daily-soak-brief --soak-rollup-jsonl runs/daily_soak/soak_rollup.jsonl --daily-root runs/daily_soak --output-jsonl runs/daily_soak/soak_operator_brief.jsonl --output-text runs/daily_soak/soak_operator_brief.txt --baseline-rollup-jsonl <PATH_TO_BASELINE>
```

### Required Inputs

* `--soak-rollup-jsonl`: The path to the V3E soak rollup JSONL file to compile.
* `--daily-root`: The path to the root directory containing the individual daily folders.

### Optional Inputs

* `--output-jsonl` (Optional): The path to write the brief JSONL rollup record (defaults to `runs/daily_soak/soak_operator_brief.jsonl`).
* `--output-text` (Optional): The path to write the brief text report (defaults to `runs/daily_soak/soak_operator_brief.txt`).
* `--baseline-rollup-jsonl` (Optional): A path to a local baseline soak rollup JSONL to check for regressions.
* `--format` (Optional): CLI stdout output format (`text` or `json`, default `text`).

### Expected Outputs

The soak brief compiler generates:
1. `runs/daily_soak/soak_operator_brief.jsonl`: A single-line JSON summary record.
2. `runs/daily_soak/soak_operator_brief.txt`: A detailed operator-readable report outlining date buckets, posture distributions, active blockers, missing daily artifacts, absolute path leaks, and baseline comparison mismatches.

## Canonical Soak Release Gate Command

To compile a deterministic offline pass/fail release packet for the daily soak loop:

```powershell
python -m algotrader.cli etf-sma-daily-soak-release-gate --soak-brief-jsonl runs/daily_soak/soak_operator_brief.jsonl --artifact-validation-jsonl runs/validation/artifact_validation_report.jsonl --output-jsonl runs/daily_soak/soak_release_gate.jsonl --output-text runs/daily_soak/soak_release_gate.txt
```

### Required Inputs

* `--soak-brief-jsonl`: The path to the V3F daily soak operator brief JSONL file.
* `--artifact-validation-jsonl`: The path to the V3D artifact validation JSONL report.

### Optional Inputs

* `--output-jsonl` (Optional): The path to write the release gate JSONL packet (defaults to `runs/daily_soak/soak_release_gate.jsonl`).
* `--output-text` (Optional): The path to write the release gate text summary (defaults to `runs/daily_soak/soak_release_gate.txt`).
* `--format` (Optional): CLI stdout output format (`text` or `json`, default `text`).

### Expected Outputs

The release gate command compiles:
1. `runs/daily_soak/soak_release_gate.jsonl`: A single-line JSON release packet containing the pass/fail status and all verified metadata.
2. `runs/daily_soak/soak_release_gate.txt`: An operator-readable ASCII report outlining the acceptance gate status, findings breakdown, active release blockers, date range counts, and output paths.

### Release Gate Status Semantics

The command exits with:
* `0` if the release gate evaluates to **ACCEPTED**.
* `1` if the release gate evaluates to **BLOCKED**.
* `2` if an operational or input validation error occurs.

## Canonical Soak Golden Acceptance Command

To run the complete deterministic offline V3 daily soak acceptance loop end-to-end, validating all outputs and generating the final golden check acceptance packet:

```powershell
python -m algotrader.cli etf-sma-daily-soak-golden-check --start-date YYYY-MM-DD --end-date YYYY-MM-DD --bars-csv <PATH_TO_CSV> --reconciliation-state-path <PATH_TO_JSONL>
```

### Inputs and Options

* `--start-date` (Optional): The beginning of the historical range (default: `2025-06-01`).
* `--end-date` (Optional): The end of the historical range (default: `2025-06-10`).
* `--bars-csv` (Optional): Path to the daily price bars CSV file.
* `--reconciliation-state-path` (Optional): Path to the offline reconciliation state JSONL file.
* `--output-root` (Optional): Target directory for soak and rollup output files (default: `runs/daily_soak`).
* `--validation-output` (Optional): Path to validation report before release gate (default: `runs/validation/artifact_validation_report.jsonl`).
* `--post-release-validation-output` (Optional): Path to validation report after release gate (default: `runs/validation/artifact_validation_after_release_gate_report.jsonl`).
* `--output-jsonl` (Optional): Output path for the compact golden check JSONL summary (default: `runs/daily_soak/soak_golden_acceptance.jsonl`).
* `--output-text` (Optional): Output path for the detailed golden check ASCII text summary (default: `runs/daily_soak/soak_golden_acceptance.txt`).
* `--format` (Optional): Output format for CLI stdout (`text` or `json`, default: `text`).

### Expected Outputs

The golden check command produces:
1. `runs/daily_soak/soak_golden_acceptance.jsonl`: A single-line JSON record detailing the overall loops execution summary, blockers, paths, and status.
2. `runs/daily_soak/soak_golden_acceptance.txt`: An operator-readable summary showing date counts, findings counts, active blockers, path leak checks, and safety assertions.

### Golden Acceptance Status Semantics

The command exits with:
* `0` if the end-to-end loop finishes with **ACCEPTED** status.
* `1` if any blocking conditions are met (meaning it status is **BLOCKED**).
* `2` if an operational or input validation error occurs.

## Offline Daily Lab Acceptance Launcher

To run the complete daily lab acceptance sequence, which performs environment prechecks, runs local verification tests, executes the soak golden checks, confirms no generated run artifacts are tracked or staged in git, and produces a final operator acceptance summary:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_daily_lab_acceptance.ps1 -StartDate YYYY-MM-DD -EndDate YYYY-MM-DD -BarsCsv <PATH_TO_CSV> -ReconciliationStatePath <PATH_TO_JSONL>
```

### Inputs and Options

* `-StartDate` (Optional): The beginning of the historical range (default: `2025-06-01`).
* `-EndDate` (Optional): The end of the historical range (default: `2025-06-10`).
* `-BarsCsv` (Optional): Path to the daily price bars CSV file.
* `-ReconciliationStatePath` (Optional): Path to the offline reconciliation state JSONL file.
* `-OutputRoot` (Optional): Target directory for soak and rollup output files (default: `runs/daily_soak`).
* `-FullVerify` (Optional): Runs the complete exact-node bounded pytest suite inside `verify_offline.ps1` instead of targeted guard tests only.

### Acceptance Summary Output

Upon completion, the launcher prints a compact final summary:
* **Verifier Status**: Pass/Fail status of `verify_offline.ps1`.
* **Golden Acceptance Status**: Pass/Fail status of the golden check.
* **Release Gate Status**: Pass/Fail status of the daily soak release gate.
* **Pre/Post-Gate Validation Findings**: Counts of scan findings.
* **Output Root**: Relative path to the output directory.
* **Safety Authorization Booleans**: Confirms authorization gates remain safely locked (`False`).
* **Git Artifact Verification**: Confirms that no generated artifacts are tracked or staged.
* **Key Output Artifact Paths**: List of generated files relative and POSIX-style.

### Complete Offline Verification

Run the canonical full default collection with bounded deterministic sharding:

```powershell
.\scripts\verify_offline.ps1 -Full
```

The full verifier collects the default suite once, partitions every node ID
exactly once across four balanced argument files, recollects each shard to prove
there are no missing, duplicate, or extra tests, and then executes the shards
with isolated temporary state and per-shard timeouts. It fails on any collection
drift, timeout, nonzero pytest exit, missing JUnit result, or aggregate testcase
count mismatch. The summary includes shard wall times and the slowest files by
aggregate testcase seconds. It does not add skip, deselect, marker, network, or
credential overrides.

## Authoritative SPY EOD Market-Data Refresh

This isolated lane refreshes adjusted SPY daily bars from Tiingo without
constructing a broker client or authorizing any paper/live order operation.
Tiingo documents most EOD prices near 17:30 ET and corrections through 20:00 ET:
`https://www.tiingo.com/documentation/end-of-day`.

The scheduled boundary is 20:10 America/New_York. Confirm the Windows host uses
the Eastern time zone before registration:

```powershell
Get-TimeZone
```

Put only the real Tiingo token in the untracked local `.env`:

```text
TIINGO_API_KEY=<local secret>
```

The adapter can load only `TIINGO_API_KEY`. `APP_PROFILE=paper` and broker
variables may coexist, but they are not looked up or serialized. A live profile
is rejected.

Preview the exact request without loading the token or using the network:

```powershell
.\scripts\refresh_spy_adjusted_data.ps1 `
  -Provider tiingo `
  -OutputCsv .data\operator_inputs\spy_tiingo_adjusted_refresh_latest.csv `
  -CanonicalCsv runs\operator_input\m446_spy_daily_tiingo_adjusted_canonical.csv `
  -RunLog runs\paper_lab\m446_adjusted_spy_bars_refresh_manifest.jsonl `
  -Mode dry_run `
  -StartDate auto `
  -RevisionLookbackDays 10 `
  -Format json
```

The actual read-only fetch additionally requires the live market-data mode and
the explicit authorization switch:

```powershell
.\scripts\refresh_spy_adjusted_data.ps1 `
  -Provider tiingo `
  -OutputCsv .data\operator_inputs\spy_tiingo_adjusted_refresh_latest.csv `
  -CanonicalCsv runs\operator_input\m446_spy_daily_tiingo_adjusted_canonical.csv `
  -RunLog runs\paper_lab\m446_adjusted_spy_bars_refresh_manifest.jsonl `
  -SoakLedger runs\paper_lab\spy_adjusted_market_data_soak_ledger.jsonl `
  -SoakReport runs\paper_lab\spy_adjusted_market_data_soak_report.json `
  -SoakRequiredSessions 5 `
  -Mode live_market_data_fetch `
  -RawResponsePath runs\paper_lab\tiingo_spy_adjusted_raw_latest.json `
  -StartDate auto `
  -RevisionLookbackDays 10 `
  -DotenvPath .env `
  -LiveMarketDataFetchAuthorized `
  -Format json
```

Register the isolated task from the checked-in template only after reviewing
its absolute repository path:

```powershell
$TaskXml = Get-Content `
  .\docs\design\spy_eod_market_data_refresh_scheduled_task.xml -Raw
Register-ScheduledTask -TaskName "spy-eod-market-data-refresh" -Xml $TaskXml
```

The task uses `IgnoreNew`, `StartWhenAvailable`, network-required execution, a
fifteen-minute limit, and three fifteen-minute retries. It is not the
paper-autopilot supervisor.

Authoritative local artifacts:

- raw provider JSON: `runs/paper_lab/tiingo_spy_adjusted_raw_latest.json`
- normalized candidate: `.data/operator_inputs/spy_tiingo_adjusted_refresh_latest.csv`
- canonical adjusted bars:
  `runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv`
- one-record refresh manifest:
  `runs/paper_lab/m446_adjusted_spy_bars_refresh_manifest.jsonl`
- append-only secret-free refresh-attempt ledger:
  `runs/paper_lab/spy_adjusted_market_data_soak_ledger.jsonl`
- automatically regenerated readiness report:
  `runs/paper_lab/spy_adjusted_market_data_soak_report.json`

Success is `accepted_adjusted_spy_data_refresh`. Inspect `revision_outcome`,
`revised_dates`, row counts, `source_sha256`, `current_canonical_sha256`,
`normalized_output_sha256`, and `canonical_csv_sha256`. HTTP, scope, JSON, date,
or bar validation failures are blocked and preserve the previous canonical
file. This lane performs no broker read, broker mutation, paper submit, or live
operation.


The soak report counts distinct expected NYSE sessions, so same-session retries
cannot inflate readiness. A failed latest session resets the current streak
until a same-session retry succeeds. The state remains
`collecting_unattended_market_data_soak` and the evidence classification remains
`operational_data_provenance_capability` until five consecutive sessions qualify.
Only then does the report emit `accepted_unattended_market_data_soak` and
`unattended_authoritative_market_data_proven`. This is not strategy evidence.

## Read-Only Journal Cancellation-Planning Preview

### Exact Submit-Only Cancellation Seed

When no open paper order exists, the cancellation path has no eligible target.
Only after exact operator authorization for the fixed request may the
repository-owned seed boundary create one target:

```powershell
. .\scripts\dev\load_env.ps1 -Quiet
python -m algotrader.execution.paper_cancellation_seed `
  --paper-submit-authorized `
  --authorization-phrase "AUTHORIZE ONE SPY PAPER DAY LIMIT BUY QTY 1 LIMIT 1.00 FOR CANCELLATION SEED ONLY"
```

The request is not configurable: one SPY paper-only DAY limit buy, quantity 1,
limit price `$1.00`, and maximum paper exposure `$1.00`. The command requires
the exact paper endpoint, loaded paper credentials, and an expected paper
account identity. Before submission it confirms the account and SPY asset are
tradable, observes zero open orders, and rejects any prior use of the fixed
client-order ID. It durably reserves and fences the submit in
`runs/paper_autopilot/state/order_journal.sqlite3` before making at most one
broker call, then performs one exact-order read. Ambiguous, rejected, filled,
missing, or mismatched outcomes stop without retry.

This boundary has no cancellation, replacement, close, liquidation, or live
capability. A successful open seed records its client-order and broker-order
identities under `runs/paper_cancellation_seed/latest/seed_result.json`, but
does not authorize cancellation. The operator must separately authorize the
exact returned identity before the cancellation binding may run. Do not run
pytest or offline verification in the credentialed shell.

### Exact Operator-Authorized Paper Cancellation

Only after the operator authorizes one cancellation attempt for the exact
client-order ID, broker-order ID, and SPY symbol may the repository-owned
binding run:

```powershell
. .\scripts\dev\load_env.ps1 -Quiet
python -m algotrader.execution.paper_exact_cancellation `
  --target-client-order-id <EXACT_CLIENT_ORDER_ID> `
  --target-broker-order-id <EXACT_BROKER_ORDER_ID> `
  --target-symbol SPY `
  --paper-cancel-authorized `
  --authorization-phrase "AUTHORIZE ONE EXACT ALPACA PAPER CANCELLATION ATTEMPT NO RETRY"
```

The command requires the exact Alpaca paper endpoint, paper profile, loaded
paper credentials, and an expected account identity. It first verifies the
local journal identity and runtime controls, then performs one account read and
one exact broker-order read. Missing, terminal, non-cancelable, mismatched,
paused, stopped, stale, or wrong-account state stops before broker mutation.

For a valid fresh target, the command reuses the deterministic planning,
handoff, exact-authorization admission, and durable invocation pipeline. The
fixed `paper-autopilot-cancellation` lease, cancellation reservation, and
atomic pre-mutation journal claim must all succeed before the single SDK cancel
call is reachable. The command performs at most one exact post-cancel read,
persists the observed order and cancel-intent states, releases the lease in a
`finally` path, and never retries. It exposes no submit, replace, close,
liquidation, target-selection, or live capability. Its ignored result is
written to
`runs/paper_exact_cancellation/latest/cancellation_result.json`.

Do not run this command from a default verification shell, substitute another
target, or repeat it after an ambiguous result. Reconciliation after an
ambiguous response is read-only and non-retryable.

### Credential-Free Exact Reconciliation Readiness

Before opening a credentialed shell, validate every locally discoverable input
with the dedicated readiness command. Run it only from the normal offline,
credential-free shell and supply the exact values intended for the later
read-only command:

```powershell
python .\scripts\build_exact_paper_cancellation_reconciliation_readiness.py `
  --authorization-artifact <EXACT_EXISTING_AUTHORIZATION_JSON> `
  --journal-path <EXACT_LOCAL_ORDER_JOURNAL> `
  --cancel-intent-id <EXACT_CANCEL_INTENT_ID> `
  --client-order-id <EXACT_CLIENT_ORDER_ID> `
  --broker-order-id <EXACT_BROKER_ORDER_ID> `
  --expected-authorization-id <EXACT_AUTHORIZATION_ID> `
  --expected-paper-account-id <EXACT_EXPECTED_PAPER_ACCOUNT_ID> `
  --occurred-at <EXACT_ISO_8601_UTC_TIMESTAMP> `
  --allow-offline-readiness
```

The permission flag defaults to false and is checked before artifact or journal
access. Both paths must be local; network filesystem paths are rejected. The
command validates the canonical existing authorization, authorization ID,
validity window, all three target identities, expected-account presence, named
journal records, and reconciliation-ready cancel state. It reads no
environment configuration or runtime-control value, opens no broker client,
uses no network, writes no file or journal record, and has no injected callback
surface. Output is sanitized JSON on stdout.

A `ready` receipt means only that these offline inputs are internally
consistent for the later command. It does not verify the broker account, load
credentials, authorize network access, authorize a broker read, invoke the
operator binding, or authorize cancellation or any other mutation. A blocked
receipt must be corrected offline; do not bypass it in a credentialed shell.

### Exact Read-Only Cancellation Reconciliation

The dedicated reconciliation command is for one already-unresolved durable
cancel intent after the operator supplies a separate existing read-only
authorization artifact. The command cannot create that artifact, infer a
target from it, enumerate unresolved intents, or enter the general CLI. Both
permission flags default to false and are checked before the artifact,
environment, journal, or broker reader can be accessed.

Do not run this command merely because an unresolved cancel intent exists. An
actual paper-broker read is a new exact operation and requires operator
authorization for the named cancel-intent, client-order, broker-order, account,
authorization ID, journal, and bounded UTC occurrence time, plus explicit
credential loading and network access. After those exact facts and that
operation are authorized, the standalone form is:

```powershell
. .\scripts\dev\load_env.ps1 -Quiet
python .\scripts\run_exact_paper_cancellation_reconciliation.py `
  --authorization-artifact <EXACT_EXISTING_AUTHORIZATION_JSON> `
  --journal-path <EXACT_LOCAL_ORDER_JOURNAL> `
  --cancel-intent-id <EXACT_CANCEL_INTENT_ID> `
  --client-order-id <EXACT_CLIENT_ORDER_ID> `
  --broker-order-id <EXACT_BROKER_ORDER_ID> `
  --expected-authorization-id <EXACT_AUTHORIZATION_ID> `
  --expected-paper-account-id <EXACT_EXPECTED_PAPER_ACCOUNT_ID> `
  --occurred-at <EXACT_ISO_8601_UTC_TIMESTAMP> `
  --operator-binding-permitted `
  --network-access-permitted
```

The authorization JSON must be the exact canonical export of one pre-existing
`PaperCancellationObservationAuthorization`. Malformed, extra, duplicate,
forged, expired, noncanonical, or identity-mismatched evidence stops before a
reader. Paper profile, canonical paper endpoint, both canonical credential
variables, exact expected account, and the named local journal records must all
validate. The binding then performs at most one account read and one exact
order read, consumes the injected observation once, and either atomically
converges both local records or updates neither. It never retries and has no
submit, cancel, replace, close, liquidation, target-selection, polling, or live
capability. Output reports only configured-account and credential-presence
facts; it does not serialize account or credential values.

Default verification must exercise this command only with missing artifacts or
deterministic fake clients and a blocked socket. Never load credentials into a
pytest or offline-verification shell, and never treat the existence of this
command or an authorization artifact as permission for a broker read.

The paper-autopilot status command can build one local no-submit cancellation
planning artifact from an existing journal record. The preview is disabled by
default and requires the exact local client-order ID, broker-order ID, symbol,
reason, and an explicit UTC evaluation time:

```powershell
python -m algotrader.cli paper-autopilot-control status `
  --order-journal-path <LOCAL_ORDER_JOURNAL_PATH> `
  --cancellation-preview `
  --allow-offline-cancellation-planning `
  --cancellation-target-client-order-id <CLIENT_ORDER_ID> `
  --cancellation-target-broker-order-id <BROKER_ORDER_ID> `
  --cancellation-target-symbol SPY `
  --cancellation-reason <LOCAL_PLANNING_REASON> `
  --cancellation-as-of <ISO_8601_UTC_TIMESTAMP> `
  --format json
```

`--allow-offline-cancellation-planning` authorizes creation of this local
artifact only. It does not authorize broker access or cancellation. The output
must retain `no_submit=true`, `cancel_attempted=false`,
`broker_access_performed=false`, and `broker_mutation_performed=false`.
Missing, duplicate, stale, ambiguous, terminal, mismatched, paused, stopped, or
otherwise ineligible local state returns a blocked artifact. Do not treat a
planned artifact as an executable cancellation request.

To avoid copying local order identifiers while retaining fail-closed targeting,
status can instead select exactly one sufficiently old cancelable record for the
requested symbol. Auto-selection is also disabled by default and cannot be
combined with explicit target IDs:

```powershell
python -m algotrader.cli paper-autopilot-control status `
  --order-journal-path <LOCAL_ORDER_JOURNAL_PATH> `
  --cancellation-preview `
  --auto-select-cancellation-candidate `
  --allow-offline-cancellation-planning `
  --cancellation-target-symbol SPY `
  --cancellation-reason <LOCAL_PLANNING_REASON> `
  --cancellation-as-of <ISO_8601_UTC_TIMESTAMP> `
  --cancellation-candidate-minimum-open-age-seconds 900 `
  --format json
```

The threshold is measured from the journal record's creation time; preview
freshness is still measured from its latest observation time. Selection blocks
instead of ranking when more than one record qualifies, when broker identity is
duplicated, or when local state is incomplete, unknown, terminal-only, paused,
stopped, future-dated, or inconsistent. It performs no broker access, no
cancellation attempt, and no journal mutation.

## Default-Denied Durable Cancellation Handoff Preview

After a successful explicit or automatically selected cancellation plan,
status can optionally emit the exact primitive inputs that a future durable
cancellation admission boundary would need. This remains a local mapping
artifact and is disabled by default:

```powershell
python -m algotrader.cli paper-autopilot-control status `
  --order-journal-path <LOCAL_ORDER_JOURNAL_PATH> `
  --cancellation-preview `
  --auto-select-cancellation-candidate `
  --allow-offline-cancellation-planning `
  --cancellation-handoff-preview `
  --allow-offline-cancellation-handoff `
  --cancellation-admission-preview `
  --cancellation-target-symbol SPY `
  --cancellation-reason <LOCAL_PLANNING_REASON> `
  --cancellation-as-of <ISO_8601_UTC_TIMESTAMP> `
  --cancellation-candidate-minimum-open-age-seconds 900 `
  --format json
```

`--allow-offline-cancellation-handoff` permits artifact creation only. It is
not cancellation authorization and cannot enable a broker callback. Even a
prepared artifact must retain `cancel_allowed=false`,
`execution_authorized=false`, `broker_callback_present=false`,
`coordinator_invoked=false`, `cancel_attempted=false`,
`broker_access_performed=false`, `broker_mutation_performed=false`, and
`journal_mutation_performed=false`. Missing permission, a blocked or missing
plan, stale or terminal records, invalid timestamps, or any plan/record identity
or observation mismatch returns a typed blocked artifact with no durable
identity inputs.

`--cancellation-admission-preview` evaluates the next local boundary but
deliberately supplies no operator-authorization evidence. When planning and
handoff preparation succeed, its expected result is the typed
`authorization_missing` blocker with empty `identity` and `evidence` values.
There is no CLI argument, environment variable, file path, or status-control
field that can manufacture or load authorization. Do not interpret this preview
as a cancellation approval workflow.

The underlying pure admission contract accepts only a caller-supplied immutable
authorization object that is affirmative, unexpired, paper-mode, cancel-scoped,
and exactly bound to the handoff's source-plan, cancel-intent, client-order, and
broker-order identities. Even a successfully admitted in-memory result records
`execution_performed=false`, `broker_callback_present=false`,
`coordinator_invoked=false`, `lease_acquired=false`,
`cancel_intent_reserved=false`, `cancel_attempted=false`, and no broker or
journal mutation. Actual coordinator invocation remains a separate operator
gate for one exact cancellation.

The internal `paper_cancellation_invocation` bridge implements that gated
coordinator sequence. Its only Alpaca binding is the exact operator command
described above. An invocation caller must provide the exact admitted artifact
ID, an explicit UTC occurrence time before authorization expiry, a fresh
snapshot assertion, a bounded lease TTL, a separate affirmative invocation
permission, and injected cancel/observation callbacks. It then uses the fixed
`paper-autopilot-cancellation` lease, durable reservation, atomic pre-mutation
claim, observation persistence, and `finally`-based lease release. Offline
tests use local SQLite journals and fake callbacks only.

Do not load paper credentials or attempt cancellation without operator
authorization for the exact target order and mutation scope. A status admission
preview remains non-executable even when the internal bridge exists.

## Preregistered Crypto Tournament Procedure

The tournament runner is offline and accepts only a local canonical hourly CSV.
It has no network, credential, broker, submit, cancel, replace, close,
liquidation, paper-mode, or live-mode switch.

1. Verify the checked-in preregistration fingerprint is
   `1475d35634750a7f00832f0a540fbaac3e28e7ed82ac7dbd8ef2d60e08f09097`.
2. For an exactly authorized read-only refresh, load paper market-data settings
   only into the isolated refresh process. Never print or paste credential
   values.
3. Fetch the fixed `2025-07-15T00:00:00Z` through the inclusive final completed
   bar at `2026-07-14T23:00:00Z` (as-of `2026-07-15T00:00:00Z`) into
   `runs\crypto_strategy_tournament\v1\input\crypto_1h_1y.csv` using
   `scripts\refresh_multi_symbol_crypto_history.ps1`. Do not use the default
   operator-input path.
4. Inspect the refresh packet and require a real-history classification, all
   four symbols, `1Hour`, the exact fixed window, an output SHA-256 matching the
   CSV, no live endpoint, no broker mutation, and no credential exposure.
5. Clear paper profile and credentials from the process before any test or
   local research command.
6. Run:

```powershell
.\scripts\run_crypto_preregistered_tournament.ps1 `
  -InputPath "runs\crypto_strategy_tournament\v1\input\crypto_1h_1y.csv" `
  -RefreshPacketPath "runs\crypto_strategy_tournament\v1\refresh\refresh_packet.json" `
  -OutputRoot "runs\crypto_strategy_tournament\v1\latest" `
  -AsOfTimestamp "2026-07-15T00:00:00Z" `
  -Format text
```

7. Treat `no_candidate_qualified` as a terminal rejection for every candidate
   in this tournament version. Do not rescue-tune.
8. Treat `eligible_for_no_submit_shadow_evaluation` only as permission to open
   a separate shadow-evidence milestone. It is not paper mutation or capital
   authorization.

The detailed immutable contract is in
`docs/design/v5_22_crypto_preregistered_tournament.md`.

## Safety Declarations

> [!WARNING]
> This workflow runs in a strictly sandboxed, credential-free environment.
>
> * **NO Live Trading**: Order execution is preview-only; no live broker API calls are allowed.
> * **NO Paper order submission**: Ordering behavior remains mock/preview and does not perform active Alpaca mutations.
> * **NO Broker state modification**: The system does not mutate ledger accounts or close positions.
> * **NO Credential loading**: Environment keys (`ALPACA_API_KEY`, etc.) must remain unloaded.
> * **NO Network operations**: All internet/socket communication is strictly blocked during offline default tests.
> * **NO LLM in loop**: No artificial intelligence agent or vector-DB queries are performed in the hot path.

## Note on Legacy Commands

Legacy daily commands (e.g., `daily-operating-brief` or `paper-lab-daily-preview`) exist in the CLI but are **not** the canonical path for V3 operator runs. Do not delete them as they are preserved for historical regression testing, but use `etf-sma-daily-offline-check` for all current operational checks.

## Crypto Tournament V2 Forward-OOS Procedure

Tournament v1 is closed. Do not remove ADA from v1, retry its terminal gate, or
reuse its OOS result. V2 uses only BTCUSD, ETHUSD, and SOLUSD with fingerprint
2ed9489543d8d21ab00d9f2f4000927b8012decf39882cb721cb2d1ce0b9376b.

Initialize once from the existing guarded local history while the normal
process is credential-free:

    .\scripts\run_crypto_tournament_v2_forward_oos.ps1 -Mode initialize -AsOf 2026-07-15T20:00:00Z

Initialization is offline. It freezes 2026-01-16T00:00:00Z through
2026-07-14T23:00:00Z, applies only the preregistered isolated prior-close gap
fill, and emits no candidate metrics.

Status and readiness are also offline:

    .\scripts\run_crypto_tournament_v2_forward_oos.ps1 -Mode status -AsOf <CURRENT_UTC_TIMESTAMP>

    .\scripts\run_crypto_tournament_v2_forward_oos.ps1 -Mode readiness -AsOf <CURRENT_UTC_TIMESTAMP>

Readiness reports the earliest missing hour and the latest completed hour. It
reads only boolean preflight state and never prints credential values.

When the operator has explicitly authorized one read-only market-data
operation, load paper market-data credentials and the explicit paper base URL
only into that isolated process. Then run:

    .\scripts\run_crypto_tournament_v2_forward_oos.ps1 -Mode market_data_fetch -AsOf <CURRENT_COMPLETED_UTC_HOUR> -MarketDataFetchAuthorized -AllowNetwork

The wrapper calculates the exact inclusive start/end window. Do not hand-edit
it, extend the endpoint, add symbols, or reuse a receipt from another output.
The call is HTTPS GET market data only. It does not read an account and cannot
submit, cancel, replace, close, liquidate, or mutate broker state.
The adapter must report data_intake_only=true and
strategy_evidence_evaluation_performed=false. It validates OHLCV and provenance
only; it must not run a strategy battery or emit interim candidate metrics.


After the isolated fetch, clear APP_PROFILE and all Alpaca credential variables
before running tests or other local commands. Repeated identical receipts are
safe and idempotent. Any conflicting historical rewrite is a hard integrity
failure and must not be forced.

Before 2026-08-13T00:00:00Z, accept only completeness and provenance packets;
candidate metrics must remain empty. At or after the terminal timestamp, a
complete admitted window evaluates all nine frozen candidates once. A
terminal input-quality failure or no_candidate_qualified result closes v2
without retuning or extending the window. The terminal packet is hash-bound;
later status checks replay it and reject new deltas or rescoring. A selected
result authorizes only a separately preregistered no-submit single-winner
forward-shadow milestone.

## Tournament V2 Forward-Shadow Readiness

The downstream single-winner shadow contract is already preregistered. Check
it only from a normal credential-free shell:

    .\scripts\run_crypto_tournament_v2_forward_shadow.ps1 -AsOf <CURRENT_UTC_TIMESTAMP>

Before tournament v2 closes, the expected classification is
`waiting_for_tournament_terminal`. That is not an error and creates no shadow
window or candidate activation. Continue the exact receipt-bound v2 refresh
cadence.

After a sealed terminal winner exists, the command verifies the terminal
packet hash, evidence fingerprint, state fingerprint, selection scope, and
exact frozen candidate identity. It then derives a 168-hour untouched future
window and one activation fingerprint. Do not hand-edit the winner, start,
end, fingerprint, or contract. A terminal input-quality failure or
`no_candidate_qualified` result closes without a shadow candidate.

This readiness command performs no network or market-data fetch and must not
be run in the credential-loaded refresh shell. A ready activation is still
no-submit and grants no paper, broker, capital, or live authority.

## Tournament V2 Forward-Shadow Operating Cycle

The V5.24 command above remains the offline activation check. The shortest
normal operating command for the implemented V5.25 state is:

```powershell
.\scripts\run_crypto_tournament_v2_forward_shadow_cycle.ps1 `
  -Mode status `
  -AsOf <CURRENT_UTC_TIMESTAMP>
```

Run `status` from a normal credential-free development shell. Before a winner,
it reports a dormant classification and creates no state. Once tournament v2
seals one eligible winner, initialize explicitly with:

```powershell
.\scripts\run_crypto_tournament_v2_forward_shadow_cycle.ps1 `
  -Mode initialize `
  -AsOf <CURRENT_UTC_TIMESTAMP>
```

Initialization freezes the selected candidate, activation, source terminal
identity, 169 causal context bars, and the exact 168-hour future window. It uses
no network. The guarded fetch mode also performs this initialization
idempotently when needed, so an extra initialize command is not required for
the fast path.

To see whether a fetch is actionable without attempting one:

```powershell
.\scripts\run_crypto_tournament_v2_forward_shadow_cycle.ps1 `
  -Mode readiness `
  -AsOf <CURRENT_UTC_TIMESTAMP>
```

Waiting, dormant, complete, and terminal classifications do not require loaded
credentials and never invoke the adapter. Only
`ready_for_explicit_read_only_market_data_fetch` is actionable. At that point,
use the isolated paper market-data shell with `APP_PROFILE=paper`, paper
market-data credentials, and the explicit paper base URL already loaded, then
run exactly:

```powershell
.\scripts\run_crypto_tournament_v2_forward_shadow_cycle.ps1 `
  -Mode market_data_fetch `
  -AsOf <CURRENT_UTC_TIMESTAMP> `
  -MarketDataFetchAuthorized `
  -AllowNetwork
```

Do not supply a symbol or time range. The command derives exactly one selected
symbol and the inclusive completed-hour range from frozen state. It uses the
existing Alpaca crypto-bars market-data GET adapter only. It cannot read an
account or submit, cancel, replace, close, liquidate, or mutate paper/live
state. Receipt mismatch, adapter failure, or state-validation failure closes
the operation without accruing state.

Only one `market_data_fetch` cycle may run for this shadow root at a time. The
command holds one local operating lock from status through receipt validation
and state accrual; an overlapping invocation fails closed before a second
adapter call. Let the already-running command finish, then rerun status. Do not
delete either lock file or hand-edit the recovery journal.

Close the isolated credential-loaded shell after the refresh. Return to a new
credential-free shell before development or tests. Checkpoints at hours 24 and
72 are completeness receipts only. At hour 168, accept either sealed shadow
evidence for a bounded-paper-probe review or the terminal input-quality gate;
neither is paper mutation, capital allocation, or live authorization.

## Tournament V2 Bounded Paper-Probe Review

Run the V5.26 review only from a normal credential-free development shell:

```powershell
.\scripts\run_crypto_tournament_v2_bounded_paper_probe_review.ps1
```

The default uses the current UTC clock. For a deterministic historical replay,
pass an explicit ISO-8601 `-AsOf` value; never use a placeholder literally.

Do not load the paper shell for this command. It rejects `APP_PROFILE=paper` or
`live`, all Alpaca credential aliases, network-test flags, and live endpoint
indicators before Python starts. It has no network, broker-read, symbol, submit,
cancel, replace, close, liquidate, paper-mutation, or live option.

Before V5.25 seals a terminal outcome, the expected result is
`waiting_for_v5_25_terminal_evidence`. After valid strategy evidence, missing
or stale venue, bounded-policy, lifecycle/independent-flat, or durable-kill
evidence produces `blocked_by_operational_evidence`. Do not hand-create or edit
capability JSON. Each capability must come from its canonical producer, resolve
every preregistered upstream source by bytes, match the exact selected symbol,
and share one coherent bundle fingerprint.

The default output root is
`runs\crypto_strategy_tournament\v2\bounded_paper_probe_review\latest`.
Follow `latest_manifest.json` to its immutable generation. That generation
contains the preregistration, JSON and Markdown review, generation manifest,
and snapshots of terminal evidence plus only capability, producer, and upstream
inputs actually evaluated after the strategy gates pass. File existence alone
does not establish readiness. The persisted packet validator is structural
only. Rerun this wrapper with its default current UTC clock to replay the local
sources. A future authorization consumer must additionally validate the pointer,
manifest, hashes, and exact replayed fingerprint before any mutation review can
rely on a generation; that consumer does not yet exist.

The strongest possible result is `eligible_for_operator_review_only`. It still
has approval state `not_authorized`, expires at the earliest capability expiry,
and carries no paper or live authority. A future bounded paper mutation would
require a separate exact operator authorization. A later live test additionally
requires completed paper evidence, a separate live-readiness review, explicit
capital allocation, live credential/endpoint controls, and exact operator
authorization.
