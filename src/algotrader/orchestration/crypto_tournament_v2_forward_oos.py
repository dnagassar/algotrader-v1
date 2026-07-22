"""Guarded operating wrapper for crypto tournament v2 forward OOS.

Default modes are network-free. The only network-capable path delegates to
the existing read-only crypto history adapter and requires its explicit
market-data authorization flags. No broker read, order, or mutation path is
present.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
import json
from pathlib import Path
from functools import partial

from algotrader.errors import ValidationError
from algotrader.execution.crypto_history_refresh_adapter import (
    CryptoHistoryRefreshConfig,
    crypto_history_refresh_preflight,
    run_crypto_history_refresh,
)
from algotrader.execution.secure_credential_provider import (
    CredentialReference,
    provider_from_name,
)
from algotrader.research.crypto_preregistered_tournament_v2 import (
    TOURNAMENT_V2_SYMBOLS,
)
from algotrader.research.crypto_tournament_v2_forward_oos import (
    CRYPTO_TOURNAMENT_V2_DEFAULT_DISCOVERY_RECEIPT_PATH,
    CRYPTO_TOURNAMENT_V2_DEFAULT_DISCOVERY_SOURCE_PATH,
    CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT,
    initialize_crypto_tournament_v2_forward_oos,
    run_crypto_tournament_v2_forward_oos,
)


CRYPTO_TOURNAMENT_V2_OPERATING_SCHEMA_VERSION = (
    "v5_23_crypto_tournament_v2_operating_cycle_v1"
)
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
    "CRYPTO_TOURNAMENT_V2_OPERATING_SCHEMA_VERSION",
    "build_crypto_tournament_v2_refresh_readiness",
    "main",
    "run_crypto_tournament_v2_operating_cycle",
]


def build_crypto_tournament_v2_refresh_readiness(
    *,
    output_root: Path | str = CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT,
    as_of: datetime | str,
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Inspect the exact next fetch without loading secrets or using network."""

    status = run_crypto_tournament_v2_forward_oos(
        output_root=output_root,
        as_of=as_of,
        write_artifacts=False,
    )
    next_refresh = _mapping(status.get("next_refresh"))
    preflight = crypto_history_refresh_preflight(env)
    blockers: list[str] = []
    next_classification = str(
        next_refresh.get("classification", "")
    )
    if next_classification != (
        "ready_for_explicit_read_only_market_data_fetch"
    ):
        blockers.append(next_classification or "no_refresh_window")
    if preflight.get("live_endpoint_indicator"):
        blockers.append("live_endpoint_indicator")
    if not preflight.get("APP_PROFILE_is_paper"):
        blockers.append("APP_PROFILE_paper_required")
    if not preflight.get("paper_credentials_present"):
        blockers.append("paper_market_data_credentials_required")
    if not preflight.get("APCA_API_BASE_URL_is_paper"):
        blockers.append("explicit_paper_base_url_required")

    if not blockers:
        classification = (
            "ready_for_explicit_read_only_market_data_fetch"
        )
    elif next_classification == "waiting_for_calendar_hour":
        classification = "waiting_for_calendar_hour"
    elif next_classification == "accrual_complete":
        classification = "accrual_complete"
    else:
        classification = (
            "blocked_market_data_credentials_or_profile"
        )
    return {
        "schema_version": CRYPTO_TOURNAMENT_V2_OPERATING_SCHEMA_VERSION,
        "record_type": "crypto_tournament_v2_refresh_readiness",
        "classification": classification,
        "blockers": list(dict.fromkeys(blockers)),
        "next_refresh": dict(next_refresh),
        "operator_preflight": {
            key: bool(value)
            for key, value in sorted(preflight.items())
        },
        "market_data_fetch_occurred": False,
        "network_access_attempted": False,
        "broker_read_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "live_authorized": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "profit_claim": "none",
    }


def run_crypto_tournament_v2_operating_cycle(
    *,
    mode: str,
    output_root: Path | str = CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT,
    as_of: datetime | str,
    discovery_source_path: Path | str = (
        CRYPTO_TOURNAMENT_V2_DEFAULT_DISCOVERY_SOURCE_PATH
    ),
    discovery_receipt_path: Path | str = (
        CRYPTO_TOURNAMENT_V2_DEFAULT_DISCOVERY_RECEIPT_PATH
    ),
    refresh_config: CryptoHistoryRefreshConfig | None = None,
    refresh_runner: RefreshRunner = run_crypto_history_refresh,
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Initialize, inspect, or execute one exact read-only accrual fetch."""

    root = Path(output_root)
    if mode == "initialize":
        if refresh_config is not None:
            raise ValidationError(
                "v2 initialization cannot run a network refresh."
            )
        return initialize_crypto_tournament_v2_forward_oos(
            discovery_source_path=discovery_source_path,
            discovery_receipt_path=discovery_receipt_path,
            output_root=root,
            as_of=as_of,
        )
    if mode == "status":
        if refresh_config is not None:
            raise ValidationError(
                "v2 status cannot run a network refresh."
            )
        return run_crypto_tournament_v2_forward_oos(
            output_root=root,
            as_of=as_of,
        )
    if mode == "readiness":
        if refresh_config is not None:
            raise ValidationError(
                "v2 readiness cannot run a network refresh."
            )
        return build_crypto_tournament_v2_refresh_readiness(
            output_root=root,
            as_of=as_of,
            env=env,
        )
    if mode != "market_data_fetch":
        raise ValidationError("unsupported tournament v2 operating mode.")
    if refresh_config is None:
        raise ValidationError(
            "market_data_fetch mode requires a refresh config."
        )
    if refresh_config.mode != "market_data_fetch":
        raise ValidationError(
            "v2 accrual accepts only guarded market_data_fetch receipts."
        )

    status = run_crypto_tournament_v2_forward_oos(
        output_root=root,
        as_of=as_of,
    )
    next_refresh = _mapping(status.get("next_refresh"))
    if next_refresh.get("classification") != (
        "ready_for_explicit_read_only_market_data_fetch"
    ):
        status["refresh"] = {
            "status": "not_run",
            "reason": next_refresh.get("classification", ""),
            "market_data_fetch_occurred": False,
            "network_access_attempted": False,
        }
        return status

    refresh_root = root / "refresh"
    prepared = replace(
        refresh_config,
        symbols=tuple(TOURNAMENT_V2_SYMBOLS),
        output_path=refresh_root / "forward_oos_delta.csv",
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
        }
        return status
    if (
        refresh.get("market_data_fetch_occurred") is not True
        or refresh.get("network_access_attempted") is not True
    ):
        status["refresh"] = _safe_refresh_summary(refresh)
        return status
    if not _refresh_matches_request(
        refresh,
        prepared=prepared,
        next_refresh=next_refresh,
    ):
        status["network_access_attempted"] = True
        status["market_data_fetch_occurred"] = True
        status["refresh"] = _safe_refresh_summary(refresh)
        status["refresh"]["status"] = "failed_closed_receipt_mismatch"
        status["refresh"]["reason"] = (
            "refresh receipt did not match the exact frozen request"
        )
        return status

    accrued = run_crypto_tournament_v2_forward_oos(
        output_root=root,
        as_of=as_of,
        delta_history_path=prepared.output_path,
        delta_receipt_path=prepared.packet_path,
        operation_network_access=True,
        operation_market_data_fetch=True,
    )
    accrued["refresh"] = _safe_refresh_summary(refresh)
    return accrued


def _refresh_matches_request(
    packet: Mapping[str, object],
    *,
    prepared: CryptoHistoryRefreshConfig,
    next_refresh: Mapping[str, object],
) -> bool:
    requested = tuple(str(item) for item in prepared.symbols)
    returned_requested = _string_sequence(
        packet.get("requested_symbols")
    )
    returned_fetched = _string_sequence(packet.get("fetched_symbols"))
    try:
        output_matches = Path(
            str(packet.get("output_path", ""))
        ).resolve() == Path(prepared.output_path).resolve()
        packet_matches = Path(
            str(packet.get("packet_path", ""))
        ).resolve() == Path(prepared.packet_path).resolve()
    except (OSError, RuntimeError):
        return False
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
    return (
        packet.get("mode") == "market_data_fetch"
        and packet.get("authorization_status") == "authorized"
        and packet.get("endpoint_safety_status")
        == "passed_non_live_endpoint_check"
        and packet.get("data_intake_only") is True
        and packet.get("strategy_evidence_evaluation_performed") is False
        and packet.get("timeframe") == "1Hour"
        and packet.get("loc") == "us"
        and returned_requested == requested
        and returned_fetched == requested
        and expected_times == returned_times
        and all(expected_times)
        and output_matches
        and packet_matches
        and all(
            field in packet and packet.get(field) is False
            for field in _FALSE_RECEIPT_FIELDS
        )
    )


def _safe_refresh_summary(
    packet: Mapping[str, object],
) -> dict[str, object]:
    summary = {
        "status": str(packet.get("classification", "")),
        "mode": str(packet.get("mode", "")),
        "as_of": str(packet.get("as_of", "")),
        "requested_start": str(packet.get("requested_start", "")),
        "requested_end": str(packet.get("requested_end", "")),
        "requested_symbols": list(
            _string_sequence(packet.get("requested_symbols"))
        ),
        "fetched_symbols": list(
            _string_sequence(packet.get("fetched_symbols"))
        ),
        "output_path": str(packet.get("output_path", "")),
        "output_sha256": str(packet.get("output_sha256", "")),
        "data_intake_only": packet.get("data_intake_only"),
        "strategy_evidence_evaluation_performed": packet.get(
            "strategy_evidence_evaluation_performed"
        ),
        "market_data_fetch_occurred": packet.get(
            "market_data_fetch_occurred"
        ),
        "network_access_attempted": packet.get(
            "network_access_attempted"
        ),
    }
    for field in _FALSE_RECEIPT_FIELDS:
        summary[field] = packet.get(field)
    return summary


def _utc_iso(value: object) -> str:
    if type(value) is not str or not value.strip():
        return ""
    try:
        parsed = datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        )
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        return ""
    return parsed.astimezone(UTC).isoformat()


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes)
    ):
        return tuple(str(item) for item in value)
    return ()

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=(
            "initialize",
            "status",
            "readiness",
            "market_data_fetch",
        ),
        default="status",
    )
    parser.add_argument(
        "--output-root",
        default=str(CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument("--as-of", default=None)
    parser.add_argument(
        "--discovery-source-path",
        default=str(
            CRYPTO_TOURNAMENT_V2_DEFAULT_DISCOVERY_SOURCE_PATH
        ),
    )
    parser.add_argument(
        "--discovery-receipt-path",
        default=str(
            CRYPTO_TOURNAMENT_V2_DEFAULT_DISCOVERY_RECEIPT_PATH
        ),
    )
    parser.add_argument(
        "--market-data-fetch-authorized",
        action="store_true",
    )
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--credential-provider", default="")
    parser.add_argument("--credential-reference", default="")
    parser.add_argument("--app-profile", default="")
    parser.add_argument("--paper-endpoint", default="")
    parser.add_argument("--market-data-endpoint", default="")
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
        not args.market_data_fetch_authorized
        or not args.allow_network
    ):
        parser.error(
            "market_data_fetch requires both explicit authorization flags."
        )
    refresh_config = None
    refresh_runner: RefreshRunner = run_crypto_history_refresh
    if args.mode == "market_data_fetch":
        if not args.credential_provider or not args.credential_reference:
            parser.error(
                "market_data_fetch requires a secure credential provider reference."
            )
        provider = provider_from_name(args.credential_provider)
        reference = CredentialReference(args.credential_reference)
        refresh_runner = partial(
            run_crypto_history_refresh,
            credential_provider=provider,
            credential_reference=reference,
            app_profile=args.app_profile,
            paper_endpoint=args.paper_endpoint,
            market_data_endpoint=args.market_data_endpoint,
        )
        refresh_config = CryptoHistoryRefreshConfig(
            mode="market_data_fetch",
            symbols=tuple(TOURNAMENT_V2_SYMBOLS),
            output_path=Path(args.output_root)
            / "refresh"
            / "forward_oos_delta.csv",
            packet_path=Path(args.output_root)
            / "refresh"
            / "refresh_packet.json",
            raw_response_path=Path(args.output_root)
            / "refresh"
            / "raw_crypto_bars.json",
            market_data_fetch_authorized=(
                args.market_data_fetch_authorized
            ),
            allow_network=args.allow_network,
            data_intake_only=True,
        )
    packet = run_crypto_tournament_v2_operating_cycle(
        mode=args.mode,
        output_root=args.output_root,
        as_of=as_of,
        discovery_source_path=args.discovery_source_path,
        discovery_receipt_path=args.discovery_receipt_path,
        refresh_config=refresh_config,
        refresh_runner=refresh_runner,
    )
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
