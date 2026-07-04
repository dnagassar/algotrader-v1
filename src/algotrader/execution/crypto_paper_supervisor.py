"""No-submit crypto paper universe supervisor seed lane."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.execution.asset_freshness_policy import (
    ASSET_CLASS_CRYPTO,
    DEFAULT_CRYPTO_MAX_BAR_AGE,
    evaluate_asset_class_freshness,
)
from algotrader.orchestration.strategy_adapter_registry import (
    StrategyAdapterRegistryInput,
    resolve_strategy_adapter,
)
from algotrader.orchestration.strategy_router import (
    StrategyRouteReceipt,
    StrategySignal,
    route_strategy_signals,
    strategy_signal_from_crypto_trend_result,
)
from algotrader.signals.crypto_trend import (
    CRYPTO_TREND_STRATEGY_ID,
    CryptoTrendSignalConfig,
    evaluate_crypto_trend_signal,
    normalize_crypto_symbol,
)

CRYPTO_PAPER_SUPERVISOR_SCHEMA_VERSION = "v4_11c_crypto_paper_supervisor_v1"
CRYPTO_PAPER_SUPERVISOR_DEFAULT_OUTPUT_ROOT = Path("runs/crypto_paper_supervisor/latest")
CRYPTO_PAPER_SUPERVISOR_DEFAULT_BARS_CSV = Path("runs/operator_input/crypto_paper_bars.csv")
CRYPTO_PAPER_SUPERVISOR_SAFETY_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "crypto_preview_only",
    "profit_claim=none",
)
CRYPTO_PAPER_SUPERVISOR_PREFERRED_SYMBOLS = ("BTCUSD", "ETHUSD")
_ASSET_PAYLOAD_FIELDS = (
    "symbol",
    "name",
    "asset_class",
    "class",
    "tradable",
    "status",
    "marginable",
    "fractionable",
    "min_order_size",
    "min_trade_increment",
    "min_order_increment",
    "min_notional",
    "min_order_notional",
)
_ASSET_PAYLOAD_FIELD_LOOKUP = {
    "".join(ch for ch in field.lower() if ch.isalnum()): field
    for field in _ASSET_PAYLOAD_FIELDS
}

CryptoCapabilitySource = Literal["observed", "simulated", "not_observed"]

__all__ = [
    "CRYPTO_PAPER_SUPERVISOR_DEFAULT_BARS_CSV",
    "CRYPTO_PAPER_SUPERVISOR_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_PAPER_SUPERVISOR_PREFERRED_SYMBOLS",
    "CRYPTO_PAPER_SUPERVISOR_SAFETY_LABELS",
    "CRYPTO_PAPER_SUPERVISOR_SCHEMA_VERSION",
    "CryptoCapabilityReceipt",
    "CryptoCapabilitySource",
    "CryptoPaperSupervisorConfig",
    "crypto_asset_capability_payload",
    "discover_crypto_paper_capability",
    "run_crypto_paper_supervisor",
    "write_crypto_paper_supervisor_artifacts",
]


@dataclass(frozen=True, slots=True)
class CryptoCapabilityReceipt:
    """Primitive-only crypto paper capability discovery receipt."""

    universe: str
    asset_class: str
    broker_read_performed: bool
    broker_state_mode: str
    crypto_trading_supported: bool
    eligible_crypto_symbols: tuple[str, ...]
    selected_symbol: str
    selected_symbol_tradable: bool
    selected_symbol_marginable: bool | None
    selected_symbol_fractionable: bool | None
    min_order_size: str
    min_trade_increment: str
    min_order_increment: str
    min_notional: str
    paper_only_mode: bool
    live_endpoint_indicator: bool
    unsupported_jurisdiction_account_blocker: str
    capability_source: CryptoCapabilitySource
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "universe", _fixed_string(self.universe, "crypto", "universe"))
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, ASSET_CLASS_CRYPTO, "asset_class"),
        )
        for field_name in (
            "broker_read_performed",
            "crypto_trading_supported",
            "selected_symbol_tradable",
            "paper_only_mode",
            "live_endpoint_indicator",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")
        for field_name in (
            "selected_symbol_marginable",
            "selected_symbol_fractionable",
        ):
            if getattr(self, field_name) is not None and type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean or None.")
        object.__setattr__(
            self,
            "broker_state_mode",
            _required_string(self.broker_state_mode, "broker_state_mode"),
        )
        object.__setattr__(
            self,
            "eligible_crypto_symbols",
            _crypto_symbol_tuple(self.eligible_crypto_symbols, "eligible_crypto_symbols"),
        )
        selected_symbol = (
            ""
            if self.selected_symbol in (None, "")
            else normalize_crypto_symbol(self.selected_symbol)
        )
        if selected_symbol and selected_symbol not in self.eligible_crypto_symbols:
            raise ValidationError("selected_symbol must be one of eligible_crypto_symbols.")
        object.__setattr__(self, "selected_symbol", selected_symbol)
        for field_name in (
            "min_order_size",
            "min_trade_increment",
            "min_order_increment",
            "min_notional",
            "unsupported_jurisdiction_account_blocker",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_string(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "capability_source",
            _capability_source(self.capability_source),
        )
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        if self.capability_source == "not_observed" and self.crypto_trading_supported:
            raise ValidationError("not_observed capability cannot mark crypto supported.")
        if self.crypto_trading_supported and not self.selected_symbol:
            raise ValidationError("selected_symbol is required when crypto is supported.")

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-safe capability metadata."""

        return {
            "universe": self.universe,
            "asset_class": self.asset_class,
            "broker_read_performed": self.broker_read_performed,
            "broker_state_mode": self.broker_state_mode,
            "crypto_trading_supported": self.crypto_trading_supported,
            "eligible_crypto_symbols": list(self.eligible_crypto_symbols),
            "selected_symbol": self.selected_symbol,
            "selected_symbol_tradable": self.selected_symbol_tradable,
            "selected_symbol_marginable": self.selected_symbol_marginable,
            "selected_symbol_fractionable": self.selected_symbol_fractionable,
            "min_order_size": self.min_order_size,
            "min_trade_increment": self.min_trade_increment,
            "min_order_increment": self.min_order_increment,
            "min_notional": self.min_notional,
            "paper_only_mode": self.paper_only_mode,
            "live_endpoint_indicator": self.live_endpoint_indicator,
            "unsupported_jurisdiction_account_blocker": (
                self.unsupported_jurisdiction_account_blocker
            ),
            "capability_source": self.capability_source,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True, slots=True)
class CryptoPaperSupervisorConfig:
    """Configuration for one crypto paper visibility/no-submit supervisor run."""

    output_root: Path | str = CRYPTO_PAPER_SUPERVISOR_DEFAULT_OUTPUT_ROOT
    bars_csv: Path | str = CRYPTO_PAPER_SUPERVISOR_DEFAULT_BARS_CSV
    preferred_symbols: tuple[str, ...] = CRYPTO_PAPER_SUPERVISOR_PREFERRED_SYMBOLS
    no_submit: bool = True
    crypto_max_bar_age: timedelta = DEFAULT_CRYPTO_MAX_BAR_AGE

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_root", _path(self.output_root, "output_root"))
        object.__setattr__(self, "bars_csv", _path(self.bars_csv, "bars_csv"))
        object.__setattr__(
            self,
            "preferred_symbols",
            _crypto_symbol_tuple(self.preferred_symbols, "preferred_symbols"),
        )
        if type(self.no_submit) is not bool:
            raise ValidationError("no_submit must be a boolean.")
        if self.no_submit is not True:
            raise ValidationError("crypto supervisor seed lane requires no_submit=True.")
        object.__setattr__(
            self,
            "crypto_max_bar_age",
            _nonnegative_timedelta(self.crypto_max_bar_age, "crypto_max_bar_age"),
        )


def discover_crypto_paper_capability(
    *,
    broker: Any | None = None,
    assets: Iterable[Any] | None = None,
    env: Mapping[str, str] | None = None,
    preferred_symbols: Sequence[str] = CRYPTO_PAPER_SUPERVISOR_PREFERRED_SYMBOLS,
    capability_source: CryptoCapabilitySource | None = None,
) -> CryptoCapabilityReceipt:
    """Discover read-only crypto paper support from asset metadata when available."""

    checked_env = _normalized_env(env)
    checked_preferred = _crypto_symbol_tuple(preferred_symbols, "preferred_symbols")
    live_indicator = _live_endpoint_indicator(checked_env)
    blockers: list[str] = []
    if live_indicator:
        blockers.append("live_endpoint_indicator")
        return _capability_receipt(
            broker_read_performed=False,
            broker_state_mode="blocked_live_endpoint_indicator",
            eligible_crypto_symbols=(),
            selected_symbol="",
            source="not_observed",
            live_endpoint_indicator=True,
            blockers=tuple(blockers),
        )

    broker_read_performed = False
    broker_state_mode = "not_observed"
    source: CryptoCapabilitySource = "not_observed"
    asset_items: tuple[Any, ...] = ()
    unsupported_blocker = ""

    if assets is not None:
        asset_items = tuple(assets)
        source = capability_source or "simulated"
        broker_state_mode = "simulated_crypto_assets"
    elif broker is not None:
        broker_read_performed = True
        try:
            asset_items = _broker_assets(broker)
        except Exception as exc:  # noqa: BLE001 - receipt must fail closed.
            broker_state_mode = "broker_asset_read_failed"
            source = "not_observed"
            blockers.append("crypto_asset_discovery_failed")
            unsupported_blocker = _unsupported_account_blocker(exc)
        else:
            broker_state_mode = "alpaca_paper_observed"
            source = capability_source or "observed"

    if source not in {"observed", "simulated", "not_observed"}:
        raise ValidationError("capability_source is invalid.")

    eligible_assets = _eligible_crypto_assets(asset_items)
    eligible_symbols = tuple(asset["symbol"] for asset in eligible_assets)
    selected_symbol = _select_preferred_symbol(eligible_symbols, checked_preferred)
    selected_asset = _asset_by_symbol(eligible_assets, selected_symbol)

    if source == "not_observed" and not blockers:
        blockers.append("crypto_capability_not_observed")
    if source != "not_observed" and not selected_symbol:
        blockers.append("no_eligible_crypto_symbols_observed")
    if unsupported_blocker:
        blockers.append(unsupported_blocker)

    metadata = _selected_asset_metadata(selected_asset, selected_symbol)
    supported = bool(selected_symbol and not unsupported_blocker)
    return CryptoCapabilityReceipt(
        universe="crypto",
        asset_class=ASSET_CLASS_CRYPTO,
        broker_read_performed=broker_read_performed,
        broker_state_mode=broker_state_mode,
        crypto_trading_supported=supported,
        eligible_crypto_symbols=eligible_symbols,
        selected_symbol=selected_symbol,
        selected_symbol_tradable=bool(metadata["selected_symbol_tradable"]),
        selected_symbol_marginable=metadata["selected_symbol_marginable"],
        selected_symbol_fractionable=metadata["selected_symbol_fractionable"],
        min_order_size=metadata["min_order_size"],
        min_trade_increment=metadata["min_trade_increment"],
        min_order_increment=metadata["min_order_increment"],
        min_notional=metadata["min_notional"],
        paper_only_mode=True,
        live_endpoint_indicator=False,
        unsupported_jurisdiction_account_blocker=unsupported_blocker,
        capability_source=source,
        blockers=tuple(_dedupe(blockers)),
    )


def run_crypto_paper_supervisor(
    config: CryptoPaperSupervisorConfig | None = None,
    *,
    env: Mapping[str, str] | None = None,
    broker: Any | None = None,
    assets: Iterable[Any] | None = None,
    timestamp: datetime | str | None = None,
    strategy_adapter_registry: StrategyAdapterRegistryInput | None = None,
    write_artifacts: bool = True,
) -> dict[str, Any]:
    """Run one crypto paper visibility cycle without any broker mutation path."""

    resolved = config or CryptoPaperSupervisorConfig()
    generated_at = _utc_datetime(timestamp or datetime.now(UTC), "timestamp")
    capability = discover_crypto_paper_capability(
        broker=broker,
        assets=assets,
        env=env,
        preferred_symbols=resolved.preferred_symbols,
    )
    selected_symbol = capability.selected_symbol
    bars, data_blockers = _load_crypto_bars(resolved.bars_csv, selected_symbol)
    latest_bar_at = _latest_bar_at(bars, generated_at)
    freshness = evaluate_asset_class_freshness(
        asset_class=ASSET_CLASS_CRYPTO,
        latest_bar_at=latest_bar_at,
        observed_at=generated_at,
        crypto_max_age=resolved.crypto_max_bar_age,
    )
    signal_payload, strategy_signal = _crypto_strategy_signal(
        selected_symbol=selected_symbol,
        bars=bars,
        generated_at=generated_at,
    )
    route_receipt = _route_receipt(strategy_signal)
    adapter_resolution = (
        resolve_strategy_adapter(
            strategy_signal,
            registry=strategy_adapter_registry,
            adapter_mode="preview_only",
        )
        if strategy_signal is not None
        else None
    )
    blockers = _supervisor_blockers(
        capability=capability,
        freshness_status=freshness.data_freshness_status,
        data_blockers=data_blockers,
        signal_payload=signal_payload,
        adapter_resolution=adapter_resolution,
    )
    readiness_status = _readiness_status(
        capability=capability,
        freshness_status=freshness.data_freshness_status,
        signal_payload=signal_payload,
        adapter_resolution=adapter_resolution,
    )
    action_decision = _action_decision(signal_payload, readiness_status)
    record = _build_record(
        config=resolved,
        generated_at=generated_at,
        capability=capability,
        freshness=freshness.to_dict(),
        bars=bars,
        signal_payload=signal_payload,
        route_receipt=route_receipt,
        adapter_resolution=adapter_resolution,
        action_decision=action_decision,
        readiness_status=readiness_status,
        blockers=blockers,
    )
    if write_artifacts:
        record["artifact_paths"] = write_crypto_paper_supervisor_artifacts(
            resolved.output_root,
            record,
        )
    return record


def write_crypto_paper_supervisor_artifacts(
    output_root: Path | str,
    record: Mapping[str, Any],
) -> dict[str, str]:
    """Write local ignored runtime artifacts for one crypto supervisor receipt."""

    root = _path(output_root, "output_root")
    root.mkdir(parents=True, exist_ok=True)
    latest_status = root / "latest_status.json"
    supervisor_receipt = root / "supervisor_receipt.jsonl"
    operating_brief = root / "operating_brief.md"
    latest_status.write_text(
        json.dumps(_json_safe(record), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    supervisor_receipt.write_text(
        json.dumps(_json_safe(_supervisor_receipt(record)), sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    operating_brief.write_text(
        _render_operating_brief(record) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "latest_status": str(latest_status),
        "supervisor_receipt": str(supervisor_receipt),
        "operating_brief": str(operating_brief),
    }


def _capability_receipt(
    *,
    broker_read_performed: bool,
    broker_state_mode: str,
    eligible_crypto_symbols: tuple[str, ...],
    selected_symbol: str,
    source: CryptoCapabilitySource,
    live_endpoint_indicator: bool,
    blockers: tuple[str, ...],
) -> CryptoCapabilityReceipt:
    return CryptoCapabilityReceipt(
        universe="crypto",
        asset_class=ASSET_CLASS_CRYPTO,
        broker_read_performed=broker_read_performed,
        broker_state_mode=broker_state_mode,
        crypto_trading_supported=False,
        eligible_crypto_symbols=eligible_crypto_symbols,
        selected_symbol=selected_symbol,
        selected_symbol_tradable=False,
        selected_symbol_marginable=None,
        selected_symbol_fractionable=None,
        min_order_size="",
        min_trade_increment="",
        min_order_increment="",
        min_notional="",
        paper_only_mode=True,
        live_endpoint_indicator=live_endpoint_indicator,
        unsupported_jurisdiction_account_blocker="",
        capability_source=source,
        blockers=blockers,
    )


def _broker_assets(broker: Any) -> tuple[Any, ...]:
    for method_name in ("list_assets", "get_all_assets", "get_assets"):
        method = getattr(broker, method_name, None)
        if callable(method):
            result = method()
            if result is None:
                return ()
            if isinstance(result, Iterable) and not isinstance(result, (str, bytes)):
                return tuple(result)
            raise ValidationError("broker asset discovery returned non-iterable assets.")
    raise ValidationError("broker asset discovery method is unavailable.")


def _eligible_crypto_assets(values: Iterable[Any]) -> tuple[dict[str, Any], ...]:
    assets: list[dict[str, Any]] = []
    for value in values:
        data = crypto_asset_capability_payload(value)
        symbol = _first_text(data, "symbol", "name")
        if not symbol:
            continue
        normalized_symbol = normalize_crypto_symbol(symbol)
        asset_class = _normalized_enum_text(_first_text(data, "asset_class", "class"))
        if asset_class and asset_class != ASSET_CLASS_CRYPTO:
            continue
        tradable = _bool_field(data, "tradable")
        if tradable is not True:
            continue
        status = _normalized_enum_text(_first_text(data, "status"))
        if status and status not in {"active", "tradable"}:
            continue
        asset: dict[str, Any] = {
            "symbol": normalized_symbol,
            "tradable": tradable,
        }
        for field_name in ("marginable", "fractionable"):
            field_value = _bool_field(data, field_name)
            if field_value is not None:
                asset[field_name] = field_value
        for field_name in (
            "min_order_size",
            "min_trade_increment",
            "min_order_increment",
            "min_notional",
            "min_order_notional",
        ):
            value_text = _first_text(data, field_name)
            if value_text:
                asset[field_name] = value_text
        assets.append(asset)
    return tuple(_dedupe_assets(assets))


def _selected_asset_metadata(
    asset: Mapping[str, Any] | None,
    selected_symbol: str,
) -> dict[str, Any]:
    min_notional = ""
    selected_symbol_tradable = False
    selected_symbol_marginable: bool | None = None
    selected_symbol_fractionable: bool | None = None
    if asset is not None:
        min_notional = _first_text(asset, "min_notional", "min_order_notional")
        selected_symbol_tradable = _bool_field(asset, "tradable") is True
        selected_symbol_marginable = _bool_field(asset, "marginable")
        selected_symbol_fractionable = _bool_field(asset, "fractionable")
    return {
        "selected_symbol_tradable": selected_symbol_tradable,
        "selected_symbol_marginable": selected_symbol_marginable,
        "selected_symbol_fractionable": selected_symbol_fractionable,
        "min_order_size": "" if asset is None else _first_text(asset, "min_order_size"),
        "min_trade_increment": (
            "" if asset is None else _first_text(asset, "min_trade_increment")
        ),
        "min_order_increment": (
            "" if asset is None else _first_text(asset, "min_order_increment")
        ),
        "min_notional": min_notional,
    }


def _load_crypto_bars(path: Path, selected_symbol: str) -> tuple[tuple[Bar, ...], tuple[str, ...]]:
    if not selected_symbol:
        return (), ("crypto_symbol_not_selected",)
    if not path.is_file():
        return (), ("crypto_bars_csv_missing",)
    bars: list[Bar] = []
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            bar = _parse_bar_row(row)
            if bar.symbol == selected_symbol:
                bars.append(bar)
    if not bars:
        return (), ("selected_crypto_symbol_missing_from_bars",)
    return tuple(bars), ()


def _parse_bar_row(row: Mapping[str, object]) -> Bar:
    symbol = normalize_crypto_symbol(_required_row_text(row, "symbol"))
    close = _positive_decimal(_required_row_text(row, "close"), "close")
    open_price = _optional_decimal(_row_text(row, "open")) or close
    high = _optional_decimal(_row_text(row, "high")) or max(open_price, close)
    low = _optional_decimal(_row_text(row, "low")) or min(open_price, close)
    volume = _optional_nonnegative_decimal(_row_text(row, "volume"))
    return Bar(
        symbol=symbol,
        timestamp=_row_datetime(row),
        open=open_price,
        high=max(high, open_price, close),
        low=min(low, open_price, close),
        close=close,
        volume=volume,
    )


def _crypto_strategy_signal(
    *,
    selected_symbol: str,
    bars: tuple[Bar, ...],
    generated_at: datetime,
) -> tuple[dict[str, Any], StrategySignal | None]:
    if not selected_symbol:
        return {
            "strategy_id": CRYPTO_TREND_STRATEGY_ID,
            "symbol": "",
            "asset_class": ASSET_CLASS_CRYPTO,
            "posture": "blocked_no_eligible_symbol",
            "signal_state": "blocked",
            "intended_action": "no_action",
            "submit_allowed": False,
            "broker_action_performed": False,
            "blockers": ["crypto_capability_not_supported"],
            "labels": list(CRYPTO_PAPER_SUPERVISOR_SAFETY_LABELS),
        }, None
    result = evaluate_crypto_trend_signal(
        bars,
        CryptoTrendSignalConfig(as_of=generated_at, symbol=selected_symbol),
    )
    strategy_signal = strategy_signal_from_crypto_trend_result(result)
    payload = result.to_dict()
    payload["signal_state"] = strategy_signal.signal_state
    payload["intended_action"] = strategy_signal.intended_action
    return payload, strategy_signal


def _route_receipt(strategy_signal: StrategySignal | None) -> StrategyRouteReceipt | None:
    if strategy_signal is None:
        return None
    return route_strategy_signals((strategy_signal,))


def _supervisor_blockers(
    *,
    capability: CryptoCapabilityReceipt,
    freshness_status: str,
    data_blockers: tuple[str, ...],
    signal_payload: Mapping[str, Any],
    adapter_resolution: Any,
) -> tuple[str, ...]:
    blockers: list[str] = [*capability.blockers, *data_blockers]
    if capability.capability_source == "not_observed":
        blockers.append("capability_not_observed")
    if (
        capability.capability_source != "not_observed"
        and capability.crypto_trading_supported is not True
    ):
        blockers.append("unsupported_crypto_capability")
    if freshness_status != "current_for_24_7_crypto_lab":
        blockers.append(freshness_status)
    blockers.extend(_string_list(signal_payload.get("blockers")))
    if adapter_resolution is None:
        blockers.append("strategy_adapter_not_resolved")
    elif adapter_resolution.resolution_status != "resolved":
        blockers.extend(adapter_resolution.blockers)
        if adapter_resolution.reason == "strategy_adapter_unsupported_symbol":
            blockers.append("unsupported_crypto_capability")
    blockers.append("crypto_preview_only_no_submit")
    return _dedupe(blockers)


def _readiness_status(
    *,
    capability: CryptoCapabilityReceipt,
    freshness_status: str,
    signal_payload: Mapping[str, Any],
    adapter_resolution: Any,
) -> str:
    if capability.live_endpoint_indicator:
        return "readiness_blocked_live_endpoint_indicator"
    if capability.capability_source == "not_observed":
        return "readiness_blocked_capability_not_observed"
    if capability.crypto_trading_supported is not True:
        return "readiness_blocked_unsupported_crypto_capability"
    if freshness_status != "current_for_24_7_crypto_lab":
        return "readiness_blocked_stale_crypto_data"
    if adapter_resolution is None or adapter_resolution.resolution_status != "resolved":
        if (
            adapter_resolution is not None
            and adapter_resolution.reason == "strategy_adapter_unsupported_symbol"
        ):
            return "readiness_blocked_unsupported_crypto_capability"
        return "readiness_blocked_strategy_adapter"
    if signal_payload.get("posture") == "insufficient_history":
        return "readiness_blocked_insufficient_history"
    return "readiness_blocked_crypto_preview_only_no_submit"


def _action_decision(signal_payload: Mapping[str, Any], readiness_status: str) -> str:
    if (
        readiness_status == "readiness_blocked_crypto_preview_only_no_submit"
        and signal_payload.get("intended_action") == "buy"
    ):
        return "preview_buy/no_submit"
    if readiness_status == "readiness_blocked_crypto_preview_only_no_submit":
        return "observe/no_action"
    if readiness_status == "readiness_preview_only_continue":
        return "observe/no_action"
    if signal_payload.get("posture") == "insufficient_history":
        return "block/insufficient_history"
    if readiness_status == "readiness_blocked_stale_crypto_data":
        return "block/stale_crypto_data"
    return "block/crypto_supervisor"


def _build_record(
    *,
    config: CryptoPaperSupervisorConfig,
    generated_at: datetime,
    capability: CryptoCapabilityReceipt,
    freshness: Mapping[str, Any],
    bars: tuple[Bar, ...],
    signal_payload: Mapping[str, Any],
    route_receipt: StrategyRouteReceipt | None,
    adapter_resolution: Any,
    action_decision: str,
    readiness_status: str,
    blockers: tuple[str, ...],
) -> dict[str, Any]:
    adapter_payload = (
        {
            "resolution_status": "blocked",
            "reason": "strategy_adapter_not_resolved",
            "adapter_id": "",
            "adapter_mode": "preview_only",
            "paper_mutation_allowed": False,
            "blockers": ["strategy_adapter_not_resolved"],
        }
        if adapter_resolution is None
        else adapter_resolution.to_dict()
    )
    selected_symbol = capability.selected_symbol
    final_operator_action = _final_operator_action(readiness_status)
    latest_bar_at = _latest_bar_at(bars, generated_at)
    return {
        "schema_version": CRYPTO_PAPER_SUPERVISOR_SCHEMA_VERSION,
        "universe": "crypto",
        "asset_class": ASSET_CLASS_CRYPTO,
        "run_timestamp": generated_at.isoformat(),
        "input_data_path": str(config.bars_csv),
        "input_data_sha256": _file_sha256(config.bars_csv),
        "selected_symbol": selected_symbol,
        "latest_bar_at": "" if latest_bar_at is None else latest_bar_at.isoformat(),
        "data_freshness_status": freshness.get("data_freshness_status", ""),
        "freshness_policy": dict(freshness),
        "broker_state_mode": capability.broker_state_mode,
        "broker_read_performed": capability.broker_read_performed,
        "capability_source": capability.capability_source,
        "crypto_trading_supported": capability.crypto_trading_supported,
        "crypto_capability": capability.to_dict(),
        "eligible_crypto_symbols": list(capability.eligible_crypto_symbols),
        "selected_symbol_tradable": capability.selected_symbol_tradable,
        "selected_symbol_marginable": capability.selected_symbol_marginable,
        "selected_symbol_fractionable": capability.selected_symbol_fractionable,
        "min_order_size": capability.min_order_size,
        "min_trade_increment": capability.min_trade_increment,
        "min_order_increment": capability.min_order_increment,
        "min_notional": capability.min_notional,
        "unsupported_jurisdiction_account_blocker": (
            capability.unsupported_jurisdiction_account_blocker
        ),
        "strategy_id": signal_payload.get("strategy_id", CRYPTO_TREND_STRATEGY_ID),
        "strategy_signal": dict(signal_payload),
        "strategy_posture": signal_payload.get("posture", ""),
        "strategy_intended_action": signal_payload.get("intended_action", "no_action"),
        "strategy_route_receipt": (
            {} if route_receipt is None else route_receipt.to_dict()
        ),
        "strategy_adapter_resolution": adapter_payload,
        "strategy_adapter_resolution_status": adapter_payload["resolution_status"],
        "strategy_adapter_reason": adapter_payload["reason"],
        "strategy_adapter_id": adapter_payload.get("adapter_id", ""),
        "strategy_adapter_mode": adapter_payload.get("adapter_mode", "preview_only"),
        "strategy_adapter_paper_mutation_allowed": False,
        "paper_mutation_allowed": False,
        "submit_allowed": False,
        "action_decision": action_decision,
        "no_submit_mode": True,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "readiness_status": readiness_status,
        "blockers": list(blockers),
        "final_operator_action": final_operator_action,
        "safety_labels": list(CRYPTO_PAPER_SUPERVISOR_SAFETY_LABELS),
        "paper_only_mode": True,
        "live_endpoint_indicator": capability.live_endpoint_indicator,
    }


def _supervisor_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "schema_version",
        "universe",
        "asset_class",
        "run_timestamp",
        "selected_symbol",
        "data_freshness_status",
        "broker_state_mode",
        "broker_read_performed",
        "capability_source",
        "crypto_trading_supported",
        "eligible_crypto_symbols",
        "selected_symbol_tradable",
        "selected_symbol_marginable",
        "selected_symbol_fractionable",
        "min_order_size",
        "min_trade_increment",
        "min_order_increment",
        "min_notional",
        "unsupported_jurisdiction_account_blocker",
        "strategy_id",
        "strategy_posture",
        "strategy_adapter_mode",
        "strategy_adapter_resolution_status",
        "strategy_adapter_reason",
        "action_decision",
        "no_submit_mode",
        "paper_submit_performed",
        "broker_mutation_performed",
        "live_mutation_performed",
        "readiness_status",
        "blockers",
        "final_operator_action",
        "safety_labels",
    )
    return {field: _json_safe(record.get(field)) for field in fields}


def _render_operating_brief(record: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Crypto Paper Supervisor Brief",
            "",
            f"- Universe: `{record.get('universe', '')}`",
            f"- Selected symbol: `{record.get('selected_symbol', '')}`",
            f"- Data freshness: `{record.get('data_freshness_status', '')}`",
            f"- Broker-state mode: `{record.get('broker_state_mode', '')}`",
            f"- Broker read performed: `{record.get('broker_read_performed')}`",
            f"- Capability source: `{record.get('capability_source', '')}`",
            f"- Crypto trading supported: `{record.get('crypto_trading_supported')}`",
            f"- Selected symbol tradable: `{record.get('selected_symbol_tradable')}`",
            f"- Strategy posture: `{record.get('strategy_posture', '')}`",
            f"- Adapter mode: `{record.get('strategy_adapter_mode', '')}`",
            f"- Action decision: `{record.get('action_decision', '')}`",
            f"- Readiness: `{record.get('readiness_status', '')}`",
            f"- Paper submit performed: `{record.get('paper_submit_performed')}`",
            f"- Broker mutation performed: `{record.get('broker_mutation_performed')}`",
            f"- Live mutation performed: `{record.get('live_mutation_performed')}`",
            f"- Final operator action: `{record.get('final_operator_action', '')}`",
        ]
    )


def _final_operator_action(readiness_status: str) -> str:
    actions = {
        "readiness_blocked_live_endpoint_indicator": "block_crypto_lane_live_indicator",
        "readiness_blocked_crypto_capability_not_supported": (
            "block_crypto_lane_until_capability_observed"
        ),
        "readiness_blocked_capability_not_observed": (
            "block_crypto_lane_until_capability_observed"
        ),
        "readiness_blocked_unsupported_crypto_capability": (
            "block_crypto_lane_unsupported_capability"
        ),
        "readiness_blocked_stale_crypto_data": "block_crypto_lane_until_data_fresh",
        "readiness_blocked_strategy_adapter": "block_crypto_lane_adapter_review",
        "readiness_blocked_insufficient_history": "observe_until_crypto_history_available",
        "readiness_blocked_crypto_preview_only_no_submit": (
            "observe_crypto_preview_no_submit"
        ),
        "readiness_preview_only_continue": "continue_crypto_observation",
    }
    return actions.get(readiness_status, "block_crypto_lane_for_review")


def _latest_bar_at(bars: Sequence[Bar], observed_at: datetime) -> datetime | None:
    usable = [
        _utc_datetime(bar.timestamp, "timestamp")
        for bar in bars
        if _utc_datetime(bar.timestamp, "timestamp") <= observed_at
    ]
    return max(usable) if usable else None


def _select_preferred_symbol(
    eligible_symbols: Sequence[str],
    preferred_symbols: Sequence[str],
) -> str:
    eligible_set = set(eligible_symbols)
    for symbol in preferred_symbols:
        normalized = normalize_crypto_symbol(symbol)
        if normalized in eligible_set:
            return normalized
    return ""


def _asset_by_symbol(
    assets: Sequence[Mapping[str, Any]],
    symbol: str,
) -> Mapping[str, Any] | None:
    if not symbol:
        return None
    for asset in assets:
        if asset.get("symbol") == symbol:
            return asset
    return None


def _dedupe_assets(assets: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for asset in assets:
        symbol = asset["symbol"]
        if symbol in seen:
            continue
        seen.add(symbol)
        result.append(dict(asset))
    return tuple(result)


def crypto_asset_capability_payload(value: Any) -> dict[str, Any]:
    """Return allowlisted primitive crypto asset capability fields."""

    if isinstance(value, Mapping):
        return _allowed_asset_payload_fields(value)
    data = _model_dump_payload(value) or {}
    for name in _ASSET_PAYLOAD_FIELDS:
        if _first_text(data, name):
            continue
        try:
            item = getattr(value, name)
        except Exception:
            continue
        if item is None or callable(item):
            continue
        data[name] = item
    return data


def _model_dump_payload(value: Any) -> dict[str, Any] | None:
    model_dump = getattr(value, "model_dump", None)
    if not callable(model_dump):
        return None
    try:
        dumped = model_dump(mode="json")
    except TypeError:
        try:
            dumped = model_dump()
        except Exception:
            return None
    except Exception:
        return None
    if not isinstance(dumped, Mapping):
        return None
    return _allowed_asset_payload_fields(dumped)


def _allowed_asset_payload_fields(data: Mapping[str, Any]) -> dict[str, Any]:
    allowed: dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            continue
        field = _ASSET_PAYLOAD_FIELD_LOOKUP.get(_payload_field_lookup_key(key))
        if field is None:
            continue
        allowed[field] = value
    return allowed


def _payload_field_lookup_key(value: object) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _unsupported_account_blocker(exc: Exception) -> str:
    message = str(exc).lower()
    if "jurisdiction" in message or "unsupported" in message:
        return "unsupported_jurisdiction_or_account"
    return ""


def _live_endpoint_indicator(env: Mapping[str, str]) -> bool:
    if env.get("APP_PROFILE", "").strip().lower() == "live":
        return True
    for name in ("ALPACA_BASE_URL", "ALPACA_PAPER_BASE_URL", "APCA_API_BASE_URL"):
        value = env.get(name, "").strip().lower()
        if value and "alpaca" in value and "paper" not in value:
            return True
    return False


def _normalized_env(env: Mapping[str, str] | None) -> dict[str, str]:
    if env is None:
        return {}
    return {str(key): str(value) for key, value in env.items()}


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _row_text(row: Mapping[str, object], field_name: str) -> str:
    for key, value in row.items():
        if str(key).strip().lower() == field_name:
            return "" if value is None else str(value).strip()
    return ""


def _required_row_text(row: Mapping[str, object], field_name: str) -> str:
    value = _row_text(row, field_name)
    if not value:
        raise ValidationError(f"{field_name} is required in CSV.")
    return value


def _row_datetime(row: Mapping[str, object]) -> datetime:
    for field_name in ("timestamp", "datetime", "date"):
        text = _row_text(row, field_name)
        if text:
            return _utc_datetime(text, field_name)
    raise ValidationError("timestamp is required in CSV.")


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
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _positive_decimal(value: object, field_name: str) -> Decimal:
    try:
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a positive decimal.") from exc
    if not decimal_value.is_finite() or decimal_value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be a positive decimal.")
    return decimal_value


def _optional_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    return _positive_decimal(value, "decimal")


def _optional_nonnegative_decimal(value: object) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError("decimal must be a non-negative decimal.") from exc
    if not decimal_value.is_finite() or decimal_value < Decimal("0"):
        raise ValidationError("decimal must be a non-negative decimal.")
    return decimal_value


def _path(value: object, field_name: str) -> Path:
    if type(value) is not str and not isinstance(value, Path):
        raise ValidationError(f"{field_name} must be a filesystem path.")
    return Path(value)


def _nonnegative_timedelta(value: object, field_name: str) -> timedelta:
    if not isinstance(value, timedelta) or value.total_seconds() < 0:
        raise ValidationError(f"{field_name} must be a non-negative timedelta.")
    return value


def _capability_source(value: object) -> CryptoCapabilitySource:
    if type(value) is not str or value not in {"observed", "simulated", "not_observed"}:
        raise ValidationError("capability_source is invalid.")
    return value  # type: ignore[return-value]


def _fixed_string(value: object, expected: str, field_name: str) -> str:
    text = _required_string(value, field_name)
    if text != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")
    return text


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _optional_string(value: object, field_name: str) -> str:
    if value in (None, ""):
        return ""
    return _required_string(value, field_name)


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")
    return tuple(_required_string(value, f"{field_name}[]") for value in values)


def _crypto_symbol_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of symbols.")
    return tuple(normalize_crypto_symbol(value) for value in values)


def _first_text(data: Mapping[str, Any], *names: str) -> str:
    for name in names:
        for key, value in data.items():
            if str(key).strip().lower() == name:
                return _field_text(value)
    return ""


def _field_text(value: Any) -> str:
    if value is None:
        return ""
    enum_value = getattr(value, "value", None)
    if type(enum_value) is str:
        return enum_value.strip()
    return str(value).strip()


def _normalized_enum_text(value: Any) -> str:
    text = _field_text(value)
    if not text:
        return ""
    normalized = text.lower().replace(" ", "_")
    if "." in normalized:
        normalized = normalized.rsplit(".", 1)[-1]
    return normalized


def _bool_field(data: Mapping[str, Any], field_name: str) -> bool | None:
    text = _first_text(data, field_name).lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    value = data.get(field_name)
    return value if type(value) is bool else None


def _string_list(value: object) -> list[str]:
    if type(value) in (list, tuple):
        return [str(item) for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value)]


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return tuple(result)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value
