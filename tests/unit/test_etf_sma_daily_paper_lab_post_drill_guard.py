from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
import algotrader.execution.etf_sma_daily_paper_lab as paper_lab_module
from algotrader.execution.etf_sma_daily_paper_lab import (
    EtfSmaDailyPaperLabConfig,
    run_etf_sma_daily_paper_lab,
    validate_etf_sma_daily_paper_lab_packet,
)


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "etf_sma_cycle_matrix"
MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_paper_lab.py")
CLIENT_ORDER_ID = "v192-spy-43fb12a5d4aa5fbf4990aa7a"

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "requests",
    "socket",
    "urllib",
)
FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "cancel_order_by_id",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
    "delete",
    "getenv",
    "load_config",
    "liquidate",
    "replace_order",
    "request",
    "socket.socket",
    "submit_order",
    "submit_order_request",
    "urlopen",
}


def test_valid_v200_guard_packet_renders_post_drill_guard_section(
    tmp_path: Path,
) -> None:
    guard_path = _write_guard_packet(tmp_path, _guard_packet())
    output_root = tmp_path / "paper_lab_v201_valid"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            run_date="2025-07-21",
            post_drill_guard_packet_path=guard_path,
            operational_only=True,
        )
    )

    mission = json.loads((output_root / "mission_control.json").read_text())
    latest = json.loads((output_root / "latest_run.json").read_text())
    record = json.loads((output_root / "operating_record.jsonl").read_text())
    manifest = json.loads((output_root / "manifest.jsonl").read_text())
    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")

    for surface in (payload, mission, record, manifest):
        guard = surface["post_drill_guard"]
        assert guard["status"] == "post_drill_guard_authority_closed"
        assert guard["classification"] == (
            "mission_control_post_drill_guard_authority_closed"
        )
        assert guard["ready_classification"] == "mission_control_post_drill_guard_ready"
        assert guard["latest_drill_outcome"] == (
            "paper_drill_submitted_cancel_confirmed"
        )
        assert guard["final_broker_order_status"] == "canceled"
        assert guard["client_order_id"] == CLIENT_ORDER_ID
        assert guard["authorization_consumed"] is True
        _assert_guard_display_denies_paper_action(guard)

    assert mission["post_drill_guard"] == payload["post_drill_guard"]
    assert "post_drill_guard" not in mission["active_operating_brief"]
    assert "post_drill_guard" not in mission["daily_latest"]
    assert "post_drill_guard" not in mission["daily_decision_summary"]
    assert "post_drill_guard" not in latest
    assert latest["post_drill_guard_status"] == "post_drill_guard_authority_closed"
    assert latest["post_drill_guard_latest_drill_outcome"] == (
        "paper_drill_submitted_cancel_confirmed"
    )
    assert latest["post_drill_guard_final_broker_order_status"] == "canceled"
    assert latest["post_drill_guard_authorization_consumed"] is True
    assert latest["post_drill_guard_paper_submit_authorized"] is False
    assert latest["post_drill_guard_paper_cancel_authorized"] is False
    assert (
        latest["post_drill_guard_next_paper_action_requires_new_authorization"]
        is True
    )
    assert "client_order_id" not in json.dumps(latest, sort_keys=True).lower()
    assert validate_etf_sma_daily_paper_lab_packet(output_root, packet=payload)[
        "validation_status"
    ] == "pass"

    assert "## Post-Drill Guard" in brief
    assert "paper_drill_submitted_cancel_confirmed" in brief
    assert "Final broker order status: `canceled`" in brief
    assert f"Client order id: `{CLIENT_ORDER_ID}`" in brief
    assert "Authorization consumed: `true`" in brief
    assert "paper_submit_authorized=false" in brief
    assert "paper_cancel_authorized=false" in brief
    assert "next_paper_action_requires_new_authorization=true" in brief


def test_missing_guard_packet_does_not_authorize_paper_action(tmp_path: Path) -> None:
    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=tmp_path / "paper_lab_v201_missing",
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            run_date="2025-07-21",
            post_drill_guard_packet_path=tmp_path / "missing.json",
            operational_only=True,
        )
    )

    guard = payload["post_drill_guard"]
    assert guard["status"] == "post_drill_guard_not_available"
    assert guard["classification"] == "mission_control_post_drill_guard_missing"
    assert guard["blocker"] == "post_drill_guard_packet_missing"
    _assert_guard_display_denies_paper_action(guard)


def test_malformed_guard_packet_does_not_authorize_paper_action(
    tmp_path: Path,
) -> None:
    guard_path = tmp_path / "post_drill_guard_packet.json"
    guard_path.write_text("{not-json", encoding="utf-8")

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=tmp_path / "paper_lab_v201_malformed",
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            run_date="2025-07-21",
            post_drill_guard_packet_path=guard_path,
            operational_only=True,
        )
    )

    guard = payload["post_drill_guard"]
    assert guard["status"] == "post_drill_guard_not_available"
    assert guard["classification"] == "mission_control_post_drill_guard_malformed"
    assert guard["blocker"] == "post_drill_guard_packet_invalid_json"
    _assert_guard_display_denies_paper_action(guard)


def test_guard_packet_with_live_activity_blocks_closed(tmp_path: Path) -> None:
    guard = _guard_packet(source_live_read_performed=True)
    guard_path = _write_guard_packet(tmp_path, guard)

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=tmp_path / "paper_lab_v201_live_activity",
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            run_date="2025-07-21",
            post_drill_guard_packet_path=guard_path,
            operational_only=True,
        )
    )

    display = payload["post_drill_guard"]
    assert display["status"] == "post_drill_guard_not_available"
    assert display["classification"] == (
        "mission_control_post_drill_guard_blocked_live_activity"
    )
    assert display["blocker"] == "post_drill_guard_packet_live_activity"
    assert display["authorization_consumed"] is False
    _assert_guard_display_denies_paper_action(display)


def test_cli_accepts_and_forwards_post_drill_guard_packet_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    guard_path = tmp_path / "post_drill_guard_packet.json"
    args = cli_module.build_parser().parse_args(
        [
            "etf-sma-daily-paper-lab",
            "--output-root",
            str(tmp_path / "parser_smoke"),
            "--post-drill-guard-packet-path",
            str(guard_path),
        ]
    )
    assert args.post_drill_guard_packet_path == str(guard_path)

    captured_configs: list[EtfSmaDailyPaperLabConfig] = []

    def fake_run(config: EtfSmaDailyPaperLabConfig) -> dict[str, object]:
        captured_configs.append(config)
        return {"ok": True}

    monkeypatch.setattr(paper_lab_module, "run_etf_sma_daily_paper_lab", fake_run)
    monkeypatch.setattr(
        paper_lab_module,
        "etf_sma_daily_paper_lab_exit_status",
        lambda payload: 0,
    )

    exit_code = cli_module.main(
        [
            "etf-sma-daily-paper-lab",
            "--output-root",
            str(tmp_path / "paper_lab_cli_post_drill_guard"),
            "--bars-csv",
            str(FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"),
            "--as-of-date",
            "2025-07-19",
            "--post-drill-guard-packet-path",
            str(guard_path),
            "--format",
            "json",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert len(captured_configs) == 1
    assert captured_configs[0].post_drill_guard_packet_path == guard_path


def test_daily_module_keeps_post_drill_guard_display_offline_and_broker_free() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    imports: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            calls.add(_call_name(node.func))

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert calls.isdisjoint(FORBIDDEN_CALL_NAMES)


def _guard_packet(**overrides: object) -> dict[str, object]:
    packet: dict[str, object] = {
        "packet_version": "v200_post_drill_operating_guard_packet_v1",
        "post_drill_guard_classification": "post_drill_guard_ready",
        "blocker": "none",
        "source_paper_drill_packet_found": True,
        "source_paper_drill_packet_parsed": True,
        "source_paper_drill_packet_error": "",
        "last_paper_drill_outcome": "paper_drill_submitted_cancel_confirmed",
        "source_paper_drill_outcome": "paper_drill_submitted_cancel_confirmed",
        "latest_bounded_paper_drill": {
            "outcome_classification": "paper_drill_submitted_cancel_confirmed",
            "final_broker_order_status": "canceled",
            "client_order_id": CLIENT_ORDER_ID,
            "broker_read_performed": True,
            "broker_mutation_performed": True,
            "paper_submit_performed": True,
            "paper_cancel_performed": True,
            "live_read_performed": False,
            "live_mutation_performed": False,
            "live_trading_performed": False,
        },
        "client_order_id": CLIENT_ORDER_ID,
        "final_broker_order_status_from_source_packet": "canceled",
        "last_authorization_consumed": True,
        "paper_submit_authorized": False,
        "paper_cancel_authorized": False,
        "next_paper_action_requires_new_authorization": True,
        "next_operator_action": (
            "new_explicit_operator_authorization_required_before_any_future_paper_action"
        ),
        "source_broker_read_performed": True,
        "source_broker_mutation_performed": True,
        "source_paper_submit_performed": True,
        "source_paper_cancel_performed": True,
        "source_live_read_performed": False,
        "source_live_mutation_performed": False,
        "source_live_trading_performed": False,
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "paper_cancel_performed": False,
        "live_read_performed": False,
        "live_mutation_performed": False,
        "live_trading_performed": False,
    }
    packet.update(overrides)
    return packet


def _write_guard_packet(root: Path, payload: dict[str, object]) -> Path:
    path = root / "post_drill_guard_packet.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _assert_guard_display_denies_paper_action(guard: dict[str, object]) -> None:
    assert guard["paper_submit_authorized"] is False
    assert guard["paper_cancel_authorized"] is False
    assert guard["next_paper_action_requires_new_authorization"] is True
    assert guard["broker_read_performed"] is False
    assert guard["broker_mutation_performed"] is False
    assert guard["paper_submit_performed"] is False
    assert guard["paper_cancel_performed"] is False
    assert guard["live_read_performed"] is False
    assert guard["live_mutation_performed"] is False
    assert guard["live_trading_performed"] is False


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
