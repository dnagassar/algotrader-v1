"""Operator-gated native credential provisioning for V5.36.

The production writer calls ``CredWriteW`` through an injectable native
boundary. Default tests inject credential-free boundaries and never access
Windows Credential Manager.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Protocol, TypeVar

from algotrader.execution.secure_credential_provider import (
    CREDENTIAL_RECORD_SCHEMA,
    CredentialFamily,
    CredentialProviderError,
    CredentialReference,
)


V536_PROVISIONING_AUTHORIZATION_SCHEMA = (
    "v5_36_windows_credential_provisioning_authorization_v1"
)
V536_PROVISIONING_RECEIPT_SCHEMA = "v5_36_credential_provisioning_receipt_v1"
_MAX_AUTHORIZATION_BYTES = 32_768
_MAX_SECRET_BYTES = 4096
_HEX_40_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_HEX_64_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_ID_RE = re.compile(r"\A[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}\Z")
_PLACEHOLDER_RE = re.compile(r"<[^<>]+>|\b(?:placeholder|tbd|todo)\b", re.IGNORECASE)
_FORBIDDEN_ENVIRONMENT_ALIASES = (
    "APP_PROFILE",
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID",
)
_AUTHORIZATION_FIELDS = {
    "schema_version",
    "authorization_id",
    "credential_reference",
    "credential_family",
    "windows_principal",
    "source_commit_sha",
    "source_tree_sha",
    "not_before_utc",
    "expires_at_utc",
    "credential_write_authorized",
    "task_mutation_authorized",
    "network_authorized",
    "broker_authorized",
    "operator_approved",
    "canonical_authorization_sha256",
}
_CREDENTIAL_WRITER_FAILURE_CLASSIFICATIONS = {
    5: "credential_writer_denied",  # ERROR_ACCESS_DENIED
    87: "credential_writer_invalid_parameter",  # ERROR_INVALID_PARAMETER
    1004: "credential_writer_invalid_flags",  # ERROR_INVALID_FLAGS
    1168: "credential_writer_preserved_target_missing",  # ERROR_NOT_FOUND
    # ERROR_NO_SUCH_LOGON_SESSION
    1312: "credential_writer_logon_session_unavailable",
    2202: "credential_writer_bad_username",  # ERROR_BAD_USERNAME
}
_RUNTIME_MODULE_RELATIVE_PATH = (
    "src/algotrader/execution/v536_credential_provisioning.py"
)
_RUNTIME_LAUNCHER_RELATIVE_PATH = "scripts/launch_v536_credential_provisioning.py"
_T = TypeVar("_T")


class V536ProvisioningError(RuntimeError):
    """Sanitized credential-provisioning failure."""

    def __init__(self, classification: str) -> None:
        self.classification = classification
        super().__init__(classification)


@dataclass(frozen=True, slots=True)
class V536ProvisioningAuthorization:
    authorization_id: str
    reference: CredentialReference
    family: CredentialFamily
    windows_principal: str
    source_commit_sha: str
    source_tree_sha: str
    not_before: datetime
    expires_at: datetime
    canonical_authorization_sha256: str


class CredentialRecordWriter(Protocol):
    def write(self, reference: CredentialReference, record: bytearray) -> None:
        ...


class NativeCredentialWriteBoundary(Protocol):
    """Minimal native write boundary; ``None`` means success."""

    def write(
        self,
        reference: CredentialReference,
        record: bytearray,
    ) -> int | None:
        ...


class OpaqueProvisioningMaterial:
    """One-use mutable credential input with redacted representations."""

    __slots__ = ("_account", "_family", "_key", "_secret", "_used")

    def __init__(
        self,
        *,
        family: CredentialFamily,
        api_key_id: str,
        api_secret_key: str,
        expected_account_id: str | None,
    ) -> None:
        if not isinstance(family, CredentialFamily):
            raise V536ProvisioningError("provisioning_material_malformed")
        self._family = family
        self._key = _secret_buffer(api_key_id)
        self._secret = _secret_buffer(api_secret_key)
        self._account = (
            bytearray()
            if expected_account_id is None
            else _secret_buffer(expected_account_id)
        )
        if family is CredentialFamily.ALPACA_PAPER_OBSERVATION and not self._account:
            self.close()
            raise V536ProvisioningError("provisioning_account_binding_missing")
        if family is CredentialFamily.ALPACA_MARKET_DATA and self._account:
            self.close()
            raise V536ProvisioningError("provisioning_account_binding_unexpected")
        self._used = False

    @property
    def family(self) -> CredentialFamily:
        return self._family

    @property
    def closed(self) -> bool:
        return self._used

    def use(self, consumer: Callable[[bytearray], _T]) -> _T:
        if self._used:
            raise V536ProvisioningError("provisioning_material_consumed")
        record = bytearray()
        try:
            record.extend(b'{"schema_version":')
            record.extend(_json_ascii(CREDENTIAL_RECORD_SCHEMA.encode("ascii")))
            record.extend(b',"family":')
            record.extend(_json_ascii(self.family.value.encode("ascii")))
            record.extend(b',"api_key_id":')
            record.extend(_json_ascii(self._key))
            record.extend(b',"api_secret_key":')
            record.extend(_json_ascii(self._secret))
            if self._account:
                record.extend(b',"expected_account_id":')
                record.extend(_json_ascii(self._account))
            record.extend(b"}")
            return consumer(record)
        finally:
            _zeroize(record)
            self.close()

    def close(self) -> None:
        for value in (self._key, self._secret, self._account):
            _zeroize(value)
        self._used = True

    def __enter__(self) -> OpaqueProvisioningMaterial:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __repr__(self) -> str:
        state = "closed" if self.closed else "open"
        return (
            "OpaqueProvisioningMaterial("
            f"family={self.family.value!r}, {state}, <redacted>)"
        )

    __str__ = __repr__


class WindowsCredWriteNativeBoundary:
    """Exact ``CredWriteW`` adapter with no logging or persistence capability."""

    def write(
        self,
        reference: CredentialReference,
        record: bytearray,
    ) -> int | None:
        class CREDENTIAL_ATTRIBUTEW(ctypes.Structure):
            _fields_ = [
                ("Keyword", wintypes.LPWSTR),
                ("Flags", wintypes.DWORD),
                ("ValueSize", wintypes.DWORD),
                ("Value", ctypes.POINTER(ctypes.c_ubyte)),
            ]

        class CREDENTIALW(ctypes.Structure):
            _fields_ = [
                ("Flags", wintypes.DWORD),
                ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR),
                ("LastWritten", wintypes.FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.POINTER(CREDENTIAL_ATTRIBUTEW)),
                ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            ]

        array_type = ctypes.c_ubyte * len(record)
        record_view = array_type.from_buffer(record)
        credential = CREDENTIALW()
        credential.Flags = 0
        credential.Type = 1  # CRED_TYPE_GENERIC
        credential.TargetName = reference.target
        credential.CredentialBlobSize = len(record)
        credential.CredentialBlob = ctypes.cast(
            record_view,
            ctypes.POINTER(ctypes.c_ubyte),
        )
        credential.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE
        credential.AttributeCount = 0
        credential.Attributes = None
        credential.UserName = None

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        cred_write = advapi32.CredWriteW
        cred_write.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
        cred_write.restype = wintypes.BOOL
        if not cred_write(ctypes.byref(credential), 0):
            return int(ctypes.get_last_error())
        return None


class WindowsCredentialManagerWriter:
    """Sanitizing generic-credential writer with injectable native I/O."""

    __slots__ = ("_native_boundary",)

    def __init__(
        self,
        *,
        native_boundary: NativeCredentialWriteBoundary | None = None,
    ) -> None:
        self._native_boundary = native_boundary

    def write(self, reference: CredentialReference, record: bytearray) -> None:
        if self._native_boundary is None and os.name != "nt":
            raise V536ProvisioningError("credential_writer_unavailable")
        if not isinstance(reference, CredentialReference):
            raise V536ProvisioningError("credential_reference_malformed")
        if not isinstance(record, bytearray) or not record:
            raise V536ProvisioningError("credential_record_malformed")
        native_boundary = self._native_boundary or WindowsCredWriteNativeBoundary()
        try:
            error_code = native_boundary.write(reference, record)
        except Exception:
            raise V536ProvisioningError("credential_writer_failed") from None
        if error_code is None:
            return
        classification = (
            _CREDENTIAL_WRITER_FAILURE_CLASSIFICATIONS.get(error_code)
            if type(error_code) is int
            else None
        )
        raise V536ProvisioningError(
            classification or "credential_writer_failed"
        ) from None


def load_v536_provisioning_authorization(
    path: Path | str,
) -> V536ProvisioningAuthorization:
    artifact = Path(path)
    if not artifact.is_absolute() or artifact.is_symlink():
        raise V536ProvisioningError("provisioning_authorization_path_invalid")
    try:
        raw = artifact.read_bytes()
    except OSError:
        raise V536ProvisioningError("provisioning_authorization_unavailable") from None
    if not raw or len(raw) > _MAX_AUTHORIZATION_BYTES:
        raise V536ProvisioningError("provisioning_authorization_malformed")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise V536ProvisioningError("provisioning_authorization_malformed") from None
    return parse_v536_provisioning_authorization(payload)


def parse_v536_provisioning_authorization(
    payload: object,
) -> V536ProvisioningAuthorization:
    if not isinstance(payload, Mapping) or set(payload) != _AUTHORIZATION_FIELDS:
        raise V536ProvisioningError("provisioning_authorization_schema_malformed")
    values = dict(payload)
    if any(
        type(value) is str and _PLACEHOLDER_RE.search(value)
        for value in values.values()
    ):
        raise V536ProvisioningError("provisioning_authorization_placeholder")
    if values.get("schema_version") != V536_PROVISIONING_AUTHORIZATION_SCHEMA:
        raise V536ProvisioningError("provisioning_authorization_schema_malformed")
    authorization_id = _required_text(values, "authorization_id")
    if _ID_RE.fullmatch(authorization_id) is None:
        raise V536ProvisioningError("provisioning_authorization_identity_malformed")
    try:
        reference = CredentialReference(
            _required_text(values, "credential_reference")
        )
        family = CredentialFamily(_required_text(values, "credential_family"))
    except (CredentialProviderError, ValueError):
        raise V536ProvisioningError("provisioning_credential_family_mismatch") from None
    if reference.family is not family:
        raise V536ProvisioningError("provisioning_credential_family_mismatch")
    principal = _required_text(values, "windows_principal")
    commit = _required_text(values, "source_commit_sha")
    tree = _required_text(values, "source_tree_sha")
    if _HEX_40_RE.fullmatch(commit) is None or _HEX_40_RE.fullmatch(tree) is None:
        raise V536ProvisioningError("provisioning_source_malformed")
    not_before = _parse_utc(values.get("not_before_utc"))
    expires_at = _parse_utc(values.get("expires_at_utc"))
    if not not_before < expires_at <= not_before + timedelta(hours=1):
        raise V536ProvisioningError("provisioning_authorization_time_invalid")
    if values.get("credential_write_authorized") is not True:
        raise V536ProvisioningError("provisioning_write_not_authorized")
    if values.get("operator_approved") is not True:
        raise V536ProvisioningError("provisioning_operator_approval_missing")
    for field in (
        "task_mutation_authorized",
        "network_authorized",
        "broker_authorized",
    ):
        if values.get(field) is not False:
            raise V536ProvisioningError("provisioning_scope_broadened")
    claimed_hash = _required_text(values, "canonical_authorization_sha256")
    if _HEX_64_RE.fullmatch(claimed_hash) is None or claimed_hash != (
        canonical_provisioning_authorization_sha256(values)
    ):
        raise V536ProvisioningError("provisioning_authorization_hash_mismatch")
    return V536ProvisioningAuthorization(
        authorization_id=authorization_id,
        reference=reference,
        family=family,
        windows_principal=principal,
        source_commit_sha=commit,
        source_tree_sha=tree,
        not_before=not_before,
        expires_at=expires_at,
        canonical_authorization_sha256=claimed_hash,
    )


def canonical_provisioning_authorization_sha256(
    payload: Mapping[str, object],
) -> str:
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


def provision_v536_credential(
    *,
    authorization: V536ProvisioningAuthorization,
    material_source: Callable[[], OpaqueProvisioningMaterial],
    writer: CredentialRecordWriter,
    current_identity: str,
    provenance: Mapping[str, object],
    clock: Callable[[], datetime],
) -> dict[str, object]:
    _reject_forbidden_environment()
    now = _parse_utc(clock())
    if not authorization.not_before <= now < authorization.expires_at:
        raise V536ProvisioningError("provisioning_authorization_expired")
    if (
        type(current_identity) is not str
        or current_identity.strip().casefold()
        != authorization.windows_principal.casefold()
    ):
        raise V536ProvisioningError("provisioning_principal_mismatch")
    if provenance.get("source_worktree_clean") is not True:
        raise V536ProvisioningError("provisioning_source_dirty")
    if provenance.get("source_commit_sha") != authorization.source_commit_sha:
        raise V536ProvisioningError("provisioning_source_commit_mismatch")
    if provenance.get("source_tree_sha") != authorization.source_tree_sha:
        raise V536ProvisioningError("provisioning_source_tree_mismatch")
    material = material_source()
    if not isinstance(material, OpaqueProvisioningMaterial):
        raise V536ProvisioningError("provisioning_material_malformed")
    if material.family is not authorization.family:
        material.close()
        raise V536ProvisioningError("provisioning_material_family_mismatch")
    try:
        material.use(lambda record: writer.write(authorization.reference, record))
    except V536ProvisioningError:
        raise
    except Exception:
        raise V536ProvisioningError("credential_writer_failed") from None
    receipt: dict[str, object] = {
        "schema_version": V536_PROVISIONING_RECEIPT_SCHEMA,
        "classification": "credential_record_provisioned",
        "authorization_id": authorization.authorization_id,
        "authorization_sha256": authorization.canonical_authorization_sha256,
        "credential_reference": str(authorization.reference),
        "credential_family": authorization.family.value,
        "source_commit_sha": authorization.source_commit_sha,
        "source_tree_sha": authorization.source_tree_sha,
        "principal_match": True,
        "secret_values_exposed": False,
        "task_mutation_occurred": False,
        "network_access_occurred": False,
        "broker_access_occurred": False,
        "provisioned_at_utc": now.isoformat(),
    }
    receipt["canonical_receipt_sha256"] = _canonical_hash(receipt)
    return receipt


def read_interactive_provisioning_material(
    family: CredentialFamily,
    *,
    prompt: Callable[[str], str] = getpass.getpass,
) -> OpaqueProvisioningMaterial:
    api_key = prompt("API key ID: ")
    api_secret = prompt("API secret key: ")
    account = (
        prompt("Expected paper account identity: ")
        if family is CredentialFamily.ALPACA_PAPER_OBSERVATION
        else None
    )
    try:
        return OpaqueProvisioningMaterial(
            family=family,
            api_key_id=api_key,
            api_secret_key=api_secret,
            expected_account_id=account,
        )
    finally:
        api_key = ""
        api_secret = ""
        account = None


def current_windows_identity() -> str:
    if os.name != "nt":
        raise V536ProvisioningError("windows_identity_unavailable")
    secur32 = ctypes.WinDLL("Secur32.dll", use_last_error=True)
    get_name = secur32.GetUserNameExW
    get_name.argtypes = [ctypes.c_int, wintypes.LPWSTR, ctypes.POINTER(wintypes.ULONG)]
    get_name.restype = wintypes.BOOL
    size = wintypes.ULONG(0)
    get_name(2, None, ctypes.byref(size))  # NameSamCompatible
    if size.value <= 1 or size.value > 32_768:
        raise V536ProvisioningError("windows_identity_unavailable")
    buffer = ctypes.create_unicode_buffer(size.value)
    if not get_name(2, buffer, ctypes.byref(size)):
        raise V536ProvisioningError("windows_identity_unavailable")
    identity = buffer.value.strip()
    if not identity:
        raise V536ProvisioningError("windows_identity_unavailable")
    return identity


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Provision one operator-authorized V5.36 credential record."
    )
    parser.add_argument("--authorization-artifact", required=True)
    parser.add_argument("--provision-authorized", action="store_true")
    return parser


def load_runtime_bound_source_provenance(
    repo_root: Path | str,
    *,
    module_path: Path | str | None = None,
    provenance_loader: Callable[[Path], Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Bind clean Git provenance to this exact executing module and launcher."""

    try:
        root = Path(repo_root).resolve(strict=True)
        actual_module = Path(module_path or __file__).resolve(strict=True)
        expected_module = (root / _RUNTIME_MODULE_RELATIVE_PATH).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise V536ProvisioningError(
            "provisioning_runtime_source_unavailable"
        ) from None
    if not root.is_dir() or actual_module != expected_module:
        raise V536ProvisioningError("provisioning_runtime_source_mismatch")

    if provenance_loader is None:
        try:
            from algotrader.execution.crypto_read_only_paper_observation_adapter import (
                get_source_provenance,
            )
        except Exception:
            raise V536ProvisioningError(
                "provisioning_runtime_source_unavailable"
            ) from None
        provenance_loader = get_source_provenance
    try:
        provenance = dict(provenance_loader(root))
    except Exception:
        raise V536ProvisioningError(
            "provisioning_runtime_source_unavailable"
        ) from None

    if provenance.get("source_worktree_clean") is not True:
        raise V536ProvisioningError("provisioning_runtime_source_dirty")
    if (
        _HEX_40_RE.fullmatch(str(provenance.get("source_commit_sha", ""))) is None
        or _HEX_40_RE.fullmatch(str(provenance.get("source_tree_sha", ""))) is None
    ):
        raise V536ProvisioningError("provisioning_runtime_source_mismatch")
    manifest = provenance.get("source_bundle_manifest")
    if not isinstance(manifest, Mapping):
        raise V536ProvisioningError("provisioning_runtime_source_manifest_missing")

    for relative_path in (
        _RUNTIME_MODULE_RELATIVE_PATH,
        _RUNTIME_LAUNCHER_RELATIVE_PATH,
    ):
        claimed_digest = manifest.get(relative_path)
        if type(claimed_digest) is not str or _HEX_64_RE.fullmatch(
            claimed_digest
        ) is None:
            raise V536ProvisioningError(
                "provisioning_runtime_source_manifest_missing"
            )
        try:
            source = (root / relative_path).resolve(strict=True)
            if source != root / relative_path:
                raise V536ProvisioningError("provisioning_runtime_source_mismatch")
            actual_digest = hashlib.sha256(
                source.read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest()
        except V536ProvisioningError:
            raise
        except (OSError, RuntimeError, ValueError):
            raise V536ProvisioningError(
                "provisioning_runtime_source_unavailable"
            ) from None
        if actual_digest != claimed_digest:
            raise V536ProvisioningError(
                "provisioning_runtime_source_digest_mismatch"
            )
    return provenance


def validate_runtime_authorization_source_binding(
    authorization: V536ProvisioningAuthorization,
    provenance: Mapping[str, object],
) -> None:
    """Reject authorization/source mismatch before Windows identity access."""

    if provenance.get("source_worktree_clean") is not True:
        raise V536ProvisioningError("provisioning_source_dirty")
    if provenance.get("source_commit_sha") != authorization.source_commit_sha:
        raise V536ProvisioningError("provisioning_source_commit_mismatch")
    if provenance.get("source_tree_sha") != authorization.source_tree_sha:
        raise V536ProvisioningError("provisioning_source_tree_mismatch")


def main(
    argv: Sequence[str] | None = None,
    *,
    expected_repo_root: Path | str | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    if not args.provision_authorized:
        print(json.dumps({"classification": "provisioning_write_not_authorized"}))
        return 2
    try:
        _reject_forbidden_environment()
        provenance = load_runtime_bound_source_provenance(
            Path.cwd() if expected_repo_root is None else expected_repo_root
        )
        authorization = load_v536_provisioning_authorization(
            Path(args.authorization_artifact)
        )
        validate_runtime_authorization_source_binding(authorization, provenance)
        receipt = provision_v536_credential(
            authorization=authorization,
            material_source=lambda: read_interactive_provisioning_material(
                authorization.family
            ),
            writer=WindowsCredentialManagerWriter(),
            current_identity=current_windows_identity(),
            provenance=provenance,
            clock=lambda: datetime.now(UTC),
        )
    except (V536ProvisioningError, CredentialProviderError) as exc:
        classification = getattr(exc, "classification", "provisioning_failed")
        print(json.dumps({"classification": classification}, sort_keys=True))
        return 2
    except Exception:
        print(json.dumps({"classification": "provisioning_failed"}, sort_keys=True))
        return 2
    print(
        json.dumps(
            {
                "classification": receipt["classification"],
                "receipt_sha256": receipt["canonical_receipt_sha256"],
                "secret_values_exposed": False,
            },
            sort_keys=True,
        )
    )
    return 0


def _reject_forbidden_environment() -> None:
    if any(
        str(os.environ.get(name, "")).strip()
        for name in _FORBIDDEN_ENVIRONMENT_ALIASES
    ):
        raise V536ProvisioningError("credential_environment_alias_rejected")


def _secret_buffer(value: object) -> bytearray:
    if type(value) is not str or not value or len(value) > _MAX_SECRET_BYTES:
        raise V536ProvisioningError("provisioning_material_malformed")
    try:
        encoded = bytearray(value.encode("ascii"))
    except UnicodeEncodeError:
        raise V536ProvisioningError("provisioning_material_malformed") from None
    if any(byte < 0x21 or byte > 0x7E for byte in encoded):
        _zeroize(encoded)
        raise V536ProvisioningError("provisioning_material_malformed")
    return encoded


def _json_ascii(value: bytes | bytearray) -> bytearray:
    result = bytearray(b'"')
    for byte in value:
        if byte in (0x22, 0x5C):
            result.append(0x5C)
        result.append(byte)
    result.append(0x22)
    return result


def _zeroize(value: bytearray) -> None:
    for index in range(len(value)):
        value[index] = 0
    value.clear()


def _required_text(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if type(value) is not str or not value.strip() or len(value) > 4096:
        raise V536ProvisioningError("provisioning_authorization_schema_malformed")
    return value.strip()


def _parse_utc(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise V536ProvisioningError("provisioning_time_malformed") from None
    else:
        raise V536ProvisioningError("provisioning_time_malformed")
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise V536ProvisioningError("provisioning_time_malformed")
    return parsed.astimezone(UTC)


def _canonical_hash(payload: Mapping[str, object]) -> str:
    body = {
        key: value
        for key, value in payload.items()
        if key != "canonical_receipt_sha256"
    }
    return hashlib.sha256(
        json.dumps(
            body,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "CredentialRecordWriter",
    "NativeCredentialWriteBoundary",
    "OpaqueProvisioningMaterial",
    "V536_PROVISIONING_AUTHORIZATION_SCHEMA",
    "V536ProvisioningAuthorization",
    "V536ProvisioningError",
    "WindowsCredWriteNativeBoundary",
    "WindowsCredentialManagerWriter",
    "canonical_provisioning_authorization_sha256",
    "current_windows_identity",
    "load_runtime_bound_source_provenance",
    "load_v536_provisioning_authorization",
    "parse_v536_provisioning_authorization",
    "provision_v536_credential",
    "read_interactive_provisioning_material",
    "validate_runtime_authorization_source_binding",
]
