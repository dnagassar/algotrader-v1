from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from threading import Lock
from types import SimpleNamespace

import pytest

from algotrader.execution.secure_credential_provider import (
    CREDENTIAL_RECORD_SCHEMA,
    CredentialFamily,
    CredentialProviderError,
    CredentialReference,
    lease_from_test_record,
)
from algotrader.execution.v535_unattended_readonly import PaperObservationFacts
from algotrader.execution.v536_canary_authorization import (
    V536_AUTHORIZATION_SCHEMA,
    V536AuthorizationError,
    canonical_authorization_sha256,
    load_v536_authorization,
    parse_v536_authorization,
)
from algotrader.execution.v536_windows_host_canary import (
    V536CanaryError,
    V536CanaryStateStore,
    arm_v536_exact_window,
    attest_v536_task_disabled,
    execute_v536_canary,
    install_v536_task_disabled,
    main,
    post_run_attest_v536_canary,
    validate_v536_pending_packet,
)
from algotrader.execution.v536_windows_task import (
    V536TaskError,
    V536TaskSnapshot,
    V536TaskSpec,
    build_v536_task_spec,
)
from algotrader.orchestration.crypto_tournament_v2_oos_scheduler import (
    RealCommandDispatcher,
)


KEY_SENTINEL = "V536_CANARY_KEY_SENTINEL"
SECRET_SENTINEL = "V536_CANARY_SECRET_SENTINEL"
ACCOUNT_SENTINEL = "V536_CANARY_ACCOUNT_SENTINEL"
WINDOW_START = datetime(2026, 8, 1, 12, tzinfo=UTC)
SCHEDULED_START = WINDOW_START + timedelta(hours=1, minutes=5)
SAFETY_FIELDS = (
    "broker_mutation_authorized",
    "broker_mutation_occurred",
    "paper_submit_authorized",
    "paper_submit_occurred",
    "paper_cancel_occurred",
    "paper_replace_occurred",
    "paper_close_occurred",
    "paper_liquidate_occurred",
    "live_authorized",
    "live_endpoint_touched",
)


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class FakeProvider:
    provider_name = "windows-credential-manager"

    def __init__(self, *, failure: str | None = None) -> None:
        self.failure = failure
        self.validate_count = 0
        self.open_count = 0
        self._lock = Lock()

    def _lease(
        self,
        reference: CredentialReference,
        expected_family: CredentialFamily | str,
    ):
        family = CredentialFamily(expected_family)
        if self.failure:
            raise CredentialProviderError(self.failure)
        record: dict[str, object] = {
            "schema_version": CREDENTIAL_RECORD_SCHEMA,
            "family": family.value,
            "api_key_id": KEY_SENTINEL,
            "api_secret_key": SECRET_SENTINEL,
        }
        if family is CredentialFamily.ALPACA_PAPER_OBSERVATION:
            record["expected_account_id"] = ACCOUNT_SENTINEL
        return lease_from_test_record(
            record,
            reference=reference,
            expected_family=family,
        )

    def validate(
        self,
        reference: CredentialReference,
        *,
        expected_family: CredentialFamily | str,
    ) -> None:
        with self._lock:
            self.validate_count += 1
        self._lease(reference, expected_family).use(lambda *_: None)

    def open(
        self,
        reference: CredentialReference,
        *,
        expected_family: CredentialFamily | str,
    ):
        with self._lock:
            self.open_count += 1
        return self._lease(reference, expected_family)


class FakeProcessRunner:
    def __init__(self, *, exit_code: int = 0) -> None:
        self.exit_code = exit_code
        self.call_count = 0
        self.calls: list[dict[str, object]] = []
        self._lock = Lock()

    def __call__(self, argv: list[str], **kwargs: object) -> object:
        with self._lock:
            self.call_count += 1
            self.calls.append(
                {
                    "argv": list(argv),
                    "env": dict(kwargs["env"]),  # type: ignore[arg-type]
                }
            )
        if self.exit_code:
            return SimpleNamespace(
                returncode=self.exit_code,
                stdout=SECRET_SENTINEL,
                stderr=KEY_SENTINEL,
            )
        output_root = Path(argv[argv.index("--output-root") + 1])
        as_of = argv[argv.index("--as-of") + 1]
        output_root.mkdir(parents=True, exist_ok=True)
        (output_root / "operating_packet.json").write_text(
            json.dumps({"as_of": as_of}, sort_keys=True),
            encoding="utf-8",
        )
        (output_root / "frozen_state.json").write_text(
            json.dumps({"updated_at": as_of}, sort_keys=True),
            encoding="utf-8",
        )
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "market_data_fetch_occurred": True,
                    "network_access_attempted": True,
                    **{field: False for field in SAFETY_FIELDS},
                },
                sort_keys=True,
            ),
            stderr=SECRET_SENTINEL,
        )


class FakePaperHttp:
    def __init__(self, *, flat: bool = True) -> None:
        self.flat = flat
        self.call_count = 0
        self._lock = Lock()

    def observe(
        self,
        *,
        api_key_id: str,
        api_secret_key: str,
        expected_account_id: str,
        paper_endpoint: str,
        clock,
    ) -> PaperObservationFacts:
        assert api_key_id == KEY_SENTINEL
        assert api_secret_key == SECRET_SENTINEL
        assert expected_account_id == ACCOUNT_SENTINEL
        assert paper_endpoint == "https://paper-api.alpaca.markets"
        with self._lock:
            self.call_count += 1
        return PaperObservationFacts(
            observed_at=clock(),
            account_match=True,
            account_active=True,
            account_flat_reconciled=self.flat,
            position_count=0 if self.flat else 1,
            open_order_count=0,
            target_asset_valid=True,
            account_read_count=1,
            positions_read_count=1,
            orders_read_count=1,
            asset_read_count=1,
        )


class FakeScheduler:
    def __init__(self) -> None:
        self.spec: V536TaskSpec | None = None
        self.phase = "missing"
        self.install_count = 0
        self.arm_count = 0
        self.disarm_count = 0
        self.read_count = 0
        self.fail_install = False
        self.fail_arm = False
        self.fail_disarm = False
        self.last_task_result = 0
        self._lock = Lock()

    def install_disabled(self, spec: V536TaskSpec) -> None:
        with self._lock:
            self.install_count += 1
            self.spec = spec
            if self.fail_install:
                raise V536TaskError("task_install_failed")
            self.phase = "disabled"

    def read(self, task_identity: str) -> V536TaskSnapshot:
        with self._lock:
            self.read_count += 1
            spec = self.spec
            phase = self.phase
        if spec is None or task_identity != spec.task_identity:
            raise V536TaskError("task_read_failed")
        values: dict[str, object] = {
            "task_identity": spec.task_identity,
            "principal": spec.principal,
            "logon_type": spec.logon_type,
            "run_level": "LeastPrivilege",
            "task_enabled": False,
            "trigger_enabled": False,
            "trigger_start": spec.trigger_start,
            "trigger_end": spec.trigger_end,
            "state": "Disabled",
            "action_execute": spec.action_execute,
            "action_arguments": spec.action_arguments,
            "working_directory": spec.working_directory,
            "allow_start_on_demand": False,
            "restart_on_failure": False,
            "multiple_instances_policy": spec.multiple_instances_policy,
            "execution_time_limit": spec.execution_time_limit,
            "last_task_result": self.last_task_result,
            "last_run_time": None,
            "next_run_time": None,
            "observed_at": spec.trigger_start - timedelta(minutes=1),
        }
        if phase == "armed":
            values.update(
                task_enabled=True,
                trigger_enabled=True,
                state="Ready",
                next_run_time=spec.trigger_start,
            )
        elif phase == "running":
            values.update(
                task_enabled=True,
                trigger_enabled=True,
                state="Running",
                last_task_result=267009,
                last_run_time=spec.trigger_start,
                observed_at=spec.trigger_start + timedelta(minutes=1),
            )
        elif phase == "post_run":
            values.update(
                last_run_time=spec.trigger_start,
                observed_at=spec.trigger_start + timedelta(minutes=3),
            )
        return V536TaskSnapshot(**values)  # type: ignore[arg-type]

    def arm(self, task_identity: str) -> None:
        with self._lock:
            self.arm_count += 1
            if self.fail_arm:
                raise V536TaskError("task_arm_failed")
            assert self.spec is not None
            assert task_identity == self.spec.task_identity
            self.phase = "armed"

    def disarm(self, task_identity: str) -> None:
        with self._lock:
            self.disarm_count += 1
            if self.fail_disarm:
                raise V536TaskError("task_disarm_failed")
            if self.spec is not None:
                assert task_identity == self.spec.task_identity
                self.phase = "post_run" if self.phase == "running" else "disabled"


def _authorization(root: Path):  # type: ignore[no-untyped-def]
    wrapper = root / "scripts" / "run_v536_windows_host_canary.ps1"
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text("# test wrapper\n", encoding="utf-8")
    artifact = root / "runs" / "v5_36_authorization.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "schema_version": V536_AUTHORIZATION_SCHEMA,
        "authorization_id": "v536-canary-test",
        "task_identity": "\\crypto-tournament-v2-oos-scheduler",
        "target_window_start_utc": WINDOW_START.isoformat(),
        "target_window_end_utc": (WINDOW_START + timedelta(hours=1)).isoformat(),
        "scheduled_start_utc": SCHEDULED_START.isoformat(),
        "automatic_disarm_deadline_utc": (
            SCHEDULED_START + timedelta(minutes=40)
        ).isoformat(),
        "windows_principal": "DOMAIN\\canary-user",
        "credential_vault_owner": "DOMAIN\\canary-user",
        "task_logon_type": "InteractiveToken",
        "deployment_root": str(root.resolve()),
        "source_commit_sha": "a" * 40,
        "source_tree_sha": "b" * 40,
        "credential_provider": "windows-credential-manager",
        "market_data_credential_reference": (
            "wincred:algotrader/v5.35/alpaca-market-data/offline-canary"
        ),
        "paper_credential_reference": (
            "wincred:algotrader/v5.35/alpaca-paper-observation/offline-canary"
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
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    return parse_v536_authorization(payload, artifact_path=artifact.resolve())


def _provenance() -> dict[str, object]:
    return {
        "source_commit_sha": "a" * 40,
        "source_tree_sha": "b" * 40,
        "source_worktree_clean": True,
        "source_branch_or_detached": "codex/v5.36-windows-host-canary",
        "adapter_source_bundle_sha256": "c" * 64,
        "source_bundle_manifest": {"safe.py": "d" * 64},
    }


def _dispatcher(provider: FakeProvider, runner: FakeProcessRunner, authorization):  # type: ignore[no-untyped-def]
    return RealCommandDispatcher(
        scheduler_enabled=True,
        market_data_read_authorized=True,
        credential_reference=authorization.market_data_reference,
        credential_provider=provider,
        credential_provider_name=authorization.credential_provider,
        app_profile="paper",
        paper_endpoint=authorization.paper_endpoint,
        market_data_endpoint=authorization.market_data_endpoint,
        process_runner=runner,
    )


def _install_and_arm(
    root: Path,
    *,
    provider: FakeProvider | None = None,
):
    authorization = _authorization(root)
    scheduler = FakeScheduler()
    store = V536CanaryStateStore(
        root / "runs" / "v5_36_windows_host_canary" / "canary_state.sqlite3"
    )
    clock = FixedClock(SCHEDULED_START - timedelta(hours=1))
    install = install_v536_task_disabled(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        provenance_reader=_provenance,
        current_identity="domain\\CANARY-USER",
        clock=clock,
        owner_id_factory=lambda: "install-owner",
    )
    assert install["classification"] == "task_installed_disabled"
    clock.now = SCHEDULED_START - timedelta(minutes=5)
    actual_provider = provider or FakeProvider()
    arm = arm_v536_exact_window(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        credential_provider=actual_provider,
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
        owner_id_factory=lambda: "arm-owner",
    )
    return authorization, scheduler, store, actual_provider, clock, arm


def test_complete_offline_production_flow_survives_restart_and_post_run_attests(
    tmp_path: Path,
) -> None:
    authorization, scheduler, store, provider, clock, arm = _install_and_arm(tmp_path)
    assert arm["classification"] == "task_armed_exact_window"
    scheduler.phase = "running"
    clock.now = SCHEDULED_START + timedelta(minutes=1)
    runner = FakeProcessRunner()
    paper = FakePaperHttp()
    pending = execute_v536_canary(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        dispatcher=_dispatcher(provider, runner, authorization),
        credential_provider=provider,
        paper_http_boundary=paper,
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
        invocation_id_factory=lambda: "execute-owner",
    )
    assert pending["classification"] == (
        "canary_reads_complete_pending_terminal_attestation"
    )
    assert pending["production_dispatcher"] == "RealCommandDispatcher"
    assert pending["task_terminal_result_deferred"] is True
    assert scheduler.disarm_count == 1
    assert scheduler.phase == "post_run"
    assert runner.call_count == 1
    assert paper.call_count == 1
    validation = validate_v536_pending_packet(
        tmp_path
        / "runs"
        / "v5_36_windows_host_canary"
        / "pending"
        / "pending_v536-canary-test.json",
        output_root=tmp_path / "runs" / "v5_36_windows_host_canary",
        authorization=authorization,
    )
    assert validation.valid, validation.errors

    # Reconstruct the durable store and perform credential-free terminal review.
    restarted_store = V536CanaryStateStore(store.path)
    clock.now = SCHEDULED_START + timedelta(minutes=3)
    final = post_run_attest_v536_canary(
        authorization=authorization,
        scheduler=scheduler,
        state_store=restarted_store,
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
    )
    assert final["classification"] == (
        "scheduled_read_only_canary_commissioning_complete"
    )
    assert final["execution_count"] == 1
    assert final["task_disarmed"] is True
    assert final["second_run_possible"] is False
    assert restarted_store.read(authorization)["status"] == "finalized"
    assert all(final[field] is False for field in SAFETY_FIELDS)

    persisted = b"".join(
        path.read_bytes()
        for path in (tmp_path / "runs").rglob("*")
        if path.is_file()
    )
    for sentinel in (KEY_SENTINEL, SECRET_SENTINEL, ACCOUNT_SENTINEL):
        assert sentinel.encode() not in persisted
        assert sentinel not in json.dumps(final, sort_keys=True)
        assert sentinel not in json.dumps(runner.calls, sort_keys=True)
    assert not list((tmp_path / "runs").rglob("*.tmp"))


def test_install_is_disabled_and_read_only_attestation_does_not_mutate(
    tmp_path: Path,
) -> None:
    authorization = _authorization(tmp_path)
    scheduler = FakeScheduler()
    store = V536CanaryStateStore(tmp_path / "state.sqlite3")
    clock = FixedClock(SCHEDULED_START - timedelta(hours=1))
    receipt = install_v536_task_disabled(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
        owner_id_factory=lambda: "install-one",
    )
    assert receipt["classification"] == "task_installed_disabled"
    assert receipt["task_scheduler_mutation_occurred"] is True
    assert scheduler.phase == "disabled"
    before = (scheduler.install_count, scheduler.arm_count, scheduler.disarm_count)
    attestation = attest_v536_task_disabled(
        authorization=authorization,
        scheduler=scheduler,
        provenance_reader=_provenance,
        current_identity="domain\\CANARY-user",
        clock=clock,
    )
    assert attestation["classification"] == "task_disabled_attested"
    assert attestation["task_scheduler_mutation_occurred"] is False
    assert before == (
        scheduler.install_count,
        scheduler.arm_count,
        scheduler.disarm_count,
    )


def test_duplicate_install_is_immutable_no_op_without_scheduler_mutation(
    tmp_path: Path,
) -> None:
    authorization = _authorization(tmp_path)
    scheduler = FakeScheduler()
    store = V536CanaryStateStore(tmp_path / "state.sqlite3")
    clock = FixedClock(SCHEDULED_START - timedelta(hours=1))
    first = install_v536_task_disabled(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
        owner_id_factory=lambda: "install-one",
    )
    second = install_v536_task_disabled(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
        owner_id_factory=lambda: "install-two",
    )
    assert first["classification"] == "task_installed_disabled"
    assert second["classification"] == "duplicate_lifecycle_no_op"
    assert second["task_mutation_occurred"] is False
    assert scheduler.install_count == 1


@pytest.mark.parametrize(
    "failure",
    (
        "credential_provider_unavailable",
        "credential_provider_denied",
        "credential_record_malformed",
        "credential_family_mismatch",
    ),
)
def test_arm_credential_failure_has_zero_arm_network_or_broker_effects(
    tmp_path: Path,
    failure: str,
) -> None:
    authorization = _authorization(tmp_path)
    scheduler = FakeScheduler()
    store = V536CanaryStateStore(tmp_path / "state.sqlite3")
    clock = FixedClock(SCHEDULED_START - timedelta(hours=1))
    install_v536_task_disabled(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
        owner_id_factory=lambda: "install-owner",
    )
    clock.now = SCHEDULED_START - timedelta(minutes=5)
    provider = FakeProvider(failure=failure)
    result = arm_v536_exact_window(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        credential_provider=provider,
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
        owner_id_factory=lambda: "arm-owner",
    )
    assert result["classification"] == f"blocked_{failure}"
    assert scheduler.arm_count == 0
    assert scheduler.phase == "disabled"
    assert store.read(authorization)["status"] == "blocked"


def test_concurrent_execution_allows_one_real_dispatch_and_immutable_duplicates(
    tmp_path: Path,
) -> None:
    authorization, scheduler, store, provider, clock, arm = _install_and_arm(tmp_path)
    assert arm["classification"] == "task_armed_exact_window"
    scheduler.phase = "running"
    clock.now = SCHEDULED_START + timedelta(minutes=1)
    runner = FakeProcessRunner()
    paper = FakePaperHttp()
    dispatcher = _dispatcher(provider, runner, authorization)
    identity_lock = Lock()
    next_id = 0

    def invoke(_index: int) -> dict[str, object]:
        nonlocal next_id
        with identity_lock:
            next_id += 1
            invocation_id = f"execution-{next_id}"
        return execute_v536_canary(
            authorization=authorization,
            scheduler=scheduler,
            state_store=V536CanaryStateStore(store.path),
            dispatcher=dispatcher,
            credential_provider=provider,
            paper_http_boundary=paper,
            provenance_reader=_provenance,
            current_identity="DOMAIN\\canary-user",
            clock=clock,
            invocation_id_factory=lambda: invocation_id,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(invoke, range(12)))
    pending = [
        item
        for item in results
        if item["classification"]
        == "canary_reads_complete_pending_terminal_attestation"
    ]
    duplicates = [
        item
        for item in results
        if item["classification"] == "duplicate_canary_execution_no_op"
    ]
    assert len(pending) == 1
    assert len(duplicates) == 11
    assert runner.call_count == 1
    assert paper.call_count == 1
    assert scheduler.disarm_count == 1
    assert len(
        list(
            (
                tmp_path
                / "runs"
                / "v5_36_windows_host_canary"
                / "duplicates"
            ).glob("duplicate_*.json")
        )
    ) == 11
    assert store.read(authorization)["execution_count"] == 1


def test_disarm_failure_blocks_even_after_successful_reads(
    tmp_path: Path,
) -> None:
    authorization, scheduler, store, provider, clock, arm = _install_and_arm(tmp_path)
    assert arm["classification"] == "task_armed_exact_window"
    scheduler.phase = "running"
    scheduler.fail_disarm = True
    clock.now = SCHEDULED_START + timedelta(minutes=1)
    runner = FakeProcessRunner()
    paper = FakePaperHttp()
    result = execute_v536_canary(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        dispatcher=_dispatcher(provider, runner, authorization),
        credential_provider=provider,
        paper_http_boundary=paper,
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
        invocation_id_factory=lambda: "execute-owner",
    )
    assert result["classification"] == "blocked_task_disarm_failed"
    assert runner.call_count == 1
    assert paper.call_count == 1
    assert store.read(authorization)["status"] == "blocked"


@pytest.mark.parametrize(
    "failure",
    (
        "credential_provider_unavailable",
        "credential_provider_denied",
        "credential_record_malformed",
        "credential_family_mismatch",
    ),
)
def test_execute_credential_failure_has_zero_process_network_or_broker_reads(
    tmp_path: Path,
    failure: str,
) -> None:
    authorization, scheduler, store, _provider, clock, arm = _install_and_arm(
        tmp_path
    )
    assert arm["classification"] == "task_armed_exact_window"
    scheduler.phase = "running"
    clock.now = SCHEDULED_START + timedelta(minutes=1)
    failing_provider = FakeProvider(failure=failure)
    runner = FakeProcessRunner()
    paper = FakePaperHttp()
    result = execute_v536_canary(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        dispatcher=_dispatcher(failing_provider, runner, authorization),
        credential_provider=failing_provider,
        paper_http_boundary=paper,
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
        invocation_id_factory=lambda: "execute-owner",
    )
    assert result["classification"] == f"blocked_{failure}"
    assert runner.call_count == 0
    assert paper.call_count == 0
    assert scheduler.disarm_count == 1
    assert scheduler.phase == "post_run"


def test_structural_secret_field_or_temp_artifact_blocks_commissioning(
    tmp_path: Path,
) -> None:
    authorization, scheduler, store, provider, clock, _arm = _install_and_arm(
        tmp_path
    )
    scheduler.phase = "running"
    clock.now = SCHEDULED_START + timedelta(minutes=1)
    output_root = tmp_path / "runs" / "v5_36_windows_host_canary"
    (output_root / "unexpected.json").write_text(
        '{"api_secret_key":"not-a-real-secret"}',
        encoding="utf-8",
    )
    result = execute_v536_canary(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        dispatcher=_dispatcher(provider, FakeProcessRunner(), authorization),
        credential_provider=provider,
        paper_http_boundary=FakePaperHttp(),
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
        invocation_id_factory=lambda: "execute-owner",
    )
    assert result["classification"] == "blocked_secret_persistence_detected"
    assert scheduler.disarm_count == 1
    assert store.read(authorization)["status"] == "blocked"


def test_non_flat_paper_state_blocks_and_still_disarms(
    tmp_path: Path,
) -> None:
    authorization, scheduler, store, provider, clock, _arm = _install_and_arm(tmp_path)
    scheduler.phase = "running"
    clock.now = SCHEDULED_START + timedelta(minutes=1)
    result = execute_v536_canary(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        dispatcher=_dispatcher(provider, FakeProcessRunner(), authorization),
        credential_provider=provider,
        paper_http_boundary=FakePaperHttp(flat=False),
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
        invocation_id_factory=lambda: "execute-owner",
    )
    assert result["classification"] == "blocked_broker_account_non_flat"
    assert scheduler.phase == "post_run"
    assert scheduler.disarm_count == 1


def test_post_run_failed_result_cannot_finalize(
    tmp_path: Path,
) -> None:
    authorization, scheduler, store, provider, clock, _arm = _install_and_arm(tmp_path)
    scheduler.phase = "running"
    clock.now = SCHEDULED_START + timedelta(minutes=1)
    execute_v536_canary(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        dispatcher=_dispatcher(provider, FakeProcessRunner(), authorization),
        credential_provider=provider,
        paper_http_boundary=FakePaperHttp(),
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
        invocation_id_factory=lambda: "execute-owner",
    )
    scheduler.last_task_result = 1
    result = post_run_attest_v536_canary(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
    )
    assert result["classification"] == "blocked_task_terminal_result_failed"
    assert store.read(authorization)["status"] == "blocked"
    blocked = (
        tmp_path
        / "runs"
        / "v5_36_windows_host_canary"
        / "blocked"
        / "blocked_execute-owner.json"
    )
    assert json.loads(blocked.read_text(encoding="utf-8")) == result


def test_pending_evidence_cross_hash_or_binding_tamper_fails_closed(
    tmp_path: Path,
) -> None:
    authorization, scheduler, store, provider, clock, _arm = _install_and_arm(tmp_path)
    scheduler.phase = "running"
    clock.now = SCHEDULED_START + timedelta(minutes=1)
    pending = execute_v536_canary(
        authorization=authorization,
        scheduler=scheduler,
        state_store=store,
        dispatcher=_dispatcher(provider, FakeProcessRunner(), authorization),
        credential_provider=provider,
        paper_http_boundary=FakePaperHttp(),
        provenance_reader=_provenance,
        current_identity="DOMAIN\\canary-user",
        clock=clock,
        invocation_id_factory=lambda: "execute-owner",
    )
    ref = pending["evidence_references"]["broker"]  # type: ignore[index]
    path = tmp_path / "runs" / "v5_36_windows_host_canary" / ref["path"]
    broker = json.loads(path.read_text(encoding="utf-8"))
    broker["paper_endpoint"] = "https://api.alpaca.markets"
    path.write_text(json.dumps(broker), encoding="utf-8")
    validation = validate_v536_pending_packet(
        tmp_path
        / "runs"
        / "v5_36_windows_host_canary"
        / "pending"
        / "pending_v536-canary-test.json",
        output_root=tmp_path / "runs" / "v5_36_windows_host_canary",
        authorization=authorization,
    )
    assert not validation.valid
    assert "broker_self_hash_mismatch" in validation.errors
    assert "paper_endpoint_mismatch" in validation.errors


def test_runtime_mismatch_precedes_state_scheduler_provider_process_and_broker(
    tmp_path: Path,
) -> None:
    authorization = _authorization(tmp_path)
    scheduler = FakeScheduler()
    provider = FakeProvider()
    runner = FakeProcessRunner()
    paper = FakePaperHttp()
    store = V536CanaryStateStore(tmp_path / "state.sqlite3")
    dirty = lambda: {**_provenance(), "source_worktree_clean": False}
    with pytest.raises(V536AuthorizationError, match="runtime_source_dirty"):
        execute_v536_canary(
            authorization=authorization,
            scheduler=scheduler,
            state_store=store,
            dispatcher=_dispatcher(provider, runner, authorization),
            credential_provider=provider,
            paper_http_boundary=paper,
            provenance_reader=dirty,
            current_identity="DOMAIN\\canary-user",
            clock=FixedClock(SCHEDULED_START + timedelta(minutes=1)),
        )
    assert scheduler.read_count == 0
    assert provider.validate_count == 0
    assert runner.call_count == 0
    assert paper.call_count == 0
    assert not store.path.exists()


def test_wrong_dispatcher_is_rejected_before_state_or_external_effects(
    tmp_path: Path,
) -> None:
    authorization = _authorization(tmp_path)
    scheduler = FakeScheduler()
    provider = FakeProvider()
    store = V536CanaryStateStore(tmp_path / "state.sqlite3")
    with pytest.raises(V536CanaryError, match="real_command_dispatcher_required"):
        execute_v536_canary(
            authorization=authorization,
            scheduler=scheduler,
            state_store=store,
            dispatcher=object(),  # type: ignore[arg-type]
            credential_provider=provider,
            paper_http_boundary=FakePaperHttp(),
            provenance_reader=_provenance,
            current_identity="DOMAIN\\canary-user",
            clock=FixedClock(SCHEDULED_START + timedelta(minutes=1)),
        )
    assert not store.path.exists()
    assert provider.validate_count == 0


def test_unresolved_operator_template_cli_has_zero_side_effects(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = {
        key: value
        for key, value in json.loads(
            (_authorization(tmp_path).artifact_path).read_text(encoding="utf-8")  # type: ignore[union-attr]
        ).items()
    }
    payload["target_window_start_utc"] = "<EXACT_CLOSED_WINDOW>"
    payload["canonical_authorization_sha256"] = canonical_authorization_sha256(
        payload
    )
    artifact = tmp_path / "runs" / "placeholder.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    exit_code = main(
        [
            "--mode",
            "execute",
            "--authorization-artifact",
            str(artifact.resolve()),
            "--task-mutation-authorized",
            "--credential-read-authorized",
            "--execute-authorized",
        ]
    )
    assert exit_code == 2
    assert json.loads(capsys.readouterr().out) == {
        "classification": "blocked_authorization_placeholder_unresolved"
    }
    assert not (tmp_path / "runs" / "v5_36_windows_host_canary").exists()


def test_cli_gates_precede_even_missing_authorization_artifact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing.json"
    exit_code = main(
        [
            "--mode",
            "execute",
            "--authorization-artifact",
            str(missing.resolve()),
        ]
    )
    assert exit_code == 2
    assert json.loads(capsys.readouterr().out) == {
        "classification": "blocked_task_mutation_not_authorized"
    }
    assert not missing.exists()


def test_cli_disarm_constructs_neither_identity_nor_credential_provider(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization = _authorization(tmp_path)
    calls: list[str] = []

    def forbidden() -> None:
        raise AssertionError("disarm must remain credential and identity independent")

    def fake_disarm(**_kwargs: object) -> dict[str, object]:
        calls.append("disarm")
        return {
            "classification": "task_disarmed",
            "canonical_receipt_sha256": "0" * 64,
        }

    monkeypatch.setattr(
        "algotrader.execution.v536_windows_host_canary.current_windows_identity",
        forbidden,
    )
    monkeypatch.setattr(
        "algotrader.execution.v536_windows_host_canary.provider_from_name",
        forbidden,
    )
    monkeypatch.setattr(
        "algotrader.execution.v536_windows_host_canary.disarm_v536_task",
        fake_disarm,
    )
    exit_code = main(
        [
            "--mode",
            "disarm",
            "--authorization-artifact",
            str(authorization.artifact_path),
            "--task-mutation-authorized",
        ]
    )
    assert exit_code == 0
    assert calls == ["disarm"]
    assert json.loads(capsys.readouterr().out)["classification"] == "task_disarmed"
