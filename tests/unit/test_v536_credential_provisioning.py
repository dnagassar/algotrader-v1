from __future__ import annotations

import ctypes
from datetime import UTC, datetime, timedelta
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys

import pytest

import algotrader.execution.v536_credential_provisioning as provisioning_module

from algotrader.execution.secure_credential_provider import CredentialFamily
from algotrader.execution.v536_credential_provisioning import (
    OpaqueProvisioningMaterial,
    V536_PROVISIONING_AUTHORIZATION_SCHEMA,
    V536ProvisioningError,
    WindowsCredWriteNativeBoundary,
    WindowsCredentialManagerWriter,
    canonical_provisioning_authorization_sha256,
    constant_width_masked_prompt,
    load_runtime_bound_source_provenance,
    main,
    parse_v536_provisioning_authorization,
    provision_v536_credential,
    read_interactive_provisioning_material,
    validate_runtime_authorization_source_binding,
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


class FakeCredWriteCallable:
    def __init__(
        self,
        *,
        result: int = 1,
        failure: Exception | None = None,
        capture_record: bool = False,
    ) -> None:
        self.result = result
        self.failure = failure
        self.capture_record = capture_record
        self.calls = 0
        self.argtypes: object = None
        self.restype: object = None
        self.observed_record: bytes | None = None

    def __call__(self, *args: object) -> int:
        self.calls += 1
        if self.capture_record:
            credential = getattr(args[0], "_obj")
            self.observed_record = ctypes.string_at(
                credential.CredentialBlob,
                credential.CredentialBlobSize,
            )
        if self.failure is not None:
            raise self.failure
        return self.result


class FakeWindowsCredentialLibrary:
    def __init__(self, cred_write: FakeCredWriteCallable) -> None:
        self.CredWriteW = cred_write


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


def test_production_native_boundary_accepts_fake_library_without_vault_access() -> None:
    cred_write = FakeCredWriteCallable(result=1)
    native = WindowsCredWriteNativeBoundary(
        native_library_loader=lambda: FakeWindowsCredentialLibrary(cred_write),
    )
    material = _material()

    receipt = provision_v536_credential(
        authorization=parse_v536_provisioning_authorization(_payload()),
        material_source=lambda: material,
        writer=WindowsCredentialManagerWriter(native_boundary=native),
        current_identity="DOMAIN\\canary-user",
        provenance=_provenance(),
        clock=lambda: NOW,
    )

    assert cred_write.calls == 1
    assert cred_write.argtypes is not None
    assert cred_write.restype is not None
    assert material.closed
    assert receipt["classification"] == "credential_record_provisioned"
    assert receipt["secret_values_exposed"] is False


def test_production_direct_address_allows_immediate_clear() -> None:
    cred_write = FakeCredWriteCallable(result=1, capture_record=True)
    native = WindowsCredWriteNativeBoundary(
        native_library_loader=lambda: FakeWindowsCredentialLibrary(cred_write),
    )
    record = bytearray(b"synthetic-record")

    native.write(
        parse_v536_provisioning_authorization(_payload()).reference,
        record,
    )
    for index in range(len(record)):
        record[index] = 0
    record.clear()

    assert cred_write.calls == 1
    assert cred_write.observed_record == b"synthetic-record"
    assert record == bytearray()


def test_production_native_setup_failure_is_fixed_and_precedes_credwrite(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    cred_write = FakeCredWriteCallable()
    loader_calls = 0

    def fail_loader() -> object:
        nonlocal loader_calls
        loader_calls += 1
        raise OSError(f"native setup {SECRET_SENTINEL}")

    native = WindowsCredWriteNativeBoundary(native_library_loader=fail_loader)
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

    assert captured.value.classification == "credential_writer_native_setup_failed"
    assert loader_calls == 1
    assert cred_write.calls == 0
    assert material.closed
    captured_io = capsys.readouterr()
    observables = (
        captured_io.out,
        captured_io.err,
        caplog.text,
        repr(captured.value),
    )
    assert all(SECRET_SENTINEL not in observable for observable in observables)


def test_production_bytearray_address_failure_is_fixed_before_credwrite() -> None:
    cred_write = FakeCredWriteCallable()
    native = WindowsCredWriteNativeBoundary(
        native_library_loader=lambda: FakeWindowsCredentialLibrary(cred_write),
        bytearray_address_resolver=lambda _record: None,
    )
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

    assert captured.value.classification == "credential_writer_native_setup_failed"
    assert cred_write.calls == 0
    assert material.closed


def test_production_native_invocation_failure_is_fixed_after_one_fake_call(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    cred_write = FakeCredWriteCallable(
        failure=OSError(f"native invocation {SECRET_SENTINEL}")
    )
    native = WindowsCredWriteNativeBoundary(
        native_library_loader=lambda: FakeWindowsCredentialLibrary(cred_write),
    )
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

    assert (
        captured.value.classification
        == "credential_writer_native_invocation_failed"
    )
    assert cred_write.calls == 1
    assert material.closed
    captured_io = capsys.readouterr()
    observables = (
        captured_io.out,
        captured_io.err,
        caplog.text,
        repr(captured.value),
    )
    assert all(SECRET_SENTINEL not in observable for observable in observables)


def test_production_unknown_native_error_is_fixed_without_raw_code(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    unknown_code = 999_999
    cred_write = FakeCredWriteCallable(result=0)
    native = WindowsCredWriteNativeBoundary(
        native_library_loader=lambda: FakeWindowsCredentialLibrary(cred_write),
        last_error_reader=lambda: unknown_code,
    )
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

    assert (
        captured.value.classification
        == "credential_writer_unknown_native_failure"
    )
    assert str(unknown_code) not in str(captured.value)
    assert cred_write.calls == 1
    assert material.closed
    captured_io = capsys.readouterr()
    observables = (
        captured_io.out,
        captured_io.err,
        caplog.text,
        repr(captured.value),
    )
    for sentinel in (KEY_SENTINEL, SECRET_SENTINEL, ACCOUNT_SENTINEL):
        assert all(sentinel not in observable for observable in observables)


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


@pytest.mark.parametrize("error_code", (0, 999_999))
def test_unknown_integer_native_failure_has_fixed_classification(
    error_code: int,
) -> None:
    native = FakeNativeCredentialWriteBoundary()
    native.error_code = error_code
    with pytest.raises(V536ProvisioningError) as captured:
        _material().use(
            lambda record: WindowsCredentialManagerWriter(
                native_boundary=native
            ).write(
                parse_v536_provisioning_authorization(_payload()).reference,
                record,
            )
        )
    assert str(captured.value) == "credential_writer_unknown_native_failure"
    assert str(error_code) not in str(captured.value)
    assert native.calls == 1


@pytest.mark.parametrize("error_code", (True, "87"))
def test_malformed_native_failure_is_generic(error_code: object) -> None:
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


def test_unapproved_native_boundary_classification_is_generic() -> None:
    native = FakeNativeCredentialWriteBoundary(
        failure=V536ProvisioningError("credential_writer_denied")
    )
    with pytest.raises(V536ProvisioningError) as captured:
        _material().use(
            lambda record: WindowsCredentialManagerWriter(
                native_boundary=native
            ).write(
                parse_v536_provisioning_authorization(_payload()).reference,
                record,
            )
        )
    assert captured.value.classification == "credential_writer_failed"
    assert native.calls == 1


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


def test_constant_width_masked_prompt_reveals_presence_not_value_or_length() -> None:
    characters = iter(KEY_SENTINEL + "\r")
    output: list[str] = []

    value = constant_width_masked_prompt(
        "API key ID: ",
        read_character=lambda: next(characters),
        write_output=output.append,
    )

    assert value == KEY_SENTINEL
    assert "".join(output) == "API key ID: *\n"
    assert KEY_SENTINEL not in "".join(output)
    assert len(KEY_SENTINEL) > "".join(output).count("*")


def test_constant_width_mask_tracks_only_empty_nonempty_transitions() -> None:
    characters = iter(("A", "B", "\b", "C", "\b", "\b", "D", "\r"))
    output: list[str] = []

    value = constant_width_masked_prompt(
        "Field: ",
        read_character=lambda: next(characters),
        write_output=output.append,
    )

    assert value == "D"
    assert "".join(output) == "Field: *\b \b*\n"


def test_constant_width_mask_ignores_windows_extended_key_pair() -> None:
    characters = iter(("\x00", "K", "A", "\r"))
    output: list[str] = []

    value = constant_width_masked_prompt(
        "Field: ",
        read_character=lambda: next(characters),
        write_output=output.append,
    )

    assert value == "A"
    assert "".join(output) == "Field: *\n"


@pytest.mark.parametrize(
    ("characters", "classification"),
    (
        (("\r",), "provisioning_masked_input_empty"),
        (("A", " ", "\r"), "provisioning_masked_input_invalid"),
        (("\x03",), "provisioning_masked_input_interrupted"),
        (("\x1a",), "provisioning_masked_input_interrupted"),
        (("AB",), "provisioning_masked_input_invalid"),
    ),
)
def test_constant_width_masked_prompt_failures_are_fixed_and_secret_free(
    characters: tuple[str, ...],
    classification: str,
) -> None:
    values = iter(characters)
    output: list[str] = []

    with pytest.raises(V536ProvisioningError) as captured:
        constant_width_masked_prompt(
            "Field: ",
            read_character=lambda: next(values),
            write_output=output.append,
        )

    assert str(captured.value) == classification
    assert KEY_SENTINEL not in repr(captured.value)
    assert KEY_SENTINEL not in "".join(output)


@pytest.mark.parametrize(
    ("failure", "classification"),
    (
        (EOFError(SECRET_SENTINEL), "provisioning_masked_input_interrupted"),
        (
            KeyboardInterrupt(SECRET_SENTINEL),
            "provisioning_masked_input_interrupted",
        ),
        (
            RuntimeError(SECRET_SENTINEL),
            "provisioning_masked_input_unavailable",
        ),
    ),
)
def test_constant_width_masked_reader_exceptions_are_sanitized(
    failure: BaseException,
    classification: str,
) -> None:
    def fail() -> str:
        raise failure

    with pytest.raises(V536ProvisioningError) as captured:
        constant_width_masked_prompt(
            "Field: ",
            read_character=fail,
            write_output=lambda _value: None,
        )

    assert str(captured.value) == classification
    assert SECRET_SENTINEL not in repr(captured.value)


def test_constant_width_masked_writer_failure_precedes_character_read() -> None:
    reads: list[bool] = []

    def fail(_value: str) -> None:
        raise RuntimeError(SECRET_SENTINEL)

    with pytest.raises(V536ProvisioningError) as captured:
        constant_width_masked_prompt(
            "Field: ",
            read_character=lambda: reads.append(True) or "A",
            write_output=fail,
        )

    assert str(captured.value) == "provisioning_masked_output_unavailable"
    assert SECRET_SENTINEL not in repr(captured.value)
    assert reads == []


def test_constant_width_masked_prompt_rejects_overlong_input() -> None:
    characters = iter(("A",) * 4097)
    output: list[str] = []

    with pytest.raises(
        V536ProvisioningError,
        match="provisioning_masked_input_too_long",
    ):
        constant_width_masked_prompt(
            "Field: ",
            read_character=lambda: next(characters),
            write_output=output.append,
        )

    assert "".join(output) == "Field: *\n"


def test_interactive_reader_uses_injected_secret_source_and_never_prints_values(
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


def test_interactive_reader_integrates_three_constant_width_masked_fields() -> None:
    answers = iter((KEY_SENTINEL, SECRET_SENTINEL, ACCOUNT_SENTINEL))
    output: list[str] = []

    def prompt(label: str) -> str:
        characters = iter(next(answers) + "\r")
        return constant_width_masked_prompt(
            label,
            read_character=lambda: next(characters),
            write_output=output.append,
        )

    material = read_interactive_provisioning_material(
        CredentialFamily.ALPACA_PAPER_OBSERVATION,
        prompt=prompt,
    )

    assert "".join(output) == (
        "API key ID: *\n"
        "API secret key: *\n"
        "Expected paper account identity: *\n"
    )
    for sentinel in (KEY_SENTINEL, SECRET_SENTINEL, ACCOUNT_SENTINEL):
        assert sentinel not in "".join(output)
    material.close()


def test_masked_prompt_failure_precedes_writer_factory() -> None:
    writer_factory_calls: list[bool] = []

    with pytest.raises(
        V536ProvisioningError,
        match="provisioning_masked_input_empty",
    ):
        provision_v536_credential(
            authorization=parse_v536_provisioning_authorization(_payload()),
            material_source=lambda: constant_width_masked_prompt(  # type: ignore[return-value]
                "Field: ",
                read_character=lambda: "\r",
                write_output=lambda _value: None,
            ),
            writer=None,
            writer_factory=lambda: writer_factory_calls.append(True),  # type: ignore[return-value]
            current_identity="DOMAIN\\canary-user",
            provenance=_provenance(),
            clock=lambda: NOW,
        )

    assert writer_factory_calls == []


def test_writer_factory_runs_after_material_acquisition() -> None:
    events: list[str] = []
    writer = FakeWriter()

    receipt = provision_v536_credential(
        authorization=parse_v536_provisioning_authorization(_payload()),
        material_source=lambda: events.append("material") or _material(),
        writer=None,
        writer_factory=lambda: events.append("writer_factory") or writer,
        current_identity="DOMAIN\\canary-user",
        provenance=_provenance(),
        clock=lambda: NOW,
    )

    assert events == ["material", "writer_factory"]
    assert len(writer.calls) == 1
    assert receipt["classification"] == "credential_record_provisioned"


def test_masked_prompt_has_no_visible_or_redirected_input_fallback() -> None:
    source = inspect.getsource(constant_width_masked_prompt).lower()
    assert "getpass" not in source
    assert "read-host" not in source
    assert "input(" not in source
    assert "subprocess" not in source
    assert "clipboard" not in source


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
    assert "from_buffer" not in source
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


def _runtime_binding_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, dict[str, object]]:
    root = tmp_path / "deployment"
    module_path = (
        root / "src" / "algotrader" / "execution" / "v536_credential_provisioning.py"
    )
    launcher_path = root / "scripts" / "launch_v536_credential_provisioning.py"
    module_path.parent.mkdir(parents=True)
    launcher_path.parent.mkdir(parents=True)
    module_path.write_bytes(b"module fixture\r\n")
    launcher_path.write_bytes(b"launcher fixture\r\n")

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()

    provenance: dict[str, object] = {
        "source_commit_sha": "a" * 40,
        "source_tree_sha": "b" * 40,
        "source_worktree_clean": True,
        "source_bundle_manifest": {
            "src/algotrader/execution/v536_credential_provisioning.py": digest(
                module_path
            ),
            "scripts/launch_v536_credential_provisioning.py": digest(launcher_path),
        },
    }
    return root, module_path, provenance


def test_runtime_source_binding_accepts_exact_module_launcher_and_digests(
    tmp_path: Path,
) -> None:
    root, module_path, provenance = _runtime_binding_fixture(tmp_path)
    result = load_runtime_bound_source_provenance(
        root,
        module_path=module_path,
        provenance_loader=lambda _root: provenance,
    )
    assert result == provenance


def test_runtime_source_binding_rejects_wrong_module_before_provenance(
    tmp_path: Path,
) -> None:
    root, _module_path, _provenance = _runtime_binding_fixture(tmp_path)
    calls: list[Path] = []
    wrong_module = tmp_path / "ambient" / "v536_credential_provisioning.py"
    wrong_module.parent.mkdir()
    wrong_module.write_text("ambient", encoding="utf-8")
    with pytest.raises(
        V536ProvisioningError,
        match="provisioning_runtime_source_mismatch",
    ):
        load_runtime_bound_source_provenance(
            root,
            module_path=wrong_module,
            provenance_loader=lambda candidate: calls.append(candidate),  # type: ignore[return-value]
        )
    assert calls == []


@pytest.mark.parametrize(
    ("mutation", "classification"),
    (
        ("missing_launcher", "provisioning_runtime_source_manifest_missing"),
        ("wrong_digest", "provisioning_runtime_source_digest_mismatch"),
        ("dirty", "provisioning_runtime_source_dirty"),
        ("bad_commit", "provisioning_runtime_source_mismatch"),
    ),
)
def test_runtime_source_binding_fails_closed_on_provenance_mismatch(
    mutation: str,
    classification: str,
    tmp_path: Path,
) -> None:
    root, module_path, provenance = _runtime_binding_fixture(tmp_path)
    manifest = provenance["source_bundle_manifest"]
    assert isinstance(manifest, dict)
    if mutation == "missing_launcher":
        manifest.pop("scripts/launch_v536_credential_provisioning.py")
    elif mutation == "wrong_digest":
        manifest["src/algotrader/execution/v536_credential_provisioning.py"] = (
            "c" * 64
        )
    elif mutation == "dirty":
        provenance["source_worktree_clean"] = False
    else:
        provenance["source_commit_sha"] = "invalid"
    with pytest.raises(V536ProvisioningError, match=classification):
        load_runtime_bound_source_provenance(
            root,
            module_path=module_path,
            provenance_loader=lambda _root: provenance,
        )


def test_runtime_source_loader_exception_is_sanitized(
    tmp_path: Path,
) -> None:
    root, module_path, _provenance = _runtime_binding_fixture(tmp_path)

    def fail(_root: Path) -> dict[str, object]:
        raise RuntimeError(f"{SECRET_SENTINEL}:{module_path}")

    with pytest.raises(V536ProvisioningError) as captured:
        load_runtime_bound_source_provenance(
            root,
            module_path=module_path,
            provenance_loader=fail,
        )
    assert str(captured.value) == "provisioning_runtime_source_unavailable"
    assert SECRET_SENTINEL not in repr(captured.value)
    assert str(module_path) not in repr(captured.value)


def test_runtime_source_failure_precedes_artifact_identity_material_and_writer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[str] = []

    def fail_runtime(_root: object) -> dict[str, object]:
        raise V536ProvisioningError("provisioning_runtime_source_mismatch")

    monkeypatch.setattr(
        provisioning_module,
        "load_runtime_bound_source_provenance",
        fail_runtime,
    )
    monkeypatch.setattr(
        provisioning_module,
        "load_v536_provisioning_authorization",
        lambda _path: calls.append("artifact"),
    )
    monkeypatch.setattr(
        provisioning_module,
        "current_windows_identity",
        lambda: calls.append("identity"),
    )
    monkeypatch.setattr(
        provisioning_module,
        "read_interactive_provisioning_material",
        lambda _family: calls.append("material"),
    )
    monkeypatch.setattr(
        provisioning_module,
        "WindowsCredentialManagerWriter",
        lambda: calls.append("writer"),
    )
    result = provisioning_module.main(
        [
            "--authorization-artifact",
            str((tmp_path / "missing.json").resolve()),
            "--provision-authorized",
        ],
        expected_repo_root=tmp_path,
    )
    assert result == 2
    assert calls == []
    output = capsys.readouterr().out + capsys.readouterr().err
    assert json.loads(output) == {
        "classification": "provisioning_runtime_source_mismatch"
    }
    assert SECRET_SENTINEL not in output


@pytest.mark.parametrize(
    ("field", "value", "classification"),
    (
        ("source_worktree_clean", False, "provisioning_source_dirty"),
        ("source_commit_sha", "c" * 40, "provisioning_source_commit_mismatch"),
        ("source_tree_sha", "d" * 40, "provisioning_source_tree_mismatch"),
    ),
)
def test_runtime_authorization_source_binding_precedes_identity(
    field: str,
    value: object,
    classification: str,
) -> None:
    provenance = _provenance()
    provenance[field] = value
    with pytest.raises(V536ProvisioningError, match=classification):
        validate_runtime_authorization_source_binding(
            parse_v536_provisioning_authorization(_payload()),
            provenance,
        )
