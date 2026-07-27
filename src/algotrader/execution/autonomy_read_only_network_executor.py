"""Autonomy read-only network execution seam for SPY market-data refresh.

This module provides a safety-bounded, audited execution seam for running the
authorized Tiingo read-only market-data refresh to seed the SPY soak layer.
It is structurally disjoint from autonomy_offline_executor.py and performs
zero broker/capital actions.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
import hashlib
import json
import os
from pathlib import Path
import sys
import time as _time
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_adjusted_spy_data_refresh import (
    ETFAdjustedDataRefreshConfig,
    load_tiingo_api_key_from_dotenv,
    run_spy_adjusted_data_refresh,
)
from algotrader.execution.exchange_session import NyseExchangeSessionCalendar
from algotrader.execution.live_capital_interlock import (
    evaluate_live_capital_interlock,
)

__all__ = [
    "AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST",
    "main",
    "run_autonomy_read_only_network_executor",
]

AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST = {
    "run_authorized_read_only_market_data_refresh_to_seed_soak": (
        "python -m algotrader.execution.autonomy_read_only_network_executor"
        " --as-of <ISO8601_UTC> [--apply] --format json"
    )
}

_ACTION_TOKEN = "run_authorized_read_only_market_data_refresh_to_seed_soak"
_RECORD_TYPE = "autonomy_network_execution_ledger_event"
_SCHEMA_VERSION = 1
_CUTOFF_TIME = time(20, 10, 0)
_NY_TZ = ZoneInfo("America/New_York")

_REL_OUTPUT_CSV = Path(".data/operator_inputs/spy_tiingo_adjusted_refresh_latest.csv")
_REL_CANONICAL_CSV = Path("runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv")
_REL_RUN_LOG = Path("runs/paper_lab/m446_adjusted_spy_bars_refresh_manifest.jsonl")
_REL_RAW_RESPONSE = Path("runs/paper_lab/tiingo_spy_adjusted_raw_latest.json")
_REL_SOAK_LEDGER = Path("runs/paper_lab/spy_adjusted_market_data_soak_ledger.jsonl")
_REL_SOAK_REPORT = Path("runs/paper_lab/spy_adjusted_market_data_soak_report.json")
_REL_LEDGER_PATH = Path("runs/autonomy_network_executor/ledger.jsonl")
_REL_LOCK_PATH = Path("runs/autonomy_network_executor/ledger.lock")

_CANONICAL_REL_PATHS = (
    _REL_OUTPUT_CSV,
    _REL_CANONICAL_CSV,
    _REL_RUN_LOG,
    _REL_RAW_RESPONSE,
    _REL_SOAK_LEDGER,
    _REL_SOAK_REPORT,
    _REL_LEDGER_PATH,
    _REL_LOCK_PATH,
)


class _CredentialProvider:

    def __init__(self, canonical_env_path: Path) -> None:
        self._cached: str | None = load_tiingo_api_key_from_dotenv(
            canonical_env_path, token_env_var="TIINGO_API_KEY"
        )

    @property
    def available(self) -> bool:
        return self._cached is not None and bool(self._cached.strip())

    def lookup(self, name: str) -> str | None:
        if name == "TIINGO_API_KEY":
            return self._cached
        return None


def _find_canonical_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src" / "algotrader").exists():
        return cwd
    raise ValidationError("noncanonical_target")


def _validate_canonical_paths(root: Path) -> tuple[Path, ...]:
    resolved_paths: list[Path] = []
    for rel_path in _CANONICAL_REL_PATHS:
        abs_path = (root / rel_path).resolve()
        try:
            abs_path.relative_to(root)
        except ValueError as exc:
            raise ValidationError("noncanonical_target") from exc
        resolved_paths.append(abs_path)
    return tuple(resolved_paths)


def _validate_canonical_env_path(root: Path) -> Path:
    env_path = (root / ".env").resolve()
    if env_path.parent != root:
        raise ValidationError("credential_path_noncanonical")
    return env_path


def _parse_as_of(as_of_raw: str) -> datetime:
    if not as_of_raw or not isinstance(as_of_raw, str):
        raise ValidationError("as_of_invalid")
    try:
        dt = datetime.fromisoformat(as_of_raw)
    except ValueError as exc:
        raise ValidationError("as_of_invalid") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt


def _resolve_expected_session(as_of_utc: datetime) -> date:
    as_of_ny = as_of_utc.astimezone(_NY_TZ)
    ny_date = as_of_ny.date()
    calendar = NyseExchangeSessionCalendar()
    session = calendar.session_for_date(ny_date)
    if session is not None and as_of_ny.time() >= _CUTOFF_TIME:
        return ny_date
    eval_time = datetime.combine(ny_date - timedelta(days=1), time(23, 59, 59), tzinfo=_NY_TZ)
    latest = calendar.latest_completed_session_on_or_before(eval_time)
    if latest is None:
        raise ValidationError("as_of_invalid")
    return latest.session_date


def _check_soak_report_qualified(soak_report_path: Path, session_id: str) -> bool:
    if not soak_report_path.exists() or not soak_report_path.is_file():
        return False
    try:
        data = json.loads(soak_report_path.read_text(encoding="utf-8"))
        qualifying = data.get("qualifying_session_dates", [])
        if isinstance(qualifying, list):
            return session_id in qualifying
    except (OSError, json.JSONDecodeError):
        pass
    return False


def _acquire_lock(lock_path: Path, timeout_seconds: float = 5.0) -> Any:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    f = open(lock_path, "a+b")
    f.seek(0, os.SEEK_END)
    if f.tell() == 0:
        f.write(b"0")
        f.flush()
    start_time = _time.monotonic()
    while True:
        try:
            f.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return f
        except OSError:
            if _time.monotonic() - start_time >= timeout_seconds:
                f.close()
                return None
            _time.sleep(0.05)


def _release_lock(lock_file: Any) -> None:
    if lock_file is None:
        return
    try:
        lock_file.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    finally:
        try:
            lock_file.close()
        except OSError:
            pass


def _read_and_validate_ledger(ledger_path: Path, session_id: str) -> tuple[int, list[dict[str, Any]]]:
    if not ledger_path.exists() or not ledger_path.is_file():
        return 0, []
    records: list[dict[str, Any]] = []
    reservation_ids: set[str] = set()
    try:
        content = ledger_path.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), start=1):
            line_str = line.strip()
            if not line_str:
                continue
            record = json.loads(line_str)
            if not isinstance(record, dict):
                raise ValidationError("ledger_corrupt")
            if (
                record.get("record_type") != _RECORD_TYPE
                or record.get("schema_version") != _SCHEMA_VERSION
                or record.get("action_token") != _ACTION_TOKEN
            ):
                raise ValidationError("ledger_corrupt")
            status = record.get("ledger_status")
            if status not in ("pending", "completed", "refused"):
                raise ValidationError("ledger_corrupt")
            records.append(record)
            rec_session = record.get("session_id")
            if rec_session == session_id and status in ("pending", "completed"):
                res_id = record.get("reservation_id")
                if isinstance(res_id, str) and res_id:
                    reservation_ids.add(res_id)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise ValidationError("ledger_corrupt") from exc
    return len(reservation_ids), records


def _append_ledger_event(ledger_path: Path, event: dict[str, Any]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event) + "\n"
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def _build_base_ledger_event(
    *,
    session_id: str,
    as_of: str,
    attempt_number: int,
    run_id: str,
    reservation_id: str | None,
    ledger_status: str,
    exit_code: int | None,
    adapter_refresh_state: str | None,
    network_access_attempted: bool,
    interlock_verdict: dict[str, Any] | None,
    credential_present: bool | None,
    refusal_category: str | None,
    attempt_budget_exhausted: bool = False,
) -> dict[str, Any]:
    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "action_token": _ACTION_TOKEN,
        "apply": True,
        "session_already_qualified": False,
        "session_id": session_id,
        "as_of": as_of,
        "attempt_number": attempt_number,
        "run_id": run_id,
        "reservation_id": reservation_id,
        "ledger_status": ledger_status,
        "exit_code": exit_code,
        "adapter_refresh_state": adapter_refresh_state,
        "network_access_attempted": network_access_attempted,
        "interlock_verdict": interlock_verdict,
        "credential_present": credential_present,
        "refusal_category": refusal_category,
        "attempt_budget_exhausted": attempt_budget_exhausted,
        "broker_access_attempted": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_trading_performed": False,
        "live_authorized": False,
        "profit_claim": "none",
    }


def run_autonomy_read_only_network_executor(
    *,
    as_of: str,
    apply: bool = False,
    format: str = "json",
) -> dict[str, Any]:
    try:
        root = _find_canonical_root()
    except ValidationError:
        return {"action_token": _ACTION_TOKEN, "refusal_category": "noncanonical_target", "exit_code": 2}

    try:
        paths = _validate_canonical_paths(root)
    except ValidationError:
        return {"action_token": _ACTION_TOKEN, "refusal_category": "noncanonical_target", "exit_code": 2}

    (
        output_csv,
        canonical_csv,
        run_log,
        raw_response_path,
        soak_ledger,
        soak_report,
        ledger_path,
        lock_path,
    ) = paths

    try:
        canonical_env_path = _validate_canonical_env_path(root)
    except ValidationError:
        return {"action_token": _ACTION_TOKEN, "refusal_category": "credential_path_noncanonical", "exit_code": 2}

    try:
        as_of_dt = _parse_as_of(as_of)
        expected_session = _resolve_expected_session(as_of_dt)
        session_id = expected_session.isoformat()
    except ValidationError:
        return {"action_token": _ACTION_TOKEN, "refusal_category": "as_of_invalid", "exit_code": 2}

    as_of_str = as_of_dt.isoformat()

    # Step 5: Short-circuit check
    if _check_soak_report_qualified(soak_report, session_id):
        return {
            "action_token": _ACTION_TOKEN,
            "apply": apply,
            "session_id": session_id,
            "as_of": as_of_str,
            "session_already_qualified": True,
            "network_access_attempted": False,
            "interlock_verdict": None,
            "exit_code": 0,
        }

    # Dry-run mode
    if not apply:
        verdict = evaluate_live_capital_interlock(os.environ)
        verdict_dict = verdict.to_dict()
        return {
            "action_token": _ACTION_TOKEN,
            "apply": False,
            "session_id": session_id,
            "as_of": as_of_str,
            "session_already_qualified": False,
            "apply_eligible": verdict.paper_boundary_ok,
            "network_access_attempted": False,
            "interlock_verdict": verdict_dict,
            "exit_code": 1,
        }

    # Apply mode: acquire lock
    lock_file = _acquire_lock(lock_path, timeout_seconds=5.0)
    if lock_file is None:
        return {
            "action_token": _ACTION_TOKEN,
            "apply": True,
            "session_id": session_id,
            "as_of": as_of_str,
            "refusal_category": "ledger_lock_unavailable",
            "exit_code": 2,
        }

    try:
        # Step 7: Ledger validation and budget check
        try:
            prior_count, _ = _read_and_validate_ledger(ledger_path, session_id)
        except ValidationError:
            return {
                "action_token": _ACTION_TOKEN,
                "apply": True,
                "session_id": session_id,
                "as_of": as_of_str,
                "refusal_category": "ledger_corrupt",
                "exit_code": 2,
            }

        attempt_number = prior_count + 1
        run_id = f"network-{session_id}-{attempt_number}"

        if prior_count >= 4:
            event = _build_base_ledger_event(
                session_id=session_id,
                as_of=as_of_str,
                attempt_number=attempt_number,
                run_id=run_id,
                reservation_id=None,
                ledger_status="refused",
                exit_code=2,
                adapter_refresh_state=None,
                network_access_attempted=False,
                interlock_verdict=None,
                credential_present=None,
                refusal_category="session_attempt_budget_exhausted",
                attempt_budget_exhausted=True,
            )
            _append_ledger_event(ledger_path, event)
            return {
                "action_token": _ACTION_TOKEN,
                "apply": True,
                "session_id": session_id,
                "as_of": as_of_str,
                "attempt_number": attempt_number,
                "run_id": run_id,
                "refusal_category": "session_attempt_budget_exhausted",
                "exit_code": 2,
            }

        # Step 8: Mandatory live-capital interlock preflight
        verdict = evaluate_live_capital_interlock(os.environ)
        verdict_dict = verdict.to_dict()

        if not verdict.paper_boundary_ok:
            event = _build_base_ledger_event(
                session_id=session_id,
                as_of=as_of_str,
                attempt_number=attempt_number,
                run_id=run_id,
                reservation_id=None,
                ledger_status="refused",
                exit_code=2,
                adapter_refresh_state=None,
                network_access_attempted=False,
                interlock_verdict=verdict_dict,
                credential_present=None,
                refusal_category="live_capital_interlock_blocked",
            )
            _append_ledger_event(ledger_path, event)
            return {
                "action_token": _ACTION_TOKEN,
                "apply": True,
                "session_id": session_id,
                "as_of": as_of_str,
                "attempt_number": attempt_number,
                "run_id": run_id,
                "interlock_verdict": verdict_dict,
                "refusal_category": "live_capital_interlock_blocked",
                "exit_code": 2,
            }

        # Step 9: Credential presence check
        provider = _CredentialProvider(canonical_env_path)
        if not provider.available:
            event = _build_base_ledger_event(
                session_id=session_id,
                as_of=as_of_str,
                attempt_number=attempt_number,
                run_id=run_id,
                reservation_id=None,
                ledger_status="refused",
                exit_code=2,
                adapter_refresh_state=None,
                network_access_attempted=False,
                interlock_verdict=verdict_dict,
                credential_present=False,
                refusal_category="token_not_available",
            )
            _append_ledger_event(ledger_path, event)
            return {
                "action_token": _ACTION_TOKEN,
                "apply": True,
                "session_id": session_id,
                "as_of": as_of_str,
                "attempt_number": attempt_number,
                "run_id": run_id,
                "interlock_verdict": verdict_dict,
                "refusal_category": "token_not_available",
                "exit_code": 2,
            }

        # Step 10: Reservation event & adapter execution
        res_event = _build_base_ledger_event(
            session_id=session_id,
            as_of=as_of_str,
            attempt_number=attempt_number,
            run_id=run_id,
            reservation_id=run_id,
            ledger_status="pending",
            exit_code=None,
            adapter_refresh_state=None,
            network_access_attempted=False,
            interlock_verdict=verdict_dict,
            credential_present=True,
            refusal_category=None,
        )
        _append_ledger_event(ledger_path, res_event)

        config = ETFAdjustedDataRefreshConfig(
            provider="tiingo",
            symbol="SPY",
            mode="live_market_data_fetch",
            live_fetch_authorized=True,
            output_csv=output_csv,
            canonical_csv=canonical_csv,
            run_log=run_log,
            raw_response_path=raw_response_path,
            soak_ledger=soak_ledger,
            soak_report=soak_report,
            soak_required_sessions=5,
            start_date="auto",
            revision_lookback_days=10,
            token_env_var="TIINGO_API_KEY",
            expected_latest_bar_date=session_id,
            run_id=run_id,
        )

        manifest = run_spy_adjusted_data_refresh(
            config,
            token_lookup=provider.lookup,
        )

        adapter_state = str(manifest.get("refresh_state", "unknown"))
        exit_code = 0 if adapter_state == "accepted" else 1

        comp_event = _build_base_ledger_event(
            session_id=session_id,
            as_of=as_of_str,
            attempt_number=attempt_number,
            run_id=run_id,
            reservation_id=run_id,
            ledger_status="completed",
            exit_code=exit_code,
            adapter_refresh_state=adapter_state,
            network_access_attempted=True,
            interlock_verdict=verdict_dict,
            credential_present=True,
            refusal_category=None,
        )
        _append_ledger_event(ledger_path, comp_event)

        return {
            "action_token": _ACTION_TOKEN,
            "apply": True,
            "session_id": session_id,
            "as_of": as_of_str,
            "attempt_number": attempt_number,
            "run_id": run_id,
            "adapter_refresh_state": adapter_state,
            "network_access_attempted": True,
            "interlock_verdict": verdict_dict,
            "exit_code": exit_code,
        }

    finally:
        _release_lock(lock_file)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Autonomy read-only network execution seam for SPY market-data refresh.",
        allow_abbrev=False,
    )
    parser.add_argument("--as-of", required=True, help="ISO-8601 UTC timestamp")
    parser.add_argument("--apply", action="store_true", default=False, help="Execute apply mode")
    parser.add_argument("--format", choices=["json"], default="json", help="Output format")

    args, unknown = parser.parse_known_args(argv)
    if unknown:
        result = {"action_token": _ACTION_TOKEN, "refusal_category": "parser_invalid_argument", "exit_code": 2}
        print(json.dumps(result))
        return 2

    result = run_autonomy_read_only_network_executor(
        as_of=args.as_of,
        apply=args.apply,
        format=args.format,
    )
    print(json.dumps(result))
    return int(result.get("exit_code", 2))


if __name__ == "__main__":
    sys.exit(main())
