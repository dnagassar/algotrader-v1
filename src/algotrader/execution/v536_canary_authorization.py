"""Strict non-secret authorization contract for the V5.36 canary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from algotrader.execution.secure_credential_provider import (
    WINDOWS_PROVIDER_NAME,
    CredentialFamily,
    CredentialProviderError,
    CredentialReference,
)
from algotrader.execution.v535_unattended_readonly import (
    EXPECTED_MARKET_DATA_ENDPOINT,
    EXPECTED_PAPER_ENDPOINT,
    V535_TASK_IDENTITY,
)


V536_AUTHORIZATION_SCHEMA = "v5_36_scheduled_canary_authorization_v1"
V536_TASK_IDENTITY = V535_TASK_IDENTITY
V536_AUTHORIZATION_MAX_BYTES = 65_536
V536_CANARY_GRACE = timedelta(minutes=5)
V536_ARM_LEAD = timedelta(minutes=15)
V536_MAX_DISARM_DELAY = timedelta(minutes=55)

_HEX_40_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_AUTHORIZATION_ID_RE = re.compile(r"\A[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}\Z")
_PLACEHOLDER_RE = re.compile(r"<[^<>]+>|\b(?:placeholder|tbd|todo)\b", re.IGNORECASE)
_AUTHORIZATION_FIELDS = {
    "schema_version",
    "authorization_id",
    "task_identity",
    "target_window_start_utc",
    "target_window_end_utc",
    "scheduled_start_utc",
    "automatic_disarm_deadline_utc",
    "windows_principal",
    "credential_vault_owner",
    "task_logon_type",
    "deployment_root",
    "source_commit_sha",
    "source_tree_sha",
    "credential_provider",
    "market_data_credential_reference",
    "paper_credential_reference",
    "market_data_endpoint",
    "paper_endpoint",
    "credential_reads_authorized",
    "task_registration_authorized",
    "task_arming_authorized",
    "task_disarming_authorized",
    "market_data_read_authorized",
    "paper_observation_authorized",
    "allow_network",
    "paper_submit_authorized",
    "paper_cancel_authorized",
    "paper_replace_authorized",
    "paper_close_authorized",
    "paper_liquidation_authorized",
    "paper_mutation_authorized",
    "live_access_authorized",
    "retry_authorized",
    "additional_windows_authorized",
    "operator_approved",
    "canonical_authorization_sha256",
}
_TRUE_GATES = {
    "credential_reads_authorized",
    "task_registration_authorized",
    "task_arming_authorized",
    "task_disarming_authorized",
    "market_data_read_authorized",
    "paper_observation_authorized",
    "allow_network",
    "operator_approved",
}
_FALSE_GATES = {
    "paper_submit_authorized",
    "paper_cancel_authorized",
    "paper_replace_authorized",
    "paper_close_authorized",
    "paper_liquidation_authorized",
    "paper_mutation_authorized",
    "live_access_authorized",
    "retry_authorized",
    "additional_windows_authorized",
}


class V536AuthorizationError(RuntimeError):
    """Sanitized V5.36 authorization failure."""

    def __init__(self, classification: str) -> None:
        self.classification = classification
        super().__init__(classification)


@dataclass(frozen=True, slots=True)
class V536CanaryAuthorization:
    authorization_id: str
    task_identity: str
    target_window_start: datetime
    target_window_end: datetime
    scheduled_start: datetime
    automatic_disarm_deadline: datetime
    windows_principal: str
    credential_vault_owner: str
    task_logon_type: str
    deployment_root: Path
    source_commit_sha: str
    source_tree_sha: str
    credential_provider: str
    market_data_reference: CredentialReference
    paper_reference: CredentialReference
    market_data_endpoint: str
    paper_endpoint: str
    canonical_authorization_sha256: str
    artifact_path: Path | None = None

    @property
    def accepted_window_identity(self) -> str:
        return (
            f"{self.target_window_start.isoformat()}_"
            f"{self.target_window_start.isoformat()}"
        )

    def public_binding(self) -> dict[str, object]:
        return {
            "authorization_id": self.authorization_id,
            "authorization_sha256": self.canonical_authorization_sha256,
            "task_identity": self.task_identity,
            "target_window_start_utc": self.target_window_start.isoformat(),
            "target_window_end_utc": self.target_window_end.isoformat(),
            "scheduled_start_utc": self.scheduled_start.isoformat(),
            "automatic_disarm_deadline_utc": (
                self.automatic_disarm_deadline.isoformat()
            ),
            "deployment_root": str(self.deployment_root),
            "task_logon_type": self.task_logon_type,
            "source_commit_sha": self.source_commit_sha,
            "source_tree_sha": self.source_tree_sha,
            "credential_provider": self.credential_provider,
            "market_data_credential_reference": str(self.market_data_reference),
            "paper_credential_reference": str(self.paper_reference),
            "market_data_endpoint": self.market_data_endpoint,
            "paper_endpoint": self.paper_endpoint,
        }


def load_v536_authorization(path: Path | str) -> V536CanaryAuthorization:
    artifact_path = Path(path)
    if not artifact_path.is_absolute() or artifact_path.is_symlink():
        raise V536AuthorizationError("authorization_path_invalid")
    try:
        if not artifact_path.is_file():
            raise V536AuthorizationError("authorization_unavailable")
        raw = artifact_path.read_bytes()
    except V536AuthorizationError:
        raise
    except OSError:
        raise V536AuthorizationError("authorization_unavailable") from None
    if not raw or len(raw) > V536_AUTHORIZATION_MAX_BYTES:
        raise V536AuthorizationError("authorization_malformed")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise V536AuthorizationError("authorization_malformed") from None
    return parse_v536_authorization(payload, artifact_path=artifact_path.resolve())


def parse_v536_authorization(
    payload: object,
    *,
    artifact_path: Path | None = None,
) -> V536CanaryAuthorization:
    if not isinstance(payload, Mapping) or set(payload) != _AUTHORIZATION_FIELDS:
        raise V536AuthorizationError("authorization_schema_malformed")
    normalized = dict(payload)
    if _contains_placeholder(normalized):
        raise V536AuthorizationError("authorization_placeholder_unresolved")
    if normalized.get("schema_version") != V536_AUTHORIZATION_SCHEMA:
        raise V536AuthorizationError("authorization_schema_malformed")
    authorization_id = _required_text(normalized, "authorization_id")
    if _AUTHORIZATION_ID_RE.fullmatch(authorization_id) is None:
        raise V536AuthorizationError("authorization_identity_malformed")
    if normalized.get("task_identity") != V536_TASK_IDENTITY:
        raise V536AuthorizationError("authorization_task_identity_mismatch")

    for field in _TRUE_GATES:
        if normalized.get(field) is not True:
            raise V536AuthorizationError("authorization_gate_incomplete")
    for field in _FALSE_GATES:
        if normalized.get(field) is not False:
            raise V536AuthorizationError("authorization_scope_broadened")

    start = _parse_utc(normalized.get("target_window_start_utc"))
    end = _parse_utc(normalized.get("target_window_end_utc"))
    scheduled = _parse_utc(normalized.get("scheduled_start_utc"))
    deadline = _parse_utc(normalized.get("automatic_disarm_deadline_utc"))
    if start.minute or start.second or start.microsecond:
        raise V536AuthorizationError("authorization_window_malformed")
    if end != start + timedelta(hours=1):
        raise V536AuthorizationError("authorization_window_malformed")
    if scheduled != end + V536_CANARY_GRACE:
        raise V536AuthorizationError("authorization_schedule_mismatch")
    if not scheduled < deadline <= scheduled + V536_MAX_DISARM_DELAY:
        raise V536AuthorizationError("authorization_disarm_deadline_invalid")

    principal = _required_text(normalized, "windows_principal")
    vault_owner = _required_text(normalized, "credential_vault_owner")
    if principal.casefold() != vault_owner.casefold():
        raise V536AuthorizationError("authorization_principal_vault_mismatch")
    if normalized.get("task_logon_type") != "InteractiveToken":
        raise V536AuthorizationError("authorization_logon_type_unsupported")

    deployment_text = _required_text(normalized, "deployment_root")
    deployment_root = Path(deployment_text)
    if not deployment_root.is_absolute() or "%" in deployment_text:
        raise V536AuthorizationError("authorization_deployment_root_invalid")

    source_commit = _required_text(normalized, "source_commit_sha")
    source_tree = _required_text(normalized, "source_tree_sha")
    if _HEX_40_RE.fullmatch(source_commit) is None:
        raise V536AuthorizationError("authorization_source_malformed")
    if _HEX_40_RE.fullmatch(source_tree) is None:
        raise V536AuthorizationError("authorization_source_malformed")

    if normalized.get("credential_provider") != WINDOWS_PROVIDER_NAME:
        raise V536AuthorizationError("authorization_provider_mismatch")
    try:
        market_reference = CredentialReference(
            _required_text(normalized, "market_data_credential_reference")
        )
        paper_reference = CredentialReference(
            _required_text(normalized, "paper_credential_reference")
        )
    except CredentialProviderError as exc:
        raise V536AuthorizationError(exc.classification) from None
    if market_reference.family is not CredentialFamily.ALPACA_MARKET_DATA:
        raise V536AuthorizationError("authorization_credential_family_mismatch")
    if paper_reference.family is not CredentialFamily.ALPACA_PAPER_OBSERVATION:
        raise V536AuthorizationError("authorization_credential_family_mismatch")

    market_endpoint = _required_text(normalized, "market_data_endpoint")
    paper_endpoint = _required_text(normalized, "paper_endpoint")
    if market_endpoint != EXPECTED_MARKET_DATA_ENDPOINT:
        raise V536AuthorizationError("authorization_market_endpoint_mismatch")
    if paper_endpoint != EXPECTED_PAPER_ENDPOINT:
        raise V536AuthorizationError("authorization_paper_endpoint_mismatch")

    claimed_hash = _required_text(normalized, "canonical_authorization_sha256")
    computed_hash = canonical_authorization_sha256(normalized)
    if claimed_hash != computed_hash:
        raise V536AuthorizationError("authorization_hash_mismatch")

    return V536CanaryAuthorization(
        authorization_id=authorization_id,
        task_identity=V536_TASK_IDENTITY,
        target_window_start=start,
        target_window_end=end,
        scheduled_start=scheduled,
        automatic_disarm_deadline=deadline,
        windows_principal=principal,
        credential_vault_owner=vault_owner,
        task_logon_type="InteractiveToken",
        deployment_root=deployment_root.resolve(),
        source_commit_sha=source_commit,
        source_tree_sha=source_tree,
        credential_provider=WINDOWS_PROVIDER_NAME,
        market_data_reference=market_reference,
        paper_reference=paper_reference,
        market_data_endpoint=market_endpoint,
        paper_endpoint=paper_endpoint,
        canonical_authorization_sha256=claimed_hash,
        artifact_path=artifact_path,
    )


def canonical_authorization_sha256(payload: Mapping[str, object]) -> str:
    body = {
        key: value
        for key, value in payload.items()
        if key != "canonical_authorization_sha256"
    }
    encoded = json.dumps(
        body,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_v536_runtime_binding(
    authorization: V536CanaryAuthorization,
    *,
    provenance: Mapping[str, object],
    current_identity: str,
    deployment_root: Path | str,
) -> None:
    if not isinstance(authorization, V536CanaryAuthorization):
        raise V536AuthorizationError("authorization_malformed")
    if type(current_identity) is not str or (
        current_identity.strip().casefold()
        != authorization.windows_principal.casefold()
    ):
        raise V536AuthorizationError("runtime_principal_mismatch")
    if authorization.windows_principal.casefold() != (
        authorization.credential_vault_owner.casefold()
    ):
        raise V536AuthorizationError("runtime_vault_owner_mismatch")
    root = Path(deployment_root)
    if not root.is_absolute() or root.resolve() != authorization.deployment_root:
        raise V536AuthorizationError("runtime_deployment_root_mismatch")
    if provenance.get("source_worktree_clean") is not True:
        raise V536AuthorizationError("runtime_source_dirty")
    if provenance.get("source_commit_sha") != authorization.source_commit_sha:
        raise V536AuthorizationError("runtime_source_commit_mismatch")
    if provenance.get("source_tree_sha") != authorization.source_tree_sha:
        raise V536AuthorizationError("runtime_source_tree_mismatch")
    manifest = provenance.get("source_bundle_manifest")
    digest = provenance.get("adapter_source_bundle_sha256")
    if not isinstance(manifest, Mapping) or not manifest:
        raise V536AuthorizationError("runtime_source_bundle_malformed")
    if type(digest) is not str or len(digest) != 64:
        raise V536AuthorizationError("runtime_source_bundle_malformed")


def require_v536_install_time(
    authorization: V536CanaryAuthorization,
    now: datetime,
) -> None:
    observed = _parse_utc(now)
    if observed >= authorization.scheduled_start:
        raise V536AuthorizationError("authorization_install_window_closed")


def require_v536_arm_time(
    authorization: V536CanaryAuthorization,
    now: datetime,
) -> None:
    observed = _parse_utc(now)
    earliest = authorization.scheduled_start - V536_ARM_LEAD
    if not earliest <= observed < authorization.scheduled_start:
        raise V536AuthorizationError("authorization_arm_time_invalid")


def require_v536_execution_time(
    authorization: V536CanaryAuthorization,
    now: datetime,
) -> None:
    observed = _parse_utc(now)
    if not authorization.scheduled_start <= observed < (
        authorization.automatic_disarm_deadline
    ):
        raise V536AuthorizationError("authorization_execution_time_invalid")


def _required_text(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if type(value) is not str or not value.strip() or len(value) > 4096:
        raise V536AuthorizationError("authorization_schema_malformed")
    return value.strip()


def _parse_utc(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise V536AuthorizationError("authorization_time_malformed") from None
    else:
        raise V536AuthorizationError("authorization_time_malformed")
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise V536AuthorizationError("authorization_time_malformed")
    return parsed.astimezone(UTC)


def _contains_placeholder(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            _contains_placeholder(key) or _contains_placeholder(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_placeholder(item) for item in value)
    return type(value) is str and _PLACEHOLDER_RE.search(value) is not None


__all__ = [
    "V536_AUTHORIZATION_SCHEMA",
    "V536_ARM_LEAD",
    "V536AuthorizationError",
    "V536CanaryAuthorization",
    "canonical_authorization_sha256",
    "load_v536_authorization",
    "parse_v536_authorization",
    "require_v536_arm_time",
    "require_v536_execution_time",
    "require_v536_install_time",
    "validate_v536_runtime_binding",
]
