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
    raw = as_of_raw.strip()
    if not raw:
        raise ValidationError("as_of_invalid")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError("as_of_invalid") from exc
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise ValidationError("as_of_invalid")
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
        if isinstance(qualifying, list) and session_id in qualifying:
            return True
    except (OSError, json.JSONDecodeError):
        pass
    return False


def _acquire_lock(lock_path: Path, timeout_seconds: float = 5.0) -> Any:
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        if not lock_path.exists():
            lock_path.write_text("lock\n", encoding="utf-8")
        elif lock_path.is_dir():
            return None
    except (OSError, PermissionError):
        return None

    deadline = _time.monotonic() + timeout_seconds
    while True:
        try:
            lock_file = open(lock_path, "r+", encoding="utf-8")
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock_file
        except (OSError, PermissionError):
            try:
                lock_file.close()
            except Exception:
                pass
            if _time.monotonic() >= deadline:
                return None
            _time.sleep(0.1)


def _release_lock(lock_file: Any) -> None:
    if lock_file is None:
        return
    try:
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


_EXPECTED_LEDGER_KEYS = frozenset({
    "record_type",
    "schema_version",
    "action_token",
    "apply",
    "session_already_qualified",
    "session_id",
    "as_of",
    "attempt_number",
    "run_id",
    "reservation_id",
    "ledger_status",
    "exit_code",
    "adapter_refresh_state",
    "network_access_attempted",
    "interlock_verdict",
    "credential_present",
    "refusal_category",
    "attempt_budget_exhausted",
    "broker_access_attempted",
    "broker_mutation_performed",
    "paper_submit_performed",
    "live_trading_performed",
    "live_authorized",
    "profit_claim",
})

_VALID_REFUSAL_CATEGORIES = frozenset({
    "session_attempt_budget_exhausted",
    "live_capital_interlock_blocked",
    "token_not_available",
})


def _read_and_validate_ledger(ledger_path: Path, session_id: str) -> tuple[int, list[dict[str, Any]]]:
    if ledger_path.exists() and not ledger_path.is_file():
        raise ValidationError("ledger_corrupt")
    if not ledger_path.exists():
        return 0, []

    records: list[dict[str, Any]] = []
    pending_reservations: dict[str, dict[str, Any]] = {}
    completed_reservations: set[str] = set()
    session_reservations: set[str] = set()
    # Round-6 correction (finding F2): the attempt numbers of the reservations
    # held per session, so the frozen session_id/attempt_number/run_id
    # relationship is enforced rather than assumed.
    reservation_attempts: dict[str, set[int]] = {}

    try:
        content = ledger_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        if not lines and content:
            raise ValidationError("ledger_corrupt")

        for line in lines:
            if not line or line != line.strip():
                raise ValidationError("ledger_corrupt")

            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValidationError("ledger_corrupt")

            if set(record.keys()) != _EXPECTED_LEDGER_KEYS:
                raise ValidationError("ledger_corrupt")

            if (
                record["record_type"] != _RECORD_TYPE
                or record["schema_version"] != _SCHEMA_VERSION
                or record["action_token"] != _ACTION_TOKEN
                or record["apply"] is not True
                or record["session_already_qualified"] is not False
                or record["broker_access_attempted"] is not False
                or record["broker_mutation_performed"] is not False
                or record["paper_submit_performed"] is not False
                or record["live_trading_performed"] is not False
                or record["live_authorized"] is not False
                or record["profit_claim"] != "none"
            ):
                raise ValidationError("ledger_corrupt")

            rec_session = record["session_id"]
            rec_as_of = record["as_of"]
            rec_attempt = record["attempt_number"]
            rec_run_id = record["run_id"]
            rec_budget_ex = record["attempt_budget_exhausted"]
            status = record["ledger_status"]

            if (
                not isinstance(rec_session, str) or not rec_session
                or not isinstance(rec_as_of, str) or not rec_as_of
                or not isinstance(rec_attempt, int) or rec_attempt < 1 or isinstance(rec_attempt, bool)
                or not isinstance(rec_run_id, str) or not rec_run_id
                or not isinstance(rec_budget_ex, bool)
                or status not in ("pending", "completed", "refused")
            ):
                raise ValidationError("ledger_corrupt")

            # Round-6 correction (finding F2): run_id is not free-form. It is
            # derived as network-<session_id>-<attempt_number>, and a record
            # whose three fields disagree cannot be trusted to describe which
            # attempt it belongs to.
            if rec_run_id != f"network-{rec_session}-{rec_attempt}":
                raise ValidationError("ledger_corrupt")

            res_id = record["reservation_id"]
            exit_code = record["exit_code"]
            adapter_state = record["adapter_refresh_state"]
            net_access = record["network_access_attempted"]
            verdict = record["interlock_verdict"]
            cred_present = record["credential_present"]
            refusal_cat = record["refusal_category"]

            if status == "pending":
                if (
                    res_id != rec_run_id
                    or exit_code is not None
                    or adapter_state is not None
                    or net_access is not False
                    or not isinstance(verdict, dict)
                    or cred_present is not True
                    or refusal_cat is not None
                    or rec_budget_ex is not False
                ):
                    raise ValidationError("ledger_corrupt")

                if res_id in pending_reservations:
                    raise ValidationError("ledger_corrupt")

                pending_reservations[res_id] = record
                reservation_attempts.setdefault(rec_session, set()).add(rec_attempt)
                if rec_session == session_id:
                    session_reservations.add(res_id)

            elif status == "completed":
                if (
                    res_id != rec_run_id
                    or exit_code not in (0, 1) or isinstance(exit_code, bool)
                    or not isinstance(adapter_state, str) or not adapter_state
                    or net_access is not True
                    or not isinstance(verdict, dict)
                    or cred_present is not True
                    or refusal_cat is not None
                    or rec_budget_ex is not False
                ):
                    raise ValidationError("ledger_corrupt")

                if res_id not in pending_reservations or res_id in completed_reservations:
                    raise ValidationError("ledger_corrupt")

                pending_rec = pending_reservations[res_id]
                if (
                    pending_rec["session_id"] != rec_session
                    or pending_rec["as_of"] != rec_as_of
                    or pending_rec["attempt_number"] != rec_attempt
                    or pending_rec["interlock_verdict"] != verdict
                    or pending_rec["credential_present"] != cred_present
                ):
                    raise ValidationError("ledger_corrupt")

                completed_reservations.add(res_id)
                if rec_session == session_id:
                    session_reservations.add(res_id)

            elif status == "refused":
                if (
                    res_id is not None
                    or exit_code != 2 or isinstance(exit_code, bool)
                    or adapter_state is not None
                    or net_access is not False
                    or refusal_cat not in _VALID_REFUSAL_CATEGORIES
                ):
                    raise ValidationError("ledger_corrupt")

                if refusal_cat == "session_attempt_budget_exhausted":
                    if (
                        verdict is not None
                        or cred_present is not None
                        or rec_budget_ex is not True
                    ):
                        raise ValidationError("ledger_corrupt")
                elif refusal_cat == "live_capital_interlock_blocked":
                    if (
                        not isinstance(verdict, dict)
                        or cred_present is not None
                        or rec_budget_ex is not False
                    ):
                        raise ValidationError("ledger_corrupt")
                elif refusal_cat == "token_not_available":
                    if (
                        not isinstance(verdict, dict)
                        or cred_present is not False
                        or rec_budget_ex is not False
                    ):
                        raise ValidationError("ledger_corrupt")

            records.append(record)

        # Round-6 correction (finding F2): a session's reservations must number
        # exactly 1..N with no gaps or repeats. Without this, a ledger holding a
        # single pending reservation numbered 2 validated as count 1, so the
        # next attempt regenerated run_id network-<session>-2 and appended a
        # duplicate reservation before the network was ever reached.
        for sess, attempts in reservation_attempts.items():
            if attempts != set(range(1, len(attempts) + 1)):
                raise ValidationError("ledger_corrupt")

    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValidationError("ledger_corrupt") from exc

    return len(session_reservations), records


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


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValidationError("parser_invalid_argument")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _SanitizedArgumentParser(
        description="Autonomy read-only network execution seam for SPY market-data refresh.",
        allow_abbrev=False,
    )
    parser.add_argument("--as-of", required=True, help="ISO-8601 UTC timestamp")
    parser.add_argument("--apply", action="store_true", default=False, help="Execute apply mode")
    parser.add_argument("--format", choices=["json"], default="json", help="Output format")

    try:
        args, unknown = parser.parse_known_args(argv)
        if unknown:
            raise ValidationError("parser_invalid_argument")
    except ValidationError:
        result: dict[str, Any] = {
            "action_token": _ACTION_TOKEN,
            "refusal_category": "parser_invalid_argument",
            "exit_code": 2,
        }
    else:
        try:
            result = run_autonomy_read_only_network_executor(
                as_of=args.as_of,
                apply=args.apply,
                format=args.format,
            )
        except ValidationError:
            # Every refusal the seam knows how to name — including
            # ``as_of_invalid`` — is returned in the result dict, so a
            # ValidationError escaping here is an unexpected internal failure.
            # Reporting it as ``parser_invalid_argument`` would blame the
            # operator's command line for something that happened deep inside
            # the adapter or the ledger.
            result = {
                "action_token": _ACTION_TOKEN,
                "refusal_category": "unexpected_validation_error",
                "exit_code": 2,
            }

    print(json.dumps(result))
    return int(result.get("exit_code", 2))


if __name__ == "__main__":
    sys.exit(main())
