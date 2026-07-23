from __future__ import annotations

from datetime import UTC, datetime, timedelta
import inspect
import json
import os
from pathlib import Path
import sys

import pytest

from algotrader.execution.secure_credential_provider import CredentialFamily
from algotrader.execution.v536_credential_provisioning import (
    OpaqueProvisioningMaterial,
    V536_PROVISIONING_AUTHORIZATION_SCHEMA,
    V536ProvisioningError,
    WindowsCredWriteNativeBoundary,
    WindowsCredentialManagerWriter,
    canonical_provisioning_authorization_sha256,
    main,
    parse_v536_provisioning_authorization,
    provision_v536_credential,
    read_interactive_provisioning_material,
)


KEY_SENTINEL = "V536_KEY_SENTINEL"
SECRET_SENTINEL = "V536_SECRET_SENTINEL"
ACCOUNT_SENTINEL = "V536_ACCOUNT_SENTINEL"
NOW = datetime(2026, 8, 1, 11, tzinfo=UTC)


class FakeWriter:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.failure = failure
        self.calls: list[tuple[str, bytes]] = []

    def write(self, reference: object, record: bytearray) -> None:
        if self.failure is not None:
            raise self.failure
        self.calls.append((str(reference), bytes(record)))


class FakeNativeCredentialWriteBoundary:
    def __init__(
        self,
        *,
        error_code: int | None = None,
        failure: Exception | None = None,
    ) -> None:
        self.error_code = error_code
        self.failure = failure
        self.calls = 0
        self.references: list[str] = []
        self.saw_mutable_nonempty_record = False
        self.record_family: object = None
        self.record_field_names: tuple[str, ...] = ()
        self.record_schema: object = None

    def write(self, reference: object, record: bytearray) -> int | None:
        self.calls += 1
        self.references.append(str(reference))
        self.saw_mutable_nonempty_record = isinstance(record, bytearray) and bool(
            record
        )
        payload = json.loads(record)
        self.record_family = payload.get("family")
        self.record_field_names = tuple(sorted(payload))
        self.record_schema = payload.get("schema_version")
        if self.failure is not None:
            raise self.failure
        return self.error_code


def _payload(
    *,
    family: str = "alpaca-paper-observation",
) -> dict[str, object]:
    reference = f"wincred:algotrader/v5.35/{family}/production"
    payload: dict[str, object] = {
        "schema_version": V536_PROVISIONING_AUTHORIZATION_SCHEMA,
        "authorization_id": f"provision-{family}",
        "credential_reference": reference,
        "credential_family": family,
        "windows_principal": "DOMAIN\\canary-user",
        "source_commit_sha": "a" * 40,
        "source_tree_sha": "b" * 40,
        "not_before_utc": (NOW - timedelta(minutes=5)).isoformat(),
        "expires_at_utc": (NOW + timedelta(minutes=20)).isoformat(),
        "credential_write_authorized": True,
        "task_mutation_authorized": False,
        "network_authorized": False,
        "broker_authorized": False,
        "operator_approved": True,
        "canonical_authorization_sha256": "",
    }
    payload["canonical_authorization_sha256"] = (
        canonical_provisioning_authorization_sha256(payload)
    )
    return payload


def _rehash(payload: dict[str, object]) -> None:
    payload["canonical_authorization_sha256"] = (
        canonical_provisioning_authorization_sha256(payload)
    )


def _provenance() -> dict[str, object]:
    return {
        "source_commit_sha": "a" * 40,
        "source_tree_sha": "b" * 40,
        "source_worktree_clean": True,
    }


def _material(
    family: CredentialFamily = CredentialFamily.ALPACA_PAPER_OBSERVATION,
) -> OpaqueProvisioningMaterial:
    return OpaqueProvisioningMaterial(
        family=family,
        api_key_id=KEY_SENTINEL,
        api_secret_key=SECRET_SENTINEL,
        expected_account_id=(
            ACCOUNT_SENTINEL
            if family is CredentialFamily.ALPACA_PAPER_OBSERVATION
            else None
        ),
    )


def test_exact_provisioning_authorization_parses() -> None:
    authorization = parse_v536_provisioning_authorization(_payload())
    assert authorization.family is CredentialFamily.ALPACA_PAPER_OBSERVATION
    assert str(authorization.reference).endswith(
        "/alpaca-paper-observation/production"
    )


@pytest.mark.parametrize(
    ("field", "value", "classification"),
    (
        (
            "credential_reference",
            "<NON_SECRET_REFERENCE>",
            "provisioning_authorization_placeholder",
        ),
        (
            "credential_write_authorized",
            False,
            "provisioning_write_not_authorized",
        ),
        (
            "operator_approved",
            False,
            "provisioning_operator_approval_missing",
        ),
        ("network_authorized", True, "provisioning_scope_broadened"),
        ("broker_authorized", True, "provisioning_scope_broadened"),
        (
            "credential_family",
            "alpaca-market-data",
            "provisioning_credential_family_mismatch",
        ),
    ),
)
def test_provisioning_authorization_is_narrow_and_exact(
    field: str,
    value: object,
    classification: str,
) -> None:
    payload = _payload()
    payload[field] = value
    _rehash(payload)
    with pytest.raises(V536ProvisioningError, match=classification):
        parse_v536_provisioning_authorization(payload)


def test_opaque_material_is_one_use_redacted_and_zeroized() -> None:
    material = _material()
    assert KEY_SENTINEL not in repr(material)
    assert SECRET_SENTINEL not in str(material)
    captured: list[bytes] = []
    material.use(lambda record: captured.append(bytes(record)))
    assert material.closed
    assert bytes(material._key) == b""  # noqa: SLF001
    assert bytes(material._secret) == b""  # noqa: SLF001
    assert bytes(material._account) == b""  # noqa: SLF001
    parsed = json.loads(captured[0])
    assert parsed == {
        "schema_version": "v5_35_credential_record_v1",
        "family": "alpaca-paper-observation",
        "api_key_id": KEY_SENTINEL,
        "api_secret_key": SECRET_SENTINEL,
        "expected_account_id": ACCOUNT_SENTINEL,
    }
    with pytest.raises(V536ProvisioningError, match="provisioning_material_consumed"):
        material.use(lambda _record: None)


def test_market_material_rejects_account_and_paper_requires_account() -> None:
    with pytest.raises(
        V536ProvisioningError,
        match="provisioning_account_binding_unexpected",
    ):
        OpaqueProvisioningMaterial(
            family=CredentialFamily.ALPACA_MARKET_DATA,
            api_key_id=KEY_SENTINEL,
            api_secret_key=SECRET_SENTINEL,
            expected_account_id=ACCOUNT_SENTINEL,
        )
    with pytest.raises(
        V536ProvisioningError,
        match="provisioning_account_binding_missing",
    ):
        OpaqueProvisioningMaterial(
            family=CredentialFamily.ALPACA_PAPER_OBSERVATION,
            api_key_id=KEY_SENTINEL,
            api_secret_key=SECRET_SENTINEL,
            expected_account_id=None,
        )


def test_provisioning_calls_only_writer_and_returns_secret_free_receipt(
    capsys: pytest.CaptureFixture[str],
) -> None:
    authorization = parse_v536_provisioning_authorization(_payload())
    writer = FakeWriter()
    receipt = provision_v536_credential(
        authorization=authorization,
        material_source=_material,
        writer=writer,
        current_identity="domain\\CANARY-USER",
        provenance=_provenance(),
        clock=lambda: NOW,
    )
    assert len(writer.calls) == 1
    assert receipt["classification"] == "credential_record_provisioned"
    serialized = json.dumps(receipt, sort_keys=True)
    output = capsys.readouterr().out + capsys.readouterr().err
    for sentinel in (KEY_SENTINEL, SECRET_SENTINEL, ACCOUNT_SENTINEL):
        assert sentinel not in serialized
        assert sentinel not in output
    assert receipt["task_mutation_occurred"] is False
    assert receipt["network_access_occurred"] is False
    assert receipt["broker_access_occurred"] is False


def test_production_writer_accepts_injected_native_success_and_preserves_receipt(
    capsys: pytest.CaptureFixture[str],
) -> None:
    native = FakeNativeCredentialWriteBoundary()
    material = _material()
    receipt = provision_v536_credential(
        authorization=parse_v536_provisioning_authorization(_payload()),
        material_source=lambda: material,
        writer=WindowsCredentialManagerWriter(native_boundary=native),
        current_identity="DOMAIN\\canary-user",
        provenance=_provenance(),
        clock=lambda: NOW,
    )
    assert native.calls == 1
    assert native.saw_mutable_nonempty_record
    assert native.references == [
        "wincred:algotrader/v5.35/alpaca-paper-observation/production"
    ]
    assert native.record_schema == "v5_35_credential_record_v1"
    assert native.record_family == "alpaca-paper-observation"
    assert native.record_field_names == (
        "api_key_id",
        "api_secret_key",
        "expected_account_id",
        "family",
        "schema_version",
    )
    assert material.closed
    assert receipt["classification"] == "credential_record_provisioned"
    assert receipt["secret_values_exposed"] is False
    output = capsys.readouterr().out + capsys.readouterr().err
    serialized = json.dumps(receipt, sort_keys=True)
    for sentinel in (KEY_SENTINEL, SECRET_SENTINEL, ACCOUNT_SENTINEL):
        assert sentinel not in output
        assert sentinel not in serialized


@pytest.mark.parametrize(
    ("error_code", "classification"),
    (
        (5, "credential_writer_denied"),
        (87, "credential_writer_invalid_parameter"),
        (1004, "credential_writer_invalid_flags"),
        (1168, "credential_writer_preserved_target_missing"),
        (1312, "credential_writer_logon_session_unavailable"),
        (2202, "credential_writer_bad_username"),
    ),
)
def test_native_credwrite_failure_is_classified_without_disclosure(
    error_code: int,
    classification: str,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    native = FakeNativeCredentialWriteBoundary(error_code=error_code)
    material = _material()
    with pytest.raises(V536ProvisioningError) as captured:
        provision_v536_credential(
            authorization=parse_v536_provisioning_authorization(_payload()),
            material_source=lambda: material,
            writer=WindowsCredentialManagerWriter(native_boundary=native),
            current_identity="DOMAIN\\canary-user",
            provenance=_provenance(),
            clock=lambda: NOW,
        )
    assert str(captured.value) == classification
    assert captured.value.classification == classification
    assert str(error_code) not in str(captured.value)
    assert native.calls == 1
    assert material.closed
    output = capsys.readouterr().out + capsys.readouterr().err
    observables = (output, caplog.text, repr(captured.value))
    for sentinel in (KEY_SENTINEL, SECRET_SENTINEL, ACCOUNT_SENTINEL):
        assert all(sentinel not in observable for observable in observables)
        assert sentinel not in sys.argv
        assert all(sentinel not in value for value in os.environ.values())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("error_code", (0, 999_999, True, "87"))
def test_unknown_or_malformed_native_failure_is_generic(
    error_code: object,
) -> None:
    native = FakeNativeCredentialWriteBoundary()
    native.error_code = error_code  # type: ignore[assignment]
    with pytest.raises(V536ProvisioningError) as captured:
        _material().use(
            lambda record: WindowsCredentialManagerWriter(
                native_boundary=native
            ).write(
                parse_v536_provisioning_authorization(_payload()).reference,
                record,
            )
        )
    assert str(captured.value) == "credential_writer_failed"
    assert str(error_code) not in str(captured.value)
    assert native.calls == 1


def test_native_boundary_exception_is_generic_and_secret_free(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    native = FakeNativeCredentialWriteBoundary(
        failure=OSError(f"[WinError 5] {SECRET_SENTINEL}")
    )
    material = _material()
    with pytest.raises(V536ProvisioningError) as captured:
        material.use(
            lambda record: WindowsCredentialManagerWriter(
                native_boundary=native
            ).write(
                parse_v536_provisioning_authorization(_payload()).reference,
                record,
            )
        )
    assert str(captured.value) == "credential_writer_failed"
    output = capsys.readouterr().out + capsys.readouterr().err
    assert SECRET_SENTINEL not in output
    assert SECRET_SENTINEL not in caplog.text
    assert SECRET_SENTINEL not in repr(captured.value)
    assert material.closed


def test_writer_validation_precedes_injected_native_boundary() -> None:
    native = FakeNativeCredentialWriteBoundary()
    writer = WindowsCredentialManagerWriter(native_boundary=native)
    with pytest.raises(V536ProvisioningError, match="credential_reference_malformed"):
        writer.write(object(), bytearray(b"opaque"))  # type: ignore[arg-type]
    authorization = parse_v536_provisioning_authorization(_payload())
    with pytest.raises(V536ProvisioningError, match="credential_record_malformed"):
        writer.write(authorization.reference, bytearray())
    assert native.calls == 0


@pytest.mark.parametrize(
    ("change", "classification"),
    (
        ({"current_identity": "DOMAIN\\other"}, "provisioning_principal_mismatch"),
        (
            {"provenance": {**_provenance(), "source_worktree_clean": False}},
            "provisioning_source_dirty",
        ),
        (
            {"provenance": {**_provenance(), "source_commit_sha": "c" * 40}},
            "provisioning_source_commit_mismatch",
        ),
        (
            {"provenance": {**_provenance(), "source_tree_sha": "d" * 40}},
            "provisioning_source_tree_mismatch",
        ),
        (
            {"clock": lambda: NOW + timedelta(hours=2)},
            "provisioning_authorization_expired",
        ),
    ),
)
def test_runtime_mismatch_precedes_material_and_writer(
    change: dict[str, object],
    classification: str,
) -> None:
    authorization = parse_v536_provisioning_authorization(_payload())
    writer = FakeWriter()
    material_calls: list[bool] = []

    def source() -> OpaqueProvisioningMaterial:
        material_calls.append(True)
        return _material()

    values: dict[str, object] = {
        "authorization": authorization,
        "material_source": source,
        "writer": writer,
        "current_identity": "DOMAIN\\canary-user",
        "provenance": _provenance(),
        "clock": lambda: NOW,
    }
    values.update(change)
    with pytest.raises(V536ProvisioningError, match=classification):
        provision_v536_credential(**values)  # type: ignore[arg-type]
    assert material_calls == []
    assert writer.calls == []


def test_environment_alias_precedes_material_and_writer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALPACA_API_KEY", KEY_SENTINEL)
    writer = FakeWriter()
    calls: list[bool] = []
    with pytest.raises(
        V536ProvisioningError,
        match="credential_environment_alias_rejected",
    ):
        provision_v536_credential(
            authorization=parse_v536_provisioning_authorization(_payload()),
            material_source=lambda: calls.append(True),  # type: ignore[return-value]
            writer=writer,
            current_identity="DOMAIN\\canary-user",
            provenance=_provenance(),
            clock=lambda: NOW,
        )
    assert calls == []
    assert writer.calls == []


def test_unexpected_writer_failure_is_sanitized_and_material_is_closed() -> None:
    material = _material()
    writer = FakeWriter(failure=RuntimeError(SECRET_SENTINEL))
    with pytest.raises(V536ProvisioningError) as captured:
        provision_v536_credential(
            authorization=parse_v536_provisioning_authorization(_payload()),
            material_source=lambda: material,
            writer=writer,
            current_identity="DOMAIN\\canary-user",
            provenance=_provenance(),
            clock=lambda: NOW,
        )
    assert str(captured.value) == "credential_writer_failed"
    assert SECRET_SENTINEL not in repr(captured.value)
    assert material.closed


def test_interactive_reader_uses_no_echo_prompt_and_never_prints_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter((KEY_SENTINEL, SECRET_SENTINEL, ACCOUNT_SENTINEL))
    prompts: list[str] = []

    def prompt(label: str) -> str:
        prompts.append(label)
        return next(answers)

    material = read_interactive_provisioning_material(
        CredentialFamily.ALPACA_PAPER_OBSERVATION,
        prompt=prompt,
    )
    assert len(prompts) == 3
    output = capsys.readouterr().out + capsys.readouterr().err
    assert KEY_SENTINEL not in output
    assert SECRET_SENTINEL not in output
    assert ACCOUNT_SENTINEL not in output
    material.close()


def test_native_writer_uses_credwrite_directly_without_helpers_or_tempfiles() -> None:
    source = (
        inspect.getsource(WindowsCredWriteNativeBoundary)
        + inspect.getsource(WindowsCredentialManagerWriter)
    ).lower()
    assert "credwritew" in source
    assert "subprocess" not in source
    assert "powershell" not in source
    assert "tempfile" not in source
    assert "cmdkey" not in source
    forbidden_apis = ("credreadw", "credenumeratew", "creddeletew", "credrenamew")
    for forbidden_api in forbidden_apis:
        assert forbidden_api not in source


def test_cli_without_explicit_write_gate_never_loads_artifact_or_prompts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing.json"
    assert main(["--authorization-artifact", str(missing.resolve())]) == 2
    assert json.loads(capsys.readouterr().out) == {
        "classification": "provisioning_write_not_authorized"
    }
    assert not missing.exists()
