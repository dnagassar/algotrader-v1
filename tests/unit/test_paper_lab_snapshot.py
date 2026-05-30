from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import json

import algotrader.cli as cli_module
from algotrader.cli import main
from algotrader.execution.alpaca_adapter import AlpacaClientAdapter
from algotrader.execution.alpaca_broker import AlpacaPaperBroker
from algotrader.execution.alpaca_client import AlpacaOrderResponse
from tests.fakes.alpaca import FakeAlpacaClient


SENSITIVE_API_KEY = "paper-lab-snapshot-api-key"
SENSITIVE_SECRET_KEY = "paper-lab-snapshot-secret-key"
SNAPSHOT_TIME = datetime(2026, 5, 29, 14, 30, tzinfo=UTC)


def test_paper_lab_snapshot_observes_account_positions_and_orders_read_only(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FakeSnapshotAlpacaClient())

    exit_code, payload = _run_json(("paper-lab-snapshot", "--format", "json"), capsys)

    assert exit_code == 0
    assert fake_client.calls == ["get_account", "get_positions", "get_orders"]
    assert fake_client.submitted_requests == []
    assert payload["ok"] is True
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["account_observation_available"] is True
    assert payload["positions_observation_available"] is True
    assert payload["orders_observation_available"] is True
    assert payload["account"] == {"cash": "100000", "currency": "USD"}
    assert payload["position_count"] == 1
    assert payload["position_symbols"] == ["MSFT"]
    assert payload["recent_order_count"] == 1
    assert payload["recent_orders"] == [
        {
            "asset_class": "equity",
            "filled_at": "",
            "normalized_status": "accepted",
            "notional": "5.00",
            "order_type": "market",
            "quantity": "",
            "raw_status": "OrderStatus.ACCEPTED",
            "side": "buy",
            "submitted_at": "2026-05-29T14:30:00+00:00",
            "symbol": "SPY",
            "time_in_force": "day",
        }
    ]


def test_paper_lab_snapshot_writes_append_only_observation_log(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    _install_fake_broker(monkeypatch, FakeSnapshotAlpacaClient())
    run_log = tmp_path / "runs" / "paper_lab" / "snapshot.jsonl"

    exit_code, payload = _run_json(
        (
            "paper-lab-snapshot",
            "--run-log",
            str(run_log),
            "--run-id",
            "snapshot-run",
            "--format",
            "json",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    rendered = run_log.read_text(encoding="utf-8")
    assert exit_code == 0
    assert [record["event_type"] for record in records] == [
        "paper_lab_snapshot_requested",
        "paper_lab_snapshot_account_observed",
        "paper_lab_snapshot_positions_observed",
        "paper_lab_snapshot_orders_observed",
    ]
    assert {record["run_id"] for record in records} == {"snapshot-run"}
    assert records[0]["command"] == "paper-lab-snapshot"
    assert records[1]["account"] == payload["account"]
    assert records[2]["position_symbols"] == ["MSFT"]
    assert records[3]["recent_orders"] == payload["recent_orders"]
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered


def test_paper_lab_snapshot_rejects_live_profile_without_building_broker(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch, profile="live")
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(("paper-lab-snapshot", "--format", "json"), capsys)

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["error"] == "profile_gate_failed"
    assert payload["gates"]["profile_gate"]["passed"] is False
    assert payload["account_observation_available"] is False
    assert payload["positions_observation_available"] is False
    assert payload["orders_observation_available"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False


def test_paper_lab_snapshot_marks_orders_unavailable_without_submitting(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FakeAlpacaClient())
    run_log = tmp_path / "runs" / "paper_lab" / "snapshot_unavailable.jsonl"

    exit_code, payload = _run_json(
        (
            "paper-lab-snapshot",
            "--run-log",
            str(run_log),
            "--run-id",
            "orders-unavailable-run",
            "--format",
            "json",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    rendered = json.dumps(payload, sort_keys=True) + run_log.read_text(
        encoding="utf-8"
    )
    assert exit_code == 1
    assert fake_client.calls == ["get_account", "get_positions"]
    assert fake_client.submitted_requests == []
    assert payload["ok"] is False
    assert payload["error"] == "paper_lab_snapshot_unavailable"
    assert payload["account_observation_available"] is True
    assert payload["positions_observation_available"] is True
    assert payload["orders_observation_available"] is False
    assert payload["unavailable_observations"] == ["orders"]
    assert payload["unavailable_reasons"]["orders"]["error_type"] == (
        "AlpacaAdapterError"
    )
    assert [record["event_type"] for record in records] == [
        "paper_lab_snapshot_requested",
        "paper_lab_snapshot_account_observed",
        "paper_lab_snapshot_positions_observed",
        "paper_lab_snapshot_unavailable",
    ]
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered
    assert "https://paper.example.test" not in rendered


def _set_env(monkeypatch, *, profile: str = "paper") -> None:
    monkeypatch.setenv("APP_PROFILE", profile)
    monkeypatch.setenv("ALPACA_API_KEY", SENSITIVE_API_KEY)
    monkeypatch.setenv("ALPACA_SECRET_KEY", SENSITIVE_SECRET_KEY)
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper.example.test")
    monkeypatch.delenv("ALGOTRADER_PAPER_HALT", raising=False)


class FakeSnapshotAlpacaClient(FakeAlpacaClient):
    def get_orders(self) -> list[AlpacaOrderResponse]:
        self.calls.append("get_orders")
        return [
            AlpacaOrderResponse(
                order_id="broker-order-1",
                client_order_id="paper-order-probe-notional-1",
                symbol="spy",
                side="buy",
                status="OrderStatus.ACCEPTED",
                notional=Decimal("5.00"),
                asset_class="equity",
                order_type="market",
                time_in_force="day",
                submitted_at=SNAPSHOT_TIME,
            )
        ]


def _install_fake_broker(
    monkeypatch,
    fake_client: FakeAlpacaClient,
) -> FakeAlpacaClient:
    def build_broker(paper_config):  # noqa: ANN001
        return AlpacaPaperBroker(
            adapter=AlpacaClientAdapter(fake_client),
            config=paper_config,
        )

    monkeypatch.setattr(cli_module, "_build_paper_broker", build_broker)
    return fake_client


def _forbid_broker_build(monkeypatch) -> None:
    def forbidden_build(paper_config):  # noqa: ANN001
        raise AssertionError("paper lab snapshot must not build a broker")

    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_build)


def _run_json(argv: tuple[str, ...], capsys) -> tuple[int, dict[str, object]]:
    output = _run_raw_json(argv, capsys)
    return _LAST_EXIT_CODE, json.loads(output)


def _run_raw_json(argv: tuple[str, ...], capsys) -> str:
    global _LAST_EXIT_CODE
    _LAST_EXIT_CODE = main(argv)
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out.strip()


def _read_jsonl(path) -> list[dict[str, object]]:  # noqa: ANN001
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


_LAST_EXIT_CODE = 0
