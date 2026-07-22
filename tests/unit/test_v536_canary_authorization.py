from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pytest

from algotrader.execution.v536_canary_authorization import (
    V536_AUTHORIZATION_SCHEMA,
    V536AuthorizationError,
    canonical_authorization_sha256,
    load_v536_authorization,
    parse_v536_authorization,
    require_v536_arm_time,
    require_v536_execution_time,
    require_v536_install_time,
    validate_v536_runtime_binding,
)


WINDOW_START = datetime(2026, 8, 1, 12, tzinfo=UTC)
SCHEDULED_START = WINDOW_START + timedelta(hours=1, minutes=5)


def _payload(root: Path) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": V536_AUTHORIZATION_SCHEMA,
        "authorization_id": "v536-canary-20260801t1305z",
        "task_identity": "\\crypto-tournament-v2-oos-scheduler",
        "target_window_start_utc": WINDOW_START.isoformat(),
        "target_window_end_utc": (WINDOW_START + timedelta(hours=1)).isoformat(),
        "scheduled_start_utc": SCHEDULED_START.isoformat(),
        "automatic_disarm_deadline_utc": (
            SCHEDULED_START + timedelta(minutes=40)
        ).isoformat(),
        "windows_principal": "DOMAIN\\canary-user",
        "credential_vault_owner": "domain\\CANARY-user",
        "task_logon_type": "InteractiveToken",
        "deployment_root": str(root.resolve()),
        "source_commit_sha": "a" * 40,
        "source_tree_sha": "b" * 40,
        "credential_provider": "windows-credential-manager",
        "market_data_credential_reference": (
            "wincred:algotrader/v5.35/alpaca-market-data/production"
        ),
        "paper_credential_reference": (
            "wincred:algotrader/v5.35/alpaca-paper-observation/production"
        ),
        "market_data_endpoint": "https://data.alpaca.markets",
        "paper_endpoint": "https://paper-api.alpaca.markets",
        "credential_reads_authorized": True,
        "task_registration_authorized": True,
        "task_arming_authorized": True,
        "task_disarming_authorized": True,
        "market_data_read_authorized": True,
        "paper_observation_authorized": True,
        "allow_network": True,
        "paper_submit_authorized": False,
        "paper_cancel_authorized": False,
        "paper_replace_authorized": False,
        "paper_close_authorized": False,
        "paper_liquidation_authorized": False,
        "paper_mutation_authorized": False,
        "live_access_authorized": False,
        "retry_authorized": False,
        "additional_windows_authorized": False,
        "operator_approved": True,
        "canonical_authorization_sha256": "",
    }
    payload["canonical_authorization_sha256"] = canonical_authorization_sha256(
        payload
    )
    return payload


def _rehash(payload: dict[str, object]) -> dict[str, object]:
    payload["canonical_authorization_sha256"] = canonical_authorization_sha256(
        payload
    )
    return payload


def _provenance() -> dict[str, object]:
    return {
        "source_commit_sha": "a" * 40,
        "source_tree_sha": "b" * 40,
        "source_worktree_clean": True,
        "source_branch_or_detached": "codex/v5.36-windows-host-canary",
        "adapter_source_bundle_sha256": "c" * 64,
        "source_bundle_manifest": {"safe.py": "d" * 64},
    }


def test_exact_authorization_parses_and_exposes_only_public_binding(
    tmp_path: Path,
) -> None:
    authorization = parse_v536_authorization(_payload(tmp_path))
    assert authorization.target_window_start == WINDOW_START
    assert authorization.scheduled_start == SCHEDULED_START
    assert authorization.windows_principal == "DOMAIN\\canary-user"
    assert authorization.accepted_window_identity == (
        f"{WINDOW_START.isoformat()}_{WINDOW_START.isoformat()}"
    )
    binding = authorization.public_binding()
    assert binding["credential_provider"] == "windows-credential-manager"
    assert set(json.dumps(binding).lower()).isdisjoint(set()) is True
    assert "api_key" not in json.dumps(binding).lower()
    assert "api_secret" not in json.dumps(binding).lower()


@pytest.mark.parametrize(
    ("field", "value", "classification"),
    (
        (
            "target_window_start_utc",
            "<EXACT_CLOSED_WINDOW>",
            "authorization_placeholder_unresolved",
        ),
        (
            "market_data_credential_reference",
            "<NON_SECRET_REFERENCE>",
            "authorization_placeholder_unresolved",
        ),
        (
            "source_commit_sha",
            "<VERIFIED_V5_36_COMMIT>",
            "authorization_placeholder_unresolved",
        ),
        (
            "automatic_disarm_deadline_utc",
            "<EXACT_UTC_TIME>",
            "authorization_placeholder_unresolved",
        ),
        ("authorization_id", "TBD", "authorization_placeholder_unresolved"),
    ),
)
def test_operator_template_placeholders_are_never_executable(
    tmp_path: Path,
    field: str,
    value: object,
    classification: str,
) -> None:
    payload = _payload(tmp_path)
    payload[field] = value
    _rehash(payload)
    with pytest.raises(V536AuthorizationError, match=classification):
        parse_v536_authorization(payload)


@pytest.mark.parametrize(
    ("field", "value", "classification"),
    (
        ("operator_approved", False, "authorization_gate_incomplete"),
        ("allow_network", False, "authorization_gate_incomplete"),
        ("paper_submit_authorized", True, "authorization_scope_broadened"),
        ("live_access_authorized", True, "authorization_scope_broadened"),
        ("retry_authorized", True, "authorization_scope_broadened"),
        (
            "task_identity",
            "\\different-task",
            "authorization_task_identity_mismatch",
        ),
        (
            "market_data_endpoint",
            "https://api.alpaca.markets",
            "authorization_market_endpoint_mismatch",
        ),
        (
            "paper_endpoint",
            "https://api.alpaca.markets",
            "authorization_paper_endpoint_mismatch",
        ),
        (
            "credential_vault_owner",
            "DOMAIN\\other-user",
            "authorization_principal_vault_mismatch",
        ),
        (
            "task_logon_type",
            "Password",
            "authorization_logon_type_unsupported",
        ),
        (
            "market_data_credential_reference",
            "wincred:algotrader/v5.35/alpaca-paper-observation/production",
            "authorization_credential_family_mismatch",
        ),
    ),
)
def test_scope_profile_family_and_identity_mismatches_fail_closed(
    tmp_path: Path,
    field: str,
    value: object,
    classification: str,
) -> None:
    payload = _payload(tmp_path)
    payload[field] = value
    _rehash(payload)
    with pytest.raises(V536AuthorizationError, match=classification):
        parse_v536_authorization(payload)


def test_unknown_or_missing_fields_and_hash_mismatch_are_rejected(
    tmp_path: Path,
) -> None:
    missing = _payload(tmp_path)
    missing.pop("operator_approved")
    with pytest.raises(V536AuthorizationError, match="authorization_schema_malformed"):
        parse_v536_authorization(missing)

    extra = _payload(tmp_path)
    extra["secret"] = "must-not-be-accepted"
    with pytest.raises(V536AuthorizationError, match="authorization_schema_malformed"):
        parse_v536_authorization(extra)

    mismatch = _payload(tmp_path)
    mismatch["canonical_authorization_sha256"] = "0" * 64
    with pytest.raises(V536AuthorizationError, match="authorization_hash_mismatch"):
        parse_v536_authorization(mismatch)


@pytest.mark.parametrize(
    ("field", "value", "classification"),
    (
        (
            "target_window_end_utc",
            (WINDOW_START + timedelta(hours=2)).isoformat(),
            "authorization_window_malformed",
        ),
        (
            "scheduled_start_utc",
            (SCHEDULED_START + timedelta(minutes=1)).isoformat(),
            "authorization_schedule_mismatch",
        ),
        (
            "automatic_disarm_deadline_utc",
            (SCHEDULED_START + timedelta(hours=1)).isoformat(),
            "authorization_disarm_deadline_invalid",
        ),
        (
            "target_window_start_utc",
            "2026-08-01T12:00:00-04:00",
            "authorization_time_malformed",
        ),
    ),
)
def test_window_schedule_and_deadline_are_exact(
    tmp_path: Path,
    field: str,
    value: object,
    classification: str,
) -> None:
    payload = _payload(tmp_path)
    payload[field] = value
    _rehash(payload)
    with pytest.raises(V536AuthorizationError, match=classification):
        parse_v536_authorization(payload)


def test_loading_requires_absolute_regular_non_symlink_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = tmp_path / "authorization.json"
    artifact.write_text(json.dumps(_payload(tmp_path)), encoding="utf-8")
    authorization = load_v536_authorization(artifact.resolve())
    assert authorization.artifact_path == artifact.resolve()

    monkeypatch.chdir(tmp_path)
    with pytest.raises(V536AuthorizationError, match="authorization_path_invalid"):
        load_v536_authorization(Path("authorization.json"))


def test_runtime_binding_requires_exact_principal_root_commit_tree_and_clean_state(
    tmp_path: Path,
) -> None:
    authorization = parse_v536_authorization(_payload(tmp_path))
    validate_v536_runtime_binding(
        authorization,
        provenance=_provenance(),
        current_identity="domain\\CANARY-USER",
        deployment_root=tmp_path.resolve(),
    )

    cases = (
        ("runtime_principal_mismatch", {"current_identity": "other\\user"}),
        (
            "runtime_deployment_root_mismatch",
            {"deployment_root": tmp_path / "different"},
        ),
        (
            "runtime_source_dirty",
            {"provenance": {**_provenance(), "source_worktree_clean": False}},
        ),
        (
            "runtime_source_commit_mismatch",
            {"provenance": {**_provenance(), "source_commit_sha": "e" * 40}},
        ),
        (
            "runtime_source_tree_mismatch",
            {"provenance": {**_provenance(), "source_tree_sha": "f" * 40}},
        ),
    )
    for classification, changes in cases:
        values = {
            "provenance": _provenance(),
            "current_identity": "DOMAIN\\canary-user",
            "deployment_root": tmp_path.resolve(),
        }
        values.update(changes)
        with pytest.raises(V536AuthorizationError, match=classification):
            validate_v536_runtime_binding(authorization, **values)  # type: ignore[arg-type]


def test_install_arm_and_execution_time_windows_are_non_overlapping(
    tmp_path: Path,
) -> None:
    authorization = parse_v536_authorization(_payload(tmp_path))
    require_v536_install_time(authorization, SCHEDULED_START - timedelta(hours=1))
    require_v536_arm_time(authorization, SCHEDULED_START - timedelta(minutes=5))
    require_v536_execution_time(authorization, SCHEDULED_START)

    with pytest.raises(
        V536AuthorizationError,
        match="authorization_install_window_closed",
    ):
        require_v536_install_time(authorization, SCHEDULED_START)
    with pytest.raises(
        V536AuthorizationError,
        match="authorization_arm_time_invalid",
    ):
        require_v536_arm_time(authorization, SCHEDULED_START)
    with pytest.raises(
        V536AuthorizationError,
        match="authorization_execution_time_invalid",
    ):
        require_v536_execution_time(
            authorization,
            SCHEDULED_START + timedelta(minutes=40),
        )
