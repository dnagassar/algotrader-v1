from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
import urllib.parse

from algotrader.execution.crypto_history_refresh_adapter import (
    CRYPTO_HISTORY_REFRESH_DEFAULT_OUTPUT_PATH,
    CryptoHistoryRefreshConfig,
    run_crypto_history_refresh,
)
from algotrader.research.crypto_strategy_evidence_battery import (
    DEFAULT_CRYPTO_EVIDENCE_SYMBOLS,
    build_crypto_strategy_real_data_evidence_packet,
    load_crypto_evidence_bars_from_csv,
)

AS_OF = datetime(2026, 7, 9, 0, 0, tzinfo=UTC)
SENSITIVE_KEY = "history-refresh-key-not-for-output"
SENSITIVE_SECRET = "history-refresh-secret-not-for-output"
VALID_ENV = {
    "APP_PROFILE": "paper",
    "APCA_API_KEY_ID": SENSITIVE_KEY,
    "APCA_API_SECRET_KEY": SENSITIVE_SECRET,
    "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
}


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_dry_run_builds_command_packet_without_writing_history(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "crypto_history.csv"
    packet_path = tmp_path / "packet.json"

    packet = run_crypto_history_refresh(
        CryptoHistoryRefreshConfig(
            mode="dry_run",
            output_path=output_path,
            packet_path=packet_path,
            as_of=AS_OF,
        ),
        env={},
    )

    assert packet["classification"] == "dry_run_ready"
    assert packet["requested_symbols"] == list(DEFAULT_CRYPTO_EVIDENCE_SYMBOLS)
    assert packet["output_path"] == str(output_path)
    assert packet["authorization_status"] == "not_required_for_dry_run"
    assert packet["market_data_fetch_occurred"] is False
    assert packet["broker_mutation_occurred"] is False
    assert packet["paper_submit_occurred"] is False
    assert not output_path.exists()
    assert json.loads(packet_path.read_text(encoding="utf-8")) == packet

    command_text = str(packet["generated_command_text"]).lower()
    assert "refresh_multi_symbol_crypto_history.ps1" in command_text
    assert "-marketdatafetchauthorized" in command_text
    for forbidden in ("submit", "cancel", "replace", "close", "liquidate"):
        assert forbidden not in command_text


def test_offline_fixture_writes_multi_symbol_output_and_stays_fixture_blocked(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "fixture_history.csv"

    packet = run_crypto_history_refresh(
        CryptoHistoryRefreshConfig(
            mode="offline_fixture",
            output_path=output_path,
            packet_path=None,
            as_of=AS_OF,
        ),
        env={},
    )

    assert packet["classification"] == "offline_fixture_ready"
    assert packet["coverage_gate_classification"] == "insufficient_real_crypto_history"
    assert packet["paper_planning_eligibility"] == "not_eligible"
    assert packet["fetched_symbols"] == list(DEFAULT_CRYPTO_EVIDENCE_SYMBOLS)
    assert packet["rows_per_symbol"] == {
        symbol: 80 for symbol in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
    }
    assert packet["missing_symbols"] == []
    assert packet["schema_validation_status"] == "passed"
    assert output_path.is_file()

    loaded_bars = load_crypto_evidence_bars_from_csv(output_path)
    assert len(loaded_bars) == 320
    gate_packet = build_crypto_strategy_real_data_evidence_packet(
        output_path,
        as_of=AS_OF,
    )
    assert gate_packet["classification"] == "insufficient_real_crypto_history"
    assert "fixture_only_history" in gate_packet["data_inventory"]["blocking_reasons"]


def test_missing_symbol_fixture_blocks_history_sufficiency(tmp_path: Path) -> None:
    fixture_input = tmp_path / "missing_eth.csv"
    output_path = tmp_path / "output.csv"
    _write_crypto_csv(
        fixture_input,
        (
            *_bars("BTCUSD", 80),
            *_bars("SOLUSD", 80),
            *_bars("ADAUSD", 80),
        ),
    )

    packet = run_crypto_history_refresh(
        CryptoHistoryRefreshConfig(
            mode="offline_fixture",
            fixture_input_path=fixture_input,
            output_path=output_path,
            packet_path=None,
            as_of=AS_OF,
        ),
        env={},
    )

    assert packet["classification"] == "insufficient_real_crypto_history"
    assert packet["coverage_gate_classification"] == "insufficient_real_crypto_history"
    assert packet["missing_symbols"] == ["ETHUSD"]
    assert "missing_required_symbols" in packet["coverage_gate_blocking_reasons"]
    assert output_path.is_file()


def test_market_data_fetch_rejects_live_endpoint_before_opener(
    tmp_path: Path,
) -> None:
    called = False

    def opener(request: object, *, timeout: int) -> FakeResponse:
        nonlocal called
        called = True
        return FakeResponse({})

    packet = run_crypto_history_refresh(
        CryptoHistoryRefreshConfig(
            mode="market_data_fetch",
            output_path=tmp_path / "history.csv",
            packet_path=None,
            as_of=AS_OF,
            allow_network=True,
            market_data_fetch_authorized=True,
        ),
        env={**VALID_ENV, "APCA_API_BASE_URL": "https://api.alpaca.markets"},
        opener=opener,
    )

    assert packet["classification"] == "rejected_live_endpoint_risk"
    assert packet["endpoint_safety_status"] == "rejected_live_endpoint_risk"
    assert packet["market_data_fetch_occurred"] is False
    assert packet["network_access_attempted"] is False
    assert packet["live_endpoint_touched"] is False
    assert called is False


def test_market_data_fetch_requires_authorization_flag_before_opener(
    tmp_path: Path,
) -> None:
    called = False

    def opener(request: object, *, timeout: int) -> FakeResponse:
        nonlocal called
        called = True
        return FakeResponse({})

    packet = run_crypto_history_refresh(
        CryptoHistoryRefreshConfig(
            mode="market_data_fetch",
            output_path=tmp_path / "history.csv",
            packet_path=None,
            as_of=AS_OF,
            allow_network=True,
            market_data_fetch_authorized=False,
        ),
        env=VALID_ENV,
        opener=opener,
    )

    assert packet["classification"] == "market_data_refresh_not_configured"
    assert "authorization_flag_required" in packet["authorization_status"]
    assert packet["market_data_fetch_occurred"] is False
    assert called is False


def test_authorized_market_data_fetch_uses_read_only_urls_and_coverage_gate(
    tmp_path: Path,
) -> None:
    requests: list[object] = []

    def opener(request: object, *, timeout: int) -> FakeResponse:
        requests.append(request)
        assert timeout == 30
        assert request.get_method() == "GET"
        assert request.data is None
        lower_url = request.full_url.lower()
        assert "/v1beta3/crypto/us/bars" in lower_url
        assert "orders" not in lower_url
        assert "submit" not in lower_url
        query = urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)
        api_symbol = query["symbols"][0]
        return FakeResponse({"bars": {api_symbol: _api_bars(api_symbol)}})

    output_path = tmp_path / "history.csv"
    packet = run_crypto_history_refresh(
        CryptoHistoryRefreshConfig(
            mode="market_data_fetch",
            output_path=output_path,
            raw_response_path=tmp_path / "raw.json",
            packet_path=None,
            as_of=AS_OF,
            allow_network=True,
            market_data_fetch_authorized=True,
        ),
        env=VALID_ENV,
        opener=opener,
    )

    assert len(requests) == 4
    assert packet["classification"] == "sufficient_real_crypto_history"
    assert packet["coverage_gate_classification"] == "sufficient_real_crypto_history"
    assert packet["rows_per_symbol_after_normalization"] == {
        symbol: 80 for symbol in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
    }
    assert packet["duplicate_rows_removed_per_symbol"] == {
        symbol: 0 for symbol in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
    }
    assert packet["market_data_fetch_occurred"] is True
    assert packet["network_access_attempted"] is True
    assert packet["broker_read_occurred"] is False
    assert packet["broker_mutation_occurred"] is False
    assert packet["paper_submit_occurred"] is False
    assert SENSITIVE_KEY not in json.dumps(packet, sort_keys=True)
    assert SENSITIVE_SECRET not in json.dumps(packet, sort_keys=True)
    assert output_path.is_file()


def test_default_output_path_remains_coverage_gate_compatible() -> None:
    assert str(CRYPTO_HISTORY_REFRESH_DEFAULT_OUTPUT_PATH).replace("\\", "/") == (
        "runs/operator_input/crypto_paper_bars.csv"
    )


def _api_bars(api_symbol: str) -> list[dict[str, object]]:
    symbol = api_symbol.replace("/", "")
    offset = {
        "BTCUSD": Decimal("100"),
        "ETHUSD": Decimal("200"),
        "SOLUSD": Decimal("300"),
        "ADAUSD": Decimal("1"),
    }[symbol]
    step = Decimal("0.01") if symbol == "ADAUSD" else Decimal("1")
    first = AS_OF - timedelta(hours=79)
    bars: list[dict[str, object]] = []
    for index in range(80):
        close = offset + (step * Decimal(index))
        bars.append(
            {
                "t": (first + timedelta(hours=index)).isoformat().replace(
                    "+00:00",
                    "Z",
                ),
                "o": str(close),
                "h": str(close + step),
                "l": str(max(close - step, Decimal("0.00000001"))),
                "c": str(close),
                "v": "1",
            }
        )
    return bars


def _bars(symbol: str, count: int) -> tuple[tuple[str, datetime, Decimal], ...]:
    first = AS_OF - timedelta(hours=count - 1)
    start = Decimal("1") if symbol == "ADAUSD" else Decimal("100")
    step = Decimal("0.01") if symbol == "ADAUSD" else Decimal("1")
    return tuple(
        (symbol, first + timedelta(hours=index), start + (step * Decimal(index)))
        for index in range(count)
    )


def _write_crypto_csv(
    path: Path,
    bars: tuple[tuple[str, datetime, Decimal], ...],
) -> None:
    lines = ["timestamp,symbol,asset_class,open,high,low,close,volume,basis,source"]
    for symbol, timestamp, close in bars:
        close_text = str(close)
        lines.append(
            ",".join(
                (
                    timestamp.isoformat(),
                    symbol,
                    "crypto",
                    close_text,
                    close_text,
                    close_text,
                    close_text,
                    "1",
                    "unit_test_ohlcv",
                    "offline_fixture",
                )
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
