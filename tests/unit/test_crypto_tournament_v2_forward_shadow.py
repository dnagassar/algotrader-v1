from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.crypto_preregistered_tournament_v2 import (
    CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT,
    build_crypto_tournament_v2_preregistration,
)
from algotrader.research.crypto_tournament_v2_forward_shadow import (
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT,
    FORWARD_SHADOW_HOURLY_BARS,
    build_crypto_tournament_v2_forward_shadow_activation,
    build_crypto_tournament_v2_forward_shadow_preregistration,
    render_crypto_tournament_v2_forward_shadow_markdown,
    run_crypto_tournament_v2_forward_shadow_readiness,
    validate_crypto_tournament_v2_forward_shadow_activation,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    PROJECT_ROOT / "scripts" / "run_crypto_tournament_v2_forward_shadow.ps1"
)


def _waiting_packet() -> dict[str, object]:
    return {
        "classification": "collecting_untouched_oos",
        "preregistration_fingerprint": (
            CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT
        ),
        "frozen_state": {
            "terminal_outcome_closed": False,
            "terminal_classification": "",
            "terminal_closed_at": "",
            "terminal_packet_sha256": "",
            "terminal_scoring_performed": False,
            "terminal_evidence_fingerprint": "",
            "state_fingerprint": "a" * 64,
        },
        "terminal_scoring_performed": False,
        "terminal_evidence_fingerprint": "",
        "selected_candidate": {},
        "broker_read_occurred": False,
        "paper_or_broker_eligible": False,
        "paper_planning_eligibility": "not_eligible",
        "paper_or_live_execution_authorized": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "paper_cancel_occurred": False,
        "paper_replace_occurred": False,
        "paper_close_occurred": False,
        "paper_liquidate_occurred": False,
        "live_authorized": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "profit_claim": "none",
    }


def _terminal_packet(
    *,
    classification: str = "eligible_for_no_submit_shadow_evaluation",
    closed_at: str = "2026-08-13T00:00:00+00:00",
) -> dict[str, object]:
    packet = _waiting_packet()
    evidence_fingerprint = "b" * 64
    scoring = classification != "terminal_input_quality_gate"
    packet.update(
        {
            "classification": classification,
            "terminal_scoring_performed": scoring,
            "terminal_evidence_fingerprint": evidence_fingerprint,
            "terminal_closure": {
                "terminal_outcome_closed": True,
                "terminal_classification": classification,
                "terminal_closed_at": closed_at,
                "terminal_scoring_performed": scoring,
                "terminal_evidence_fingerprint": evidence_fingerprint,
            },
        }
    )
    packet["frozen_state"] = {
        "terminal_outcome_closed": True,
        "terminal_classification": classification,
        "terminal_closed_at": closed_at,
        "terminal_packet_sha256": "c" * 64,
        "terminal_scoring_performed": scoring,
        "terminal_evidence_fingerprint": evidence_fingerprint,
        "state_fingerprint": "d" * 64,
    }
    if classification == "eligible_for_no_submit_shadow_evaluation":
        candidate = build_crypto_tournament_v2_preregistration()["candidates"][0]
        packet["selected_candidate"] = {
            "candidate_id": candidate["candidate_id"],
            "candidate_fingerprint": candidate["candidate_fingerprint"],
            "candidate_decision": classification,
            "selection_scope": classification,
            "paper_or_broker_eligible": False,
        }
    else:
        packet["selected_candidate"] = {}
    return packet


def test_preregistration_is_locked_before_candidate_selection() -> None:
    contract = build_crypto_tournament_v2_forward_shadow_preregistration()

    assert contract["preregistration_fingerprint"] == (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT
    )
    assert contract["temporal_policy"]["hourly_bars"] == 168
    assert contract["temporal_policy"]["window_extension_allowed"] is False
    assert contract["strategy_policy"]["candidate_parameters_mutable"] is False
    assert contract["authority_boundary"] == {
        "network_access_authorized": False,
        "broker_read_authorized": False,
        "broker_mutation_authorized": False,
        "paper_planning_authorized": False,
        "paper_mutation_authorized": False,
        "capital_allocation_authorized": False,
        "live_endpoint_authorized": False,
        "live_trading_authorized": False,
        "operator_review_required_after_terminal_shadow": True,
    }


def test_nonterminal_tournament_waits_without_minting_activation() -> None:
    packet = build_crypto_tournament_v2_forward_shadow_activation(
        _waiting_packet(),
        as_of="2026-07-16T01:00:00Z",
    )

    assert packet["classification"] == "waiting_for_tournament_terminal"
    assert packet["principal_blocker"] == (
        "tournament_v2_untouched_oos_not_terminal"
    )
    assert packet["selected_candidate"] == {}
    assert packet["activation_fingerprint"] == ""
    assert packet["paper_or_broker_eligible"] is False
    assert packet["capital_allocation_authorized"] is False


def test_sealed_winner_binds_exact_candidate_and_future_window() -> None:
    packet = build_crypto_tournament_v2_forward_shadow_activation(
        _terminal_packet(),
        as_of="2026-08-13T00:00:00Z",
    )

    assert packet["classification"] == (
        "ready_to_activate_no_submit_forward_shadow"
    )
    assert packet["principal_blocker"] == "none"
    assert packet["selected_candidate"]["candidate_id"].startswith(
        "crypto:tournament_v2:BTCUSD:"
    )
    assert packet["shadow_window"] == {
        "status": "frozen_untouched_future_window",
        "start": "2026-08-13T00:00:00+00:00",
        "end_exclusive": "2026-08-20T00:00:00+00:00",
        "hourly_bars": FORWARD_SHADOW_HOURLY_BARS,
        "checkpoint_hours": [24, 72, 168],
    }
    assert len(packet["activation_fingerprint"]) == 64
    assert packet["paper_or_live_execution_authorized"] is False


def test_delayed_terminal_close_starts_at_next_complete_hour() -> None:
    packet = build_crypto_tournament_v2_forward_shadow_activation(
        _terminal_packet(closed_at="2026-08-13T00:07:00+00:00"),
        as_of="2026-08-13T00:07:00Z",
    )

    assert packet["shadow_window"]["start"] == "2026-08-13T01:00:00+00:00"
    assert packet["shadow_window"]["end_exclusive"] == (
        "2026-08-20T01:00:00+00:00"
    )


@pytest.mark.parametrize(
    "classification",
    ("no_candidate_qualified", "terminal_input_quality_gate"),
)
def test_terminal_without_winner_closes_without_shadow(
    classification: str,
) -> None:
    packet = build_crypto_tournament_v2_forward_shadow_activation(
        _terminal_packet(classification=classification),
        as_of="2026-08-13T00:00:00Z",
    )

    assert packet["classification"] == "closed_without_shadow_candidate"
    assert packet["principal_blocker"] == "tournament_v2_produced_no_winner"
    assert packet["selected_candidate"] == {}
    assert packet["activation_fingerprint"] == ""


def test_rejects_selected_candidate_fingerprint_tampering() -> None:
    source = _terminal_packet()
    source["selected_candidate"]["candidate_fingerprint"] = "e" * 64

    with pytest.raises(ValidationError, match="frozen v2 manifest"):
        build_crypto_tournament_v2_forward_shadow_activation(
            source,
            as_of="2026-08-13T00:00:00Z",
        )


def test_rejects_terminal_evidence_binding_tampering() -> None:
    source = _terminal_packet()
    source["frozen_state"]["terminal_evidence_fingerprint"] = "e" * 64

    with pytest.raises(ValidationError, match="evidence fingerprint mismatch"):
        build_crypto_tournament_v2_forward_shadow_activation(
            source,
            as_of="2026-08-13T00:00:00Z",
        )


def test_rejects_any_source_mutation_authority() -> None:
    source = _terminal_packet()
    source["paper_submit_authorized"] = True

    with pytest.raises(ValidationError, match="paper_submit_authorized"):
        build_crypto_tournament_v2_forward_shadow_activation(
            source,
            as_of="2026-08-13T00:00:00Z",
        )


def test_rejects_source_broker_read_activity() -> None:
    source = _terminal_packet()
    source["broker_read_occurred"] = True

    with pytest.raises(ValidationError, match="broker_read_occurred"):
        build_crypto_tournament_v2_forward_shadow_activation(
            source,
            as_of="2026-08-13T00:00:00Z",
        )


def test_rejects_eligible_terminal_with_consistently_false_scoring() -> None:
    source = _terminal_packet()
    source["terminal_scoring_performed"] = False
    source["frozen_state"]["terminal_scoring_performed"] = False
    source["terminal_closure"]["terminal_scoring_performed"] = False

    with pytest.raises(ValidationError, match="requires terminal scoring"):
        build_crypto_tournament_v2_forward_shadow_activation(
            source,
            as_of="2026-08-13T00:00:00Z",
        )


def test_activation_identity_binds_source_state_fingerprint() -> None:
    first = build_crypto_tournament_v2_forward_shadow_activation(
        _terminal_packet(),
        as_of="2026-08-13T00:00:00Z",
    )
    changed_source = _terminal_packet()
    changed_source["frozen_state"]["state_fingerprint"] = "e" * 64
    second = build_crypto_tournament_v2_forward_shadow_activation(
        changed_source,
        as_of="2026-08-13T00:00:00Z",
    )

    assert first["activation_fingerprint"] != second["activation_fingerprint"]
    tampered = dict(first)
    tampered["source_binding"] = dict(first["source_binding"])
    tampered["source_binding"]["state_fingerprint"] = "f" * 64
    with pytest.raises(ValidationError, match="activation fingerprint mismatch"):
        validate_crypto_tournament_v2_forward_shadow_activation(tampered)


def test_rejects_refingerprinted_later_shadow_window_start() -> None:
    activation = build_crypto_tournament_v2_forward_shadow_activation(
        _terminal_packet(),
        as_of="2026-08-13T00:00:00Z",
    )
    source = activation["source_binding"]
    candidate = activation["selected_candidate"]
    window = dict(activation["shadow_window"])
    window["start"] = "2026-08-13T01:00:00+00:00"
    window["end_exclusive"] = "2026-08-20T01:00:00+00:00"
    tampered = dict(activation)
    tampered["shadow_window"] = window
    basis = {
        "forward_shadow_preregistration_fingerprint": tampered[
            "preregistration_fingerprint"
        ],
        "source_terminal_packet_sha256": source["terminal_packet_sha256"],
        "source_terminal_evidence_fingerprint": source[
            "terminal_evidence_fingerprint"
        ],
        "source_state_fingerprint": source["state_fingerprint"],
        "selected_candidate_id": candidate["candidate_id"],
        "selected_candidate_fingerprint": candidate["candidate_fingerprint"],
        "start": window["start"],
        "end_exclusive": window["end_exclusive"],
        "hourly_bars": FORWARD_SHADOW_HOURLY_BARS,
    }
    tampered["activation_fingerprint"] = hashlib.sha256(
        json.dumps(
            basis,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()

    with pytest.raises(ValidationError, match="must equal the first eligible"):
        validate_crypto_tournament_v2_forward_shadow_activation(tampered)


def test_runner_writes_only_local_offline_readiness_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import algotrader.research.crypto_tournament_v2_forward_shadow as subject

    monkeypatch.setattr(
        subject,
        "run_crypto_tournament_v2_forward_oos",
        lambda **_: _waiting_packet(),
    )
    output_root = tmp_path / "shadow"

    packet = run_crypto_tournament_v2_forward_shadow_readiness(
        tournament_root=tmp_path / "tournament",
        output_root=output_root,
        as_of="2026-07-16T01:00:00Z",
    )

    assert packet["classification"] == "waiting_for_tournament_terminal"
    assert json.loads(
        (output_root / "readiness_packet.json").read_text(encoding="utf-8")
    ) == packet
    assert (output_root / "preregistration.json").is_file()
    assert (output_root / "readiness_packet.md").is_file()


def test_markdown_and_wrapper_keep_scope_explicit() -> None:
    packet = build_crypto_tournament_v2_forward_shadow_activation(
        _waiting_packet(),
        as_of="2026-07-16T01:00:00Z",
    )
    rendered = render_crypto_tournament_v2_forward_shadow_markdown(packet)
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "waiting_for_tournament_terminal" in rendered
    assert "Paper/capital authorization: none" in rendered
    assert "APP_PROFILE -eq \"paper\"" in script
    assert "ALPACA_API_SECRET_KEY" in script
    assert "--as-of" in script
    assert "MarketDataFetchAuthorized" not in script
    assert "AllowNetwork" not in script
