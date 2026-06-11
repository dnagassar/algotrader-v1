"""Operator summary generator over Daily Soak Acceptance History Index (V3K).

Consumes V3J history index JSONL and writes an operator summary.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError


@dataclass(slots=True)
class EtfSmaDailySoakOperatorSummaryConfig:
    """Configuration for V3K Daily Soak Operator Summary."""

    history_index: Path | str = "runs/daily_soak/v3j_daily_soak_acceptance_history_index.jsonl"
    out: Path | str = "runs/daily_soak/v3k_daily_soak_operator_summary.jsonl"
    text_out: Path | str | None = None


def _normalize_path(path: Path | str) -> str:
    """Computes POSIX path relative to current working directory safely."""
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return str(p.as_posix())


def run_etf_sma_daily_soak_operator_summary(
    config: EtfSmaDailySoakOperatorSummaryConfig,
) -> list[dict[str, Any]]:
    """Execute the operator summary command."""
    index_path = Path(config.history_index)
    out_path = Path(config.out)

    # V3K Canonical Safety Authorizations (must all be false)
    safety_auths = {
        "live_authorized": False,
        "paper_submit_authorized": False,
        "paper_broker_reads_authorized": False,
        "broker_mutation_authorized": False,
        "network_authorized": False,
        "credentials_loaded": False,
    }

    # Internal tracking variables
    malformed_records_found = False
    invalid_schema_records_found = False
    source_safety_authorized_truthy = False
    has_usable_summary_or_latest_run = False
    status_conflict_found = False

    parsed_records: list[dict[str, Any]] = []

    # Check if file exists and is non-empty
    if not index_path.exists() or index_path.stat().st_size == 0:
        classification = "no_history"
        reason = f"Input history index file is missing or empty: {index_path}"
    else:
        try:
            content = index_path.read_text(encoding="utf-8").strip()
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            for line in lines:
                try:
                    rec = json.loads(line)
                    if not isinstance(rec, dict):
                        invalid_schema_records_found = True
                        continue
                    parsed_records.append(rec)
                except json.JSONDecodeError:
                    malformed_records_found = True
        except Exception as exc:
            # Operational failures like permissions etc are caught at a higher level,
            # but if file exists and cannot be read, classify as invalid_history_index or repair_required
            classification = "invalid_history_index"
            reason = f"Failed to read input history index file: {exc}"
            return _write_outputs(config, classification, reason, safety_auths)

        if malformed_records_found:
            classification = "repair_required"
            reason = "Malformed JSONL records found in the history index."
        elif not parsed_records:
            classification = "no_history"
            reason = f"Input history index contains no records: {index_path}"
        else:
            # Extract safety flags from the V3J records to ensure none are truthy
            for rec in parsed_records:
                # 1. Check safety_authorizations dict
                auths = rec.get("safety_authorizations")
                if isinstance(auths, dict):
                    for val in auths.values():
                        if val is not False:
                            source_safety_authorized_truthy = True
                
                # 2. Check source_derived_safety if present
                derived_safety = rec.get("source_derived_safety")
                if isinstance(derived_safety, dict):
                    for val in derived_safety.values():
                        if val is not False:
                            source_safety_authorized_truthy = True
                
                # 3. Check root-level authorization keys
                for key, val in rec.items():
                    if key.endswith("_authorized") or key.endswith("_loaded"):
                        if val is not False:
                            source_safety_authorized_truthy = True

            # Extract counts and details
            attempted_count = 0
            accepted_count = 0
            blocked_count = 0
            insufficient_history_count = 0
            validation_finding_count_total = 0
            latest_golden_acceptance_status = None
            latest_release_gate_status = None
            latest_run_id = None
            latest_as_of = None
            key_artifact_paths: list[str] = []
            latest_run_artifact_paths: list[str] = []
            blocker_trends: dict[str, int] = {}
            latest_blockers: list[str] = []

            # Locate key V3J record types
            summary_rec = next((r for r in parsed_records if r.get("record_type") == "summary"), None)
            latest_run_rec = next((r for r in parsed_records if r.get("record_type") == "latest_run"), None)
            blocker_trends_rec = next((r for r in parsed_records if r.get("record_type") == "blocker_trends"), None)

            if summary_rec:
                has_usable_summary_or_latest_run = True
                attempted_count = summary_rec.get("attempted_count", 0)
                accepted_count = summary_rec.get("accepted_count", 0)
                blocked_count = summary_rec.get("blocked_count", 0)
                insufficient_history_count = summary_rec.get("insufficient_history_count", 0)
                validation_finding_count_total = summary_rec.get("validation_finding_count_total", 0)
                latest_golden_acceptance_status = summary_rec.get("latest_golden_acceptance_status")
                latest_release_gate_status = summary_rec.get("latest_release_gate_status")
                latest_run_id = summary_rec.get("latest_run_id")
                latest_as_of = summary_rec.get("latest_as_of")
                key_artifact_paths = summary_rec.get("key_artifact_paths", [])
                
                # Validate summary schema
                for key in ["phase", "record_type", "status", "safety_authorizations"]:
                    if key not in summary_rec:
                        invalid_schema_records_found = True

            if latest_run_rec:
                has_usable_summary_or_latest_run = True
                latest_run_artifact_paths = latest_run_rec.get("key_artifact_paths", [])
                if not latest_as_of:
                    latest_as_of = latest_run_rec.get("latest_as_of")
                if not latest_golden_acceptance_status:
                    latest_golden_acceptance_status = latest_run_rec.get("latest_golden_acceptance_status")
                if not latest_release_gate_status:
                    latest_release_gate_status = latest_run_rec.get("latest_release_gate_status")

            if blocker_trends_rec:
                blocker_trends = blocker_trends_rec.get("blocker_trends", {})

            # Gather blockers from the last per_run record (representing latest run)
            per_run_records = [r for r in parsed_records if r.get("record_type") == "per_run"]
            if per_run_records:
                latest_per_run = per_run_records[-1]
                latest_blockers = latest_per_run.get("blockers", [])

            # Check for conflict in status/counts
            sum_of_parts = accepted_count + blocked_count + insufficient_history_count
            if attempted_count < sum_of_parts:
                status_conflict_found = True
            
            # Reconcile status fields
            if latest_golden_acceptance_status == "accepted" and blocked_count > 0 and latest_blockers:
                status_conflict_found = True

            # Determine classification
            if source_safety_authorized_truthy:
                classification = "repair_required"
                reason = "Source history index contains non-false/truthy safety authorization flags."
            elif malformed_records_found:
                classification = "repair_required"
                reason = "Malformed JSONL records found in the history index."
            elif invalid_schema_records_found:
                classification = "repair_required"
                reason = "Invalid V3J schema records found in the history index."
            elif status_conflict_found:
                classification = "repair_required"
                reason = "Conflicts or inconsistencies detected in status counts or blocker fields."
            elif not has_usable_summary_or_latest_run:
                classification = "invalid_history_index"
                reason = "Input exists but does not contain usable V3J summary or latest_run records."
            else:
                # Normal logic path
                if (
                    latest_golden_acceptance_status == "accepted"
                    and latest_release_gate_status == "accepted"
                    and validation_finding_count_total == 0
                ):
                    classification = "proceed_offline"
                    reason = "Latest daily lab acceptance is green and safety invariants hold."
                elif (
                    latest_golden_acceptance_status == "blocked"
                    or latest_release_gate_status == "blocked"
                    or validation_finding_count_total > 0
                ):
                    # Check if blocked ONLY due to known deterministic no-history/insufficient-history blockers
                    allowed_no_history = {
                        "insufficient_history",
                        "insufficient_history_to_risk_on",
                        "sma_insufficient_history",
                        "no_history",
                        "no_data",
                        "no-data",
                        "blocked-no-history",
                    }
                    is_no_history_blocker = False
                    if latest_blockers and validation_finding_count_total == 0:
                        has_explicit_allowed = any(b in allowed_no_history for b in latest_blockers)
                        if has_explicit_allowed:
                            non_no_history = [b for b in latest_blockers if b not in allowed_no_history]
                            if not non_no_history:
                                is_no_history_blocker = True
                            elif len(non_no_history) == 1 and non_no_history[0] == "release_gate_blocked":
                                is_no_history_blocker = True
                    
                    if is_no_history_blocker:
                        classification = "inspect_blockers"
                        reason = "Latest status is blocked due to known deterministic no-history/insufficient-history fixtures."
                    else:
                        classification = "repair_required"
                        reason = "Latest daily lab acceptance is blocked due to non-history blockers or validation findings."
                else:
                    classification = "repair_required"
                    reason = "Latest status is blocked or could not be reconciled."

            # Construct fields for outputs
            blocker_trend_summary = dict(sorted(blocker_trends.items()))
            recurring_blockers = sorted([b for b, count in blocker_trends.items() if count >= 2])

            return _write_outputs(
                config=config,
                classification=classification,
                reason=reason,
                safety_auths=safety_auths,
                latest_golden_acceptance_status=latest_golden_acceptance_status,
                latest_release_gate_status=latest_release_gate_status,
                latest_run_id=latest_run_id,
                latest_as_of=latest_as_of,
                attempted_count=attempted_count,
                accepted_count=accepted_count,
                blocked_count=blocked_count,
                insufficient_history_count=insufficient_history_count,
                validation_finding_count_total=validation_finding_count_total,
                recurring_blockers=recurring_blockers,
                blocker_trend_summary=blocker_trend_summary,
                key_artifact_paths=sorted(key_artifact_paths),
                latest_run_artifact_paths=sorted(latest_run_artifact_paths),
            )

    return _write_outputs(config, classification, reason, safety_auths)


def _write_outputs(
    config: EtfSmaDailySoakOperatorSummaryConfig,
    classification: str,
    reason: str,
    safety_auths: dict[str, bool],
    latest_golden_acceptance_status: str | None = None,
    latest_release_gate_status: str | None = None,
    latest_run_id: str | None = None,
    latest_as_of: str | None = None,
    attempted_count: int = 0,
    accepted_count: int = 0,
    blocked_count: int = 0,
    insufficient_history_count: int = 0,
    validation_finding_count_total: int = 0,
    recurring_blockers: list[str] | None = None,
    blocker_trend_summary: dict[str, int] | None = None,
    key_artifact_paths: list[str] | None = None,
    latest_run_artifact_paths: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Helper to write the deterministic output JSONL and Markdown artifacts."""
    source_history_path = _normalize_path(config.history_index)
    out_path = Path(config.out)

    rec_recurring = recurring_blockers or []
    rec_trend = blocker_trend_summary or {}
    rec_key_paths = key_artifact_paths or []
    rec_latest_paths = latest_run_artifact_paths or []

    # Build the 4 output records
    records_to_write: list[dict[str, Any]] = []

    # 1. Summary Record
    summary_rec = {
        "phase": "V3K",
        "record_type": "summary",
        "status": classification,
        "source_history_index_path": source_history_path,
        "latest_golden_acceptance_status": latest_golden_acceptance_status,
        "latest_release_gate_status": latest_release_gate_status,
        "latest_run_id": latest_run_id,
        "latest_as_of": latest_as_of,
        "attempted_count": attempted_count,
        "accepted_count": accepted_count,
        "blocked_count": blocked_count,
        "insufficient_history_count": insufficient_history_count,
        "validation_finding_count_total": validation_finding_count_total,
        "recurring_blockers": rec_recurring,
        "blocker_trend_summary": rec_trend,
        "key_artifact_paths": rec_key_paths,
        "latest_run_artifact_paths": rec_latest_paths,
        "next_safe_action_classification": classification,
        "next_safe_action_reason": reason,
        "safety_authorizations": safety_auths,
    }
    records_to_write.append(summary_rec)

    # 2. Latest Status Record
    latest_status_rec = {
        "phase": "V3K",
        "record_type": "latest_status",
        "status": classification,
        "source_history_index_path": source_history_path,
        "latest_golden_acceptance_status": latest_golden_acceptance_status,
        "latest_release_gate_status": latest_release_gate_status,
        "latest_run_id": latest_run_id,
        "latest_as_of": latest_as_of,
        "latest_run_artifact_paths": rec_latest_paths,
        "safety_authorizations": safety_auths,
    }
    records_to_write.append(latest_status_rec)

    # 3. Blocker Summary Record
    blocker_summary_rec = {
        "phase": "V3K",
        "record_type": "blocker_summary",
        "status": classification,
        "source_history_index_path": source_history_path,
        "recurring_blockers": rec_recurring,
        "blocker_trend_summary": rec_trend,
        "safety_authorizations": safety_auths,
    }
    records_to_write.append(blocker_summary_rec)

    # 4. Next Action Record
    next_action_rec = {
        "phase": "V3K",
        "record_type": "next_action",
        "status": classification,
        "source_history_index_path": source_history_path,
        "latest_golden_acceptance_status": latest_golden_acceptance_status,
        "latest_release_gate_status": latest_release_gate_status,
        "latest_run_id": latest_run_id,
        "latest_as_of": latest_as_of,
        "attempted_count": attempted_count,
        "accepted_count": accepted_count,
        "blocked_count": blocked_count,
        "insufficient_history_count": insufficient_history_count,
        "validation_finding_count_total": validation_finding_count_total,
        "recurring_blockers": rec_recurring,
        "blocker_trend_summary": rec_trend,
        "key_artifact_paths": rec_key_paths,
        "latest_run_artifact_paths": rec_latest_paths,
        "next_safe_action_classification": classification,
        "next_safe_action_reason": reason,
        "safety_authorizations": safety_auths,
    }
    records_to_write.append(next_action_rec)

    # Ensure output folder exists
    if out_path.parent != Path(".") and not out_path.parent.exists():
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # Write output JSONL
    try:
        lines_str = "".join(
            json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n"
            for r in records_to_write
        )
        out_path.write_text(lines_str, encoding="utf-8", newline="\n")
    except Exception as exc:
        raise ValidationError(f"Failed to write operator summary JSONL output: {exc}")

    # Write optional markdown summary
    if config.text_out:
        text_out_path = Path(config.text_out)
        if text_out_path.parent != Path(".") and not text_out_path.parent.exists():
            try:
                text_out_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        # Build stable report content without dates or file modified times.
        # Ensure it has stable sorting.
        safety_booleans_str = "\n".join(
            f"- {k}: {v}" for k, v in sorted(safety_auths.items())
        )
        recurring_blockers_str = (
            "\n".join(f"- {b}" for b in sorted(rec_recurring))
            if rec_recurring
            else "none"
        )
        artifacts_str = (
            "\n".join(f"- {p}" for p in sorted(rec_key_paths))
            if rec_key_paths
            else "none"
        )

        report = (
            f"# Daily Lab Acceptance Operator Summary (V3K)\n\n"
            f"## Status\n"
            f"- **Next Safest Action**: {classification.upper()}\n"
            f"- **Reason**: {reason}\n\n"
            f"## Latest Run details\n"
            f"- **Golden Acceptance Status**: {latest_golden_acceptance_status or 'UNKNOWN'}\n"
            f"- **Release Gate Status**: {latest_release_gate_status or 'UNKNOWN'}\n"
            f"- **Run ID**: {latest_run_id or 'UNKNOWN'}\n"
            f"- **As-Of**: {latest_as_of or 'UNKNOWN'}\n\n"
            f"## Counts Summary\n"
            f"- **Attempted Days**: {attempted_count}\n"
            f"- **Accepted Days**: {accepted_count}\n"
            f"- **Blocked Days**: {blocked_count}\n"
            f"- **Insufficient History Days**: {insufficient_history_count}\n"
            f"- **Total Validation Findings**: {validation_finding_count_total}\n\n"
            f"## Recurring Blockers\n"
            f"{recurring_blockers_str}\n\n"
            f"## Safety Authorizations\n"
            f"{safety_booleans_str}\n\n"
            f"## Key Artifacts\n"
            f"{artifacts_str}\n"
        )

        try:
            text_out_path.write_text(report, encoding="utf-8", newline="\n")
        except Exception as exc:
            raise ValidationError(f"Failed to write operator summary text output: {exc}")

    return records_to_write
