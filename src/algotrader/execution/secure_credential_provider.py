"""Opaque, non-plaintext credential-provider boundary for V5.35.

The production adapter reads one Windows Credential Manager generic record.
Default tests inject providers implementing :class:`CredentialProvider`; they
never invoke the operating-system store.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import ctypes
from ctypes import wintypes
from enum import StrEnum
import json
import os
import re
from typing import Protocol, TypeVar


CREDENTIAL_RECORD_SCHEMA = "v5_35_credential_record_v1"
WINDOWS_PROVIDER_NAME = "windows-credential-manager"
_REFERENCE_RE = re.compile(
    r"\Awincred:algotrader/v5[.]35/"
    r"(?P<family>alpaca-market-data|alpaca-paper-observation)/"
    r"(?P<name>[A-Za-z0-9][A-Za-z0-9._-]{0,63})\Z"
)
_MAX_RECORD_BYTES = 65_536
_T = TypeVar("_T")


class CredentialFamily(StrEnum):
    ALPACA_MARKET_DATA = "alpaca-market-data"
    ALPACA_PAPER_OBSERVATION = "alpaca-paper-observation"


class CredentialProviderError(RuntimeError):
    """Sanitized credential-provider failure with a stable classification."""

    def __init__(self, classification: str) -> None:
        self.classification = classification
        super().__init__(classification)


class CredentialReference:
    """Strict non-secret reference to one credential-store record."""

    __slots__ = ("_value", "_family", "_target")

    def __init__(self, value: str) -> None:
        if type(value) is not str:
            raise CredentialProviderError("credential_reference_malformed")
        match = _REFERENCE_RE.fullmatch(value.strip())
        if match is None:
            raise CredentialProviderError("credential_reference_malformed")
        self._value = value.strip()
        self._family = CredentialFamily(match.group("family"))
        self._target = self._value.removeprefix("wincred:")

    @property
    def family(self) -> CredentialFamily:
        return self._family

    @property
    def target(self) -> str:
        return self._target

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"CredentialReference({self._value!r})"


class OpaqueCredentialLease:
    """One-use credential material that is redacted and explicitly zeroized."""

    __slots__ = ("_api_key", "_api_secret", "_account", "_family", "_used")

    def __init__(
        self,
        *,
        family: CredentialFamily,
        api_key_id: str,
        api_secret_key: str,
        expected_account_id: str | None,
    ) -> None:
        self._family = family
        self._api_key = bytearray(api_key_id.encode("utf-8"))
        self._api_secret = bytearray(api_secret_key.encode("utf-8"))
        self._account = bytearray((expected_account_id or "").encode("utf-8"))
        self._used = False

    @property
    def family(self) -> CredentialFamily:
        return self._family

    @property
    def closed(self) -> bool:
        return self._used

    def use(
        self,
        consumer: Callable[[str, str, str | None], _T],
    ) -> _T:
        """Reveal material only to one explicit boundary callback."""

        if self._used:
            raise CredentialProviderError("credential_lease_consumed")
        try:
            api_key = self._api_key.decode("utf-8")
            api_secret = self._api_secret.decode("utf-8")
            account = self._account.decode("utf-8") or None
            return consumer(api_key, api_secret, account)
        finally:
            self.close()

    def close(self) -> None:
        for buffer in (self._api_key, self._api_secret, self._account):
            for index in range(len(buffer)):
                buffer[index] = 0
            buffer.clear()
        self._used = True

    def __enter__(self) -> OpaqueCredentialLease:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __repr__(self) -> str:
        state = "closed" if self.closed else "open"
        return f"OpaqueCredentialLease(family={self.family.value!r}, {state}, <redacted>)"

    __str__ = __repr__


class CredentialProvider(Protocol):
    """Provider seam; only credential-store implementations belong here."""

    @property
    def provider_name(self) -> str:
        ...

    def open(
        self,
        reference: CredentialReference | str,
        *,
        expected_family: CredentialFamily | str,
    ) -> OpaqueCredentialLease:
        ...

    def validate(
        self,
        reference: CredentialReference | str,
        *,
        expected_family: CredentialFamily | str,
    ) -> None:
        ...


class WindowsCredentialManagerProvider:
    """Windows Credential Manager generic-credential adapter.

    ``CredReadW`` and ``CredFree`` are used directly so no plaintext helper
    process, PowerShell command, command argument, or temporary file is needed.
    """

    @property
    def provider_name(self) -> str:
        return WINDOWS_PROVIDER_NAME

    def validate(
        self,
        reference: CredentialReference | str,
        *,
        expected_family: CredentialFamily | str,
    ) -> None:
        reference = _coerce_reference(reference)
        expected_family = _coerce_family(expected_family)
        lease = self.open(reference, expected_family=expected_family)
        lease.use(lambda _key, _secret, _account: None)

    def open(
        self,
        reference: CredentialReference | str,
        *,
        expected_family: CredentialFamily | str,
    ) -> OpaqueCredentialLease:
        reference = _coerce_reference(reference)
        expected_family = _coerce_family(expected_family)
        _require_reference_family(reference, expected_family)
        if os.name != "nt":
            raise CredentialProviderError("credential_provider_unavailable")
        raw = self._read_generic_credential(reference.target)
        try:
            return _lease_from_record_bytes(
                raw,
                reference=reference,
                expected_family=expected_family,
            )
        finally:
            for index in range(len(raw)):
                raw[index] = 0
            raw.clear()

    @staticmethod
    def _read_generic_credential(target: str) -> bytearray:
        class FILETIME(ctypes.Structure):
            _fields_ = [
                ("dwLowDateTime", wintypes.DWORD),
                ("dwHighDateTime", wintypes.DWORD),
            ]

        class CREDENTIALW(ctypes.Structure):
            _fields_ = [
                ("Flags", wintypes.DWORD),
                ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR),
                ("LastWritten", FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.c_void_p),
                ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            ]

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        pointer = ctypes.POINTER(CREDENTIALW)()
        cred_read = advapi32.CredReadW
        cred_read.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(CREDENTIALW)),
        ]
        cred_read.restype = wintypes.BOOL
        cred_free = advapi32.CredFree
        cred_free.argtypes = [ctypes.c_void_p]
        cred_free.restype = None

        if not cred_read(target, 1, 0, ctypes.byref(pointer)):
            error_code = ctypes.get_last_error()
            if error_code == 5:
                raise CredentialProviderError("credential_provider_denied")
            if error_code == 1168:
                raise CredentialProviderError("credential_record_unavailable")
            raise CredentialProviderError("credential_provider_unavailable")
        try:
            size = int(pointer.contents.CredentialBlobSize)
            if size <= 0 or size > _MAX_RECORD_BYTES:
                raise CredentialProviderError("credential_record_malformed")
            return bytearray(
                ctypes.string_at(pointer.contents.CredentialBlob, size)
            )
        finally:
            cred_free(pointer)


def provider_from_name(name: str) -> CredentialProvider:
    if name != WINDOWS_PROVIDER_NAME:
        raise CredentialProviderError("credential_provider_unsupported")
    return WindowsCredentialManagerProvider()


def lease_from_test_record(
    record: Mapping[str, object],
    *,
    reference: CredentialReference,
    expected_family: CredentialFamily,
) -> OpaqueCredentialLease:
    """Parse a synthetic record for injected store fakes without OS access."""

    try:
        encoded = json.dumps(dict(record), separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CredentialProviderError("credential_record_malformed") from exc
    raw = bytearray(encoded)
    try:
        return _lease_from_record_bytes(
            raw,
            reference=reference,
            expected_family=expected_family,
        )
    finally:
        for index in range(len(raw)):
            raw[index] = 0
        raw.clear()


def _lease_from_record_bytes(
    raw: bytearray,
    *,
    reference: CredentialReference,
    expected_family: CredentialFamily,
) -> OpaqueCredentialLease:
    _require_reference_family(reference, expected_family)
    if not raw or len(raw) > _MAX_RECORD_BYTES:
        raise CredentialProviderError("credential_record_malformed")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CredentialProviderError("credential_record_malformed") from exc
    if not isinstance(payload, dict):
        raise CredentialProviderError("credential_record_malformed")
    required = {"schema_version", "family", "api_key_id", "api_secret_key"}
    optional = {"expected_account_id"}
    if set(payload) - required - optional or not required.issubset(payload):
        raise CredentialProviderError("credential_record_malformed")
    if payload.get("schema_version") != CREDENTIAL_RECORD_SCHEMA:
        raise CredentialProviderError("credential_record_malformed")
    if payload.get("family") != expected_family.value:
        raise CredentialProviderError("credential_family_mismatch")
    api_key = _required_secret_text(payload.get("api_key_id"))
    api_secret = _required_secret_text(payload.get("api_secret_key"))
    account_value = payload.get("expected_account_id")
    account = None if account_value is None else _required_secret_text(account_value)
    if expected_family is CredentialFamily.ALPACA_PAPER_OBSERVATION and account is None:
        raise CredentialProviderError("credential_record_malformed")
    return OpaqueCredentialLease(
        family=expected_family,
        api_key_id=api_key,
        api_secret_key=api_secret,
        expected_account_id=account,
    )


def _require_reference_family(
    reference: CredentialReference | str,
    expected_family: CredentialFamily | str,
) -> None:
    reference = _coerce_reference(reference)
    expected_family = _coerce_family(expected_family)
    if reference.family is not expected_family:
        raise CredentialProviderError("credential_family_mismatch")


def _coerce_reference(reference: CredentialReference | str) -> CredentialReference:
    if isinstance(reference, CredentialReference):
        return reference
    return CredentialReference(reference)


def _coerce_family(family: CredentialFamily | str) -> CredentialFamily:
    try:
        return family if isinstance(family, CredentialFamily) else CredentialFamily(family)
    except (TypeError, ValueError):
        raise CredentialProviderError("credential_family_mismatch") from None


def _required_secret_text(value: object) -> str:
    if type(value) is not str or not value.strip() or len(value) > 4096:
        raise CredentialProviderError("credential_record_malformed")
    return value
