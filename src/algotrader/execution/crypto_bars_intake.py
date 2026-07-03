"""Offline BTCUSD crypto bars intake for the no-submit paper visibility lane."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.asset_freshness_policy import (
    ASSET_CLASS_CRYPTO,
    DEFAULT_CRYPTO_MAX_BAR_AGE,
    evaluate_asset_class_freshness,
)
from algotrader.signals.crypto_trend import (
    CRYPTO_TREND_STRATEGY_ID,
    normalize_crypto_symbol,
)

CRYPTO_BARS_INTAKE_SCHEMA_VERSION = "v4_11d_crypto_bars_intake_v1"
CRYPTO_BARS_INTAKE_COMMAND = "crypto-bars-refresh-intake"
CRYPTO_BARS_INTAKE_DEFAULT_SYMBOL = "BTCUSD"
CRYPTO_BARS_INTAKE_REQUIRED_BARS = 50
CRYPTO_BARS_INTAKE_DEFAULT_BASIS = "alpaca_crypto_bars_v1beta3_ohlcv"
CRYPTO_BARS_INTAKE_DEFAULT_SOURCE = "alpaca_market_data_crypto_bars_v1beta3_us"
CRYPTO_BARS_INTAKE_DEFAULT_RAW_RESPONSE_PATH = Path(
    "runs/operator_input/crypto_paper_bars_raw.json"
)
CRYPTO_BARS_INTAKE_DEFAULT_CANONICAL_CSV = Path(
    "runs/operator_input/crypto_paper_bars.csv"
)
CRYPTO_BARS_INTAKE_DEFAULT_RUN_LOG = Path(
    "runs/crypto_paper_visibility/latest/crypto_bars_intake_manifest.jsonl"
)
CRYPTO_BARS_INTAKE_CANONICAL_COLUMNS = (
    "timestamp",
    "symbol",
    "asset_class",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "basis",
    "source",
)

_SAFETY_FALSE_FIELDS = (
    "submit_authorized",
    "paper_submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "paper_submit_performed",
    "broker_mutation_performed",
    "live_mutation_performed",
    "live_authorized",
)

__all__ = [
    "CRYPTO_BARS_INTAKE_CANONICAL_COLUMNS",
    "CRYPTO_BARS_INTAKE_COMMAND",
    "CRYPTO_BARS_INTAKE_DEFAULT_BASIS",
    "CRYPTO_BARS_INTAKE_DEFAULT_CANONICAL_CSV",
    "CRYPTO_BARS_INTAKE_DEFAULT_RAW_RESPONSE_PATH",
    "CRYPTO_BARS_INTAKE_DEFAULT_RUN_LOG",
    "CRYPTO_BARS_INTAKE_DEFAULT_SOURCE",
    "CRYPTO_BARS_INTAKE_DEFAULT_SYMBOL",
    "CRYPTO_BARS_INTAKE_REQUIRED_BARS",
    "CRYPTO_BARS_INTAKE_SCHEMA_VERSION",
    "CryptoBarsIntakeConfig",
    "build_crypto_bars_intake",
    "render_crypto_bars_intake_json",
    "render_crypto_bars_intake_text",
    "run_crypto_bars_intake",
    "write_crypto_bars_intake_jsonl",
]


@dataclass(frozen=True, slots=True)
class CryptoBarsIntakeConfig:
    """Inputs for deterministic local BTCUSD crypto bars normalization."""

    input_path: Path | str = CRYPTO_BARS_INTAKE_DEFAULT_RAW_RESPONSE_PATH
    canonical_csv: Path | str = CRYPTO_BARS_INTAKE_DEFAULT_CANONICAL_CSV
    run_log: Path | str = CRYPTO_BARS_INTAKE_DEFAULT_RUN_LOG
    observed_at: datetime | str | None = None
    symbol: str = CRYPTO_BARS_INTAKE_DEFAULT_SYMBOL
    asset_class: str = ASSET_CLASS_CRYPTO
    basis: str = CRYPTO_BARS_INTAKE_DEFAULT_BASIS
    source: str = CRYPTO_BARS_INTAKE_DEFAULT_SOURCE
    run_id: str = "v4_11d_crypto_bars_refresh_intake"
    required_bars: int = CRYPTO_BARS_INTAKE_REQUIRED_BARS
    max_bar_age: timedelta = DEFAULT_CRYPTO_MAX_BAR_AGE
    market_data_read_performed: bool = False
    network_access_attempted: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_path", _path(self.input_path, "input_path"))
        object.__setattr__(
            self,
            "canonical_csv",
            _path(self.canonical_csv, "canonical_csv"),
        )
        object.__setattr__(self, "run_log", _path(self.run_log, "run_log"))
        symbol = normalize_crypto_symbol(self.symbol)
        if symbol != CRYPTO_BARS_INTAKE_DEFAULT_SYMBOL:
            raise ValidationError("crypto bars intake currently supports BTCUSD only.")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, ASSET_CLASS_CRYPTO, "asset_class"),
        )
        object.__setattr__(self, "basis", _required_string(self.basis, "basis"))
        object.__setattr__(self, "source", _required_string(self.source, "source"))
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "required_bars",
            _positive_int(self.required_bars, "required_bars"),
        )
        object.__setattr__(
            self,
            "max_bar_age",
            _nonnegative_timedelta(self.max_bar_age, "max_bar_age"),
        )
        observed_at = (
            datetime.now(UTC)
            if self.observed_at is None
            else _utc_datetime(self.observed_at, "observed_at")
        )
        object.__setattr__(self, "observed_at", observed_at)
        for field_name in ("market_data_read_performed", "network_access_attempted"):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")


@dataclass(frozen=True, slots=True)
class _ParsedCryptoBar:
    timestamp: datetime
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


def run_crypto_bars_intake(config: CryptoBarsIntakeConfig) -> dict[str, object]:
    """Build and write one crypto bars intake manifest."""

    checked_config = _config(config)
    payload = build_crypto_bars_intake(checked_config)
    write_crypto_bars_intake_jsonl(payload, checked_config.run_log)
    return payload


def build_crypto_bars_intake(config: CryptoBarsIntakeConfig) -> dict[str, object]:
    """Validate, canonicalize, and summarize local BTCUSD crypto bars input."""

    checked_config = _config(config)
    input_path = checked_config.input_path
    if not input_path.exists() or not input_path.is_file():
        return _manifest(
            checked_config,
            intake_state="blocked_missing_crypto_bars_input",
            blockers=("crypto_bars_input_missing",),
        )

    try:
        data = input_path.read_bytes()
        input_sha256 = hashlib.sha256(data).hexdigest()
        text = data.decode("utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return _manifest(
            checked_config,
            intake_state="blocked_invalid_crypto_bars",
            blockers=("malformed_crypto_bars_input",),
        )

    try:
        bars = _parse_input_text(text, checked_config)
    except ValidationError as exc:
        return _manifest(
            checked_config,
            intake_state="blocked_invalid_crypto_bars",
            blockers=_dedupe(_string_sequence(exc.args[0] if exc.args else str(exc))),
            input_sha256=input_sha256,
        )

    if not bars:
        return _manifest(
            checked_config,
            intake_state="blocked_invalid_crypto_bars",
            blockers=("zero_valid_crypto_bars",),
            input_sha256=input_sha256,
        )

    validation_blockers = _validation_blockers(bars, checked_config)
    if validation_blockers:
        return _manifest(
            checked_config,
            intake_state="blocked_invalid_crypto_bars",
            blockers=validation_blockers,
            input_sha256=input_sha256,
            bar_count=len(bars),
        )

    ordered_bars = tuple(sorted(bars, key=lambda bar: bar.timestamp))
    usable_bars = tuple(
        bar for bar in ordered_bars if bar.timestamp <= checked_config.observed_at
    )
    latest_bar_at = ordered_bars[-1].timestamp
    freshness = evaluate_asset_class_freshness(
        asset_class=ASSET_CLASS_CRYPTO,
        latest_bar_at=latest_bar_at,
        observed_at=checked_config.observed_at,
        crypto_max_age=checked_config.max_bar_age,
    )
    if freshness.data_freshness_status != "current_for_24_7_crypto_lab":
        return _manifest(
            checked_config,
            intake_state="blocked_stale_crypto_bars",
            blockers=tuple(freshness.blockers),
            input_sha256=input_sha256,
            bar_count=len(ordered_bars),
            usable_bar_count=len(usable_bars),
            latest_bar_at=latest_bar_at.isoformat(),
            date_range_start=ordered_bars[0].timestamp.isoformat(),
            date_range_end=ordered_bars[-1].timestamp.isoformat(),
            freshness=freshness.to_dict(),
        )

    if len(usable_bars) < checked_config.required_bars:
        return _manifest(
            checked_config,
            intake_state="blocked_insufficient_crypto_history",
            blockers=("insufficient_history",),
            input_sha256=input_sha256,
            bar_count=len(ordered_bars),
            usable_bar_count=len(usable_bars),
            latest_bar_at=latest_bar_at.isoformat(),
            date_range_start=ordered_bars[0].timestamp.isoformat(),
            date_range_end=ordered_bars[-1].timestamp.isoformat(),
            freshness=freshness.to_dict(),
        )

    _write_canonical_csv(checked_config.canonical_csv, ordered_bars, checked_config)
    canonical_sha256 = _sha256_file(checked_config.canonical_csv)
    return _manifest(
        checked_config,
        intake_state="accepted_fresh_crypto_bars",
        blockers=(),
        input_sha256=input_sha256,
        canonical_sha256=canonical_sha256,
        bar_count=len(ordered_bars),
        usable_bar_count=len(usable_bars),
        latest_bar_at=latest_bar_at.isoformat(),
        date_range_start=ordered_bars[0].timestamp.isoformat(),
        date_range_end=ordered_bars[-1].timestamp.isoformat(),
        freshness=freshness.to_dict(),
    )


def write_crypto_bars_intake_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> None:
    """Write exactly one JSONL manifest record."""

    path = Path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_crypto_bars_intake_json(payload) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def render_crypto_bars_intake_json(payload: Mapping[str, object]) -> str:
    """Render the intake payload as deterministic compact JSON."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_crypto_bars_intake_text(payload: Mapping[str, object]) -> str:
    """Render the intake payload as compact operator-readable text."""

    blockers = ",".join(_string_sequence(payload.get("blockers"))) or "none"
    return "\n".join(
        (
            f"crypto_bars_intake_command={CRYPTO_BARS_INTAKE_COMMAND}",
            f"schema_version={payload.get('schema_version', '')}",
            f"intake_state={payload.get('intake_state', '')}",
            f"symbol={payload.get('symbol', '')}",
            f"asset_class={payload.get('asset_class', '')}",
            f"basis={payload.get('basis', '')}",
            f"source={payload.get('source', '')}",
            f"accepted_bar_count={payload.get('accepted_bar_count', 0)}",
            f"usable_bar_count={payload.get('usable_bar_count', 0)}",
            f"required_bars={payload.get('required_bars', 0)}",
            f"latest_bar_at={payload.get('latest_bar_at', '')}",
            f"data_freshness_status={payload.get('data_freshness_status', '')}",
            f"canonical_csv_path={payload.get('canonical_csv_path', '')}",
            f"market_data_read_performed={_bool_text(payload.get('market_data_read_performed'))}",
            f"network_access_attempted={_bool_text(payload.get('network_access_attempted'))}",
            f"paper_submit_performed={_bool_text(payload.get('paper_submit_performed'))}",
            f"broker_mutation_performed={_bool_text(payload.get('broker_mutation_performed'))}",
            f"live_mutation_performed={_bool_text(payload.get('live_mutation_performed'))}",
            f"blockers={blockers}",
        )
    )


def _parse_input_text(
    text: str,
    config: CryptoBarsIntakeConfig,
) -> tuple[_ParsedCryptoBar, ...]:
    stripped = text.lstrip()
    if not stripped:
        raise ValidationError("empty_crypto_bars_input")
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValidationError("malformed_json") from exc
        return _parse_alpaca_payload(payload, config)
    return _parse_csv_text(text, config)


def _parse_alpaca_payload(
    payload: object,
    config: CryptoBarsIntakeConfig,
) -> tuple[_ParsedCryptoBar, ...]:
    items = _payload_bar_items(payload, config.symbol)
    return tuple(_bar_from_mapping(item, config, row_number=index) for index, item in enumerate(items, start=1))


def _payload_bar_items(payload: object, symbol: str) -> tuple[Mapping[str, object], ...]:
    if isinstance(payload, list):
        return _mapping_tuple(payload)
    if not isinstance(payload, Mapping):
        raise ValidationError("crypto_bars_payload_must_be_object_or_list")

    bars = payload.get("bars", payload)
    if isinstance(bars, list):
        return _mapping_tuple(bars)
    if isinstance(bars, Mapping):
        for key, value in bars.items():
            try:
                normalized_key = normalize_crypto_symbol(str(key))
            except ValidationError:
                continue
            if normalized_key == symbol:
                if not isinstance(value, list):
                    raise ValidationError("crypto_symbol_bars_must_be_list")
                return _mapping_tuple(value)
        raise ValidationError(f"selected_symbol_missing_from_payload:{symbol}")
    raise ValidationError("crypto_bars_payload_must_include_bars")


def _parse_csv_text(
    text: str,
    config: CryptoBarsIntakeConfig,
) -> tuple[_ParsedCryptoBar, ...]:
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValidationError("malformed_csv")
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValidationError("duplicate_columns")
    rows: list[_ParsedCryptoBar] = []
    blockers: list[str] = []
    for row_number, row in enumerate(reader, start=2):
        if None in row:
            blockers.append("malformed_csv_row")
            continue
        try:
            rows.append(_bar_from_mapping(row, config, row_number=row_number))
        except ValidationError as exc:
            blockers.append(_row_blocker(exc))
    if blockers:
        raise ValidationError(",".join(_dedupe(blockers)))
    return tuple(rows)


def _bar_from_mapping(
    row: Mapping[str, object],
    config: CryptoBarsIntakeConfig,
    *,
    row_number: int,
) -> _ParsedCryptoBar:
    symbol_text = _first_text(row, "symbol", "S")
    symbol = config.symbol if not symbol_text else normalize_crypto_symbol(symbol_text)
    if symbol != config.symbol:
        raise ValidationError(f"row_{row_number}_symbol_must_be_{config.symbol}")
    asset_class = _first_text(row, "asset_class")
    if asset_class and asset_class.strip().lower() != ASSET_CLASS_CRYPTO:
        raise ValidationError(f"row_{row_number}_asset_class_must_be_crypto")
    open_price = _positive_decimal(_required_text(row, "open", "o"), "open")
    high = _positive_decimal(_required_text(row, "high", "h"), "high")
    low = _positive_decimal(_required_text(row, "low", "l"), "low")
    close = _positive_decimal(_required_text(row, "close", "c"), "close")
    volume_text = _first_text(row, "volume", "v")
    volume = Decimal("0") if not volume_text else _nonnegative_decimal(volume_text, "volume")
    if high < max(open_price, close):
        raise ValidationError(f"row_{row_number}_high_below_open_or_close")
    if low > min(open_price, close):
        raise ValidationError(f"row_{row_number}_low_above_open_or_close")
    return _ParsedCryptoBar(
        timestamp=_row_timestamp(row, row_number),
        symbol=symbol,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _row_timestamp(row: Mapping[str, object], row_number: int) -> datetime:
    text = _required_text(row, "timestamp", "datetime", "date", "t")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"row_{row_number}_timestamp_must_be_iso8601") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"row_{row_number}_timestamp_timezone_required")
    return parsed.astimezone(UTC)


def _validation_blockers(
    bars: Sequence[_ParsedCryptoBar],
    config: CryptoBarsIntakeConfig,
) -> tuple[str, ...]:
    blockers: list[str] = []
    seen_timestamps: set[datetime] = set()
    for bar in bars:
        if bar.symbol != config.symbol:
            blockers.append(f"symbol_must_be_{config.symbol}")
        if bar.timestamp in seen_timestamps:
            blockers.append("duplicate_timestamps")
        seen_timestamps.add(bar.timestamp)
    ordered = tuple(sorted(bars, key=lambda bar: bar.timestamp))
    for previous, current in zip(ordered, ordered[1:]):
        if current.timestamp <= previous.timestamp:
            blockers.append("timestamps_must_be_strictly_ascending")
            break
    return _dedupe(blockers)


def _write_canonical_csv(
    path: Path,
    bars: Sequence[_ParsedCryptoBar],
    config: CryptoBarsIntakeConfig,
) -> None:
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(CRYPTO_BARS_INTAKE_CANONICAL_COLUMNS)
        for bar in bars:
            writer.writerow(
                (
                    bar.timestamp.isoformat(),
                    bar.symbol,
                    ASSET_CLASS_CRYPTO,
                    _decimal_text(bar.open),
                    _decimal_text(bar.high),
                    _decimal_text(bar.low),
                    _decimal_text(bar.close),
                    _decimal_text(bar.volume),
                    config.basis,
                    config.source,
                )
            )


def _manifest(
    config: CryptoBarsIntakeConfig,
    *,
    intake_state: str,
    blockers: tuple[str, ...],
    input_sha256: str = "",
    canonical_sha256: str = "",
    bar_count: int = 0,
    usable_bar_count: int = 0,
    latest_bar_at: str = "",
    date_range_start: str = "",
    date_range_end: str = "",
    freshness: Mapping[str, object] | None = None,
) -> dict[str, object]:
    freshness_payload = dict(freshness or {})
    payload: dict[str, object] = {
        "schema_version": CRYPTO_BARS_INTAKE_SCHEMA_VERSION,
        "record_type": "crypto_bars_refresh_intake_manifest",
        "command": CRYPTO_BARS_INTAKE_COMMAND,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "asset_class": ASSET_CLASS_CRYPTO,
        "strategy_id": CRYPTO_TREND_STRATEGY_ID,
        "basis": config.basis,
        "source": config.source,
        "input_path": str(config.input_path),
        "input_sha256": input_sha256,
        "canonical_csv_path": str(config.canonical_csv),
        "canonical_csv_sha256": canonical_sha256,
        "intake_state": intake_state,
        "accepted_bar_count": bar_count if not blockers else 0,
        "observed_bar_count": bar_count,
        "usable_bar_count": usable_bar_count,
        "required_bars": config.required_bars,
        "latest_bar_at": latest_bar_at,
        "date_range_start": date_range_start,
        "date_range_end": date_range_end,
        "observed_at": config.observed_at.isoformat(),
        "freshness_policy": freshness_payload.get("freshness_policy", "crypto_24_7_max_bar_age"),
        "data_freshness_status": freshness_payload.get("data_freshness_status", ""),
        "freshness": freshness_payload,
        "blockers": list(blockers),
        "market_data_read_performed": config.market_data_read_performed,
        "network_access_attempted": config.network_access_attempted,
        "no_submit_mode": True,
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": "none",
        "credential_values_stored": False,
    }
    for field_name in _SAFETY_FALSE_FIELDS:
        payload[field_name] = False
    return payload


def _mapping_tuple(values: Sequence[object]) -> tuple[Mapping[str, object], ...]:
    result: list[Mapping[str, object]] = []
    for index, value in enumerate(values, start=1):
        if not isinstance(value, Mapping):
            raise ValidationError(f"crypto_bar_{index}_must_be_object")
        result.append(value)
    return tuple(result)


def _first_text(row: Mapping[str, object], *field_names: str) -> str:
    wanted = {name.lower() for name in field_names}
    for key, value in row.items():
        if str(key).strip().lower() in wanted:
            return "" if value is None else str(value).strip()
    return ""


def _required_text(row: Mapping[str, object], *field_names: str) -> str:
    text = _first_text(row, *field_names)
    if not text:
        raise ValidationError(f"missing_required_field:{field_names[0]}")
    return text


def _positive_decimal(value: object, field_name: str) -> Decimal:
    parsed = _decimal(value, field_name)
    if parsed <= Decimal("0"):
        raise ValidationError(f"{field_name}_must_be_positive")
    return parsed


def _nonnegative_decimal(value: object, field_name: str) -> Decimal:
    parsed = _decimal(value, field_name)
    if parsed < Decimal("0"):
        raise ValidationError(f"{field_name}_must_be_nonnegative")
    return parsed


def _decimal(value: object, field_name: str) -> Decimal:
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name}_must_be_decimal") from exc
    if not parsed.is_finite():
        raise ValidationError(f"{field_name}_must_be_finite")
    return parsed


def _row_blocker(exc: ValidationError) -> str:
    text = str(exc)
    if "symbol_must_be" in text:
        return "symbol_must_be_BTCUSD"
    if "asset_class_must_be_crypto" in text:
        return "asset_class_must_be_crypto"
    if "timestamp_timezone_required" in text:
        return "timestamp_timezone_required"
    if "timestamp_must_be_iso8601" in text:
        return "timestamp_must_be_iso8601"
    if "missing_required_field" in text:
        return text
    if "high_below_open_or_close" in text:
        return "invalid_ohlc_relationship"
    if "low_above_open_or_close" in text:
        return "invalid_ohlc_relationship"
    if "must_be_" in text:
        return "invalid_ohlcv_values"
    return text


def _config(value: object) -> CryptoBarsIntakeConfig:
    if not isinstance(value, CryptoBarsIntakeConfig):
        raise ValidationError("config must be a CryptoBarsIntakeConfig.")
    return value


def _path(value: object, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif type(value) is str and value.strip():
        path = Path(value.strip())
    else:
        raise ValidationError(f"{field_name} must be a filesystem path.")
    return path


def _utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be an ISO timestamp.") from exc
    else:
        raise ValidationError(f"{field_name} must be an ISO timestamp.")
    if parsed.tzinfo is None:
        raise ValidationError(f"{field_name} must include timezone information.")
    return parsed.astimezone(UTC)


def _fixed_string(value: object, expected: str, field_name: str) -> str:
    text = _required_string(value, field_name)
    if text != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")
    return text


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return value


def _nonnegative_timedelta(value: object, field_name: str) -> timedelta:
    if not isinstance(value, timedelta) or value.total_seconds() < 0:
        raise ValidationError(f"{field_name} must be a non-negative timedelta.")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item).strip())
    if value in (None, ""):
        return ()
    return tuple(part for part in str(value).split(",") if part.strip())


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value
