from __future__ import annotations

import pytest

from algotrader.execution.secure_credential_provider import (
    CREDENTIAL_RECORD_SCHEMA,
    CredentialFamily,
    CredentialProviderError,
    CredentialReference,
    OpaqueCredentialLease,
    WindowsCredentialManagerProvider,
    lease_from_test_record,
    provider_from_name,
)


MARKET_REFERENCE = CredentialReference(
    "wincred:algotrader/v5.35/alpaca-market-data/offline-test"
)
PAPER_REFERENCE = CredentialReference(
    "wincred:algotrader/v5.35/alpaca-paper-observation/offline-test"
)


def _record(
    family: CredentialFamily,
    *,
    key: str = "V535_KEY_SENTINEL",
    secret: str = "V535_SECRET_SENTINEL",
    account: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "schema_version": CREDENTIAL_RECORD_SCHEMA,
        "family": family.value,
        "api_key_id": key,
        "api_secret_key": secret,
    }
    if account is not None:
        result["expected_account_id"] = account
    return result


@pytest.mark.parametrize(
    "value",
    (
        "",
        "file:credentials.json",
        "wincred:../secret",
        "wincred:algotrader/v5.35/alpaca-market-data/has space",
        "wincred:algotrader/v5.35/unknown/name",
        "wincred:algotrader/v5.34/alpaca-market-data/name",
    ),
)
def test_reference_is_strict_and_non_plaintext(value: str) -> None:
    with pytest.raises(
        CredentialProviderError,
        match="credential_reference_malformed",
    ):
        CredentialReference(value)


def test_record_family_must_match_reference_and_expected_family() -> None:
    with pytest.raises(
        CredentialProviderError,
        match="credential_family_mismatch",
    ):
        lease_from_test_record(
            _record(CredentialFamily.ALPACA_MARKET_DATA),
            reference=MARKET_REFERENCE,
            expected_family=CredentialFamily.ALPACA_PAPER_OBSERVATION,
        )

    with pytest.raises(
        CredentialProviderError,
        match="credential_family_mismatch",
    ):
        lease_from_test_record(
            _record(CredentialFamily.ALPACA_PAPER_OBSERVATION, account="account"),
            reference=MARKET_REFERENCE,
            expected_family=CredentialFamily.ALPACA_MARKET_DATA,
        )


@pytest.mark.parametrize(
    "record",
    (
        {},
        {
            "schema_version": "wrong",
            "family": CredentialFamily.ALPACA_MARKET_DATA.value,
            "api_key_id": "key",
            "api_secret_key": "secret",
        },
        {
            "schema_version": CREDENTIAL_RECORD_SCHEMA,
            "family": CredentialFamily.ALPACA_MARKET_DATA.value,
            "api_key_id": "",
            "api_secret_key": "secret",
        },
        {
            "schema_version": CREDENTIAL_RECORD_SCHEMA,
            "family": CredentialFamily.ALPACA_MARKET_DATA.value,
            "api_key_id": "key",
            "api_secret_key": "secret",
            "unexpected": "field",
        },
    ),
)
def test_malformed_records_fail_with_sanitized_classification(
    record: dict[str, object],
) -> None:
    with pytest.raises(
        CredentialProviderError,
        match="credential_record_malformed",
    ) as raised:
        lease_from_test_record(
            record,
            reference=MARKET_REFERENCE,
            expected_family=CredentialFamily.ALPACA_MARKET_DATA,
        )
    assert "V535_SECRET_SENTINEL" not in str(raised.value)


def test_paper_record_requires_account_binding() -> None:
    with pytest.raises(
        CredentialProviderError,
        match="credential_record_malformed",
    ):
        lease_from_test_record(
            _record(CredentialFamily.ALPACA_PAPER_OBSERVATION),
            reference=PAPER_REFERENCE,
            expected_family=CredentialFamily.ALPACA_PAPER_OBSERVATION,
        )


def test_opaque_lease_is_one_use_redacted_and_zeroized() -> None:
    lease = lease_from_test_record(
        _record(
            CredentialFamily.ALPACA_PAPER_OBSERVATION,
            account="V535_ACCOUNT_SENTINEL",
        ),
        reference=PAPER_REFERENCE,
        expected_family=CredentialFamily.ALPACA_PAPER_OBSERVATION,
    )
    before = repr(lease)
    assert "V535_KEY_SENTINEL" not in before
    assert "V535_SECRET_SENTINEL" not in before
    assert "V535_ACCOUNT_SENTINEL" not in before

    observed = lease.use(
        lambda key, secret, account: (key == "V535_KEY_SENTINEL")
        and (secret == "V535_SECRET_SENTINEL")
        and (account == "V535_ACCOUNT_SENTINEL")
    )
    assert observed is True
    assert lease.closed is True
    assert "V535_SECRET_SENTINEL" not in repr(lease)
    with pytest.raises(
        CredentialProviderError,
        match="credential_lease_consumed",
    ):
        lease.use(lambda *_: None)


def test_lease_zeroizes_when_consumer_raises() -> None:
    lease = OpaqueCredentialLease(
        family=CredentialFamily.ALPACA_MARKET_DATA,
        api_key_id="V535_KEY_SENTINEL",
        api_secret_key="V535_SECRET_SENTINEL",
        expected_account_id=None,
    )

    def fail(*_: object) -> None:
        raise RuntimeError("fixed_failure")

    with pytest.raises(RuntimeError, match="fixed_failure"):
        lease.use(fail)
    assert lease.closed is True
    assert "V535_SECRET_SENTINEL" not in repr(lease)


def test_windows_provider_unavailable_fails_without_store_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import algotrader.execution.secure_credential_provider as module

    monkeypatch.setattr(module.os, "name", "posix")
    provider = WindowsCredentialManagerProvider()
    with pytest.raises(
        CredentialProviderError,
        match="credential_provider_unavailable",
    ):
        provider.open(
            MARKET_REFERENCE,
            expected_family=CredentialFamily.ALPACA_MARKET_DATA,
        )


def test_provider_factory_accepts_only_production_adapter_name() -> None:
    assert isinstance(
        provider_from_name("windows-credential-manager"),
        WindowsCredentialManagerProvider,
    )
    with pytest.raises(
        CredentialProviderError,
        match="credential_provider_unsupported",
    ):
        provider_from_name("plaintext-file")
