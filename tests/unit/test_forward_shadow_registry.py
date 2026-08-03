from __future__ import annotations

import csv
from datetime import date, timedelta
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research import forward_shadow_registry as subject

UNIVERSE = ("SPY", "AGG")
RULE_FINGERPRINT = "a" * 64
REGISTERED_AT = "2026-08-03T21:00:00+00:00"


def _write_bars(path: Path, sessions: list[date], prices: dict[str, list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            ["symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume"]
        )
        for symbol in UNIVERSE:
            for index, session in enumerate(sessions):
                value = prices[symbol][index]
                writer.writerow(
                    [
                        symbol,
                        session.isoformat(),
                        value,
                        value,
                        value,
                        value,
                        value,
                        1000,
                    ]
                )


@pytest.fixture()
def data_file(tmp_path: Path) -> Path:
    sessions = [date(2026, 7, 31)] + [
        date(2026, 8, 3) + timedelta(days=offset) for offset in range(10)
    ]
    prices = {
        "SPY": [100.0 * (1.01**index) for index in range(len(sessions))],
        "AGG": [100.0 for _ in sessions],
    }
    path = tmp_path / "canonical_data.csv"
    _write_bars(path, sessions, prices)
    return path


def _register(root: Path, *, minimum: int = 3) -> dict:
    return subject.register_forward_shadow(
        root,
        hypothesis_id="demo_hypothesis",
        hypothesis_statement="Hold SPY while registered.",
        universe=UNIVERSE,
        benchmark_symbol="SPY",
        rule_reference="docs/design/example.md",
        rule_fingerprint=RULE_FINGERPRINT,
        gates=subject.ForwardShadowGates(minimum_observation_sessions=minimum),
        registered_at=REGISTERED_AT,
    )


def _append(
    root: Path,
    data_file: Path,
    session: date,
    targets: dict[str, str] | None = None,
    recorded_at: str | None = None,
) -> dict:
    return subject.append_forward_shadow_observation(
        root,
        session=session,
        targets=targets if targets is not None else {"SPY": "1"},
        canonical_data_path=data_file,
        recorded_at=recorded_at or f"{session.isoformat()}T21:00:00+00:00",
    )


def test_policy_fingerprint_is_frozen_and_zero_authority() -> None:
    policy = subject.build_forward_shadow_policy()

    assert policy["policy_fingerprint"] == subject.FORWARD_SHADOW_POLICY_FINGERPRINT
    assert policy["temporal_policy"]["backfill_allowed"] is False
    assert policy["temporal_policy"]["future_session_allowed"] is False
    assert (
        policy["evaluation_policy"]["verdict_before_minimum_observations"]
        == "withheld"
    )
    assert (
        policy["evaluation_policy"]["gate_mutation_after_registration_allowed"]
        is False
    )
    assert policy["authority_boundary"]["live_trading_authorized"] is False
    assert policy["authority_boundary"]["paper_mutation_authorized"] is False
    assert policy["promotion_policy"]["pass_authorizes_paper"] is False
    assert policy["promotion_policy"]["pass_authorizes_live"] is False


def test_registration_is_immutable_and_refuses_reregistration(tmp_path: Path) -> None:
    root = tmp_path / "shadow"
    payload = _register(root)

    assert payload["registration_fingerprint"]
    assert payload["registration_date"] == "2026-08-03"
    assert payload["safety"]["live_authorized"] is False
    assert (root / "registration.json").is_file()
    assert (root / "observations.jsonl").is_file()

    with pytest.raises(ValidationError, match="already registered"):
        _register(root)


def test_benchmark_must_belong_to_universe(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="benchmark_symbol must belong"):
        subject.register_forward_shadow(
            tmp_path / "shadow",
            hypothesis_id="x",
            hypothesis_statement="y",
            universe=UNIVERSE,
            benchmark_symbol="QQQ",
            rule_reference="ref",
            rule_fingerprint=RULE_FINGERPRINT,
            gates=subject.ForwardShadowGates(minimum_observation_sessions=2),
            registered_at=REGISTERED_AT,
        )


def test_backfilled_session_is_rejected(tmp_path: Path, data_file: Path) -> None:
    root = tmp_path / "shadow"
    _register(root)

    with pytest.raises(ValidationError, match="backfill rejected"):
        _append(root, data_file, date(2026, 7, 31), recorded_at=REGISTERED_AT)


def test_session_on_registration_date_is_rejected(
    tmp_path: Path, data_file: Path
) -> None:
    root = tmp_path / "shadow"
    _register(root)

    with pytest.raises(ValidationError, match="backfill rejected"):
        _append(root, data_file, date(2026, 8, 3))


def test_future_session_is_rejected(tmp_path: Path, data_file: Path) -> None:
    root = tmp_path / "shadow"
    _register(root)

    with pytest.raises(ValidationError, match="future session rejected"):
        _append(
            root,
            data_file,
            date(2026, 8, 6),
            recorded_at="2026-08-05T21:00:00+00:00",
        )


def test_out_of_order_and_duplicate_sessions_are_rejected(
    tmp_path: Path, data_file: Path
) -> None:
    root = tmp_path / "shadow"
    _register(root)
    _append(root, data_file, date(2026, 8, 5))

    with pytest.raises(ValidationError, match="out-of-order session"):
        _append(root, data_file, date(2026, 8, 5))
    with pytest.raises(ValidationError, match="out-of-order session"):
        _append(
            root,
            data_file,
            date(2026, 8, 4),
            recorded_at="2026-08-06T21:00:00+00:00",
        )


def test_targets_outside_universe_and_over_allocation_are_rejected(
    tmp_path: Path, data_file: Path
) -> None:
    root = tmp_path / "shadow"
    _register(root)

    with pytest.raises(ValidationError, match="outside the frozen universe"):
        _append(root, data_file, date(2026, 8, 4), targets={"QQQ": "1"})
    with pytest.raises(ValidationError, match="nonnegative implicit cash"):
        _append(
            root, data_file, date(2026, 8, 4), targets={"SPY": "0.7", "AGG": "0.5"}
        )
    with pytest.raises(ValidationError, match="negative"):
        _append(root, data_file, date(2026, 8, 4), targets={"SPY": "-0.1"})


def test_first_observation_chains_to_registration_and_charges_entry_turnover(
    tmp_path: Path, data_file: Path
) -> None:
    root = tmp_path / "shadow"
    registration = _register(root)

    entry = _append(root, data_file, date(2026, 8, 4))

    assert entry["sequence"] == 1
    assert entry["previous_entry_sha256"] == registration["registration_fingerprint"]
    # Starts flat, so the first session earns nothing and pays a full-size
    # one-way transition into the target.
    assert entry["gross_return"] == "0.000000000000"
    assert entry["turnover"] == "1.000000000000"
    assert entry["cost_contribution"] == "-0.000500000000"
    assert entry["net_return"] == "-0.000500000000"
    assert entry["safety"]["live_authorized"] is False


def test_second_observation_earns_the_prior_target(
    tmp_path: Path, data_file: Path
) -> None:
    root = tmp_path / "shadow"
    _register(root)
    _append(root, data_file, date(2026, 8, 4))

    entry = _append(root, data_file, date(2026, 8, 5))

    assert entry["sequence"] == 2
    # SPY compounds at exactly 1% per session and the target is unchanged, so
    # gross is 1% and turnover is zero.
    assert entry["gross_return"] == "0.010000000000"
    assert entry["turnover"] == "0.000000000000"
    assert entry["net_return"] == "0.010000000000"
    assert entry["benchmark_return"] == "0.010000000000"


def test_ledger_tampering_is_detected(tmp_path: Path, data_file: Path) -> None:
    root = tmp_path / "shadow"
    _register(root)
    _append(root, data_file, date(2026, 8, 4))
    _append(root, data_file, date(2026, 8, 5))
    ledger = root / "observations.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines()

    edited = json.loads(lines[0])
    edited["net_return"] = "0.999000000000"
    ledger.write_text(
        json.dumps(edited, sort_keys=True, separators=(",", ":")) + "\n" + lines[1] + "\n",
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ValidationError, match="entry hash mismatch"):
        subject.load_forward_shadow_state(root)


def test_ledger_truncation_is_detected(tmp_path: Path, data_file: Path) -> None:
    root = tmp_path / "shadow"
    _register(root)
    _append(root, data_file, date(2026, 8, 4))
    _append(root, data_file, date(2026, 8, 5))
    ledger = root / "observations.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines()

    ledger.write_text(lines[1] + "\n", encoding="utf-8", newline="\n")

    with pytest.raises(ValidationError, match="broken sequence|hash chain"):
        subject.load_forward_shadow_state(root)


def test_editing_gates_after_registration_fails_closed(
    tmp_path: Path, data_file: Path
) -> None:
    root = tmp_path / "shadow"
    _register(root)
    _append(root, data_file, date(2026, 8, 4))
    registration_path = root / "registration.json"
    payload = json.loads(registration_path.read_text(encoding="utf-8"))

    payload["gates"]["minimum_sharpe_ratio"] = "-9.000000000000"
    registration_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )

    with pytest.raises(ValidationError, match="registration fingerprint mismatch"):
        subject.load_forward_shadow_state(root)


def test_status_withholds_all_metrics_before_the_window_completes(
    tmp_path: Path, data_file: Path
) -> None:
    root = tmp_path / "shadow"
    _register(root, minimum=5)
    _append(root, data_file, date(2026, 8, 4))
    _append(root, data_file, date(2026, 8, 5))

    packet = subject.evaluate_forward_shadow(
        root, as_of="2026-08-05T22:00:00+00:00"
    )

    assert packet["classification"] == "accruing_untouched_forward_evidence"
    assert packet["verdict_available"] is False
    assert packet["metrics_withheld_until_window_completes"] is True
    assert packet["observation_sessions"] == 2
    assert packet["remaining_sessions"] == 3
    assert "metrics" not in packet
    assert "all_gates_passed" not in packet
    assert "gate_conditions" not in packet
    rendered = subject.render_forward_shadow_markdown(packet)
    assert "withheld until the frozen window completes" in rendered
    assert "Annualized return" not in rendered


def test_completed_window_produces_a_scored_verdict(
    tmp_path: Path, data_file: Path
) -> None:
    root = tmp_path / "shadow"
    _register(root, minimum=3)
    for offset in range(3):
        _append(root, data_file, date(2026, 8, 4) + timedelta(days=offset))

    packet = subject.evaluate_forward_shadow(
        root, as_of="2026-08-07T22:00:00+00:00"
    )

    assert packet["verdict_available"] is True
    assert packet["classification"].startswith("forward_evidence_complete_")
    metrics = packet["metrics"]
    assert metrics["session_count"] == 3
    assert metrics["first_session"] == "2026-08-04"
    assert metrics["last_session"] == "2026-08-06"
    # SPY compounds 1% on each of the three sessions.
    assert metrics["benchmark_total_return"] == "0.030301000000"
    # The rule holds SPY but starts flat, so it forgoes the first session's
    # move and pays the entry transition: 0.9995 * 1.01 * 1.01 - 1.
    assert metrics["total_return"] == "0.019589950000"
    assert metrics["benchmark_annualized_return_delta"].startswith("-")
    assert packet["paper_promotion_allowed"] is False
    assert packet["live_authorized"] is False
    assert (root / "status.json").is_file()
    assert (root / "status.md").is_file()


def test_state_load_requires_registration_and_ledger(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="registration is missing"):
        subject.load_forward_shadow_state(tmp_path / "absent")


def test_cli_policy_and_status_round_trip(
    tmp_path: Path, data_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "shadow"
    _register(root, minimum=4)
    _append(root, data_file, date(2026, 8, 4))

    assert subject.main(["policy"]) == 0
    policy = json.loads(capsys.readouterr().out)
    assert policy["policy_fingerprint"] == subject.FORWARD_SHADOW_POLICY_FINGERPRINT

    assert (
        subject.main(
            ["status", "--root", str(root), "--as-of", "2026-08-04T22:00:00+00:00"]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "accruing" in out
    assert "withheld" in out

    assert subject.main(["status", "--root", str(tmp_path / "absent"), "--as-of", REGISTERED_AT]) == 2
    assert "forward_shadow_status=blocked" in capsys.readouterr().out
