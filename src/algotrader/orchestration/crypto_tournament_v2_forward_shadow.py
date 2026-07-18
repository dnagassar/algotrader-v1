"""Guarded selected-winner operating bridge for tournament-v2 forward shadow.

Initialization, status, and readiness are network-free.  The sole
network-capable mode delegates one exact selected-symbol OHLCV request to the
existing read-only market-data adapter and requires both explicit authorization
flags.  No broker read, order, paper mutation, or live-capital path exists.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import BinaryIO, Iterator

from algotrader.errors import ValidationError
from algotrader.execution.crypto_history_refresh_adapter import (
    CryptoHistoryRefreshConfig,
    crypto_history_refresh_preflight,
    run_crypto_history_refresh,
)
from algotrader.research.crypto_tournament_v2_forward_oos import (
    CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT,
)
from algotrader.research.crypto_tournament_v2_forward_shadow import (
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT,
    run_crypto_tournament_v2_forward_shadow_readiness,
)
from algotrader.research.crypto_tournament_v2_forward_shadow_state import (
    initialize_crypto_tournament_v2_forward_shadow_state,
    run_crypto_tournament_v2_forward_shadow_state,
)


CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_OPERATING_SCHEMA_VERSION = (
    "v5_25_crypto_tournament_v2_forward_shadow_operating_cycle_v1"
)
_EXPECTED_RECEIPT_SCHEMA = "v5_22_crypto_history_refresh_adapter_receipt_v2"
_EXPECTED_SOURCE = "alpaca_market_data_crypto_bars_v1beta3"
_FALSE_RECEIPT_FIELDS = (
    "broker_read_occurred",
    "broker_mutation_authorized",
    "broker_mutation_occurred",
    "paper_submit_authorized",
    "paper_submit_occurred",
    "paper_cancel_occurred",
    "paper_replace_occurred",
    "paper_close_occurred",
    "paper_liquidate_occurred",
    "live_authorized",
    "live_endpoint_indicator",
    "live_endpoint_touched",
    "credential_values_exposed",
)

RefreshRunner = Callable[
    [CryptoHistoryRefreshConfig], Mapping[str, object]
]

__all__ = [
    "CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_OPERATING_SCHEMA_VERSION",
    "build_crypto_tournament_v2_forward_shadow_refresh_readiness",
    "main",
    "run_crypto_tournament_v2_forward_shadow_operating_cycle",
]


def build_crypto_tournament_v2_forward_shadow_refresh_readiness(
    *,
    tournament_root: Path | str = CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT,
    output_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
    ),
    as_of: datetime | str,
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Inspect the next immutable selected-symbol request without network."""

    status = _network_free_status(
        tournament_root=tournament_root,
        output_root=output_root,
        as_of=as_of,
        write_artifacts=False,
    )
    next_refresh = _mapping(status.get("next_refresh"))
    next_classification = str(next_refresh.get("classification", ""))
    if next_classification != (
        "ready_for_explicit_read_only_market_data_fetch"
    ):
        return _readiness_packet(
            status=status,
            classification=(
                next_classification
                or str(status.get("classification", "no_refresh_window"))
            ),
            blockers=(),
            preflight={},
        )

    preflight = crypto_history_refresh_preflight(env)
    blockers: list[str] = []
    if preflight.get("live_endpoint_indicator"):
        blockers.append("live_endpoint_indicator")
    if not preflight.get("APP_PROFILE_is_paper"):
        blockers.append("APP_PROFILE_paper_required")
    if not preflight.get("paper_credentials_present"):
        blockers.append("paper_market_data_credentials_required")
    if not preflight.get("APCA_API_BASE_URL_is_paper"):
        blockers.append("explicit_paper_base_url_required")
    classification = (
        "ready_for_explicit_read_only_market_data_fetch"
        if not blockers
        else "blocked_market_data_credentials_or_profile"
    )
    return _readiness_packet(
        status=status,
        classification=classification,
        blockers=blockers,
        preflight=preflight,
    )


def run_crypto_tournament_v2_forward_shadow_operating_cycle(
    *,
    mode: str,
    tournament_root: Path | str = CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT,
    output_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
    ),
    as_of: datetime | str,
    refresh_config: CryptoHistoryRefreshConfig | None = None,
    refresh_runner: RefreshRunner = run_crypto_history_refresh,
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Run one cycle, serializing the complete network-capable generation."""

    if mode == "market_data_fetch":
        root = Path(output_root)
        if str(root).startswith(("\\\\", "//")):
            raise ValidationError("output_root must be a local path.")
        if refresh_config is None:
            raise ValidationError(
                "market_data_fetch mode requires a refresh config."
            )
        if refresh_config.mode != "market_data_fetch":
            raise ValidationError(
                "forward-shadow accrual accepts only market_data_fetch mode."
            )
        if (
            not refresh_config.market_data_fetch_authorized
            or not refresh_config.allow_network
        ):
            raise ValidationError(
                "market_data_fetch requires both explicit authorization flags."
            )
        with _exclusive_operating_cycle_lock(root):
            return _run_crypto_tournament_v2_forward_shadow_operating_cycle(
                mode=mode,
                tournament_root=tournament_root,
                output_root=output_root,
                as_of=as_of,
                refresh_config=refresh_config,
                refresh_runner=refresh_runner,
                env=env,
            )
    return _run_crypto_tournament_v2_forward_shadow_operating_cycle(
        mode=mode,
        tournament_root=tournament_root,
        output_root=output_root,
        as_of=as_of,
        refresh_config=refresh_config,
        refresh_runner=refresh_runner,
        env=env,
    )


def _run_crypto_tournament_v2_forward_shadow_operating_cycle(
    *,
    mode: str,
    tournament_root: Path | str = CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT,
    output_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
    ),
    as_of: datetime | str,
    refresh_config: CryptoHistoryRefreshConfig | None = None,
    refresh_runner: RefreshRunner = run_crypto_history_refresh,
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Initialize, inspect, or accrue one exact no-submit shadow delta."""

    root = Path(output_root)
    if mode in {"initialize", "status", "readiness"}:
        if refresh_config is not None:
            raise ValidationError(
                "offline forward-shadow modes cannot accept a refresh config."
            )
        if mode == "initialize":
            return initialize_crypto_tournament_v2_forward_shadow_state(
                tournament_root=tournament_root,
                output_root=root,
                as_of=as_of,
            )
        if mode == "status":
            return _network_free_status(
                tournament_root=tournament_root,
                output_root=root,
                as_of=as_of,
                write_artifacts=True,
            )
        return build_crypto_tournament_v2_forward_shadow_refresh_readiness(
            tournament_root=tournament_root,
            output_root=root,
            as_of=as_of,
            env=env,
        )
    if mode != "market_data_fetch":
        raise ValidationError("unsupported forward-shadow operating mode.")
    if refresh_config is None:
        raise ValidationError(
            "market_data_fetch mode requires a refresh config."
        )
    if refresh_config.mode != "market_data_fetch":
        raise ValidationError(
            "forward-shadow accrual accepts only market_data_fetch mode."
        )
    if (
        not refresh_config.market_data_fetch_authorized
        or not refresh_config.allow_network
    ):
        raise ValidationError(
            "market_data_fetch requires both explicit authorization flags."
        )

    state_path = root / "frozen_state.json"
    if not state_path.is_file():
        initialized = initialize_crypto_tournament_v2_forward_shadow_state(
            tournament_root=tournament_root,
            output_root=root,
            as_of=as_of,
        )
        if not state_path.is_file():
            initialized["refresh"] = _not_run_refresh(
                str(initialized.get("classification", "state_not_initialized"))
            )
            return initialized

    status = run_crypto_tournament_v2_forward_shadow_state(
        output_root=root,
        as_of=as_of,
        write_artifacts=False,
    )
    next_refresh = _mapping(status.get("next_refresh"))
    if next_refresh.get("classification") != (
        "ready_for_explicit_read_only_market_data_fetch"
    ):
        status["refresh"] = _not_run_refresh(
            str(next_refresh.get("classification", "no_refresh_window"))
        )
        return status

    symbols = _string_sequence(next_refresh.get("symbols"))
    frozen_state = _mapping(status.get("frozen_state"))
    selected_symbol = str(frozen_state.get("selected_symbol", ""))
    if len(symbols) != 1 or symbols[0] != selected_symbol:
        raise ValidationError(
            "forward-shadow next refresh is not bound to one frozen symbol."
        )
    refresh_root = root / "refresh"
    prepared = replace(
        refresh_config,
        symbols=symbols,
        output_path=refresh_root / "selected_symbol_delta.csv",
        packet_path=refresh_root / "refresh_packet.json",
        raw_response_path=refresh_root / "raw_crypto_bars.json",
        as_of=str(next_refresh["as_of"]),
        start=str(next_refresh["requested_start"]),
        end=str(next_refresh["requested_end"]),
        timeframe="1Hour",
        loc="us",
        data_intake_only=True,
        write_packet=True,
    )
    before_state_sha = _file_sha256(state_path)
    try:
        refresh = dict(refresh_runner(prepared))
    except Exception as exc:
        status["network_access_attempted"] = True
        status["market_data_fetch_occurred"] = None
        status["refresh"] = {
            "status": "failed_closed",
            "error_type": exc.__class__.__name__,
            "market_data_fetch_occurred": None,
            "market_data_fetch_occurrence_known": False,
            "network_access_attempted": True,
            "state_unchanged": _file_sha256(state_path) == before_state_sha,
        }
        return status

    if not _refresh_matches_request(
        refresh,
        prepared=prepared,
        next_refresh=next_refresh,
    ):
        status["network_access_attempted"] = bool(
            refresh.get("network_access_attempted") is True
        )
        status["market_data_fetch_occurred"] = refresh.get(
            "market_data_fetch_occurred"
        )
        status["refresh"] = _safe_refresh_summary(refresh)
        status["refresh"].update(
            {
                "status": "failed_closed_receipt_mismatch",
                "reason": "receipt_did_not_match_frozen_request",
                "state_unchanged": _file_sha256(state_path)
                == before_state_sha,
            }
        )
        return status

    try:
        accrued = run_crypto_tournament_v2_forward_shadow_state(
            output_root=root,
            as_of=as_of,
            delta_history_path=prepared.output_path,
            delta_receipt_path=prepared.packet_path,
            operation_network_access=True,
            operation_market_data_fetch=True,
        )
    except ValidationError as exc:
        status["network_access_attempted"] = True
        status["market_data_fetch_occurred"] = True
        status["refresh"] = _safe_refresh_summary(refresh)
        status["refresh"].update(
            {
                "status": "failed_closed_state_validation",
                "error_type": exc.__class__.__name__,
                "state_unchanged": _file_sha256(state_path)
                == before_state_sha,
            }
        )
        return status
    accrued["refresh"] = _safe_refresh_summary(refresh)
    accrued["refresh"]["state_accrual_status"] = "accepted"
    return accrued


@contextmanager
def _exclusive_operating_cycle_lock(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".forward_shadow_operating_cycle.lock"
    stream = lock_path.open("a+b")
    try:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl  # pragma: no cover - exercised on non-Windows hosts

            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        stream.close()
        raise ValidationError(
            "another forward-shadow market-data operating cycle is active."
        ) from exc
    try:
        yield
    finally:
        try:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl  # pragma: no cover - exercised on non-Windows hosts

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()


def _network_free_status(
    *,
    tournament_root: Path | str,
    output_root: Path | str,
    as_of: datetime | str,
    write_artifacts: bool,
) -> dict[str, object]:
    root = Path(output_root)
    if (root / "frozen_state.json").is_file():
        return run_crypto_tournament_v2_forward_shadow_state(
            output_root=root,
            as_of=as_of,
            write_artifacts=write_artifacts,
        )
    activation = run_crypto_tournament_v2_forward_shadow_readiness(
        tournament_root=tournament_root,
        output_root=root,
        as_of=as_of,
        write_artifacts=False,
    )
    packet = dict(activation)
    packet["shadow_state_initialized"] = False
    packet["phase"] = "dormant_before_shadow_state_initialization"
    if packet.get("classification") == (
        "ready_to_activate_no_submit_forward_shadow"
    ):
        packet["classification"] = (
            "ready_to_initialize_no_submit_forward_shadow"
        )
        packet["next_action"] = (
            "initialize_persisted_no_submit_forward_shadow_state"
        )
    packet["next_refresh"] = {
        "classification": "state_initialization_required",
        "requested_start": "",
        "requested_end": "",
        "as_of": "",
    }
    packet["network_access_attempted"] = False
    packet["market_data_fetch_occurred"] = False
    return packet


def _readiness_packet(
    *,
    status: Mapping[str, object],
    classification: str,
    blockers: Sequence[str],
    preflight: Mapping[str, object],
) -> dict[str, object]:
    return {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_OPERATING_SCHEMA_VERSION
        ),
        "record_type": "crypto_tournament_v2_forward_shadow_refresh_readiness",
        "classification": classification,
        "blockers": list(dict.fromkeys(blockers)),
        "status_classification": str(status.get("classification", "")),
        "selected_candidate": dict(
            _mapping(status.get("selected_candidate"))
        ),
        "next_refresh": dict(_mapping(status.get("next_refresh"))),
        "operator_preflight": {
            key: bool(value) for key, value in sorted(preflight.items())
        },
        "market_data_fetch_occurred": False,
        "network_access_attempted": False,
        "broker_read_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "paper_cancel_occurred": False,
        "paper_replace_occurred": False,
        "paper_close_occurred": False,
        "paper_liquidate_occurred": False,
        "paper_or_live_execution_authorized": False,
        "capital_allocation_authorized": False,
        "live_authorized": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "profit_claim": "none",
    }


def _refresh_matches_request(
    packet: Mapping[str, object],
    *,
    prepared: CryptoHistoryRefreshConfig,
    next_refresh: Mapping[str, object],
) -> bool:
    expected_symbols = tuple(prepared.symbols)
    output_path = Path(prepared.output_path)
    packet_path = Path(prepared.packet_path) if prepared.packet_path else None
    if packet_path is None or not output_path.is_file() or not packet_path.is_file():
        return False
    try:
        disk_packet = json.loads(packet_path.read_text(encoding="utf-8"))
        output_matches = Path(str(packet.get("output_path", ""))).resolve() == (
            output_path.resolve()
        )
        packet_matches = Path(str(packet.get("packet_path", ""))).resolve() == (
            packet_path.resolve()
        )
    except (OSError, RuntimeError, json.JSONDecodeError):
        return False
    if disk_packet != dict(packet):
        return False
    rows = _mapping(packet.get("rows_per_symbol_after_normalization"))
    expected_times = (
        _utc_iso(next_refresh.get("requested_start")),
        _utc_iso(next_refresh.get("requested_end")),
        _utc_iso(next_refresh.get("as_of")),
    )
    returned_times = (
        _utc_iso(packet.get("requested_start")),
        _utc_iso(packet.get("requested_end")),
        _utc_iso(packet.get("as_of")),
    )
    required = {
        "schema_version": _EXPECTED_RECEIPT_SCHEMA,
        "record_type": "crypto_history_refresh_adapter_packet",
        "classification": "market_data_refresh_ready",
        "coverage_gate_classification": "not_evaluated_data_intake_only",
        "mode": "market_data_fetch",
        "authorization_status": "authorized",
        "endpoint_safety_status": "passed_non_live_endpoint_check",
        "data_source": _EXPECTED_SOURCE,
        "timeframe": "1Hour",
        "loc": "us",
        "schema_validation_status": "passed",
        "duplicate_timestamp_status": "passed",
        "duplicate_timestamp_status_after_normalization": "passed",
        "profit_claim": "none",
    }
    return (
        all(packet.get(key) == value for key, value in required.items())
        and packet.get("market_data_fetch_occurred") is True
        and packet.get("network_access_attempted") is True
        and packet.get("data_intake_only") is True
        and packet.get("strategy_evidence_evaluation_performed") is False
        and packet.get("paper_planning_promotion_allowed") is False
        and _string_sequence(packet.get("requested_symbols"))
        == expected_symbols
        and _string_sequence(packet.get("fetched_symbols"))
        == expected_symbols
        and not _string_sequence(packet.get("missing_symbols"))
        and set(rows) == set(expected_symbols)
        and all(isinstance(rows[symbol], int) and rows[symbol] > 0 for symbol in rows)
        and expected_times == returned_times
        and all(expected_times)
        and output_matches
        and packet_matches
        and str(packet.get("output_sha256", "")).lower()
        == _file_sha256(output_path)
        and all(
            field in packet and packet.get(field) is False
            for field in _FALSE_RECEIPT_FIELDS
        )
    )


def _safe_refresh_summary(packet: Mapping[str, object]) -> dict[str, object]:
    summary = {
        "status": str(packet.get("classification", "")),
        "mode": str(packet.get("mode", "")),
        "as_of": str(packet.get("as_of", "")),
        "requested_start": str(packet.get("requested_start", "")),
        "requested_end": str(packet.get("requested_end", "")),
        "requested_symbols": list(
            _string_sequence(packet.get("requested_symbols"))
        ),
        "fetched_symbols": list(_string_sequence(packet.get("fetched_symbols"))),
        "output_path": str(packet.get("output_path", "")),
        "output_sha256": str(packet.get("output_sha256", "")),
        "data_intake_only": packet.get("data_intake_only"),
        "strategy_evidence_evaluation_performed": packet.get(
            "strategy_evidence_evaluation_performed"
        ),
        "market_data_fetch_occurred": packet.get("market_data_fetch_occurred"),
        "network_access_attempted": packet.get("network_access_attempted"),
    }
    for field in _FALSE_RECEIPT_FIELDS:
        summary[field] = packet.get(field)
    return summary


def _not_run_refresh(reason: str) -> dict[str, object]:
    return {
        "status": "not_run",
        "reason": reason,
        "market_data_fetch_occurred": False,
        "network_access_attempted": False,
    }


def _utc_iso(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        return ""
    return parsed.astimezone(UTC).isoformat()


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value)
    return ()


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("initialize", "status", "readiness", "market_data_fetch"),
        default="status",
    )
    parser.add_argument(
        "--tournament-root",
        default=str(CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument(
        "--output-root",
        default=str(CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--market-data-fetch-authorized", action="store_true")
    parser.add_argument("--allow-network", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    as_of = args.as_of or datetime.now(UTC).isoformat()
    if args.mode != "market_data_fetch" and (
        args.market_data_fetch_authorized or args.allow_network
    ):
        parser.error(
            "network authorization flags require market_data_fetch mode."
        )
    if args.mode == "market_data_fetch" and (
        not args.market_data_fetch_authorized or not args.allow_network
    ):
        parser.error(
            "market_data_fetch requires both explicit authorization flags."
        )
    refresh_config = None
    if args.mode == "market_data_fetch":
        refresh_root = Path(args.output_root) / "refresh"
        refresh_config = CryptoHistoryRefreshConfig(
            mode="market_data_fetch",
            output_path=refresh_root / "selected_symbol_delta.csv",
            packet_path=refresh_root / "refresh_packet.json",
            raw_response_path=refresh_root / "raw_crypto_bars.json",
            market_data_fetch_authorized=True,
            allow_network=True,
            data_intake_only=True,
        )
    packet = run_crypto_tournament_v2_forward_shadow_operating_cycle(
        mode=args.mode,
        tournament_root=args.tournament_root,
        output_root=args.output_root,
        as_of=as_of,
        refresh_config=refresh_config,
    )
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
