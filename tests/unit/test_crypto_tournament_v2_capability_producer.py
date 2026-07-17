from __future__ import annotations

import ast
import csv
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import runpy

import pytest

from algotrader.certification import (
    crypto_tournament_v2_bounded_paper_probe_generation_replay as replay_subject,
)
from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.errors import ValidationError
from algotrader.execution.crypto_bounded_probe_safety_certification import (
    build_crypto_bounded_probe_safety_certification,
)
from algotrader.execution.crypto_bounded_probe_independent_flat_reconciliation import (
    build_crypto_bounded_probe_independent_flat_reconciliation,
)
from algotrader.execution import (
    crypto_bounded_probe_independent_flat_reconciliation as flat_subject,
)
from algotrader.execution.crypto_paper_visibility_operator import (
    run_crypto_paper_visibility_cycle,
)
from algotrader.execution.crypto_paper_fill_exit_certification import (
    REQUIRED_LABELS as V510_REQUIRED_LABELS,
)
from algotrader.orchestration import (
    crypto_tournament_v2_bounded_paper_probe_capability_producer as subject,
    crypto_tournament_v2_bounded_paper_probe_review as review,
)
from algotrader.orchestration.crypto_paper_certification_ingestion import (
    REQUIRED_LABELS as V59_REQUIRED_LABELS,
    run_crypto_paper_certification_ingestion,
)
from algotrader.orchestration.crypto_tournament_v2_bounded_paper_probe_review import (
    CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT,
)
from algotrader.orchestration.crypto_universe_refresh import (
    run_crypto_universe_refresh,
)


ROOT = Path(__file__).resolve().parents[2]
REVIEW_TEST = ROOT / "tests" / "unit" / (
    "test_crypto_tournament_v2_bounded_paper_probe_review.py"
)
REVIEW_HELPERS = runpy.run_path(str(REVIEW_TEST))
REFRESH_HELPERS = runpy.run_path(
    str(ROOT / "tests" / "unit" / "test_crypto_universe_refresh.py")
)
TERMINAL_EVIDENCE = REVIEW_HELPERS["_terminal_evidence"]
AS_OF = REVIEW_HELPERS["AS_OF"]
REFRESH_BARS = REFRESH_HELPERS["_bars"]
WRITE_BAR_ROW = REFRESH_HELPERS["_write_bar_row"]
KERNEL = ROOT / "src" / "algotrader" / "execution" / "crypto_bounded_probe_safety.py"
CERTIFIER = ROOT / "src" / "algotrader" / "execution" / (
    "crypto_bounded_probe_safety_certification.py"
)
FOCUSED_TEST = ROOT / "tests" / "unit" / "test_crypto_bounded_probe_safety.py"
MODULE = ROOT / "src" / "algotrader" / "orchestration" / (
    "crypto_tournament_v2_bounded_paper_probe_capability_producer.py"
)
ACCOUNT_BINDING_SOURCE = ROOT / "src" / "algotrader" / "core" / (
    "paper_account_binding.py"
)
FLAT_RECONCILIATION_SOURCE = ROOT / "src" / "algotrader" / "execution" / (
    "crypto_bounded_probe_independent_flat_reconciliation.py"
)
VENUE_REFRESH_SOURCE = ROOT / "src" / "algotrader" / "orchestration" / (
    "crypto_universe_refresh.py"
)
VENUE_VISIBILITY_OPERATOR_SOURCE = ROOT / "src" / "algotrader" / "execution" / (
    "crypto_paper_visibility_operator.py"
)
VENUE_SUPERVISOR_SOURCE = ROOT / "src" / "algotrader" / "execution" / (
    "crypto_paper_supervisor.py"
)
PAPER_SUBMIT_CANCEL_SOURCE = ROOT / "src" / "algotrader" / "execution" / (
    "crypto_paper_submit_cancel_certification.py"
)
PAPER_SUBMIT_APPROVAL_SOURCE = ROOT / "src" / "algotrader" / "orchestration" / (
    "crypto_paper_submit_approval_packet.py"
)
PAPER_OMS_DRY_RUN_SOURCE = ROOT / "src" / "algotrader" / "orchestration" / (
    "crypto_paper_oms_dry_run.py"
)
PAPER_FILL_EXIT_SOURCE = ROOT / "src" / "algotrader" / "execution" / (
    "crypto_paper_fill_exit_certification.py"
)
PAPER_CERTIFICATION_INGESTION_SOURCE = (
    ROOT
    / "src"
    / "algotrader"
    / "orchestration"
    / "crypto_paper_certification_ingestion.py"
)


def _json_bytes(value: dict[str, object]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _stable_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _v59_operator_phrase(
    *, prior_certification_id: str, client_order_id: str
) -> str:
    return (
        "Authorized for future v5.10 review: using prior_certification_id "
        f"{prior_certification_id} and prior client_order_id {client_order_id}, "
        "authorize exactly one bounded BTCUSD Alpaca paper entry attempt and "
        "one bounded exit/flatten attempt for the resulting BTCUSD paper "
        "position, with max notional 25. This does not authorize live trading, "
        "additional orders, replacement, liquidation/close-all, capital "
        "changes, credential exposure, or paid services."
    )


def _build_safety_sources() -> dict[str, bytes]:
    kernel = KERNEL.read_bytes()
    certifier = CERTIFIER.read_bytes()
    focused_test = FOCUSED_TEST.read_bytes()
    receipt = build_crypto_bounded_probe_safety_certification(
        kernel_source_bytes=kernel,
        certifier_source_bytes=certifier,
        focused_test_source_bytes=focused_test,
        as_of=AS_OF - timedelta(hours=1),
    )
    return {
        "capability_producer_source": MODULE.read_bytes(),
        "account_binding_source": ACCOUNT_BINDING_SOURCE.read_bytes(),
        "independent_flat_reconciliation_source": (
            FLAT_RECONCILIATION_SOURCE.read_bytes()
        ),
        "safety_kernel_source": kernel,
        "safety_certifier_source": certifier,
        "safety_focused_test_source": focused_test,
        "safety_certification_receipt": _json_bytes(receipt),
    }


class _FakeReadOnlyVenueClient:
    def get_all_assets(self) -> list[dict[str, object]]:
        return [
            {
                "symbol": "BTC/USD",
                "asset_class": "crypto",
                "tradable": True,
                "status": "active",
                "marginable": False,
                "fractionable": True,
                "min_notional": "1",
                "min_order_size": "0.0001",
                "min_trade_increment": "0.00000001",
            }
        ]


def _build_venue_sources(root: Path) -> dict[str, bytes]:
    bars_path = root / "operator_input" / "crypto_paper_bars.csv"
    visibility_root = root / "runs" / "crypto_paper_visibility" / "latest"
    refresh_root = root / "runs" / "crypto_universe_refresh" / "paper_read"
    bars_path.parent.mkdir(parents=True)
    with bars_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            (
                "timestamp", "symbol", "asset_class", "open", "high",
                "low", "close", "volume",
            )
        )
        for bar in REFRESH_BARS("BTCUSD", AS_OF, count=80):
            WRITE_BAR_ROW(writer, bar)
    run_crypto_paper_visibility_cycle(
        output_root=visibility_root,
        bars_csv=bars_path,
        timestamp=AS_OF,
        env={
            "APP_PROFILE": "paper",
            "ALPACA_API_KEY": "fixture-paper-key",
            "ALPACA_SECRET_KEY": "fixture-paper-secret",
            "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
        },
        sdk_client_factory=lambda _config: _FakeReadOnlyVenueClient(),
        write_artifacts=True,
    )
    visibility_path = visibility_root / "latest_status.json"
    run_crypto_universe_refresh(
        output_root=refresh_root,
        mode="paper_read_only",
        bars_csv=bars_path,
        crypto_visibility_status=visibility_path,
        as_of=AS_OF,
        write_artifacts=True,
    )
    return {
        "venue_refresh_manifest": (refresh_root / "manifest.json").read_bytes(),
        "venue_universe": (refresh_root / "crypto_universe.json").read_bytes(),
        "orderability_metadata": (
            refresh_root / "crypto_orderability_metadata.json"
        ).read_bytes(),
        "venue_router_input_manifest": (
            refresh_root / "crypto_router_input_manifest.json"
        ).read_bytes(),
        "venue_runtime_visibility_status": visibility_path.read_bytes(),
        "venue_refresh_source": VENUE_REFRESH_SOURCE.read_bytes(),
        "venue_visibility_operator_source": (
            VENUE_VISIBILITY_OPERATOR_SOURCE.read_bytes()
        ),
        "venue_supervisor_source": VENUE_SUPERVISOR_SOURCE.read_bytes(),
    }


@pytest.fixture(scope="module")
def safety_sources(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, bytes]:
    return {
        **_build_safety_sources(),
        **_build_venue_sources(tmp_path_factory.mktemp("canonical_venue")),
    }


def _account(account_id: str) -> dict[str, object]:
    return {
        "account_id": account_id,
        "id": account_id,
        "account_number": f"number-{account_id}",
        "status": "ACTIVE",
        "blocked": False,
        "account_blocked": False,
        "trading_blocked": False,
    }


def _paper_preflight() -> dict[str, object]:
    return {
        "APP_PROFILE_is_paper": True,
        "APP_PROFILE_is_live": False,
        "paper_credentials_present": True,
        "expected_paper_account_id_loaded": True,
        "paper_endpoint_exact_match_indicator": True,
        "live_endpoint_indicator": False,
        "network_test_flag_enabled": False,
    }


def _artifact_entry(path: str, payload: bytes) -> dict[str, object]:
    return {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    }


def _lifecycle_sources(
    *,
    mechanics_symbol: str,
    submit_account_id: str,
    fill_account_id: str,
) -> dict[str, bytes]:
    labels = list(V59_REQUIRED_LABELS)
    v56_path = "runs/synthetic/lifecycle/v56/paper_oms_dry_run.json"
    v57_path = "runs/synthetic/lifecycle/v57/paper_submit_approval_packet.json"
    v58_path = "runs/synthetic/lifecycle/v58/certification_result.json"
    v59_path = (
        "runs/synthetic/lifecycle/v59/"
        "paper_fill_experiment_approval_packet.json"
    )
    v510_path = (
        "runs/synthetic/lifecycle/v510/fill_exit_certification_result.json"
    )
    v56 = {
        "schema_version": "v5_6_crypto_paper_oms_dry_run_v1",
        "as_of": (AS_OF - timedelta(hours=5)).isoformat(),
        "dry_run_status": "blocked_not_authorized",
        "approval_state": "not_authorized",
        "broker_action_permitted": False,
        "intended_action": "buy_preview",
        "asset_class": "crypto",
        "symbol": "BTCUSD",
        "selected_candidate_id": "crypto:BTCUSD:synthetic",
        "latest_price": "63006.709",
        "rounded_qty": "0.000396783",
        "preview_cap": "25",
        "dry_run_id": "dryrun_synthetic",
        "pre_broker_order_id": "prebroker_synthetic",
        "blockers": [],
        "labels": labels,
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "broker_read_performed_current_run": False,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "network_access_attempted": False,
        "profit_claim": "none",
    }
    b56 = _json_bytes(v56)
    v57 = {
        "schema_version": "v5_7_crypto_paper_submit_approval_packet_v1",
        "as_of": (AS_OF - timedelta(hours=4)).isoformat(),
        "dry_run_source": v56_path,
        "approval_packet_status": "ready_for_operator_review",
        "approval_state": "not_authorized",
        "broker_action_permitted": False,
        "dry_run_id": v56["dry_run_id"],
        "pre_broker_order_id": v56["pre_broker_order_id"],
        "selected_candidate_id": v56["selected_candidate_id"],
        "symbol": "BTCUSD",
        "intended_action": "buy_preview",
        "exact_qty": v56["rounded_qty"],
        "exact_cap": v56["preview_cap"],
        "required_operator_phrase": "synthetic-v58-authorization",
        "blockers": [],
        "labels": labels,
        "paper_submit_authorized": False,
        "paper_cancel_authorized": False,
        "paper_submit_performed": False,
        "paper_cancel_performed": False,
        "broker_mutation_performed": False,
        "broker_read_performed_current_run": False,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "network_access_attempted": False,
        "profit_claim": "none",
    }
    b57 = _json_bytes(v57)
    approval_summary = {
        field_name: v57.get(field_name)
        for field_name in (
            "schema_version", "approval_packet_status", "approval_state",
            "dry_run_id", "pre_broker_order_id", "symbol", "exact_qty",
            "exact_cap", "blockers", "labels",
        )
    }
    dry_run_summary = {
        field_name: v56.get(field_name)
        for field_name in (
            "schema_version", "dry_run_status", "approval_state", "dry_run_id",
            "pre_broker_order_id", "symbol", "rounded_qty", "preview_cap",
            "latest_price", "blockers", "labels",
        )
    }
    v58 = {
        "schema_version": "v5_8_crypto_paper_submit_cancel_certification_v1",
        "as_of": (AS_OF - timedelta(hours=2)).isoformat(),
        "approval_packet_source": v57_path,
        "dry_run_source": v56_path,
        "approved_authorization_text": v57["required_operator_phrase"],
        "dry_run_id": v56["dry_run_id"],
        "pre_broker_order_id": v56["pre_broker_order_id"],
        "symbol": mechanics_symbol,
        "client_order_id": "synthetic-v58-client-order-id",
        "approved_qty": "0.000396783",
        "submitted_qty": "0.000396783",
        "approved_max_notional": "25",
        "estimated_submit_notional": "12.5",
        "outcome_classification": "submitted_cancel_confirmed",
        "submit_attempt_count": 1,
        "cancel_attempt_count": 1,
        "final_order_status": "canceled",
        "reconciliation_status": "reconciled",
        "filled_qty": "0",
        "residual_position": {},
        "account_observation": _account(submit_account_id),
        "operator_preflight": _paper_preflight(),
        "expected_paper_account_id_loaded": True,
        "expected_account_matched": True,
        "paper_submit_authorized": True,
        "paper_cancel_authorized": True,
        "paper_submit_performed": True,
        "paper_cancel_performed": True,
        "broker_read_observed": True,
        "broker_mutation_performed": True,
        "retry_submit_allowed": False,
        "second_order_submit_allowed": False,
        "close_or_liquidate_allowed": False,
        "replace_allowed": False,
        "residual_open_order": False,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "blockers": [],
        "labels": labels,
        "approval_packet_summary": approval_summary,
        "dry_run_summary": dry_run_summary,
    }
    b58 = _json_bytes(v58)
    placeholder_md = b"# synthetic\n"
    placeholder_record = b"{}\n"
    m58 = {
        "schema_version": v58["schema_version"],
        "as_of": v58["as_of"],
        "artifact_root": "runs/synthetic/lifecycle/v58",
        "generated_under_runs": True,
        "credential_values_redacted": True,
        "required_artifacts": {
            "certification_result_json": _artifact_entry(v58_path, b58),
            "certification_result_md": _artifact_entry(
                "runs/synthetic/lifecycle/v58/certification_result.md",
                placeholder_md,
            ),
            "operating_record": _artifact_entry(
                "runs/synthetic/lifecycle/v58/operating_record.jsonl",
                placeholder_record,
            ),
        },
        "input_artifacts": {
            "approval_packet": {
                "path": v57_path,
                "sha256": hashlib.sha256(b57).hexdigest(),
            },
            "paper_oms_dry_run": {
                "path": v56_path,
                "sha256": hashlib.sha256(b56).hexdigest(),
            },
        },
        "paper_submit_authorized": True,
        "paper_submit_performed": True,
        "broker_mutation_performed": True,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "outcome_classification": v58["outcome_classification"],
        "labels": labels,
    }
    b58_manifest = _json_bytes(m58)
    v58_sha = hashlib.sha256(b58).hexdigest()
    prior_id = "v58_btcusd_submit_cancel_" + _stable_hash(
        {
            "client_order_id": v58["client_order_id"],
            "outcome": v58["outcome_classification"],
            "source_sha256": v58_sha,
        }
    )[:16]
    v59 = {
        "schema_version": "v5_9_crypto_paper_certification_ingestion_v1",
        "record_type": "paper_fill_experiment_approval_packet",
        "as_of": (AS_OF - timedelta(minutes=90)).isoformat(),
        "approval_packet_status": "ready_for_operator_review",
        "approval_state": "not_authorized",
        "certification_status": "certified_submit_cancel_no_fill",
        "requested_future_authorization_scope": (
            "bounded_btcusd_paper_fill_and_exit_certification"
        ),
        "prior_certification_result_source": v58_path,
        "prior_certification_result_sha256": v58_sha,
        "prior_certification_result_referenced": {
            "path": v58_path,
            "sha256": v58_sha,
            "schema_version": v58["schema_version"],
            "as_of": v58["as_of"],
            "outcome_classification": v58["outcome_classification"],
            "client_order_id": v58["client_order_id"],
            "final_order_status": v58["final_order_status"],
            "filled_qty": v58["filled_qty"],
        },
        "prior_certification_id": prior_id,
        "prior_client_order_id": v58["client_order_id"],
        "prior_final_order_status": v58["final_order_status"],
        "prior_filled_qty": v58["filled_qty"],
        "prior_residual_position": {},
        "proposed_symbol": "BTCUSD",
        "proposed_symbol_scope": "BTCUSD only",
        "proposed_max_notional": "25",
        "proposed_max_notional_cap": "25",
        "proposed_notional_no_greater_than_25": True,
        "required_operator_phrase": _v59_operator_phrase(
            prior_certification_id=prior_id,
            client_order_id=v58["client_order_id"],
        ),
        "operator_phrase_generated_for_review_only": True,
        "operator_phrase_accepted": False,
        "disallowed_actions": [
            "current_broker_read", "current_broker_mutation",
            "current_paper_submit", "current_paper_cancel",
            "current_paper_replace", "current_paper_close",
            "current_paper_liquidate", "live_trading", "live_submit",
            "live_cancel", "live_replace", "live_close", "live_liquidate",
            "additional_orders_beyond_one_entry_and_one_exit", "replacement",
            "liquidation_or_close_all", "capital_change",
            "credential_exposure", "paid_service_new_account_or_new_secret",
            "autonomous_submit_without_operator_authorization",
            "retry_submit",
        ],
        "blockers": [],
        "labels": labels,
        "live_authorized": False,
        "autonomous_submit_authorized": False,
        "paper_fill_authorized": False,
        "paper_entry_authorized": False,
        "paper_exit_authorized": False,
        "paper_submit_authorized": False,
        "broker_action_permitted": False,
        "broker_mutation_authorized_by_this_packet": False,
        "broker_read_performed_current_run": False,
        "broker_mutation_performed_current_run": False,
        "paper_submit_performed_current_run": False,
        "paper_cancel_performed_current_run": False,
        "live_endpoint_touched_current_run": False,
        "live_mutation_performed_current_run": False,
        "credential_values_exposed": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "next_operator_action": (
            "operator_review_required_before_any_future_bounded_btcusd_paper_"
            "fill_and_exit_certification"
        ),
        "artifact_paths": {
            "certification_ingestion_json": (
                "runs/synthetic/lifecycle/v59/certification_ingestion.json"
            ),
            "certification_ingestion_md": (
                "runs/synthetic/lifecycle/v59/certification_ingestion.md"
            ),
            "paper_fill_experiment_approval_packet_json": v59_path,
            "paper_fill_experiment_approval_packet_md": (
                "runs/synthetic/lifecycle/v59/"
                "paper_fill_experiment_approval_packet.md"
            ),
            "operating_record": (
                "runs/synthetic/lifecycle/v59/operating_record.jsonl"
            ),
            "manifest": "runs/synthetic/lifecycle/v59/manifest.json",
        },
    }
    b59 = _json_bytes(v59)
    v59_required = {
        "certification_ingestion_json": _artifact_entry(
            "runs/synthetic/lifecycle/v59/certification_ingestion.json",
            b"{}\n",
        ),
        "certification_ingestion_md": _artifact_entry(
            "runs/synthetic/lifecycle/v59/certification_ingestion.md",
            placeholder_md,
        ),
        "paper_fill_experiment_approval_packet_json": _artifact_entry(
            v59_path,
            b59,
        ),
        "paper_fill_experiment_approval_packet_md": _artifact_entry(
            "runs/synthetic/lifecycle/v59/paper_fill_experiment_approval_packet.md",
            placeholder_md,
        ),
        "operating_record": _artifact_entry(
            "runs/synthetic/lifecycle/v59/operating_record.jsonl",
            placeholder_record,
        ),
    }
    m59 = {
        "schema_version": v59["schema_version"],
        "record_type": "crypto_paper_certification_ingestion_manifest",
        "as_of": v59["as_of"],
        "artifact_root": "runs/synthetic/lifecycle/v59",
        "required_artifacts": v59_required,
        "manifest": {"path": "runs/synthetic/lifecycle/v59/manifest.json"},
        "input_artifacts": {
            "certification_result": {"path": v58_path, "sha256": v58_sha}
        },
        "certification_status": v59["certification_status"],
        "approval_packet_status": v59["approval_packet_status"],
        "approval_state": "not_authorized",
        "broker_action_permitted": False,
        "paper_submit_authorized": False,
        "paper_fill_authorized": False,
        "broker_mutation_authorized_by_this_packet": False,
        "broker_read_performed_current_run": False,
        "broker_mutation_performed_current_run": False,
        "paper_submit_performed_current_run": False,
        "live_endpoint_touched_current_run": False,
        "live_mutation_performed_current_run": False,
        "credential_values_exposed": False,
        "network_access_attempted": False,
        "generated_under_runs": True,
        "labels": labels,
        "profit_claim": "none",
    }
    b59_manifest = _json_bytes(m59)
    approval_packet_summary = {
        field_name: v59.get(field_name)
        for field_name in (
            "schema_version", "approval_packet_status", "approval_state",
            "requested_future_authorization_scope", "prior_certification_id",
            "prior_client_order_id", "proposed_symbol", "proposed_max_notional",
            "blockers", "labels",
        )
    }
    prior_summary = {
        "schema_version": v58["schema_version"],
        "client_order_id": v58["client_order_id"],
        "symbol": v58["symbol"],
        "approved_max_notional": v58["approved_max_notional"],
        "outcome_classification": v58["outcome_classification"],
        "final_order_status": v58["final_order_status"],
        "filled_qty": v58["filled_qty"],
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
    }
    v510 = {
        "schema_version": "v5_10_crypto_paper_fill_exit_certification_v1",
        "as_of": (AS_OF - timedelta(hours=1)).isoformat(),
        "approval_packet_source": v59_path,
        "prior_certification_source": v58_path,
        "approved_authorization_text": v59["required_operator_phrase"],
        "prior_certification_id": prior_id,
        "prior_client_order_id": v58["client_order_id"],
        "symbol": mechanics_symbol,
        "approved_max_notional": "25",
        "outcome_classification": "filled_exit_confirmed",
        "entry_attempt_count": 1,
        "exit_attempt_count": 1,
        "entry_final_status": "filled",
        "exit_final_status": "filled",
        "entry_filled_qty": "0.00025",
        "exit_filled_qty": "0.00025",
        "entry_final_order": {
            "status": "filled",
            "filled_qty": "0.00025",
            "submitted_at": (
                AS_OF - timedelta(minutes=59, seconds=30)
            ).isoformat(),
            "filled_at": (
                AS_OF - timedelta(minutes=59, seconds=20)
            ).isoformat(),
        },
        "exit_final_order": {
            "status": "filled",
            "filled_qty": "0.00025",
            "submitted_at": (
                AS_OF - timedelta(minutes=59, seconds=10)
            ).isoformat(),
            "filled_at": (AS_OF - timedelta(minutes=59)).isoformat(),
        },
        "final_position": {},
        "residual_position_status": (
            f"flat_or_no_{mechanics_symbol}_position_observed"
        ),
        "estimated_entry_notional": "25",
        "account_observation": _account(fill_account_id),
        "operator_preflight": _paper_preflight(),
        "paper_fill_exit_authorized": True,
        "paper_submit_performed": True,
        "broker_read_observed": True,
        "broker_mutation_performed": True,
        "entry_call_count_max": 1,
        "exit_call_count_max": 1,
        "retry_entry_allowed": False,
        "retry_exit_allowed": False,
        "close_or_liquidate_allowed": False,
        "replace_allowed": False,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "blockers": [],
        "labels": list(V510_REQUIRED_LABELS),
        "approval_packet_summary": approval_packet_summary,
        "prior_certification_summary": prior_summary,
    }
    b510 = _json_bytes(v510)
    m510 = {
        "schema_version": v510["schema_version"],
        "record_type": "crypto_paper_fill_exit_certification_manifest",
        "as_of": v510["as_of"],
        "artifact_root": "runs/synthetic/lifecycle/v510",
        "generated_under_runs": True,
        "credential_values_redacted": True,
        "required_artifacts": {
            "fill_exit_certification_result_json": {
                "path": v510_path,
                "exists": True,
                "sha256": hashlib.sha256(b510).hexdigest(),
            },
            "fill_exit_certification_result_md": {
                "path": "runs/synthetic/lifecycle/v510/fill_exit.md",
                "exists": True,
                "sha256": hashlib.sha256(placeholder_md).hexdigest(),
            },
            "operating_record": {
                "path": "runs/synthetic/lifecycle/v510/operating_record.jsonl",
                "exists": True,
                "sha256": hashlib.sha256(placeholder_record).hexdigest(),
            },
            "manifest": {"path": "runs/synthetic/lifecycle/v510/manifest.json"},
        },
        "input_artifacts": {
            "approval_packet": {"path": v59_path, "exists": True},
            "prior_certification_result": {"path": v58_path, "exists": True},
        },
        "broker_read_observed": True,
        "broker_mutation_performed": True,
        "paper_submit_performed": True,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "outcome_classification": v510["outcome_classification"],
        "labels": list(V510_REQUIRED_LABELS),
    }
    return {
        "paper_oms_dry_run": b56,
        "submit_approval_packet": b57,
        "submit_cancel_receipt": b58,
        "submit_cancel_manifest": b58_manifest,
        "fill_approval_packet": b59,
        "fill_approval_manifest": b59_manifest,
        "fill_exit_receipt": b510,
        "fill_exit_manifest": _json_bytes(m510),
        "paper_submit_cancel_source": PAPER_SUBMIT_CANCEL_SOURCE.read_bytes(),
        "paper_submit_approval_source": PAPER_SUBMIT_APPROVAL_SOURCE.read_bytes(),
        "paper_oms_dry_run_source": PAPER_OMS_DRY_RUN_SOURCE.read_bytes(),
        "paper_fill_exit_source": PAPER_FILL_EXIT_SOURCE.read_bytes(),
        "paper_certification_ingestion_source": (
            PAPER_CERTIFICATION_INGESTION_SOURCE.read_bytes()
        ),
    }


def _raw_sources(
    safety_sources: dict[str, bytes],
    *,
    symbol: str,
    flat_age: timedelta = timedelta(minutes=15),
    lifecycle_symbol: str | None = None,
    submit_account_id: str = "paper-account-a",
    fill_account_id: str = "paper-account-a",
    flat_account_id: str = "paper-account-a",
) -> dict[str, bytes]:
    mechanics_symbol = lifecycle_symbol or symbol
    lifecycle = _lifecycle_sources(
        mechanics_symbol=mechanics_symbol,
        submit_account_id=submit_account_id,
        fill_account_id=fill_account_id,
    )
    flat = build_crypto_bounded_probe_independent_flat_reconciliation(
        symbol=symbol,
        observed_at=AS_OF - flat_age,
        account_observation=_account(flat_account_id),
        expected_account_configured=True,
        expected_account_matched=True,
        positions=[],
        open_orders=[],
        broker_read_occurred=True,
        account_read_occurred=True,
        positions_read_occurred=True,
        open_orders_read_occurred=True,
    )
    return {
        "independent_flat_reconciliation": _json_bytes(flat),
        **lifecycle,
        **safety_sources,
    }


def test_candidate_deferred_ignores_irrelevant_malformed_sources() -> None:
    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            None,
            resolved_input_bytes={"orderability_metadata": b"not json"},
            as_of=AS_OF,
        )
    )

    assert production.status["classification"] == (
        "candidate_deferred_pending_terminal_winner"
    )
    assert production.status["capability_bundle_emitted"] is False
    assert set(production.artifacts) == {"production_status.json"}
    assert not any(name.startswith("bundle/") for name in production.artifacts)


def test_quality_closed_terminal_emits_diagnostics_only() -> None:
    terminal = TERMINAL_EVIDENCE(
        classification="terminal_shadow_input_quality_gate"
    )
    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            terminal,
            resolved_input_bytes={},
            as_of=AS_OF,
        )
    )

    assert production.status["classification"] == (
        "terminal_closed_without_strategy_eligible_winner"
    )
    assert production.status["capability_bundle_emitted"] is False
    assert not any(name.startswith("bundle/") for name in production.artifacts)


def test_exact_terminal_winner_can_emit_complete_v5_26_bundle(
    safety_sources: dict[str, bytes],
) -> None:
    symbol = "BTCUSD"
    terminal = TERMINAL_EVIDENCE(symbol=symbol)
    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            terminal,
            resolved_input_bytes=_raw_sources(safety_sources, symbol=symbol),
            as_of=AS_OF,
        )
    )

    assert production.status["classification"] == (
        "selected_winner_capability_bundle_emitted"
    )
    assert production.status["capability_bundle_emitted"] is True
    assert production.status["review_preview_classification"] == (
        "eligible_for_operator_review_only"
    )
    assert production.status["terminal_binding"]["selected_symbol"] == symbol
    assert production.status["paper_mutation_authorized"] is False
    for kind in subject._CAPABILITY_KINDS:
        capability = json.loads(production.artifacts[f"bundle/{kind}.json"])
        assert capability["subject"]["symbol"] == symbol
        assert capability["policy_fingerprint"] == (
            CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT
        )


@pytest.mark.parametrize("symbol", ("ETHUSD", "SOLUSD"))
def test_legacy_btc_lifecycle_cannot_certify_other_symbols(
    safety_sources: dict[str, bytes],
    symbol: str,
) -> None:
    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(symbol=symbol),
            resolved_input_bytes=_raw_sources(
                safety_sources,
                symbol=symbol,
                lifecycle_symbol=symbol,
            ),
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False
    assert not any(name.startswith("bundle/") for name in production.artifacts)


def test_lifecycle_receipts_must_observe_same_paper_account(
    safety_sources: dict[str, bytes],
) -> None:
    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=_raw_sources(
                safety_sources,
                symbol="BTCUSD",
                fill_account_id="paper-account-b",
            ),
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("status", "SUSPENDED"),
        ("blocked", True),
        ("account_blocked", True),
        ("trading_blocked", True),
        ("blocked", None),
        ("account_blocked", None),
        ("trading_blocked", None),
    ),
)
def test_lifecycle_account_observation_requires_active_unblocked_state(
    field: str,
    value: object,
) -> None:
    account = _account("paper-account-a")
    if value is None:
        del account[field]
    else:
        account[field] = value

    with pytest.raises(ValidationError):
        subject._validate_lifecycle_account_observation(account, "account")


def test_hash_coherent_blocked_fill_account_cannot_emit_bundle(
    safety_sources: dict[str, bytes],
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    receipt = json.loads(raw["fill_exit_receipt"])
    receipt["account_observation"]["trading_blocked"] = True
    receipt_bytes = _json_bytes(receipt)
    manifest = json.loads(raw["fill_exit_manifest"])
    manifest["required_artifacts"]["fill_exit_certification_result_json"][
        "sha256"
    ] = hashlib.sha256(receipt_bytes).hexdigest()
    raw["fill_exit_receipt"] = receipt_bytes
    raw["fill_exit_manifest"] = _json_bytes(manifest)

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False


@pytest.mark.parametrize(
    "field",
    ("broker_action_permitted", "credential_values_exposed"),
)
def test_hash_coherent_v59_authority_field_cannot_emit_bundle(
    safety_sources: dict[str, bytes],
    field: str,
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    packet = json.loads(raw["fill_approval_packet"])
    packet[field] = True
    packet_bytes = _json_bytes(packet)
    manifest = json.loads(raw["fill_approval_manifest"])
    entry = manifest["required_artifacts"][
        "paper_fill_experiment_approval_packet_json"
    ]
    entry["sha256"] = hashlib.sha256(packet_bytes).hexdigest()
    entry["size"] = len(packet_bytes)
    raw["fill_approval_packet"] = packet_bytes
    raw["fill_approval_manifest"] = _json_bytes(manifest)

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False


def test_canonical_v59_writer_output_is_accepted_end_to_end(
    safety_sources: dict[str, bytes],
    tmp_path: Path,
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    prior_path = (
        tmp_path
        / "runs"
        / "crypto_paper_submit_cancel_certification"
        / "latest"
        / "certification_result.json"
    )
    prior_path.parent.mkdir(parents=True)
    prior_path.write_bytes(raw["submit_cancel_receipt"])
    v59_root = (
        tmp_path
        / "runs"
        / "crypto_paper_certification_ingestion"
        / "latest"
    )
    ingestion = run_crypto_paper_certification_ingestion(
        certification_result_path=prior_path,
        output_root=v59_root,
        as_of=(AS_OF - timedelta(minutes=90)).isoformat(),
        write_artifacts=True,
    )
    artifact_paths = ingestion["artifact_paths"]
    packet_path = Path(
        artifact_paths["paper_fill_experiment_approval_packet_json"]
    )
    manifest_path = Path(artifact_paths["manifest"])
    raw["fill_approval_packet"] = packet_path.read_bytes()
    raw["fill_approval_manifest"] = manifest_path.read_bytes()

    submit_manifest = json.loads(raw["submit_cancel_manifest"])
    submit_manifest["required_artifacts"]["certification_result_json"][
        "path"
    ] = str(prior_path)
    raw["submit_cancel_manifest"] = _json_bytes(submit_manifest)

    packet = json.loads(raw["fill_approval_packet"])
    receipt = json.loads(raw["fill_exit_receipt"])
    receipt.update(
        {
            "approval_packet_source": str(packet_path),
            "prior_certification_source": str(prior_path),
            "approved_authorization_text": packet["required_operator_phrase"],
            "prior_certification_id": packet["prior_certification_id"],
            "prior_client_order_id": packet["prior_client_order_id"],
            "approval_packet_summary": {
                field_name: packet.get(field_name)
                for field_name in (
                    "schema_version",
                    "approval_packet_status",
                    "approval_state",
                    "requested_future_authorization_scope",
                    "prior_certification_id",
                    "prior_client_order_id",
                    "proposed_symbol",
                    "proposed_max_notional",
                    "blockers",
                    "labels",
                )
            },
        }
    )
    receipt_bytes = _json_bytes(receipt)
    fill_manifest = json.loads(raw["fill_exit_manifest"])
    fill_manifest["required_artifacts"][
        "fill_exit_certification_result_json"
    ]["sha256"] = hashlib.sha256(receipt_bytes).hexdigest()
    fill_manifest["input_artifacts"]["approval_packet"]["path"] = str(
        packet_path
    )
    fill_manifest["input_artifacts"]["prior_certification_result"][
        "path"
    ] = str(prior_path)
    raw["fill_exit_receipt"] = receipt_bytes
    raw["fill_exit_manifest"] = _json_bytes(fill_manifest)

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is True
    assert production.status["classification"] == (
        "selected_winner_capability_bundle_emitted"
    )


def test_flat_observation_must_match_lifecycle_paper_account(
    safety_sources: dict[str, bytes],
) -> None:
    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=_raw_sources(
                safety_sources,
                symbol="BTCUSD",
                flat_account_id="paper-account-b",
            ),
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False


def test_flat_observation_must_follow_final_exit_fill(
    safety_sources: dict[str, bytes],
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    receipt = json.loads(raw["fill_exit_receipt"])
    receipt["exit_final_order"]["submitted_at"] = (
        AS_OF - timedelta(minutes=5, seconds=10)
    ).isoformat()
    receipt["exit_final_order"]["filled_at"] = (
        AS_OF - timedelta(minutes=5)
    ).isoformat()
    receipt_bytes = _json_bytes(receipt)
    manifest = json.loads(raw["fill_exit_manifest"])
    manifest["required_artifacts"]["fill_exit_certification_result_json"][
        "sha256"
    ] = hashlib.sha256(receipt_bytes).hexdigest()
    raw["fill_exit_receipt"] = receipt_bytes
    raw["fill_exit_manifest"] = _json_bytes(manifest)

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False


@pytest.mark.parametrize(
    ("top_level_field", "order_field"),
    (
        ("entry_filled_qty", "entry_final_order"),
        ("exit_filled_qty", "exit_final_order"),
    ),
)
def test_zero_quantity_fill_cannot_certify_lifecycle_mechanics(
    safety_sources: dict[str, bytes],
    top_level_field: str,
    order_field: str,
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    receipt = json.loads(raw["fill_exit_receipt"])
    receipt[top_level_field] = "0"
    receipt[order_field]["filled_qty"] = "0"
    receipt_bytes = _json_bytes(receipt)
    manifest = json.loads(raw["fill_exit_manifest"])
    manifest["required_artifacts"]["fill_exit_certification_result_json"][
        "sha256"
    ] = hashlib.sha256(receipt_bytes).hexdigest()
    raw["fill_exit_receipt"] = receipt_bytes
    raw["fill_exit_manifest"] = _json_bytes(manifest)

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False


def test_historical_btc_mechanics_cannot_certify_eth_winner(
    safety_sources: dict[str, bytes],
) -> None:
    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(symbol="ETHUSD"),
            resolved_input_bytes=_raw_sources(
                safety_sources,
                symbol="ETHUSD",
                lifecycle_symbol="BTCUSD",
            ),
            as_of=AS_OF,
        )
    )

    assert production.status["classification"] == (
        "selected_winner_operational_evidence_blocked"
    )
    assert production.status["capability_bundle_emitted"] is False
    assert not any(name.startswith("bundle/") for name in production.artifacts)


def test_one_missing_source_prevents_entire_bundle(
    safety_sources: dict[str, bytes],
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    del raw["independent_flat_reconciliation"]

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False
    assert "resolved_source_missing:independent_flat_reconciliation" in (
        production.status["blockers"]
    )
    assert not any(name.startswith("bundle/") for name in production.artifacts)


def test_flat_freshness_boundary_is_exact(
    safety_sources: dict[str, bytes],
) -> None:
    exact = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=_raw_sources(
                safety_sources,
                symbol="BTCUSD",
                flat_age=timedelta(minutes=15),
            ),
            as_of=AS_OF,
        )
    )
    late = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=_raw_sources(
                safety_sources,
                symbol="BTCUSD",
                flat_age=timedelta(minutes=15, microseconds=1),
            ),
            as_of=AS_OF,
        )
    )

    assert exact.status["capability_bundle_emitted"] is True
    assert late.status["capability_bundle_emitted"] is False


def test_source_tamper_breaks_receipt_binding(
    safety_sources: dict[str, bytes],
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    raw["safety_kernel_source"] += b"\n# tamper\n"

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False
    assert not any(name.startswith("bundle/") for name in production.artifacts)


@pytest.mark.parametrize(
    ("role", "receipt_field"),
    (
        ("safety_kernel_source", "kernel_source_sha256"),
        ("safety_certifier_source", "certifier_source_sha256"),
        ("safety_focused_test_source", "focused_test_source_sha256"),
    ),
)
def test_rehashed_safety_source_substitution_cannot_emit_bundle(
    safety_sources: dict[str, bytes],
    role: str,
    receipt_field: str,
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    raw[role] += b"\n# caller-coherent substitution\n"
    receipt = json.loads(raw["safety_certification_receipt"])
    receipt[receipt_field] = hashlib.sha256(raw[role]).hexdigest()
    unsigned = dict(receipt)
    unsigned.pop("receipt_fingerprint")
    receipt["receipt_fingerprint"] = _stable_hash(unsigned)
    raw["safety_certification_receipt"] = _json_bytes(receipt)

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False
    assert not any(
        name.startswith("resolved_sources/")
        for name in production.artifacts
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("min_notional", "0.01"),
        ("min_order_notional", "100"),
    ),
)
def test_venue_advertised_minimum_must_match_broker_runtime_metadata(
    safety_sources: dict[str, bytes],
    field: str,
    value: str,
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    orderability = json.loads(raw["orderability_metadata"])
    orderability["records"][0][field] = value
    orderability_bytes = _json_bytes(orderability)
    manifest = json.loads(raw["venue_refresh_manifest"])
    manifest["required_artifacts"]["crypto_orderability_metadata"][
        "sha256"
    ] = hashlib.sha256(orderability_bytes).hexdigest()
    raw["orderability_metadata"] = orderability_bytes
    raw["venue_refresh_manifest"] = _json_bytes(manifest)

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False
    assert not any(
        name.startswith("resolved_sources/")
        for name in production.artifacts
    )


def test_future_dated_dry_run_cannot_launder_lifecycle_freshness(
    safety_sources: dict[str, bytes],
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    dry_run = json.loads(raw["paper_oms_dry_run"])
    dry_run["as_of"] = "2099-01-01T00:00:00+00:00"
    dry_run_bytes = _json_bytes(dry_run)
    manifest = json.loads(raw["submit_cancel_manifest"])
    manifest["input_artifacts"]["paper_oms_dry_run"]["sha256"] = (
        hashlib.sha256(dry_run_bytes).hexdigest()
    )
    raw["paper_oms_dry_run"] = dry_run_bytes
    raw["submit_cancel_manifest"] = _json_bytes(manifest)

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False


def test_fill_approval_manifest_timestamp_must_match_packet(
    safety_sources: dict[str, bytes],
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    manifest = json.loads(raw["fill_approval_manifest"])
    manifest["as_of"] = (AS_OF - timedelta(minutes=89)).isoformat()
    raw["fill_approval_manifest"] = _json_bytes(manifest)

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False


@pytest.mark.parametrize(
    "role",
    (
        "venue_refresh_manifest",
        "venue_universe",
        "orderability_metadata",
        "venue_router_input_manifest",
        "venue_runtime_visibility_status",
        "submit_cancel_manifest",
        "submit_approval_packet",
        "paper_oms_dry_run",
        "fill_exit_manifest",
        "fill_approval_packet",
        "fill_approval_manifest",
    ),
)
def test_unrelated_json_cannot_satisfy_provenance_role(
    safety_sources: dict[str, bytes],
    role: str,
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    raw[role] = _json_bytes({})

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False


@pytest.mark.parametrize(
    "role",
    (
        "venue_refresh_manifest",
        "submit_cancel_manifest",
        "fill_approval_manifest",
        "fill_exit_manifest",
    ),
)
def test_manifest_extra_authority_field_blocks_emission(
    safety_sources: dict[str, bytes],
    role: str,
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    manifest = json.loads(raw[role])
    manifest["live_authorized"] = True
    raw[role] = _json_bytes(manifest)

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False


def test_boolean_fill_attempt_count_blocks_after_manifest_rehash(
    safety_sources: dict[str, bytes],
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    receipt = json.loads(raw["fill_exit_receipt"])
    receipt["entry_attempt_count"] = True
    receipt_bytes = _json_bytes(receipt)
    manifest = json.loads(raw["fill_exit_manifest"])
    manifest["required_artifacts"]["fill_exit_certification_result_json"][
        "sha256"
    ] = hashlib.sha256(receipt_bytes).hexdigest()
    raw["fill_exit_receipt"] = receipt_bytes
    raw["fill_exit_manifest"] = _json_bytes(manifest)

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            TERMINAL_EVIDENCE(),
            resolved_input_bytes=raw,
            as_of=AS_OF,
        )
    )

    assert production.status["capability_bundle_emitted"] is False


def test_every_canonical_local_source_marker_and_digest_is_valid(
    safety_sources: dict[str, bytes],
) -> None:
    raw = _raw_sources(safety_sources, symbol="BTCUSD")
    raw_hashes = {
        role: hashlib.sha256(payload).hexdigest()
        for role, payload in raw.items()
    }

    assert set(subject._LOCAL_SOURCE_PATHS) <= set(raw)
    subject._validate_local_source_bindings(raw, raw_hashes)


def test_waiting_generation_is_immutable_and_pinned_loadable(tmp_path: Path) -> None:
    output = tmp_path / "capabilities"
    status = subject.run_crypto_tournament_v2_bounded_paper_probe_capability_producer(
        shadow_root=tmp_path / "missing-shadow",
        output_root=output,
        as_of=AS_OF,
    )
    latest = json.loads((output / "latest_manifest.json").read_text())
    loaded = (
        subject.load_crypto_tournament_v2_bounded_paper_probe_capability_generation(
            output,
            expected_publication_fingerprint=latest["publication_fingerprint"],
        )
    )

    assert loaded.status == status
    assert loaded.status["classification"] == (
        "candidate_deferred_pending_terminal_winner"
    )
    assert loaded.artifacts["production_status.json"]


def test_v5_26_loader_consumes_and_embeds_complete_pinned_generation(
    tmp_path: Path,
    safety_sources: dict[str, bytes],
) -> None:
    terminal = TERMINAL_EVIDENCE()
    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            terminal,
            resolved_input_bytes=_raw_sources(safety_sources, symbol="BTCUSD"),
            as_of=AS_OF,
        )
    )
    capability_root = tmp_path / "capabilities"
    subject._publish_production(capability_root, production)
    (
        capabilities,
        capability_hashes,
        sources,
        source_hashes,
        upstreams,
        upstream_hashes,
        support,
    ) = review._load_capability_artifacts(capability_root)
    packet = review.build_crypto_tournament_v2_bounded_paper_probe_review(
        terminal,
        capability_evidence=capabilities,
        capability_artifact_sha256=capability_hashes,
        capability_source_evidence=sources,
        capability_source_artifact_sha256=source_hashes,
        capability_upstream_evidence=upstreams,
        capability_upstream_artifact_sha256=upstream_hashes,
        as_of=AS_OF,
    )

    assert packet["classification"] == "eligible_for_operator_review_only"
    assert "latest_manifest.json" in support
    assert any(name.endswith("generation_manifest.json") for name in support)

    review_root = tmp_path / "review"
    review._publish_review_artifacts(
        review_root,
        preregistration=(
            review.build_crypto_tournament_v2_bounded_paper_probe_preregistration()
        ),
        packet=packet,
        markdown=(
            review.render_crypto_tournament_v2_bounded_paper_probe_review_markdown(
                packet
            )
        ),
        terminal_evidence=terminal,
        capability_evidence=capabilities,
        capability_source_evidence=sources,
        capability_upstream_evidence=upstreams,
        capability_support_artifacts=support,
    )
    latest = json.loads((review_root / "latest_manifest.json").read_text())
    generation = review_root / latest["generation_relative_path"]
    assert (
        generation
        / "inputs"
        / "capability_production"
        / "latest_manifest.json"
    ).is_file()

    (capability_root / "venue_orderability.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="mixed flat and immutable"):
        review._load_capability_artifacts(capability_root)


def test_producer_import_boundary_has_no_execution_broker_or_network() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"), filename=str(MODULE))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert not any(
        name.startswith(
            (
                "algotrader.execution",
                "alpaca",
                "httpx",
                "requests",
                "socket",
                "urllib",
            )
        )
        for name in imports
    )
    assert calls.isdisjoint(
        {
            "cancel_order",
            "close_position",
            "get_account",
            "get_orders",
            "replace_order",
            "submit_order",
            "urlopen",
        }
    )


@pytest.mark.parametrize(
    "value",
    ("0001-01-01T00:00:00+14:00", "9999-12-31T23:59:59-14:00"),
)
@pytest.mark.parametrize(
    "parser",
    (subject._utc_datetime, review._utc_datetime, replay_subject._utc_datetime,
     flat_subject._utc_datetime),
)
def test_extreme_offset_timestamps_fail_as_validation_error(
    value: str,
    parser: object,
) -> None:
    with pytest.raises(ValidationError):
        parser(value, "timestamp")  # type: ignore[operator]


@pytest.mark.parametrize(
    "name",
    (
        "../escape.json",
        "dir/file.json:stream",
        "dir/NUL.json",
        "dir/COM1.txt",
        "dir/file.json.",
        "dir/file.json ",
        "dir/control\x00.json",
        "dir/control\x1f.json",
    ),
)
def test_windows_unsafe_artifact_names_are_rejected(name: str) -> None:
    with pytest.raises(ValidationError, match="unsafe"):
        subject._safe_relative_name(name)
