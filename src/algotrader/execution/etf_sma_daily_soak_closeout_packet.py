"""Offline closeout packet for Daily Soak acceptance artifacts (V3L)."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class EtfSmaDailySoakCloseoutPacketConfig:
    """Configuration for V3L Daily Soak Closeout Packet."""

    history_index: Path | str = (
        "runs/daily_soak/v3j_daily_soak_acceptance_history_index.jsonl"
    )
    operator_summary: Path | str = (
        "runs/daily_soak/v3k_daily_soak_operator_summary.jsonl"
    )
    operator_summary_md: Path | str = (
        "runs/daily_soak/v3k_daily_soak_operator_summary.md"
    )
    out: Path | str = "runs/daily_soak/v3l_daily_soak_closeout_packet.jsonl"
    text_out: Path | str | None = "runs/daily_soak/v3l_daily_soak_closeout_packet.md"


_SAFETY_BOOLEANS = {
    "broker_reads": False,
    "broker_mutations": False,
    "paper_submit": False,
    "live_trading": False,
    "credentials_required": False,
    "network_required": False,
    "generated_runs_artifact": True,
}

_LABELS = [
    "paper_lab_only",
    "research_only",
    "not_live_authorized",
    "profit_claim=none",
    "offline_only",
]

_GENERIC_BLOCKERS = {"release_gate_blocked"}

_ACCEPTANCE_COMMAND = (
    "powershell -NoProfile -ExecutionPolicy Bypass -File "
    ".\\scripts\\run_daily_lab_acceptance.ps1 "
    "-StartDate 2025-06-01 "
    "-EndDate 2025-06-10 "
    "-BarsCsv tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv "
    "-ReconciliationStatePath "
    "tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl"
)


def run_etf_sma_daily_soak_closeout_packet(
    config: EtfSmaDailySoakCloseoutPacketConfig,
) -> list[dict[str, Any]]:
    """Build the deterministic V3L closeout packet from V3J and V3K artifacts."""

    history_path = Path(config.history_index)
    operator_summary_path = Path(config.operator_summary)
    operator_summary_md_path = Path(config.operator_summary_md)

    input_artifacts = [
        _artifact_reference("history_index", history_path),
        _artifact_reference("operator_summary_jsonl", operator_summary_path),
        _artifact_reference("operator_summary_markdown", operator_summary_md_path),
    ]

    history_records, history_findings = _read_jsonl_records(history_path)
    operator_records, operator_findings = _read_jsonl_records(operator_summary_path)

    history_summary = _first_record(history_records, "summary")
    history_latest_run = _first_record(history_records, "latest_run")
    history_blocker_trends = _first_record(history_records, "blocker_trends")
    history_per_runs = [
        record for record in history_records if record.get("record_type") == "per_run"
    ]
    history_latest_per_run = history_per_runs[-1] if history_per_runs else {}

    operator_summary = _first_record(operator_records, "summary")
    operator_latest_status = _first_record(operator_records, "latest_status")
    operator_blocker_summary = _first_record(operator_records, "blocker_summary")
    operator_next_action = _first_record(operator_records, "next_action")

    incomplete_reasons = _incomplete_reasons(
        input_artifacts=input_artifacts,
        history_records=history_records,
        history_findings=history_findings,
        operator_records=operator_records,
        operator_findings=operator_findings,
    )

    latest_blockers = _string_list(history_latest_per_run.get("blockers"))
    explicit_latest_blockers = sorted(
        {blocker for blocker in latest_blockers if blocker not in _GENERIC_BLOCKERS}
    )
    operator_classification = _first_string(
        operator_summary.get("next_safe_action_classification"),
        operator_summary.get("status"),
        operator_next_action.get("next_safe_action_classification"),
        operator_next_action.get("status"),
    )

    if incomplete_reasons:
        closeout_status = "incomplete_inputs"
        recommended_next_offline_action = (
            "regenerate_history_index"
            if any("history_index" in reason for reason in incomplete_reasons)
            else "regenerate_operator_summary"
        )
    elif explicit_latest_blockers or operator_classification == "inspect_blockers":
        closeout_status = "inspect_blockers"
        recommended_next_offline_action = "inspect_latest_blocker_evidence"
    else:
        closeout_status = "ready_for_operator_review"
        recommended_next_offline_action = "continue_offline_daily_soak"

    next_offline_command = _next_offline_command(
        recommended_next_offline_action,
        history_path,
        operator_summary_path,
        operator_summary_md_path,
        Path(config.out),
        Path(config.text_out) if config.text_out else None,
    )

    latest_golden_acceptance_status = _first_string(
        history_summary.get("latest_golden_acceptance_status"),
        history_latest_run.get("latest_golden_acceptance_status"),
        operator_summary.get("latest_golden_acceptance_status"),
        operator_latest_status.get("latest_golden_acceptance_status"),
    )
    latest_release_gate_status = _first_string(
        history_summary.get("latest_release_gate_status"),
        history_latest_run.get("latest_release_gate_status"),
        operator_summary.get("latest_release_gate_status"),
        operator_latest_status.get("latest_release_gate_status"),
    )
    latest_run_id = _first_string(
        history_summary.get("latest_run_id"),
        operator_summary.get("latest_run_id"),
        operator_next_action.get("latest_run_id"),
    )
    latest_as_of = _first_string(
        history_summary.get("latest_as_of"),
        history_latest_run.get("latest_as_of"),
        operator_summary.get("latest_as_of"),
        operator_latest_status.get("latest_as_of"),
    )
    start_date = _first_string(history_latest_per_run.get("start_date"))
    end_date = _first_string(history_latest_per_run.get("end_date"), latest_as_of)
    if not start_date and latest_run_id:
        start_date, inferred_end_date = _split_run_id(latest_run_id)
        end_date = end_date or inferred_end_date

    blocker_trend_summary = _mapping_from_first(
        history_summary.get("blocker_trends"),
        history_blocker_trends.get("blocker_trends"),
        operator_summary.get("blocker_trend_summary"),
        operator_blocker_summary.get("blocker_trend_summary"),
    )

    packet = {
        "acceptance_run_window": {
            "start_date": start_date,
            "end_date": end_date,
            "latest_as_of": latest_as_of,
            "latest_run_id": latest_run_id,
        },
        "artifact_parse_findings": sorted(history_findings + operator_findings),
        "blocker_classification": {
            "blocker_trend_summary": dict(sorted(blocker_trend_summary.items())),
            "explicit_latest_blockers": explicit_latest_blockers,
            "generic_latest_blockers": sorted(
                {blocker for blocker in latest_blockers if blocker in _GENERIC_BLOCKERS}
            ),
            "latest_blockers": latest_blockers,
            "operator_summary_classification": operator_classification,
            "requires_inspection": closeout_status == "inspect_blockers",
        },
        "closeout_status": closeout_status,
        "input_artifacts": input_artifacts,
        "incomplete_reasons": incomplete_reasons,
        "labels": list(_LABELS),
        "latest_status_summary": {
            "attempted_count": _int_or_zero(
                _first_value(
                    history_summary.get("attempted_count"),
                    operator_summary.get("attempted_count"),
                )
            ),
            "accepted_count": _int_or_zero(
                _first_value(
                    history_summary.get("accepted_count"),
                    operator_summary.get("accepted_count"),
                )
            ),
            "blocked_count": _int_or_zero(
                _first_value(
                    history_summary.get("blocked_count"),
                    operator_summary.get("blocked_count"),
                )
            ),
            "history_index_status": _first_string(history_summary.get("status")),
            "insufficient_history_count": _int_or_zero(
                _first_value(
                    history_summary.get("insufficient_history_count"),
                    operator_summary.get("insufficient_history_count"),
                )
            ),
            "latest_golden_acceptance_status": latest_golden_acceptance_status,
            "latest_release_gate_status": latest_release_gate_status,
            "operator_summary_status": _first_string(operator_summary.get("status")),
            "validation_finding_count_total": _int_or_zero(
                _first_value(
                    history_summary.get("validation_finding_count_total"),
                    operator_summary.get("validation_finding_count_total"),
                )
            ),
        },
        "next_offline_command": next_offline_command,
        "phase": "V3L",
        "record_type": "closeout_packet",
        "recommended_next_offline_action": recommended_next_offline_action,
        "safety_booleans": dict(_SAFETY_BOOLEANS),
    }

    records = [packet]
    _write_jsonl(Path(config.out), records)
    if config.text_out:
        _write_markdown(Path(config.text_out), packet)

    return records


def _artifact_reference(kind: str, path: Path) -> dict[str, Any]:
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


def _read_jsonl_records(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    findings: list[str] = []
    records: list[dict[str, Any]] = []

    if not path.exists():
        findings.append(f"{_normalize_path(path)}:missing")
        return records, findings
    if not path.is_file():
        findings.append(f"{_normalize_path(path)}:not_file")
        return records, findings

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        findings.append(f"{_normalize_path(path)}:read_error:{type(exc).__name__}")
        return records, findings

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            findings.append(f"{_normalize_path(path)}:line_{line_number}:malformed_json")
            continue
        if not isinstance(payload, dict):
            findings.append(f"{_normalize_path(path)}:line_{line_number}:non_object")
            continue
        records.append(payload)

    if not records:
        findings.append(f"{_normalize_path(path)}:no_records")
    return records, findings


def _incomplete_reasons(
    *,
    input_artifacts: list[dict[str, Any]],
    history_records: list[dict[str, Any]],
    history_findings: list[str],
    operator_records: list[dict[str, Any]],
    operator_findings: list[str],
) -> list[str]:
    by_kind = {artifact["kind"]: artifact for artifact in input_artifacts}
    reasons: list[str] = []

    if not by_kind["history_index"]["exists"]:
        reasons.append("missing_history_index")
    elif history_findings or not history_records:
        reasons.append("unusable_history_index")

    if not by_kind["operator_summary_jsonl"]["exists"]:
        reasons.append("missing_operator_summary")
    elif operator_findings or not operator_records:
        reasons.append("unusable_operator_summary")

    if not by_kind["operator_summary_markdown"]["exists"]:
        reasons.append("missing_operator_summary_markdown")

    return sorted(set(reasons))


def _next_offline_command(
    action: str,
    history_path: Path,
    operator_summary_path: Path,
    operator_summary_md_path: Path,
    out_path: Path,
    text_out_path: Path | None,
) -> str:
    if action == "regenerate_history_index":
        return (
            "python -m algotrader.cli etf-sma-daily-soak-acceptance-history-index "
            "--daily-soak-dir runs/daily_soak "
            f"--out {_normalize_path(history_path)}"
        )
    if action in {"regenerate_operator_summary", "inspect_latest_blocker_evidence"}:
        return (
            "python -m algotrader.cli etf-sma-daily-soak-operator-summary "
            f"--history-index {_normalize_path(history_path)} "
            f"--out {_normalize_path(operator_summary_path)} "
            f"--text-out {_normalize_path(operator_summary_md_path)}"
        )
    if action == "continue_offline_daily_soak":
        return _ACCEPTANCE_COMMAND
    return (
        "python -m algotrader.cli etf-sma-daily-soak-closeout-packet "
        f"--history-index {_normalize_path(history_path)} "
        f"--operator-summary {_normalize_path(operator_summary_path)} "
        f"--operator-summary-md {_normalize_path(operator_summary_md_path)} "
        f"--out {_normalize_path(out_path)}"
        + (f" --text-out {_normalize_path(text_out_path)}" if text_out_path else "")
    )


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
        raise ValidationError(f"Failed to write closeout packet JSONL output: {exc}")


def _write_markdown(path: Path, packet: dict[str, Any]) -> None:
    if path.parent != Path(".") and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    artifact_rows = "\n".join(
        "| {kind} | {path} | {exists} | {size} | {sha} |".format(
            kind=_markdown_cell(str(artifact["kind"])),
            path=_markdown_cell(str(artifact["path"])),
            exists=str(artifact["exists"]).lower(),
            size=(
                str(artifact["size_bytes"])
                if artifact["size_bytes"] is not None
                else "unavailable"
            ),
            sha=artifact["sha256"] or "unavailable",
        )
        for artifact in packet["input_artifacts"]
    )

    latest = packet["latest_status_summary"]
    blockers = packet["blocker_classification"]
    safety_lines = "\n".join(
        f"- {key}: {str(value).lower()}"
        for key, value in sorted(packet["safety_booleans"].items())
    )
    explicit_blockers = (
        ", ".join(blockers["explicit_latest_blockers"])
        if blockers["explicit_latest_blockers"]
        else "none"
    )
    latest_blockers = (
        ", ".join(blockers["latest_blockers"]) if blockers["latest_blockers"] else "none"
    )
    incomplete_reasons = (
        ", ".join(packet["incomplete_reasons"])
        if packet["incomplete_reasons"]
        else "none"
    )

    report = (
        "# V3L Daily Soak Closeout Packet\n\n"
        "## Input Artifacts\n"
        "| kind | path | exists | size_bytes | sha256 |\n"
        "| --- | --- | --- | ---: | --- |\n"
        f"{artifact_rows}\n\n"
        "## Latest Status Summary\n"
        f"- closeout_status: {packet['closeout_status']}\n"
        f"- latest_run_id: {packet['acceptance_run_window']['latest_run_id'] or 'UNKNOWN'}\n"
        f"- start_date: {packet['acceptance_run_window']['start_date'] or 'UNKNOWN'}\n"
        f"- end_date: {packet['acceptance_run_window']['end_date'] or 'UNKNOWN'}\n"
        f"- latest_as_of: {packet['acceptance_run_window']['latest_as_of'] or 'UNKNOWN'}\n"
        f"- latest_golden_acceptance_status: {latest['latest_golden_acceptance_status'] or 'UNKNOWN'}\n"
        f"- latest_release_gate_status: {latest['latest_release_gate_status'] or 'UNKNOWN'}\n"
        f"- operator_summary_status: {latest['operator_summary_status'] or 'UNKNOWN'}\n"
        f"- validation_finding_count_total: {latest['validation_finding_count_total']}\n\n"
        "## Blocker Classification Summary\n"
        f"- requires_inspection: {str(blockers['requires_inspection']).lower()}\n"
        f"- latest_blockers: {latest_blockers}\n"
        f"- explicit_latest_blockers: {explicit_blockers}\n"
        f"- operator_summary_classification: {blockers['operator_summary_classification'] or 'UNKNOWN'}\n"
        f"- incomplete_reasons: {incomplete_reasons}\n\n"
        "## Safety Summary\n"
        f"{safety_lines}\n\n"
        "## Next Offline Command Suggestion\n"
        f"```powershell\n{packet['next_offline_command']}\n```\n\n"
        "This packet does not authorize broker reads, paper submit, broker mutation, "
        "or live trading.\n"
    )

    try:
        path.write_text(report, encoding="utf-8", newline="\n")
    except Exception as exc:
        raise ValidationError(f"Failed to write closeout packet text output: {exc}")


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


def _first_record(records: list[dict[str, Any]], record_type: str) -> dict[str, Any]:
    return next(
        (record for record in records if record.get("record_type") == record_type),
        {},
    )


def _first_string(*values: Any) -> str | None:
    value = _first_value(*values)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_value(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _mapping_from_first(*values: Any) -> dict[str, int]:
    for value in values:
        if isinstance(value, dict):
            return {
                str(key): _int_or_zero(count)
                for key, count in value.items()
                if str(key)
            }
    return {}


def _int_or_zero(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _split_run_id(run_id: str) -> tuple[str | None, str | None]:
    parts = run_id.split("_")
    if len(parts) >= 2 and parts[0] and parts[1]:
        return parts[0], parts[1]
    return None, None


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|")
