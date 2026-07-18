"""Target-scoped paper broker collector for independent flat evidence.

The command boundary performs account, position, and open-order reads only.
It never constructs an order or exposes a mutation method. Successful output
is the sanitized receipt built by the pure V5.27 flat reconciler.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
import hashlib
import json
import os
from algotrader.core.crypto_bounded_probe_lifecycle import canonical_json_bytes
from pathlib import Path
from typing import Any

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL, AlpacaPaperConfig
from algotrader.core.paper_account_binding import (
    build_alpaca_paper_account_binding,
)
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import AlpacaRecentOrderQuery
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.execution.crypto_bounded_probe_independent_flat_reconciliation import (
    CRYPTO_BOUNDED_PROBE_FLAT_SUPPORTED_SYMBOLS,
    build_crypto_bounded_probe_independent_flat_reconciliation,
    validate_crypto_bounded_probe_independent_flat_reconciliation,
)
from algotrader.execution.crypto_tournament_v2_bounded_paper_probe_lifecycle_operator import (
    validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_receipt,
)



SCHEMA_VERSION = "v5_29_crypto_bounded_probe_independent_flat_operator_v1"
DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_strategy_tournament/v2/bounded_paper_probe_capabilities"
)
DEFAULT_LIFECYCLE_PATH = Path(
    "runs/crypto_strategy_tournament/v2/bounded_paper_probe_lifecycle/latest/"
    "lifecycle_result.json"
)
TARGET_LIFECYCLE_SCHEMA_VERSION = (
    "v5_29_crypto_tournament_v2_bounded_paper_probe_lifecycle_v1"
)
LEGACY_LIFECYCLE_SCHEMA_VERSION = (
    "v5_10_crypto_paper_fill_exit_certification_v1"
)


_MAX_LIFECYCLE_SOURCE_BYTES = 1_048_576

BrokerClientFactory = Callable[[AlpacaPaperConfig], Any]

_CREDENTIAL_NAMES = (
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
)
_EXPECTED_ACCOUNT_NAMES = (
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID",
)
_NETWORK_TEST_FLAG_NAMES = (
    "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
    "PYTEST_NETWORK",
    "NETWORK_TESTS",
    "ALLOW_NETWORK_TESTS",
)


def run_crypto_bounded_probe_independent_flat_operator(
    *,
    symbol: str,
    lifecycle_path: Path | str = DEFAULT_LIFECYCLE_PATH,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    timestamp: datetime | str | None = None,
    clock: Callable[[], datetime] | None = None,
    env: Mapping[str, str] | None = None,
    broker_client_factory: BrokerClientFactory | None = None,
    expected_paper_account_id: str = "",
    independent_flat_read_authorized: bool = False,
    allow_network: bool = False,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Collect one post-exit, account-wide flat paper observation."""

    selected_symbol = _symbol(symbol)
    claimed_not_before = (
        None if timestamp is None else _utc_datetime(timestamp, "timestamp")
    )
    trusted_clock = clock or (lambda: datetime.now(UTC))
    clock_blockers: list[str] = []
    try:
        observed_at = _trusted_clock_time(trusted_clock)
    except ValidationError:
        observed_at = claimed_not_before or datetime.now(UTC)
        clock_blockers.append("trusted_clock_invalid")
    if (
        claimed_not_before is not None
        and observed_at < claimed_not_before
    ):
        clock_blockers.append("trusted_clock_precedes_requested_not_before")
    source_path = _path(lifecycle_path, "lifecycle_path")
    root = _path(output_root, "output_root")
    lifecycle, lifecycle_sha256, lifecycle_source_blocker = (
        _read_json_mapping(source_path)
    )
    lifecycle_binding, lifecycle_blockers = _lifecycle_binding(
        lifecycle,
        selected_symbol=selected_symbol,
        observed_at=observed_at,
        source_sha256=lifecycle_sha256,
    )
    if lifecycle_source_blocker:
        lifecycle_blockers = [lifecycle_source_blocker]
    source_env = _normalized_env(dict(os.environ) if env is None else env)
    expected_account = (
        str(expected_paper_account_id).strip()
        or _first_nonempty(source_env, _EXPECTED_ACCOUNT_NAMES)
    )
    preflight = _preflight(source_env, expected_account=expected_account)
    blockers = [*clock_blockers, *lifecycle_blockers]
    if (
        lifecycle_binding.get("schema_version")
        == TARGET_LIFECYCLE_SCHEMA_VERSION
        and expected_account
    ):
        expected_binding = build_alpaca_paper_account_binding(
            {"account_id": expected_account},
            expected_account_configured=True,
            expected_account_matched=True,
        )
        if lifecycle_binding.get("account_binding") != expected_binding:
            blockers.append("target_lifecycle_account_binding_mismatch")
    if independent_flat_read_authorized is not True:
        blockers.append("independent_flat_read_authorization_required")
    if allow_network is not True:
        blockers.append("allow_network_switch_required")
    blockers.extend(_preflight_blockers(preflight))
    base: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_bounded_probe_independent_flat_operator_status",
        "as_of": observed_at.isoformat(),
        "subject": {
            "asset_class": "crypto",
            "symbol": selected_symbol,
            "environment": "alpaca_paper",
        },
        "lifecycle_source": str(source_path),
        "lifecycle_binding": lifecycle_binding,
        "operator_preflight": preflight,
        "read_authorized": independent_flat_read_authorized is True,
        "network_authorized": allow_network is True,
        "broker_read_occurred": False,
        "account_read_occurred": False,
        "positions_read_occurred": False,
        "open_orders_read_occurred": False,
        "broker_mutation_occurred": False,
        "paper_mutation_occurred": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "receipt_emitted": False,
        "receipt_fingerprint": "",
        "final_position_count": -1,
        "final_open_order_count": -1,
        "blockers": list(dict.fromkeys(blockers)),
        "classification": "blocked_before_broker_read",
        "next_action": "resolve_flat_read_preflight_before_retry",
        "profit_claim": "none",
    }
    if blockers:
        return _finish(root, base, receipt=None, write_artifacts=write_artifacts)

    client_result = _build_client(source_env, broker_client_factory)
    client = client_result["client"]
    if client is None:
        return _finish(
            root,
            {
                **base,
                "blockers": ["paper_broker_client_unavailable"],
                "client_error_type": client_result["error_type"],
            },
            receipt=None,
            write_artifacts=write_artifacts,
        )

    account_result = _read_account(client)
    positions_result = _read_positions(client)
    orders_result = _read_open_orders(client)
    try:
        completed_at = _trusted_clock_time(
            trusted_clock,
            not_before=observed_at,
        )
        clock_read_blocker = ""
    except ValidationError:
        completed_at = observed_at
        clock_read_blocker = "trusted_clock_invalid"
    read_errors = [
        value
        for value in (
            clock_read_blocker,
            account_result["blocker"],
            positions_result["blocker"],
            orders_result["blocker"],
        )
        if value
    ]
    account = account_result["value"]
    positions = positions_result["value"]
    open_orders = orders_result["value"]
    if not _expected_account_matches(account, expected_account):
        read_errors.append("expected_paper_account_mismatch")
    if positions:
        read_errors.append("account_wide_position_observed")
    if open_orders:
        read_errors.append("account_wide_open_order_observed")
    observed_base = {
        **base,
        "as_of": completed_at.isoformat(),
        "broker_read_occurred": True,
        "account_read_occurred": account_result["occurred"],
        "positions_read_occurred": positions_result["occurred"],
        "open_orders_read_occurred": orders_result["occurred"],
        "final_position_count": len(positions),
        "final_open_order_count": len(open_orders),
        "blockers": list(dict.fromkeys(read_errors)),
        "classification": (
            "blocked_by_flat_reconciliation"
            if read_errors
            else "flat_observation_ready"
        ),
        "next_action": (
            "reconcile_account_state_without_mutation"
            if read_errors
            else "emit_sanitized_independent_flat_receipt"
        ),
    }
    if read_errors:
        return _finish(
            root,
            observed_base,
            receipt=None,
            write_artifacts=write_artifacts,
        )

    try:
        receipt = build_crypto_bounded_probe_independent_flat_reconciliation(
            symbol=selected_symbol,
            observed_at=completed_at,
            account_observation=account,
            expected_account_configured=True,
            expected_account_matched=True,
            positions=positions,
            open_orders=open_orders,
            broker_read_occurred=True,
            account_read_occurred=True,
            positions_read_occurred=True,
            open_orders_read_occurred=True,
        )
        validate_crypto_bounded_probe_independent_flat_reconciliation(receipt)
    except ValidationError:
        return _finish(
            root,
            {
                **observed_base,
                "blockers": ["sanitized_flat_receipt_validation_failed"],
                "classification": "blocked_by_flat_reconciliation",
                "next_action": "repair_account_observation_before_retry",
            },
            receipt=None,
            write_artifacts=write_artifacts,
        )
    return _finish(
        root,
        {
            **observed_base,
            "receipt_emitted": True,
            "receipt_fingerprint": receipt["observation_fingerprint"],
            "blockers": [],
            "classification": "independent_flat_receipt_emitted",
            "next_action": "run_source_bound_capability_production",
        },
        receipt=receipt,
        write_artifacts=write_artifacts,
    )


def _lifecycle_binding(
    lifecycle: Mapping[str, object],
    *,
    selected_symbol: str,
    observed_at: datetime,
    source_sha256: str,
) -> tuple[dict[str, object], list[str]]:
    blockers: list[str] = []
    schema = str(lifecycle.get("schema_version", ""))
    lifecycle_symbol = ""
    if schema == LEGACY_LIFECYCLE_SCHEMA_VERSION:
        lifecycle_symbol = str(lifecycle.get("symbol", "")).strip().upper()
        if lifecycle_symbol != "BTCUSD":
            blockers.append("legacy_lifecycle_symbol_invalid")
        if lifecycle.get("outcome_classification") != "filled_exit_confirmed":
            blockers.append("lifecycle_fill_exit_not_confirmed")
    elif schema == TARGET_LIFECYCLE_SCHEMA_VERSION:
        try:
            validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_receipt(
                lifecycle
            )
        except (ValidationError, KeyError, TypeError, ValueError):
            blockers.append("target_lifecycle_receipt_invalid")
        subject = lifecycle.get("subject")
        if isinstance(subject, Mapping):
            lifecycle_symbol = str(subject.get("symbol", "")).strip().upper()
        if lifecycle.get("record_type") != (
            "crypto_tournament_v2_bounded_paper_probe_lifecycle"
        ):
            blockers.append("target_lifecycle_record_type_invalid")
        if lifecycle.get("outcome_classification") != "filled_exit_confirmed":
            blockers.append("lifecycle_fill_exit_not_confirmed")
    else:
        blockers.append("supported_lifecycle_receipt_required")
    if lifecycle_symbol != selected_symbol:
        blockers.append("lifecycle_selected_symbol_mismatch")
    exit_order = lifecycle.get("exit_final_order")
    if (
        not isinstance(exit_order, Mapping)
        or str(exit_order.get("status", "")).strip().lower() != "filled"
    ):
        blockers.append("lifecycle_exit_fill_required")
        filled_at = None
    else:
        try:
            filled_at = _utc_datetime(exit_order.get("filled_at"), "filled_at")
        except ValidationError:
            filled_at = None
            blockers.append("lifecycle_exit_filled_at_invalid")
    if filled_at is not None and filled_at > observed_at:
        blockers.append("flat_observation_precedes_exit_fill")
    return (
        {
            "schema_version": schema,
            "symbol": lifecycle_symbol,
            **(
                {
                    "account_binding": dict(lifecycle["account_binding"])
                }
                if schema == TARGET_LIFECYCLE_SCHEMA_VERSION
                and isinstance(lifecycle.get("account_binding"), Mapping)
                else {}
            ),
            "exit_filled_at": (
                "" if filled_at is None else filled_at.isoformat()
            ),
            "source_sha256": source_sha256,
        },
        list(dict.fromkeys(blockers)),
    )


def _preflight(
    env: Mapping[str, str], *, expected_account: str
) -> dict[str, bool]:
    endpoint = _effective_paper_url(env)
    return {
        "APP_PROFILE_is_paper": env.get("APP_PROFILE", "").lower() == "paper",
        "APP_PROFILE_is_live": env.get("APP_PROFILE", "").lower() == "live",
        "paper_credentials_present": bool(
            env.get("ALPACA_API_KEY") and env.get("ALPACA_SECRET_KEY")
        ),
        "expected_paper_account_id_loaded": bool(expected_account),
        "paper_endpoint_exact_match_indicator": (
            _endpoint(endpoint) == _endpoint(DEFAULT_ALPACA_PAPER_BASE_URL)
        ),
        "live_endpoint_indicator": _live_endpoint(env),
        "network_test_flag_enabled": any(
            env.get(name, "").strip().lower()
            in {"1", "true", "yes", "on"}
            for name in _NETWORK_TEST_FLAG_NAMES
        )
        or "--allow-network"
        in env.get("PYTEST_ADDOPTS", "").strip().lower(),
        **{
            f"{name}_present": bool(env.get(name))
            for name in _CREDENTIAL_NAMES
        },
    }


def _preflight_blockers(preflight: Mapping[str, bool]) -> list[str]:
    checks = (
        ("APP_PROFILE_is_paper", True, "APP_PROFILE_paper_required"),
        ("APP_PROFILE_is_live", False, "APP_PROFILE_live_not_authorized"),
        ("paper_credentials_present", True, "paper_credentials_required"),
        (
            "expected_paper_account_id_loaded",
            True,
            "expected_paper_account_id_required",
        ),
        (
            "paper_endpoint_exact_match_indicator",
            True,
            "paper_endpoint_exact_match_required",
        ),
        ("live_endpoint_indicator", False, "live_endpoint_indicator"),
        ("network_test_flag_enabled", False, "network_test_flag_enabled"),
    )
    return [
        blocker
        for key, expected, blocker in checks
        if preflight.get(key) is not expected
    ]


def _build_client(
    env: Mapping[str, str], factory: BrokerClientFactory | None
) -> dict[str, object]:
    try:
        config = AlpacaPaperConfig(
            app_profile=env.get("APP_PROFILE", ""),
            alpaca_api_key=env.get("ALPACA_API_KEY"),
            alpaca_secret_key=env.get("ALPACA_SECRET_KEY"),
            alpaca_paper_base_url=_effective_paper_url(env),
        )
        return {
            "client": (factory or AlpacaSdkClient)(config),
            "error_type": "",
        }
    except Exception as exc:  # noqa: BLE001 - command fails closed.
        return {"client": None, "error_type": exc.__class__.__name__}


def _read_account(client: Any) -> dict[str, object]:
    try:
        raw_account = client.get_account()
        raw = _object_payload(
            raw_account,
            (
                "id",
                "account_id",
                "account_number",
                "status",
                "blocked",
                "account_blocked",
                "trading_blocked",
            ),
        )
        if not isinstance(raw_account, Mapping):
            for name in ("blocked", "account_blocked", "trading_blocked"):
                if hasattr(raw_account, name):
                    raw[name] = getattr(raw_account, name)
        required_flags = ("account_blocked", "trading_blocked")
        if any(
            name not in raw or type(raw[name]) is not bool
            for name in required_flags
        ) or (
            "blocked" in raw and type(raw["blocked"]) is not bool
        ):
            return {
                "value": {},
                "occurred": True,
                "blocker": "paper_account_blocking_fields_invalid",
            }
        flags = {name: raw[name] for name in required_flags}
        if "blocked" in raw:
            flags["blocked"] = raw["blocked"]
        value = {
            "id": str(raw.get("id", "")).strip(),
            "account_id": str(raw.get("account_id", "")).strip(),
            "account_number": str(raw.get("account_number", "")).strip(),
            "status": str(raw.get("status", "")).strip(),
            **flags,
        }
        if not value["id"] and value["account_id"]:
            value["id"] = value["account_id"]
        if not value["account_id"] and value["id"]:
            value["account_id"] = value["id"]
        blocker = (
            "paper_account_trading_blocked"
            if any(flags.values())
            else ""
        )
        return {"value": value, "occurred": True, "blocker": blocker}
    except Exception:  # noqa: BLE001 - broker ambiguity is sanitized.
        return {
            "value": {},
            "occurred": False,
            "blocker": "account_read_failed",
        }


def _read_positions(client: Any) -> dict[str, object]:
    try:
        rows = [
            _object_payload(value, ("symbol", "qty", "side"))
            for value in client.get_positions()
        ]
        return {"value": rows, "occurred": True, "blocker": ""}
    except Exception:  # noqa: BLE001
        return {
            "value": [],
            "occurred": False,
            "blocker": "positions_read_failed",
        }


def _read_open_orders(client: Any) -> dict[str, object]:
    try:
        query = AlpacaRecentOrderQuery(
            status_filter="open",
            limit=100,
        )
        rows = [
            _object_payload(
                value,
                ("symbol", "status", "client_order_id"),
            )
            for value in client.get_orders(query)
        ]
        return {
            "value": rows,
            "occurred": True,
            "blocker": (
                "account_wide_open_order_scan_may_be_truncated"
                if len(rows) >= query.limit
                else ""
            ),
        }
    except Exception:  # noqa: BLE001
        return {
            "value": [],
            "occurred": False,
            "blocker": "open_orders_read_failed",
        }


def _expected_account_matches(
    account: Mapping[str, object], expected: str
) -> bool:
    return bool(expected) and expected in {
        str(account.get(name, "")).strip()
        for name in ("id", "account_id", "account_number")
        if str(account.get(name, "")).strip()
    }


def _finish(
    root: Path,
    status: Mapping[str, object],
    *,
    receipt: Mapping[str, object] | None,
    write_artifacts: bool,
) -> dict[str, object]:
    result = dict(status)
    result["status_fingerprint"] = _stable_hash(result)
    if write_artifacts:
        root.mkdir(parents=True, exist_ok=True)
        _atomic_write(root / "latest_status.json", _json_bytes(result))
        receipt_path = root / "independent_flat_reconciliation.json"
        manifest_path = root / "independent_flat_manifest.json"
        if receipt is None:
            superseded = root / "superseded"
            for existing in (receipt_path, manifest_path):
                if existing.is_file():
                    superseded.mkdir(parents=True, exist_ok=True)
                    destination = superseded / (
                        result["status_fingerprint"] + "-" + existing.name
                    )
                    os.replace(existing, destination)
        if receipt is not None:
            receipt_bytes = _json_bytes(receipt)
            _atomic_write(
                receipt_path,
                receipt_bytes,
            )
            manifest: dict[str, object] = {
                "schema_version": SCHEMA_VERSION,
                "record_type": (
                    "crypto_bounded_probe_independent_flat_manifest"
                ),
                "as_of": result["as_of"],
                "symbol": result["subject"]["symbol"],
                "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
                "status_sha256": hashlib.sha256(
                    _json_bytes(result)
                ).hexdigest(),
                "collector_source_sha256": hashlib.sha256(
                    Path(__file__).resolve().read_bytes()
                ).hexdigest(),
                "lifecycle_source_sha256": result[
                    "lifecycle_binding"
                ]["source_sha256"],
                "broker_mutation_occurred": False,
                "paper_mutation_occurred": False,
                "live_endpoint_touched": False,
                "credential_values_exposed": False,
            }
            manifest["manifest_fingerprint"] = _stable_hash(manifest)
            _atomic_write(
                manifest_path,
                _json_bytes(manifest),
            )
    return result


def _normalized_env(raw: Mapping[str, str]) -> dict[str, str]:
    env = {
        str(key): str(value).strip()
        for key, value in raw.items()
        if value is not None
    }
    env["ALPACA_API_KEY"] = (
        env.get("ALPACA_API_KEY") or env.get("APCA_API_KEY_ID", "")
    )
    env["ALPACA_SECRET_KEY"] = (
        env.get("ALPACA_SECRET_KEY")
        or env.get("ALPACA_API_SECRET_KEY")
        or env.get("APCA_API_SECRET_KEY", "")
    )
    return env


def _effective_paper_url(env: Mapping[str, str]) -> str:
    return (
        env.get("ALPACA_PAPER_BASE_URL")
        or env.get("APCA_API_BASE_URL")
        or DEFAULT_ALPACA_PAPER_BASE_URL
    )


def _live_endpoint(env: Mapping[str, str]) -> bool:
    if env.get("APP_PROFILE", "").lower() == "live":
        return True
    for name in (
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
    ):
        value = env.get(name, "").lower()
        if "api.alpaca.markets" in value and "paper" not in value:
            return True
    return False


def _endpoint(value: str) -> str:
    return value.strip().rstrip("/").lower()


def _object_payload(
    value: object, fields: Sequence[str]
) -> dict[str, object]:
    if isinstance(value, Mapping):
        return {name: value[name] for name in fields if name in value}
    return {
        name: field
        for name in fields
        if (field := getattr(value, name, None)) is not None
    }


class _DuplicateJsonKeyError(ValueError):
    pass


def _read_json_mapping(
    path: Path,
) -> tuple[dict[str, object], str, str]:
    if not path.is_file() or _is_link_or_reparse(path):
        return {}, "", "lifecycle_source_not_regular_non_reparse_file"
    try:
        with path.open("rb") as stream:
            payload = stream.read(_MAX_LIFECYCLE_SOURCE_BYTES + 1)
    except OSError:
        return {}, "", "lifecycle_source_not_regular_non_reparse_file"
    if not payload:
        return {}, "", "lifecycle_source_empty"
    if len(payload) > _MAX_LIFECYCLE_SOURCE_BYTES:
        return {}, "", "lifecycle_source_too_large"

    def reject_duplicates(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise _DuplicateJsonKeyError(key)
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise ValueError(f"non-finite JSON constant: {value}")

    try:
        decoded = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return {}, "", "lifecycle_source_not_utf8"
    try:
        value = json.loads(
            decoded,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except _DuplicateJsonKeyError:
        return {}, "", "lifecycle_source_duplicate_keys"
    except (ValueError, json.JSONDecodeError):
        return {}, "", "lifecycle_source_invalid_json"
    if not isinstance(value, Mapping):
        return {}, "", "lifecycle_source_not_object"
    parsed = dict(value)
    if (
        parsed.get("schema_version") == TARGET_LIFECYCLE_SCHEMA_VERSION
        and payload != canonical_json_bytes(parsed)
    ):
        return {}, "", "target_lifecycle_source_not_canonical_json"
    return parsed, hashlib.sha256(payload).hexdigest(), ""


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & 0x400)


def _path(value: Path | str, field_name: str) -> Path:
    path = Path(value)
    if not str(path).strip():
        raise ValidationError(f"{field_name} is required.")
    return path


def _symbol(value: object) -> str:
    symbol = str(value).strip().upper()
    if symbol not in CRYPTO_BOUNDED_PROBE_FLAT_SUPPORTED_SYMBOLS:
        raise ValidationError(
            "independent flat target symbol is unsupported."
        )
    return symbol


def _utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(
                value.strip().replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValidationError(
                f"{field_name} must be ISO-8601."
            ) from exc
    else:
        raise ValidationError(f"{field_name} must be a datetime.")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware.")
    return parsed.astimezone(UTC)


def _trusted_clock_time(
    clock: Callable[[], datetime],
    *,
    not_before: datetime | None = None,
) -> datetime:
    try:
        observed = _utc_datetime(clock(), "trusted_clock")
    except Exception as exc:
        raise ValidationError("trusted clock is unavailable.") from exc
    if not_before is not None and observed < not_before:
        raise ValidationError("trusted clock regressed.")
    return observed


def _first_nonempty(
    env: Mapping[str, str], names: Sequence[str]
) -> str:
    return next(
        (
            env.get(name, "").strip()
            for name in names
            if env.get(name, "").strip()
        ),
        "",
    )


def _stable_hash(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        allow_abbrev=False,
    )
    parser.add_argument("--target-symbol", required=True)
    parser.add_argument(
        "--lifecycle-path", default=str(DEFAULT_LIFECYCLE_PATH)
    )
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument(
        "--independent-flat-read-authorized", action="store_true"
    )
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args(argv)
    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol=args.target_symbol,
        lifecycle_path=args.lifecycle_path,
        output_root=args.output_root,
        independent_flat_read_authorized=(
            args.independent_flat_read_authorized
        ),
        allow_network=args.allow_network,
    )
    print(json.dumps(status, sort_keys=True, indent=2))
    return (
        0
        if status["classification"]
        == "independent_flat_receipt_emitted"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
