from __future__ import annotations

import json
from pathlib import Path

import pytest

from algotrader.execution.autonomy_next_plan import (
    EXECUTION_AUTHORIZED_NETWORK_READ_ONLY,
    classify_action,
)
from algotrader.execution.autonomy_read_only_network_executor import (
    AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST,
)
from algotrader.execution.autonomy_spy_refresh_cycle import (
    AUTONOMY_SPY_REFRESH_ACTION_TOKEN,
    CANONICAL_SPY_DAILY_BARS_RELPATH,
    main,
    run_autonomy_spy_refresh_cycle,
)
from algotrader.execution.autonomy_supervisor import (
    AUTONOMY_SUPERVISOR_LANES,
    STATE_ABSENT,
)


AS_OF = "2026-07-28T20:11:00+00:00"
SESSION_ID = "2026-07-28"


def _canonical_test_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    with_bars: bool = False,
) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    (tmp_path / "src" / "algotrader").mkdir(parents=True)
    if with_bars:
        bars = tmp_path / CANONICAL_SPY_DAILY_BARS_RELPATH
        bars.parent.mkdir(parents=True)
        bars.write_text(
            "date,open,high,low,close,volume\n"
            "2026-07-28,100,101,99,100.5,1000\n",
            encoding="utf-8",
        )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _network_result(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "action_token": (
            "run_authorized_read_only_market_data_refresh_to_seed_soak"
        ),
        "apply": True,
        "session_id": SESSION_ID,
        "as_of": AS_OF,
        "session_already_qualified": False,
        "attempt_number": 1,
        "run_id": f"network-{SESSION_ID}-1",
        "adapter_refresh_state": "accepted_adjusted_spy_data_refresh",
        "network_access_attempted": True,
        "interlock_verdict": {
            "paper_boundary_ok": True,
            "app_profile": "paper",
            "endpoint_class": "paper",
            "live_signals": [],
            "blockers": [],
            "live_authorized": False,
        },
        "exit_code": 0,
    }
    result.update(overrides)
    return result


def _cycle_result(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "run_id": f"v5.53-spy-{SESSION_ID}",
        "as_of": AS_OF,
        "apply": True,
        "operator_inputs_provided": True,
        "operator_input_bound_actions": [
            "run_spy_offline_daily_cycle_to_seed_evidence"
        ],
        "before_system_status": "no_lane_evidence",
        "before_plan_class": "offline_action_available",
        "eligible_count": 2,
        "execution_count": 2,
        "all_executions_succeeded": True,
        "after_system_status": "nominal",
        "cycle_outcome": "refreshed",
        "converged": True,
        "refreshed_lanes": [
            "spy_offline_daily_cycle",
            "crypto_supervised_readiness_trial",
        ],
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }
    result.update(overrides)
    return result


def test_success_binds_canonical_csv_into_sanitized_offline_cycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _canonical_test_root(tmp_path, monkeypatch, with_bars=True)
    captured: dict[str, object] = {}

    def fake_network(**kwargs: object) -> dict[str, object]:
        captured["network_kwargs"] = kwargs
        return _network_result()

    def fake_self_refresh(config, **kwargs: object) -> dict[str, object]:  # noqa: ANN001
        captured["config"] = config
        captured["self_refresh_kwargs"] = kwargs
        return _cycle_result()

    result = run_autonomy_spy_refresh_cycle(
        as_of=AS_OF,
        apply=True,
        network_runner=fake_network,
        self_refresh_builder=fake_self_refresh,
    )

    assert result["exit_code"] == 0
    assert result["stage_status"] == "completed"
    assert result["observable_outcome"] == "m444_refreshed_nominal"
    assert result["spy_daily_cycle_refreshed"] is True
    assert result["network_access_attempted"] is True
    assert result["credential_access_attempted"] is True
    assert result["offline_environment_sanitized"] is True
    assert result["broker_access_attempted"] is False
    assert result["broker_mutation_performed"] is False
    assert result["paper_submit_performed"] is False
    assert result["live_authorized"] is False
    assert captured["network_kwargs"] == {
        "as_of": AS_OF,
        "apply": True,
        "format": "json",
    }

    config = captured["config"]
    assert config.run_id == f"v5.53-spy-{SESSION_ID}"
    assert config.as_of == AS_OF
    assert config.lanes_root == Path("runs")
    kwargs = captured["self_refresh_kwargs"]
    assert kwargs["apply"] is True
    assert kwargs["environ"] == {}
    operator_inputs = kwargs["operator_inputs"]
    assert operator_inputs.validated_at == AS_OF
    assert operator_inputs.daily_bars_csv == (
        root / CANONICAL_SPY_DAILY_BARS_RELPATH
    ).resolve()


def test_network_dry_run_stops_before_offline_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _canonical_test_root(tmp_path, monkeypatch)

    def fail_if_called(*args: object, **kwargs: object) -> None:
        pytest.fail("offline stage must not run after a network preview")

    result = run_autonomy_spy_refresh_cycle(
        as_of=AS_OF,
        network_runner=lambda **kwargs: _network_result(  # noqa: ARG005
            apply=False,
            adapter_refresh_state=None,
            network_access_attempted=False,
            exit_code=1,
        ),
        self_refresh_builder=fail_if_called,
    )

    assert result["exit_code"] == 1
    assert result["stage_status"] == "network_dry_run_preview"
    assert result["observable_outcome"] == "network_dry_run_preview"
    assert result["network_access_attempted"] is False
    assert result["credential_access_attempted"] is False
    assert "offline_self_refresh" not in result


def test_network_refusal_is_propagated_without_offline_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _canonical_test_root(tmp_path, monkeypatch)

    def fail_if_called(*args: object, **kwargs: object) -> None:
        pytest.fail("offline stage must not run after network refusal")

    result = run_autonomy_spy_refresh_cycle(
        as_of=AS_OF,
        apply=True,
        network_runner=lambda **kwargs: _network_result(  # noqa: ARG005
            adapter_refresh_state=None,
            network_access_attempted=False,
            refusal_category="live_capital_interlock_blocked",
            exit_code=2,
        ),
        self_refresh_builder=fail_if_called,
    )

    assert result["exit_code"] == 2
    assert result["stage_status"] == "network_refused"
    assert result["refusal_category"] == "live_capital_interlock_blocked"
    assert result["broker_access_attempted"] is False
    assert result["live_authorized"] is False


def test_accepted_network_result_requires_canonical_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _canonical_test_root(tmp_path, monkeypatch)

    result = run_autonomy_spy_refresh_cycle(
        as_of=AS_OF,
        apply=True,
        network_runner=lambda **kwargs: _network_result(),  # noqa: ARG005
    )

    assert result["exit_code"] == 2
    assert result["stage_status"] == "offline_refused"
    assert result["refusal_category"] == "canonical_daily_bars_missing"


def test_already_qualified_session_reuses_canonical_csv_without_credential_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _canonical_test_root(tmp_path, monkeypatch, with_bars=True)

    result = run_autonomy_spy_refresh_cycle(
        as_of=AS_OF,
        apply=True,
        network_runner=lambda **kwargs: _network_result(  # noqa: ARG005
            adapter_refresh_state=None,
            session_already_qualified=True,
            network_access_attempted=False,
        ),
        self_refresh_builder=lambda *args, **kwargs: _cycle_result(  # noqa: ARG005
            execution_count=0,
            all_executions_succeeded=None,
            refreshed_lanes=[],
        ),
    )

    assert result["exit_code"] == 0
    assert result["observable_outcome"] == "cycle_converged_no_spy_refresh"
    assert result["network_access_attempted"] is False
    assert result["credential_access_attempted"] is False


def test_offline_failure_is_not_reported_as_completed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _canonical_test_root(tmp_path, monkeypatch, with_bars=True)

    result = run_autonomy_spy_refresh_cycle(
        as_of=AS_OF,
        apply=True,
        network_runner=lambda **kwargs: _network_result(),  # noqa: ARG005
        self_refresh_builder=lambda *args, **kwargs: _cycle_result(  # noqa: ARG005
            all_executions_succeeded=False,
            cycle_outcome="execution_failed",
            converged=False,
            refreshed_lanes=[],
        ),
    )

    assert result["exit_code"] == 1
    assert result["stage_status"] == "offline_failed"
    assert result["observable_outcome"] == "offline_execution_failed"


def test_unknown_network_fields_and_exception_text_cannot_leak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _canonical_test_root(tmp_path, monkeypatch, with_bars=True)
    secret = "secret-token-must-not-appear"

    result = run_autonomy_spy_refresh_cycle(
        as_of=AS_OF,
        apply=True,
        network_runner=lambda **kwargs: _network_result(  # noqa: ARG005
            credential_value=secret,
            interlock_verdict={
                "paper_boundary_ok": True,
                "unexpected": secret,
            },
        ),
        self_refresh_builder=lambda *args, **kwargs: _cycle_result(),  # noqa: ARG005
    )
    assert secret not in json.dumps(result)
    assert "credential_value" not in result["network_refresh"]
    assert "unexpected" not in result["network_refresh"]["interlock_verdict"]

    def raising_network(**kwargs: object) -> dict[str, object]:
        raise RuntimeError(secret)

    failed = run_autonomy_spy_refresh_cycle(
        as_of=AS_OF,
        apply=True,
        network_runner=raising_network,
    )
    assert failed["refusal_category"] == "network_executor_internal_failure"
    assert secret not in json.dumps(failed)


def test_action_is_allowlisted_classified_and_supervisor_routed() -> None:
    assert AUTONOMY_SPY_REFRESH_ACTION_TOKEN in AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST
    classified = classify_action(AUTONOMY_SPY_REFRESH_ACTION_TOKEN)
    assert classified.execution_class == EXECUTION_AUTHORIZED_NETWORK_READ_ONLY
    assert classified.offline_runnable is False
    assert "autonomy_spy_refresh_cycle" in classified.command

    spy_soak = next(
        lane for lane in AUTONOMY_SUPERVISOR_LANES
        if lane.lane_id == "spy_market_data_soak"
    )
    assert spy_soak.next_actions[STATE_ABSENT] == AUTONOMY_SPY_REFRESH_ACTION_TOKEN


def test_wrapper_and_schedule_route_the_integrated_command() -> None:
    wrapper = Path("scripts/run_spy_integrated_refresh_cycle.ps1").read_text(
        encoding="utf-8"
    )
    schedule = Path(
        "docs/design/spy_eod_market_data_refresh_scheduled_task.xml"
    ).read_text(encoding="utf-8")

    assert "[DateTimeOffset]::UtcNow" in wrapper
    assert "algotrader.execution.autonomy_spy_refresh_cycle" in wrapper
    assert "--apply" in wrapper
    assert "run_spy_integrated_refresh_cycle.ps1" in schedule
    assert "run_spy_read_only_network_executor.ps1" not in schedule


def test_successful_apply_reconciles_decision_time_shadow_without_broadening_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _canonical_test_root(tmp_path, monkeypatch, with_bars=True)
    calls: list[dict[str, object]] = []

    def reconciler(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        return {
            "milestone": "v5.54",
            "mode": "reconcile",
            "state": "reconciled",
            "session_id": "2026-07-24",
            "classification": "matched",
            "provisional_decision": "target_long",
            "authoritative_decision": "target_long",
            "network_access_attempted": False,
            "credential_access_attempted": False,
            "broker_access_attempted": False,
            "broker_mutation_performed": False,
            "paper_submit_performed": False,
            "submitted": False,
            "mutated": False,
            "live_trading_performed": False,
            "live_authorized": False,
            "profit_claim": "none",
            "exit_code": 0,
            "secret_extra": "must-not-cross",
        }

    result = run_autonomy_spy_refresh_cycle(
        as_of=AS_OF,
        apply=True,
        network_runner=lambda **_kwargs: _network_result(),
        self_refresh_builder=lambda _config, **_kwargs: _cycle_result(),
        shadow_reconciler=reconciler,
    )

    assert result["exit_code"] == 0
    assert calls == [
        {
            "session_id": SESSION_ID,
            "as_of": AS_OF,
        }
    ]
    assert result["decision_time_shadow"]["state"] == "reconciled"
    assert result["decision_time_shadow"]["classification"] == "matched"
    assert "secret_extra" not in result["decision_time_shadow"]
    assert result["network_access_attempted"] is True
    assert result["broker_access_attempted"] is False


def test_parser_refuses_unknown_arguments_without_echoing_them(
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "secret-parser-value"
    exit_code = main(
        [
            "--as-of",
            AS_OF,
            "--unknown",
            secret,
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 2
    assert payload["refusal_category"] == "parser_invalid_argument"
    assert secret not in captured.out
    assert captured.err == ""
