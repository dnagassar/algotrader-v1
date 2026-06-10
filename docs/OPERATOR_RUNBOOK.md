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
