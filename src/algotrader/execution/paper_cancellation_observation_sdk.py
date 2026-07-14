"""One-shot paper-SDK reader for exact cancellation observations.

Construction is credential-gated and paper-endpoint-gated. The returned
callable performs one account read and one exact broker-order read, exposes no
raw SDK client, and cannot be reused or retried.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol

from algotrader.config import (
    DEFAULT_ALPACA_PAPER_BASE_URL,
    AlpacaPaperConfig,
    require_paper_profile,
)
from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.execution.alpaca_translator import (
    translate_alpaca_account,
    translate_alpaca_order_observation,
)
from algotrader.execution.cancellation_reconciliation import (
    CancellationReconciliationIdentity,
)
from algotrader.execution.paper_cancellation_observation import (
    PaperCancellationBrokerOrderObservation,
)


PAPER_CANCELLATION_OBSERVATION_SDK_VERSION = (
    "paper_cancellation_observation_sdk_v1"
)


class PaperCancellationObservationReadClient(Protocol):
    """The complete broker capability visible to this binding."""

    def get_account(self) -> Any:
        ...

    def get_order_by_id(self, broker_order_id: str) -> Any:
        ...


PaperCancellationObservationClientFactory = Callable[
    [AlpacaPaperConfig],
    PaperCancellationObservationReadClient,
]
ObservationClock = Callable[[], datetime]


class PaperCancellationSdkReadError(RuntimeError):
    """Sanitized failure from the one-shot paper read binding."""

    def __init__(self, stage: str, cause: Exception | None = None) -> None:
        self.error_stage = str(stage).strip()
        self.cause_type = "" if cause is None else cause.__class__.__name__
        suffix = "" if not self.cause_type else f" cause_type={self.cause_type}"
        super().__init__(f"Paper cancellation SDK read failed: stage={self.error_stage}{suffix}.")


class PaperCancellationSdkExactOrderReader:
    """Consume one exact paper account/order observation and then close."""

    __slots__ = (
        "__client",
        "__identity",
        "__clock",
        "__consumed",
        "__invocation_count",
        "__account_read_count",
        "__order_read_count",
    )

    def __init__(
        self,
        client: PaperCancellationObservationReadClient,
        identity: CancellationReconciliationIdentity,
        clock: ObservationClock,
    ) -> None:
        if not isinstance(identity, CancellationReconciliationIdentity):
            raise ValidationError(
                "identity must be a CancellationReconciliationIdentity."
            )
        if not callable(clock):
            raise ValidationError("clock must be callable.")
        self.__client = client
        self.__identity = identity
        self.__clock = clock
        self.__consumed = False
        self.__invocation_count = 0
        self.__account_read_count = 0
        self.__order_read_count = 0

    @property
    def consumed(self) -> bool:
        return self.__consumed

    @property
    def invocation_count(self) -> int:
        return self.__invocation_count

    @property
    def account_read_count(self) -> int:
        return self.__account_read_count

    @property
    def order_read_count(self) -> int:
        return self.__order_read_count

    def __call__(
        self,
        broker_order_id: str,
    ) -> PaperCancellationBrokerOrderObservation:
        requested_order_id = str(broker_order_id).strip()
        if requested_order_id != self.__identity.broker_order_id:
            raise PaperCancellationSdkReadError("broker_order_identity_mismatch")
        if self.__consumed:
            raise PaperCancellationSdkReadError("reader_already_consumed")

        self.__consumed = True
        self.__invocation_count += 1
        try:
            self.__account_read_count += 1
            account = translate_alpaca_account(self.__client.get_account())
        except Exception as exc:
            raise PaperCancellationSdkReadError("account_read_failed", exc) from None

        try:
            self.__order_read_count += 1
            order = translate_alpaca_order_observation(
                self.__client.get_order_by_id(requested_order_id)
            )
        except Exception as exc:
            raise PaperCancellationSdkReadError("exact_order_read_failed", exc) from None

        try:
            observed_at = require_utc_datetime(self.__clock())
            return PaperCancellationBrokerOrderObservation(
                account_id=account.account_id,
                cancel_intent_id=self.__identity.cancel_intent_id,
                client_order_id=order.client_order_id,
                broker_order_id=order.order_id,
                broker_status=order.normalized_status,
                observed_at=observed_at,
                filled_quantity=order.filled_quantity,
                filled_average_price=order.filled_average_price,
            )
        except Exception as exc:
            raise PaperCancellationSdkReadError(
                "observation_translation_failed",
                exc,
            ) from None

    def __repr__(self) -> str:
        return (
            "PaperCancellationSdkExactOrderReader("
            f"consumed={self.__consumed}, "
            f"invocation_count={self.__invocation_count}, "
            f"account_read_count={self.__account_read_count}, "
            f"order_read_count={self.__order_read_count})"
        )


def build_paper_cancellation_sdk_reader(
    config: AlpacaPaperConfig,
    identity: CancellationReconciliationIdentity,
    *,
    client_factory: PaperCancellationObservationClientFactory | None = None,
    clock: ObservationClock | None = None,
) -> PaperCancellationSdkExactOrderReader:
    """Build a consumed-on-use exact reader behind canonical paper gates."""

    if not isinstance(config, AlpacaPaperConfig):
        raise ValidationError("config must be an AlpacaPaperConfig.")
    if not isinstance(identity, CancellationReconciliationIdentity):
        raise ValidationError(
            "identity must be a CancellationReconciliationIdentity."
        )
    require_paper_profile(config)
    if config.alpaca_paper_base_url != DEFAULT_ALPACA_PAPER_BASE_URL:
        raise ValidationError("the exact canonical paper endpoint is required.")

    resolved_factory = client_factory or AlpacaSdkClient
    if not callable(resolved_factory):
        raise ValidationError("client_factory must be callable.")
    resolved_clock = clock or _utc_now
    if not callable(resolved_clock):
        raise ValidationError("clock must be callable.")

    try:
        client = resolved_factory(config)
    except Exception as exc:
        raise PaperCancellationSdkReadError("client_construction_failed", exc) from None

    return PaperCancellationSdkExactOrderReader(
        client=client,
        identity=identity,
        clock=resolved_clock,
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "PAPER_CANCELLATION_OBSERVATION_SDK_VERSION",
    "PaperCancellationObservationReadClient",
    "PaperCancellationSdkExactOrderReader",
    "PaperCancellationSdkReadError",
    "build_paper_cancellation_sdk_reader",
]
