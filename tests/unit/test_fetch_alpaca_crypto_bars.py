from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

MODULE_PATH = Path("scripts/research/fetch_alpaca_crypto_bars.py")
MODULE_NAME = "fetch_alpaca_crypto_bars_for_tests"

GENERATED_AT = datetime(2026, 7, 3, 2, tzinfo=UTC)
SENSITIVE_KEY = "paper-key-value-not-for-output"
SENSITIVE_SECRET = "paper-secret-value-not-for-output"
VALID_ENV = {
    "APP_PROFILE": "paper",
    "APCA_API_KEY_ID": SENSITIVE_KEY,
    "APCA_API_SECRET_KEY": SENSITIVE_SECRET,
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


def test_crypto_bars_url_uses_official_v1beta3_endpoint_and_ascending_sort() -> None:
    fetcher = load_fetcher()

    url = fetcher.build_crypto_bars_url(
        api_symbol="BTC/USD",
        start=GENERATED_AT - timedelta(hours=80),
        end=GENERATED_AT,
    )

    assert url.startswith("https://data.alpaca.markets/v1beta3/crypto/us/bars?")
    assert "symbols=BTC%2FUSD" in url
    assert "timeframe=1Hour" in url
    assert "sort=asc" in url
    assert "limit=10000" in url


def test_fetch_uses_get_request_without_body_and_keyword_timeout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fetcher = load_fetcher()
    credentials = fetcher.AlpacaCredentials(SENSITIVE_KEY, SENSITIVE_SECRET)
    requests: list[object] = []

    def opener(request: object, *args: object, **kwargs: object) -> FakeResponse:
        requests.append(request)
        assert args == ()
        assert kwargs == {"timeout": 17}
        assert request.get_method() == "GET"
        assert request.data is None
        lower_url = request.full_url.lower()
        assert "v1beta3/crypto/us/bars" in lower_url
        assert "orders" not in lower_url
        assert "submit" not in lower_url
        return FakeResponse({"bars": {"BTC/USD": _bars()}, "next_page_token": None})

    payload = fetcher.fetch_alpaca_crypto_bars(
        api_symbol="BTC/USD",
        start=GENERATED_AT - timedelta(hours=80),
        end=GENERATED_AT,
        credentials=credentials,
        allow_network=True,
        market_data_fetch_authorized=True,
        opener=opener,
        timeout=17,
    )
    captured = capsys.readouterr()

    assert len(requests) == 1
    assert len(payload["bars"]["BTC/USD"]) == 60
    assert captured.out == ""
    assert captured.err == ""
    assert SENSITIVE_KEY not in captured.out + captured.err
    assert SENSITIVE_SECRET not in captured.out + captured.err


def test_fetch_and_intake_uses_fake_opener_and_writes_canonical_outputs(
    tmp_path: Path,
) -> None:
    fetcher = load_fetcher()
    requests: list[object] = []

    def opener(request: object, timeout: int) -> FakeResponse:
        requests.append(request)
        assert timeout == 30
        return FakeResponse({"bars": {"BTC/USD": _bars()}, "next_page_token": None})

    payload = fetcher.fetch_and_intake_crypto_bars(
        raw_response_path=tmp_path / "raw.json",
        canonical_csv=tmp_path / "crypto_paper_bars.csv",
        run_log=tmp_path / "manifest.jsonl",
        observed_at=GENERATED_AT,
        allow_network=True,
        market_data_fetch_authorized=True,
        env=VALID_ENV,
        opener=opener,
    )
    rendered = fetcher.render_crypto_bars_intake_text(payload)

    assert len(requests) == 1
    request = requests[0]
    assert "v1beta3/crypto/us/bars" in request.full_url
    assert "symbols=BTC%2FUSD" in request.full_url
    assert payload["intake_state"] == "accepted_fresh_crypto_bars"
    assert payload["market_data_read_performed"] is True
    assert payload["network_access_attempted"] is True
    assert payload["operator_preflight"]["APP_PROFILE_is_paper"] is True
    assert payload["operator_preflight"]["paper_credentials_present"] is True
    assert (tmp_path / "crypto_paper_bars.csv").is_file()
    assert (tmp_path / "manifest.jsonl").is_file()
    assert SENSITIVE_KEY not in rendered
    assert SENSITIVE_SECRET not in rendered


def test_fetch_requires_explicit_network_and_market_data_authorization() -> None:
    fetcher = load_fetcher()
    credentials = fetcher.AlpacaCredentials(SENSITIVE_KEY, SENSITIVE_SECRET)
    called = False

    def opener(request: object, timeout: int) -> FakeResponse:
        nonlocal called
        called = True
        return FakeResponse({})

    with pytest.raises(fetcher.CryptoBarsFetchError, match="requires --allow-network"):
        fetcher.fetch_alpaca_crypto_bars(
            api_symbol="BTC/USD",
            start=GENERATED_AT - timedelta(hours=80),
            end=GENERATED_AT,
            credentials=credentials,
            allow_network=False,
            market_data_fetch_authorized=True,
            opener=opener,
        )

    assert called is False


def test_fetch_error_redacts_credentials_from_exception_message() -> None:
    fetcher = load_fetcher()
    credentials = fetcher.AlpacaCredentials(SENSITIVE_KEY, SENSITIVE_SECRET)

    def opener(request: object, timeout: int) -> FakeResponse:
        raise RuntimeError(f"network failed key={SENSITIVE_KEY} secret={SENSITIVE_SECRET}")

    with pytest.raises(fetcher.CryptoBarsFetchError) as exc_info:
        fetcher.fetch_alpaca_crypto_bars(
            api_symbol="BTC/USD",
            start=GENERATED_AT - timedelta(hours=80),
            end=GENERATED_AT,
            credentials=credentials,
            allow_network=True,
            market_data_fetch_authorized=True,
            opener=opener,
        )

    message = str(exc_info.value)
    assert SENSITIVE_KEY not in message
    assert SENSITIVE_SECRET not in message
    assert "<redacted>" in message


def test_live_profile_blocks_before_opener(tmp_path: Path) -> None:
    fetcher = load_fetcher()
    called = False

    def opener(request: object, timeout: int) -> FakeResponse:
        nonlocal called
        called = True
        return FakeResponse({"bars": {"BTC/USD": _bars()}})

    with pytest.raises(fetcher.CryptoBarsFetchError, match="live endpoint"):
        fetcher.fetch_and_intake_crypto_bars(
            raw_response_path=tmp_path / "raw.json",
            canonical_csv=tmp_path / "canonical.csv",
            run_log=tmp_path / "manifest.jsonl",
            observed_at=GENERATED_AT,
            allow_network=True,
            market_data_fetch_authorized=True,
            env={**VALID_ENV, "APP_PROFILE": "live"},
            opener=opener,
        )

    assert called is False


def test_credentials_repr_is_redacted() -> None:
    fetcher = load_fetcher()
    credentials = fetcher.read_credentials_from_env(VALID_ENV)

    assert SENSITIVE_KEY not in repr(credentials)
    assert SENSITIVE_SECRET not in repr(credentials)
    assert "<redacted>" in repr(credentials)


def load_fetcher() -> ModuleType:
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _bars() -> list[dict[str, object]]:
    latest_at = GENERATED_AT - timedelta(minutes=30)
    first = latest_at - timedelta(hours=59)
    bars: list[dict[str, object]] = []
    for index in range(60):
        close = Decimal("50000") + Decimal(index)
        timestamp = first + timedelta(hours=index)
        bars.append(
            {
                "t": timestamp.isoformat().replace("+00:00", "Z"),
                "o": str(close - Decimal("1")),
                "h": str(close + Decimal("2")),
                "l": str(close - Decimal("2")),
                "c": str(close),
                "v": "1.25",
            }
        )
    return bars
