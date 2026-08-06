"""Coverage for the V6.05 funding carry collector.

Network is always injected, so the suite exercises the real panel assembly,
blocking and writing logic without touching a venue.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution import funding_carry_collector as subject

_HOUR_MS = 60 * 60 * 1000
_INTERVAL_MS = 8 * _HOUR_MS
_BASE = int(datetime(2026, 1, 1, 0, 0, tzinfo=UTC).timestamp() * 1000)


def _funding_rows(intervals: int) -> list[dict[str, object]]:
    rows = []
    # Hourly observations covering every hour the intervals need, inclusive.
    for hour in range(-8, intervals * 8 + 1):
        rows.append(
            {
                "timestamp": _BASE + hour * _HOUR_MS,
                "interest_1h": 0.0001,
                "index_price": 100.0,
            }
        )
    return rows


def _kline(intervals: int) -> dict[str, object]:
    ticks, closes = [], []
    for hour in range(-9, intervals * 8 + 1):
        ticks.append(_BASE + hour * _HOUR_MS)
        closes.append(100.0)
    return {"ticks": ticks, "close": closes}


def test_panel_admits_only_complete_eight_hour_windows() -> None:
    panel = subject.assemble_panel(_funding_rows(3), _closes(3))

    assert panel, "no intervals were admitted"
    for stamp in panel:
        assert stamp % _INTERVAL_MS == 0
        # Eight hourly rates of 0.0001 each.
        assert panel[stamp]["funding"] == pytest.approx(0.0008)
        assert panel[stamp]["index"] == pytest.approx(100.0)
        assert panel[stamp]["perp"] == pytest.approx(100.0)


def _closes(intervals: int) -> dict[int, float]:
    return {
        int(tick): float(close)
        for tick, close in zip(
            _kline(intervals)["ticks"], _kline(intervals)["close"], strict=False
        )
    }


def test_an_incomplete_funding_window_is_dropped_not_partially_summed() -> None:
    rows = [row for row in _funding_rows(2) if row["timestamp"] != _BASE - 3 * _HOUR_MS]

    panel = subject.assemble_panel(rows, _closes(2))

    # The interval ending at _BASE needed that hour, so it is absent entirely.
    assert _BASE not in panel


def test_the_perpetual_mark_uses_the_v6_00_tick_offset() -> None:
    """Deribit ticks are bar open times; the close at T is the price at T+1h."""

    closes = _closes(2)
    # Only the offset mark is available for the interval ending at _BASE.
    only_offset = {_BASE - _HOUR_MS: closes[_BASE - _HOUR_MS]}

    panel = subject.assemble_panel(_funding_rows(2), only_offset)

    assert _BASE in panel
    assert panel[_BASE]["perp"] == pytest.approx(closes[_BASE - _HOUR_MS])


def test_a_missing_mark_drops_the_interval() -> None:
    panel = subject.assemble_panel(_funding_rows(2), {})

    assert panel == {}


def test_malformed_funding_rows_are_skipped_rather_than_crashing() -> None:
    rows = [*_funding_rows(2), {"timestamp": "bad", "interest_1h": None}]

    panel = subject.assemble_panel(rows, _closes(2))

    assert panel


# --- configuration ---------------------------------------------------------


def test_live_fetch_requires_authorization(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="requires explicit authorization"):
        subject.FundingCarryCollectorConfig(
            output_root=tmp_path, canonical_csv=tmp_path / "c.csv",
            mode="live_market_data_fetch",
        )


def test_authorization_without_live_mode_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="authorization flag requires"):
        subject.FundingCarryCollectorConfig(
            output_root=tmp_path, canonical_csv=tmp_path / "c.csv",
            live_market_data_fetch_authorized=True,
        )


def test_dry_run_performs_zero_network_access(tmp_path: Path) -> None:
    def explode(*args: object, **kwargs: object) -> bytes:
        raise AssertionError("the network must not be touched")

    receipt = subject.run_funding_carry_collector(
        subject.FundingCarryCollectorConfig(
            output_root=tmp_path, canonical_csv=tmp_path / "c.csv"
        ),
        http_get=explode,
    )

    assert receipt["network_access_attempted"] is False
    assert receipt["state"] == "dry_run_plan_built"
    assert receipt["planned_requests"] == 6


# --- collection ------------------------------------------------------------


def _fetcher(intervals: int = 6):
    funding = json.dumps({"result": _funding_rows(intervals)}).encode()
    kline = json.dumps({"result": _kline(intervals)}).encode()

    def fetch(host: str, path: str, *args: object, **kwargs: object) -> bytes:
        return funding if "funding" in path else kline

    return fetch


def test_collection_writes_all_four_canonical_series(tmp_path: Path) -> None:
    csv_path = tmp_path / "carry.csv"

    receipt = subject.run_funding_carry_collector(
        subject.FundingCarryCollectorConfig(
            output_root=tmp_path, canonical_csv=csv_path,
            mode="live_market_data_fetch", live_market_data_fetch_authorized=True,
        ),
        http_get=_fetcher(),
        now=datetime(2026, 1, 3, tzinfo=UTC),
    )

    assert receipt["state"] == "collected"
    assert receipt["canonical"]["symbols"] == [
        "BTCCARRY", "ETHCARRY", "SOLCARRY", "USDCASH"
    ]
    assert csv_path.exists()


def test_the_collector_never_touches_the_shadow_ledger(tmp_path: Path) -> None:
    """Collection and observation are separate acts, deliberately."""

    receipt = subject.run_funding_carry_collector(
        subject.FundingCarryCollectorConfig(
            output_root=tmp_path, canonical_csv=tmp_path / "c.csv",
            mode="live_market_data_fetch", live_market_data_fetch_authorized=True,
        ),
        http_get=_fetcher(),
        now=datetime(2026, 1, 3, tzinfo=UTC),
    )

    assert receipt["shadow_ledger_appended"] is False
    assert not list(tmp_path.glob("**/observations.jsonl"))


def test_a_venue_returning_nothing_blocks_rather_than_writing(tmp_path: Path) -> None:
    def empty(host: str, path: str, *args: object, **kwargs: object) -> bytes:
        return json.dumps({"result": [] if "funding" in path else {}}).encode()

    receipt = subject.run_funding_carry_collector(
        subject.FundingCarryCollectorConfig(
            output_root=tmp_path, canonical_csv=tmp_path / "c.csv",
            mode="live_market_data_fetch", live_market_data_fetch_authorized=True,
        ),
        http_get=empty,
        now=datetime(2026, 1, 3, tzinfo=UTC),
    )

    assert receipt["state"] == "blocked_no_usable_series"
    assert not (tmp_path / "c.csv").exists()


def test_only_sessions_present_for_every_symbol_are_written(tmp_path: Path) -> None:
    """A session missing one leg would give the shadow a lopsided book."""

    full = _fetcher(6)
    short = _fetcher(3)

    def partial(host: str, path: str, *args: object, **kwargs: object) -> bytes:
        # SOL is fetched with a shorter history than BTC and ETH.
        instrument = kwargs.get("instrument") or path
        return short(host, path) if "SOL" in str(instrument) else full(host, path)

    receipt = subject.run_funding_carry_collector(
        subject.FundingCarryCollectorConfig(
            output_root=tmp_path, canonical_csv=tmp_path / "c.csv",
            mode="live_market_data_fetch", live_market_data_fetch_authorized=True,
        ),
        http_get=partial,
        now=datetime(2026, 1, 3, tzinfo=UTC),
    )

    assert receipt["state"] == "collected"
    written = receipt["canonical"]["row_count"]
    symbols = receipt["canonical"]["symbols"]
    assert written % len(symbols) == 0, "each session must carry every symbol"


# --- the signal-to-noise precondition, mandated by the preregistration -----


def _desynchronised_kline(intervals: int) -> dict[str, object]:
    """Perpetual marks that wander independently of the index.

    This is the V5.99 shape: the two legs are not stamped at the same instant,
    so per-interval basis dwarfs the funding being collected.
    """

    ticks, closes = [], []
    for hour in range(-9, intervals * 8 + 1):
        ticks.append(_BASE + hour * _HOUR_MS)
        # Swings on the eight-hour boundary the panel actually samples, so the
        # mark genuinely disagrees with the index at every admitted interval.
        closes.append(100.0 + (5.0 if ((hour + 9) // 8) % 2 else -5.0))
    return {"ticks": ticks, "close": closes}


def test_a_desynchronised_leg_blocks_instead_of_being_written(tmp_path: Path) -> None:
    """V5.99 produced a confident -6.3% from exactly this data."""

    funding = json.dumps({"result": _funding_rows(6)}).encode()
    good = json.dumps({"result": _kline(6)}).encode()
    bad = json.dumps({"result": _desynchronised_kline(6)}).encode()

    def fetch(host: str, path: str, *args: object, **kwargs: object) -> bytes:
        if "funding" in path:
            return funding
        return bad if "SOL" in str(kwargs.get("instrument", path)) else good

    receipt = subject.run_funding_carry_collector(
        subject.FundingCarryCollectorConfig(
            output_root=tmp_path, canonical_csv=tmp_path / "c.csv",
            mode="live_market_data_fetch", live_market_data_fetch_authorized=True,
        ),
        http_get=fetch,
        now=datetime(2026, 1, 3, tzinfo=UTC),
    )

    assert receipt["state"] in (
        "blocked_incomplete_universe", "blocked_no_usable_series"
    )
    assert not (tmp_path / "c.csv").exists()


def test_a_missing_leg_blocks_the_whole_collection(tmp_path: Path) -> None:
    """A two-leg book is a different hypothesis from the registered three-leg one."""

    funding = json.dumps({"result": _funding_rows(6)}).encode()
    good = json.dumps({"result": _kline(6)}).encode()
    empty = json.dumps({"result": {}}).encode()

    def fetch(host: str, path: str, *args: object, **kwargs: object) -> bytes:
        if "funding" in path:
            return funding
        return empty if "ETH" in str(kwargs.get("instrument", path)) else good

    receipt = subject.run_funding_carry_collector(
        subject.FundingCarryCollectorConfig(
            output_root=tmp_path, canonical_csv=tmp_path / "c.csv",
            mode="live_market_data_fetch", live_market_data_fetch_authorized=True,
        ),
        http_get=fetch,
        now=datetime(2026, 1, 3, tzinfo=UTC),
    )

    assert receipt["state"] == "blocked_incomplete_universe"
    assert "ETHCARRY" in receipt["missing_legs"]
    assert not (tmp_path / "c.csv").exists()


def test_a_clean_collection_records_its_signal_to_noise(tmp_path: Path) -> None:
    receipt = subject.run_funding_carry_collector(
        subject.FundingCarryCollectorConfig(
            output_root=tmp_path, canonical_csv=tmp_path / "c.csv",
            mode="live_market_data_fetch", live_market_data_fetch_authorized=True,
        ),
        http_get=_fetcher(),
        now=datetime(2026, 1, 3, tzinfo=UTC),
    )

    assert receipt["state"] == "collected"
    assert set(receipt["signal_to_noise"]) == {"BTCCARRY", "ETHCARRY", "SOLCARRY"}
    assert all(
        report["sufficient"] is True
        for report in receipt["signal_to_noise"].values()
    )


def test_collector_has_no_credential_reading_code_path() -> None:
    import ast

    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    attributes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Attribute):
            attributes.add(node.attr)

    for module in ("os", "dotenv", "keyring", "subprocess"):
        assert module not in imported, f"credential-capable import: {module}"
    for accessor in ("getenv", "environ", "get_password", "load_dotenv"):
        assert accessor not in attributes, f"credential accessor used: {accessor}"


def test_collector_opens_no_socket_of_its_own() -> None:
    import ast

    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }

    for module in ("http", "socket", "urllib", "requests", "httpx", "ssl"):
        assert module not in imported, f"collector opens its own socket via {module}"
