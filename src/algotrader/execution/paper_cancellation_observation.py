"""Exact operator-gated read-only observation for cancellation recovery.

This module owns authorization and gate validation around one injected exact
order read. It does not import a broker SDK, load credentials, select a target,
poll, retry, mutate a broker, or update the local order journal.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
import hashlib
import json

from algotrader.core.time import require_utc_datetime
from algotrader.core.validation import decimal_value
from algotrader.errors import ValidationError
from algotrader.execution.cancellation_reconciliation import (
    CancellationReconciliationIdentity,
    CancellationReconciliationObservation,
)


PAPER_CANCELLATION_OBSERVATION_VERSION = "paper_cancellation_observation_v1"
PAPER_CANCELLATION_OBSERVATION_AUTHORIZATION_VERSION = (
    "paper_cancellation_observation_authorization_v1"
)
PAPER_CANCELLATION_OBSERVATION_MODE = "paper"
PAPER_CANCELLATION_OBSERVATION_OPERATION = "read_exact_cancellation_order"
MAXIMUM_OBSERVATION_AUTHORIZATION_TTL_SECONDS = 300


class PaperCancellationObservationStatus(StrEnum):
    OBSERVED = "observed"
    BLOCKED = "blocked"


class PaperCancellationObservationBlocker(StrEnum):
    AUTHORIZATION_MISSING = "authorization_missing"
    AUTHORIZATION_NOT_GRANTED = "authorization_not_granted"
    AUTHORIZATION_ID_MISMATCH = "authorization_id_mismatch"
    AUTHORIZATION_MODE_MISMATCH = "authorization_mode_mismatch"
    AUTHORIZATION_OPERATION_MISMATCH = "authorization_operation_mismatch"
    AUTHORIZATION_NOT_YET_VALID = "authorization_not_yet_valid"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    CANCEL_INTENT_ID_MISMATCH = "cancel_intent_id_mismatch"
    CLIENT_ORDER_ID_MISMATCH = "client_order_id_mismatch"
    BROKER_ORDER_ID_MISMATCH = "broker_order_id_mismatch"
    OBSERVATION_NOT_PERMITTED = "observation_not_permitted"
    NETWORK_ACCESS_NOT_PERMITTED = "network_access_not_permitted"
    PAPER_PROFILE_REQUIRED = "paper_profile_required"
    API_KEY_REQUIRED = "paper_api_key_required"
    SECRET_KEY_REQUIRED = "paper_secret_key_required"
    EXACT_PAPER_ENDPOINT_REQUIRED = "exact_paper_endpoint_required"
    LIVE_ENDPOINT_DETECTED = "live_endpoint_detected"
    EXPECTED_ACCOUNT_REQUIRED = "expected_paper_account_required"
    READ_FAILED = "exact_order_read_failed"
    OBSERVATION_CONTRACT_INVALID = "observation_contract_invalid"
    ACCOUNT_IDENTITY_MISMATCH = "expected_paper_account_mismatch"
    OBSERVATION_BEFORE_REQUEST = "observation_before_request"
    AUTHORIZATION_EXPIRED_DURING_OBSERVATION = (
        "authorization_expired_during_observation"
    )


@dataclass(frozen=True, slots=True)
class PaperCancellationObservationAuthorization:
    authorization_id: str
    mode: str
    operation: str
    cancel_intent_id: str
    client_order_id: str
    broker_order_id: str
    issued_at: datetime
    expires_at: datetime
    authorized: bool

    def __post_init__(self) -> None:
        mode = _required(self.mode, "mode").lower()
        operation = _required(self.operation, "operation").lower()
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "operation", operation)
        for field_name in (
            "cancel_intent_id",
            "client_order_id",
            "broker_order_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _required(getattr(self, field_name), field_name),
            )
        issued_at = _utc_datetime(self.issued_at, "issued_at")
        expires_at = _utc_datetime(self.expires_at, "expires_at")
        _validate_authorization_window(issued_at, expires_at)
        object.__setattr__(self, "issued_at", issued_at)
        object.__setattr__(self, "expires_at", expires_at)
        if type(self.authorized) is not bool:
            raise ValidationError("authorized must be a boolean.")
        expected_id = _authorization_id(
            mode=mode,
            operation=operation,
            cancel_intent_id=self.cancel_intent_id,
            client_order_id=self.client_order_id,
            broker_order_id=self.broker_order_id,
            issued_at=issued_at,
            expires_at=expires_at,
            authorized=self.authorized,
        )
        if str(self.authorization_id).strip() != expected_id:
            raise ValidationError(
                "authorization_id does not match observation authorization evidence."
            )
        object.__setattr__(self, "authorization_id", expected_id)

    def to_dict(self) -> dict[str, object]:
        return {
            "authorization_version": (
                PAPER_CANCELLATION_OBSERVATION_AUTHORIZATION_VERSION
            ),
            "authorization_id": self.authorization_id,
            "mode": self.mode,
            "operation": self.operation,
            "cancel_intent_id": self.cancel_intent_id,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "authorized": self.authorized,
        }


def build_paper_cancellation_observation_authorization(
    *,
    mode: str,
    operation: str,
    cancel_intent_id: str,
    client_order_id: str,
    broker_order_id: str,
    issued_at: datetime,
    expires_at: datetime,
    authorized: bool,
) -> PaperCancellationObservationAuthorization:
    """Build immutable exact-read authorization without contacting a broker."""

    normalized_mode = _required(mode, "mode").lower()
    normalized_operation = _required(operation, "operation").lower()
    normalized_cancel_intent_id = _required(
        cancel_intent_id,
        "cancel_intent_id",
    )
    normalized_client_order_id = _required(client_order_id, "client_order_id")
    normalized_broker_order_id = _required(broker_order_id, "broker_order_id")
    normalized_issued_at = _utc_datetime(issued_at, "issued_at")
    normalized_expires_at = _utc_datetime(expires_at, "expires_at")
    _validate_authorization_window(normalized_issued_at, normalized_expires_at)
    if type(authorized) is not bool:
        raise ValidationError("authorized must be a boolean.")
    return PaperCancellationObservationAuthorization(
        authorization_id=_authorization_id(
            mode=normalized_mode,
            operation=normalized_operation,
            cancel_intent_id=normalized_cancel_intent_id,
            client_order_id=normalized_client_order_id,
            broker_order_id=normalized_broker_order_id,
            issued_at=normalized_issued_at,
            expires_at=normalized_expires_at,
            authorized=authorized,
        ),
        mode=normalized_mode,
        operation=normalized_operation,
        cancel_intent_id=normalized_cancel_intent_id,
        client_order_id=normalized_client_order_id,
        broker_order_id=normalized_broker_order_id,
        issued_at=normalized_issued_at,
        expires_at=normalized_expires_at,
        authorized=authorized,
    )


@dataclass(frozen=True, slots=True)
class PaperCancellationObservationRequest:
    expected_authorization_id: str
    occurred_at: datetime
    expected_account_id: str = field(default="", repr=False)
    observation_permitted: bool = False
    network_access_permitted: bool = False
    paper_profile_ready: bool = False
    api_key_present: bool = False
    secret_key_present: bool = False
    paper_endpoint_validated: bool = False
    live_endpoint_detected: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "expected_authorization_id",
            _required(self.expected_authorization_id, "expected_authorization_id"),
        )
        object.__setattr__(
            self,
            "occurred_at",
            _utc_datetime(self.occurred_at, "occurred_at"),
        )
        object.__setattr__(
            self,
            "expected_account_id",
            str(self.expected_account_id).strip(),
        )
        for field_name in (
            "observation_permitted",
            "network_access_permitted",
            "paper_profile_ready",
            "api_key_present",
            "secret_key_present",
            "paper_endpoint_validated",
            "live_endpoint_detected",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")

    def to_dict(self) -> dict[str, object]:
        return {
            "expected_authorization_id": self.expected_authorization_id,
            "occurred_at": self.occurred_at.isoformat(),
            "expected_account_configured": bool(self.expected_account_id),
            "observation_permitted": self.observation_permitted,
            "network_access_permitted": self.network_access_permitted,
            "paper_profile_ready": self.paper_profile_ready,
            "api_key_present": self.api_key_present,
            "secret_key_present": self.secret_key_present,
            "paper_endpoint_validated": self.paper_endpoint_validated,
            "live_endpoint_detected": self.live_endpoint_detected,
        }


@dataclass(frozen=True, slots=True)
class PaperCancellationBrokerOrderObservation:
    account_id: str = field(repr=False)
    cancel_intent_id: str
    client_order_id: str
    broker_order_id: str
    broker_status: str
    observed_at: datetime
    filled_quantity: Decimal | str | None = None
    filled_average_price: Decimal | str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "account_id",
            "cancel_intent_id",
            "client_order_id",
            "broker_order_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _required(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "broker_status",
            _normalized_status(self.broker_status),
        )
        object.__setattr__(
            self,
            "observed_at",
            _utc_datetime(self.observed_at, "observed_at"),
        )
        object.__setattr__(
            self,
            "filled_quantity",
            _optional_non_negative_decimal(
                self.filled_quantity,
                "filled_quantity",
            ),
        )
        object.__setattr__(
            self,
            "filled_average_price",
            _optional_positive_decimal(
                self.filled_average_price,
                "filled_average_price",
            ),
        )


@dataclass(frozen=True, slots=True)
class PaperCancellationObservationResult:
    identity: CancellationReconciliationIdentity
    request: PaperCancellationObservationRequest
    authorization_id: str
    status: PaperCancellationObservationStatus
    blocker: PaperCancellationObservationBlocker | None
    read_callback_invoked: bool
    read_count: int
    account_identity_matched: bool
    observation: CancellationReconciliationObservation | None
    error_type: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.identity, CancellationReconciliationIdentity):
            raise ValidationError(
                "identity must be a CancellationReconciliationIdentity."
            )
        if not isinstance(self.request, PaperCancellationObservationRequest):
            raise ValidationError(
                "request must be a PaperCancellationObservationRequest."
            )
        if not isinstance(self.status, PaperCancellationObservationStatus):
            raise ValidationError(
                "status must be a PaperCancellationObservationStatus."
            )
        object.__setattr__(
            self,
            "authorization_id",
            str(self.authorization_id).strip(),
        )
        object.__setattr__(self, "error_type", str(self.error_type).strip())
        for field_name in (
            "read_callback_invoked",
            "account_identity_matched",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")
        if type(self.read_count) is not int or self.read_count not in {0, 1}:
            raise ValidationError("read_count must be zero or one.")
        if self.read_callback_invoked != (self.read_count == 1):
            raise ValidationError(
                "read_callback_invoked must agree with read_count."
            )
        if self.status is PaperCancellationObservationStatus.OBSERVED:
            if (
                self.blocker is not None
                or not self.read_callback_invoked
                or not self.account_identity_matched
                or not isinstance(
                    self.observation,
                    CancellationReconciliationObservation,
                )
                or not self.authorization_id
            ):
                raise ValidationError(
                    "observed result requires exact authorized observation evidence."
                )
            if self.authorization_id != self.request.expected_authorization_id:
                raise ValidationError(
                    "observed result authorization identity is inconsistent."
                )
            if (
                self.observation.cancel_intent_id != self.identity.cancel_intent_id
                or self.observation.client_order_id != self.identity.client_order_id
                or self.observation.broker_order_id != self.identity.broker_order_id
            ):
                raise ValidationError(
                    "observed result order identity is inconsistent."
                )
        elif (
            not isinstance(self.blocker, PaperCancellationObservationBlocker)
            or self.observation is not None
            or self.account_identity_matched
        ):
            raise ValidationError(
                "blocked result requires one blocker and no observation."
            )

    @property
    def observed(self) -> bool:
        return self.status is PaperCancellationObservationStatus.OBSERVED

    def to_dict(self) -> dict[str, object]:
        return {
            "observation_version": PAPER_CANCELLATION_OBSERVATION_VERSION,
            "status": self.status.value,
            "blocker": "" if self.blocker is None else self.blocker.value,
            "identity": {
                "cancel_intent_id": self.identity.cancel_intent_id,
                "client_order_id": self.identity.client_order_id,
                "broker_order_id": self.identity.broker_order_id,
            },
            "authorization_id": self.authorization_id,
            "request": self.request.to_dict(),
            "read_callback_invoked": self.read_callback_invoked,
            "read_count": self.read_count,
            "account_identity_matched": self.account_identity_matched,
            "observation_produced": self.observation is not None,
            "observation": (
                {} if self.observation is None else self.observation.to_dict()
            ),
            "error_type": self.error_type,
            "retry_permitted": False,
            "target_selection_performed": False,
            "polling_performed": False,
            "local_journal_updated": False,
            "reconciliation_invoked": False,
            "credential_values_accessed_by_boundary": False,
            "network_client_constructed_by_boundary": False,
            "broker_sdk_imported_by_boundary": False,
            "broker_mutation_authorized": False,
            "broker_mutation_performed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "replace_attempted": False,
            "close_attempted": False,
            "liquidation_attempted": False,
            "live_authorized": False,
        }


ExactOrderReader = Callable[[str], PaperCancellationBrokerOrderObservation]


def observe_exact_paper_cancellation(
    identity: CancellationReconciliationIdentity,
    authorization: PaperCancellationObservationAuthorization | None,
    request: PaperCancellationObservationRequest,
    *,
    read_exact_order: ExactOrderReader,
) -> PaperCancellationObservationResult:
    """Invoke one exact read after every operator and paper gate passes."""

    if not isinstance(identity, CancellationReconciliationIdentity):
        raise ValidationError(
            "identity must be a CancellationReconciliationIdentity."
        )
    if authorization is not None and not isinstance(
        authorization,
        PaperCancellationObservationAuthorization,
    ):
        raise ValidationError(
            "authorization must be a PaperCancellationObservationAuthorization or None."
        )
    if not isinstance(request, PaperCancellationObservationRequest):
        raise ValidationError(
            "request must be a PaperCancellationObservationRequest."
        )
    if not callable(read_exact_order):
        raise ValidationError("read_exact_order must be callable.")

    blocker = _pre_read_blocker(identity, authorization, request)
    if blocker is not None:
        return _blocked(identity, request, authorization, blocker)

    try:
        broker_observation = read_exact_order(identity.broker_order_id)
    except Exception as exc:
        return _blocked(
            identity,
            request,
            authorization,
            PaperCancellationObservationBlocker.READ_FAILED,
            read_callback_invoked=True,
            error_type=exc.__class__.__name__,
        )
    if not isinstance(
        broker_observation,
        PaperCancellationBrokerOrderObservation,
    ):
        return _blocked(
            identity,
            request,
            authorization,
            PaperCancellationObservationBlocker.OBSERVATION_CONTRACT_INVALID,
            read_callback_invoked=True,
            error_type="ValidationError",
        )
    post_read_blocker = _post_read_blocker(
        identity,
        authorization,
        request,
        broker_observation,
    )
    if post_read_blocker is not None:
        return _blocked(
            identity,
            request,
            authorization,
            post_read_blocker,
            read_callback_invoked=True,
        )

    try:
        observation = CancellationReconciliationObservation(
            cancel_intent_id=broker_observation.cancel_intent_id,
            client_order_id=broker_observation.client_order_id,
            broker_order_id=broker_observation.broker_order_id,
            broker_status=broker_observation.broker_status,
            observed_at=broker_observation.observed_at,
            filled_quantity=broker_observation.filled_quantity,
            filled_average_price=broker_observation.filled_average_price,
        )
    except ValidationError:
        return _blocked(
            identity,
            request,
            authorization,
            PaperCancellationObservationBlocker.OBSERVATION_CONTRACT_INVALID,
            read_callback_invoked=True,
            error_type="ValidationError",
        )
    return PaperCancellationObservationResult(
        identity=identity,
        request=request,
        authorization_id=authorization.authorization_id,
        status=PaperCancellationObservationStatus.OBSERVED,
        blocker=None,
        read_callback_invoked=True,
        read_count=1,
        account_identity_matched=True,
        observation=observation,
    )


def _pre_read_blocker(
    identity: CancellationReconciliationIdentity,
    authorization: PaperCancellationObservationAuthorization | None,
    request: PaperCancellationObservationRequest,
) -> PaperCancellationObservationBlocker | None:
    if authorization is None:
        return PaperCancellationObservationBlocker.AUTHORIZATION_MISSING
    if not authorization.authorized:
        return PaperCancellationObservationBlocker.AUTHORIZATION_NOT_GRANTED
    if request.expected_authorization_id != authorization.authorization_id:
        return PaperCancellationObservationBlocker.AUTHORIZATION_ID_MISMATCH
    if authorization.mode != PAPER_CANCELLATION_OBSERVATION_MODE:
        return PaperCancellationObservationBlocker.AUTHORIZATION_MODE_MISMATCH
    if authorization.operation != PAPER_CANCELLATION_OBSERVATION_OPERATION:
        return PaperCancellationObservationBlocker.AUTHORIZATION_OPERATION_MISMATCH
    if request.occurred_at < authorization.issued_at:
        return PaperCancellationObservationBlocker.AUTHORIZATION_NOT_YET_VALID
    if request.occurred_at >= authorization.expires_at:
        return PaperCancellationObservationBlocker.AUTHORIZATION_EXPIRED
    if identity.cancel_intent_id != authorization.cancel_intent_id:
        return PaperCancellationObservationBlocker.CANCEL_INTENT_ID_MISMATCH
    if identity.client_order_id != authorization.client_order_id:
        return PaperCancellationObservationBlocker.CLIENT_ORDER_ID_MISMATCH
    if identity.broker_order_id != authorization.broker_order_id:
        return PaperCancellationObservationBlocker.BROKER_ORDER_ID_MISMATCH
    if not request.observation_permitted:
        return PaperCancellationObservationBlocker.OBSERVATION_NOT_PERMITTED
    if not request.network_access_permitted:
        return PaperCancellationObservationBlocker.NETWORK_ACCESS_NOT_PERMITTED
    if not request.paper_profile_ready:
        return PaperCancellationObservationBlocker.PAPER_PROFILE_REQUIRED
    if not request.api_key_present:
        return PaperCancellationObservationBlocker.API_KEY_REQUIRED
    if not request.secret_key_present:
        return PaperCancellationObservationBlocker.SECRET_KEY_REQUIRED
    if not request.paper_endpoint_validated:
        return PaperCancellationObservationBlocker.EXACT_PAPER_ENDPOINT_REQUIRED
    if request.live_endpoint_detected:
        return PaperCancellationObservationBlocker.LIVE_ENDPOINT_DETECTED
    if not request.expected_account_id:
        return PaperCancellationObservationBlocker.EXPECTED_ACCOUNT_REQUIRED
    return None


def _post_read_blocker(
    identity: CancellationReconciliationIdentity,
    authorization: PaperCancellationObservationAuthorization,
    request: PaperCancellationObservationRequest,
    observation: PaperCancellationBrokerOrderObservation,
) -> PaperCancellationObservationBlocker | None:
    if observation.account_id != request.expected_account_id:
        return PaperCancellationObservationBlocker.ACCOUNT_IDENTITY_MISMATCH
    if observation.cancel_intent_id != identity.cancel_intent_id:
        return PaperCancellationObservationBlocker.CANCEL_INTENT_ID_MISMATCH
    if observation.client_order_id != identity.client_order_id:
        return PaperCancellationObservationBlocker.CLIENT_ORDER_ID_MISMATCH
    if observation.broker_order_id != identity.broker_order_id:
        return PaperCancellationObservationBlocker.BROKER_ORDER_ID_MISMATCH
    if observation.observed_at < request.occurred_at:
        return PaperCancellationObservationBlocker.OBSERVATION_BEFORE_REQUEST
    if observation.observed_at >= authorization.expires_at:
        return (
            PaperCancellationObservationBlocker.AUTHORIZATION_EXPIRED_DURING_OBSERVATION
        )
    return None


def _blocked(
    identity: CancellationReconciliationIdentity,
    request: PaperCancellationObservationRequest,
    authorization: PaperCancellationObservationAuthorization | None,
    blocker: PaperCancellationObservationBlocker,
    *,
    read_callback_invoked: bool = False,
    error_type: str = "",
) -> PaperCancellationObservationResult:
    return PaperCancellationObservationResult(
        identity=identity,
        request=request,
        authorization_id=(
            "" if authorization is None else authorization.authorization_id
        ),
        status=PaperCancellationObservationStatus.BLOCKED,
        blocker=blocker,
        read_callback_invoked=read_callback_invoked,
        read_count=1 if read_callback_invoked else 0,
        account_identity_matched=False,
        observation=None,
        error_type=error_type,
    )


def _authorization_id(
    *,
    mode: str,
    operation: str,
    cancel_intent_id: str,
    client_order_id: str,
    broker_order_id: str,
    issued_at: datetime,
    expires_at: datetime,
    authorized: bool,
) -> str:
    payload = {
        "authorization_version": (
            PAPER_CANCELLATION_OBSERVATION_AUTHORIZATION_VERSION
        ),
        "mode": mode,
        "operation": operation,
        "cancel_intent_id": cancel_intent_id,
        "client_order_id": client_order_id,
        "broker_order_id": broker_order_id,
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "authorized": authorized,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"paper_cancel_observation_auth_{digest}"


def _validate_authorization_window(
    issued_at: datetime,
    expires_at: datetime,
) -> None:
    if expires_at <= issued_at:
        raise ValidationError("expires_at must be later than issued_at.")
    if (
        expires_at - issued_at
    ).total_seconds() > MAXIMUM_OBSERVATION_AUTHORIZATION_TTL_SECONDS:
        raise ValidationError(
            "observation authorization lifetime exceeds the maximum."
        )


def _required(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _normalized_status(value: object) -> str:
    text = _required(value, "broker_status").lower()
    if "." in text:
        text = text.rsplit(".", maxsplit=1)[-1]
    return text.replace("-", "_").replace(" ", "_")


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    try:
        return require_utc_datetime(value)
    except (TypeError, ValidationError) as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc


def _optional_non_negative_decimal(
    value: Decimal | str | None,
    field_name: str,
) -> Decimal | None:
    if value is None or value == "":
        return None
    parsed = decimal_value(value, field_name)
    if parsed < 0:
        raise ValidationError(f"{field_name} must be non-negative.")
    return parsed


def _optional_positive_decimal(
    value: Decimal | str | None,
    field_name: str,
) -> Decimal | None:
    if value is None or value == "":
        return None
    parsed = decimal_value(value, field_name)
    if parsed <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return parsed


__all__ = [
    "MAXIMUM_OBSERVATION_AUTHORIZATION_TTL_SECONDS",
    "PAPER_CANCELLATION_OBSERVATION_AUTHORIZATION_VERSION",
    "PAPER_CANCELLATION_OBSERVATION_MODE",
    "PAPER_CANCELLATION_OBSERVATION_OPERATION",
    "PAPER_CANCELLATION_OBSERVATION_VERSION",
    "PaperCancellationBrokerOrderObservation",
    "PaperCancellationObservationAuthorization",
    "PaperCancellationObservationBlocker",
    "PaperCancellationObservationRequest",
    "PaperCancellationObservationResult",
    "PaperCancellationObservationStatus",
    "build_paper_cancellation_observation_authorization",
    "observe_exact_paper_cancellation",
]
