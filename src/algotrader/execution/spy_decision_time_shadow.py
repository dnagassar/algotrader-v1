"""Paper-only SPY decision-time shadow and adjusted-close reconciliation.

The capture path reads one bounded Alpaca Market Data snapshot for SPY during
an active NYSE session, combines its latest IEX trade with the existing
adjusted-close history, and records an advisory SMA50/200 target posture.  It
does not inspect a broker account, construct an order, or authorize submission.

The reconciliation path is credential-free and network-free.  Once the
authoritative Tiingo canonical CSV contains the captured session, it evaluates
the same signal on the adjusted close and records whether the provisional
target posture matched or diverged.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any
from zoneinfo import ZoneInfo

from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.execution.exchange_session import (
    ExchangeSession,
    NyseExchangeSessionCalendar,
)
from algotrader.execution.live_capital_interlock import (
    evaluate_live_capital_interlock,
)
from algotrader.execution.secure_credential_provider import (
    CredentialFamily,
    CredentialProvider,
    CredentialProviderError,
    CredentialReference,
    WINDOWS_PROVIDER_NAME,
    provider_from_name,
)
from algotrader.research.local_daily_bars import load_local_daily_bars_csv
from algotrader.signals.etf_sma_evaluator import (
    EtfSmaSignalConfig,
    evaluate_etf_sma_signal,
)

__all__ = [
    "ALPACA_SPY_SNAPSHOT_HOST",
    "ALPACA_SPY_SNAPSHOT_PATH",
    "DEFAULT_MARKET_DATA_CREDENTIAL_REFERENCE",
    "SPY_DECISION_TIME_EXECUTION_WINDOWS",
    "SpyDecisionSnapshot",
    "alpaca_bounded_spy_snapshot_get",
    "capture_spy_decision_time_shadow",
    "main",
    "normalize_alpaca_spy_snapshot",
    "reconcile_spy_decision_time_shadow",
]

_MILESTONE = "v5.54"
_SYMBOL = "SPY"
_CAPTURE_RECORD_TYPE = "spy_decision_time_shadow_provisional"
_RECONCILIATION_RECORD_TYPE = "spy_decision_time_shadow_reconciliation"
_SCHEMA_VERSION = 1
_EXPECTED_PAPER_ENDPOINT = "https://paper-api.alpaca.markets"
_CANONICAL_CSV_RELPATH = Path(
    "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
)
_SHADOW_ROOT_RELPATH = Path("runs/paper_lab/spy_decision_time_shadow")
_PROVISIONAL_FILENAME = "provisional.json"
_RECONCILIATION_FILENAME = "reconciliation.json"
_SHORT_WINDOW = 50
_LONG_WINDOW = 200
_MAX_TRADE_AGE_SECONDS = 300
_MARKET_CLOSE_LEAD_SECONDS = 300
_HTTP_TIMEOUT_SECONDS = 10.0
_MAX_RESPONSE_BYTES = 262_144
_MAX_HTTP_GETS_PER_INVOCATION = 1
_FEED = "iex"
_NEW_YORK = ZoneInfo("America/New_York")

ALPACA_SPY_SNAPSHOT_HOST = "data.alpaca.markets"
ALPACA_SPY_SNAPSHOT_PATH = "/v2/stocks/SPY/snapshot?feed=iex"
DEFAULT_MARKET_DATA_CREDENTIAL_REFERENCE = (
    "wincred:algotrader/v5.35/alpaca-market-data/production"
)
SPY_DECISION_TIME_EXECUTION_WINDOWS = (
    "next_session_open",
    "market_close",
)

SnapshotFetcher = Callable[[str, str], "SpyDecisionSnapshot"]


class SpyDecisionTimeShadowError(RuntimeError):
    """Sanitized, stable failure classification for the shadow lane."""

    def __init__(self, classification: str) -> None:
        self.classification = classification
        super().__init__(classification)


@dataclass(frozen=True, slots=True)
class SpyDecisionSnapshot:
    """Validated, credential-free fields from one Alpaca SPY snapshot."""

    daily_bar_at: datetime
    latest_trade_at: datetime
    daily_open: Decimal
    daily_high: Decimal
    daily_low: Decimal
    daily_close: Decimal
    daily_volume: int
    latest_trade_price: Decimal
    feed: str = _FEED

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "daily_bar_at",
            _utc_datetime(self.daily_bar_at, "daily_bar_at"),
        )
        object.__setattr__(
            self,
            "latest_trade_at",
            _utc_datetime(self.latest_trade_at, "latest_trade_at"),
        )
        for field_name in (
            "daily_open",
            "daily_high",
            "daily_low",
            "daily_close",
            "latest_trade_price",
        ):
            object.__setattr__(
                self,
                field_name,
                _positive_decimal(getattr(self, field_name), field_name),
            )
        if type(self.daily_volume) is not int or self.daily_volume < 0:
            raise ValidationError("daily_volume must be a non-negative integer.")
        if self.feed != _FEED:
            raise ValidationError("feed must be exactly iex.")
        if self.daily_high < max(
            self.daily_open,
            self.daily_low,
            self.daily_close,
        ):
            raise ValidationError("daily_high is inconsistent with OHLC values.")
        if self.daily_low > min(
            self.daily_open,
            self.daily_high,
            self.daily_close,
        ):
            raise ValidationError("daily_low is inconsistent with OHLC values.")


def alpaca_bounded_spy_snapshot_get(
    api_key_id: str,
    api_secret_key: str,
    *,
    connection_factory: Callable[..., Any] | None = None,
) -> SpyDecisionSnapshot:
    """Perform one exact-host, exact-path, bounded Alpaca SPY snapshot GET."""

    api_key = _secret_text(api_key_id)
    api_secret = _secret_text(api_secret_key)
    try:
        import http.client

        factory = http.client.HTTPSConnection if connection_factory is None else connection_factory
        connection = factory(
            ALPACA_SPY_SNAPSHOT_HOST,
            timeout=_HTTP_TIMEOUT_SECONDS,
        )
        try:
            connection.request(
                "GET",
                ALPACA_SPY_SNAPSHOT_PATH,
                headers={
                    "APCA-API-KEY-ID": api_key,
                    "APCA-API-SECRET-KEY": api_secret,
                    "Accept": "application/json",
                },
            )
            response = connection.getresponse()
            status = int(response.status)
            content = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(content) > _MAX_RESPONSE_BYTES:
                raise SpyDecisionTimeShadowError("market_data_response_too_large")
            if status < 200 or status >= 300:
                raise SpyDecisionTimeShadowError(_http_status_classification(status))
        finally:
            connection.close()
    except SpyDecisionTimeShadowError:
        raise
    except (TimeoutError, OSError):
        raise SpyDecisionTimeShadowError("market_data_network_error") from None
    except Exception:
        raise SpyDecisionTimeShadowError("market_data_transport_error") from None

    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SpyDecisionTimeShadowError("market_data_response_invalid_json") from None
    return normalize_alpaca_spy_snapshot(payload)


def normalize_alpaca_spy_snapshot(payload: object) -> SpyDecisionSnapshot:
    """Normalize the two snapshot objects used by the decision-time lane."""

    if not isinstance(payload, Mapping):
        raise SpyDecisionTimeShadowError("market_data_snapshot_invalid")
    daily = payload.get("dailyBar")
    trade = payload.get("latestTrade")
    if not isinstance(daily, Mapping) or not isinstance(trade, Mapping):
        raise SpyDecisionTimeShadowError("market_data_snapshot_incomplete")
    try:
        return SpyDecisionSnapshot(
            daily_bar_at=_timestamp(daily.get("t"), "dailyBar.t"),
            latest_trade_at=_timestamp(trade.get("t"), "latestTrade.t"),
            daily_open=_decimal(daily.get("o"), "dailyBar.o"),
            daily_high=_decimal(daily.get("h"), "dailyBar.h"),
            daily_low=_decimal(daily.get("l"), "dailyBar.l"),
            daily_close=_decimal(daily.get("c"), "dailyBar.c"),
            daily_volume=_non_negative_int(daily.get("v"), "dailyBar.v"),
            latest_trade_price=_decimal(trade.get("p"), "latestTrade.p"),
        )
    except ValidationError:
        raise SpyDecisionTimeShadowError("market_data_snapshot_invalid") from None


def capture_spy_decision_time_shadow(
    *,
    as_of: str,
    apply: bool = False,
    execution_window: str = "next_session_open",
    credential_reference: CredentialReference | str = (
        DEFAULT_MARKET_DATA_CREDENTIAL_REFERENCE
    ),
    credential_provider: CredentialProvider | None = None,
    snapshot_fetcher: SnapshotFetcher | None = None,
    env: Mapping[str, str] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Capture one idempotent, paper-only provisional SPY target posture."""

    result = _base_result(mode="capture", apply=apply)
    try:
        observed_at = _parse_as_of(as_of)
        checked_window = _execution_window(execution_window)
        checked_root = _canonical_root(root)
        session = _active_session(observed_at)
        canonical_csv = _canonical_csv(checked_root)
        history, canonical_latest_date = _adjusted_history(
            canonical_csv,
            as_of_date=session.session_date - timedelta(days=1),
        )
        previous_session = _previous_completed_session(session.opens_at)
        if canonical_latest_date != previous_session.session_date:
            raise SpyDecisionTimeShadowError("canonical_history_not_current")
        if len(history) < _LONG_WINDOW:
            raise SpyDecisionTimeShadowError("canonical_history_insufficient")
        planned_execution_at = _planned_execution_at(
            session,
            observed_at,
            checked_window,
        )
        receipt_path = _provisional_path(checked_root, session.session_date)
    except SpyDecisionTimeShadowError as exc:
        return _capture_refusal(result, exc.classification)
    except (OSError, ValidationError):
        return _capture_refusal(result, "canonical_history_invalid")

    result.update(
        {
            "session_id": session.session_date.isoformat(),
            "observed_at": observed_at.isoformat(),
            "execution_window": checked_window,
            "planned_execution_at": planned_execution_at.isoformat(),
            "canonical_latest_bar_date": canonical_latest_date.isoformat(),
            "receipt_path": _relative_text(receipt_path, checked_root),
        }
    )

    if receipt_path.exists():
        existing = _read_provisional_receipt(
            receipt_path,
            expected_session=session.session_date,
        )
        if existing is None:
            return _capture_refusal(result, "provisional_receipt_invalid")
        result.update(
            {
                "state": "provisional_decision_already_recorded",
                "decision": existing["decision"],
                "posture": existing["posture"],
                "network_access_attempted": False,
                "credential_access_attempted": False,
                "exit_code": 0,
            }
        )
        return result

    guard_env = _paper_guard_environment(os.environ if env is None else env)
    verdict = evaluate_live_capital_interlock(guard_env)
    result["interlock_verdict"] = verdict.to_dict()
    if not verdict.paper_boundary_ok:
        return _capture_refusal(result, "paper_interlock_refused")

    if not apply:
        result.update(
            {
                "state": "capture_dry_run_eligible",
                "apply_eligible": True,
                "exit_code": 1,
            }
        )
        return result

    result["credential_access_attempted"] = True
    try:
        reference = (
            credential_reference
            if isinstance(credential_reference, CredentialReference)
            else CredentialReference(credential_reference)
        )
        if reference.family is not CredentialFamily.ALPACA_MARKET_DATA:
            raise CredentialProviderError("credential_family_mismatch")
        provider = (
            provider_from_name(WINDOWS_PROVIDER_NAME)
            if credential_provider is None
            else credential_provider
        )
        lease = provider.open(
            reference,
            expected_family=CredentialFamily.ALPACA_MARKET_DATA,
        )
    except CredentialProviderError as exc:
        return _capture_refusal(result, exc.classification)

    active_fetcher = (
        alpaca_bounded_spy_snapshot_get
        if snapshot_fetcher is None
        else snapshot_fetcher
    )
    result["network_access_attempted"] = True
    try:
        with lease:
            snapshot = lease.use(
                lambda api_key, api_secret, _account: active_fetcher(
                    api_key,
                    api_secret,
                )
            )
        if not isinstance(snapshot, SpyDecisionSnapshot):
            raise SpyDecisionTimeShadowError("market_data_snapshot_invalid")
        _validate_snapshot_for_session(snapshot, session, observed_at)
        receipt = _build_provisional_receipt(
            snapshot=snapshot,
            history=history,
            canonical_csv=canonical_csv,
            canonical_latest_date=canonical_latest_date,
            session=session,
            observed_at=observed_at,
            execution_window=checked_window,
            planned_execution_at=planned_execution_at,
        )
        _write_json_once(receipt_path, receipt)
    except SpyDecisionTimeShadowError as exc:
        return _capture_refusal(result, exc.classification)
    except CredentialProviderError as exc:
        return _capture_refusal(result, exc.classification)
    except (OSError, ValidationError):
        return _capture_refusal(result, "provisional_receipt_write_failed")

    result.update(
        {
            "state": "provisional_decision_recorded",
            "decision": receipt["decision"],
            "posture": receipt["posture"],
            "latest_trade_at": receipt["latest_trade_at"],
            "data_age_seconds": receipt["data_age_seconds"],
            "provisional_close": receipt["provisional_close"],
            "sma50": receipt["sma50"],
            "sma200": receipt["sma200"],
            "reconciliation_state": "pending_authoritative_adjusted_bar",
            "exit_code": 0,
        }
    )
    return result


def reconcile_spy_decision_time_shadow(
    *,
    session_id: str,
    as_of: str,
    root: Path | None = None,
) -> dict[str, Any]:
    """Reconcile a provisional posture with the canonical adjusted close."""

    result = _base_result(mode="reconcile", apply=True)
    try:
        observed_at = _parse_as_of(as_of)
        session_date = _date_text(session_id, "session_id")
        checked_root = _canonical_root(root)
        provisional_path = _provisional_path(checked_root, session_date)
        reconciliation_path = _reconciliation_path(checked_root, session_date)
        result.update(
            {
                "session_id": session_date.isoformat(),
                "observed_at": observed_at.isoformat(),
                "provisional_receipt_path": _relative_text(
                    provisional_path,
                    checked_root,
                ),
                "reconciliation_receipt_path": _relative_text(
                    reconciliation_path,
                    checked_root,
                ),
            }
        )
        if not provisional_path.is_file():
            result.update(
                {
                    "state": "provisional_decision_not_captured",
                    "exit_code": 0,
                }
            )
            return result
        provisional = _read_provisional_receipt(
            provisional_path,
            expected_session=session_date,
        )
        if provisional is None:
            return _reconciliation_refusal(result, "provisional_receipt_invalid")
        if reconciliation_path.exists():
            existing = _read_reconciliation_receipt(
                reconciliation_path,
                expected_session=session_date,
            )
            if existing is None:
                return _reconciliation_refusal(
                    result,
                    "reconciliation_receipt_invalid",
                )
            result.update(
                {
                    "state": "reconciliation_already_recorded",
                    "classification": existing["classification"],
                    "provisional_decision": existing["provisional_decision"],
                    "authoritative_decision": existing["authoritative_decision"],
                    "exit_code": 0,
                }
            )
            return result
        canonical_csv = _canonical_csv(checked_root)
        history, canonical_latest_date = _adjusted_history(
            canonical_csv,
            as_of_date=session_date,
            allow_future_rows=True,
        )
    except SpyDecisionTimeShadowError as exc:
        return _reconciliation_refusal(result, exc.classification)
    except (OSError, ValidationError):
        return _reconciliation_refusal(result, "canonical_history_invalid")

    if canonical_latest_date < session_date:
        result.update(
            {
                "state": "pending_authoritative_adjusted_bar",
                "canonical_latest_bar_date": canonical_latest_date.isoformat(),
                "exit_code": 1,
            }
        )
        return result
    if canonical_latest_date != session_date:
        return _reconciliation_refusal(result, "canonical_session_bar_missing")

    try:
        signal = evaluate_etf_sma_signal(
            history,
            EtfSmaSignalConfig(
                as_of=datetime.combine(session_date, time.max, tzinfo=UTC),
                symbol=_SYMBOL,
                short_window=_SHORT_WINDOW,
                long_window=_LONG_WINDOW,
            ),
        )
        authoritative = signal.to_dict()
        authoritative_decision = _decision_for_posture(signal.posture)
        classification = (
            "matched"
            if authoritative_decision == provisional["decision"]
            else "diverged"
        )
        receipt = {
            "record_type": _RECONCILIATION_RECORD_TYPE,
            "schema_version": _SCHEMA_VERSION,
            "milestone": _MILESTONE,
            "session_id": session_date.isoformat(),
            "reconciled_at": observed_at.isoformat(),
            "classification": classification,
            "provisional_decision": provisional["decision"],
            "authoritative_decision": authoritative_decision,
            "provisional_posture": provisional["posture"],
            "authoritative_posture": signal.posture,
            "provisional_close": provisional["provisional_close"],
            "authoritative_adjusted_close": authoritative["latest_close"],
            "provisional_sma50": provisional["sma50"],
            "authoritative_sma50": authoritative["short_sma"],
            "provisional_sma200": provisional["sma200"],
            "authoritative_sma200": authoritative["long_sma"],
            "provisional_receipt_sha256": _sha256(provisional_path),
            "canonical_csv_sha256": _sha256(canonical_csv),
            "price_basis": "authoritative_tiingo_adjusted_close",
            "network_access_attempted": False,
            "credential_access_attempted": False,
            "broker_access_attempted": False,
            "broker_mutation_performed": False,
            "paper_submit_performed": False,
            "submitted": False,
            "mutated": False,
            "live_trading_performed": False,
            "live_authorized": False,
            "profit_claim": "none",
        }
        _write_json_once(reconciliation_path, receipt)
    except (OSError, ValidationError):
        return _reconciliation_refusal(result, "reconciliation_write_failed")

    result.update(
        {
            "state": "reconciled",
            "classification": classification,
            "provisional_decision": provisional["decision"],
            "authoritative_decision": authoritative_decision,
            "canonical_latest_bar_date": canonical_latest_date.isoformat(),
            "exit_code": 0,
        }
    )
    return result


def _build_provisional_receipt(
    *,
    snapshot: SpyDecisionSnapshot,
    history: tuple[Bar, ...],
    canonical_csv: Path,
    canonical_latest_date: date,
    session: ExchangeSession,
    observed_at: datetime,
    execution_window: str,
    planned_execution_at: datetime,
) -> dict[str, Any]:
    provisional_close = snapshot.latest_trade_price
    provisional_bar = Bar(
        symbol=_SYMBOL,
        timestamp=datetime.combine(session.session_date, time.min, tzinfo=UTC),
        open=provisional_close,
        high=provisional_close,
        low=provisional_close,
        close=provisional_close,
        volume=Decimal(snapshot.daily_volume),
    )
    signal = evaluate_etf_sma_signal(
        (*history, provisional_bar),
        EtfSmaSignalConfig(
            as_of=observed_at,
            symbol=_SYMBOL,
            short_window=_SHORT_WINDOW,
            long_window=_LONG_WINDOW,
        ),
    )
    signal_payload = signal.to_dict()
    return {
        "record_type": _CAPTURE_RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "milestone": _MILESTONE,
        "session_id": session.session_date.isoformat(),
        "observed_at": observed_at.isoformat(),
        "latest_trade_at": snapshot.latest_trade_at.isoformat(),
        "data_age_seconds": int(
            (observed_at - snapshot.latest_trade_at).total_seconds()
        ),
        "source": "alpaca_market_data_snapshot",
        "source_host": ALPACA_SPY_SNAPSHOT_HOST,
        "source_path": ALPACA_SPY_SNAPSHOT_PATH,
        "source_method": "GET",
        "feed": snapshot.feed,
        "feed_scope": "iex_single_exchange_not_consolidated_sip",
        "price_basis": "current_iex_trade_as_provisional_adjusted_close_proxy",
        "provisional_close": signal_payload["latest_close"],
        "sma50": signal_payload["short_sma"],
        "sma200": signal_payload["long_sma"],
        "posture": signal.posture,
        "decision": _decision_for_posture(signal.posture),
        "execution_window": execution_window,
        "planned_execution_at": planned_execution_at.isoformat(),
        "market_closes_at": session.closes_at.isoformat(),
        "canonical_latest_bar_date": canonical_latest_date.isoformat(),
        "canonical_csv_sha256": _sha256(canonical_csv),
        "reconciliation_state": "pending_authoritative_adjusted_bar",
        "http_get_limit": _MAX_HTTP_GETS_PER_INVOCATION,
        "http_timeout_seconds": _HTTP_TIMEOUT_SECONDS,
        "http_response_byte_limit": _MAX_RESPONSE_BYTES,
        "network_access_attempted": True,
        "credential_access_attempted": True,
        "paper_profile_guarded": True,
        "broker_access_attempted": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "submitted": False,
        "mutated": False,
        "live_trading_performed": False,
        "live_authorized": False,
        "execution_intent_created": False,
        "execution_plan_created": False,
        "profit_claim": "none",
    }


def _validate_snapshot_for_session(
    snapshot: SpyDecisionSnapshot,
    session: ExchangeSession,
    observed_at: datetime,
) -> None:
    if snapshot.daily_bar_at.astimezone(session.opens_at.tzinfo).date() != (
        session.session_date
    ):
        raise SpyDecisionTimeShadowError("snapshot_daily_bar_wrong_session")
    if not session.opens_at <= snapshot.latest_trade_at < session.closes_at:
        raise SpyDecisionTimeShadowError("snapshot_latest_trade_outside_session")
    if snapshot.latest_trade_at > observed_at + timedelta(seconds=5):
        raise SpyDecisionTimeShadowError("snapshot_latest_trade_future_dated")
    age_seconds = int((observed_at - snapshot.latest_trade_at).total_seconds())
    if age_seconds > _MAX_TRADE_AGE_SECONDS:
        raise SpyDecisionTimeShadowError("snapshot_latest_trade_stale")


def _adjusted_history(
    canonical_csv: Path,
    *,
    as_of_date: date,
    allow_future_rows: bool = False,
) -> tuple[tuple[Bar, ...], date]:
    result = load_local_daily_bars_csv(
        canonical_csv,
        symbol=_SYMBOL,
        as_of=as_of_date,
    )
    if (
        not result.input_sorted_by_date
        or result.ignored_wrong_symbol_row_count
        or (result.ignored_future_bar_count and not allow_future_rows)
        or not result.usable_bars
    ):
        raise SpyDecisionTimeShadowError("canonical_history_invalid")
    bars = tuple(
        Bar(
            symbol=item.symbol,
            timestamp=datetime.combine(item.date, time.min, tzinfo=UTC),
            open=item.adjusted_close,
            high=item.adjusted_close,
            low=item.adjusted_close,
            close=item.adjusted_close,
            volume=Decimal(item.volume),
        )
        for item in result.usable_bars
    )
    return bars, result.usable_bars[-1].date


def _active_session(observed_at: datetime) -> ExchangeSession:
    calendar = NyseExchangeSessionCalendar()
    session = calendar.session_for_date(observed_at.astimezone(_NEW_YORK).date())
    if session is None:
        raise SpyDecisionTimeShadowError("not_nyse_session")
    if observed_at < session.opens_at:
        raise SpyDecisionTimeShadowError("session_not_open")
    if observed_at >= session.closes_at:
        raise SpyDecisionTimeShadowError("session_already_closed")
    return session


def _previous_completed_session(observed_at: datetime) -> ExchangeSession:
    session = NyseExchangeSessionCalendar().latest_completed_session_on_or_before(
        observed_at - timedelta(microseconds=1)
    )
    if session is None:
        raise SpyDecisionTimeShadowError("previous_nyse_session_unavailable")
    return session


def _next_session(current: ExchangeSession) -> ExchangeSession:
    calendar = NyseExchangeSessionCalendar()
    for offset in range(1, 11):
        candidate = calendar.session_for_date(
            current.session_date + timedelta(days=offset)
        )
        if candidate is not None:
            return candidate
    raise SpyDecisionTimeShadowError("next_nyse_session_unavailable")


def _planned_execution_at(
    session: ExchangeSession,
    observed_at: datetime,
    execution_window: str,
) -> datetime:
    if execution_window == "next_session_open":
        return _next_session(session).opens_at
    latest_eligible = session.closes_at - timedelta(
        seconds=_MARKET_CLOSE_LEAD_SECONDS
    )
    if observed_at > latest_eligible:
        raise SpyDecisionTimeShadowError("market_close_shadow_window_elapsed")
    return session.closes_at


def _paper_guard_environment(source: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(source, Mapping):
        raise ValidationError("env must be a mapping.")
    guard = {
        str(key): str(value)
        for key, value in source.items()
        if isinstance(key, str) and isinstance(value, str)
    }
    guard.setdefault("APP_PROFILE", "paper")
    guard.setdefault("ALPACA_PAPER_BASE_URL", _EXPECTED_PAPER_ENDPOINT)
    guard.setdefault("APCA_API_BASE_URL", _EXPECTED_PAPER_ENDPOINT)
    # The interlock composes the legacy AlpacaPaperConfig boundary, which
    # requires credential *presence*.  These fixed non-secret sentinels
    # represent the secure lease that is opened only after this live-signal
    # preflight passes; real values never enter this mapping or any verdict.
    guard.setdefault("ALPACA_API_KEY", "opaque-secure-lease")
    guard.setdefault("ALPACA_SECRET_KEY", "opaque-secure-lease")
    return guard


def _canonical_root(value: Path | None) -> Path:
    root = Path.cwd().resolve() if value is None else Path(value).resolve()
    if not (root / "pyproject.toml").is_file():
        raise SpyDecisionTimeShadowError("noncanonical_target")
    if not (root / "src" / "algotrader").is_dir():
        raise SpyDecisionTimeShadowError("noncanonical_target")
    return root


def _canonical_csv(root: Path) -> Path:
    path = (root / _CANONICAL_CSV_RELPATH).resolve()
    _require_under_root(path, root)
    if not path.is_file():
        raise SpyDecisionTimeShadowError("canonical_history_missing")
    return path


def _session_root(root: Path, session_date: date) -> Path:
    path = (root / _SHADOW_ROOT_RELPATH / session_date.isoformat()).resolve()
    _require_under_root(path, root)
    return path


def _provisional_path(root: Path, session_date: date) -> Path:
    return _session_root(root, session_date) / _PROVISIONAL_FILENAME


def _reconciliation_path(root: Path, session_date: date) -> Path:
    return _session_root(root, session_date) / _RECONCILIATION_FILENAME


def _require_under_root(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError:
        raise SpyDecisionTimeShadowError("noncanonical_target") from None


def _write_json_once(path: Path, payload: Mapping[str, object]) -> None:
    if path.exists():
        raise SpyDecisionTimeShadowError("receipt_already_exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise SpyDecisionTimeShadowError("receipt_temporary_path_occupied")
    encoded = (
        json.dumps(dict(payload), sort_keys=True, indent=2, separators=(",", ": "))
        + "\n"
    )
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_provisional_receipt(
    path: Path,
    *,
    expected_session: date,
) -> dict[str, Any] | None:
    payload = _read_json_mapping(path)
    if payload is None:
        return None
    required = {
        "record_type": _CAPTURE_RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "session_id": expected_session.isoformat(),
        "network_access_attempted": True,
        "credential_access_attempted": True,
        "broker_access_attempted": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "submitted": False,
        "mutated": False,
        "live_trading_performed": False,
        "live_authorized": False,
        "execution_intent_created": False,
        "execution_plan_created": False,
        "profit_claim": "none",
    }
    if any(payload.get(key) != value for key, value in required.items()):
        return None
    if payload.get("decision") not in {"target_long", "target_cash", "no_decision"}:
        return None
    if payload.get("posture") not in {
        "bullish_risk_on",
        "defensive_risk_off",
        "insufficient_history",
    }:
        return None
    return payload


def _read_reconciliation_receipt(
    path: Path,
    *,
    expected_session: date,
) -> dict[str, Any] | None:
    payload = _read_json_mapping(path)
    if payload is None:
        return None
    required = {
        "record_type": _RECONCILIATION_RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "session_id": expected_session.isoformat(),
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "broker_access_attempted": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "submitted": False,
        "mutated": False,
        "live_trading_performed": False,
        "live_authorized": False,
        "profit_claim": "none",
    }
    if any(payload.get(key) != value for key, value in required.items()):
        return None
    if payload.get("classification") not in {"matched", "diverged"}:
        return None
    return payload


def _read_json_mapping(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return dict(payload) if isinstance(payload, Mapping) else None


def _base_result(*, mode: str, apply: bool) -> dict[str, Any]:
    return {
        "milestone": _MILESTONE,
        "mode": mode,
        "apply": apply,
        "state": "not_started",
        "session_id": None,
        "decision": None,
        "posture": None,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "broker_access_attempted": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "submitted": False,
        "mutated": False,
        "live_trading_performed": False,
        "live_authorized": False,
        "execution_intent_created": False,
        "execution_plan_created": False,
        "profit_claim": "none",
        "refusal_category": None,
        "exit_code": 2,
    }


def _capture_refusal(result: dict[str, Any], classification: str) -> dict[str, Any]:
    result.update(
        {
            "state": "capture_refused",
            "refusal_category": classification,
            "exit_code": 2,
        }
    )
    return result


def _reconciliation_refusal(
    result: dict[str, Any],
    classification: str,
) -> dict[str, Any]:
    result.update(
        {
            "state": "reconciliation_refused",
            "refusal_category": classification,
            "exit_code": 2,
        }
    )
    return result


def _decision_for_posture(posture: str) -> str:
    return {
        "bullish_risk_on": "target_long",
        "defensive_risk_off": "target_cash",
        "insufficient_history": "no_decision",
    }[posture]


def _execution_window(value: object) -> str:
    if type(value) is not str or value not in SPY_DECISION_TIME_EXECUTION_WINDOWS:
        raise SpyDecisionTimeShadowError("execution_window_invalid")
    return value


def _parse_as_of(value: object) -> datetime:
    if type(value) is not str or not value.strip():
        raise SpyDecisionTimeShadowError("as_of_invalid")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        raise SpyDecisionTimeShadowError("as_of_invalid") from None
    if parsed.tzinfo is None:
        raise SpyDecisionTimeShadowError("as_of_invalid")
    return parsed.astimezone(UTC)


def _date_text(value: object, field_name: str) -> date:
    if type(value) is not str:
        raise SpyDecisionTimeShadowError(f"{field_name}_invalid")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise SpyDecisionTimeShadowError(f"{field_name}_invalid") from None
    if parsed.isoformat() != value:
        raise SpyDecisionTimeShadowError(f"{field_name}_invalid")
    return parsed


def _timestamp(value: object, field_name: str) -> datetime:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a timestamp.")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise ValidationError(f"{field_name} must be a timestamp.") from None
    return _utc_datetime(parsed, field_name)


def _utc_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValidationError(f"{field_name} must be timezone-aware.")
    return value.astimezone(UTC)


def _decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValidationError(f"{field_name} must be a positive decimal.")
    try:
        parsed = Decimal(str(value).strip())
    except InvalidOperation:
        raise ValidationError(f"{field_name} must be a positive decimal.") from None
    return _positive_decimal(parsed, field_name)


def _positive_decimal(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal or not value.is_finite() or value <= 0:
        raise ValidationError(f"{field_name} must be a positive Decimal.")
    return value


def _non_negative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float) and value.is_integer():
        parsed = int(value)
    elif isinstance(value, str):
        try:
            parsed = int(value.strip())
        except ValueError:
            raise ValidationError(
                f"{field_name} must be a non-negative integer."
            ) from None
    else:
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    if parsed < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    return parsed


def _secret_text(value: object) -> str:
    if type(value) is not str or not value.strip() or len(value) > 4096:
        raise SpyDecisionTimeShadowError("credential_record_malformed")
    return value


def _http_status_classification(status: int) -> str:
    if status in {401, 403}:
        return "market_data_authentication_failed"
    if status == 429:
        return "market_data_rate_limited"
    if 500 <= status <= 599:
        return "market_data_server_error"
    return "market_data_http_failure"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_text(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise SpyDecisionTimeShadowError("parser_invalid_argument")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _SanitizedArgumentParser(
        description="Capture or reconcile the paper-only SPY decision-time shadow.",
        allow_abbrev=False,
    )
    parser.add_argument("--mode", choices=("capture", "reconcile"), required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--apply", action="store_true", default=False)
    parser.add_argument(
        "--execution-window",
        choices=SPY_DECISION_TIME_EXECUTION_WINDOWS,
        default="next_session_open",
    )
    parser.add_argument(
        "--credential-reference",
        default=DEFAULT_MARKET_DATA_CREDENTIAL_REFERENCE,
    )
    parser.add_argument("--session-id")
    try:
        args, unknown = parser.parse_known_args(argv)
        if unknown:
            raise SpyDecisionTimeShadowError("parser_invalid_argument")
        if args.mode == "capture":
            if args.session_id is not None:
                raise SpyDecisionTimeShadowError("parser_invalid_argument")
            result = capture_spy_decision_time_shadow(
                as_of=args.as_of,
                apply=args.apply,
                execution_window=args.execution_window,
                credential_reference=args.credential_reference,
            )
        else:
            if args.apply or not args.session_id:
                raise SpyDecisionTimeShadowError("parser_invalid_argument")
            result = reconcile_spy_decision_time_shadow(
                session_id=args.session_id,
                as_of=args.as_of,
            )
    except SpyDecisionTimeShadowError as exc:
        result = _base_result(mode="unknown", apply=False)
        result.update(
            {
                "state": "refused",
                "refusal_category": exc.classification,
                "exit_code": 2,
            }
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return int(result["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
