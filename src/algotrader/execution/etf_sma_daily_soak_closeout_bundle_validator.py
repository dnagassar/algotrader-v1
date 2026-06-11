"""Offline daily lab closeout bundle validator (V3O)."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class DailyLabCloseoutBundleValidationConfig:
    """Configuration for V3O Daily Lab Closeout Bundle Validator."""

    daily_soak_dir: str = "runs/daily_soak"
    validation_out: str = "runs/daily_soak/v3o_daily_lab_closeout_bundle_validation.jsonl"
    validation_text_out: str = "runs/daily_soak/v3o_daily_lab_closeout_bundle_validation.md"


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

_RISK_KEYS = {
    # shapes like safety / safety_booleans / source_derived_safety
    "broker_reads",
    "broker_mutations",
    "paper_submit",
    "credentials_required",
    "network_required",
    "live_trading",
    # shapes like safety_authorizations
    "live_authorized",
    "paper_submit_authorized",
    "paper_broker_reads_authorized",
    "broker_mutation_authorized",
    "network_authorized",
    "credentials_loaded",
}


def run_daily_lab_closeout_bundle_validation(
    config: DailyLabCloseoutBundleValidationConfig,
) -> dict[str, Any]:
    """Execute bundle validation checks over the closeout artifacts."""
    soak_dir = Path(config.daily_soak_dir)
    validation_out_path = Path(config.validation_out)
    validation_text_out_path = Path(config.validation_text_out)

    expected_artifacts_info = [
        ("v3j_history_index", soak_dir / "v3j_daily_soak_acceptance_history_index.jsonl"),
        ("v3k_operator_summary_jsonl", soak_dir / "v3k_daily_soak_operator_summary.jsonl"),
        ("v3k_operator_summary_markdown", soak_dir / "v3k_daily_soak_operator_summary.md"),
        ("v3l_closeout_packet_jsonl", soak_dir / "v3l_daily_soak_closeout_packet.jsonl"),
        ("v3l_closeout_packet_markdown", soak_dir / "v3l_daily_soak_closeout_packet.md"),
        ("v3n_receipt_jsonl", soak_dir / "v3n_daily_lab_closeout_run_receipt.jsonl"),
        ("v3n_receipt_markdown", soak_dir / "v3n_daily_lab_closeout_run_receipt.md"),
    ]

    failures: list[str] = []
    artifacts_details: list[dict[str, Any]] = []

    # 1. Verify existence, size, sha256, parseability, and non-emptiness of artifacts
    for kind, path in expected_artifacts_info:
        exists = path.exists()
        size_bytes = None
        sha256 = None
        parseable = None
        non_empty = None

        if exists and path.is_file():
            size_bytes = path.stat().st_size
            sha256 = _sha256(path)

            if path.suffix == ".jsonl":
                parseable = True
                try:
                    with path.open("r", encoding="utf-8-sig") as f:
                        for line in f:
                            if line.strip():
                                json.loads(line)
                except Exception as exc:
                    parseable = False
                    failures.append(f"JSONL artifact {kind} is malformed at {path}: {exc}")
            elif path.suffix == ".md":
                try:
                    content = path.read_text(encoding="utf-8-sig").strip()
                    non_empty = len(content) > 0
                    if not non_empty:
                        failures.append(f"Markdown artifact {kind} is empty at {path}.")
                except Exception as exc:
                    non_empty = False
                    failures.append(f"Failed to read markdown artifact {kind} at {path}: {exc}")
        else:
            failures.append(f"Artifact {kind} missing at {_normalize_path(path)}.")
            exists = False

        artifacts_details.append({
            "kind": kind,
            "path": _normalize_path(path),
            "exists": exists,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "parseable": parseable,
            "non_empty": non_empty,
        })

    # 2. V3N receipt reference check
    receipt_ref_failures: list[str] = []
    receipt_path = soak_dir / "v3n_daily_lab_closeout_run_receipt.jsonl"

    if not receipt_path.exists():
        receipt_ref_failures.append("V3N receipt JSONL file does not exist.")
    else:
        try:
            with receipt_path.open("r", encoding="utf-8-sig") as f:
                receipt_records = [json.loads(line) for line in f if line.strip()]
            if not receipt_records:
                receipt_ref_failures.append("V3N receipt JSONL file is empty.")
            else:
                receipt_rec = receipt_records[0]
                receipt_artifacts = receipt_rec.get("artifacts", [])
                receipt_art_map = {
                    art.get("kind"): art for art in receipt_artifacts if art.get("kind")
                }

                for kind, path in expected_artifacts_info:
                    norm_path = _normalize_path(path)
                    ref = receipt_art_map.get(kind)
                    if not ref:
                        receipt_ref_failures.append(
                            f"V3N receipt missing artifact reference for kind '{kind}'."
                        )
                    else:
                        if ref.get("path") != norm_path:
                            receipt_ref_failures.append(
                                f"V3N receipt path mismatch for kind '{kind}': "
                                f"expected '{norm_path}', found '{ref.get('path')}'"
                            )
                        actual_exists = path.exists()
                        if ref.get("exists") != actual_exists:
                            receipt_ref_failures.append(
                                f"V3N receipt exists status mismatch for kind '{kind}': "
                                f"expected {actual_exists}, found {ref.get('exists')}"
                            )
                        if actual_exists and path.is_file():
                            actual_size = path.stat().st_size
                            actual_sha = _sha256(path)
                            if kind != "v3n_receipt_jsonl":
                                if ref.get("size_bytes") != actual_size:
                                    receipt_ref_failures.append(
                                        f"V3N receipt size mismatch for kind '{kind}': "
                                        f"expected {actual_size}, found {ref.get('size_bytes')}"
                                    )
                                if ref.get("sha256") != actual_sha:
                                    receipt_ref_failures.append(
                                        f"V3N receipt sha256 mismatch for kind '{kind}': "
                                        f"expected '{actual_sha}', found '{ref.get('sha256')}'"
                                    )
        except Exception as exc:
            receipt_ref_failures.append(f"Failed to read/parse V3N receipt JSONL: {exc}")

    receipt_reference_check = {
        "status": "failed" if receipt_ref_failures else "passed",
        "failures": receipt_ref_failures,
    }
    if receipt_ref_failures:
        failures.extend(receipt_ref_failures)

    # 3. Required labels check
    required_labels_failures: list[str] = []
    for kind, path in expected_artifacts_info:
        if path.suffix == ".jsonl" and path.exists() and path.is_file():
            try:
                with path.open("r", encoding="utf-8-sig") as f:
                    for line_idx, line in enumerate(f, 1):
                        if line.strip():
                            record = json.loads(line)
                            if "labels" in record:
                                labels = record["labels"]
                                if not isinstance(labels, list):
                                    required_labels_failures.append(
                                        f"Artifact {kind}:{line_idx} labels is not a list."
                                    )
                                    continue
                                for req_label in [
                                    "paper_lab_only",
                                    "not_live_authorized",
                                    "profit_claim=none",
                                    "offline_only",
                                ]:
                                    if req_label not in labels:
                                        required_labels_failures.append(
                                            f"Artifact {kind}:{line_idx} missing required label '{req_label}'."
                                        )
                                if (
                                    "research_only" not in labels
                                    and "signal_evaluation_only" not in labels
                                ):
                                    required_labels_failures.append(
                                        f"Artifact {kind}:{line_idx} missing one of "
                                        f"'research_only' or 'signal_evaluation_only'."
                                    )
            except Exception:
                pass

    required_labels_check = {
        "status": "failed" if required_labels_failures else "passed",
        "failures": required_labels_failures,
    }
    if required_labels_failures:
        failures.extend(required_labels_failures)

    # 4. Safety booleans check
    safety_booleans_failures: list[str] = []
    for kind, path in expected_artifacts_info:
        if path.suffix == ".jsonl" and path.exists() and path.is_file():
            try:
                with path.open("r", encoding="utf-8-sig") as f:
                    for line_idx, line in enumerate(f, 1):
                        if line.strip():
                            record = json.loads(line)
                            for key in [
                                "safety",
                                "safety_booleans",
                                "safety_authorizations",
                                "source_derived_safety",
                            ]:
                                if key in record:
                                     val = record[key]
                                     if isinstance(val, dict):
                                         for k, v in val.items():
                                             if k in _RISK_KEYS:
                                                 if not isinstance(v, bool):
                                                     safety_booleans_failures.append(
                                                         f"Artifact {kind}:{line_idx} safety field "
                                                         f"'{key}.{k}' is not a boolean."
                                                     )
                                                 elif v is not False:
                                                     safety_booleans_failures.append(
                                                         f"Artifact {kind}:{line_idx} safety field "
                                                         f"'{key}.{k}' is unsafe (True)."
                                                     )
                                     else:
                                         safety_booleans_failures.append(
                                             f"Artifact {kind}:{line_idx} safety key "
                                             f"'{key}' is not a dictionary."
                                         )
            except Exception:
                pass

    safety_booleans_check = {
        "status": "failed" if safety_booleans_failures else "passed",
        "failures": safety_booleans_failures,
    }
    if safety_booleans_failures:
        failures.extend(safety_booleans_failures)

    # 5. Tracked runtime artifacts check
    tracked_runtime_failures: list[str] = []
    tracked_files: list[str] = []

    repo_root = Path(__file__).resolve().parent
    while repo_root.parent != repo_root:
        if (repo_root / ".git").exists():
            break
        repo_root = repo_root.parent
    else:
        repo_root = Path.cwd()

    try:
        res = subprocess.run(
            ["git", "ls-files", "runs"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            if (repo_root / ".git").exists():
                tracked_runtime_failures.append(
                    f"git command failed (exit code {res.returncode}): {res.stderr.strip()}"
                )
        else:
            tracked_files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            for f in tracked_files:
                tracked_runtime_failures.append(f"Tracked runtime file found: {f}")
    except FileNotFoundError:
        if (repo_root / ".git").exists():
            tracked_runtime_failures.append("git command not found, but .git directory exists.")
    except Exception as exc:
        tracked_runtime_failures.append(f"Error querying git tracked files: {exc}")

    tracked_runtime_artifacts_check = {
        "status": "failed" if tracked_runtime_failures else "passed",
        "failures": tracked_runtime_failures,
        "tracked_files": tracked_files,
    }
    if tracked_runtime_failures:
        failures.extend(tracked_runtime_failures)

    validation_record = {
        "schema_version": "1",
        "milestone": "V3O",
        "status": "failed" if failures else "passed",
        "bundle_root": _normalize_path(soak_dir),
        "expected_artifacts": [_normalize_path(p) for _, p in expected_artifacts_info],
        "artifacts": artifacts_details,
        "receipt_reference_check": receipt_reference_check,
        "required_labels_check": required_labels_check,
        "safety_booleans_check": safety_booleans_check,
        "tracked_runtime_artifacts_check": tracked_runtime_artifacts_check,
        "failures": failures,
        "recommended_next_offline_action": (
            "review_closeout_packet" if not failures else "inspect_validation_failures"
        ),
        "labels": list(_LABELS),
        "safety": dict(_SAFETY_BOOLEANS),
    }

    _write_jsonl(validation_out_path, [validation_record])
    _write_markdown(validation_text_out_path, validation_record)

    return validation_record


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
        raise ValidationError(f"Failed to write validation JSONL output: {exc}")


def _write_markdown(path: Path, record: dict[str, Any]) -> None:
    if path.parent != Path(".") and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    checks_summary = [
        f"| Receipt Reference Check | `{record['receipt_reference_check']['status']}` | {len(record['receipt_reference_check']['failures'])} |",
        f"| Required Labels Check | `{record['required_labels_check']['status']}` | {len(record['required_labels_check']['failures'])} |",
        f"| Safety Booleans Check | `{record['safety_booleans_check']['status']}` | {len(record['safety_booleans_check']['failures'])} |",
        f"| Tracked Runtime Artifacts Check | `{record['tracked_runtime_artifacts_check']['status']}` | {len(record['tracked_runtime_artifacts_check']['failures'])} |",
    ]
    checks_table = "\n".join(checks_summary)

    failures_list = (
        "\n".join(f"- {f}" for f in record["failures"])
        if record["failures"]
        else "No failures detected."
    )

    report = (
        f"# V3O Daily Lab Closeout Bundle Validation Report\n\n"
        f"## Status\n"
        f"- **validation_status**: `{record['status']}`\n"
        f"- **recommended_next_offline_action**: `{record['recommended_next_offline_action']}`\n\n"
        f"## Validation Checks Summary\n"
        f"| Check | Status | Failures Count |\n"
        f"| --- | --- | --- |\n"
        f"{checks_table}\n\n"
        f"## Failures Details\n"
        f"{failures_list}\n\n"
        f"This validation does not authorize broker reads, paper submit, broker mutation, or live trading.\n"
    )

    try:
        path.write_text(report, encoding="utf-8", newline="\n")
    except Exception as exc:
        raise ValidationError(f"Failed to write validation text output: {exc}")
