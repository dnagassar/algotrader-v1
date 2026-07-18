from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal
import json
from pathlib import Path
import runpy
import hashlib

import pytest

from algotrader.core.crypto_bounded_probe_lifecycle import (
    BUDGETS,
    SAFETY_POLICY_FINGERPRINT,
    build_dormant_lifecycle_plan,
    build_ready_lifecycle_plan,
    exact_operation_authorization_text,
    stable_hash,
    validate_lifecycle_plan,
)
from algotrader.core.paper_account_binding import (
    build_alpaca_paper_account_binding,
)
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import AlpacaOrderRequest
from algotrader.orchestration import (
    crypto_tournament_v2_bounded_paper_probe_lifecycle as lifecycle_subject,
)
from algotrader.orchestration.crypto_tournament_v2_bounded_paper_probe_lifecycle import (
    build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan,
    run_crypto_tournament_v2_bounded_paper_probe_lifecycle_planner,
)


NOW = datetime(2026, 8, 13, 0, 5, tzinfo=UTC)
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


VENUE_ROLES = (
    "venue_refresh_manifest",
    "venue_universe",
    "orderability_metadata",
    "venue_router_input_manifest",
    "venue_runtime_visibility_status",
    "venue_refresh_source",
    "venue_visibility_operator_source",
    "venue_supervisor_source",
)


def _candidate(symbol: str) -> dict[str, object]:
    unsigned: dict[str, object] = {
        "candidate_id": (
            f"crypto:tournament_v2:{symbol}:trend_momentum_72h"
        ),
        "symbol": symbol,
        "strategy_id": "trend_momentum_72h",
        "strategy_family": "trend_momentum",
        "elapsed_hour_parameters": {"lookback_hours": 72},
        "primary_1h_parameters": {"lookback_bars": 72},
        "robustness_4h_parameters": {"lookback_bars": 18},
        "direction": "long_or_cash",
        "signal_execution": "one_bar_lag",
        "imputed_bar_transition_policy": (
            "hold_prior_target_no_transition"
        ),
        "factory_version": "unit-test-v2",
    }
    return {
        **unsigned,
        "candidate_fingerprint": stable_hash(unsigned),
    }


def _orderability_record(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "asset_class": "crypto",
        "source_mode": "paper_read_only",
        "broker_state_mode": "alpaca_paper_observed",
        "tradable": True,
        "status": "active",
        "min_notional": "1",
        "min_order_notional": "1",
        "min_order_size": "0.000001",
        "min_trade_increment": "0.000001",
        "price_increment": "0.01",
        "qty_increment": "0.000001",
        "broker_observed_min_notional": "1",
        "broker_observed_min_order_size": "0.000001",
        "broker_observed_min_trade_increment": "0.000001",
        "broker_observed_price_increment": "0.01",
        "derived_min_order_value": "1",
        "orderability_basis": "broker_notional_and_qty_metadata",
        "metadata_status": "metadata_observed",
        "metadata_blockers": [],
        "orderability_status": "notional_orderable",
        "orderability_blockers": [],
    }


def _ready_plan(symbol: str) -> dict[str, object]:
    return build_ready_lifecycle_plan(
        symbol=symbol,
        terminal_binding={
            "selected_symbol": symbol,
            "selected_candidate": _candidate(symbol),
            "classification": (
                "evidence_complete_for_bounded_paper_probe_review"
            ),
            "preregistration_fingerprint": SHA_A,
            "activation_fingerprint": SHA_B,
            "state_fingerprint": SHA_C,
            "terminal_evidence_fingerprint": SHA_A,
            "terminal_closed_at": "2026-08-13T00:00:00+00:00",
            "evidence_export_fingerprint": SHA_B,
            "terminal_source_sha256": SHA_C,
        },
        venue_binding={
            "target_symbol": symbol,
            "observed_at": NOW.isoformat(),
            "bundle_fingerprint": SHA_A,
            "resolved_source_digests": {
                role: SHA_B for role in VENUE_ROLES
            },
            "orderability_record": _orderability_record(symbol),
        },
        safety_binding={
            "policy_fingerprint": SAFETY_POLICY_FINGERPRINT,
            "certification_receipt_fingerprint": SHA_A,
            "certification_source_sha256": SHA_B,
            "kernel_source_sha256": SHA_C,
            "certifier_source_sha256": SHA_A,
            "focused_test_source_sha256": SHA_B,
            "runtime_source_bundle_sha256": SHA_C,
            "certified_at": NOW.isoformat(),
        },
        account_binding=build_alpaca_paper_account_binding(
            {"account_id": "expected-paper-account"},
            expected_account_configured=True,
            expected_account_matched=True,
        ),
        as_of=NOW,
    )


def test_planner_is_dormant_before_terminal_without_resolving_inputs() -> None:
    plan = build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan(
        None,
        venue_source_bytes={"orderability_metadata": b"not-json"},
        safety_certification={"not": "valid"},
        expected_paper_account_id="not-consumed-before-winner",
        as_of=NOW,
    )

    assert plan == build_dormant_lifecycle_plan(NOW)
    assert plan["classification"] == "dormant_pending_terminal_winner"
    assert plan["deterministic_ids"] == {}
    assert plan["authority"]["paper_mutation_authorized"] is False


def test_ready_planner_binds_exact_pretty_terminal_and_safety_bytes(
    tmp_path: Path,
) -> None:
    helpers = runpy.run_path(
        str(
            Path(__file__).with_name(
                "test_crypto_tournament_v2_capability_producer.py"
            )
        )
    )
    raw = {
        **helpers["_build_safety_sources"](),
        **helpers["_build_venue_sources"](tmp_path),
    }
    terminal = helpers["TERMINAL_EVIDENCE"](symbol="BTCUSD")
    terminal_bytes = (
        json.dumps(terminal, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    safety_bytes = raw["safety_certification_receipt"]
    safety_receipt = json.loads(safety_bytes)
    venue_roles = (
        "venue_refresh_manifest",
        "venue_universe",
        "orderability_metadata",
        "venue_router_input_manifest",
        "venue_runtime_visibility_status",
        "venue_refresh_source",
        "venue_visibility_operator_source",
        "venue_supervisor_source",
    )

    plan = build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan(
        terminal,
        venue_source_bytes={role: raw[role] for role in venue_roles},
        safety_certification=safety_receipt,
        safety_certification_source_sha256=hashlib.sha256(
            safety_bytes
        ).hexdigest(),
        safety_kernel_source_bytes=raw["safety_kernel_source"],
        safety_certifier_source_bytes=raw["safety_certifier_source"],
        safety_focused_test_source_bytes=raw["safety_focused_test_source"],
        expected_paper_account_id="expected-paper-account",
        terminal_source_sha256=hashlib.sha256(terminal_bytes).hexdigest(),
        as_of=helpers["AS_OF"],
    )

    validate_lifecycle_plan(plan)
    assert plan["classification"] == "ready_for_exact_operation_authorization"
    assert plan["subject"]["symbol"] == "BTCUSD"
    assert plan["terminal_binding"]["terminal_source_sha256"] == (
        hashlib.sha256(terminal_bytes).hexdigest()
    )
    assert plan["safety_binding"]["certification_source_sha256"] == (
        hashlib.sha256(safety_bytes).hexdigest()
    )
@pytest.mark.parametrize("symbol", ("BTCUSD", "ETHUSD", "SOLUSD"))
def test_ready_plan_binds_exact_winner_account_and_one_shot_ids(
    symbol: str,
) -> None:
    plan = _ready_plan(symbol)

    validate_lifecycle_plan(plan)
    authorization = exact_operation_authorization_text(plan)

    assert plan["subject"]["symbol"] == symbol
    assert plan["budgets"] == BUDGETS
    assert plan["entry_notional_usd"] == "10"
    assert plan["time_in_force"] == "gtc"
    assert plan["authority"]["paper_mutation_authorized"] is False
    assert f"symbol={symbol}" in authorization
    assert "entry_usd=10" in authorization
    assert hashlib.sha256(authorization.encode()).hexdigest() == (
        plan["required_authorization_sha256"]
    )


def test_plan_tamper_fails_even_after_outer_fingerprint_is_unchanged() -> None:
    plan = _ready_plan("ETHUSD")
    plan["entry_notional_usd"] = "11"

    with pytest.raises(ValidationError, match="fingerprint mismatch"):
        validate_lifecycle_plan(plan)


@pytest.mark.parametrize("symbol", ("BTCUSD", "ETHUSD", "SOLUSD"))
def test_v530_request_namespace_allows_only_exact_market_gtc_shapes(
    symbol: str,
) -> None:
    plan = _ready_plan(symbol)
    ids = plan["deterministic_ids"]

    entry = AlpacaOrderRequest(
        client_order_id=ids["entry_client_order_id"],
        symbol=symbol,
        side="buy",
        asset_class="crypto",
        notional=Decimal("10"),
        order_type="market",
        time_in_force="gtc",
    )
    exit_request = AlpacaOrderRequest(
        client_order_id=ids["exit_client_order_id"],
        symbol=symbol,
        side="sell",
        asset_class="crypto",
        qty=Decimal("0.01"),
        order_type="market",
        time_in_force="gtc",
    )

    assert entry.notional == Decimal("10")
    assert exit_request.qty == Decimal("0.01")


@pytest.mark.parametrize(
    ("side", "notional", "qty", "time_in_force"),
    (
        ("buy", Decimal("9"), None, "gtc"),
        ("buy", Decimal("10"), None, "ioc"),
        ("sell", None, Decimal("0.01"), "ioc"),
    ),
)
def test_v530_request_namespace_rejects_shape_drift(
    side: str,
    notional: Decimal | None,
    qty: Decimal | None,
    time_in_force: str,
) -> None:
    plan = _ready_plan("SOLUSD")
    ids = plan["deterministic_ids"]

    with pytest.raises(ValueError):
        AlpacaOrderRequest(
            client_order_id=(
                ids["entry_client_order_id"]
                if side == "buy"
                else ids["exit_client_order_id"]
            ),
            symbol="SOLUSD",
            side=side,
            asset_class="crypto",
            notional=notional,
            qty=qty,
            order_type="market",
            time_in_force=time_in_force,
        )


@pytest.mark.parametrize(
    (
        "client_order_id", "symbol", "side", "notional", "qty",
    ),
    (
        ("v530-bounded-probe-btcusd-entry-aaaaaaaaaaaaaaaa", "SOLUSD", "buy", Decimal("10"), None),
        ("v530-bounded-probe-btcusd-entry-aaaaaaaaaaaaaaaa", "BTCUSD", "sell", None, Decimal("0.01")),
        (
            "v530-bounded-probe-btcusd-exit-aaaaaaaaaaaaaaaa",
            "BTCUSD",
            "buy",
            Decimal("10"),
            None,
        ),
        ("v530-bounded-probe-btcusd-entry-gggggggggggggggg", "BTCUSD", "buy", Decimal("10"), None),
        ("v530-bounded-probe-btcusd-entry-aaaaaaaaaaaaaaa", "BTCUSD", "buy", Decimal("10"), None),
        ("v530-bounded-probe-btcusd-entry-AAAAAAAAAAAAAAAA", "BTCUSD", "buy", Decimal("10"), None),
    ),
)
def test_v530_request_namespace_rejects_identity_drift(
    client_order_id: str,
    symbol: str,
    side: str,
    notional: Decimal | None,
    qty: Decimal | None,
) -> None:
    with pytest.raises(ValueError, match="V5.30 bounded-probe request shape"):
        AlpacaOrderRequest(
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            asset_class="crypto",
            notional=notional,
            qty=qty,
            order_type="market",
            time_in_force="gtc",
        )


def test_ready_plan_rejects_rehashed_placeholder_provenance() -> None:
    plan = _ready_plan("BTCUSD")
    plan["terminal_binding"] = {
        "classification": (
            "evidence_complete_for_bounded_paper_probe_review"
        ),
        "selected_symbol": "BTCUSD",
        "terminal_source_sha256": SHA_A,
    }
    unsigned = dict(plan)
    unsigned.pop("plan_fingerprint")
    plan["plan_fingerprint"] = stable_hash(unsigned)

    with pytest.raises(ValidationError, match="terminal.*binding"):
        validate_lifecycle_plan(plan)


def test_planner_rejects_rehashed_incomplete_safety_receipt(
    tmp_path: Path,
) -> None:
    helpers = runpy.run_path(
        str(
            Path(__file__).with_name(
                "test_crypto_tournament_v2_capability_producer.py"
            )
        )
    )
    raw = {
        **helpers["_build_safety_sources"](),
        **helpers["_build_venue_sources"](tmp_path),
    }
    terminal = helpers["TERMINAL_EVIDENCE"](
        symbol="BTCUSD"
    )
    terminal_bytes = (
        json.dumps(terminal, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    receipt = json.loads(raw["safety_certification_receipt"])
    receipt["symbol_results"] = []
    unsigned_receipt = dict(receipt)
    unsigned_receipt.pop("receipt_fingerprint")
    receipt["receipt_fingerprint"] = stable_hash(unsigned_receipt)
    safety_bytes = (
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    venue_roles = {
        role: raw[role]
        for role in VENUE_ROLES
    }

    with pytest.raises(
        ValidationError,
        match="symbol results are incomplete",
    ):
        build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan(
            terminal,
            venue_source_bytes=venue_roles,
            safety_certification=receipt,
            safety_certification_source_sha256=hashlib.sha256(
                safety_bytes
            ).hexdigest(),
            safety_kernel_source_bytes=raw["safety_kernel_source"],
            safety_certifier_source_bytes=raw["safety_certifier_source"],
            safety_focused_test_source_bytes=(
                raw["safety_focused_test_source"]
            ),
            expected_paper_account_id="expected-paper-account",
            terminal_source_sha256=hashlib.sha256(
                terminal_bytes
            ).hexdigest(),
            as_of=helpers["AS_OF"],
        )


def _frozen_state_for_terminal(
    terminal: dict[str, object],
) -> dict[str, object]:
    source = dict(terminal["source_binding"])
    return {
        "terminal_outcome_closed": True,
        "preregistration_fingerprint": source[
            "preregistration_fingerprint"
        ],
        "schema_version": source["state_schema_version"],
        "activation_fingerprint": source["activation_fingerprint"],
        "source_state_fingerprint": source[
            "activation_source_state_fingerprint"
        ],
        "state_fingerprint": source["state_fingerprint"],
        "context_sha256": source["context_sha256"],
        "terminal_packet_sha256": source["terminal_packet_sha256"],
        "terminal_evidence_fingerprint": source[
            "terminal_evidence_fingerprint"
        ],
        "terminal_closed_at": source["terminal_closed_at"],
        "artifact_sha256": dict(source["artifact_sha256"]),
    }


def _sealed_planner_sources(
    tmp_path: Path,
) -> tuple[dict[str, object], Path, Path, Path]:
    helpers = runpy.run_path(
        str(
            Path(__file__).with_name(
                "test_crypto_tournament_v2_capability_producer.py"
            )
        )
    )
    safety = helpers["_build_safety_sources"]()
    venue = helpers["_build_venue_sources"](
        tmp_path / "fixture_venue"
    )
    venue_root = tmp_path / "venue"
    venue_root.mkdir()
    venue_paths = {
        "venue_refresh_manifest": venue_root / "manifest.json",
        "venue_universe": venue_root / "crypto_universe.json",
        "orderability_metadata": (
            venue_root / "crypto_orderability_metadata.json"
        ),
        "venue_router_input_manifest": (
            venue_root / "crypto_router_input_manifest.json"
        ),
    }
    for role, path in venue_paths.items():
        path.write_bytes(venue[role])
    runtime_path = tmp_path / "latest_status.json"
    runtime_path.write_bytes(venue["venue_runtime_visibility_status"])
    safety_path = tmp_path / "safety_certification_receipt.json"
    safety_path.write_bytes(safety["safety_certification_receipt"])
    terminal = helpers["TERMINAL_EVIDENCE"](
        symbol="BTCUSD"
    )
    return (
        terminal,
        venue_paths["orderability_metadata"],
        runtime_path,
        safety_path,
    )


def test_sealed_planner_writes_exact_terminal_plan_and_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        terminal,
        venue_path,
        runtime_path,
        safety_path,
    ) = _sealed_planner_sources(tmp_path)
    shadow_root = tmp_path / "shadow"
    shadow_root.mkdir()
    (shadow_root / "frozen_state.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        lifecycle_subject.capability_producer,
        "run_crypto_tournament_v2_forward_shadow_state",
        lambda **_: {"frozen_state": _frozen_state_for_terminal(terminal)},
    )
    export_calls: list[object] = []

    def export_terminal(**_: object) -> dict[str, object]:
        export_calls.append(object())
        return terminal

    monkeypatch.setattr(
        lifecycle_subject.capability_producer,
        "export_crypto_tournament_v2_forward_shadow_terminal_evidence",
        export_terminal,
    )
    output_root = tmp_path / "planner"
    env = {
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": "expected-paper-account"
    }
    planner_timestamp = json.loads(venue_path.read_bytes())["as_of"]

    status = run_crypto_tournament_v2_bounded_paper_probe_lifecycle_planner(
        shadow_root=shadow_root,
        output_root=output_root,
        venue_orderability_path=venue_path,
        venue_runtime_visibility_path=runtime_path,
        safety_certification_receipt_path=safety_path,
        timestamp=planner_timestamp,
        env=env,
    )

    assert status["classification"] == (
        "ready_for_exact_operation_authorization"
    )
    assert status["ready_for_exact_operation_authorization"] is True
    assert len(export_calls) == 1
    latest = output_root / "latest"
    terminal_bytes = (
        json.dumps(terminal, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    assert (latest / "terminal_evidence.json").read_bytes() == (
        terminal_bytes
    )
    plan_bytes = (latest / "lifecycle_plan.json").read_bytes()
    plan = json.loads(plan_bytes)
    assert plan_bytes == lifecycle_subject.canonical_json_bytes(plan)
    assert plan["terminal_binding"]["terminal_source_sha256"] == (
        hashlib.sha256(terminal_bytes).hexdigest()
    )
    authorization = (
        latest / "authorization_request.txt"
    ).read_text(encoding="utf-8").strip()
    assert authorization == exact_operation_authorization_text(plan)
    assert hashlib.sha256(authorization.encode("utf-8")).hexdigest() == (
        plan["required_authorization_sha256"]
    )
    rendered_status = (latest / "planner_status.json").read_text(
        encoding="utf-8"
    )
    assert "expected-paper-account" not in rendered_status
    assert "expected-paper-account" not in authorization

    assert len(export_calls) == 1
    later = run_crypto_tournament_v2_bounded_paper_probe_lifecycle_planner(
        shadow_root=shadow_root,
        output_root=output_root,
        venue_orderability_path=venue_path,
        venue_runtime_visibility_path=runtime_path,
        safety_certification_receipt_path=safety_path,
        timestamp=planner_timestamp,
        env=env,
    )
    assert later["classification"] == (
        "ready_for_exact_operation_authorization"
    )
    assert (latest / "terminal_evidence.json").read_bytes() == (
        terminal_bytes
    )
    assert len(export_calls) == 2


@pytest.mark.parametrize(
    "tampered_field",
    ("selected_candidate", "terminal_metrics", "shadow_window", "safety"),
)
def test_sealed_planner_rejects_pinned_terminal_identity_spoof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tampered_field: str,
) -> None:
    terminal, venue_path, runtime_path, safety_path = (
        _sealed_planner_sources(tmp_path)
    )
    tampered = json.loads(json.dumps(terminal))
    if tampered_field == "selected_candidate":
        tampered["selected_candidate"]["candidate_id"] = "spoofed-winner"
        tampered["selected_symbol"] = "ETHUSD"
    elif tampered_field == "terminal_metrics":
        tampered["terminal_metrics"] = {"spoofed": True}
    elif tampered_field == "shadow_window":
        tampered["shadow_window"]["hourly_bars"] = 1
    else:
        tampered["safety"]["profit_claim"] = "spoofed"
    identity = {
        key: value
        for key, value in tampered.items()
        if key not in {"as_of", "evidence_export_fingerprint"}
    }
    tampered["evidence_export_fingerprint"] = stable_hash(identity)
    shadow_root = tmp_path / "shadow"
    shadow_root.mkdir()
    (shadow_root / "frozen_state.json").write_text("{}\n", encoding="utf-8")
    output_root = tmp_path / "planner"
    latest = output_root / "latest"
    latest.mkdir(parents=True)
    (latest / "terminal_evidence.json").write_bytes(
        (json.dumps(tampered, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    monkeypatch.setattr(
        lifecycle_subject.capability_producer,
        "run_crypto_tournament_v2_forward_shadow_state",
        lambda **_: {"frozen_state": _frozen_state_for_terminal(terminal)},
    )
    monkeypatch.setattr(
        lifecycle_subject.capability_producer,
        "export_crypto_tournament_v2_forward_shadow_terminal_evidence",
        lambda **_: terminal,
    )

    status = run_crypto_tournament_v2_bounded_paper_probe_lifecycle_planner(
        shadow_root=shadow_root,
        output_root=output_root,
        venue_orderability_path=venue_path,
        venue_runtime_visibility_path=runtime_path,
        safety_certification_receipt_path=safety_path,
        timestamp=json.loads(venue_path.read_bytes())["as_of"],
        env={"ALPACA_EXPECTED_PAPER_ACCOUNT_ID": "expected-paper-account"},
    )

    assert status["classification"] == "blocked_by_local_evidence"
    assert status["ready_for_exact_operation_authorization"] is False
    assert (latest / "authorization_request.txt").read_bytes() == b""


def test_sealed_planner_rejects_pinned_terminal_from_other_shadow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal, venue_path, runtime_path, safety_path = (
        _sealed_planner_sources(tmp_path)
    )
    shadow_root = tmp_path / "shadow"
    shadow_root.mkdir()
    (shadow_root / "frozen_state.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    output_root = tmp_path / "planner"
    latest = output_root / "latest"
    latest.mkdir(parents=True)
    terminal_bytes = (
        json.dumps(terminal, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    (latest / "terminal_evidence.json").write_bytes(terminal_bytes)
    frozen_state = _frozen_state_for_terminal(terminal)
    frozen_state["state_fingerprint"] = "0" * 64
    monkeypatch.setattr(
        lifecycle_subject.capability_producer,
        "run_crypto_tournament_v2_forward_shadow_state",
        lambda **_: {"frozen_state": frozen_state},
    )
    monkeypatch.setattr(
        lifecycle_subject.capability_producer,
        "export_crypto_tournament_v2_forward_shadow_terminal_evidence",
        lambda **_: terminal,
    )
    planner_timestamp = json.loads(venue_path.read_bytes())["as_of"]

    status = run_crypto_tournament_v2_bounded_paper_probe_lifecycle_planner(
        shadow_root=shadow_root,
        output_root=output_root,
        venue_orderability_path=venue_path,
        venue_runtime_visibility_path=runtime_path,
        safety_certification_receipt_path=safety_path,
        timestamp=planner_timestamp,
        env={
            "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": "expected-paper-account"
        },
    )

    assert status["classification"] == "blocked_by_local_evidence"
    assert status["ready_for_exact_operation_authorization"] is False
    assert any(
        "does not match current frozen shadow" in blocker
        for blocker in status["blockers"]
    )
    assert (latest / "authorization_request.txt").read_bytes() == b""


def test_sealed_planner_is_dormant_without_terminal_and_clears_request(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "planner"

    status = run_crypto_tournament_v2_bounded_paper_probe_lifecycle_planner(
        shadow_root=tmp_path / "missing_shadow",
        output_root=output_root,
        timestamp=NOW,
        env={},
    )

    assert status["classification"] == (
        "dormant_pending_terminal_winner"
    )
    latest = output_root / "latest"
    plan = json.loads((latest / "lifecycle_plan.json").read_bytes())
    assert plan["classification"] == "dormant_pending_terminal_winner"
    assert (latest / "authorization_request.txt").read_bytes() == b""


def test_sealed_planner_preflight_blocks_before_shadow_or_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shadow_root = tmp_path / "shadow"
    shadow_root.mkdir()
    (shadow_root / "frozen_state.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    calls: list[object] = []
    monkeypatch.setattr(
        lifecycle_subject.capability_producer,
        "run_crypto_tournament_v2_forward_shadow_state",
        lambda **kwargs: calls.append(kwargs),
    )
    output_root = tmp_path / "planner"

    status = run_crypto_tournament_v2_bounded_paper_probe_lifecycle_planner(
        shadow_root=shadow_root,
        output_root=output_root,
        timestamp=NOW,
        env={"ALPACA_API_KEY": "loaded-but-never-output"},
    )

    assert status["classification"] == "blocked_by_offline_preflight"
    assert status["credential_values_exposed"] is False
    assert calls == []
    assert not output_root.exists()
    assert "loaded-but-never-output" not in json.dumps(status)


@pytest.mark.parametrize(
    ("classification", "expected"),
    (
        ("ready_for_exact_operation_authorization", 0),
        ("dormant_pending_terminal_winner", 2),
        ("blocked_by_local_evidence", 2),
    ),
)
def test_sealed_planner_main_exit_code_is_truthful(
    monkeypatch: pytest.MonkeyPatch,
    classification: str,
    expected: int,
) -> None:
    monkeypatch.setattr(
        lifecycle_subject,
        "run_crypto_tournament_v2_bounded_paper_probe_lifecycle_planner",
        lambda **_: {"classification": classification},
    )

    assert lifecycle_subject.main(["--no-write"]) == expected


def test_sealed_planner_cli_has_no_account_or_caller_clock_argument() -> None:
    parser = lifecycle_subject.build_parser()
    option_strings = {
        option
        for action in parser._actions
        for option in action.option_strings
    }

    assert "--expected-paper-account-id" not in option_strings
    assert "--as-of" not in option_strings
