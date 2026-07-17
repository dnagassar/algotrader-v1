"""Non-secret, domain-separated paper-account evidence binding."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib

from algotrader.errors import ValidationError


ALPACA_PAPER_ACCOUNT_BINDING_SCHEMA_VERSION = (
    "v5_27_alpaca_paper_account_binding_v1"
)
_DOMAIN = b"algotrader:v5_27:alpaca_paper_account:v1\x00"
_EXPECTED_KEYS = {
    "schema_version",
    "broker",
    "environment",
    "identity_namespace",
    "fingerprint_algorithm",
    "account_fingerprint",
    "expected_account_configured",
    "expected_account_matched",
}

__all__ = [
    "ALPACA_PAPER_ACCOUNT_BINDING_SCHEMA_VERSION",
    "build_alpaca_paper_account_binding",
    "validate_alpaca_paper_account_binding",
]


def build_alpaca_paper_account_binding(
    account: Mapping[str, object],
    *,
    expected_account_configured: bool,
    expected_account_matched: bool,
) -> dict[str, object]:
    """Return a stable binding without returning the source identifier."""

    if not isinstance(account, Mapping):
        raise ValidationError("paper account observation must be a mapping.")
    if expected_account_configured is not True:
        raise ValidationError("expected paper account must be configured.")
    if expected_account_matched is not True:
        raise ValidationError("expected paper account must match.")
    account_id = _identity_text(account.get("account_id"), "account_id")
    alias_id = _identity_text(account.get("id"), "id")
    account_number = _identity_text(
        account.get("account_number"),
        "account_number",
    )
    if account_id and alias_id and account_id != alias_id:
        raise ValidationError("paper account id aliases disagree.")
    opaque_identity = account_id or alias_id
    namespace = "alpaca_account_id"
    if not opaque_identity:
        opaque_identity = account_number
        namespace = "alpaca_account_number"
    if not opaque_identity:
        raise ValidationError("paper account identity is unavailable.")
    fingerprint = hashlib.sha256(
        _DOMAIN
        + namespace.encode("ascii")
        + b"\x00"
        + opaque_identity.encode("utf-8")
    ).hexdigest()
    binding: dict[str, object] = {
        "schema_version": ALPACA_PAPER_ACCOUNT_BINDING_SCHEMA_VERSION,
        "broker": "alpaca",
        "environment": "alpaca_paper",
        "identity_namespace": namespace,
        "fingerprint_algorithm": "sha256",
        "account_fingerprint": fingerprint,
        "expected_account_configured": True,
        "expected_account_matched": True,
    }
    validate_alpaca_paper_account_binding(binding)
    return binding


def validate_alpaca_paper_account_binding(
    binding: Mapping[str, object],
) -> None:
    """Validate the exact public binding schema without an account value."""

    fingerprint = str(binding.get("account_fingerprint", ""))
    if (
        set(binding) != _EXPECTED_KEYS
        or binding.get("schema_version")
        != ALPACA_PAPER_ACCOUNT_BINDING_SCHEMA_VERSION
        or binding.get("broker") != "alpaca"
        or binding.get("environment") != "alpaca_paper"
        or binding.get("identity_namespace")
        not in {"alpaca_account_id", "alpaca_account_number"}
        or binding.get("fingerprint_algorithm") != "sha256"
        or len(fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in fingerprint)
        or binding.get("expected_account_configured") is not True
        or binding.get("expected_account_matched") is not True
    ):
        raise ValidationError("paper account binding is invalid.")


def _identity_text(value: object, field_name: str) -> str:
    if value is None:
        return ""
    if type(value) is not str:
        raise ValidationError(f"paper {field_name} must be a string.")
    return value.strip()
