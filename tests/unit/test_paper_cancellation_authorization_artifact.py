from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pytest

from algotrader.execution.paper_cancellation_authorization_artifact import (
    PAPER_CANCELLATION_AUTHORIZATION_ARTIFACT_MAX_BYTES,
    PaperCancellationAuthorizationArtifactError,
    load_paper_cancellation_observation_authorization,
)
from algotrader.execution.paper_cancellation_observation import (
    PAPER_CANCELLATION_OBSERVATION_MODE,
    PAPER_CANCELLATION_OBSERVATION_OPERATION,
    build_paper_cancellation_observation_authorization,
)


NOW = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)


def _authorization():
    return build_paper_cancellation_observation_authorization(
        mode=PAPER_CANCELLATION_OBSERVATION_MODE,
        operation=PAPER_CANCELLATION_OBSERVATION_OPERATION,
        cancel_intent_id="cancel-intent-1",
        client_order_id="client-order-1",
        broker_order_id="broker-order-1",
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        authorized=True,
    )


def _write_payload(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def test_loader_reconstructs_exact_existing_authorization(tmp_path: Path) -> None:
    path = tmp_path / "authorization.json"
    expected = _authorization()
    _write_payload(path, expected.to_dict())

    loaded = load_paper_cancellation_observation_authorization(path)

    assert loaded == expected
    assert loaded.to_dict() == expected.to_dict()


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("authorization_version", "future-version"),
        ("authorization_id", "forged-authorization-id"),
        ("mode", "PAPER"),
        ("operation", "READ_EXACT_CANCELLATION_ORDER"),
        ("issued_at", "2026-07-14T14:00:00Z"),
        ("expires_at", "2026-07-14T14:05:00Z"),
        ("authorized", 1),
    ],
)
def test_loader_rejects_noncanonical_or_forged_evidence(
    tmp_path: Path,
    field_name: str,
    replacement: object,
) -> None:
    payload = _authorization().to_dict()
    payload[field_name] = replacement
    path = tmp_path / "authorization.json"
    _write_payload(path, payload)

    with pytest.raises(PaperCancellationAuthorizationArtifactError):
        load_paper_cancellation_observation_authorization(path)


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {**_authorization().to_dict(), "unexpected": True},
        {
            key: value
            for key, value in _authorization().to_dict().items()
            if key != "broker_order_id"
        },
    ],
)
def test_loader_requires_one_exact_schema_object(
    tmp_path: Path,
    payload: object,
) -> None:
    path = tmp_path / "authorization.json"
    _write_payload(path, payload)

    with pytest.raises(PaperCancellationAuthorizationArtifactError):
        load_paper_cancellation_observation_authorization(path)


@pytest.mark.parametrize(
    "raw",
    [
        b"not-json",
        b"\xff\xfe",
        (
            b'{"authorization_version":"x",'
            b'"authorization_version":"x"}'
        ),
        b"",
    ],
)
def test_loader_rejects_malformed_duplicate_non_utf8_or_empty_artifacts(
    tmp_path: Path,
    raw: bytes,
) -> None:
    path = tmp_path / "authorization.json"
    path.write_bytes(raw)

    with pytest.raises(PaperCancellationAuthorizationArtifactError):
        load_paper_cancellation_observation_authorization(path)


def test_loader_rejects_missing_or_oversized_artifacts(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(PaperCancellationAuthorizationArtifactError):
        load_paper_cancellation_observation_authorization(missing)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(
        b"{" + b" " * PAPER_CANCELLATION_AUTHORIZATION_ARTIFACT_MAX_BYTES + b"}"
    )
    with pytest.raises(PaperCancellationAuthorizationArtifactError):
        load_paper_cancellation_observation_authorization(oversized)
