"""Strict loader for an existing exact cancellation-read authorization.

The loader reconstructs and validates an immutable authorization exported by
``PaperCancellationObservationAuthorization.to_dict``. It cannot mint, renew,
select, or broaden authorization and performs no environment, network, broker,
or journal access.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
import json
from pathlib import Path

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError
from algotrader.execution.paper_cancellation_observation import (
    PAPER_CANCELLATION_OBSERVATION_AUTHORIZATION_VERSION,
    PaperCancellationObservationAuthorization,
)


PAPER_CANCELLATION_AUTHORIZATION_ARTIFACT_MAX_BYTES = 16_384

_AUTHORIZATION_ARTIFACT_FIELDS = frozenset(
    {
        "authorization_version",
        "authorization_id",
        "mode",
        "operation",
        "cancel_intent_id",
        "client_order_id",
        "broker_order_id",
        "issued_at",
        "expires_at",
        "authorized",
    }
)


class PaperCancellationAuthorizationArtifactError(ValidationError):
    """An authorization artifact failed strict reconstruction."""


def load_paper_cancellation_observation_authorization(
    path: Path | str,
) -> PaperCancellationObservationAuthorization:
    """Load one canonical pre-existing authorization artifact or fail closed."""

    artifact_path = _artifact_path(path)
    try:
        with artifact_path.open("rb") as stream:
            raw = stream.read(
                PAPER_CANCELLATION_AUTHORIZATION_ARTIFACT_MAX_BYTES + 1
            )
    except OSError as exc:
        raise PaperCancellationAuthorizationArtifactError(
            "authorization artifact is unavailable."
        ) from exc
    if not raw or len(raw) > PAPER_CANCELLATION_AUTHORIZATION_ARTIFACT_MAX_BYTES:
        raise PaperCancellationAuthorizationArtifactError(
            "authorization artifact size is invalid."
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PaperCancellationAuthorizationArtifactError(
            "authorization artifact must be UTF-8 JSON."
        ) from exc
    try:
        payload = json.loads(text, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, PaperCancellationAuthorizationArtifactError) as exc:
        raise PaperCancellationAuthorizationArtifactError(
            "authorization artifact JSON is invalid."
        ) from exc
    if not isinstance(payload, dict):
        raise PaperCancellationAuthorizationArtifactError(
            "authorization artifact must contain one JSON object."
        )
    if frozenset(payload) != _AUTHORIZATION_ARTIFACT_FIELDS:
        raise PaperCancellationAuthorizationArtifactError(
            "authorization artifact fields do not match the canonical schema."
        )
    if (
        type(payload["authorization_version"]) is not str
        or payload["authorization_version"]
        != PAPER_CANCELLATION_OBSERVATION_AUTHORIZATION_VERSION
    ):
        raise PaperCancellationAuthorizationArtifactError(
            "authorization artifact version is invalid."
        )

    try:
        authorization = PaperCancellationObservationAuthorization(
            authorization_id=payload["authorization_id"],
            mode=payload["mode"],
            operation=payload["operation"],
            cancel_intent_id=payload["cancel_intent_id"],
            client_order_id=payload["client_order_id"],
            broker_order_id=payload["broker_order_id"],
            issued_at=_artifact_datetime(payload["issued_at"], "issued_at"),
            expires_at=_artifact_datetime(payload["expires_at"], "expires_at"),
            authorized=payload["authorized"],
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise PaperCancellationAuthorizationArtifactError(
            "authorization artifact evidence is invalid."
        ) from exc

    if payload != authorization.to_dict():
        raise PaperCancellationAuthorizationArtifactError(
            "authorization artifact is not a canonical authorization export."
        )
    return authorization


def _artifact_path(value: Path | str) -> Path:
    text = str(value).strip()
    if not text:
        raise PaperCancellationAuthorizationArtifactError(
            "authorization artifact path is required."
        )
    return Path(text)


def _artifact_datetime(value: object, field_name: str) -> datetime:
    if type(value) is not str:
        raise PaperCancellationAuthorizationArtifactError(
            f"authorization {field_name} must be a canonical UTC timestamp."
        )
    try:
        parsed = datetime.fromisoformat(value)
        return require_utc_datetime(parsed)
    except (TypeError, ValueError, ValidationError) as exc:
        raise PaperCancellationAuthorizationArtifactError(
            f"authorization {field_name} must be a canonical UTC timestamp."
        ) from exc


def _unique_object(pairs: Iterable[tuple[str, object]]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise PaperCancellationAuthorizationArtifactError(
                "authorization artifact contains duplicate fields."
            )
        payload[key] = value
    return payload


__all__ = [
    "PAPER_CANCELLATION_AUTHORIZATION_ARTIFACT_MAX_BYTES",
    "PaperCancellationAuthorizationArtifactError",
    "load_paper_cancellation_observation_authorization",
]
