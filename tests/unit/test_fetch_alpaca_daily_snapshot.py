import ast
import hashlib
import importlib.util
import json
import sys
import urllib.error
import urllib.parse
from pathlib import Path
from types import ModuleType

import pytest


MODULE_PATH = Path("scripts/research/fetch_alpaca_daily_snapshot.py")
MODULE_NAME = "fetch_alpaca_daily_snapshot_for_tests"
SNAPSHOT_DIR = Path(".data") / "research_snapshots"
CSV_HEADER = "date,open,high,low,close,adjusted_close,volume"

RAW_KEY_ID = "raw-test-key-id"
RAW_SECRET_KEY = "raw-test-secret-key"
VALID_ENV = {
    "ALPACA_API_KEY_ID": RAW_KEY_ID,
    "ALPACA_API_SECRET_KEY": RAW_SECRET_KEY,
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "numpy",
    "openai",
    "pandas",
    "QuantConnect",
    "quantconnect",
    "requests",
    "sqlmodel",
    "vectorbt",
    "yfinance",
)

_FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "create_order",
    "get_account",
    "get_order",
    "get_position",
    "list_orders",
    "list_positions",
    "post",
    "read_csv",
    "submit_order",
    "to_sql",
}

_FORBIDDEN_CALL_SUFFIXES = (
    ".cancel_order",
    ".create_order",
    ".get_account",
    ".get_order",
    ".get_position",
    ".list_orders",
    ".list_positions",
    ".post",
    ".read_csv",
    ".submit_order",
    ".to_sql",
)


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def load_fetcher() -> ModuleType:
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def daily_bar(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "t": "2026-01-02T05:00:00Z",
        "o": "100.00",
        "h": "101.50",
        "l": "99.75",
        "c": "100.25",
        "v": 123456,
    }
    values.update(overrides)
    return values


def opener_for(payload: object, requests: list[object] | None = None):
    def fake_opener(request: object, timeout: int) -> FakeResponse:
        if requests is not None:
            requests.append(request)
        return FakeResponse(payload)

    return fake_opener


def test_missing_allow_network_blocks_fetch_and_does_not_write(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fetcher = load_fetcher()
    output_path = tmp_path / SNAPSHOT_DIR / "SPY_daily.csv"

    exit_code = fetcher.main(
        (
            "--start",
            "2026-01-02",
            "--end",
            "2026-01-03",
            "--output",
            str(output_path),
        )
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "allow-network" in captured.err
    assert captured.out == ""
    assert not output_path.exists()


def test_missing_credentials_are_rejected_before_any_fetch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fetcher = load_fetcher()
    monkeypatch.delenv("ALPACA_API_KEY_ID", raising=False)
    monkeypatch.delenv("ALPACA_API_SECRET_KEY", raising=False)

    exit_code = fetcher.main(
        (
            "--allow-network",
            "--start",
            "2026-01-02",
            "--end",
            "2026-01-03",
            "--output",
            str(tmp_path / SNAPSHOT_DIR / "SPY_daily.csv"),
        )
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Missing Alpaca Market Data credentials" in captured.err
    assert RAW_KEY_ID not in captured.err
    assert RAW_SECRET_KEY not in captured.err


def test_credentials_are_not_printed_or_serialized() -> None:
    fetcher = load_fetcher()
    credentials = fetcher.read_credentials_from_env(VALID_ENV)

    assert RAW_KEY_ID not in repr(credentials)
    assert RAW_SECRET_KEY not in repr(credentials)
    assert RAW_KEY_ID not in str(credentials)
    assert RAW_SECRET_KEY not in str(credentials)

    def failing_opener(request: object, timeout: int) -> FakeResponse:
        raise RuntimeError(f"network failure included {RAW_SECRET_KEY}")

    with pytest.raises(fetcher.SnapshotFetchError) as exc_info:
        fetcher.fetch_alpaca_daily_bars(
            "SPY",
            "2026-01-02",
            "2026-01-03",
            credentials,
            opener=failing_opener,
        )

    assert RAW_KEY_ID not in str(exc_info.value)
    assert RAW_SECRET_KEY not in str(exc_info.value)


def test_request_url_construction_uses_market_data_stock_bars_endpoint() -> None:
    fetcher = load_fetcher()

    url = fetcher.build_request_url(
        " spy ",
        "2026-01-02",
        "2026-01-31",
        page_token="abc123",
    )
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "data.alpaca.markets"
    assert parsed.path == "/v2/stocks/SPY/bars"
    assert query == {
        "timeframe": ["1Day"],
        "start": ["2026-01-02"],
        "end": ["2026-01-31"],
        "adjustment": ["all"],
        "feed": ["iex"],
        "limit": ["10000"],
        "page_token": ["abc123"],
    }


@pytest.mark.parametrize("feed", ("sip", "delayed_sip"))
def test_custom_feed_is_accepted_and_included_in_request_url(feed: str) -> None:
    fetcher = load_fetcher()

    url = fetcher.build_request_url(
        "SPY",
        "2026-01-02",
        "2026-01-31",
        feed=feed,
    )
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)

    assert query["feed"] == [feed]


def test_invalid_feed_is_rejected() -> None:
    fetcher = load_fetcher()

    with pytest.raises(fetcher.SnapshotFetchError, match="feed must be one of"):
        fetcher.build_request_url(
            "SPY",
            "2026-01-02",
            "2026-01-31",
            feed="basic",
        )

    with pytest.raises(SystemExit):
        fetcher.build_parser().parse_args(
            (
                "--start",
                "2026-01-02",
                "--end",
                "2026-01-31",
                "--output",
                "SPY_daily.csv",
                "--feed",
                "basic",
            )
        )


def test_invalid_feed_is_rejected_before_request_execution() -> None:
    fetcher = load_fetcher()
    credentials = fetcher.read_credentials_from_env(VALID_ENV)
    requests: list[object] = []

    with pytest.raises(fetcher.SnapshotFetchError, match="feed must be one of"):
        fetcher.fetch_alpaca_daily_bars(
            "SPY",
            "2026-01-02",
            "2026-01-31",
            credentials,
            feed="basic",
            opener=opener_for({"bars": [daily_bar()]}, requests),
        )

    assert requests == []


def test_output_path_must_be_under_research_snapshots_by_default(
    tmp_path: Path,
) -> None:
    fetcher = load_fetcher()
    allowed_path = tmp_path / SNAPSHOT_DIR / "SPY_daily.csv"

    checked_path = fetcher.validate_output_path(allowed_path, repo_root=tmp_path)

    assert checked_path == allowed_path.resolve()


def test_outside_output_path_requires_explicit_override(tmp_path: Path) -> None:
    fetcher = load_fetcher()
    outside_path = tmp_path / "SPY_daily.csv"

    with pytest.raises(fetcher.SnapshotFetchError, match="research_snapshots"):
        fetcher.validate_output_path(outside_path, repo_root=tmp_path)

    checked_path = fetcher.validate_output_path(
        outside_path,
        repo_root=tmp_path,
        allow_outside_data_dir=True,
    )

    assert checked_path == outside_path.resolve()


def test_existing_output_file_is_rejected_unless_overwrite(tmp_path: Path) -> None:
    fetcher = load_fetcher()
    output_path = tmp_path / SNAPSHOT_DIR / "SPY_daily.csv"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("existing\n", encoding="utf-8")

    with pytest.raises(fetcher.SnapshotFetchError, match="overwrite"):
        fetcher.validate_output_path(output_path, repo_root=tmp_path)

    checked_path = fetcher.validate_output_path(
        output_path,
        repo_root=tmp_path,
        overwrite=True,
    )

    assert checked_path == output_path.resolve()


def test_mocked_alpaca_response_writes_required_csv_columns_and_rows(
    tmp_path: Path,
) -> None:
    fetcher = load_fetcher()
    output_path = tmp_path / SNAPSHOT_DIR / "SPY_daily.csv"
    payload = {
        "bars": [
            daily_bar(),
            daily_bar(
                t="2026-01-03T05:00:00Z",
                o="101.00",
                h="103.00",
                l="100.50",
                c="102.25",
                adjusted_close="101.75",
                v=234567,
            ),
        ],
        "next_page_token": None,
    }
    requests: list[object] = []

    result = fetcher.fetch_alpaca_daily_snapshot(
        symbol="spy",
        start_date="2026-01-02",
        end_date="2026-01-03",
        output_path=output_path,
        allow_network=True,
        env=VALID_ENV,
        repo_root=tmp_path,
        opener=opener_for(payload, requests),
    )
    lines = output_path.read_text(encoding="utf-8").splitlines()
    request = requests[0]
    query = urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)

    assert result.symbol == "SPY"
    assert result.feed == "iex"
    assert result.row_count == 2
    assert result.adjustment_policy == "unknown"
    assert result.return_basis == "price_return"
    assert result.adjusted_close_available is False
    assert result.adjusted_close_source == "close_price_fallback"
    assert result.file_sha256 == hashlib.sha256(output_path.read_bytes()).hexdigest()
    assert request.full_url.startswith("https://data.alpaca.markets/v2/stocks/SPY/bars?")
    assert query["feed"] == ["iex"]
    assert request.get_header("Apca-api-key-id") == RAW_KEY_ID
    assert request.get_header("Apca-api-secret-key") == RAW_SECRET_KEY
    assert lines == [
        CSV_HEADER,
        "2026-01-02,100.00,101.50,99.75,100.25,100.25,123456",
        "2026-01-03,101.00,103.00,100.50,102.25,101.75,234567",
    ]


def test_custom_feed_is_used_for_snapshot_request_and_result(tmp_path: Path) -> None:
    fetcher = load_fetcher()
    output_path = tmp_path / SNAPSHOT_DIR / "SPY_daily.csv"
    requests: list[object] = []

    result = fetcher.fetch_alpaca_daily_snapshot(
        symbol="SPY",
        start_date="2026-01-02",
        end_date="2026-01-02",
        output_path=output_path,
        allow_network=True,
        feed="sip",
        env=VALID_ENV,
        repo_root=tmp_path,
        opener=opener_for({"bars": [daily_bar()], "next_page_token": None}, requests),
    )
    query = urllib.parse.parse_qs(urllib.parse.urlparse(requests[0].full_url).query)

    assert result.feed == "sip"
    assert query["feed"] == ["sip"]


def test_missing_adjusted_close_is_reported_as_price_close_fallback(
    tmp_path: Path,
) -> None:
    fetcher = load_fetcher()
    output_path = tmp_path / SNAPSHOT_DIR / "SPY_daily.csv"

    result = fetcher.fetch_alpaca_daily_snapshot(
        symbol="SPY",
        start_date="2026-01-02",
        end_date="2026-01-02",
        output_path=output_path,
        allow_network=True,
        env=VALID_ENV,
        repo_root=tmp_path,
        opener=opener_for({"bars": [daily_bar()], "next_page_token": None}),
    )
    report = fetcher.render_fetch_report(result)

    assert output_path.read_text(encoding="utf-8").splitlines() == [
        CSV_HEADER,
        "2026-01-02,100.00,101.50,99.75,100.25,100.25,123456",
    ]
    assert "Adjustment policy: unknown" in report
    assert "Return basis: price_return" in report
    assert "Adjusted close available: false" in report
    assert "Adjusted close source: close_price_fallback" in report
    assert "total_return" not in report


def test_stdout_report_includes_feed_without_real_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fetcher = load_fetcher()
    output_path = tmp_path / SNAPSHOT_DIR / "SPY_daily.csv"
    requests: list[object] = []
    monkeypatch.setenv("ALPACA_API_KEY_ID", RAW_KEY_ID)
    monkeypatch.setenv("ALPACA_API_SECRET_KEY", RAW_SECRET_KEY)
    monkeypatch.setattr(
        fetcher.urllib.request,
        "urlopen",
        opener_for({"bars": [daily_bar()], "next_page_token": None}, requests),
    )

    exit_code = fetcher.main(
        (
            "--allow-network",
            "--allow-outside-data-dir",
            "--start",
            "2026-01-02",
            "--end",
            "2026-01-02",
            "--output",
            str(output_path),
            "--feed",
            "delayed_sip",
        )
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Feed: delayed_sip" in captured.out
    assert "Adjustment policy: unknown" in captured.out
    assert "Return basis: price_return" in captured.out
    assert "Adjusted close available: false" in captured.out
    assert "Adjusted close source: close_price_fallback" in captured.out
    assert RAW_KEY_ID not in captured.out
    assert RAW_SECRET_KEY not in captured.out
    assert captured.err == ""
    assert len(requests) == 1


def test_output_csv_header_is_exact(tmp_path: Path) -> None:
    fetcher = load_fetcher()
    output_path = tmp_path / "snapshot.csv"
    rows = fetcher.normalize_api_bar_response({"bars": [daily_bar()]})

    fetcher.write_csv_rows(output_path, rows)

    assert output_path.read_text(encoding="utf-8").splitlines()[0] == CSV_HEADER


def test_rows_are_written_sorted_by_returned_date_order(tmp_path: Path) -> None:
    fetcher = load_fetcher()
    output_path = tmp_path / "snapshot.csv"
    rows = fetcher.normalize_api_bar_response(
        {
            "bars": [
                daily_bar(t="2026-01-02T05:00:00Z"),
                daily_bar(t="2026-01-05T05:00:00Z"),
            ]
        }
    )

    fetcher.write_csv_rows(output_path, rows)
    dates = [line.split(",", maxsplit=1)[0] for line in output_path.read_text(encoding="utf-8").splitlines()[1:]]

    assert dates == ["2026-01-02", "2026-01-05"]


@pytest.mark.parametrize(
    "payload",
    (
        None,
        {},
        {"bars": {}},
        {"bars": []},
    ),
)
def test_malformed_response_is_rejected(payload: object) -> None:
    fetcher = load_fetcher()

    with pytest.raises(fetcher.SnapshotFetchError):
        fetcher.normalize_api_bar_response(payload)


@pytest.mark.parametrize("field_name", ("o", "h", "l", "c", "v"))
def test_missing_ohlcv_fields_are_rejected(field_name: str) -> None:
    fetcher = load_fetcher()
    bar = daily_bar()
    del bar[field_name]

    with pytest.raises(fetcher.SnapshotFetchError, match="missing required"):
        fetcher.normalize_api_bar_response({"bars": [bar]})


def test_duplicate_dates_are_rejected() -> None:
    fetcher = load_fetcher()

    with pytest.raises(fetcher.SnapshotFetchError, match="duplicate dates"):
        fetcher.normalize_api_bar_response(
            {
                "bars": [
                    daily_bar(t="2026-01-02T05:00:00Z"),
                    daily_bar(t="2026-01-02T05:00:00Z"),
                ]
            }
        )


def test_unordered_dates_are_rejected() -> None:
    fetcher = load_fetcher()

    with pytest.raises(fetcher.SnapshotFetchError, match="strictly increasing"):
        fetcher.normalize_api_bar_response(
            {
                "bars": [
                    daily_bar(t="2026-01-05T05:00:00Z"),
                    daily_bar(t="2026-01-02T05:00:00Z"),
                ]
            }
        )


@pytest.mark.parametrize(
    "field_name,bad_value",
    (
        ("o", "0"),
        ("h", "-1"),
        ("l", "NaN"),
        ("c", ""),
        ("adjusted_close", "0"),
    ),
)
def test_invalid_prices_are_rejected(field_name: str, bad_value: object) -> None:
    fetcher = load_fetcher()

    with pytest.raises(fetcher.SnapshotFetchError):
        fetcher.normalize_api_bar_response({"bars": [daily_bar(**{field_name: bad_value})]})


@pytest.mark.parametrize("bad_volume", (-1, "1.5", True))
def test_invalid_volume_is_rejected(bad_volume: object) -> None:
    fetcher = load_fetcher()

    with pytest.raises(fetcher.SnapshotFetchError, match="volume"):
        fetcher.normalize_api_bar_response({"bars": [daily_bar(v=bad_volume)]})


def test_sha256_helper_is_deterministic(tmp_path: Path) -> None:
    fetcher = load_fetcher()
    output_path = tmp_path / "snapshot.csv"
    output_path.write_text("date,close\n2026-01-02,100\n", encoding="utf-8")

    first = fetcher.compute_output_sha256(output_path)
    second = fetcher.compute_output_sha256(output_path)

    assert first == second
    assert first == hashlib.sha256(output_path.read_bytes()).hexdigest()


def test_no_raw_credentials_appear_in_errors(tmp_path: Path) -> None:
    fetcher = load_fetcher()

    def failing_opener(request: object, timeout: int) -> FakeResponse:
        raise RuntimeError(f"{RAW_KEY_ID} {RAW_SECRET_KEY}")

    with pytest.raises(fetcher.SnapshotFetchError) as exc_info:
        fetcher.fetch_alpaca_daily_snapshot(
            symbol="SPY",
            start_date="2026-01-02",
            end_date="2026-01-03",
            output_path=tmp_path / SNAPSHOT_DIR / "SPY_daily.csv",
            allow_network=True,
            env=VALID_ENV,
            repo_root=tmp_path,
            opener=failing_opener,
        )

    assert RAW_KEY_ID not in str(exc_info.value)
    assert RAW_SECRET_KEY not in str(exc_info.value)


def test_http_403_error_mentions_safe_feed_troubleshooting_without_credentials(
    tmp_path: Path,
) -> None:
    fetcher = load_fetcher()

    def failing_opener(request: object, timeout: int) -> FakeResponse:
        raise urllib.error.HTTPError(
            url="https://data.alpaca.markets/v2/stocks/SPY/bars",
            code=403,
            msg=f"Forbidden for {RAW_SECRET_KEY}",
            hdrs={},
            fp=None,
        )

    with pytest.raises(fetcher.SnapshotFetchError) as exc_info:
        fetcher.fetch_alpaca_daily_snapshot(
            symbol="SPY",
            start_date="2026-01-02",
            end_date="2026-01-03",
            output_path=tmp_path / SNAPSHOT_DIR / "SPY_daily.csv",
            allow_network=True,
            feed="sip",
            env=VALID_ENV,
            repo_root=tmp_path,
            opener=failing_opener,
        )

    message = str(exc_info.value)
    assert "HTTP status 403" in message
    assert "Credentials may be invalid or stale" in message
    assert "market-data permissions" in message
    assert "selected feed may not be available for the account" in message
    assert "Try --feed iex for basic access" in message
    assert RAW_KEY_ID not in message
    assert RAW_SECRET_KEY not in message


def test_fetcher_ast_guardrails_against_forbidden_imports_and_calls() -> None:
    import_violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]
    call_violations = [
        name
        for name in _call_names()
        if name in _FORBIDDEN_CALL_NAMES
        or any(name.endswith(suffix) for suffix in _FORBIDDEN_CALL_SUFFIXES)
    ]

    assert import_violations == []
    assert call_violations == []


def test_fetcher_ast_guardrails_against_trading_api_endpoints() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    assert '"https://data.alpaca.markets"' in source
    assert '"/v2/stocks/{symbol}/bars"' in source
    for forbidden_text in (
        "paper-api.alpaca.markets",
        "api.alpaca.markets/v2/account",
        "/v2/account",
        "/v2/orders",
        "/v2/positions",
        "submit_order",
        "alpaca-py",
        "alpaca_trade_api",
    ):
        assert forbidden_text not in source


def _tree() -> ast.AST:
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


def _call_names() -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""
