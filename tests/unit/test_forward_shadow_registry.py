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
        gates=subject.ForwardShadowGates(minimum_decisions=minimum),
        registered_at=REGISTERED_AT,
    )


def _append(
    root: Path,
    data_file: Path,
    session: date,
    targets: dict[str, str] | None = None,
    recorded_at: str | None = None,
    is_decision: bool = True,
) -> dict:
    return subject.append_forward_shadow_observation(
        root,
        session=session,
        targets=targets if targets is not None else {"SPY": "1"},
        canonical_data_path=data_file,
        recorded_at=recorded_at or f"{session.isoformat()}T21:00:00+00:00",
        is_decision=is_decision,
    )


def test_policy_fingerprint_is_frozen_and_zero_authority() -> None:
    policy = subject.build_forward_shadow_policy()

    assert policy["policy_fingerprint"] == subject.FORWARD_SHADOW_POLICY_FINGERPRINT
    assert policy["power_policy"]["session_count_is_not_evidence"] is True
    assert policy["sequential_policy"]["boundaries_frozen_at_registration"] is True
    assert policy["multiplicity_policy"]["members_beyond_planned_count_refused"] is True
    assert policy["temporal_policy"]["backfill_allowed"] is False
    assert policy["temporal_policy"]["future_session_allowed"] is False
    assert (
        policy["evaluation_policy"]["verdict_before_stopping_condition"]
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
            gates=subject.ForwardShadowGates(minimum_decisions=2),
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
    assert packet["metrics_withheld_until_stopping_condition"] is True
    assert packet["observation_sessions"] == 2
    assert packet["completed_decision_intervals"] == 1
    assert packet["remaining_decisions"] == 4
    assert "metrics" not in packet
    assert "all_gates_passed" not in packet
    assert "gate_conditions" not in packet
    rendered = subject.render_forward_shadow_markdown(packet)
    assert "withheld until a frozen stopping condition" in rendered
    assert "Annualized return" not in rendered


def test_completed_window_produces_a_scored_verdict(
    tmp_path: Path, data_file: Path
) -> None:
    root = tmp_path / "shadow"
    _register(root, minimum=2)
    for offset in range(3):
        _append(root, data_file, date(2026, 8, 4) + timedelta(days=offset))

    packet = subject.evaluate_forward_shadow(
        root, as_of="2026-08-07T22:00:00+00:00"
    )

    assert packet["verdict_available"] is True
    assert packet["classification"].startswith("forward_evidence_complete_")
    metrics = packet["metrics"]
    assert metrics["session_count"] == 3
    assert metrics["completed_decision_intervals"] == 2
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


# --- decision-count gating -------------------------------------------------


def _register_custom(
    root: Path,
    *,
    minimum: int = 3,
    benchmark: str = "SPY",
    sequential: subject.SequentialBoundaries | None = None,
    cohort_root: Path | None = None,
) -> dict:
    return subject.register_forward_shadow(
        root,
        hypothesis_id="custom_hypothesis",
        hypothesis_statement="Configurable hypothesis for boundary tests.",
        universe=UNIVERSE,
        benchmark_symbol=benchmark,
        rule_reference="docs/design/example.md",
        rule_fingerprint=RULE_FINGERPRINT,
        gates=subject.ForwardShadowGates(
            minimum_decisions=minimum,
            sequential=sequential or subject.SequentialBoundaries(),
        ),
        registered_at=REGISTERED_AT,
        cohort_root=cohort_root,
    )


def test_holding_sessions_do_not_manufacture_decisions(
    tmp_path: Path, data_file: Path
) -> None:
    """A monthly rule observed for many days has still made few decisions."""

    root = tmp_path / "shadow"
    _register(root, minimum=4)
    _append(root, data_file, date(2026, 8, 4), is_decision=True)
    for offset in (5, 6):
        _append(root, data_file, date(2026, 8, offset), is_decision=False)
    _append(root, data_file, date(2026, 8, 7), is_decision=True)

    packet = subject.evaluate_forward_shadow(
        root, as_of="2026-08-07T22:00:00+00:00", write_artifacts=False
    )

    assert packet["observation_sessions"] == 4
    assert packet["decision_sessions"] == 2
    # Four sessions, but only one completed decision interval of evidence.
    assert packet["completed_decision_intervals"] == 1
    assert packet["remaining_decisions"] == 3
    assert packet["verdict_available"] is False


def test_first_observation_must_be_a_decision(
    tmp_path: Path, data_file: Path
) -> None:
    root = tmp_path / "shadow"
    _register(root)

    with pytest.raises(ValidationError, match="first observation must be a decision"):
        _append(root, data_file, date(2026, 8, 4), is_decision=False)


def test_non_decision_session_cannot_change_targets(
    tmp_path: Path, data_file: Path
) -> None:
    root = tmp_path / "shadow"
    _register(root)
    _append(root, data_file, date(2026, 8, 4))

    with pytest.raises(ValidationError, match="cannot change the target weights"):
        _append(
            root,
            data_file,
            date(2026, 8, 5),
            targets={"AGG": "1"},
            is_decision=False,
        )


def test_is_decision_must_be_explicit(tmp_path: Path, data_file: Path) -> None:
    root = tmp_path / "shadow"
    _register(root)

    with pytest.raises(ValidationError, match="explicit boolean"):
        subject.append_forward_shadow_observation(
            root,
            session=date(2026, 8, 4),
            targets={"SPY": "1"},
            canonical_data_path=data_file,
            recorded_at="2026-08-04T21:00:00+00:00",
            is_decision="yes",
        )


# --- sequential boundaries -------------------------------------------------


_FAST_FUTILITY = subject.SequentialBoundaries(
    minimum_excess_per_decision="0.020000000000",
    reference_excess_sigma="0.020000000000",
    minimum_decisions_before_stopping=3,
)
_FAST_EFFICACY = subject.SequentialBoundaries(
    minimum_excess_per_decision="0.005000000000",
    reference_excess_sigma="0.005000000000",
    minimum_decisions_before_stopping=2,
)


def test_futility_boundary_stops_a_losing_hypothesis_early(
    tmp_path: Path, data_file: Path
) -> None:
    """The point of the whole design: kill a dead hypothesis without waiting."""

    root = tmp_path / "shadow"
    # Benchmark SPY rises 1%/session; the rule sits in flat AGG and loses to it.
    _register_custom(root, minimum=50, sequential=_FAST_FUTILITY)
    for offset in range(4, 9):
        _append(root, data_file, date(2026, 8, offset), targets={"AGG": "1"})

    packet = subject.evaluate_forward_shadow(
        root, as_of="2026-08-09T22:00:00+00:00", write_artifacts=False
    )

    assert packet["classification"] == "stopped_early_for_futility"
    assert packet["stopping_reason"] == "futility"
    assert packet["verdict_available"] is True
    assert packet["all_gates_passed"] is False
    assert packet["next_action"] == "close_hypothesis_without_tuning"
    # It stopped far short of the 50 decisions the fixed window demanded.
    assert packet["completed_decision_intervals"] < 50
    assert packet["paper_promotion_allowed"] is False


def test_efficacy_boundary_stops_a_winning_hypothesis_early(
    tmp_path: Path, data_file: Path
) -> None:
    root = tmp_path / "shadow"
    # Benchmark AGG is flat; the rule holds SPY and beats it every session.
    _register_custom(
        root, minimum=50, benchmark="AGG", sequential=_FAST_EFFICACY
    )
    for offset in range(4, 9):
        _append(root, data_file, date(2026, 8, offset), targets={"SPY": "1"})

    packet = subject.evaluate_forward_shadow(
        root, as_of="2026-08-09T22:00:00+00:00", write_artifacts=False
    )

    assert packet["classification"] == "stopped_early_for_efficacy"
    assert packet["stopping_reason"] == "efficacy"
    assert packet["verdict_available"] is True
    assert packet["completed_decision_intervals"] < 50
    # Even a clean efficacy stop authorizes nothing on its own.
    assert packet["paper_promotion_allowed"] is False
    assert packet["live_authorized"] is False


def test_no_boundary_fires_before_the_frozen_minimum(
    tmp_path: Path, data_file: Path
) -> None:
    root = tmp_path / "shadow"
    patient = subject.SequentialBoundaries(
        minimum_excess_per_decision="0.020000000000",
        reference_excess_sigma="0.020000000000",
        minimum_decisions_before_stopping=25,
    )
    _register_custom(root, minimum=50, sequential=patient)
    for offset in range(4, 9):
        _append(root, data_file, date(2026, 8, offset), targets={"AGG": "1"})

    packet = subject.evaluate_forward_shadow(
        root, as_of="2026-08-09T22:00:00+00:00", write_artifacts=False
    )

    # The evidence has crossed the futility line, but stopping is not yet
    # permitted, so no verdict and no metrics leak.
    assert float(packet["sequential_state"]["log_likelihood_ratio"]) < float(
        packet["sequential_state"]["futility_boundary"]
    )
    assert packet["sequential_state"]["boundary_crossed"] is None
    assert packet["classification"] == "accruing_untouched_forward_evidence"
    assert packet["verdict_available"] is False
    assert "metrics" not in packet


def test_sequential_boundaries_reject_invalid_parameters() -> None:
    with pytest.raises(ValidationError, match="alpha must lie strictly"):
        subject.SequentialBoundaries(alpha="1.500000000000")
    with pytest.raises(
        ValidationError, match="reference_excess_sigma must be positive"
    ):
        subject.SequentialBoundaries(reference_excess_sigma="0")
    with pytest.raises(
        ValidationError, match="minimum_excess_per_decision must be positive"
    ):
        subject.SequentialBoundaries(minimum_excess_per_decision="0")
    with pytest.raises(ValidationError, match="minimum_decisions_before_stopping"):
        subject.SequentialBoundaries(minimum_decisions_before_stopping=0)


# --- cohort multiplicity ---------------------------------------------------


def test_cohort_bonferroni_tightens_effective_alpha(tmp_path: Path) -> None:
    cohort_root = tmp_path / "cohort"
    subject.register_forward_shadow_cohort(
        cohort_root,
        cohort_id="parallel_batch",
        planned_member_count=4,
        family_wise_alpha="0.050000000000",
        registered_at=REGISTERED_AT,
    )

    registration = _register_custom(
        tmp_path / "member_a", cohort_root=cohort_root
    )
    binding = registration["cohort_binding"]

    assert binding["cohort_id"] == "parallel_batch"
    assert binding["planned_member_count"] == 4
    assert binding["correction"] == "bonferroni"
    assert binding["effective_alpha"] == "0.012500000000"


def test_cohort_refuses_more_members_than_planned(tmp_path: Path) -> None:
    cohort_root = tmp_path / "cohort"
    subject.register_forward_shadow_cohort(
        cohort_root,
        cohort_id="small_batch",
        planned_member_count=2,
        registered_at=REGISTERED_AT,
    )
    for index in range(2):
        subject.register_forward_shadow(
            tmp_path / f"member_{index}",
            hypothesis_id=f"hypothesis_{index}",
            hypothesis_statement="statement",
            universe=UNIVERSE,
            benchmark_symbol="SPY",
            rule_reference="ref",
            rule_fingerprint=RULE_FINGERPRINT,
            gates=subject.ForwardShadowGates(minimum_decisions=3),
            registered_at=REGISTERED_AT,
            cohort_root=cohort_root,
        )

    with pytest.raises(ValidationError, match="cohort is full"):
        subject.register_forward_shadow(
            tmp_path / "member_overflow",
            hypothesis_id="hypothesis_overflow",
            hypothesis_statement="statement",
            universe=UNIVERSE,
            benchmark_symbol="SPY",
            rule_reference="ref",
            rule_fingerprint=RULE_FINGERPRINT,
            gates=subject.ForwardShadowGates(minimum_decisions=3),
            registered_at=REGISTERED_AT,
            cohort_root=cohort_root,
        )


def test_cohort_registration_is_immutable(tmp_path: Path) -> None:
    cohort_root = tmp_path / "cohort"
    subject.register_forward_shadow_cohort(
        cohort_root,
        cohort_id="one",
        planned_member_count=1,
        registered_at=REGISTERED_AT,
    )

    with pytest.raises(ValidationError, match="already registered"):
        subject.register_forward_shadow_cohort(
            cohort_root,
            cohort_id="one",
            planned_member_count=99,
            registered_at=REGISTERED_AT,
        )


def test_editing_cohort_binding_after_registration_fails_closed(
    tmp_path: Path,
) -> None:
    cohort_root = tmp_path / "cohort"
    subject.register_forward_shadow_cohort(
        cohort_root,
        cohort_id="batch",
        planned_member_count=8,
        registered_at=REGISTERED_AT,
    )
    root = tmp_path / "member"
    _register_custom(root, cohort_root=cohort_root)
    registration_path = root / "registration.json"
    payload = json.loads(registration_path.read_text(encoding="utf-8"))

    # Loosen the multiplicity correction after the fact.
    payload["cohort_binding"]["effective_alpha"] = "0.050000000000"
    registration_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ValidationError, match="registration fingerprint mismatch"):
        subject.load_forward_shadow_state(root)
