"""Offline daily rollup for M448 refreshed current-cycle.

This module reads one explicit local M447 rerun manifest record, validates the
required invariants, and writes one M448 current-cycle rollup record stating
observe_hold_noop. It does not access broker SDKs, credentials, network,
paper profile, or mutation paths.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "EtfSmaRefreshedCurrentCycleRollupM448Config",
    "EtfSmaRefreshedCurrentCycleRollupM448WriteResult",
    "build_etf_sma_refreshed_current_cycle_rollup_m448",
    "render_etf_sma_refreshed_current_cycle_rollup_m448_json",
    "render_etf_sma_refreshed_current_cycle_rollup_m448_text",
    "run_etf_sma_refreshed_current_cycle_rollup_m448",
    "write_etf_sma_refreshed_current_cycle_rollup_m448_jsonl",
]

_MILESTONE = "M448"
_RECORD_TYPE = "m448_refreshed_current_cycle_rollup"
_COMMAND = "etf-sma-refreshed-current-cycle-rollup-m448"
_DEFAULT_RUN_ID = "m448_refreshed_current_cycle_rollup"
_DEFAULT_SOURCE_M447_MANIFEST = "runs/paper_lab/m447_offline_daily_cycle_m446_rerun_manifest.jsonl"
_DEFAULT_OUTPUT_JSONL = "runs/paper_lab/m448_refreshed_current_cycle_rollup.jsonl"
_EXPECTED_DATE = "2026-06-08"
_EXPECTED_CSV_SHA256 = "408fd46ef351442cbcb72067e7c7874d92981554fe560b68e3da98492b77db69"
_PROFIT_CLAIM = "none"

_SAFETY_FIELDS_TO_VALIDATE = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)


@dataclass(frozen=True, slots=True)
class EtfSmaRefreshedCurrentCycleRollupM448Config:
    """Explicit local inputs for the M448 rollup."""

    run_id: str = _DEFAULT_RUN_ID
    source_m447_manifest_path: Path | str = _DEFAULT_SOURCE_M447_MANIFEST
    expected_m447_latest_bar_date: str = _EXPECTED_DATE
    expected_m446_csv_sha256: str = _EXPECTED_CSV_SHA256
    output_jsonl: Path | str = _DEFAULT_OUTPUT_JSONL

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "source_m447_manifest_path",
            _required_path(self.source_m447_manifest_path, "source_m447_manifest_path"),
        )
        object.__setattr__(
            self,
            "expected_m447_latest_bar_date",
            _required_string(self.expected_m447_latest_bar_date, "expected_m447_latest_bar_date"),
        )
        object.__setattr__(
            self,
            "expected_m446_csv_sha256",
            _required_string(self.expected_m446_csv_sha256, "expected_m446_csv_sha256"),
        )
        object.__setattr__(
            self,
            "output_jsonl",
            _required_path(self.output_jsonl, "output_jsonl"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaRefreshedCurrentCycleRollupM448WriteResult:
    """Write metadata for a single M448 rollup record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool

    def __post_init__(self) -> None:
        if self.record_count != 1:
            raise ValidationError("record_count must be exactly 1.")
        if self.bytes_written <= 0:
            raise ValidationError("bytes_written must be positive.")
        if not self.newline_terminated:
            raise ValidationError("Output must be newline terminated.")


def run_etf_sma_refreshed_current_cycle_rollup_m448(
    config: EtfSmaRefreshedCurrentCycleRollupM448Config,
) -> dict[str, object]:
    """Execute the M448 Rollup flow and write the rollup file."""
    payload = build_etf_sma_refreshed_current_cycle_rollup_m448(config)
    write_etf_sma_refreshed_current_cycle_rollup_m448_jsonl(payload, config.output_jsonl)
    return payload


def build_etf_sma_refreshed_current_cycle_rollup_m448(
    config: EtfSmaRefreshedCurrentCycleRollupM448Config,
) -> dict[str, object]:
    """Build the M448 rollup record, validating invariants and failing closed."""
    manifest_path = Path(config.source_m447_manifest_path)
    if not manifest_path.exists():
        raise ValidationError(f"M447 manifest file missing: {manifest_path}")
    if not manifest_path.is_file():
        raise ValidationError(f"M447 manifest path is not a file: {manifest_path}")

    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

    manifest_lines = [
        line.strip() for line in manifest_bytes.decode("utf-8").splitlines() if line.strip()
    ]
    if len(manifest_lines) != 1:
        raise ValidationError(f"M447 manifest must contain exactly 1 JSON record, found {len(manifest_lines)}")

    try:
        m447_record = json.loads(manifest_lines[0])
    except json.JSONDecodeError as exc:
        raise ValidationError(f"M447 manifest is not valid JSONL: {exc}") from exc

    if not isinstance(m447_record, Mapping):
        raise ValidationError("M447 manifest record is not a JSON object")

    # Validate all requested fields exactly:
    # 1. source_m446_canonical_csv_sha256
    m446_csv_sha256 = m447_record.get("source_m446_canonical_csv_sha256")
    if m446_csv_sha256 != config.expected_m446_csv_sha256:
        raise ValidationError(
            f"M447 source_m446_canonical_csv_sha256 mismatch: manifest has {m446_csv_sha256}, "
            f"expected {config.expected_m446_csv_sha256}"
        )

    # 2. expected_latest_bar_date
    expected_latest_bar_date = m447_record.get("expected_latest_bar_date")
    if expected_latest_bar_date != config.expected_m447_latest_bar_date:
        raise ValidationError(
            f"M447 expected_latest_bar_date mismatch: manifest has {expected_latest_bar_date}, "
            f"expected {config.expected_m447_latest_bar_date}"
        )

    # 3. latest_local_bar_date
    latest_local_bar_date = m447_record.get("latest_local_bar_date")
    if latest_local_bar_date != config.expected_m447_latest_bar_date:
        raise ValidationError(
            f"M447 latest_local_bar_date mismatch: manifest has {latest_local_bar_date}, "
            f"expected {config.expected_m447_latest_bar_date}"
        )

    # 4. freshness_state
    freshness_state = m447_record.get("freshness_state")
    if freshness_state != "accepted_current_adjusted_bars":
        raise ValidationError(
            f"M447 freshness_state mismatch: manifest has {freshness_state}, "
            f"expected 'accepted_current_adjusted_bars'"
        )

    # 5. freshness_blockers
    freshness_blockers = m447_record.get("freshness_blockers")
    if not isinstance(freshness_blockers, list) or len(freshness_blockers) > 0:
        raise ValidationError(
            f"M447 freshness_blockers is not empty: {freshness_blockers}"
        )

    # 6. cycle_decision
    cycle_decision = m447_record.get("cycle_decision")
    if cycle_decision != "hold/noop":
        raise ValidationError(
            f"M447 cycle_decision mismatch: manifest has {cycle_decision}, expected 'hold/noop'"
        )

    # 7. recommended_operator_action
    recommended_operator_action = m447_record.get("recommended_operator_action")
    if recommended_operator_action != "observe_hold_noop":
        raise ValidationError(
            f"M447 recommended_operator_action mismatch: manifest has {recommended_operator_action}, "
            f"expected 'observe_hold_noop'"
        )

    # 8. safety booleans
    for field_name in _SAFETY_FIELDS_TO_VALIDATE:
        if m447_record.get(field_name) is not False:
            raise ValidationError(f"Safety constraint violation: M447 field '{field_name}' is not False")

    # 9. profit_claim
    if m447_record.get("profit_claim") != _PROFIT_CLAIM:
        raise ValidationError(f"Safety constraint violation: profit_claim must be '{_PROFIT_CLAIM}'")

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": config.run_id,
        "source_m447_manifest_path": str(config.source_m447_manifest_path),
        "source_m447_manifest_sha256": manifest_sha256,
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": config.expected_m447_latest_bar_date,
        "latest_local_bar_date": config.expected_m447_latest_bar_date,
        "posture": str(m447_record.get("posture", "risk_on")),
        "cycle_decision": "hold/noop",
        "current_action": "observe_hold_noop",
        "recommended_operator_action": "observe_hold_noop",
        "paper_action_authorized": False,
        "submit_authorized": False,
        "paper_submit_authorized": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": _PROFIT_CLAIM,
    }


def render_etf_sma_refreshed_current_cycle_rollup_m448_json(
    payload: Mapping[str, object],
) -> str:
    """Render rollup record as compact JSON."""
    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_refreshed_current_cycle_rollup_m448_text(
    payload: Mapping[str, object],
) -> str:
    """Render a clean text summary of the M448 rollup."""
    return "\n".join(
        (
            "ETF/SMA offline current cycle rollup (M448)",
            f"milestone: {payload.get('milestone', '')}",
            f"run_id: {payload.get('run_id', '')}",
            f"expected_latest_bar_date: {payload.get('expected_latest_bar_date', '')}",
            f"latest_local_bar_date: {payload.get('latest_local_bar_date', '')}",
            f"freshness_state: {payload.get('freshness_state', '')}",
            f"posture: {payload.get('posture', '')}",
            f"cycle_decision: {payload.get('cycle_decision', '')}",
            f"current_action: {payload.get('current_action', '')}",
            f"recommended_operator_action: {payload.get('recommended_operator_action', '')}",
            f"submitted: {str(payload.get('submitted', '')).lower()}",
            f"mutated: {str(payload.get('mutated', '')).lower()}",
            f"broker_action_performed: {str(payload.get('broker_action_performed', '')).lower()}",
        )
    )


def write_etf_sma_refreshed_current_cycle_rollup_m448_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaRefreshedCurrentCycleRollupM448WriteResult:
    """Write exactly one M448 rollup record, overwriting previous contents."""
    path = Path(output_path)
    if path.parent != Path(".") and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    line = render_etf_sma_refreshed_current_cycle_rollup_m448_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)

    return EtfSmaRefreshedCurrentCycleRollupM448WriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=True,
    )


def _required_string(value: object, field_name: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _required_path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    else:
        text = str(value).strip() if value is not None else ""
        if not text:
            raise ValidationError(f"{field_name} is required.")
        path = Path(text)
    return path


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list) or isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value
