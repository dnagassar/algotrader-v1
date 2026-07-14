"""Standalone exact read-only cancellation reconciliation command.

This operator-only command consumes one existing canonical authorization
artifact and explicit target identity. Both the operator-binding and network
permissions default to false. When every gate is explicit, it constructs the
canonical paper configuration and invokes the repository-owned one-shot
operator binding exactly once. It never selects a target, polls, retries, mints
authorization, or exposes a broker mutation.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
import json
from pathlib import Path

from algotrader.config import AlpacaPaperConfig
from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError
from algotrader.execution.paper_cancellation_authorization_artifact import (
    load_paper_cancellation_observation_authorization,
)
from algotrader.execution.paper_cancellation_observation import (
    PaperCancellationObservationAuthorization,
)
from algotrader.execution.paper_cancellation_observation_sdk import (
    ObservationClock,
    PaperCancellationObservationClientFactory,
)
from algotrader.execution.paper_cancellation_reconciliation_operator import (
    PaperCancellationReconciliationOperatorRequest,
    PaperCancellationReconciliationOperatorResult,
    PaperCancellationReconciliationOperatorStatus,
    run_exact_paper_cancellation_reconciliation_operator,
)


PAPER_CANCELLATION_RECONCILIATION_COMMAND_VERSION = (
    "paper_cancellation_reconciliation_command_v1"
)

AuthorizationLoader = Callable[
    [Path | str],
    PaperCancellationObservationAuthorization,
]


class PaperCancellationReconciliationCommandStatus(StrEnum):
    BLOCKED_BEFORE_OPERATOR = "blocked_before_operator"
    OPERATOR_BLOCKED = "operator_blocked"
    CONVERGED = "converged"


@dataclass(frozen=True, slots=True)
class PaperCancellationReconciliationCommandRequest:
    authorization_artifact_path: Path | str
    journal_path: Path | str
    cancel_intent_id: str
    client_order_id: str
    broker_order_id: str
    expected_authorization_id: str
    occurred_at: datetime
    expected_account_id: str = field(default="", repr=False)
    operator_binding_permitted: bool = False
    network_access_permitted: bool = False

    def __post_init__(self) -> None:
        for field_name in ("authorization_artifact_path", "journal_path"):
            text = _required(getattr(self, field_name), field_name)
            object.__setattr__(self, field_name, Path(text))
        for field_name in (
            "cancel_intent_id",
            "client_order_id",
            "broker_order_id",
            "expected_authorization_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _required(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "occurred_at",
            _utc_datetime(self.occurred_at, "occurred_at"),
        )
        object.__setattr__(
            self,
            "expected_account_id",
            _required(self.expected_account_id, "expected_account_id"),
        )
        for field_name in (
            "operator_binding_permitted",
            "network_access_permitted",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")

    def to_dict(self) -> dict[str, object]:
        return {
            "authorization_artifact_path_configured": True,
            "journal_path": str(self.journal_path),
            "cancel_intent_id": self.cancel_intent_id,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "expected_authorization_id": self.expected_authorization_id,
            "occurred_at": self.occurred_at.isoformat(),
            "expected_account_configured": True,
            "operator_binding_permitted": self.operator_binding_permitted,
            "network_access_permitted": self.network_access_permitted,
        }


@dataclass(frozen=True, slots=True)
class PaperCancellationReconciliationCommandResult:
    request: PaperCancellationReconciliationCommandRequest
    status: PaperCancellationReconciliationCommandStatus
    blocker: str
    authorization_artifact_loaded: bool
    paper_configuration_loaded: bool
    process_environment_read: bool
    operator_invoked: bool
    operator_result: PaperCancellationReconciliationOperatorResult | None = None
    error_type: str = ""

    def __post_init__(self) -> None:
        if not isinstance(
            self.request,
            PaperCancellationReconciliationCommandRequest,
        ):
            raise ValidationError(
                "request must be a PaperCancellationReconciliationCommandRequest."
            )
        if not isinstance(
            self.status,
            PaperCancellationReconciliationCommandStatus,
        ):
            raise ValidationError(
                "status must be a PaperCancellationReconciliationCommandStatus."
            )
        for field_name in (
            "authorization_artifact_loaded",
            "paper_configuration_loaded",
            "process_environment_read",
            "operator_invoked",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")
        object.__setattr__(self, "blocker", str(self.blocker).strip())
        object.__setattr__(self, "error_type", str(self.error_type).strip())
        if self.operator_result is not None and not isinstance(
            self.operator_result,
            PaperCancellationReconciliationOperatorResult,
        ):
            raise ValidationError(
                "operator_result must be a "
                "PaperCancellationReconciliationOperatorResult or None."
            )

        if self.status is PaperCancellationReconciliationCommandStatus.CONVERGED:
            if (
                self.blocker
                or not self.authorization_artifact_loaded
                or not self.paper_configuration_loaded
                or not self.operator_invoked
                or self.operator_result is None
                or self.operator_result.status
                is not PaperCancellationReconciliationOperatorStatus.CONVERGED
            ):
                raise ValidationError(
                    "converged command result requires one successful operator result."
                )
        elif self.status is PaperCancellationReconciliationCommandStatus.OPERATOR_BLOCKED:
            if not self.blocker or not self.operator_invoked:
                raise ValidationError(
                    "operator-blocked command result requires one blocker and invocation."
                )
        elif (
            not self.blocker
            or self.operator_invoked
            or self.operator_result is not None
        ):
            raise ValidationError(
                "pre-operator block requires one blocker and no operator result."
            )

    def to_dict(self) -> dict[str, object]:
        operator_payload = (
            {} if self.operator_result is None else self.operator_result.to_dict()
        )
        broker_read_callback_invoked = bool(
            operator_payload.get("exact_order_reader_invoked", False)
        )
        return {
            "command_version": PAPER_CANCELLATION_RECONCILIATION_COMMAND_VERSION,
            "status": self.status.value,
            "blocker": self.blocker,
            "request": self.request.to_dict(),
            "authorization_artifact_loaded": self.authorization_artifact_loaded,
            "authorization_minted": False,
            "paper_configuration_loaded": self.paper_configuration_loaded,
            "process_environment_read": self.process_environment_read,
            "credential_values_serialized": False,
            "operator_invoked": self.operator_invoked,
            "operator_result": operator_payload,
            "broker_read_callback_invoked": broker_read_callback_invoked,
            "retry_permitted": False,
            "safe_to_recancel": False,
            "target_selection_performed": False,
            "unresolved_intents_enumerated": False,
            "polling_performed": False,
            "runtime_control_changed": False,
            "broker_mutation_authorized": False,
            "broker_mutation_performed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "replace_attempted": False,
            "close_attempted": False,
            "liquidation_attempted": False,
            "live_authorized": False,
            "error_type": self.error_type,
        }


def run_exact_paper_cancellation_reconciliation_command(
    request: PaperCancellationReconciliationCommandRequest,
    *,
    env: Mapping[str, str] | None = None,
    client_factory: PaperCancellationObservationClientFactory | None = None,
    reader_clock: ObservationClock | None = None,
    authorization_loader: AuthorizationLoader = (
        load_paper_cancellation_observation_authorization
    ),
) -> PaperCancellationReconciliationCommandResult:
    """Consume one exact artifact and invoke one exact operator binding."""

    if not isinstance(request, PaperCancellationReconciliationCommandRequest):
        raise ValidationError(
            "request must be a PaperCancellationReconciliationCommandRequest."
        )
    if not callable(authorization_loader):
        raise ValidationError("authorization_loader must be callable.")

    if not request.operator_binding_permitted:
        return _blocked_before_operator(request, "operator_binding_not_permitted")
    if not request.network_access_permitted:
        return _blocked_before_operator(request, "network_access_not_permitted")

    try:
        authorization = authorization_loader(request.authorization_artifact_path)
        if not isinstance(
            authorization,
            PaperCancellationObservationAuthorization,
        ):
            raise ValidationError(
                "authorization loader returned an invalid authorization."
            )
    except Exception as exc:
        return _blocked_before_operator(
            request,
            "authorization_artifact_invalid",
            error_type=exc.__class__.__name__,
        )

    process_environment_read = env is None
    try:
        config = AlpacaPaperConfig.from_env(env)
    except Exception as exc:
        return _blocked_before_operator(
            request,
            "paper_configuration_invalid",
            authorization_artifact_loaded=True,
            process_environment_read=process_environment_read,
            error_type=exc.__class__.__name__,
        )

    operator_request = PaperCancellationReconciliationOperatorRequest(
        journal_path=request.journal_path,
        cancel_intent_id=request.cancel_intent_id,
        client_order_id=request.client_order_id,
        broker_order_id=request.broker_order_id,
        expected_authorization_id=request.expected_authorization_id,
        occurred_at=request.occurred_at,
        expected_account_id=request.expected_account_id,
        operator_binding_permitted=request.operator_binding_permitted,
        network_access_permitted=request.network_access_permitted,
    )
    try:
        operator_result = run_exact_paper_cancellation_reconciliation_operator(
            config,
            authorization,
            operator_request,
            client_factory=client_factory,
            reader_clock=reader_clock,
        )
    except Exception as exc:
        return PaperCancellationReconciliationCommandResult(
            request=request,
            status=PaperCancellationReconciliationCommandStatus.OPERATOR_BLOCKED,
            blocker="operator_binding_failed",
            authorization_artifact_loaded=True,
            paper_configuration_loaded=True,
            process_environment_read=process_environment_read,
            operator_invoked=True,
            error_type=exc.__class__.__name__,
        )

    status = (
        PaperCancellationReconciliationCommandStatus.CONVERGED
        if operator_result.status
        is PaperCancellationReconciliationOperatorStatus.CONVERGED
        else PaperCancellationReconciliationCommandStatus.OPERATOR_BLOCKED
    )
    return PaperCancellationReconciliationCommandResult(
        request=request,
        status=status,
        blocker=operator_result.blocker,
        authorization_artifact_loaded=True,
        paper_configuration_loaded=True,
        process_environment_read=process_environment_read,
        operator_invoked=True,
        operator_result=operator_result,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m algotrader.execution.paper_cancellation_reconciliation_command",
        description=(
            "Reconcile one exactly identified unresolved paper cancellation from "
            "one existing authorization artifact and one read-only observation."
        ),
    )
    parser.add_argument("--authorization-artifact", required=True)
    parser.add_argument("--journal-path", required=True)
    parser.add_argument("--cancel-intent-id", required=True)
    parser.add_argument("--client-order-id", required=True)
    parser.add_argument("--broker-order-id", required=True)
    parser.add_argument("--expected-authorization-id", required=True)
    parser.add_argument("--expected-paper-account-id", required=True)
    parser.add_argument("--occurred-at", required=True, type=_utc_argument)
    parser.add_argument("--operator-binding-permitted", action="store_true")
    parser.add_argument("--network-access-permitted", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        request = PaperCancellationReconciliationCommandRequest(
            authorization_artifact_path=args.authorization_artifact,
            journal_path=args.journal_path,
            cancel_intent_id=args.cancel_intent_id,
            client_order_id=args.client_order_id,
            broker_order_id=args.broker_order_id,
            expected_authorization_id=args.expected_authorization_id,
            occurred_at=args.occurred_at,
            expected_account_id=args.expected_paper_account_id,
            operator_binding_permitted=args.operator_binding_permitted,
            network_access_permitted=args.network_access_permitted,
        )
    except (TypeError, ValueError, ValidationError) as exc:
        print(json.dumps(_invalid_request_payload(exc), sort_keys=True, indent=2))
        return 2

    result = run_exact_paper_cancellation_reconciliation_command(request)
    print(json.dumps(result.to_dict(), sort_keys=True, indent=2))
    return (
        0
        if result.status is PaperCancellationReconciliationCommandStatus.CONVERGED
        else 2
    )


def _blocked_before_operator(
    request: PaperCancellationReconciliationCommandRequest,
    blocker: str,
    *,
    authorization_artifact_loaded: bool = False,
    process_environment_read: bool = False,
    error_type: str = "",
) -> PaperCancellationReconciliationCommandResult:
    return PaperCancellationReconciliationCommandResult(
        request=request,
        status=(
            PaperCancellationReconciliationCommandStatus.BLOCKED_BEFORE_OPERATOR
        ),
        blocker=_required(blocker, "blocker"),
        authorization_artifact_loaded=authorization_artifact_loaded,
        paper_configuration_loaded=False,
        process_environment_read=process_environment_read,
        operator_invoked=False,
        error_type=error_type,
    )


def _invalid_request_payload(exc: Exception) -> dict[str, object]:
    return {
        "command_version": PAPER_CANCELLATION_RECONCILIATION_COMMAND_VERSION,
        "status": "invalid_request",
        "blocker": "command_request_invalid",
        "authorization_artifact_loaded": False,
        "authorization_minted": False,
        "paper_configuration_loaded": False,
        "process_environment_read": False,
        "credential_values_serialized": False,
        "operator_invoked": False,
        "broker_read_callback_invoked": False,
        "retry_permitted": False,
        "broker_mutation_authorized": False,
        "broker_mutation_performed": False,
        "live_authorized": False,
        "error_type": exc.__class__.__name__,
    }


def _utc_argument(value: str) -> datetime:
    try:
        return _utc_datetime(datetime.fromisoformat(value), "occurred_at")
    except (TypeError, ValueError, ValidationError) as exc:
        raise argparse.ArgumentTypeError(
            "occurred-at must be a timezone-aware canonical UTC timestamp."
        ) from exc


def _required(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    try:
        return require_utc_datetime(value)
    except (TypeError, ValidationError) as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PAPER_CANCELLATION_RECONCILIATION_COMMAND_VERSION",
    "PaperCancellationReconciliationCommandRequest",
    "PaperCancellationReconciliationCommandResult",
    "PaperCancellationReconciliationCommandStatus",
    "build_parser",
    "main",
    "run_exact_paper_cancellation_reconciliation_command",
]
