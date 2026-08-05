"""Safety coverage for the public perpetual data adapter.

This is the only component in the V5.98/V5.99 work that touches a network, and
it opened a third external destination in a repository previously limited to
two. Its safety properties are therefore asserted rather than trusted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution import perp_funding_refresh_adapter as subject


def _config(tmp_path: Path, **overrides):
    base = {
        "symbol": "BTC-PERPETUAL",
        "series": "funding",
        "output_root": tmp_path,
    }
    base.update(overrides)
    return subject.PerpFundingRefreshConfig(**base)


def _exploding_http_get(*args, **kwargs):
    raise AssertionError("the network must not be touched")


# --- network boundary ------------------------------------------------------


def test_dry_run_performs_zero_network_calls(tmp_path: Path) -> None:
    receipt = subject.run_perp_funding_refresh(
        _config(tmp_path), http_get=_exploding_http_get
    )

    assert receipt["network_access_attempted"] is False
    assert receipt["refresh_state"] == "dry_run_request_plan_built"
    assert receipt["http_outcome_category"] == "not_attempted"
    assert receipt["raw_response_path"] == ""


def test_every_request_is_get_against_one_allowlisted_host(tmp_path: Path) -> None:
    for series in ("funding", "perp_kline", "spot_kline"):
        request = subject.build_perp_request(_config(tmp_path, series=series))
        assert request["method"] == "GET"
        assert request["scheme"] == "https"
        assert request["destination_host"] == subject.DESTINATION_HOST
        assert request["destination_host"] in request["destination_allowlist"]
        assert request["destination_allowlist_match"] is True
        assert request["url"].startswith(f"https://{subject.DESTINATION_HOST}/")


def test_https_get_refuses_a_host_outside_the_allowlist() -> None:
    with pytest.raises(ValidationError, match="not allowlisted"):
        subject._https_get("evil.example.com", "/api/v2/public/anything")


# --- credentials -----------------------------------------------------------


def test_no_request_carries_credentials(tmp_path: Path) -> None:
    for series in ("funding", "perp_kline", "spot_kline"):
        request = subject.build_perp_request(_config(tmp_path, series=series))
        assert request["credentials_used"] is False
        assert request["authenticated"] is False
        assert request["headers"] == {}
        assert "key" not in request["url"].lower()
        assert "token" not in request["url"].lower()
        assert "sign" not in request["url"].lower()


def test_module_has_no_credential_reading_code_path() -> None:
    """The strongest available guarantee: the capability is simply absent.

    Parsed rather than string-matched — an earlier version of this test scanned
    raw source and tripped over the word "dotenv" in the module docstring,
    which proves nothing about behaviour.
    """

    import ast

    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))

    imported: set[str] = set()
    called: set[str] = set()
    attributes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Attribute):
            attributes.add(node.attr)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.add(node.func.id)

    # No credential-bearing library is imported at all.
    for module in ("os", "dotenv", "keyring", "subprocess"):
        assert module not in imported, f"credential-capable import: {module}"
    # No environment or credential accessor is invoked.
    for accessor in ("getenv", "environ", "get_password", "load_dotenv"):
        assert accessor not in attributes, f"credential accessor used: {accessor}"
        assert accessor not in called, f"credential accessor called: {accessor}"


def test_receipt_records_zero_authority(tmp_path: Path) -> None:
    receipt = subject.run_perp_funding_refresh(
        _config(tmp_path), http_get=_exploding_http_get
    )

    for field in (
        "credential_access_attempted",
        "credential_values_exposed",
        "authenticated_request",
        "broker_access_attempted",
        "broker_mutation_attempted",
        "paper_submit_attempted",
        "live_authorized",
        "live_trading_performed",
    ):
        assert receipt[field] is False, field
    assert receipt["network_method_allowlist"] == ["GET"]
    assert receipt["network_destination_allowlist_enforced"] is True


# --- input validation ------------------------------------------------------


def test_unapproved_symbol_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="symbol is not approved"):
        _config(tmp_path, symbol="DOGE-PERPETUAL")


def test_unapproved_series_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="series is not approved"):
        _config(tmp_path, series="orderbook")


def test_live_fetch_requires_explicit_authorization(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="requires explicit authorization"):
        _config(tmp_path, mode="live_market_data_fetch")


def test_authorization_flag_alone_does_not_enable_a_live_fetch(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="requires live fetch mode"):
        _config(tmp_path, live_market_data_fetch_authorized=True)


def test_limit_is_bounded(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match=r"limit must lie"):
        _config(tmp_path, limit=0)
    with pytest.raises(ValidationError, match=r"limit must lie"):
        _config(tmp_path, limit=5000)


# --- response handling -----------------------------------------------------


def test_json_rpc_list_envelope_is_unwrapped(tmp_path: Path) -> None:
    payload = json.dumps(
        {"jsonrpc": "2.0", "result": [{"timestamp": 1, "interest_1h": 0.0}]}
    ).encode()

    receipt = subject.run_perp_funding_refresh(
        _config(
            tmp_path,
            mode="live_market_data_fetch",
            live_market_data_fetch_authorized=True,
        ),
        http_get=lambda *a, **k: payload,
    )

    assert receipt["row_count"] == 1
    assert receipt["refresh_state"] == "accepted_public_series_refresh"
    assert receipt["raw_response_sha256"]
    assert Path(receipt["raw_response_path"]).is_file()


def test_chart_envelope_of_parallel_arrays_is_unwrapped(tmp_path: Path) -> None:
    payload = json.dumps(
        {"result": {"status": "ok", "ticks": [1, 2, 3], "close": [10.0, 11.0, 12.0]}}
    ).encode()

    receipt = subject.run_perp_funding_refresh(
        _config(
            tmp_path,
            series="perp_kline",
            mode="live_market_data_fetch",
            live_market_data_fetch_authorized=True,
        ),
        http_get=lambda *a, **k: payload,
    )

    assert receipt["row_count"] == 3


def test_unrecognised_response_shape_blocks(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="unrecognised public series"):
        subject.run_perp_funding_refresh(
            _config(
                tmp_path,
                mode="live_market_data_fetch",
                live_market_data_fetch_authorized=True,
            ),
            http_get=lambda *a, **k: b'{"result": 42}',
        )
