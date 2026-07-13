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
* `-FullVerify` (Optional): Runs full offline pytest suite inside `verify_offline.ps1` instead of targeted guard tests only.

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

## Read-Only Journal Cancellation-Planning Preview

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
