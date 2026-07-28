from __future__ import annotations

import ast
import csv
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

import pytest

from algotrader.execution.exchange_session import NyseExchangeSessionCalendar
from algotrader.execution.secure_credential_provider import (
    CREDENTIAL_RECORD_SCHEMA,
    CredentialFamily,
    CredentialReference,
    lease_from_test_record,
)
from algotrader.execution.spy_decision_time_shadow import (
    ALPACA_SPY_SNAPSHOT_HOST,
    ALPACA_SPY_SNAPSHOT_PATH,
    SpyDecisionSnapshot,
    SpyDecisionTimeShadowError,
    alpaca_bounded_spy_snapshot_get,
    capture_spy_decision_time_shadow,
    normalize_alpaca_spy_snapshot,
    reconcile_spy_decision_time_shadow,
)

TARGET = date(2026, 7, 28)
OBSERVED_AT = datetime(2026, 7, 28, 14, 0, tzinfo=UTC)
REFERENCE = CredentialReference(
    "wincred:algotrader/v5.35/alpaca-market-data/offline-test"
)


class FakeProvider:
    provider_name = "test-provider"

    def __init__(self) -> None:
        self.open_count = 0

    def open(
        self,
        reference: CredentialReference | str,
        *,
        expected_family: CredentialFamily | str,
    ):  # type: ignore[no-untyped-def]
        self.open_count += 1
        checked_reference = (
            reference
            if isinstance(reference, CredentialReference)
            else CredentialReference(reference)
        )
        family = (
            expected_family
            if isinstance(expected_family, CredentialFamily)
            else CredentialFamily(expected_family)
        )
        return lease_from_test_record(
            {
                "schema_version": CREDENTIAL_RECORD_SCHEMA,
                "family": CredentialFamily.ALPACA_MARKET_DATA.value,
                "api_key_id": "test-key",
                "api_secret_key": "test-secret",
            },
            reference=checked_reference,
            expected_family=family,
        )

    def validate(
        self,
        reference: CredentialReference | str,
        *,
        expected_family: CredentialFamily | str,
    ) -> None:
        lease = self.open(reference, expected_family=expected_family)
        lease.use(lambda _key, _secret, _account: None)


class FakeResponse:
    def __init__(self, payload: bytes, *, status: int = 200) -> None:
        self.status = status
        self.payload = payload
        self.read_limit: int | None = None

    def read(self, limit: int) -> bytes:
        self.read_limit = limit
        return self.payload


class FakeConnection:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.request_args: tuple[Any, ...] | None = None
        self.request_kwargs: dict[str, Any] | None = None
        self.closed = False

    def request(self, *args: Any, **kwargs: Any) -> None:
        self.request_args = args
        self.request_kwargs = kwargs

    def getresponse(self) -> FakeResponse:
        return self.response

    def close(self) -> None:
        self.closed = True


def _root(tmp_path: Path, *, history_price: str = "100") -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    (tmp_path / "src" / "algotrader").mkdir(parents=True)
    canonical = (
        tmp_path
        / "runs"
        / "operator_input"
        / "m446_spy_daily_tiingo_adjusted_canonical.csv"
    )
    canonical.parent.mkdir(parents=True)
    _write_history(
        canonical,
        _previous_sessions(TARGET, count=200),
        price=history_price,
    )
    return tmp_path


def _previous_sessions(target: date, *, count: int) -> list[date]:
    calendar = NyseExchangeSessionCalendar()
    cursor = target - timedelta(days=1)
    sessions: list[date] = []
    while len(sessions) < count:
        if calendar.session_for_date(cursor) is not None:
            sessions.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(sessions))


def _write_history(path: Path, dates: list[date], *, price: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "symbol",
                "date",
                "open",
                "high",
                "low",
                "close",
                "adjusted_close",
                "volume",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        for item in dates:
            writer.writerow(
                {
                    "symbol": "SPY",
                    "date": item.isoformat(),
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "adjusted_close": price,
                    "volume": "1000",
                }
            )


def _append_target(path: Path, *, price: str) -> None:
    with path.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("SPY", TARGET.isoformat(), price, price, price, price, price, "1200"))


def _snapshot(*, price: str = "101", trade_at: datetime | None = None) -> SpyDecisionSnapshot:
    return SpyDecisionSnapshot(
        daily_bar_at=datetime(2026, 7, 28, 13, 30, tzinfo=UTC),
        latest_trade_at=trade_at or datetime(2026, 7, 28, 13, 59, 30, tzinfo=UTC),
        daily_open=Decimal("100"),
        daily_high=Decimal("102"),
        daily_low=Decimal("99"),
        daily_close=Decimal(price),
        daily_volume=123456,
        latest_trade_price=Decimal(price),
    )


def _capture(
    root: Path,
    *,
    apply: bool = True,
    snapshot: SpyDecisionSnapshot | None = None,
    env: dict[str, str] | None = None,
) -> tuple[dict[str, Any], FakeProvider, list[tuple[str, str]]]:
    provider = FakeProvider()
    calls: list[tuple[str, str]] = []

    def fetcher(key: str, secret: str) -> SpyDecisionSnapshot:
        calls.append((key, secret))
        return snapshot or _snapshot()

    result = capture_spy_decision_time_shadow(
        as_of=OBSERVED_AT.isoformat(),
        apply=apply,
        credential_reference=REFERENCE,
        credential_provider=provider,
        snapshot_fetcher=fetcher,
        env={} if env is None else env,
        root=root,
    )
    return result, provider, calls


def test_capture_dry_run_is_eligible_without_credentials_network_or_write(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)

    result, provider, calls = _capture(root, apply=False)

    assert result["state"] == "capture_dry_run_eligible"
    assert result["session_id"] == TARGET.isoformat()
    assert result["apply_eligible"] is True
    assert result["network_access_attempted"] is False
    assert result["credential_access_attempted"] is False
    assert result["exit_code"] == 1
    assert provider.open_count == 0
    assert calls == []
    assert not (root / "runs" / "paper_lab" / "spy_decision_time_shadow").exists()


def test_capture_records_one_advisory_provisional_decision(tmp_path: Path) -> None:
    root = _root(tmp_path)

    result, provider, calls = _capture(root)

    assert result["state"] == "provisional_decision_recorded"
    assert result["decision"] == "target_long"
    assert result["posture"] == "bullish_risk_on"
    assert result["execution_window"] == "next_session_open"
    assert result["planned_execution_at"] == "2026-07-29T13:30:00+00:00"
    assert result["network_access_attempted"] is True
    assert result["credential_access_attempted"] is True
    assert result["broker_access_attempted"] is False
    assert result["broker_mutation_performed"] is False
    assert result["paper_submit_performed"] is False
    assert result["execution_intent_created"] is False
    assert result["execution_plan_created"] is False
    assert result["exit_code"] == 0
    assert provider.open_count == 1
    assert calls == [("test-key", "test-secret")]

    receipt_path = (
        root
        / "runs"
        / "paper_lab"
        / "spy_decision_time_shadow"
        / TARGET.isoformat()
        / "provisional.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["price_basis"] == (
        "current_iex_trade_as_provisional_adjusted_close_proxy"
    )
    assert receipt["feed_scope"] == "iex_single_exchange_not_consolidated_sip"
    assert receipt["http_get_limit"] == 1
    assert receipt["http_timeout_seconds"] == 10.0
    assert receipt["http_response_byte_limit"] == 262_144
    assert receipt["live_authorized"] is False
    assert "test-key" not in receipt_path.read_text(encoding="utf-8")
    assert "test-secret" not in receipt_path.read_text(encoding="utf-8")


def test_capture_is_idempotent_without_second_credential_or_network_access(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    first, _, _ = _capture(root)
    assert first["exit_code"] == 0

    second, provider, calls = _capture(root)

    assert second["state"] == "provisional_decision_already_recorded"
    assert second["network_access_attempted"] is False
    assert second["credential_access_attempted"] is False
    assert provider.open_count == 0
    assert calls == []


@pytest.mark.parametrize(
    ("as_of", "refusal"),
    (
        ("2026-07-28T13:29:59+00:00", "session_not_open"),
        ("2026-07-28T20:00:00+00:00", "session_already_closed"),
        ("2026-07-25T14:00:00+00:00", "not_nyse_session"),
    ),
)
def test_capture_refuses_outside_active_nyse_session(
    tmp_path: Path,
    as_of: str,
    refusal: str,
) -> None:
    root = _root(tmp_path)
    provider = FakeProvider()

    result = capture_spy_decision_time_shadow(
        as_of=as_of,
        apply=True,
        credential_reference=REFERENCE,
        credential_provider=provider,
        snapshot_fetcher=lambda _key, _secret: _snapshot(),
        env={},
        root=root,
    )

    assert result["state"] == "capture_refused"
    assert result["refusal_category"] == refusal
    assert result["network_access_attempted"] is False
    assert provider.open_count == 0


def test_capture_fails_closed_on_stale_trade_and_live_signal(tmp_path: Path) -> None:
    root = _root(tmp_path)
    stale, provider, calls = _capture(
        root,
        snapshot=_snapshot(
            trade_at=OBSERVED_AT - timedelta(seconds=301),
        ),
    )
    assert stale["refusal_category"] == "snapshot_latest_trade_stale"
    assert stale["network_access_attempted"] is True
    assert provider.open_count == 1
    assert len(calls) == 1

    live_root = _root(tmp_path / "live")
    refused, live_provider, live_calls = _capture(
        live_root,
        env={"ALLOW_LIVE_TRADING": "true"},
    )
    assert refused["refusal_category"] == "paper_interlock_refused"
    assert refused["network_access_attempted"] is False
    assert refused["credential_access_attempted"] is False
    assert live_provider.open_count == 0
    assert live_calls == []


def test_normalize_and_transport_use_exact_bounded_snapshot_scope() -> None:
    payload = json.dumps(
        {
            "dailyBar": {
                "t": "2026-07-28T13:30:00Z",
                "o": 100,
                "h": 102,
                "l": 99,
                "c": 101,
                "v": 1000,
            },
            "latestTrade": {
                "t": "2026-07-28T13:59:30Z",
                "p": 101,
            },
        }
    ).encode("utf-8")
    response = FakeResponse(payload)
    connection = FakeConnection(response)
    factory_calls: list[tuple[str, float]] = []

    def factory(host: str, *, timeout: float) -> FakeConnection:
        factory_calls.append((host, timeout))
        return connection

    snapshot = alpaca_bounded_spy_snapshot_get(
        "key",
        "secret",
        connection_factory=factory,
    )

    assert snapshot.latest_trade_price == Decimal("101")
    assert factory_calls == [(ALPACA_SPY_SNAPSHOT_HOST, 10.0)]
    assert connection.request_args == ("GET", ALPACA_SPY_SNAPSHOT_PATH)
    assert connection.request_kwargs is not None
    assert set(connection.request_kwargs["headers"]) == {
        "APCA-API-KEY-ID",
        "APCA-API-SECRET-KEY",
        "Accept",
    }
    assert response.read_limit == 262_145
    assert connection.closed is True


def test_transport_refuses_oversized_or_incomplete_snapshot() -> None:
    response = FakeResponse(b"x" * 262_145)
    connection = FakeConnection(response)

    with pytest.raises(
        SpyDecisionTimeShadowError,
        match="market_data_response_too_large",
    ):
        alpaca_bounded_spy_snapshot_get(
            "key",
            "secret",
            connection_factory=lambda _host, timeout: connection,
        )

    with pytest.raises(
        SpyDecisionTimeShadowError,
        match="market_data_snapshot_incomplete",
    ):
        normalize_alpaca_spy_snapshot({"dailyBar": {}})


def test_reconciliation_records_matched_and_is_idempotent(tmp_path: Path) -> None:
    root = _root(tmp_path)
    capture, _, _ = _capture(root)
    assert capture["decision"] == "target_long"
    canonical = (
        root
        / "runs"
        / "operator_input"
        / "m446_spy_daily_tiingo_adjusted_canonical.csv"
    )
    _append_target(canonical, price="101")

    result = reconcile_spy_decision_time_shadow(
        session_id=TARGET.isoformat(),
        as_of="2026-07-29T00:11:00+00:00",
        root=root,
    )
    repeated = reconcile_spy_decision_time_shadow(
        session_id=TARGET.isoformat(),
        as_of="2026-07-29T00:12:00+00:00",
        root=root,
    )

    assert result["state"] == "reconciled"
    assert result["classification"] == "matched"
    assert result["provisional_decision"] == "target_long"
    assert result["authoritative_decision"] == "target_long"
    assert result["network_access_attempted"] is False
    assert result["credential_access_attempted"] is False
    assert result["exit_code"] == 0
    assert repeated["state"] == "reconciliation_already_recorded"
    assert repeated["classification"] == "matched"


def test_reconciliation_observes_decision_divergence(tmp_path: Path) -> None:
    root = _root(tmp_path)
    capture, _, _ = _capture(root)
    assert capture["decision"] == "target_long"
    canonical = (
        root
        / "runs"
        / "operator_input"
        / "m446_spy_daily_tiingo_adjusted_canonical.csv"
    )
    _append_target(canonical, price="99")

    result = reconcile_spy_decision_time_shadow(
        session_id=TARGET.isoformat(),
        as_of="2026-07-29T00:11:00+00:00",
        root=root,
    )

    assert result["state"] == "reconciled"
    assert result["classification"] == "diverged"
    assert result["provisional_decision"] == "target_long"
    assert result["authoritative_decision"] == "target_cash"
    assert result["paper_submit_performed"] is False
    assert result["live_authorized"] is False


def test_reconciliation_waits_for_authoritative_session_bar(tmp_path: Path) -> None:
    root = _root(tmp_path)
    capture, _, _ = _capture(root)
    assert capture["exit_code"] == 0

    result = reconcile_spy_decision_time_shadow(
        session_id=TARGET.isoformat(),
        as_of="2026-07-28T20:01:00+00:00",
        root=root,
    )

    assert result["state"] == "pending_authoritative_adjusted_bar"
    assert result["canonical_latest_bar_date"] == "2026-07-27"
    assert result["network_access_attempted"] is False
    assert result["exit_code"] == 1


def test_shadow_module_has_no_order_or_broker_mutation_calls() -> None:
    path = Path("src/algotrader/execution/spy_decision_time_shadow.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden = {
        "cancel_order",
        "close_all_positions",
        "close_position",
        "create_order",
        "liquidate",
        "replace_order",
        "submit_order",
        "submit_order_request",
    }

    call_names = {
        node.func.id
        if isinstance(node.func, ast.Name)
        else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    assert call_names.isdisjoint(forbidden)
