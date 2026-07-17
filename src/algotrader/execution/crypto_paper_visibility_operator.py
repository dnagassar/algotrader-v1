"""Operator-facing no-submit crypto paper visibility cycle."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

from algotrader.config import (
    DEFAULT_ALPACA_PAPER_BASE_URL,
    AlpacaPaperConfig,
)
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.execution.crypto_paper_supervisor import (
    CRYPTO_PAPER_SUPERVISOR_DEFAULT_BARS_CSV,
    CRYPTO_PAPER_SUPERVISOR_DEFAULT_OUTPUT_ROOT,
    CRYPTO_PAPER_SUPERVISOR_PREFERRED_SYMBOLS,
    CryptoPaperSupervisorConfig,
    run_crypto_paper_supervisor,
    write_crypto_paper_supervisor_artifacts,
)

CRYPTO_PAPER_VISIBILITY_COMMAND = "run_crypto_paper_visibility_cycle"
CRYPTO_PAPER_VISIBILITY_OPERATING_MODE = "visibility/no_submit"
CRYPTO_PAPER_VISIBILITY_TARGET_SYMBOLS = ("BTCUSD", "ETHUSD", "SOLUSD")

SdkClientFactory = Callable[[AlpacaPaperConfig], Any]

_CREDENTIAL_NAMES = (
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
)
_SECRET_KEY_CANDIDATES = (
    "ALPACA_SECRET_KEY",
    "ALPACA_API_SECRET_KEY",
    "APCA_API_SECRET_KEY",
)
_PUBLIC_ENV_NAMES = (
    "APP_PROFILE",
    "ALPACA_BASE_URL",
    "ALPACA_PAPER_BASE_URL",
    "APCA_API_BASE_URL",
)

__all__ = [
    "CRYPTO_PAPER_VISIBILITY_COMMAND",
    "CRYPTO_PAPER_VISIBILITY_OPERATING_MODE",
    "CRYPTO_PAPER_VISIBILITY_TARGET_SYMBOLS",
    "crypto_visibility_environment_preflight",
    "render_crypto_visibility_text",
    "run_crypto_paper_visibility_cycle",
    "validate_crypto_visibility_target_symbol",
]


def run_crypto_paper_visibility_cycle(
    *,
    output_root: str | Path = CRYPTO_PAPER_SUPERVISOR_DEFAULT_OUTPUT_ROOT,
    bars_csv: str | Path = CRYPTO_PAPER_SUPERVISOR_DEFAULT_BARS_CSV,
    timestamp: datetime | str | None = None,
    target_symbol: str | None = None,
    env: Mapping[str, str] | None = None,
    sdk_client_factory: SdkClientFactory | None = None,
    write_artifacts: bool = True,
) -> dict[str, Any]:
    """Run a no-submit crypto visibility cycle with optional paper asset read."""

    checked_target_symbol = validate_crypto_visibility_target_symbol(target_symbol)
    source_env = _env_mapping(env)
    preflight = crypto_visibility_environment_preflight(source_env)
    broker = None
    broker_read_requested = False
    broker_read_error_type = ""

    if (
        preflight["APP_PROFILE_is_paper"] is True
        and preflight["paper_credentials_present"] is True
        and preflight["paper_endpoint_exact_match_indicator"] is True
        and preflight["live_endpoint_indicator"] is not True
    ):
        broker_read_requested = True
        try:
            broker = AlpacaSdkClient(
                _alpaca_paper_config_from_env(source_env),
                sdk_client_factory=sdk_client_factory,
            )
        except Exception as exc:  # noqa: BLE001 - operator receipt fails closed.
            broker = None
            broker_read_error_type = exc.__class__.__name__

    record = run_crypto_paper_supervisor(
        CryptoPaperSupervisorConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            preferred_symbols=(
                (checked_target_symbol,)
                if checked_target_symbol
                else CRYPTO_PAPER_SUPERVISOR_PREFERRED_SYMBOLS
            ),
        ),
        env=_public_broker_env(source_env),
        broker=broker,
        timestamp=timestamp,
        write_artifacts=False,
    )
    record["operator_command"] = CRYPTO_PAPER_VISIBILITY_COMMAND
    record["target_symbol"] = checked_target_symbol
    record["target_scoped"] = bool(checked_target_symbol)
    record["operating_mode"] = CRYPTO_PAPER_VISIBILITY_OPERATING_MODE
    record["operator_preflight"] = preflight
    record["broker_read_requested"] = broker_read_requested
    record["broker_read_error_type"] = broker_read_error_type
    record["no_submit_wrapper"] = True

    if broker_read_error_type:
        record["blockers"] = _dedupe(
            (*_string_sequence(record.get("blockers")), "broker_read_client_unavailable")
        )
        if record.get("readiness_status") == "readiness_blocked_capability_not_observed":
            record["final_operator_action"] = "repair_paper_read_client_then_rerun"

    if write_artifacts:
        record["artifact_paths"] = write_crypto_paper_supervisor_artifacts(
            output_root,
            record,
        )

    return record


def validate_crypto_visibility_target_symbol(target_symbol: object) -> str:
    """Return an exact frozen-universe target or fail before any broker setup."""

    if target_symbol in (None, ""):
        return ""
    if (
        type(target_symbol) is not str
        or target_symbol not in CRYPTO_PAPER_VISIBILITY_TARGET_SYMBOLS
    ):
        raise ValidationError(
            "target_symbol must be exactly BTCUSD, ETHUSD, SOLUSD, or omitted."
        )
    return target_symbol


def crypto_visibility_environment_preflight(
    env: Mapping[str, str] | None = None,
) -> dict[str, bool]:
    """Return boolean-only credential and endpoint preflight state."""

    source = _env_mapping(env)
    app_profile = source.get("APP_PROFILE", "").strip().lower()
    effective_paper_base_url = _effective_paper_base_url(source)
    paper_endpoint_exact_match = (
        _normalize_endpoint(effective_paper_base_url)
        == _normalize_endpoint(DEFAULT_ALPACA_PAPER_BASE_URL)
    )
    credential_state = {
        f"{name}_present": bool(source.get(name, "").strip())
        for name in _CREDENTIAL_NAMES
    }
    paper_credentials_present = bool(_first_nonempty(source, ("ALPACA_API_KEY", "APCA_API_KEY_ID"))) and bool(
        _first_nonempty(source, _SECRET_KEY_CANDIDATES)
    )
    return {
        "APP_PROFILE_is_paper": app_profile == "paper",
        "APP_PROFILE_is_live": app_profile == "live",
        **credential_state,
        "paper_credentials_present": paper_credentials_present,
        "paper_endpoint_exact_match_indicator": paper_endpoint_exact_match,
        "live_endpoint_indicator": _live_endpoint_indicator(source),
    }


def render_crypto_visibility_text(record: Mapping[str, Any]) -> str:
    """Render a compact operator-readable no-submit visibility receipt."""

    preflight = record.get("operator_preflight", {})
    if not isinstance(preflight, Mapping):
        preflight = {}
    lines = [
        f"crypto_visibility_command={CRYPTO_PAPER_VISIBILITY_COMMAND}",
        f"crypto_visibility_operating_mode={CRYPTO_PAPER_VISIBILITY_OPERATING_MODE}",
        "crypto_visibility_no_submit_enforced=true",
    ]
    for key in (
        "APP_PROFILE_is_paper",
        "APP_PROFILE_is_live",
        "ALPACA_API_KEY_present",
        "ALPACA_API_SECRET_KEY_present",
        "ALPACA_SECRET_KEY_present",
        "APCA_API_KEY_ID_present",
        "APCA_API_SECRET_KEY_present",
        "paper_endpoint_exact_match_indicator",
        "live_endpoint_indicator",
    ):
        lines.append(f"preflight_{key}={_bool_text(preflight.get(key))}")

    lines.extend(
        [
            f"broker_read_requested={_bool_text(record.get('broker_read_requested'))}",
            f"broker_read_performed={_bool_text(record.get('broker_read_performed'))}",
            f"broker_state_mode={_value_text(record.get('broker_state_mode'))}",
            f"capability_source={_value_text(record.get('capability_source'))}",
            f"target_symbol={_value_text(record.get('target_symbol'))}",
            f"target_scoped={_bool_text(record.get('target_scoped'))}",
            f"crypto_trading_supported={_bool_text(record.get('crypto_trading_supported'))}",
            f"eligible_crypto_symbols={_csv_text(record.get('eligible_crypto_symbols'))}",
            f"selected_symbol={_value_text(record.get('selected_symbol'))}",
            f"selected_symbol_tradable={_bool_or_unknown_text(record.get('selected_symbol_tradable'))}",
            f"selected_symbol_marginable={_bool_or_unknown_text(record.get('selected_symbol_marginable'))}",
            f"selected_symbol_fractionable={_bool_or_unknown_text(record.get('selected_symbol_fractionable'))}",
            f"min_order_size={_value_text(record.get('min_order_size'))}",
            f"min_trade_increment={_value_text(record.get('min_trade_increment'))}",
            f"min_order_increment={_value_text(record.get('min_order_increment'))}",
            f"min_notional={_value_text(record.get('min_notional'))}",
            "unsupported_jurisdiction_account_blocker="
            f"{_value_text(record.get('unsupported_jurisdiction_account_blocker'))}",
            f"data_freshness_status={_value_text(record.get('data_freshness_status'))}",
            f"strategy_id={_value_text(record.get('strategy_id'))}",
            f"strategy_adapter_mode={_value_text(record.get('strategy_adapter_mode'))}",
            f"action_decision={_value_text(record.get('action_decision'))}",
            f"no_submit_mode={_bool_text(record.get('no_submit_mode'))}",
            f"paper_submit_performed={_bool_text(record.get('paper_submit_performed'))}",
            f"broker_mutation_performed={_bool_text(record.get('broker_mutation_performed'))}",
            f"live_mutation_performed={_bool_text(record.get('live_mutation_performed'))}",
            f"readiness_status={_value_text(record.get('readiness_status'))}",
            f"blockers={_csv_text(record.get('blockers'))}",
            f"final_operator_action={_value_text(record.get('final_operator_action'))}",
            f"safety_labels={_csv_text(record.get('safety_labels'))}",
            f"broker_read_error_type={_value_text(record.get('broker_read_error_type'))}",
        ]
    )
    artifacts = record.get("artifact_paths")
    if isinstance(artifacts, Mapping):
        for key in ("latest_status", "supervisor_receipt", "operating_brief"):
            lines.append(f"artifact_{key}={_value_text(artifacts.get(key))}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="crypto-paper-visibility-operator",
        description="Run the no-submit crypto paper visibility cycle.",
    )
    parser.add_argument(
        "--output-root",
        default=str(CRYPTO_PAPER_SUPERVISOR_DEFAULT_OUTPUT_ROOT),
        help="Directory for crypto visibility artifacts under runs/.",
    )
    parser.add_argument(
        "--bars-csv",
        default=str(CRYPTO_PAPER_SUPERVISOR_DEFAULT_BARS_CSV),
        help="CSV of crypto bars used for the preview lane.",
    )
    parser.add_argument(
        "--target-symbol",
        choices=CRYPTO_PAPER_VISIBILITY_TARGET_SYMBOLS,
        default="",
        help="Optional exact frozen-universe symbol with no fallback.",
    )
    parser.add_argument(
        "--timestamp",
        default="",
        help="Optional ISO timestamp for deterministic visibility receipts.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    args = parser.parse_args(argv)

    record = run_crypto_paper_visibility_cycle(
        output_root=args.output_root,
        bars_csv=args.bars_csv,
        timestamp=args.timestamp or datetime.now(UTC),
        target_symbol=args.target_symbol,
    )
    if args.format == "json":
        print(json.dumps(record, sort_keys=True, indent=2))
    else:
        print(render_crypto_visibility_text(record))

    preflight = record.get("operator_preflight", {})
    if isinstance(preflight, Mapping) and preflight.get("live_endpoint_indicator") is True:
        return 2
    return 0


def _alpaca_paper_config_from_env(env: Mapping[str, str]) -> AlpacaPaperConfig:
    return AlpacaPaperConfig(
        app_profile=env.get("APP_PROFILE", ""),
        alpaca_api_key=_first_nonempty(env, ("ALPACA_API_KEY", "APCA_API_KEY_ID")),
        alpaca_secret_key=_first_nonempty(env, _SECRET_KEY_CANDIDATES),
        alpaca_paper_base_url=_effective_paper_base_url(env),
    )


def _public_broker_env(env: Mapping[str, str]) -> dict[str, str]:
    return {
        name: value
        for name in _PUBLIC_ENV_NAMES
        if (value := env.get(name, "").strip())
    }


def _env_mapping(env: Mapping[str, str] | None) -> dict[str, str]:
    source = os.environ if env is None else env
    return {str(key): str(value) for key, value in source.items()}


def _effective_paper_base_url(env: Mapping[str, str]) -> str:
    return env.get("ALPACA_PAPER_BASE_URL", "").strip() or DEFAULT_ALPACA_PAPER_BASE_URL


def _live_endpoint_indicator(env: Mapping[str, str]) -> bool:
    if env.get("APP_PROFILE", "").strip().lower() == "live":
        return True
    for name in ("ALPACA_BASE_URL", "ALPACA_PAPER_BASE_URL", "APCA_API_BASE_URL"):
        value = env.get(name, "").strip().lower()
        if value and "api.alpaca.markets" in value and "paper" not in value:
            return True
    return False


def _normalize_endpoint(value: str) -> str:
    return value.strip().lower().rstrip("/")


def _first_nonempty(env: Mapping[str, str], names: Sequence[str]) -> str:
    for name in names:
        value = env.get(name, "").strip()
        if value:
            return value
    return ""


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item).strip())
    if value in (None, ""):
        return ()
    return (str(value),)


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _bool_or_unknown_text(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "unknown"


def _value_text(value: object) -> str:
    if value in (None, ""):
        return ""
    return str(value)


def _csv_text(value: object) -> str:
    return ",".join(_string_sequence(value))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
