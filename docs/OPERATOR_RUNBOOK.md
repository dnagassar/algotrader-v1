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

### Per-Worktree Interpreter Binding

Before the first `-Full` run in a worktree (and after switching worktrees), bind
the system Python's editable `algotrader` install to the current worktree:

```powershell
.\scripts\bind_worktree_python.ps1
```

The full suite includes subprocess wrappers (the V5.30 bounded paper-probe
lifecycle and the independent-flat operator) that resolve a trusted, signed,
*registered* Python interpreter and strip `PYTHONPATH` by design. They import
`algotrader` from the system interpreter's site-packages, so a virtual
environment cannot satisfy them. There is one registered interpreter, and its
editable install points at whichever worktree it was last bound to; if that
worktree is deleted it dangles, and those wrappers fail with
`ModuleNotFoundError: No module named 'algotrader'` even though every in-process
test still passes (pytest's `pythonpath=["src"]` shadows the broken install).
`bind_worktree_python.ps1` repoints that install at the current worktree. It is
package management only: no credentials, broker, paper, trading-network, or Task
Scheduler action. Use `-WithDependencies` for a first-time machine setup.

`verify_offline.ps1 -Full` runs this binding check automatically and auto-binds
the current worktree by default before executing the suite, so the normal flow
is just `.\scripts\verify_offline.ps1 -Full`. Pass `-NoAutoBind` to require an
explicit prior bind and fail fast instead of auto-binding.

### Complete Offline Verification

Run the canonical full default collection with bounded deterministic sharding:

```powershell
.\scripts\verify_offline.ps1 -Full
```

The full verifier collects the default suite once, partitions every node ID
exactly once across one balanced argument file per shard, recollects each shard
to prove there are no missing, duplicate, or extra tests, and then executes the
shards in parallel with isolated temporary state and per-shard timeouts. The
shard count auto-scales to the detected logical CPU count (capped at 16); pin it
with `-Full -Shards <n>`. It fails on any collection drift, timeout, nonzero
pytest exit, missing JUnit result, or aggregate testcase count mismatch. The
summary includes shard wall times and the slowest files by aggregate testcase
seconds. It does not add skip, deselect, marker, network, or credential
overrides.

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

### NexusTrade monthly universe historical acquisition

The exact twelve-symbol research universe can be planned without reading the
credential or using the network:

```powershell
.\scripts\refresh_nexustrade_monthly_adjusted_data.ps1 `
  -Mode dry_run `
  -DotenvPath "C:\path\to\existing\untracked\.env"
```

With explicit read-only market-data authorization, use the same wrapper:

```powershell
.\scripts\refresh_nexustrade_monthly_adjusted_data.ps1 `
  -Mode live_market_data_fetch `
  -DotenvPath "C:\path\to\existing\untracked\.env" `
  -LiveMarketDataFetchAuthorized
```

The wrapper never copies the dotenv file and loads only `TIINGO_API_KEY`
inside each bounded child fetch. It performs one exact-host GET for each of
`AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST, SPY`.
The default fixed interval is `2019-01-02` through `2025-03-28`.

On success it writes per-symbol canonical files under `runs/operator_input`,
the combined
`runs/operator_input/multi_etf_adjusted_daily_canonical.csv`, and the
secret-free coverage/provenance manifest under
`runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json`.
The manifest requires every symbol to match Tiingo SPY's observed EOD dates,
records input and combined SHA-256 hashes, and confirms coverage for both a
365-calendar-day and 365-observed-session warm-up. It deliberately leaves the
candidate's authentic warm-up clock, bar mode, and slippage unresolved unless
candidate-specific source material explicitly states them.

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

The default uses the current UTC clock. For deterministic reevaluation at an
explicit clock, pass an ISO-8601 `-AsOf` value; never use a placeholder
literally. This is not the pinned immutable-publication replay described below.

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
does not establish readiness. The V5.26 persisted packet validator is
structural only. V5.27 adds the separate source-bound production and pinned
replay path described below. A review generation remains non-authorizing even
when replay succeeds.

The strongest possible result is `eligible_for_operator_review_only`. It still
has approval state `not_authorized`, expires at the earliest capability expiry,
and carries no paper or live authority. A future bounded paper mutation would
require a separate exact operator authorization. A later live test additionally
requires completed paper evidence, a separate live-readiness review, explicit
capital allocation, live credential/endpoint controls, and exact operator
authorization.

## Tournament V2 Capability Production And Pinned Replay

Run the complete V5.27 offline capability pipeline from a normal
credential-free development shell, never from the paper shell:

```powershell
.\scripts\run_crypto_tournament_v2_capability_pipeline.ps1 `
  -InputFamily legacy
```

The wrapper rejects paper/live profiles, all supported Alpaca credential
aliases, network-test switches, and live endpoint indicators before Python
starts. It performs no network request, broker/account read, broker mutation,
submit, cancel, replace, close, liquidation, paper mutation, capital action, or
live action. It refreshes the source-bound safety certification and publishes
from existing local venue, lifecycle, and flat evidence; it does not fetch or
create those observations. Candidate-specific evidence is resolved only after
V5.25 names the exact accepted winner.

Until that terminal winner exists, the expected production classification is
`candidate_deferred_pending_terminal_winner` with blocker
`v5_25_terminal_winner_not_available`. This is a successful fail-closed result,
not an instruction to hand-create capability data or change the OOS calendar.

If capability production eventually emits an eligible bundle, run the V5.26
review command above. Then replay that exact immutable review publication by
pinning its 64-character publication fingerprint:

```powershell
.\scripts\replay_crypto_tournament_v2_bounded_paper_probe_review.ps1 `
  -ExpectedPublicationFingerprint <64-character-fingerprint>
```

The replay command resolves the pinned outer review generation directly; it
does not trust the outer mutable-latest pointer. It validates that generation's
manifest and artifact hashes, the embedded pinned capability pointer, captured
raw sources, canonical JSON, trusted current UTC, and exact recomputed
fingerprints. An unpinned mutable-latest lookup is not sufficient for a later
authorization review. Replay success still grants no mutation, capital,
broker, paper, or live authority.

A fully validated eligible generation retains exact legacy lifecycle source
bytes for pinned replay. Those ignored local `runs\` artifacts may contain
noncredential broker/account/order identifiers even though normalized outputs
use a hashed account binding. Do not attach, publish, or copy a generation as a
routine report. Blocked and malformed inputs are not snapshotted.

Legacy-family lifecycle eligibility is intentionally strict. V5.8 must show zero fill and no
residual state; V5.9 must be the exact canonical packet/manifest output with its
unchanged operator phrase and false authority fields; and V5.10 must show
positive, cross-bound entry and exit fills. A fresh independent flat read must
occur at or after the broker-reported V5.10 exit-order `filled_at`. A flat read
that is merely later than the V5.10 run timestamp is invalid. The sealed review
re-derives this ordering and selected-symbol venue semantics rather than
trusting normalized claims.

V5.28 provides exact target-scoped visibility for BTCUSD, ETHUSD, and SOLUSD.
The target is validated case-sensitively before Python or SDK setup, becomes the
sole supervisor preference, and never falls back to another observed symbol.

A fresh real paper read remains an exact operator gate. Only after authorization
for that specific read, use the paper shell and the frozen target, for example:

```powershell
.\scripts\run_crypto_universe_refresh.ps1 `
  -Mode paper_read_only `
  -TargetSymbol SOLUSD `
  -PaperReadOnlyAuthorized
```

Do not run that command from a credential-free development shell or without the
exact read authorization. Untargeted visibility remains available for general
observation, but it cannot satisfy V5.27 winner-scoped venue eligibility. The
legacy lifecycle chain is BTCUSD-only, and the historical BTC chain no longer
retains the exact V5.6 bytes cited downstream. The next evidence milestone is
winner-specific lifecycle and independent-flat evidence after the terminal
candidate is known; do not weaken those gates.

## Target-Scoped Independent Flat Collection

After the exact winner-specific lifecycle has a confirmed filled exit, collect
the independent flat observation immediately from the isolated paper shell:

```powershell
.\scripts\run_crypto_bounded_probe_independent_flat_operator.ps1 `
  -TargetSymbol <BTCUSD|ETHUSD|SOLUSD> `
  -LifecyclePath <exact-lifecycle-result-path> `
  -IndependentFlatReadAuthorized `
  -AllowNetwork
```

The command validates the symbol and lifecycle before client construction. It
reads the paper account, every position, and every open order; it cannot mutate
the broker. Success requires exact expected-account matching, an active and
unblocked account, zero account-wide positions, zero account-wide open orders,
and an observation no earlier than the lifecycle exit order's broker-reported
filled_at. There is no caller clock or account-ID argument: expected account is
environment-only and observation time is taken from a trusted read-completion
clock. Target lifecycle input must be regular, non-reparse, at most 1 MiB,
strict UTF-8, duplicate-free canonical JSON, and pass the full V5.30 success
validator. Explicit false account-block flags are mandatory, and an open-order
result at the 100-order bound is treated as potentially truncated and blocks.

The receipt and manifest are written under
runs/crypto_strategy_tournament/v2/bounded_paper_probe_capabilities. Raw account
identifiers are not persisted. A failed newer observation supersedes any prior
mutable-latest flat receipt, so rerun capability production only after the
current command emits independent_flat_receipt_emitted.

Do not run this before a filled-exit lifecycle exists, from a credential-free
development shell, against a live endpoint, or as authority for any submit,
cancel, replace, close, liquidation, capital, or live action.

## Exact Winner Lifecycle Planning And Paper Execution

Run planning only from a normal credential-free, network-free development
shell after the tournament and V5.25 shadow have genuinely sealed an accepted
winner and the selected-symbol venue evidence is fresh:

```powershell
.\scripts\build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan.ps1
```

The planner derives the current UTC time, terminal evidence, expected account
binding, target venue binding, safety binding, and runtime source bundle. It
accepts no caller account or clock argument. Exit 0 means only
`ready_for_exact_operation_authorization`; exit 2 means dormant or blocked. Its
`authorization_request.txt` is a non-authorizing request artifact and must
never be renamed, copied, or used as a grant.

For an exact paper operation, the operator creates a separate strict-UTF-8
grant file under `%LOCALAPPDATA%\algo_trader\operator_grants`. The wrapper does
not create that directory and rejects repository files, links/reparse points,
planner request basenames, empty files, and files above 4096 bytes. From the
isolated paper shell, run:

```powershell
.\scripts\run_crypto_tournament_v2_bounded_paper_probe_lifecycle.ps1 `
  -PaperMutationAuthorized `
  -AllowNetwork `
  -Plan runs\crypto_strategy_tournament\v2\bounded_paper_probe_lifecycle\latest\lifecycle_plan.json `
  -GrantedAuthorizationPath <operator-owned-exact-grant-path>
```

The grant text is sent only over stdin. The fixed envelope is one USD 10
crypto market/GTC entry, one exact filled-quantity market/GTC exit, one entry
attempt, one exit attempt, one cancel attempt total, a 15-minute entry window,
and zero replace/close/liquidate operations. Exit 0 is reserved for
`filled_exit_confirmed`. Exit 2 is nonterminal or blocked: follow the persisted
receipt's `next_action` and never blind-retry. If an entry remains open, reuse
the exact same plan, grant, journal, safety state, and deterministic IDs after
expiry so only that order can be observed or canceled.

## Preferred Target Closeout

After the exact lifecycle quartet records a confirmed filled exit, run the
preferred closeout from the isolated paper shell:

```powershell
.\scripts\run_crypto_tournament_v2_bounded_paper_probe_closeout.ps1 `
  -TargetSymbol <BTCUSD|ETHUSD|SOLUSD> `
  -IndependentFlatReadAuthorized `
  -AllowNetwork
```

The closeout requires terminal evidence, plan, lifecycle result, and manifest.
It performs the read-only independent-flat collection first, then removes every
profile, credential, account, endpoint, network-test, and Python-startup
variable before running target-family capability production, sealed review,
and pinned replay. It propagates the first nonzero child exit, derives clocks
and the review publication fingerprint internally, and cannot plan or mutate.
Use `-InputFamily target` only with the complete target evidence family;
partial, mixed, extra, or legacy fallback inputs are rejected.

Review and replay exit 0 only for their eligible/no-blocker outcomes. Waiting,
blocked, malformed, stale, or nonexact evidence exits 2 and does not authorize
paper or live activity.

As of `2026-07-18T00:00:00Z`, the real V2 state has only 48 of 672 OOS hours per
symbol through frontier `2026-07-17T23:00:00Z`; it has no metrics, qualified
candidate, or winner, and the fixed endpoint remains
`2026-08-13T00:00:00Z`. The V5.25 shadow therefore still waits, and no real
V5.30 lifecycle quartet or V5.29 flat trio exists. Continue receipt-bound OOS
accrual without early scoring, then complete the accepted 168-hour V5.25 shadow
before venue refresh, planning, exact grant, paper lifecycle, and closeout.

## Deterministic One-Shot Tournament-V2 OOS Scheduler

V5.35 replaces the unattended production action with
`scripts/run_v535_unattended_readonly.ps1`. The older scheduler wrapper remains
available for credential-free preview/status/recovery only; its real dispatcher
now fails closed without an injected secure provider and reference. The V5.35
wrapper rejects inherited credential/profile aliases and passes only non-secret
Windows Credential Manager references.

The canonical XML template is disabled at task and trigger levels and disallows
start-on-demand. V5.35 verification does not provision credentials, register
the template, enable it, or run it. Those are separate operator gates.

The one-shot scheduler calculates eligible closed crypto hours, claims jobs atomically using SQLite transaction fencing, dispatches the existing accrual command, and records durable audit receipts. It is entirely offline by default, never polls or sleeps, and enforces strict security gates.

### Usage Modes

* **Preview (Default)**: Runs the scheduler in offline preview mode without using credentials or network. It prints a deterministic mock receipt:
  ```powershell
  .\scripts\run_crypto_tournament_v2_oos_scheduler.ps1 -Mode preview
  ```
* **Legacy Run Once**: This older command has no complete V5.35 credential boundary and now fails closed. Do not use it for V5.35:
  ```powershell
  .\scripts\run_crypto_tournament_v2_oos_scheduler.ps1 -Mode run_once -SchedulerEnabled -MarketDataReadAuthorized -AllowNetwork
  ```
* **Status**: Displays the current status of the scheduler and lists the last 10 recorded jobs:
  ```powershell
  .\scripts\run_crypto_tournament_v2_oos_scheduler.ps1 -Mode status
  ```
* **Recover Stale**: Scans the database and marks any running jobs that have exceeded the 15-minute lease limit as FAILED:
  ```powershell
  .\scripts\run_crypto_tournament_v2_oos_scheduler.ps1 -Mode recover_stale
  ```
* **Reset Failed**: Resets a failed job to pending state using explicit operator authorization switches:
  ```powershell
  .\scripts\run_crypto_tournament_v2_oos_scheduler.ps1 -Mode reset_failed -JobId <FAILED_JOB_ID> -ResetAuthorized
  ```

#### Stale Job Recovery and Failure Reset Policy

*   **No Automatic Retry**: Automatic retries are strictly prohibited to prevent cascading network errors, database corruption, or rate-limit violations during transient failures.
*   **Identifying Failed Windows**: If a job fails, the scheduler's accepted frontier will not advance. To identify failed windows, query the status command:
    ```powershell
    .\scripts\run_crypto_tournament_v2_oos_scheduler.ps1 -Mode status
    ```
    The status output table lists the recorded jobs, their IDs, windows, and current status.
*   **Failed Window Reset Command**: To make a failed window retryable, execute the reset command with the exact job ID and the explicit authorization switch:
    ```powershell
    .\scripts\run_crypto_tournament_v2_oos_scheduler.ps1 -Mode reset_failed -JobId <FAILED_JOB_ID> -ResetAuthorized
    ```
*   **Executing the Rerun**: No unattended rerun is authorized by V5.35. Leave a failed window blocked for separately scoped operator review:
    ```powershell
    # No V5.35 rerun command is authorized by this milestone.
    ```
*   **Avoiding Skipped Intervals**: Since the scheduler computes the eligible window starting immediately after the accepted frontier, a blocked/failed job blocks subsequent hours from being processed in that lane. Once reset and rerun successfully, the accepted frontier advances, ensuring that no intervals are skipped or processed out of order.

#### Timing Semantics and Hour Bounds

*   **Bar Timestamps**: Hourly bar timestamps represent the **opening time** of the bar, not its completion or publication time. For example, a bar covering the interval `20:00:00Z` to `21:00:00Z` is identified by the timestamp `20:00:00Z`.
*   **Closing Boundary**: An hourly bar is not closed and cannot be fetched until the end of its hour (e.g., `21:00:00Z` for the `20:00:00Z` bar).
*   **Trigger and Grace Period Offset**: The Windows scheduled task triggers 5 minutes after every UTC hour boundary (e.g., at `HH:05`). The 5-minute offset represents the publication grace period. Thus, a scheduler tick firing at `21:05:00Z` evaluates the eligibility of the prior hour's bar-open timestamp (`20:00:00Z` or `21:05:00Z - 1 hour - 5 minutes` floored).
*   **Forming Bar Protection**: The scheduler strictly filters out any currently forming bar. At tick time `HH:MM`, the bar for hour `HH:00` is currently forming and will never be requested, queued, or dispatched.
*   **Dispatcher Status**: The real command dispatcher remains **disabled** in normal configuration and is only enabled dynamically at runtime with explicit authorization switches.
*   **Task Registration Status**: The Windows scheduled task template is provided for operator review and remains **unregistered** by default.

### Windows Scheduled Task Template

A disabled Windows Task Scheduler XML template is available at `docs/design/crypto_tournament_v2_oos_scheduler_task.xml`. It describes a trigger 5 minutes after every UTC hour boundary, uses least privileges, prevents overlapping executions (`MultipleInstancesPolicy = IgnoreNew`), and has a 15-minute execution limit. It is review evidence only in V5.35.

Only preview the resolved XML during V5.35:
*   **Preview XML Template (Default)**:
    ```powershell
    .\scripts\register_crypto_tournament_v2_oos_scheduler_task.ps1
    ```

Do not use the helper's registration or unregistration switches under V5.35;
task mutation remains outside the milestone authorization.

No real credentials, live endpoints, or trading actions are permitted or stored in the task configuration.

## V5.36 Independent-Review And One-Canary Route

V5.36 adds a generated, one-time Windows task around the V5.35 production
read-only dispatcher. It does not use the recurring V5.35 review template and
never calls `Start-ScheduledTask`. The task is installed disabled, attested,
armed for exactly one UTC trigger, and disarmed after its first attempt. Final
commissioning requires a later credential-free terminal attestation.

The implementation milestone performs none of those host operations. The
authorization template containing `<EXACT_CLOSED_WINDOW>`,
`<NON_SECRET_REFERENCE>`, `<VERIFIED_V5_36_COMMIT>`, or `<EXACT_UTC_TIME>` is
not executable. First obtain independent review of the exact clean V5.36
commit. Then create one strict, non-secret
`v5_36_scheduled_canary_authorization_v1` artifact outside generated output,
using the exact field contract in
`docs/design/v5_36_credential_provisioning_and_windows_task_boundary.md`.
Never put credential values or a raw account identity in that artifact or in
chat. V5.36.5 explicitly supports an operator-owned authorization file outside
the deployment root. The file must be an absolute, existing, non-symlink
regular file. The repository-owned wrapper and task working directory remain
strictly contained within the exact deployment root.

V5.36.5a also coordinates immutable canary evidence writes with the structural
secret scan so an active repository-owned atomic write cannot be mistaken for
a residual temporary artifact. The scan still blocks on every temporary file
that exists while it owns the evidence boundary; operators must not delete,
rename, or retry around such a result.

From a normal credential-free shell owned by the exact task principal, preview
the resolved task definition:

```powershell
.\scripts\run_v536_windows_host_canary.ps1 `
  -Mode preview `
  -AuthorizationArtifact <ABSOLUTE_RESOLVED_CANARY_AUTHORIZATION_PATH>
```

If preview blocks, stop. Do not edit around the validator. If both exact vault
records already exist for the same Windows principal, proceed to disabled
installation only under the independently reviewed authorization:

```powershell
.\scripts\run_v536_windows_host_canary.ps1 `
  -Mode install-disabled `
  -AuthorizationArtifact <ABSOLUTE_RESOLVED_CANARY_AUTHORIZATION_PATH> `
  -TaskMutationAuthorized

.\scripts\run_v536_windows_host_canary.ps1 `
  -Mode attest-disabled `
  -AuthorizationArtifact <ABSOLUTE_RESOLVED_CANARY_AUTHORIZATION_PATH>
```

Review the disabled attestation before arming. Arm no earlier than 15 minutes
before the exact scheduled start and before that start:

```powershell
.\scripts\run_v536_windows_host_canary.ps1 `
  -Mode arm-exact-window `
  -AuthorizationArtifact <ABSOLUTE_RESOLVED_CANARY_AUTHORIZATION_PATH> `
  -TaskMutationAuthorized `
  -CredentialReadAuthorized
```

Do not manually start the task and do not invoke `-Mode execute` from the
operator console. Task Scheduler owns the single trigger. The registered
action supplies only the absolute non-secret authorization path and the three
required switches. It resolves credentials inside the production boundary,
performs at most the exact market-data GET and paper account/position/order/
asset reads, then attempts disarm regardless of result.

If emergency disarm is needed before or after the trigger, this credential-free
operation constructs neither a vault provider nor a broker client:

```powershell
.\scripts\run_v536_windows_host_canary.ps1 `
  -Mode disarm `
  -AuthorizationArtifact <ABSOLUTE_RESOLVED_CANARY_AUTHORIZATION_PATH> `
  -TaskMutationAuthorized
```

After the task has exited, run terminal attestation from a credential-free
shell:

```powershell
.\scripts\run_v536_windows_host_canary.ps1 `
  -Mode post-run-attest `
  -AuthorizationArtifact <ABSOLUTE_RESOLVED_CANARY_AUTHORIZATION_PATH>
```

Only `scheduled_read_only_canary_commissioning_complete` records a successful
one-attempt commissioning packet. Any `blocked_*` result is terminal for that
authorization: do not retry, reset, extend the deadline, or schedule another
window without a new milestone and new exact authorization.

Credential writes are not included in the canary read authority. If either
vault record is absent, stop and obtain a separate, one-family, at-most-one-hour
`v5_36_windows_credential_provisioning_authorization_v1` grant. Only then may
the exact principal use an interactive non-echoing masked console:

```powershell
.\scripts\provision_v536_windows_credential.ps1 `
  -AuthorizationArtifact <ABSOLUTE_RESOLVED_PROVISIONING_AUTHORIZATION_PATH> `
  -ProvisionAuthorized
```

Run that command once per separately authorized family. Never redirect input,
record the console, load credential aliases, or pass secrets as arguments.
Provisioning does not authorize task mutation, network access, broker reads,
or canary execution. The V5.36.3 prompt shows exactly one `*` while the
current field is non-empty, regardless of field length. Backspace removes the
marker only when the field becomes empty. The marker confirms input without
echoing credential characters or length.

V5.36.4 may additionally return
`credential_writer_native_setup_failed`,
`credential_writer_native_invocation_failed`, or
`credential_writer_unknown_native_failure`. These are fixed diagnostic
classifications only. They do not prove credential-record state and do not
authorize inspection, retry, remediation, Task Scheduler work, network access,
broker access, or canary execution. Preserve the grant as terminal and route
any identified adapter defect through a new frozen repair contract and
independent review.

V5.36.4a isolated the temporary native buffer-view lifetime defect before
mandatory zeroization. Its first release mechanism was rejected by synthetic
proof before a production commit. This changes no operator command or
authority. Earlier credential-record state remains unknown, and fresh grants
remain prohibited until independent review.

V5.36.4b avoids creating the exported native buffer view entirely by binding
the original mutable record through CPython's direct bytearray address API.
The record is still overwritten and cleared immediately, with no copy or
operator-procedure change.

## V5.32 End-to-End Supervised Crypto Readiness Trial

Run the complete 24-cycle deterministic proof from a normal credential-free
shell:

```powershell
.\scripts\run_crypto_supervised_readiness_trial.ps1
```

The command runs the same hourly sequence twice, validates restart-safe state,
executes the eight required fail-closed scenarios, and writes a readiness packet
under `runs\crypto_supervised_readiness_trial\latest`. A successful default run
reports `v5_32_trial_classification=accepted` and readiness rung `R1`.

Validate the outer packet and manifest hashes without rerunning the trial:

```powershell
.\scripts\run_crypto_supervised_readiness_trial.ps1 -ValidateOnly
```

The default command rejects paper/live profiles, loaded credentials, and
network-test flags. It performs no network or broker read. Credential values
are never printed.

If an exact read-only Alpaca paper shell is already available and this specific
observation is authorized, run:

```powershell
.\scripts\run_crypto_supervised_readiness_trial.ps1 `
  -BrokerObservedReadiness `
  -AllowAlpacaPaperRead
```

Both switches are required. The wrapper must positively identify paper profile,
credential presence, and the exact paper endpoint and must reject any live
indicator. This lane is read-only and no-submit; the script has no paper
mutation, submit, cancel, replace, close, liquidation, or live switch. Without
inherited credentials, retain the default
`blocked_credentials_unavailable` classification and do not expose secrets.

## V5.37 Cross-Lane Autonomy Supervisor

Run the supervisor from a normal credential-free development shell to get one
whole-system readout across every autonomy lane. It reads only local evidence
artifacts, never loads credentials or the network, and never mutates anything.

```powershell
.\scripts\run_autonomy_supervisor.ps1 `
  -RunId supervisor-<yyyymmdd> `
  -AsOf <CURRENT_UTC_TIMESTAMP> `
  -Format text
```

The wrapper refuses to run if `APP_PROFILE=paper`/`live` or any Alpaca
credential/network-test variable is loaded; this command must never see
secrets. `-AsOf` is required and is the only time source (no wall clock is read),
so the report is deterministic. Provide it as an ISO-8601 UTC timestamp.

For a machine-readable record, add `-Format json` and `-RunLog
runs\autonomy_supervisor\latest\report.jsonl` to write exactly one JSONL record.

The command reports, per lane, a normalized state in
`absent`/`waiting`/`nominal`/`stale`/`attention_required`/`unknown`/`blocked`,
the surfaced blockers, and one offline next action. The whole-system
`system_status` is `blocked` if any lane is blocked, `attention_required` if any
lane is unknown, attention, or *actionably* stale, `waiting` if any lane is
waiting, `nominal` if at least one lane is healthy, and `no_lane_evidence` when
nothing has run yet.

`no_lane_evidence` fails closed by default: the report carries
`evidence_required=true` and the command exits `1`, so a wrong or empty
`-LanesRoot` cannot read as healthy to an unattended caller. Do not suppress
this result in unattended automation. Pass `-AllowEmptyLab` only when an
all-absent lane set is intentional (a deliberately empty bootstrap lab); the
exception is recorded on the report as `allow_empty_lab=true`,
`evidence_required=false`, and the command exits `0` for that case. It must not
be used to make an unknown lane root appear healthy. Exit code is `0` for
nominal/waiting, `0` for no_lane_evidence only with `-AllowEmptyLab` (otherwise
`1`), `1` for attention/blocked, and `2` on input error, so it is schedulable.

When `evidence_required=true` the report also carries
`system_attention_required=true` and the aggregate blocker
`system_no_lane_evidence`. Before V5.42a those two fields read as though nothing
needed attention and nothing blocked, even while the exit code correctly said
`1`. If you have automation or notes that read the record's rollup booleans
rather than the exit code, this is the field pair to trust now. A declared empty
lab (`-AllowEmptyLab`) keeps both quiet, as before. `main`'s V5.41b
(`docs/design/v5_41b_standalone_supervisor_empty_lab_contract.md`) reached this
identical `evidence_required`/`system_attention_required`/
`system_no_lane_evidence` fix independently, which corroborates it as a defect
repair rather than a matter of taste.

Staleness splits in two. A lane whose `stale_requires_operator_action` is true
(today: `spy_offline_daily_cycle` and `spy_market_data_soak`) has no offline
command that could refresh it, so when it goes stale the system reports `waiting`
rather than `attention_required` — the lane still shows `stale`, its age, and
appears in `stale_lanes`, but the autonomous loop correctly reports it has
nothing to run and hands you the exact remediation it needs. Only a stale lane that an
allowlisted offline command *could* advance escalates to `attention_required`.

In a clean checkout every lane reads `absent` because its `runs/` evidence is
generated and gitignored, so the first run exits `1` by design; run the
individual lane commands first to seed evidence. To point a lane at an exact artifact instead of its default path, pass
`-Lane "lane_id=path"` (repeatable), for example:

```powershell
.\scripts\run_autonomy_supervisor.ps1 `
  -RunId supervisor-<yyyymmdd> `
  -AsOf <CURRENT_UTC_TIMESTAMP> `
  -Lane "crypto_bounded_paper_probe_review=runs\crypto_strategy_tournament\v2\bounded_paper_probe_review\latest\review.json" `
  -Format text
```

Known lane ids: `spy_market_data_soak`, `spy_offline_daily_cycle`,
`crypto_supervised_readiness_trial`, `crypto_forward_shadow_cycle`,
`crypto_bounded_paper_probe_review`, `crypto_capability_production`. A
`recommended_next_action` is always an offline, read-only, or operator-review
follow-up; it never authorizes or names a broker mutation.

The recommendation names the highest-severity lane that has evidence, so a lane
that is merely `absent` is never recommended while another lane has evidence. On
an all-absent lane root, `recommended_next_action_lane` is empty and the action
is `all_lanes_absent_run_lane_commands_to_seed_evidence`: seed the lanes you
intend to supervise rather than reading it as one lane's instruction. The
detailed contracts are in
`docs/design/v5_37_offline_cross_lane_autonomy_supervisor.md` and
`docs/design/v5_37a_all_absent_aggregate_recommendation_contract.md`.

## V5.38 Offline Autonomy Next-Action Planner

The supervisor tells you *what state* each lane is in; the planner tells you
*what to do next*. Run it from the same credential-free shell to turn the
supervisor's abstract recommendations into a concrete, safety-classified plan.

```powershell
.\scripts\run_autonomy_next_plan.ps1 `
  -RunId plan-<yyyymmdd> `
  -AsOf <CURRENT_UTC_TIMESTAMP> `
  -Format text
```

Like the supervisor, the wrapper refuses to run under a loaded profile or any
Alpaca credential/network-test variable, `-AsOf` is the only time source, and it
reads only local evidence. Add `-Format json` and `-RunLog
runs\autonomy_next_plan\latest\plan.jsonl` for a machine-readable record, and
`-Lane "lane_id=path"` (repeatable) to point a lane at an exact artifact.

For each lane the plan reports an execution class and, when applicable, the exact
offline command to run:

- `noop` — lane nominal or healthily waiting; nothing to run.
- `offline_operator_input` — an offline command exists but needs operator-supplied
  inputs (listed under `required_operator_inputs`). Today: the SPY offline daily
  cycle seed `etf-sma-offline-daily-cycle-run` (needs `--validated-at` and
  `--daily-bars-csv`).
- `auto_offline` — a fully-defaulted offline command exists (today:
  `etf-sma-offline-daily-cycle-rerun-m446`, which needs the refreshed M446 CSV
  present). Only unattended-execution authority remains.
- `operator_gated` — no offline path; the `gate` names why
  (`network_market_data_fetch`, `broker_observation`, `operator_review`,
  `task_scheduler_health`, `no_offline_command_available`).

The whole-system `plan_class` is `offline_action_available`,
`operator_authority_required`, or `all_nominal_or_waiting`; `next_offline_action`
names the single highest-leverage offline-runnable action. Exit code is `0` when
nothing is pending, `1` when an action is pending, and `2` on input error — a
pending-action signal distinct from the supervisor's severity signal.

Important gate: the planner **plans** commands but never runs them. In a clean
checkout it may identify offline work or operator-input lanes, but execution is
a separate step through the gated executor. Unattended offline execution must
remain within the explicit task scope and the current `AGENTS.md` safety
boundaries. The detailed contract is in
`docs/design/v5_38_offline_autonomy_next_action_planner.md`.

## V5.39 Gated Offline Autonomy Executor

The executor is the one authorized step that *acts* on the plan — running only
the offline-runnable, allowlisted subset. It is dry-run by default; you must pass
`-Apply` to actually execute.

```powershell
# Dry run: show what would run, execute nothing.
.\scripts\run_autonomy_apply_plan.ps1 -RunId apply-<yyyymmdd> -AsOf <UTC> -Format text

# Apply: actually run the eligible allowlisted offline commands.
.\scripts\run_autonomy_apply_plan.ps1 -RunId apply-<yyyymmdd> -AsOf <UTC> -Apply `
  -RunLog runs\autonomy_apply_plan\latest\ledger.jsonl -Format json

# Bind the two SPY inputs and apply an absent/stale daily-cycle action.
.\scripts\run_autonomy_apply_plan.ps1 -RunId apply-spy-<yyyymmdd> -AsOf <UTC> `
  -ValidatedAt <UTC> -DailyBarsCsv <LOCAL_ADJUSTED_SPY_CSV> -Apply `
  -RunLog runs\autonomy_apply_plan\latest\ledger.jsonl -Format json
```

The wrapper and the executor both refuse to run under `APP_PROFILE=paper`/`live`
or any Alpaca credential/network-test variable (reporting the variable name only,
never its value), and each executed command runs with a child environment that
strips every credential/profile variable. Fully-defaulted crypto readiness
replays are fixed in `AUTONOMY_EXECUTOR_ALLOWLIST`. SPY daily-cycle seed and
stale-refresh actions use a separate exact operator-input registry: both
`-ValidatedAt` and an existing local `-DailyBarsCsv` must be supplied together,
argv is constructed without a shell, and the M441–M444 outputs are pinned under
`runs\paper_lab`, including the supervised
`m444_offline_daily_cycle_run.jsonl`. Without both inputs the SPY action remains
skipped as `requires_operator_input`. The ledger records whether inputs were
provided, which actions were bound, and every eligible, skipped, and executed
action with exit codes and false broker/network/live safety booleans.

Exit code: `2` on input error or a preflight-refused `-Apply`; `1` on a failed
execution or a dry run with eligible work pending; `0` otherwise.

The pinned `etf-sma-offline-daily-cycle-rerun-m446` command remains manually
runnable historical reproduction only; it writes the M447 manifest and is not
an autonomy action. Use the paired-input path above for either
`run_offline_daily_cycle_chain_to_seed_evidence` or
`operator_refresh_offline_daily_cycle_inputs`. The historical V5.39 contract is
in `docs/design/v5_39_gated_offline_autonomy_executor.md`; V5.52 adds the bounded
operator-input binding described here.

## V5.42 Autonomy Self-Refresh Cycle

The self-refresh cycle runs the whole loop in one command: observe (supervisor)
→ decide (planner) → act (executor) → re-observe (supervisor), and reports
whether the system converged. It is dry-run by default; pass `-Apply` to actually
execute the eligible allowlisted offline refresh actions.

```powershell
# Dry run: preview the whole cycle, execute nothing.
.\scripts\run_autonomy_self_refresh_cycle.ps1 -RunId cycle-<yyyymmdd> -AsOf <UTC> -Format text

# Explicit bootstrap exception: accept an intentionally empty lab.
.\scripts\run_autonomy_self_refresh_cycle.ps1 -RunId empty-<yyyymmdd> -AsOf <UTC> `
  -LanesRoot <empty-lab-root> -AllowEmptyLab -Format json

# Apply: run the eligible offline refresh actions and re-observe.
.\scripts\run_autonomy_self_refresh_cycle.ps1 -RunId cycle-<yyyymmdd> -AsOf <UTC> -Apply `
  -RunLog runs\autonomy_self_refresh_cycle\latest\cycle.jsonl -Format json

# One-command SPY absent/stale -> accepted re-observation.
.\scripts\run_autonomy_self_refresh_cycle.ps1 -RunId cycle-spy-<yyyymmdd> `
  -AsOf <UTC> -ValidatedAt <UTC> -DailyBarsCsv <LOCAL_ADJUSTED_SPY_CSV> -Apply `
  -RunLog runs\autonomy_self_refresh_cycle\latest\cycle.jsonl -Format json
```

`cycle_outcome` is one of `evidence_required`, `dry_run_preview`,
`noop_no_action`, `refreshed`, `still_pending`, or `execution_failed`.
`converged` is true when the re-observed system status is `nominal` or
`waiting`. `no_lane_evidence` fails closed by default with
`evidence_required=true`, `converged=false`, and exit `1`. Use
`-AllowEmptyLab` only when an all-absent lane set is intentional; the exception
is recorded as `allow_empty_lab=true`. Exit code is `2` on input error, `1` on
execution failure or any non-converged cycle, and `0` otherwise. The same
credential/profile refusal and safety guarantees as the executor apply. The
detailed contract is in
`docs/design/v5_42_offline_autonomy_self_refresh_cycle.md`.

`refreshed` versus `still_pending` uses both whole-system severity and successful
lane-level transitions. `refreshed_lanes` names executed lanes that changed to
`nominal` or `waiting`; this means a successful SPY absent/stale → nominal
transition is visible even if an unrelated lane keeps the aggregate system at
`waiting`. V5.42a's fail-closed system ordering remains intact: losing all lane
evidence never reads as refreshed, and unrecognized statuses are refused.

What to expect today: an absent crypto readiness lane can run the import-pure
replay automatically under `-Apply`. An absent or stale SPY daily-cycle lane can
run only when the paired inputs are supplied; the child must accept the CSV and
produce an accepted canonical M444 manifest before re-observation can list the
lane in `refreshed_lanes`. Missing, partial, nonexistent, noncanonical, blocked,
or failed bindings never claim a refresh. The other network, scheduler, broker
observation, and operator-review lanes remain gated.

A wrong or empty `-LanesRoot` now reports `no_lane_evidence` with
`cycle_outcome: evidence_required`, `converged: false`, and exit `1`. Do not
suppress this result in unattended automation. `-AllowEmptyLab` is the explicit,
auditable exception for a deliberately empty bootstrap lab; it must not be used
to make an unknown lane root appear healthy.

## V5.40 Live-Capital Interlock Boundary Verification

The live-capital interlock is the runtime structural guard enforcing the paper-only repository execution policy. Before initiating paper-trading or broker-touching tasks, operators and autonomous callers run the boundary check to verify profile, endpoint, and live-signal status.

```powershell
# Human-readable operator verification
python -m algotrader.cli paper-boundary-check

# JSON payload output for automated tooling
python -m algotrader.cli paper-boundary-check --format json
```

The command checks:
1. `APP_PROFILE` must strictly equal `paper`.
2. The broker endpoint base URL must contain `paper` and classify as a paper endpoint.
3. No live enablement variables (`ALLOW_LIVE_TRADING`, etc.) or live host URLs (`api.alpaca.markets`) exist in the environment.

Exit codes:
- `0` — Paper boundary is satisfied (`paper_boundary_ok: true`).
- `1` — Paper boundary refused / live signal detected (`paper_boundary_ok: false`).

Detailed contract: `docs/design/v5_40_live_capital_interlock_contract.md`.

Secure-provider child note: the scheduler intentionally strips profile and
credential environment variables and passes the exact paper profile/endpoints as
non-secret arguments. The history adapter preserves any ambient key instead of
overriding it, refuses live profile/endpoint/enablement signals before opening
the credential lease, and performs the complete interlock again inside the lease
callback immediately before read-only HTTP. A refusal must leave both provider
open count and HTTP call count at zero. This path grants no broker mutation or
live-capital authority.

## V5.53 Integrated SPY Refresh to M444

Use the integrated command when an explicitly authorized read-only Tiingo
refresh should immediately feed the supervised offline SPY daily cycle:

```powershell
# Preview only: validates the paper interlock and session; no credential or network access.
python -m algotrader.execution.autonomy_spy_refresh_cycle `
  --as-of <ISO8601_UTC> --format json

# Authorized apply from a minimal credential-bearing process.
.\scripts\run_spy_integrated_refresh_cycle.ps1
```

The apply path requires the canonical `.env` Tiingo token and a passing
paper-only interlock in the wrapper process. Use the repository's non-echoing
credential provider/helper; never copy credential values into commands,
artifacts, reports, or handoffs. The wrapper captures UTC once. It performs at
most one exact-host Tiingo GET per invocation, while the network ledger permits
at most four reserved attempts for one NYSE session. Provider transport limits
are 20 seconds, 8 MiB, and 20,000 rows.

Exit `0` means the network session was accepted/already qualified and the
credential-free offline cycle converged. Inspect `observable_outcome`,
`network_refresh`, `offline_self_refresh`, and `spy_daily_cycle_refreshed`.
`observable_outcome=m444_refreshed_nominal` is the strong end-to-end result:
the canonical adjusted CSV was bound to the offline action, M444 was accepted,
and the SPY lane refreshed to nominal. Exit `1` is a preview, adapter rejection,
offline failure, or non-converged cycle; exit `2` is a fail-closed refusal.

Canonical evidence:

- `runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv`
- `runs/autonomy_network_executor/ledger.jsonl`
- `runs/paper_lab/m446_adjusted_spy_bars_refresh_manifest.jsonl`
- `runs/paper_lab/spy_adjusted_market_data_soak_report.json`
- `runs/paper_lab/m444_offline_daily_cycle_run.jsonl`

The offline child is invoked with an empty environment mapping plus its
internally pinned `PYTHONPATH`; it must report no network, credential, broker,
paper-submit, mutation, or live action. Do not run default tests from the
credential-bearing process.

## V5.54 Paper-Only SPY Decision-Time Shadow

Run the capture during an active NYSE session. The default advisory execution
window is the next session open:

```powershell
# Preview: calendar, paper interlock, canonical-history freshness, and paths only.
python -m algotrader.execution.spy_decision_time_shadow `
  --mode capture `
  --as-of <ISO8601_UTC> `
  --execution-window next_session_open

# Authorized capture: one bounded SPY/IEX snapshot GET through the secure lease.
.\scripts\run_spy_decision_time_shadow.ps1
```

The wrapper uses the non-secret credential reference
`wincred:algotrader/v5.35/alpaca-market-data/production`. Do not put credential
values in the command or environment. Capture refuses outside the active NYSE
session, if canonical adjusted history does not end on the previous completed
session, on a stale/future/out-of-session latest trade, or when the paper/live
interlock detects a live signal. Transport limits are one exact-host GET per
invocation, 10 seconds, and 256 KiB.

Exit `0` with `state=provisional_decision_recorded` is the strong capture
result. Inspect `decision`, `posture`, `latest_trade_at`, `data_age_seconds`,
`planned_execution_at`, `sma50`, and `sma200`. Repeating the command for that
session returns `provisional_decision_already_recorded` without credential or
network access. The output is advisory only: `execution_intent_created`,
`execution_plan_created`, broker access, broker mutation, paper submit, and live
authorization must all remain false.

The next successful integrated V5.53 run reconciles automatically after the
authoritative Tiingo bar reaches M444. Manual credential-free reconciliation is
also available:

```powershell
python -m algotrader.execution.spy_decision_time_shadow `
  --mode reconcile `
  --session-id <YYYY-MM-DD> `
  --as-of <ISO8601_UTC>
```

`classification=matched` means the provisional and authoritative target
decisions agree; `diverged` means they differ. Before the canonical CSV contains
that session, the state is `pending_authoritative_adjusted_bar` and no receipt
is written. Evidence is stored only in generated state:

- `runs/paper_lab/spy_decision_time_shadow/<YYYY-MM-DD>/provisional.json`
- `runs/paper_lab/spy_decision_time_shadow/<YYYY-MM-DD>/reconciliation.json`

## V5.55 Secure Unattended SPY Paper Cycle

The operator no longer waits at 20:10. The existing
`spy-eod-market-data-refresh` task refreshes and reconciles adjusted data after
the provider cutoff. The secure paper task independently acts during the next
NYSE session's first hour.

Run a real paper-account visibility pass with mutation structurally disabled:

```powershell
.\scripts\run_secure_spy_paper_cycle.ps1 -Format json
```

The strong no-submit result is `state=ready_no_submit` with:

- `credential_lease_consumed=true`;
- `paper_broker_read_performed=true`;
- `expected_account_matched=true`;
- `readiness.generated=true`;
- `paper_submit_performed=false`;
- `broker_mutation_performed=false`; and
- `live_authorized=false`.

Preview the weekday 09:31 task registration:

```powershell
.\scripts\register_secure_spy_paper_cycle_task.ps1
```

Install the exact checked-in task:

```powershell
.\scripts\register_secure_spy_paper_cycle_task.ps1 -RegisterTask
```

The task action includes `-AllowPaperMutation`, but Python still refuses before
credential access outside an actual NYSE session's 09:30–10:30 window. It runs
at 09:31 with three 15-minute retries, ignores overlapping instances, does not
catch up a missed trigger, and cannot run on demand through Task Scheduler.
Each cycle permits at most one new SPY paper order with a `$25.00` notional
cap. A complete exposure-reducing SPY close is allowed to flatten a larger
existing position.

Inspect task and generated cycle state without exposing credentials:

```powershell
Get-ScheduledTask -TaskName "algo-trader-secure-spy-paper-cycle"
Get-ScheduledTaskInfo -TaskName "algo-trader-secure-spy-paper-cycle"
Get-Content runs\paper_autopilot\secure_spy_paper_cycle\latest_receipt.json
```

Healthy terminal states are `healthy_no_action`,
`paper_action_reconciled`, or `revalidated_no_action`.
`reconciliation_required`, `blocked_live_safety`, an account mismatch, an open
SPY order, an unexpected non-SPY position, stale data, or any readiness mismatch
is fail-closed. Do not bypass the task window, readiness hash, order journal,
paper endpoint, cap, or reconciliation to make a blocked run proceed.

## V5.56 Selectable RSI Paper Strategy

The secure lane accepts exactly one active strategy per cycle. The installed
task remains explicit about the SMA default:

```powershell
.\scripts\run_secure_spy_paper_cycle.ps1 `
  -ActiveStrategyId "spy_sma_50_200_training_wheel" `
  -Format text
```

Exercise the promoted RSI(14) strategy with real paper-broker observation and
mutation disabled:

```powershell
.\scripts\run_secure_spy_paper_cycle.ps1 `
  -ActiveStrategyId "spy_rsi_14_mean_reversion_paper" `
  -Format text
```

The expected neutral result is `state=healthy_no_action` with
`selected_strategy_id=spy_rsi_14_mean_reversion_paper`,
`paper_broker_read_performed=true`, and all submit/mutation/live fields false.
An actionable RSI result becomes `ready_no_submit` unless
`-AllowPaperMutation` is also explicit and every V5.55 window, readiness,
account, cap, journal, and reconciliation gate passes.

## V5.57 Strategy Sleeve Bootstrap and Dual Tasks

The shared paper account now supports simultaneous SMA and RSI policy lanes
through durable strategy-owned SPY quantity sleeves. Before installing the
dual tasks, assign any existing aggregate SPY position to its owning strategy
with one no-submit bootstrap. For the existing SMA-owned position:

```powershell
.\scripts\run_secure_spy_paper_cycle.ps1 `
  -ActiveStrategyId "spy_sma_50_200_training_wheel" `
  -AdoptExistingPositionToActiveSleeve `
  -Format text
```

Do not use `-AllowPaperMutation` with the adoption flag. Adoption succeeds only
for a pristine sleeve ledger and performs broker reads but no submit, cancel,
replace, close, or other broker mutation. Require:

- `state=healthy_no_action` or `state=ready_no_submit`;
- `strategy_sleeve_broker_quantity_match=true`;
- `paper_submit_performed=false`;
- `broker_mutation_performed=false`; and
- `live_authorized=false`.

Then verify both strategies independently with mutation disabled:

```powershell
.\scripts\run_secure_spy_paper_cycle.ps1 `
  -ActiveStrategyId "spy_sma_50_200_training_wheel" `
  -Format text

.\scripts\run_secure_spy_paper_cycle.ps1 `
  -ActiveStrategyId "spy_rsi_14_mean_reversion_paper" `
  -Format text
```

Preview and install both exact task definitions:

```powershell
.\scripts\register_secure_spy_paper_cycle_task.ps1
.\scripts\register_secure_spy_paper_cycle_task.ps1 -RegisterTask
```

The SMA task runs at 09:31 ET and the RSI task at 09:38 ET. Both retain three
15-minute retries, `IgnoreNew`, no catch-up, no on-demand start, the NYSE
09:30–10:30 mutation window, one order per cycle, `$25.00` entry cap, `$60.00`
aggregate entry-exposure cap, and two sleeve orders per UTC session day. The
shared runtime lease serializes overlap.

Inspect both task definitions:

```powershell
Get-ScheduledTask -TaskName "algo-trader-secure-spy-paper-cycle"
Get-ScheduledTask -TaskName "algo-trader-secure-spy-rsi-paper-cycle"
```

Stop on `strategy_sleeve_broker_quantity_mismatch`,
`strategy_sleeve_intent_pending`, a sleeve reconciliation requirement, or any
readiness sleeve generation/cap mismatch. Do not edit the SQLite ledger by
hand or re-run adoption against a non-pristine ledger.

## V5.58 NexusTrade Research Intake

Capture exact NexusTrade strategy rules and backtest metadata in a local JSON
file. Do not include API keys, tokens, account identifiers, broker payloads, or
credentials. Run the credential-free offline bridge:

```powershell
.\scripts\run_nexustrade_strategy_intake.ps1 `
  -InputPath "path\to\nexustrade_candidates.json" `
  -OutputRoot "runs\nexustrade_strategy_intake\latest" `
  -BarsCsv "runs\operator_input\multi_etf_adjusted_daily_canonical.csv"
```

The root JSON fields are exactly:

- `schema_version` (`"1"`), `provider` (`"nexustrade"`), `captured_at`,
  `source_url`, and `candidates`.

Each candidate contains exactly:

- `candidate_id`, `strategy_name`, `hypothesis`, `source_url`, `family`,
  `symbol`, `timeframe`, `parameters`, `source_rules`, `source_backtest`,
  `parent_strategy_ids`, and `pairing_role`.

Supported local daily families are `sma_crossover_long_only`,
`time_series_momentum_long_only`, `drawdown_filter_long_only`, and
`etf_relative_momentum_basket`. Other families are retained with
`needs_local_adapter`. `pairing_role` is one of `standalone`,
`confirmation_filter`, `risk_regime_filter`, or `diversifier`; it records the
research hypothesis but grants no routing or execution authority.

Require `source_metrics_used_for_ranking=false`,
`source_metrics_used_for_promotion=false`,
`paper_promotion_allowed=false`, all broker/network/mutation fields false, and
one of these candidate routes:

- `repair_intake_blockers`;
- `await_or_repair_local_data`;
- `continue_local_research`;
- `reject`; or
- `preview_review`.

Only `preview_review` advances to a separate no-submit design review. Never use
NexusTrade's deploy control or connect broker credentials through this lane.

## V5.64 Independent Monthly Replication

This command runs the separately preregistered independent replication. It is
not an authentic replay of the March 2025 NexusTrade run:

```powershell
.\scripts\run_nexustrade_monthly_independent_replication.ps1
```

The wrapper fails closed when `APP_PROFILE` is paper/live or any broker,
NexusTrade, or Tiingo credential alias is loaded. It uses only the committed
protocol, the V5.63 canonical-data manifest, and the local combined adjusted
daily CSV. Credential values are never printed.

Expected ignored outputs under
`runs/v5_64_nexustrade_monthly_independent_replication` are:

- `preregistration.json`;
- `replication_results.json`;
- `replication_summary.md`; and
- `manifest.json`.

Inspect each candidate's `route` and gate details. Only `preview_review` can
support a later separately authorized no-submit shadow design.
`continue_local_research` and `reject` cannot advance. No result grants paper
promotion, broker access, order submission, or live authority.

## V5.65 Monthly High-Volatility Defense

Run the separately preregistered V5.65 defense only from a credential-free,
offline process:

```powershell
.\scripts\run_nexustrade_monthly_high_volatility_defense.ps1
```

The wrapper fails closed when `APP_PROFILE` is paper/live or a broker,
NexusTrade, or Tiingo credential alias is loaded. It prints credential
presence booleans only and never prints values. The engine also verifies the
frozen V5.64 protocol and engine hashes before loading canonical bars.

Expected ignored outputs under
`runs/v5_65_nexustrade_monthly_high_volatility_defense` are:

- `preregistration.json`;
- `defense_results.json`;
- `defense_summary.md`; and
- `manifest.json`.

Inspect `candidate.route`, every gate, `overlay_integrity`, and the
per-window volatility diagnostics. A `continue_local_research` or `reject`
route freezes the hypothesis without creating a no-submit shadow. Only a
locally produced `preview_review` may support a later separately authorized
no-submit design. The command never authorizes paper promotion, broker access,
orders, or live activity.

## V5.66 High-Volatility Attribution Diagnostic

Run the preregistered attribution only from a credential-free, offline
process:

```powershell
.\scripts\run_nexustrade_high_volatility_attribution.ps1
```

The wrapper fails closed when `APP_PROFILE` is paper/live or a broker,
NexusTrade, or Tiingo credential alias is loaded. It prints presence booleans
only. Before loading canonical bars, the engine validates the V5.66 protocol,
canonical data/manifest, V5.64/V5.65 protocols and engines, and all frozen
V5.65 output hashes. It also refuses output if the recomputed V5.64 parent or
V5.65 actual metrics, target vectors, or overlay integrity differ.

Expected ignored outputs under
`runs/v5_66_nexustrade_high_volatility_attribution` are:

- `preregistration.json`;
- `attribution_results.json`;
- `attribution_summary.md`; and
- `manifest.json`.

Inspect `frozen_reproduction`, `diagnostic_classification`, every cost/window
under `attribution.cost_results`, `volatility_transition_ledger`, and the
manifest hashes. `D` and `I` are diagnostic counterfactuals, never candidates.
No classification creates a route, preview, shadow, paper promotion, broker
access, order authority, or live authority.

## V5.67 Monthly Risk-Balanced Allocation

Run the independently preregistered V5.67 candidate only from a
credential-free, offline process:

```powershell
.\scripts\run_nexustrade_monthly_risk_balanced_allocation.ps1
```

The wrapper fails closed when `APP_PROFILE` is paper/live or a broker,
NexusTrade, or Tiingo credential alias is loaded. A Tiingo key may remain in an
unloaded `.env` file; V5.67 does not need or read it because the validated
canonical adjusted-daily CSV is already local. The wrapper reports booleans
only and never prints credential values.

Before replay, the engine validates the V5.67 protocol, frozen V5.64 protocol,
engine, and four output hashes, the V5.66 exclusion boundary, and V5.63 data
and manifest. It refuses V5.67 output unless the V5.64 preregistration, result,
and summary reproduce exactly.

Expected ignored outputs under
`runs/v5_67_nexustrade_monthly_risk_balanced_allocation` are:

- `preregistration.json`;
- `risk_balanced_results.json`;
- `risk_balanced_summary.md`; and
- `manifest.json`.

Inspect `candidate.route`, every gate, `allocation_integrity`,
`frozen_parent_reproduction`, all cost/window records, and the manifest hashes.
The canonical V5.67 route is `continue_local_research`; freeze it without
parameter tuning or another same-thesis repair. It creates no preview, shadow,
paper promotion, broker access, order authority, or live authority.
