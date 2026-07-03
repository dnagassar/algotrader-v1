"""Asset-class freshness policy receipts for paper-lab supervisors."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from algotrader.errors import ValidationError

AssetClassFreshnessStatus = Literal[
    "current_for_daily_bar_lab",
    "stale_data_preview_only",
    "blocked_future_dated_local_data",
    "current_for_24_7_crypto_lab",
    "stale_crypto_data_preview_only",
    "blocked_future_dated_crypto_data",
    "missing_data_timestamp",
]

ASSET_CLASS_EQUITY = "equity"
ASSET_CLASS_CRYPTO = "crypto"
DEFAULT_CRYPTO_MAX_BAR_AGE = timedelta(hours=2)

__all__ = [
    "ASSET_CLASS_CRYPTO",
    "ASSET_CLASS_EQUITY",
    "DEFAULT_CRYPTO_MAX_BAR_AGE",
    "AssetClassFreshnessReceipt",
    "AssetClassFreshnessStatus",
    "evaluate_asset_class_freshness",
]


@dataclass(frozen=True, slots=True)
class AssetClassFreshnessReceipt:
    """Primitive-only data freshness decision for one asset-class lane."""

    asset_class: str
    freshness_policy: str
    data_freshness_status: AssetClassFreshnessStatus
    latest_bar_at: datetime | None
    observed_at: datetime
    expected_latest_bar_date: date | None
    max_age_seconds: int | None
    age_seconds: int | None
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_class", _asset_class(self.asset_class))
        object.__setattr__(
            self,
            "freshness_policy",
            _required_string(self.freshness_policy, "freshness_policy"),
        )
        object.__setattr__(
            self,
            "data_freshness_status",
            _status(self.data_freshness_status),
        )
        if self.latest_bar_at is not None:
            object.__setattr__(
                self,
                "latest_bar_at",
                _utc_datetime(self.latest_bar_at, "latest_bar_at"),
            )
        object.__setattr__(
            self,
            "observed_at",
            _utc_datetime(self.observed_at, "observed_at"),
        )
        if self.expected_latest_bar_date is not None and not isinstance(
            self.expected_latest_bar_date,
            date,
        ):
            raise ValidationError("expected_latest_bar_date must be a date or None.")
        if self.max_age_seconds is not None and self.max_age_seconds < 0:
            raise ValidationError("max_age_seconds must be non-negative or None.")
        if self.age_seconds is not None and self.age_seconds < 0:
            raise ValidationError("age_seconds must be non-negative or None.")
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-safe freshness metadata."""

        return {
            "asset_class": self.asset_class,
            "freshness_policy": self.freshness_policy,
            "data_freshness_status": self.data_freshness_status,
            "latest_bar_at": (
                None if self.latest_bar_at is None else self.latest_bar_at.isoformat()
            ),
            "observed_at": self.observed_at.isoformat(),
            "expected_latest_bar_date": (
                None
                if self.expected_latest_bar_date is None
                else self.expected_latest_bar_date.isoformat()
            ),
            "max_age_seconds": self.max_age_seconds,
            "age_seconds": self.age_seconds,
            "blockers": list(self.blockers),
        }


def evaluate_asset_class_freshness(
    *,
    asset_class: str,
    latest_bar_at: datetime | date | str | None,
    observed_at: datetime | str,
    expected_latest_bar_date: date | str | None = None,
    crypto_max_age: timedelta = DEFAULT_CRYPTO_MAX_BAR_AGE,
) -> AssetClassFreshnessReceipt:
    """Evaluate exchange-session equity freshness or 24/7 crypto freshness."""

    normalized_asset_class = _asset_class(asset_class)
    observed = _utc_datetime(observed_at, "observed_at")
    latest = None if latest_bar_at is None else _utc_datetime(latest_bar_at, "latest_bar_at")
    if normalized_asset_class == ASSET_CLASS_EQUITY:
        return _equity_freshness(
            latest_bar_at=latest,
            observed_at=observed,
            expected_latest_bar_date=_optional_date(
                expected_latest_bar_date,
                "expected_latest_bar_date",
            ),
        )
    if normalized_asset_class == ASSET_CLASS_CRYPTO:
        return _crypto_freshness(
            latest_bar_at=latest,
            observed_at=observed,
            crypto_max_age=_nonnegative_timedelta(crypto_max_age, "crypto_max_age"),
        )
    raise ValidationError("asset_class must be equity or crypto.")


def _equity_freshness(
    *,
    latest_bar_at: datetime | None,
    observed_at: datetime,
    expected_latest_bar_date: date | None,
) -> AssetClassFreshnessReceipt:
    blockers: list[str] = []
    if latest_bar_at is None:
        blockers.append("missing_latest_bar_at")
        status: AssetClassFreshnessStatus = "missing_data_timestamp"
    elif expected_latest_bar_date is None:
        blockers.append("expected_latest_bar_date_missing")
        status = "stale_data_preview_only"
    elif latest_bar_at.date() > expected_latest_bar_date:
        blockers.append("latest_bar_date_after_expected")
        status = "blocked_future_dated_local_data"
    elif latest_bar_at.date() < expected_latest_bar_date:
        blockers.append("latest_bar_date_before_expected")
        status = "stale_data_preview_only"
    else:
        status = "current_for_daily_bar_lab"
    return AssetClassFreshnessReceipt(
        asset_class=ASSET_CLASS_EQUITY,
        freshness_policy="exchange_session_expected_latest_bar_date",
        data_freshness_status=status,
        latest_bar_at=latest_bar_at,
        observed_at=observed_at,
        expected_latest_bar_date=expected_latest_bar_date,
        max_age_seconds=None,
        age_seconds=None,
        blockers=tuple(blockers),
    )


def _crypto_freshness(
    *,
    latest_bar_at: datetime | None,
    observed_at: datetime,
    crypto_max_age: timedelta,
) -> AssetClassFreshnessReceipt:
    blockers: list[str] = []
    max_age_seconds = int(crypto_max_age.total_seconds())
    age_seconds: int | None = None
    if latest_bar_at is None:
        blockers.append("missing_latest_bar_at")
        status: AssetClassFreshnessStatus = "missing_data_timestamp"
    elif latest_bar_at > observed_at:
        blockers.append("latest_crypto_bar_future_dated")
        status = "blocked_future_dated_crypto_data"
    else:
        age_seconds = int((observed_at - latest_bar_at).total_seconds())
        if age_seconds > max_age_seconds:
            blockers.append("crypto_bar_age_exceeds_threshold")
            status = "stale_crypto_data_preview_only"
        else:
            status = "current_for_24_7_crypto_lab"
    return AssetClassFreshnessReceipt(
        asset_class=ASSET_CLASS_CRYPTO,
        freshness_policy="crypto_24_7_max_bar_age",
        data_freshness_status=status,
        latest_bar_at=latest_bar_at,
        observed_at=observed_at,
        expected_latest_bar_date=None,
        max_age_seconds=max_age_seconds,
        age_seconds=age_seconds,
        blockers=tuple(blockers),
    )


def _asset_class(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError("asset_class must be a non-empty string.")
    return value.strip().lower()


def _status(value: object) -> AssetClassFreshnessStatus:
    allowed = {
        "current_for_daily_bar_lab",
        "stale_data_preview_only",
        "blocked_future_dated_local_data",
        "current_for_24_7_crypto_lab",
        "stale_crypto_data_preview_only",
        "blocked_future_dated_crypto_data",
        "missing_data_timestamp",
    }
    if type(value) is not str or value not in allowed:
        raise ValidationError("data_freshness_status is invalid.")
    return value  # type: ignore[return-value]


def _optional_date(value: date | str | None, field_name: str) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a date or YYYY-MM-DD string.")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be a date or YYYY-MM-DD string."
        ) from exc


def _utc_datetime(value: datetime | date | str, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min, tzinfo=UTC)
    elif type(value) is str and value.strip():
        text = value.strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be an ISO timestamp.") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
    else:
        raise ValidationError(f"{field_name} must be an ISO timestamp.")
    return parsed.astimezone(UTC)


def _nonnegative_timedelta(value: object, field_name: str) -> timedelta:
    if not isinstance(value, timedelta) or value.total_seconds() < 0:
        raise ValidationError(f"{field_name} must be a non-negative timedelta.")
    return value


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")
    return tuple(_required_string(value, f"{field_name}[]") for value in values)
