"""Offline daily lab closeout run receipt generator (V3N)."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class DailyLabCloseoutRunReceiptConfig:
    """Configuration for V3N Daily Lab Closeout Run Receipt."""

    start_date: str
    end_date: str
    bars_csv: str
    reconciliation_state_path: str
    daily_soak_dir: str
    status: str
    steps_json: str
    receipt_out: str = "runs/daily_soak/v3n_daily_lab_closeout_run_receipt.jsonl"
    receipt_text_out: str = "runs/daily_soak/v3n_daily_lab_closeout_run_receipt.md"


_SAFETY_BOOLEANS = {
    "broker_reads": False,
    "broker_mutations": False,
    "paper_submit": False,
    "credentials_required": False,
    "network_required": False,
    "live_trading": False,
}

_LABELS = [
    "paper_lab_only",
    "research_only",
    "not_live_authorized",
    "profit_claim=none",
    "offline_only",
]


def run_daily_lab_closeout_receipt(
    config: DailyLabCloseoutRunReceiptConfig,
) -> dict[str, Any]:
    """Generate the V3N run receipt (JSONL and Markdown)."""

    steps_input = config.steps_json.strip()
    if (steps_input.endswith(".json") or steps_input.endswith(".jsonl")) and Path(steps_input).exists():
        try:
            steps = json.loads(Path(steps_input).read_text(encoding="utf-8-sig"))
        except Exception as exc:
            raise ValidationError(f"Failed to read steps from file {steps_input}: {exc}")
    else:
        try:
            steps = json.loads(steps_input)
        except Exception as exc:
            raise ValidationError(f"Failed to parse steps_json string: {exc}")

    if not isinstance(steps, list):
        raise ValidationError("steps must represent a list of steps.")

    # Map status to recommended next offline action
    # Suggested next actions:
    # - review_closeout_packet (if completed)
    # - inspect_failed_step (if failed)
    if config.status == "completed":
        recommended_action = "review_closeout_packet"
    elif config.status in (
        "failed_acceptance_launcher",
        "failed_history_index",
        "failed_operator_summary",
        "failed_closeout_packet",
        "failed_receipt_generation",
    ):
        recommended_action = "inspect_failed_step"
    else:
        recommended_action = "rerun_offline_daily_lab_closeout"

    # Set up artifact definitions
    soak_dir = Path(config.daily_soak_dir)
    receipt_out_path = Path(config.receipt_out)
    receipt_text_out_path = Path(config.receipt_text_out)

    expected_artifacts_info = [
        ("v3j_history_index", soak_dir / "v3j_daily_soak_acceptance_history_index.jsonl"),
        ("v3k_operator_summary_jsonl", soak_dir / "v3k_daily_soak_operator_summary.jsonl"),
        ("v3k_operator_summary_markdown", soak_dir / "v3k_daily_soak_operator_summary.md"),
        ("v3l_closeout_packet_jsonl", soak_dir / "v3l_daily_soak_closeout_packet.jsonl"),
        ("v3l_closeout_packet_markdown", soak_dir / "v3l_daily_soak_closeout_packet.md"),
        ("v3n_receipt_jsonl", receipt_out_path),
        ("v3n_receipt_markdown", receipt_text_out_path),
    ]

    # Helper function to generate artifact reference
    def make_artifact_ref(kind: str, path: Path) -> dict[str, Any]:
        exists = path.exists()
        size_bytes = path.stat().st_size if exists and path.is_file() else None
        sha256 = _sha256(path) if exists and path.is_file() else None
        return {
            "exists": exists,
            "kind": kind,
            "path": _normalize_path(path),
            "sha256": sha256,
            "size_bytes": size_bytes,
        }

    # Pass 1: Build the receipt dictionary with whatever is currently on disk
    artifacts = [make_artifact_ref(kind, path) for kind, path in expected_artifacts_info]

    receipt = {
        "schema_version": "1",
        "milestone": "V3N",
        "status": config.status,
        "start_date": config.start_date,
        "end_date": config.end_date,
        "bars_csv": _normalize_path(Path(config.bars_csv)),
        "reconciliation_state_path": _normalize_path(Path(config.reconciliation_state_path)),
        "daily_soak_dir": _normalize_path(soak_dir),
        "steps": steps,
        "artifacts": artifacts,
        "safety": dict(_SAFETY_BOOLEANS),
        "labels": list(_LABELS),
        "recommended_next_offline_action": recommended_action,
    }

    # Write the JSONL receipt file
    _write_jsonl(receipt_out_path, [receipt])

    # Pass 2: Re-generate artifact metadata now that receipt JSONL is written (and receipt MD will be written)
    # To get correct size and sha256 for receipt_jsonl, we recompute
    artifacts = [make_artifact_ref(kind, path) for kind, path in expected_artifacts_info]
    receipt["artifacts"] = artifacts

    # Rewrite the JSONL receipt with updated artifact list (now has valid details for jsonl receipt itself)
    _write_jsonl(receipt_out_path, [receipt])

    # Write the Markdown text receipt
    _write_markdown(receipt_text_out_path, receipt)

    # Re-evaluate once more after markdown is written so both JSONL and Markdown match exactly
    artifacts = [make_artifact_ref(kind, path) for kind, path in expected_artifacts_info]
    receipt["artifacts"] = artifacts
    _write_jsonl(receipt_out_path, [receipt])

    return receipt


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_path(path: Path | str) -> str:
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return str(p.as_posix())


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    if path.parent != Path(".") and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        )
        path.write_text(payload, encoding="utf-8", newline="\n")
    except Exception as exc:
        raise ValidationError(f"Failed to write receipt JSONL output: {exc}")


def _write_markdown(path: Path, receipt: dict[str, Any]) -> None:
    if path.parent != Path(".") and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    # Build steps table
    step_rows = []
    for step in receipt["steps"]:
        exit_code = step.get("exit_code")
        exit_code_str = str(exit_code) if exit_code is not None else "N/A"
        step_rows.append(
            f"| {step.get('name')} | `{step.get('status')}` | {exit_code_str} | `{step.get('command')}` |"
        )
    steps_table = "\n".join(step_rows)

    # Build artifacts table
    artifact_rows = []
    for art in receipt["artifacts"]:
        size_str = str(art.get("size_bytes")) if art.get("size_bytes") is not None else "N/A"
        sha_str = art.get("sha256") or "N/A"
        artifact_rows.append(
            f"| {art.get('kind')} | {art.get('path')} | {str(art.get('exists')).lower()} | {size_str} | {sha_str} |"
        )
    artifacts_table = "\n".join(artifact_rows)

    # Safety summary
    safety_lines = "\n".join(
        f"- {key}: {str(value).lower()}"
        for key, value in sorted(receipt["safety"].items())
    )

    # Labels list
    labels_str = ", ".join(receipt["labels"])

    report = (
        f"# V3N Daily Lab Closeout Run Receipt\n\n"
        f"## Status\n"
        f"- **final_status**: `{receipt['status']}`\n"
        f"- **recommended_next_offline_action**: `{receipt['recommended_next_offline_action']}`\n\n"
        f"## Requested Run Inputs\n"
        f"- **start_date**: {receipt['start_date']}\n"
        f"- **end_date**: {receipt['end_date']}\n"
        f"- **bars_csv**: `{receipt['bars_csv']}`\n"
        f"- **reconciliation_state_path**: `{receipt['reconciliation_state_path']}`\n"
        f"- **daily_soak_dir**: `{receipt['daily_soak_dir']}`\n\n"
        f"## Step Execution Sequence\n"
        f"| Step Name | Status | Exit Code | Command |\n"
        f"| --- | --- | --- | --- |\n"
        f"{steps_table}\n\n"
        f"## Expected Artifacts\n"
        f"| Kind | Path | Exists | Size (Bytes) | SHA256 |\n"
        f"| --- | --- | --- | --- | --- |\n"
        f"{artifacts_table}\n\n"
        f"## Safety Summary\n"
        f"{safety_lines}\n\n"
        f"## Labels\n"
        f"- {labels_str}\n\n"
        f"This receipt does not authorize broker reads, paper submit, broker mutation, or live trading.\n"
    )

    try:
        path.write_text(report, encoding="utf-8", newline="\n")
    except Exception as exc:
        raise ValidationError(f"Failed to write receipt text output: {exc}")
