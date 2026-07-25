from __future__ import annotations

import ast
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.autonomy_supervisor import (
    AUTONOMY_SUPERVISOR_LABELS,
    AUTONOMY_SUPERVISOR_LANES,
    AutonomySupervisorConfig,
    build_autonomy_supervisor_report,
    build_autonomy_supervisor_report_from_records,
    render_autonomy_supervisor_json,
    render_autonomy_supervisor_text,
    write_autonomy_supervisor_jsonl,
)


MODULE_PATH = Path("src/algotrader/execution/autonomy_supervisor.py")
AS_OF = "2026-07-24T00:00:00Z"

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "os",
    "requests",
    "socket",
    "ssl",
    "urllib",
)
FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
    "getenv",
    "liquidate",
    "load_config",
    "monotonic",
    "now",
    "replace_order",
    "request",
    "socket.socket",
    "submit_order",
    "submit_order_request",
    "time",
    "urlopen",
    "utcnow",
}

_SAFETY_FALSE_KEYS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "broker_mutation_allowed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)


def _config(tmp_path: Path, **overrides) -> AutonomySupervisorConfig:  # noqa: ANN003
    kwargs = {
        "run_id": "supervisor-test",
        "as_of": AS_OF,
        "lanes_root": tmp_path,
    }
    kwargs.update(overrides)
    return AutonomySupervisorConfig(**kwargs)


def _lane_state(payload: dict, lane_id: str) -> str:
    for summary in payload["lanes"]:
        if summary["lane_id"] == lane_id:
            return summary["normalized_state"]
    raise AssertionError(f"lane {lane_id} not present")


def _lane_summary(payload: dict, lane_id: str) -> dict:
    for summary in payload["lanes"]:
        if summary["lane_id"] == lane_id:
            return summary
    raise AssertionError(f"lane {lane_id} not present")


def _assert_safety_booleans_false(payload: dict) -> None:
    for key in _SAFETY_FALSE_KEYS:
        assert payload[key] is False, key


def test_all_lanes_absent_reports_no_lane_evidence(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report(_config(tmp_path))

    assert payload["system_status"] == "no_lane_evidence"
    assert payload["system_blocked"] is False
    assert payload["system_attention_required"] is False
    assert payload["lane_count"] == len(AUTONOMY_SUPERVISOR_LANES)
    assert payload["lane_state_counts"]["absent"] == len(AUTONOMY_SUPERVISOR_LANES)
    assert set(payload["absent_lanes"]) == {
        lane.lane_id for lane in AUTONOMY_SUPERVISOR_LANES
    }
    assert payload["labels"] == list(AUTONOMY_SUPERVISOR_LABELS)
    assert payload["profit_claim"] == "none"
    assert payload["recommended_next_action"] != ""
    _assert_safety_booleans_false(payload)


def test_blocked_review_lane_makes_system_blocked(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path),
        {
            "crypto_supervised_readiness_trial": {"trial_classification": "accepted"},
            "crypto_bounded_paper_probe_review": {
                "classification": "blocked_by_operational_evidence",
                "blockers": ["missing_venue_capability"],
            },
        },
    )

    assert payload["system_status"] == "blocked"
    assert payload["system_blocked"] is True
    assert payload["system_attention_required"] is True
    assert _lane_state(payload, "crypto_bounded_paper_probe_review") == "blocked"
    assert _lane_state(payload, "crypto_supervised_readiness_trial") == "nominal"
    assert payload["recommended_next_action_lane"] == (
        "crypto_bounded_paper_probe_review"
    )
    assert "missing_venue_capability" in payload["aggregate_blockers"]
    _assert_safety_booleans_false(payload)


def test_eligible_review_lane_requires_attention_not_blocked(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path),
        {
            "crypto_bounded_paper_probe_review": {
                "classification": "eligible_for_operator_review_only",
            },
        },
    )

    assert _lane_state(payload, "crypto_bounded_paper_probe_review") == (
        "attention_required"
    )
    assert payload["system_status"] == "attention_required"
    assert payload["system_blocked"] is False
    assert payload["system_attention_required"] is True
    summary = _lane_summary(payload, "crypto_bounded_paper_probe_review")
    assert summary["next_action"] == "operator_review_only_no_paper_mutation_authorized"


def test_waiting_lanes_report_waiting_system(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path),
        {
            "crypto_forward_shadow_cycle": {
                "classification": "waiting_for_tournament_terminal",
            },
            "crypto_bounded_paper_probe_review": {
                "classification": "waiting_for_v5_25_terminal_evidence",
            },
        },
    )

    assert payload["system_status"] == "waiting"
    assert _lane_state(payload, "crypto_forward_shadow_cycle") == "waiting"
    assert _lane_state(payload, "crypto_bounded_paper_probe_review") == "waiting"
    assert payload["system_attention_required"] is False


def test_unknown_state_value_fails_closed_to_unknown(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path),
        {"crypto_supervised_readiness_trial": {"trial_classification": "brand_new"}},
    )

    assert _lane_state(payload, "crypto_supervised_readiness_trial") == "unknown"
    assert payload["system_status"] == "attention_required"


def test_cautionary_token_in_unmapped_state_normalizes_blocked(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path),
        {
            "spy_offline_daily_cycle": {
                "daily_chain_state": "blocked_something_unexpected",
                "chain_blockers": ["unexpected"],
            }
        },
    )

    assert _lane_state(payload, "spy_offline_daily_cycle") == "blocked"
    summary = _lane_summary(payload, "spy_offline_daily_cycle")
    assert "unexpected" in summary["blockers"]


def test_safety_flag_not_false_blocks_lane(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path),
        {
            "spy_market_data_soak": {
                "evidence_state": "accepted_unattended_market_data_soak",
                "network_access_attempted": True,
            }
        },
    )

    summary = _lane_summary(payload, "spy_market_data_soak")
    assert summary["normalized_state"] == "blocked"
    assert summary["safety_flags_ok"] is False
    assert "source_safety_flags_not_false" in summary["blockers"]
    _assert_safety_booleans_false(payload)


def test_operator_action_required_escalates_to_attention(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path),
        {
            "spy_market_data_soak": {
                "evidence_state": "collecting_unattended_market_data_soak",
                "operator_action_required": True,
            }
        },
    )

    assert _lane_state(payload, "spy_market_data_soak") == "attention_required"


def test_stale_nominal_lane_escalates_to_stale(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path, as_of="2026-07-24T00:00:00Z"),
        {
            "spy_market_data_soak": {
                "evidence_state": "accepted_unattended_market_data_soak",
                "latest_attempted_session_date": "2026-07-01",
            }
        },
    )

    summary = _lane_summary(payload, "spy_market_data_soak")
    assert summary["stale"] is True
    assert summary["normalized_state"] == "stale"
    assert summary["age_hours"] is not None and summary["age_hours"] > 96
    # The lane is still reported stale, but only the operator can restart the
    # scheduled refresh task, so the system waits rather than claiming an
    # attention condition the autonomous loop could act on.
    assert summary["stale_requires_operator_action"] is True
    assert payload["system_status"] == "waiting"
    assert "spy_market_data_soak" in payload["stale_lanes"]


def test_fresh_nominal_soak_is_not_stale(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path, as_of="2026-07-24T00:00:00Z"),
        {
            "spy_market_data_soak": {
                "evidence_state": "accepted_unattended_market_data_soak",
                "latest_attempted_session_date": "2026-07-23",
            }
        },
    )

    summary = _lane_summary(payload, "spy_market_data_soak")
    assert summary["stale"] is False
    assert summary["normalized_state"] == "nominal"
    assert payload["system_status"] == "nominal"


def test_daily_cycle_stale_after_30h(tmp_path: Path) -> None:
    # V5.42 Stage 3: a timestamped daily-cycle record older than 30h is stale.
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path, as_of="2026-07-24T00:00:00Z"),
        {
            "spy_offline_daily_cycle": {
                "daily_chain_state": "accepted_observe_hold_noop",
                "generated_at": "2026-07-20T00:00:00Z",
            }
        },
    )

    summary = _lane_summary(payload, "spy_offline_daily_cycle")
    assert summary["stale"] is True
    assert summary["normalized_state"] == "stale"
    # No allowlisted offline command writes this lane's artifact, so staleness
    # routes to the operator rather than to the pinned m446 milestone rerun.
    assert summary["next_action"] == "operator_refresh_offline_daily_cycle_inputs"
    assert summary["stale_requires_operator_action"] is True
    assert payload["system_status"] == "waiting"
    assert "spy_offline_daily_cycle" in payload["stale_lanes"]


def test_daily_cycle_fresh_is_nominal(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path, as_of="2026-07-24T00:00:00Z"),
        {
            "spy_offline_daily_cycle": {
                "daily_chain_state": "accepted_observe_hold_noop",
                "generated_at": "2026-07-23T18:00:00Z",
            }
        },
    )

    summary = _lane_summary(payload, "spy_offline_daily_cycle")
    assert summary["stale"] is False
    assert summary["normalized_state"] == "nominal"


def test_daily_cycle_without_timestamp_is_not_stale(tmp_path: Path) -> None:
    # No timestamp -> staleness cannot be computed -> never stale (seeded/absent
    # evidence is unaffected by the 30h bound).
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path, as_of="2026-07-24T00:00:00Z"),
        {
            "spy_offline_daily_cycle": {
                "daily_chain_state": "accepted_observe_hold_noop",
            }
        },
    )

    summary = _lane_summary(payload, "spy_offline_daily_cycle")
    assert summary["stale"] is False
    assert summary["normalized_state"] == "nominal"


def test_file_based_reading_json_object_and_jsonl_last(tmp_path: Path) -> None:
    soak_path = tmp_path / "paper_lab" / "spy_adjusted_market_data_soak_report.json"
    soak_path.parent.mkdir(parents=True)
    soak_path.write_text(
        json.dumps(
            {
                "evidence_state": "collecting_unattended_market_data_soak",
                "latest_attempted_session_date": "2026-07-23",
            }
        ),
        encoding="utf-8",
    )
    cycle_path = tmp_path / "cycle.jsonl"
    cycle_path.write_text(
        '{"daily_chain_state":"blocked_old"}\n'
        '{"daily_chain_state":"accepted_observe_hold_noop"}\n',
        encoding="utf-8",
    )

    payload = build_autonomy_supervisor_report(
        _config(
            tmp_path,
            lane_artifact_overrides={"spy_offline_daily_cycle": cycle_path},
        )
    )

    assert _lane_state(payload, "spy_market_data_soak") == "waiting"
    # The last JSONL record wins over the earlier blocked one.
    assert _lane_state(payload, "spy_offline_daily_cycle") == "nominal"
    soak_summary = _lane_summary(payload, "spy_market_data_soak")
    assert soak_summary["found"] is True
    assert soak_summary["parsed"] is True


def test_malformed_artifact_blocks_lane(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("{not-json}", encoding="utf-8")

    payload = build_autonomy_supervisor_report(
        _config(
            tmp_path,
            lane_artifact_overrides={"spy_market_data_soak": bad_path},
        )
    )

    summary = _lane_summary(payload, "spy_market_data_soak")
    assert summary["found"] is True
    assert summary["parsed"] is False
    assert summary["normalized_state"] == "blocked"
    assert any(
        blocker.startswith("source_unreadable:") for blocker in summary["blockers"]
    )


def test_missing_state_field_is_unknown(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path),
        {"crypto_capability_production": {"unrelated_field": "value"}},
    )

    summary = _lane_summary(payload, "crypto_capability_production")
    assert summary["normalized_state"] == "unknown"
    assert "source_state_field_absent" in summary["blockers"]


def test_write_jsonl_writes_exactly_one_record(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report(_config(tmp_path))
    output_path = tmp_path / "runs" / "supervisor" / "report.jsonl"
    output_path.parent.mkdir(parents=True)
    output_path.write_text('{"old":1}\n{"old":2}\n', encoding="utf-8")

    result = write_autonomy_supervisor_jsonl(payload, output_path)
    records = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert result.record_count == 1
    assert result.submitted is False
    assert result.mutated is False
    assert result.live_authorized is False
    assert result.newline_terminated is True
    assert records == [json.loads(render_autonomy_supervisor_json(payload))]


def test_render_json_is_deterministic_and_sorted(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report_from_records(
        _config(tmp_path),
        {"crypto_supervised_readiness_trial": {"trial_classification": "accepted"}},
    )
    first = render_autonomy_supervisor_json(payload)
    second = render_autonomy_supervisor_json(payload)

    assert first == second
    keys = list(json.loads(first).keys())
    assert keys == sorted(keys)


def test_render_text_lists_lanes_and_safety(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report(_config(tmp_path))
    text = render_autonomy_supervisor_text(payload)

    assert "Cross-lane autonomy supervisor" in text
    for lane in AUTONOMY_SUPERVISOR_LANES:
        assert lane.lane_id in text
    assert "live_authorized: false" in text


def test_report_is_deterministic_for_same_records(tmp_path: Path) -> None:
    records = {
        "spy_market_data_soak": {
            "evidence_state": "collecting_unattended_market_data_soak",
            "latest_attempted_session_date": "2026-07-23",
        },
        "crypto_bounded_paper_probe_review": {
            "classification": "waiting_for_v5_25_terminal_evidence",
        },
    }
    first = build_autonomy_supervisor_report_from_records(_config(tmp_path), records)
    second = build_autonomy_supervisor_report_from_records(_config(tmp_path), records)

    assert first == second


def test_invalid_as_of_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        AutonomySupervisorConfig(
            run_id="r",
            as_of="not-a-timestamp",
            lanes_root=tmp_path,
        )


def test_unknown_lane_override_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        AutonomySupervisorConfig(
            run_id="r",
            as_of=AS_OF,
            lanes_root=tmp_path,
            lane_artifact_overrides={"not_a_lane": tmp_path / "x.json"},
        )


def test_unknown_lane_record_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        build_autonomy_supervisor_report_from_records(
            _config(tmp_path),
            {"not_a_lane": {"classification": "accepted"}},
        )


def test_registry_integrity() -> None:
    lane_ids = [lane.lane_id for lane in AUTONOMY_SUPERVISOR_LANES]
    assert len(lane_ids) == len(set(lane_ids))
    required_states = {
        "absent",
        "nominal",
        "waiting",
        "stale",
        "attention_required",
        "blocked",
        "unknown",
    }
    for lane in AUTONOMY_SUPERVISOR_LANES:
        assert required_states.issubset(set(lane.next_actions.keys())), lane.lane_id
        for value in lane.state_map.values():
            assert value in required_states, (lane.lane_id, value)


def test_cli_command_registered_and_runs(tmp_path: Path) -> None:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_module.main(
            [
                "autonomy-supervisor-status",
                "--run-id",
                "cli-test",
                "--as-of",
                AS_OF,
                "--lanes-root",
                str(tmp_path),
                "--format",
                "json",
            ]
        )

    payload = json.loads(buffer.getvalue().strip())
    assert exit_code == 1
    assert payload["record_type"] == "autonomy_supervisor_report"
    assert payload["system_status"] == "no_lane_evidence"
    assert payload["allow_empty_lab"] is False
    assert payload["evidence_required"] is True
    _assert_safety_booleans_false(payload)


def test_no_lane_evidence_fails_closed_by_default(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report(_config(tmp_path))

    assert payload["system_status"] == "no_lane_evidence"
    assert payload["allow_empty_lab"] is False
    assert payload["evidence_required"] is True


def test_no_lane_evidence_allows_explicit_empty_lab(tmp_path: Path) -> None:
    payload = build_autonomy_supervisor_report(
        _config(tmp_path), allow_empty_lab=True
    )

    assert payload["system_status"] == "no_lane_evidence"
    assert payload["allow_empty_lab"] is True
    assert payload["evidence_required"] is False


def test_evidence_required_false_when_lane_evidence_present(tmp_path: Path) -> None:
    review_path = tmp_path / "review.json"
    review_path.write_text(
        json.dumps({"classification": "blocked_by_operational_evidence"}),
        encoding="utf-8",
    )
    payload = build_autonomy_supervisor_report(
        AutonomySupervisorConfig(
            run_id="run",
            as_of=AS_OF,
            lanes_root=tmp_path,
            lane_artifact_overrides={
                "crypto_bounded_paper_probe_review": review_path
            },
        )
    )

    assert payload["system_status"] != "no_lane_evidence"
    assert payload["evidence_required"] is False


def test_rejects_non_bool_allow_empty_lab(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        build_autonomy_supervisor_report(
            _config(tmp_path), allow_empty_lab="yes"  # type: ignore[arg-type]
        )


def test_cli_no_lane_evidence_exits_one_by_default(tmp_path: Path) -> None:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_module.main(
            [
                "autonomy-supervisor-status",
                "--run-id",
                "cli-empty",
                "--as-of",
                AS_OF,
                "--lanes-root",
                str(tmp_path),
                "--format",
                "json",
            ]
        )

    payload = json.loads(buffer.getvalue().strip())
    assert payload["system_status"] == "no_lane_evidence"
    assert payload["evidence_required"] is True
    assert exit_code == 1


def test_cli_allows_explicit_empty_lab(tmp_path: Path) -> None:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_module.main(
            [
                "autonomy-supervisor-status",
                "--run-id",
                "cli-empty",
                "--as-of",
                AS_OF,
                "--lanes-root",
                str(tmp_path),
                "--allow-empty-lab",
                "--format",
                "json",
            ]
        )

    payload = json.loads(buffer.getvalue().strip())
    assert payload["allow_empty_lab"] is True
    assert payload["evidence_required"] is False
    assert exit_code == 0


def test_powershell_wrapper_forwards_allow_empty_lab() -> None:
    script_path = Path("scripts/run_autonomy_supervisor.ps1")
    script = script_path.read_text(encoding="utf-8")

    assert "[switch]$AllowEmptyLab" in script
    assert '$Arguments += "--allow-empty-lab"' in script


def test_cli_blocked_lane_returns_nonzero_exit(tmp_path: Path) -> None:
    review_path = tmp_path / "review.json"
    review_path.write_text(
        json.dumps({"classification": "blocked_by_operational_evidence"}),
        encoding="utf-8",
    )
    run_log = tmp_path / "supervisor.jsonl"
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_module.main(
            [
                "autonomy-supervisor-status",
                "--run-id",
                "cli-test",
                "--as-of",
                AS_OF,
                "--lanes-root",
                str(tmp_path),
                "--lane",
                f"crypto_bounded_paper_probe_review={review_path}",
                "--run-log",
                str(run_log),
                "--format",
                "json",
            ]
        )

    assert exit_code == 1
    record = json.loads(run_log.read_text(encoding="utf-8").strip())
    assert record["system_status"] == "blocked"


def test_cli_bad_lane_override_returns_validation_exit(tmp_path: Path) -> None:
    exit_code = cli_module.main(
        [
            "autonomy-supervisor-status",
            "--run-id",
            "cli-test",
            "--as-of",
            AS_OF,
            "--lanes-root",
            str(tmp_path),
            "--lane",
            "missing_equals_sign",
        ]
    )
    assert exit_code == 2


def test_module_has_no_forbidden_imports_or_calls() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _assert_import_allowed(alias.name)
        elif isinstance(node, ast.ImportFrom):
            _assert_import_allowed(node.module or "")
        elif isinstance(node, ast.Call):
            _assert_call_allowed(node.func)


def _assert_import_allowed(module_name: str) -> None:
    root = module_name.split(".")[0]
    assert root not in FORBIDDEN_IMPORT_PREFIXES, module_name


def _assert_call_allowed(func: ast.expr) -> None:
    if isinstance(func, ast.Name):
        assert func.id not in FORBIDDEN_CALL_NAMES, func.id
    elif isinstance(func, ast.Attribute):
        assert func.attr not in FORBIDDEN_CALL_NAMES, func.attr
