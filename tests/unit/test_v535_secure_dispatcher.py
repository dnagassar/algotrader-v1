from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.crypto_history_refresh_adapter import (
    CryptoHistoryRefreshConfig,
    run_crypto_history_refresh,
)
from algotrader.execution.secure_credential_provider import (
    CREDENTIAL_RECORD_SCHEMA,
    CredentialFamily,
    CredentialProviderError,
    CredentialReference,
    lease_from_test_record,
)
from algotrader.orchestration.crypto_tournament_v2_oos_scheduler import (
    SCHEDULER_SCHEMA_VERSION,
    RealCommandDispatcher,
    SchedulerJob,
    SchedulerJobStatus,
)


KEY_SENTINEL = "V535_DISPATCH_KEY_SENTINEL"
SECRET_SENTINEL = "V535_DISPATCH_SECRET_SENTINEL"
REFERENCE = CredentialReference(
    "wincred:algotrader/v5.35/alpaca-market-data/offline-dispatch"
)


class RecordProvider:
    provider_name = "windows-credential-manager"

    def __init__(
        self,
        *,
        failure: str | None = None,
        family: CredentialFamily = CredentialFamily.ALPACA_MARKET_DATA,
    ) -> None:
        self.failure = failure
        self.family = family
        self.validate_count = 0
        self.open_count = 0

    def _lease(self, expected_family: CredentialFamily):
        if self.failure:
            raise CredentialProviderError(self.failure)
        record = {
            "schema_version": CREDENTIAL_RECORD_SCHEMA,
            "family": self.family.value,
            "api_key_id": KEY_SENTINEL,
            "api_secret_key": SECRET_SENTINEL,
        }
        return lease_from_test_record(
            record,
            reference=REFERENCE,
            expected_family=expected_family,
        )

    def validate(
        self,
        reference: CredentialReference,
        *,
        expected_family: CredentialFamily,
    ) -> None:
        assert reference is REFERENCE
        self.validate_count += 1
        self._lease(expected_family).use(lambda *_: None)

    def open(
        self,
        reference: CredentialReference,
        *,
        expected_family: CredentialFamily,
    ):
        assert reference is REFERENCE
        self.open_count += 1
        return self._lease(expected_family)


def _job() -> SchedulerJob:
    start = datetime(2026, 7, 18, 20, tzinfo=UTC)
    return SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id="v535-secure-dispatch-job",
        lane="crypto_tournament_v2_forward_oos",
        source_commit="a" * 40,
        created_at=start,
        requested_start_bar_open=start,
        requested_end_bar_open=start,
        provider_as_of_boundary=start + timedelta(hours=1),
        symbols=("BTCUSD", "ETHUSD", "SOLUSD"),
        accepted_frontier_bar_open=start - timedelta(hours=1),
        expected_frontier_bar_open=start + timedelta(hours=1),
        status=SchedulerJobStatus.RUNNING,
        attempt_number=1,
        claim_identity="v535-claim",
    )


@pytest.mark.parametrize(
    "classification",
    (
        "credential_provider_unavailable",
        "credential_record_malformed",
        "credential_family_mismatch",
        "credential_provider_denied",
    ),
)
def test_provider_failure_creates_no_process_or_files(
    tmp_path: Path,
    classification: str,
) -> None:
    calls: list[object] = []
    dispatcher = RealCommandDispatcher(
        scheduler_enabled=True,
        market_data_read_authorized=True,
        credential_reference=REFERENCE,
        credential_provider=RecordProvider(failure=classification),
        process_runner=lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    with pytest.raises(ValidationError, match=classification):
        dispatcher.dispatch(
            _job(),
            tmp_path / "output",
            tmp_path / "source.csv",
            tmp_path / "source.json",
            allow_network=True,
        )
    assert calls == []
    assert list(tmp_path.rglob("*")) == []


def test_real_dispatcher_passes_only_non_secret_child_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_root = tmp_path / "output"
    captured: dict[str, Any] = {}

    def run_process(argv: list[str], **kwargs: object) -> object:
        captured["argv"] = list(argv)
        captured["env"] = dict(kwargs["env"])  # type: ignore[arg-type]
        output_root.mkdir(parents=True)
        (output_root / "operating_packet.json").write_text(
            json.dumps({"as_of": "2026-07-18T21:00:00+00:00"}),
            encoding="utf-8",
        )
        (output_root / "frozen_state.json").write_text(
            json.dumps({"updated_at": "2026-07-18T21:00:00+00:00"}),
            encoding="utf-8",
        )
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"status": "completed"}),
            stderr=f"should_not_persist:{SECRET_SENTINEL}",
        )

    monkeypatch.setattr(os, "environ", {"SYSTEMROOT": "C:\\Windows"})
    provider = RecordProvider()
    dispatcher = RealCommandDispatcher(
        scheduler_enabled=True,
        market_data_read_authorized=True,
        credential_reference=REFERENCE,
        credential_provider=provider,
        process_runner=run_process,
    )
    result = dispatcher.dispatch(
        _job(),
        output_root,
        tmp_path / "source.csv",
        tmp_path / "source.json",
        allow_network=True,
    )

    assert result["status"] == "success"
    assert result["dispatch_type"] == "real"
    assert provider.validate_count == 1
    serialized = json.dumps(
        {"argv": captured["argv"], "env": captured["env"], "result": result},
        sort_keys=True,
    )
    assert str(REFERENCE) in serialized
    assert "windows-credential-manager" in serialized
    assert KEY_SENTINEL not in serialized
    assert SECRET_SENTINEL not in serialized
    assert not any(name.startswith(("ALPACA_", "APCA_")) for name in captured["env"])
    assert SECRET_SENTINEL not in "".join(
        path.read_text(encoding="utf-8")
        for path in tmp_path.rglob("*")
        if path.is_file()
    )


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_child_side_provider_resolves_only_at_read_only_http_boundary(
    tmp_path: Path,
) -> None:
    provider = RecordProvider()
    observed_headers: list[dict[str, str]] = []

    def opener(request: object, *, timeout: int) -> _Response:
        assert timeout == 30
        headers = dict(getattr(request, "headers"))
        observed_headers.append(headers)
        assert headers["APCA-API-KEY-ID"] == KEY_SENTINEL
        assert headers["APCA-API-SECRET-KEY"] == SECRET_SENTINEL
        return _Response(
            {
                "bars": [
                    {
                        "t": "2026-07-18T20:00:00Z",
                        "o": "100",
                        "h": "102",
                        "l": "99",
                        "c": "101",
                        "v": "1",
                    }
                ],
                "next_page_token": None,
            }
        )

    config = CryptoHistoryRefreshConfig(
        mode="market_data_fetch",
        symbols=("BTCUSD",),
        output_path=tmp_path / "delta.csv",
        packet_path=tmp_path / "packet.json",
        raw_response_path=tmp_path / "raw.json",
        as_of="2026-07-18T21:00:00Z",
        start="2026-07-18T20:00:00Z",
        end="2026-07-18T20:00:00Z",
        market_data_fetch_authorized=True,
        allow_network=True,
        data_intake_only=True,
    )
    result = run_crypto_history_refresh(
        config,
        env={},
        opener=opener,
        credential_provider=provider,
        credential_reference=REFERENCE,
        app_profile="paper",
        paper_endpoint="https://paper-api.alpaca.markets",
        market_data_endpoint="https://data.alpaca.markets",
    )

    assert provider.open_count == 1
    assert len(observed_headers) == 1
    assert result["classification"] == "market_data_refresh_ready"
    persisted = "".join(
        path.read_text(encoding="utf-8")
        for path in tmp_path.rglob("*")
        if path.is_file()
    )
    assert KEY_SENTINEL not in persisted
    assert SECRET_SENTINEL not in persisted
    assert KEY_SENTINEL not in json.dumps(result, sort_keys=True)
    assert SECRET_SENTINEL not in json.dumps(result, sort_keys=True)


def test_secure_child_rejects_environment_alias_before_provider_or_http(
    tmp_path: Path,
) -> None:
    provider = RecordProvider()
    opener_calls: list[object] = []
    result = run_crypto_history_refresh(
        CryptoHistoryRefreshConfig(
            mode="market_data_fetch",
            symbols=("BTCUSD",),
            output_path=tmp_path / "delta.csv",
            packet_path=None,
            raw_response_path=None,
            market_data_fetch_authorized=True,
            allow_network=True,
            data_intake_only=True,
        ),
        env={"ALPACA_API_KEY": KEY_SENTINEL},
        opener=lambda *args, **kwargs: opener_calls.append((args, kwargs)),
        credential_provider=provider,
        credential_reference=REFERENCE,
        app_profile="paper",
        paper_endpoint="https://paper-api.alpaca.markets",
        market_data_endpoint="https://data.alpaca.markets",
    )

    assert result["classification"] == "market_data_refresh_not_configured"
    assert "credential_environment_alias_rejected" in result["authorization_status"]
    assert provider.open_count == 0
    assert opener_calls == []
    assert list(tmp_path.rglob("*")) == []
