from __future__ import annotations

import ast
import json
from pathlib import Path

import algotrader.cli as cli_module
import pytest
from algotrader.execution.etf_sma_authorized_offline_cycle_preview import (
    EtfSmaAuthorizedOfflineCyclePreviewConfig,
    build_etf_sma_authorized_offline_cycle_preview,
    render_etf_sma_authorized_offline_cycle_preview_json,
    write_etf_sma_authorized_offline_cycle_preview_jsonl,
)


MODULE_PATH = Path(
    "src/algotrader/execution/etf_sma_authorized_offline_cycle_preview.py"
)
_COMMAND = "etf-sma-authorized-offline-cycle-preview"
_SUCCESS_STATUS = "offline_cycle_preview_computed"
_BLOCKED_POSTURE_STATUS = "blocked_authorized_posture_required"
_BLOCKED_STATE_STATUS = "blocked_offline_paper_state_required"
_BLOCKED_OPEN_ORDER_STATUS = "blocked_open_order_present"
_BLOCKED_UNEXPECTED_POSITION_STATUS = "blocked_unexpected_position"
_POSTURE_SUCCESS_STATUS = "authorized_adjusted_close_sma_posture_computed"
_INPUT_REPLAY_STATUS = "authorized_adjusted_baseline_backtest_replayed"
_PREFERRED_BASELINE = "adjusted_close_matched_window"
_PREFERRED_BASIS = "adjusted_close_price_return"
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "os",
    "requests",
    "socket",
    "urllib",
)
_FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
    "delete",
    "getenv",
    "liquidate",
    "load_config",
    "replace_order",
    "request",
    "socket",
    "socket.socket",
    "submit_order",
    "submit_order_request",
    "urlopen",
}


@pytest.mark.parametrize(
    ("sma_posture", "spy_position_qty", "expected_decision"),
    [
        ("risk_on", "", "buy_preview"),
        ("risk_on", "0.25", "hold/noop"),
        ("risk_off", "0.25", "sell_preview"),
        ("risk_off", "", "hold/noop"),
    ],
    ids=(
        "risk_on_flat_buy_preview",
        "risk_on_position_hold",
        "risk_off_position_sell_preview",
        "risk_off_flat_hold",
    ),
)
def test_valid_m430_and_offline_state_compute_preview_decisions(
    tmp_path: Path,
    sma_posture: str,
    spy_position_qty: str,
    expected_decision: str,
) -> None:
    posture_path = _write_jsonl(tmp_path / "m430.jsonl", _m430_payload(sma_posture))
    state_path = _write_jsonl(
        tmp_path / "state.jsonl",
        _offline_state(spy_position_qty=spy_position_qty),
    )

    payload = build_etf_sma_authorized_offline_cycle_preview(
        _config(posture_path, state_path)
    )

    assert payload["milestone"] == "M431"
    assert payload["symbol"] == "SPY"
    assert payload["cycle_preview_status"] == _SUCCESS_STATUS
    assert payload["input_posture_status"] == _POSTURE_SUCCESS_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["posture_source_milestone"] == "M430"
    assert payload["replay_source_milestone"] == "M429"
    assert payload["snapshot_source_milestone"] == "M428"
    assert payload["metrics_source_milestone"] == "M427"
    assert payload["summary_source_milestone"] == "M426"
    assert payload["stub_source_milestone"] == "M425"
    assert payload["authorization_source_milestone"] == "M424"
    assert payload["guard_source_milestone"] == "M423"
    assert payload["baseline_source_milestone"] == "M422"
    assert payload["source_evidence_milestone"] == "M421"
    assert payload["strategy_family"] == "etf_sma_50_200"
    assert payload["data_basis"] == _PREFERRED_BASIS
    assert payload["as_of_date"] == "2026-06-05"
    assert payload["latest_available_bar_date"] == "2026-06-05"
    assert payload["sma50"] == ("713.5118" if sma_posture == "risk_on" else "100")
    assert payload["sma200"] == ("681.5535044594288505" if sma_posture == "risk_on" else "200")
    assert payload["sma_posture"] == sma_posture
    assert payload["sufficient_history"] is True
    assert payload["broker_state_loaded"] is False
    assert payload["offline_paper_state_loaded"] is True
    assert payload["offline_paper_state_source"] == str(state_path)
    assert payload["open_order_count"] == 0
    assert payload["open_spy_order_count"] == 0
    assert payload["spy_position_present"] is bool(spy_position_qty)
    assert payload["spy_position_qty"] == spy_position_qty
    assert payload["unexpected_position_symbols"] == []
    assert payload["cycle_decision"] == expected_decision
    assert payload["paper_preview_computed"] is True
    assert payload["order_quantity_computed"] is False
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    assert payload["blockers"] == []
    _assert_never_mutates(payload)


def test_valid_m430_with_open_spy_order_blocks_preview(tmp_path: Path) -> None:
    posture_path = _write_jsonl(tmp_path / "m430.jsonl", _m430_payload("risk_on"))
    state_path = _write_jsonl(
        tmp_path / "state.jsonl",
        _offline_state(open_spy_order_count=1, spy_position_qty="0.033172072"),
    )

    payload = build_etf_sma_authorized_offline_cycle_preview(
        _config(posture_path, state_path)
    )

    assert payload["cycle_preview_status"] == _BLOCKED_OPEN_ORDER_STATUS
    assert payload["cycle_decision"] == "blocked/open_order_present"
    assert payload["paper_preview_computed"] is False
    assert payload["offline_paper_state_loaded"] is True
    assert payload["open_order_count"] == 1
    assert payload["open_spy_order_count"] == 1
    assert "open_spy_order_present" in payload["blockers"]
    _assert_never_mutates(payload)


def test_valid_m430_with_unexpected_non_spy_position_blocks_preview(
    tmp_path: Path,
) -> None:
    posture_path = _write_jsonl(tmp_path / "m430.jsonl", _m430_payload("risk_on"))
    state_path = _write_jsonl(
        tmp_path / "state.jsonl",
        _offline_state(non_spy_positions=[{"symbol": "QQQ", "qty": "1"}]),
    )

    payload = build_etf_sma_authorized_offline_cycle_preview(
        _config(posture_path, state_path)
    )

    assert payload["cycle_preview_status"] == _BLOCKED_UNEXPECTED_POSITION_STATUS
    assert payload["cycle_decision"] == "blocked/unexpected_position"
    assert payload["paper_preview_computed"] is False
    assert payload["offline_paper_state_loaded"] is True
    assert payload["unexpected_position_symbols"] == ["QQQ"]
    assert payload["blockers"] == ["unexpected_position_symbols_present"]
    _assert_never_mutates(payload)


def test_missing_offline_paper_state_blocks_after_valid_m430(
    tmp_path: Path,
) -> None:
    posture_path = _write_jsonl(tmp_path / "m430.jsonl", _m430_payload("risk_on"))
    missing_state_path = tmp_path / "missing_state.jsonl"

    payload = build_etf_sma_authorized_offline_cycle_preview(
        _config(posture_path, missing_state_path)
    )

    assert payload["cycle_preview_status"] == _BLOCKED_STATE_STATUS
    assert payload["cycle_decision"] == "blocked/offline_paper_state_required"
    assert payload["downstream_comparison_authorized"] is True
    assert payload["offline_paper_state_loaded"] is False
    assert payload["paper_preview_computed"] is False
    assert payload["blockers"] == ["offline_paper_state_artifact_not_found"]
    _assert_never_mutates(payload)


@pytest.mark.parametrize(
    ("writer", "expected_blocker"),
    [
        (lambda path: None, "input_posture_artifact_not_found"),
        (lambda path: path.write_text("", encoding="utf-8"), "input_posture_artifact_empty"),
        (
            lambda path: path.write_text("{not-json}\n", encoding="utf-8"),
            "input_posture_artifact_invalid_json_line_1",
        ),
        (
            lambda path: path.write_text(
                json.dumps(_m430_payload("risk_on"), sort_keys=True)
                + "\n"
                + json.dumps(_m430_payload("risk_on"), sort_keys=True)
                + "\n",
                encoding="utf-8",
            ),
            "ambiguous_input_posture_artifact_record_count",
        ),
    ],
    ids=("missing", "empty", "malformed", "multi_record"),
)
def test_missing_empty_malformed_or_multi_record_m430_blocks(
    tmp_path: Path,
    writer,
    expected_blocker: str,
) -> None:
    posture_path = tmp_path / "m430.jsonl"
    writer(posture_path)
    state_path = _write_jsonl(tmp_path / "state.jsonl", _offline_state())

    payload = build_etf_sma_authorized_offline_cycle_preview(
        _config(posture_path, state_path)
    )

    assert payload["cycle_preview_status"] == _BLOCKED_POSTURE_STATUS
    assert payload["cycle_decision"] == "blocked/authorized_posture_required"
    assert payload["downstream_comparison_authorized"] is False
    assert payload["offline_paper_state_loaded"] is False
    assert payload["paper_preview_computed"] is False
    assert expected_blocker in payload["blockers"]
    _assert_never_mutates(payload)


@pytest.mark.parametrize(
    ("mutator", "expected_blocker"),
    [
        (
            lambda payload: payload.update({"downstream_comparison_authorized": False}),
            "input_posture_downstream_comparison_authorized_not_true",
        ),
        (
            lambda payload: payload.update({"submitted": True}),
            "input_posture_submitted_not_false",
        ),
    ],
    ids=("unauthorized", "safety_dirty"),
)
def test_unauthorized_or_safety_dirty_m430_blocks(
    tmp_path: Path,
    mutator,
    expected_blocker: str,
) -> None:
    posture = _m430_payload("risk_on")
    mutator(posture)
    posture_path = _write_jsonl(tmp_path / "m430.jsonl", posture)
    state_path = _write_jsonl(tmp_path / "state.jsonl", _offline_state())

    payload = build_etf_sma_authorized_offline_cycle_preview(
        _config(posture_path, state_path)
    )

    assert payload["cycle_preview_status"] == _BLOCKED_POSTURE_STATUS
    assert payload["cycle_decision"] == "blocked/authorized_posture_required"
    assert expected_blocker in payload["blockers"]
    assert payload["downstream_comparison_authorized"] is False
    assert payload["offline_paper_state_loaded"] is False
    _assert_never_mutates(payload)


def test_insufficient_history_m430_posture_blocks(tmp_path: Path) -> None:
    posture = _m430_payload("risk_on")
    posture.update(
        {
            "posture_snapshot_status": "insufficient_adjusted_history",
            "sufficient_history": False,
            "sma_posture": "insufficient_history",
            "sma200": None,
        }
    )
    posture_path = _write_jsonl(tmp_path / "m430.jsonl", posture)
    state_path = _write_jsonl(tmp_path / "state.jsonl", _offline_state())

    payload = build_etf_sma_authorized_offline_cycle_preview(
        _config(posture_path, state_path)
    )

    assert payload["cycle_preview_status"] == _BLOCKED_POSTURE_STATUS
    assert "input_posture_unexpected_posture_snapshot_status" in payload["blockers"]
    assert "input_posture_sufficient_history_not_true" in payload["blockers"]
    assert "input_posture_unexpected_sma_posture" in payload["blockers"]
    _assert_never_mutates(payload)


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "active_preferred_baseline",
            "raw_close_matched_window",
            "input_posture_unexpected_active_preferred_baseline",
        ),
        (
            "active_preferred_basis",
            "raw_close_price_return",
            "input_posture_unexpected_active_preferred_basis",
        ),
        (
            "comparison_basis",
            "full_history",
            "input_posture_unexpected_comparison_basis",
        ),
    ],
)
def test_baseline_basis_or_comparison_basis_drift_blocks(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    payload = _build_with_posture_override(tmp_path, field_name, value)

    assert payload["cycle_preview_status"] == _BLOCKED_POSTURE_STATUS
    assert expected_blocker in payload["blockers"]
    _assert_never_mutates(payload)


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "strategy_family",
            "other_strategy",
            "input_posture_unexpected_strategy_family",
        ),
        (
            "data_basis",
            "raw_close_price_return",
            "input_posture_unexpected_data_basis",
        ),
    ],
)
def test_strategy_family_or_data_basis_drift_blocks(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    payload = _build_with_posture_override(tmp_path, field_name, value)

    assert payload["cycle_preview_status"] == _BLOCKED_POSTURE_STATUS
    assert expected_blocker in payload["blockers"]
    _assert_never_mutates(payload)


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "trade_recommendation",
            "buy",
            "input_posture_unexpected_trade_recommendation",
        ),
        ("profit_claim", "positive", "input_posture_unexpected_profit_claim"),
    ],
)
def test_trade_recommendation_or_profit_claim_drift_blocks(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    payload = _build_with_posture_override(tmp_path, field_name, value)

    assert payload["cycle_preview_status"] == _BLOCKED_POSTURE_STATUS
    assert expected_blocker in payload["blockers"]
    _assert_never_mutates(payload)


def test_output_remains_deterministic(tmp_path: Path) -> None:
    posture_path = _write_jsonl(tmp_path / "m430.jsonl", _m430_payload("risk_on"))
    state_path = _write_jsonl(tmp_path / "state.jsonl", _offline_state())
    config = _config(posture_path, state_path)

    first = build_etf_sma_authorized_offline_cycle_preview(config)
    second = build_etf_sma_authorized_offline_cycle_preview(config)

    assert first == second
    assert render_etf_sma_authorized_offline_cycle_preview_json(first) == (
        render_etf_sma_authorized_offline_cycle_preview_json(second)
    )


def test_writes_exactly_one_jsonl_record(tmp_path: Path) -> None:
    posture_path = _write_jsonl(tmp_path / "m430.jsonl", _m430_payload("risk_on"))
    state_path = _write_jsonl(tmp_path / "state.jsonl", _offline_state())
    run_log = tmp_path / "m431.jsonl"
    payload = build_etf_sma_authorized_offline_cycle_preview(
        _config(posture_path, state_path)
    )

    result = write_etf_sma_authorized_offline_cycle_preview_jsonl(payload, run_log)
    records = _read_jsonl(run_log)

    assert result.record_count == 1
    assert result.submitted is False
    assert result.mutated is False
    assert result.broker_action_performed is False
    assert records == [payload]


def test_cli_writes_preview_before_runtime_config_loading(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    posture_path = _write_jsonl(tmp_path / "m430.jsonl", _m430_payload("risk_on"))
    state_path = _write_jsonl(tmp_path / "state.jsonl", _offline_state())
    run_log = tmp_path / "m431_cli.jsonl"

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M431 offline command must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("M431 offline command must not build a broker")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)

    assert cli_module.main(
        [
            _COMMAND,
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m431_cli",
            "--run-log",
            str(run_log),
            "--posture-path",
            str(posture_path),
            "--offline-paper-state-path",
            str(state_path),
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["run_id"] == "unit_m431_cli"
    assert payload["cycle_decision"] == "buy_preview"
    _assert_never_mutates(payload)


def test_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references(MODULE_PATH)

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names(MODULE_PATH).isdisjoint(_FORBIDDEN_CALL_NAMES)


def _build_with_posture_override(
    tmp_path: Path,
    field_name: str,
    value: object,
) -> dict[str, object]:
    posture = _m430_payload("risk_on")
    posture[field_name] = value
    posture_path = _write_jsonl(tmp_path / "m430.jsonl", posture)
    state_path = _write_jsonl(tmp_path / "state.jsonl", _offline_state())
    return build_etf_sma_authorized_offline_cycle_preview(
        _config(posture_path, state_path)
    )


def _config(
    posture_path: Path,
    offline_paper_state_path: Path,
) -> EtfSmaAuthorizedOfflineCyclePreviewConfig:
    return EtfSmaAuthorizedOfflineCyclePreviewConfig(
        run_id="unit_m431",
        symbol="SPY",
        posture_path=posture_path,
        offline_paper_state_path=offline_paper_state_path,
    )


def _m430_payload(sma_posture: str) -> dict[str, object]:
    risk_on = sma_posture == "risk_on"
    payload: dict[str, object] = {
        "active_preferred_baseline": _PREFERRED_BASELINE,
        "active_preferred_basis": _PREFERRED_BASIS,
        "adjusted_close": "737.55",
        "adjusted_close_input_helper": "load_local_daily_bars_csv",
        "adjusted_close_input_source": "m429_daily_bars_csv",
        "as_of_date": "2026-06-05",
        "authorization_source_milestone": "M424",
        "baseline_source_milestone": "M422",
        "blockers": [],
        "broker_action_performed": False,
        "broker_state_loaded": False,
        "command": "etf-sma-authorized-adjusted-close-posture-snapshot",
        "comparison_basis": "matched_window",
        "credential_access_attempted": False,
        "data_basis": _PREFERRED_BASIS,
        "downstream_comparison_authorized": True,
        "guard_source_milestone": "M423",
        "input_replay_status": _INPUT_REPLAY_STATUS,
        "latest_available_bar_date": "2026-06-05",
        "live_authorized": False,
        "metrics_source_milestone": "M427",
        "milestone": "M430",
        "mutated": False,
        "network_access_attempted": False,
        "new_market_data_loaded": False,
        "order_decision_computed": False,
        "paper_preview_computed": False,
        "posture_computed": True,
        "posture_snapshot_status": _POSTURE_SUCCESS_STATUS,
        "profit_claim": "none",
        "record_type": "etf_sma_authorized_adjusted_close_posture_snapshot",
        "replay_source_milestone": "M429",
        "run_id": "unit_m430",
        "schema_version": "1",
        "sma200": "681.5535044594288505" if risk_on else "200",
        "sma50": "713.5118" if risk_on else "100",
        "sma_posture": sma_posture,
        "snapshot_source_milestone": "M428",
        "source_evidence_milestone": "M421",
        "strategy_family": "etf_sma_50_200",
        "stub_source_milestone": "M425",
        "submitted": False,
        "sufficient_history": True,
        "summary_source_milestone": "M426",
        "symbol": "SPY",
        "trade_recommendation": "none",
    }
    return payload


def _offline_state(
    *,
    open_spy_order_count: int = 0,
    spy_position_qty: str = "",
    non_spy_positions: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    unexpected_positions = non_spy_positions or []
    open_order_symbols = ["SPY"] * open_spy_order_count
    payload: dict[str, object] = {
        "record_type": "paper_lab_state_rollup",
        "command": "paper-lab-state-rollup",
        "run_id": "unit_state",
        "symbol": "SPY",
        "state_rollup_status": (
            "blocked" if open_spy_order_count else "review_only"
        ),
        "open_order_count": open_spy_order_count,
        "open_order_present": open_spy_order_count > 0,
        "open_spy_order_count": open_spy_order_count,
        "open_spy_order_present": open_spy_order_count > 0,
        "open_order_symbols": open_order_symbols,
        "spy_position_qty": spy_position_qty,
        "spy_position_present": bool(spy_position_qty),
        "non_spy_positions": unexpected_positions,
        "non_spy_position_present": bool(unexpected_positions),
        "blockers": (
            ["m376_order_nonterminal", "open_order_present"]
            if open_spy_order_count
            else []
        ),
        "profit_claim": "none",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "preview_order_authorized": False,
    }
    return payload


def _write_jsonl(path: Path, *records: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _assert_never_mutates(payload: dict[str, object]) -> None:
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False
    assert payload["broker_state_loaded"] is False
    assert payload["order_quantity_computed"] is False
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"


def _import_references(path: Path) -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            prefix = "." * node.level
            imports.add(f"{prefix}{node.module}")
    return imports


def _call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _matches_forbidden_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    cleaned = module.lstrip(".")
    return any(
        cleaned == prefix or cleaned.startswith(f"{prefix}.")
        for prefix in prefixes
    )
