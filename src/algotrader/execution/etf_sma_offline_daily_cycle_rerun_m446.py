"""Offline daily rerun command using refreshed M446 adjusted SPY daily-bars.

This module reruns or rewires the ETF/SMA daily cycle chain so it consumes the refreshed
M446 canonical adjusted daily-bars CSV and validates freshness and safety properties.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from algotrader.errors import ValidationError
from .etf_sma_offline_daily_cycle_run import (
    EtfSmaOfflineDailyCycleRunConfig,
    run_etf_sma_offline_daily_cycle_run,
)

__all__ = [
    "EtfSmaOfflineDailyCycleRerunM446Config",
    "EtfSmaOfflineDailyCycleRerunM446WriteResult",
    "build_etf_sma_offline_daily_cycle_rerun_m446",
    "render_etf_sma_offline_daily_cycle_rerun_m446_json",
    "render_etf_sma_offline_daily_cycle_rerun_m446_text",
    "run_etf_sma_offline_daily_cycle_rerun_m446",
    "write_etf_sma_offline_daily_cycle_rerun_m446_jsonl",
]

_MILESTONE = "M447"
_RECORD_TYPE = "etf_sma_offline_daily_cycle_m446_rerun_manifest"
_COMMAND = "etf-sma-offline-daily-cycle-rerun-m446"
_DEFAULT_RUN_ID = "m447_offline_daily_cycle_m446_rerun"
_DEFAULT_SOURCE_M446_MANIFEST = "runs/paper_lab/m446_adjusted_spy_bars_refresh_manifest.jsonl"
_DEFAULT_SOURCE_M446_CSV = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
_DEFAULT_EXPECTED_CSV_SHA256 = "408fd46ef351442cbcb72067e7c7874d92981554fe560b68e3da98492b77db69"
_DEFAULT_ORDER_RECONCILIATION_LOG = "runs/paper_lab/m439_m436_spy_buy_fresh_read_only_reconciliation.jsonl"
_DEFAULT_OUTPUT_JSONL = "runs/paper_lab/m447_offline_daily_cycle_m446_rerun_manifest.jsonl"
_EXPECTED_DATE = "2026-06-08"
_PROFIT_CLAIM = "none"

_SAFETY_FIELDS = (
    "paper_action_authorized",
    "submit_authorized",
    "paper_submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)


@dataclass(frozen=True, slots=True)
class EtfSmaOfflineDailyCycleRerunM446Config:
    """Explicit local inputs for the M447 rerun."""

    run_id: str = _DEFAULT_RUN_ID
    source_m446_manifest_path: Path | str = _DEFAULT_SOURCE_M446_MANIFEST
    source_m446_canonical_csv_path: Path | str = _DEFAULT_SOURCE_M446_CSV
    expected_m446_csv_sha256: str = _DEFAULT_EXPECTED_CSV_SHA256
    order_reconciliation_log: Path | str = _DEFAULT_ORDER_RECONCILIATION_LOG
    validated_at: str = "2026-06-08T20:33:47+00:00"
    expected_latest_bar_date: str = _EXPECTED_DATE
    output_jsonl: Path | str = _DEFAULT_OUTPUT_JSONL

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "source_m446_manifest_path",
            _required_path(self.source_m446_manifest_path, "source_m446_manifest_path"),
        )
        object.__setattr__(
            self,
            "source_m446_canonical_csv_path",
            _required_path(self.source_m446_canonical_csv_path, "source_m446_canonical_csv_path"),
        )
        object.__setattr__(
            self,
            "expected_m446_csv_sha256",
            _required_string(self.expected_m446_csv_sha256, "expected_m446_csv_sha256"),
        )
        object.__setattr__(
            self,
            "order_reconciliation_log",
            _required_path(self.order_reconciliation_log, "order_reconciliation_log"),
        )
        object.__setattr__(
            self,
            "validated_at",
            _required_string(self.validated_at, "validated_at"),
        )
        object.__setattr__(
            self,
            "expected_latest_bar_date",
            _required_string(self.expected_latest_bar_date, "expected_latest_bar_date"),
        )
        object.__setattr__(
            self,
            "output_jsonl",
            _required_path(self.output_jsonl, "output_jsonl"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaOfflineDailyCycleRerunM446WriteResult:
    """Write metadata for a single M447 rerun record."""

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


def run_etf_sma_offline_daily_cycle_rerun_m446(
    config: EtfSmaOfflineDailyCycleRerunM446Config,
) -> dict[str, object]:
    """Execute the offline M447 Daily Cycle Rerun flow and write the manifest."""
    payload = build_etf_sma_offline_daily_cycle_rerun_m446(config)
    write_etf_sma_offline_daily_cycle_rerun_m446_jsonl(payload, config.output_jsonl)
    return payload


def build_etf_sma_offline_daily_cycle_rerun_m446(
    config: EtfSmaOfflineDailyCycleRerunM446Config,
) -> dict[str, object]:
    """Build the M447 rerun manifest record, failing closed if validation checks fail."""
    # 1. Verify M446 manifest exists, read it, and compute its SHA256
    manifest_path = Path(config.source_m446_manifest_path)
    if not manifest_path.exists():
        raise ValidationError(f"M446 manifest file missing: {manifest_path}")
    if not manifest_path.is_file():
        raise ValidationError(f"M446 manifest path is not a file: {manifest_path}")

    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

    # Parse M446 manifest
    manifest_lines = [
        line.strip() for line in manifest_bytes.decode("utf-8").splitlines() if line.strip()
    ]
    if len(manifest_lines) != 1:
        raise ValidationError(f"M446 manifest must contain exactly 1 JSON record, found {len(manifest_lines)}")

    try:
        m446_record = json.loads(manifest_lines[0])
    except json.JSONDecodeError as exc:
        raise ValidationError(f"M446 manifest is not valid JSONL: {exc}") from exc

    if not isinstance(m446_record, Mapping):
        raise ValidationError("M446 manifest record is not a JSON object")

    # 2. Verify M446 canonical CSV exists and compute its SHA256
    csv_path = Path(config.source_m446_canonical_csv_path)
    if not csv_path.exists():
        raise ValidationError(f"M446 canonical CSV missing: {csv_path}")
    if not csv_path.is_file():
        raise ValidationError(f"M446 canonical CSV path is not a file: {csv_path}")

    csv_bytes = csv_path.read_bytes()
    csv_sha256 = hashlib.sha256(csv_bytes).hexdigest()

    # Validate M446 manifest CSV properties
    m446_csv_sha256 = m446_record.get("refreshed_canonical_csv_sha256")
    if not m446_csv_sha256:
        raise ValidationError("M446 manifest does not contain 'refreshed_canonical_csv_sha256'")

    # 3. CSV SHA256 must match the manifest value
    if csv_sha256 != m446_csv_sha256:
        raise ValidationError(
            f"M446 CSV SHA256 mismatch: calculated {csv_sha256}, manifest has {m446_csv_sha256}"
        )

    # 4. CSV SHA256 must match the expected/configured hash
    if csv_sha256 != config.expected_m446_csv_sha256:
        raise ValidationError(
            f"M446 CSV SHA256 mismatch: calculated {csv_sha256}, expected {config.expected_m446_csv_sha256}"
        )

    # 5. Verify expected latest bar date
    if config.expected_latest_bar_date != _EXPECTED_DATE:
        raise ValidationError(
            f"expected_latest_bar_date must be {_EXPECTED_DATE}, got {config.expected_latest_bar_date}"
        )

    # Validate dates in the manifest and CSV
    m446_latest_date = m446_record.get("latest_local_bar_date")
    if m446_latest_date != _EXPECTED_DATE:
        raise ValidationError(
            f"M446 latest_local_bar_date is not {_EXPECTED_DATE}, got {m446_latest_date}"
        )

    # Extract date columns from the CSV and check the latest date
    latest_local_bar_date = _get_latest_bar_date_from_csv(csv_path)
    if latest_local_bar_date != _EXPECTED_DATE:
        raise ValidationError(
            f"CSV latest date is not {_EXPECTED_DATE}, got {latest_local_bar_date}"
        )

    # 6. Verify that order reconciliation log is present
    recon_path = Path(config.order_reconciliation_log)
    if not recon_path.exists():
        raise ValidationError(f"Order reconciliation log missing: {recon_path}")

    # 7. Run the daily cycle in a temp directory using the refreshed daily-bars CSV
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        temp_readiness = temp_dir_path / "m441_temp.jsonl"
        temp_validation = temp_dir_path / "m442_temp.jsonl"
        temp_summary = temp_dir_path / "m443_temp.jsonl"
        temp_manifest = temp_dir_path / "m444_temp.jsonl"

        try:
            cycle_manifest = run_etf_sma_offline_daily_cycle_run(
                EtfSmaOfflineDailyCycleRunConfig(
                    run_id=config.run_id,
                    validated_at=config.validated_at,
                    daily_bars_csv=csv_path,
                    order_reconciliation_log=recon_path,
                    readiness_output_jsonl=temp_readiness,
                    validation_output_jsonl=temp_validation,
                    summary_output_jsonl=temp_summary,
                    manifest_output_jsonl=temp_manifest,
                )
            )
        except Exception as exc:
            raise ValidationError(f"Rerun chain execution failed: {exc}") from exc

    # 8. Check that all required fields from the rerun chain are present and valid
    cycle_decision = cycle_manifest.get("summary_cycle_decision") or cycle_manifest.get("readiness_cycle_decision")
    posture = cycle_manifest.get("posture")
    sma50 = cycle_manifest.get("sma50")
    sma200 = cycle_manifest.get("sma200")
    usable_spy_bars = cycle_manifest.get("usable_spy_bars")
    recommended_operator_action = cycle_manifest.get("recommended_operator_action")

    missing_fields = []
    if not cycle_decision:
        missing_fields.append("cycle_decision")
    if not posture:
        missing_fields.append("posture")
    if sma50 in (None, ""):
        missing_fields.append("sma50")
    if sma200 in (None, ""):
        missing_fields.append("sma200")
    if usable_spy_bars in (None, ""):
        missing_fields.append("usable_spy_bars")
    if not recommended_operator_action:
        missing_fields.append("recommended_operator_action")

    if missing_fields:
        raise ValidationError(f"Rerun chain failed to produce required fields: {', '.join(missing_fields)}")

    # 9. Verify safety flags on rerun manifest and force all to be False
    for field_name in _SAFETY_FIELDS:
        if cycle_manifest.get(field_name) is not False:
            raise ValidationError(f"Safety constraint violation: rerun manifest field '{field_name}' is not False")

    if cycle_manifest.get("profit_claim") != _PROFIT_CLAIM:
        raise ValidationError(f"Safety constraint violation: profit_claim must be '{_PROFIT_CLAIM}'")

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": config.run_id,
        "source_m446_manifest_path": str(config.source_m446_manifest_path),
        "source_m446_manifest_sha256": manifest_sha256,
        "source_m446_canonical_csv_path": str(config.source_m446_canonical_csv_path),
        "source_m446_canonical_csv_sha256": csv_sha256,
        "expected_latest_bar_date": config.expected_latest_bar_date,
        "latest_local_bar_date": latest_local_bar_date,
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "cycle_decision": str(cycle_decision),
        "posture": str(posture),
        "sma50": str(sma50),
        "sma200": str(sma200),
        "usable_spy_bars": int(usable_spy_bars),
        "recommended_operator_action": str(recommended_operator_action),
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


def _get_latest_bar_date_from_csv(path: Path) -> str:
    """Parse CSV to find the latest date in the 'date' column."""
    import csv
    with path.open("r", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        date_col = None
        if reader.fieldnames:
            for col in reader.fieldnames:
                if col.strip().lower() == "date":
                    date_col = col
                    break
        if not date_col:
            raise ValidationError(f"CSV date column missing in {path}")

        latest_date = None
        for row in reader:
            val = row.get(date_col)
            if not val or not val.strip():
                continue
            date_str = val.strip()
            if latest_date is None or date_str > latest_date:
                latest_date = date_str

        if not latest_date:
            raise ValidationError(f"No valid rows/dates found in CSV {path}")
        return latest_date


def render_etf_sma_offline_daily_cycle_rerun_m446_json(
    payload: Mapping[str, object],
) -> str:
    """Render rerun manifest record as compact JSON."""
    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_offline_daily_cycle_rerun_m446_text(
    payload: Mapping[str, object],
) -> str:
    """Render a clean text summary of the M447 rerun manifest."""
    return "\n".join(
        (
            "ETF/SMA offline daily cycle rerun (M446 SPY CSV)",
            f"milestone: {payload.get('milestone', '')}",
            f"run_id: {payload.get('run_id', '')}",
            f"expected_latest_bar_date: {payload.get('expected_latest_bar_date', '')}",
            f"latest_local_bar_date: {payload.get('latest_local_bar_date', '')}",
            f"freshness_state: {payload.get('freshness_state', '')}",
            f"usable_spy_bars: {payload.get('usable_spy_bars', '')}",
            f"sma50: {payload.get('sma50', '')}",
            f"sma200: {payload.get('sma200', '')}",
            f"posture: {payload.get('posture', '')}",
            f"cycle_decision: {payload.get('cycle_decision', '')}",
            f"recommended_operator_action: {payload.get('recommended_operator_action', '')}",
            f"submitted: {str(payload.get('submitted', '')).lower()}",
            f"mutated: {str(payload.get('mutated', '')).lower()}",
            f"broker_action_performed: {str(payload.get('broker_action_performed', '')).lower()}",
        )
    )


def write_etf_sma_offline_daily_cycle_rerun_m446_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaOfflineDailyCycleRerunM446WriteResult:
    """Write exactly one M447 rerun manifest record, overwriting previous contents."""
    path = Path(output_path)
    if path.parent != Path(".") and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    line = render_etf_sma_offline_daily_cycle_rerun_m446_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)

    return EtfSmaOfflineDailyCycleRerunM446WriteResult(
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
