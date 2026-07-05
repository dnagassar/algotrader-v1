"""No-submit crypto Paper OMS dry-run gate.

This module consumes a v5.5 crypto Paper OMS handoff packet and writes a
broker-neutral dry-run record. It validates the handoff, assigns deterministic
pre-broker preview identity, and refuses broker mutation by default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.orchestration.crypto_paper_oms_handoff import (
    CRYPTO_PAPER_OMS_HANDOFF_ACCEPTED_BACKINGS,
    CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_FALSE_FLAGS,
    CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_LABELS,
)

CRYPTO_PAPER_OMS_DRY_RUN_SCHEMA_VERSION = "v5_6_crypto_paper_oms_dry_run_v1"
CRYPTO_PAPER_OMS_DRY_RUN_DEFAULT_HANDOFF = Path(
    "runs/crypto_paper_oms_handoff/latest/paper_oms_handoff.json"
)
CRYPTO_PAPER_OMS_DRY_RUN_DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_paper_oms_dry_run/latest"
)

CRYPTO_PAPER_OMS_DRY_RUN_REQUIRED_LABELS = (
    *CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_LABELS,
    "paper_oms_dry_run_only",
    "pre_broker_preview_only",
    "not_submittable",
)
CRYPTO_PAPER_OMS_DRY_RUN_ACCEPTED_ACTIONS = ("buy_preview", "no_action")
CRYPTO_PAPER_OMS_DRY_RUN_REQUIRED_FALSE_FLAGS = (
    *CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_FALSE_FLAGS,
    "live_endpoint_touched",
    "credential_values_exposed",
)

__all__ = [
    "CRYPTO_PAPER_OMS_DRY_RUN_ACCEPTED_ACTIONS",
    "CRYPTO_PAPER_OMS_DRY_RUN_DEFAULT_HANDOFF",
    "CRYPTO_PAPER_OMS_DRY_RUN_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_PAPER_OMS_DRY_RUN_REQUIRED_FALSE_FLAGS",
    "CRYPTO_PAPER_OMS_DRY_RUN_REQUIRED_LABELS",
    "CRYPTO_PAPER_OMS_DRY_RUN_SCHEMA_VERSION",
    "build_crypto_paper_oms_dry_run_record",
    "main",
    "render_paper_oms_dry_run_markdown",
    "run_crypto_paper_oms_dry_run",
    "write_crypto_paper_oms_dry_run_artifacts",
]


def run_crypto_paper_oms_dry_run(
    *,
    handoff_path: Path | str = CRYPTO_PAPER_OMS_DRY_RUN_DEFAULT_HANDOFF,
    output_root: Path | str = CRYPTO_PAPER_OMS_DRY_RUN_DEFAULT_OUTPUT_ROOT,
    allow_fixture_backed: bool = False,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Read a v5.5 Paper OMS handoff and write a no-submit dry-run record."""

    source_path = Path(handoff_path)
    handoff = _read_json_mapping(source_path)
    record = build_crypto_paper_oms_dry_run_record(
        handoff=handoff,
        handoff_source=source_path,
        allow_fixture_backed=allow_fixture_backed,
    )
    if write_artifacts:
        record["artifact_paths"] = write_crypto_paper_oms_dry_run_artifacts(
            output_root,
            record,
        )
    return record


def build_crypto_paper_oms_dry_run_record(
    *,
    handoff: Mapping[str, object],
    handoff_source: Path | str,
    allow_fixture_backed: bool = False,
) -> dict[str, object]:
    """Build a primitive-only broker-neutral dry-run record."""

    source_path = Path(handoff_source)
    source_labels = list(_string_sequence(handoff.get("labels")))
    selected_candidate_id = _first_text(handoff, "selected_candidate_id")
    selected_backing = _canonical_backing(
        _first_text(handoff, "selected_backing"),
        source_labels=source_labels,
    )
    asset_class = _first_text(handoff, "asset_class")
    symbol = _first_text(handoff, "symbol", "selected_symbol")
    selected_strategy = _first_text(
        handoff,
        "selected_strategy",
        "strategy_id",
        "selected_strategy_id",
    )
    intended_action = _first_text(handoff, "intended_action")
    handoff_status = _first_text(handoff, "handoff_status")
    approval_state = _first_text(handoff, "approval_state")
    as_of = _first_text(handoff, "as_of", "data_timestamp")
    latest_price = _positive_decimal_field(handoff, "latest_price")
    rounded_qty = _positive_decimal_field(handoff, "rounded_qty")
    derived_preview_value = _positive_decimal_field(
        handoff,
        "derived_preview_value",
    )
    preview_cap = _positive_decimal_field(
        handoff,
        "preview_cap",
        "preview_notional_cap",
        "max_preview_value",
    )
    source_blockers = list(_string_sequence(handoff.get("blockers")))
    missing_required_labels = _missing_required_labels(
        source_labels=source_labels,
        selected_backing=selected_backing,
        allow_fixture_backed=allow_fixture_backed,
    )

    identity = _deterministic_identity(
        as_of=as_of,
        selected_candidate_id=selected_candidate_id,
        symbol=symbol,
        selected_strategy=selected_strategy,
        rounded_qty=_decimal_or_empty(rounded_qty),
        derived_preview_value=_decimal_or_empty(derived_preview_value),
    )
    blockers = _dry_run_blockers(
        handoff=handoff,
        source_blockers=source_blockers,
        handoff_status=handoff_status,
        approval_state=approval_state,
        intended_action=intended_action,
        asset_class=asset_class,
        selected_candidate_id=selected_candidate_id,
        symbol=symbol,
        selected_strategy=selected_strategy,
        selected_backing=selected_backing,
        latest_price=latest_price,
        rounded_qty=rounded_qty,
        derived_preview_value=derived_preview_value,
        preview_cap=preview_cap,
        missing_required_labels=missing_required_labels,
        allow_fixture_backed=allow_fixture_backed,
    )
    dry_run_status = _dry_run_status(blockers, approval_state)
    labels = _dry_run_labels(
        source_labels=source_labels,
        selected_backing=selected_backing,
        allow_fixture_backed=allow_fixture_backed,
    )
    broker_preview = {
        "envelope_type": "broker_neutral_pre_broker_preview",
        "not_submittable": True,
        "pre_broker_preview_only": True,
        "approval_required": True,
        "asset_class": asset_class,
        "symbol": symbol,
        "side": "buy" if intended_action == "buy_preview" else "",
        "quantity": _decimal_or_empty(rounded_qty),
        "preview_value": _decimal_or_empty(derived_preview_value),
        "preview_cap": _decimal_or_empty(preview_cap),
        "selected_candidate_id": selected_candidate_id,
        "selected_strategy": selected_strategy,
        "selected_backing": selected_backing,
        "pre_broker_order_id": identity["pre_broker_order_id"],
        "broker_action_permitted": False,
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
    }

    return {
        "schema_version": CRYPTO_PAPER_OMS_DRY_RUN_SCHEMA_VERSION,
        "as_of": as_of,
        "handoff_source": str(source_path),
        "dry_run_status": dry_run_status,
        "approval_state": approval_state,
        "broker_action_permitted": False,
        "intended_action": intended_action,
        "asset_class": asset_class,
        "symbol": symbol,
        "selected_candidate_id": selected_candidate_id,
        "selected_strategy": selected_strategy,
        "selected_backing": selected_backing,
        "latest_price": _decimal_or_empty(latest_price),
        "rounded_qty": _decimal_or_empty(rounded_qty),
        "derived_preview_value": _decimal_or_empty(derived_preview_value),
        "preview_cap": _decimal_or_empty(preview_cap),
        "dry_run_id": identity["dry_run_id"],
        "pre_broker_order_id": identity["pre_broker_order_id"],
        "idempotency_key": identity["idempotency_key"],
        "identity_basis": identity["identity_basis"],
        "blockers": blockers,
        "source_blockers": source_blockers,
        "missing_required_labels": missing_required_labels,
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "broker_read_performed_current_run": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "labels": labels,
        "broker_neutral_preview": broker_preview,
        "no_submit_statement": (
            "No order was submitted. This dry-run does not authorize broker "
            "mutation and is pre-broker preview only."
        ),
        "next_operator_action": _next_operator_action(dry_run_status),
        "source_handoff_summary": _source_handoff_summary(handoff),
    }


def write_crypto_paper_oms_dry_run_artifacts(
    output_root: Path | str,
    record: Mapping[str, object],
) -> dict[str, str]:
    """Write ignored runtime artifacts for the no-submit dry-run gate."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "paper_oms_dry_run_json": root / "paper_oms_dry_run.json",
        "paper_oms_dry_run_md": root / "paper_oms_dry_run.md",
        "operating_record": root / "operating_record.jsonl",
    }
    _write_json(paths["paper_oms_dry_run_json"], record)
    paths["paper_oms_dry_run_md"].write_text(
        render_paper_oms_dry_run_markdown(record) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    paths["operating_record"].write_text(
        json.dumps(
            _json_safe(
                {
                    "record_type": "crypto_paper_oms_dry_run",
                    "schema_version": CRYPTO_PAPER_OMS_DRY_RUN_SCHEMA_VERSION,
                    "as_of": record.get("as_of", ""),
                    "handoff_source": record.get("handoff_source", ""),
                    "dry_run_status": record.get("dry_run_status", ""),
                    "approval_state": record.get("approval_state", ""),
                    "broker_action_permitted": False,
                    "intended_action": record.get("intended_action", ""),
                    "selected_candidate_id": record.get("selected_candidate_id", ""),
                    "selected_backing": record.get("selected_backing", ""),
                    "dry_run_id": record.get("dry_run_id", ""),
                    "pre_broker_order_id": record.get("pre_broker_order_id", ""),
                    "idempotency_key": record.get("idempotency_key", ""),
                    "blockers": record.get("blockers", []),
                    "paper_submit_authorized": False,
                    "paper_submit_performed": False,
                    "broker_mutation_performed": False,
                    "live_mutation_performed": False,
                    "live_endpoint_touched": False,
                    "credential_values_exposed": False,
                    "profit_claim": "none",
                }
            ),
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest_path = root / "manifest.json"
    manifest = {
        "schema_version": CRYPTO_PAPER_OMS_DRY_RUN_SCHEMA_VERSION,
        "as_of": record.get("as_of", ""),
        "artifact_root": str(root),
        "required_artifacts": {
            key: {
                "path": str(path),
                "sha256": _file_sha256(path),
                "size": path.stat().st_size,
            }
            for key, path in sorted(paths.items())
        },
        "manifest": {
            "path": str(manifest_path),
        },
        "input_artifacts": {
            "paper_oms_handoff": _artifact_reference(
                _first_text(record, "handoff_source")
            ),
        },
        "dry_run_status": record.get("dry_run_status", ""),
        "approval_state": record.get("approval_state", ""),
        "broker_action_permitted": False,
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "broker_read_performed_current_run": False,
        "network_access_attempted": False,
        "generated_under_runs": "runs" in root.parts,
        "labels": list(_string_sequence(record.get("labels"))),
        "profit_claim": "none",
    }
    _write_json(manifest_path, manifest)
    return {
        **{key: str(path) for key, path in paths.items()},
        "manifest": str(manifest_path),
    }


def render_paper_oms_dry_run_markdown(record: Mapping[str, object]) -> str:
    """Render the operator-facing no-submit Paper OMS dry-run brief."""

    blockers = list(_string_sequence(record.get("blockers")))
    return "\n".join(
        [
            "# Crypto Paper OMS Dry Run",
            "",
            f"- handoff source: `{record.get('handoff_source', '')}`",
            f"- selected candidate: `{record.get('selected_candidate_id', '')}`",
            f"- selected strategy: `{record.get('selected_strategy', '')}`",
            f"- selected backing/provenance: `{record.get('selected_backing', '')}`",
            f"- intended action: `{record.get('intended_action', '')}`",
            (
                "- preview qty/value: "
                f"`{record.get('rounded_qty', '')}` / "
                f"`{record.get('derived_preview_value', '')}` "
                f"(cap `{record.get('preview_cap', '')}`)"
            ),
            "- deterministic preview identity: "
            f"`dry_run_id={record.get('dry_run_id', '')}`, "
            f"`pre_broker_order_id={record.get('pre_broker_order_id', '')}`, "
            f"`idempotency_key={record.get('idempotency_key', '')}`",
            f"- approval state: `{record.get('approval_state', '')}`",
            f"- dry-run status: `{record.get('dry_run_status', '')}`",
            (
                "- broker action blocked because: "
                f"`{_block_reason(record, blockers)}`"
            ),
            "- no-submit statement: no order was submitted.",
            (
                "- mutation statement: no broker mutation is authorized; "
                "this is pre-broker preview only."
            ),
            f"- next operator action: `{record.get('next_operator_action', '')}`",
            "",
            "Labels: " + ", ".join(_string_sequence(record.get("labels"))),
        ]
    )


def _dry_run_blockers(
    *,
    handoff: Mapping[str, object],
    source_blockers: Sequence[str],
    handoff_status: str,
    approval_state: str,
    intended_action: str,
    asset_class: str,
    selected_candidate_id: str,
    symbol: str,
    selected_strategy: str,
    selected_backing: str,
    latest_price: Decimal | None,
    rounded_qty: Decimal | None,
    derived_preview_value: Decimal | None,
    preview_cap: Decimal | None,
    missing_required_labels: Sequence[str],
    allow_fixture_backed: bool,
) -> list[str]:
    blockers: list[str] = []
    if handoff_status != "approval_required":
        blockers.append("handoff_status_not_approval_required")
    if source_blockers:
        blockers.append("handoff_contains_source_blockers")
    if approval_state != "not_authorized":
        blockers.append("approval_state_not_not_authorized")
    if intended_action not in CRYPTO_PAPER_OMS_DRY_RUN_ACCEPTED_ACTIONS:
        blockers.append("unsupported_intended_action")
    if asset_class != "crypto":
        blockers.append("asset_class_not_crypto")
    if not selected_candidate_id:
        blockers.append("missing_selected_candidate")
    if not symbol:
        blockers.append("missing_symbol")
    if not selected_strategy:
        blockers.append("missing_selected_strategy")
    if selected_backing == "fixture_backed" and not allow_fixture_backed:
        blockers.append("fixture_backed_handoff")
    if (
        selected_backing not in CRYPTO_PAPER_OMS_HANDOFF_ACCEPTED_BACKINGS
        and not (allow_fixture_backed and selected_backing == "fixture_backed")
    ):
        blockers.append("unsupported_selected_backing")
    if latest_price is None:
        blockers.append("missing_or_invalid_latest_price")
    if rounded_qty is None:
        blockers.append("missing_or_invalid_rounded_qty")
    if derived_preview_value is None:
        blockers.append("missing_or_invalid_derived_preview_value")
    if preview_cap is None:
        blockers.append("missing_or_invalid_preview_cap")
    if (
        preview_cap is not None
        and derived_preview_value is not None
        and derived_preview_value > preview_cap
    ):
        blockers.append("derived_preview_value_exceeds_cap")
    for field_name in CRYPTO_PAPER_OMS_DRY_RUN_REQUIRED_FALSE_FLAGS:
        if _is_true(handoff.get(field_name)):
            blockers.append(f"{field_name}_true")
    if _is_true(handoff.get("broker_read_performed_current_run")):
        blockers.append("broker_read_performed_current_run_true")
    if _is_true(handoff.get("network_access_attempted")):
        blockers.append("network_access_attempted_true")
    if _first_text(handoff, "profit_claim") != "none":
        blockers.append("profit_claim_not_none")
    if missing_required_labels:
        blockers.append("missing_required_safety_labels")
    return list(_dedupe(blockers))


def _dry_run_status(blockers: Sequence[str], approval_state: str) -> str:
    if blockers:
        return "blocked_invalid_handoff"
    if approval_state == "not_authorized":
        return "blocked_not_authorized"
    return "blocked_approval_gate"


def _deterministic_identity(
    *,
    as_of: str,
    selected_candidate_id: str,
    symbol: str,
    selected_strategy: str,
    rounded_qty: str,
    derived_preview_value: str,
) -> dict[str, object]:
    basis = {
        "as_of": as_of,
        "selected_candidate_id": selected_candidate_id,
        "symbol": symbol,
        "selected_strategy": selected_strategy,
        "rounded_qty": rounded_qty,
        "derived_preview_value": derived_preview_value,
    }
    encoded = json.dumps(basis, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return {
        "dry_run_id": f"dryrun_{digest[:24]}",
        "pre_broker_order_id": f"prebroker_{digest[24:48]}",
        "idempotency_key": f"crypto_paper_oms_dry_run:{digest}",
        "identity_basis": basis,
    }


def _source_handoff_summary(handoff: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": _first_text(handoff, "schema_version"),
        "as_of": _first_text(handoff, "as_of"),
        "handoff_status": _first_text(handoff, "handoff_status"),
        "approval_state": _first_text(handoff, "approval_state"),
        "intended_action": _first_text(handoff, "intended_action"),
        "selected_candidate_id": _first_text(handoff, "selected_candidate_id"),
        "selected_backing": _first_text(handoff, "selected_backing"),
        "sizing_preview_source": _first_text(handoff, "sizing_preview_source"),
        "blockers": list(_string_sequence(handoff.get("blockers"))),
        "labels": list(_string_sequence(handoff.get("labels"))),
        "paper_submit_authorized": _is_true(handoff.get("paper_submit_authorized")),
        "paper_submit_performed": _is_true(handoff.get("paper_submit_performed")),
        "broker_mutation_performed": _is_true(
            handoff.get("broker_mutation_performed")
        ),
        "live_mutation_performed": _is_true(handoff.get("live_mutation_performed")),
        "live_endpoint_touched": _is_true(handoff.get("live_endpoint_touched")),
        "credential_values_exposed": _is_true(
            handoff.get("credential_values_exposed")
        ),
    }


def _missing_required_labels(
    *,
    source_labels: Sequence[str],
    selected_backing: str,
    allow_fixture_backed: bool,
) -> list[str]:
    required = list(CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_LABELS)
    if selected_backing in CRYPTO_PAPER_OMS_HANDOFF_ACCEPTED_BACKINGS:
        required.append(selected_backing)
    elif allow_fixture_backed and selected_backing == "fixture_backed":
        required.append("fixture_backed")
    else:
        required.append("real_local_artifact_backed_or_real_paper_read_backed")
    label_set = set(source_labels)
    return [label for label in required if label not in label_set]


def _dry_run_labels(
    *,
    source_labels: Sequence[str],
    selected_backing: str,
    allow_fixture_backed: bool,
) -> list[str]:
    labels: list[str] = [*source_labels, *CRYPTO_PAPER_OMS_DRY_RUN_REQUIRED_LABELS]
    if selected_backing in CRYPTO_PAPER_OMS_HANDOFF_ACCEPTED_BACKINGS:
        labels.append(selected_backing)
    elif allow_fixture_backed and selected_backing == "fixture_backed":
        labels.append("fixture_backed")
    return list(_dedupe(labels))


def _canonical_backing(value: str, *, source_labels: Sequence[str]) -> str:
    if value in CRYPTO_PAPER_OMS_HANDOFF_ACCEPTED_BACKINGS:
        return value
    if value == "paper_read_only_artifact_backed" and "real_paper_read_backed" in set(
        source_labels
    ):
        return "real_paper_read_backed"
    if value == "fixture_backed":
        return "fixture_backed"
    if "real_local_artifact_backed" in source_labels:
        return "real_local_artifact_backed"
    if "real_paper_read_backed" in source_labels:
        return "real_paper_read_backed"
    if "fixture_backed" in source_labels:
        return "fixture_backed"
    return value


def _next_operator_action(dry_run_status: str) -> str:
    if dry_run_status == "blocked_not_authorized":
        return (
            "operator_may_review_preview_identity_and_choose_whether_to_create_"
            "a_separate_future_paper_submit_authorization"
        )
    return "repair_handoff_safety_blockers_then_rerun_paper_oms_handoff_and_dry_run"


def _block_reason(record: Mapping[str, object], blockers: Sequence[str]) -> str:
    if blockers:
        return ",".join(blockers)
    approval_state = _first_text(record, "approval_state")
    if approval_state == "not_authorized":
        return "approval_state_not_authorized"
    return "broker_action_permitted_false_by_default"


def _read_json_mapping(path: Path) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"unable to read JSON artifact: {path}") from exc
    if not isinstance(payload, Mapping):
        raise ValidationError(f"JSON artifact must contain an object: {path}")
    return payload


def _artifact_reference(path_text: str) -> dict[str, str]:
    path = Path(path_text)
    return {
        "path": str(path),
        "sha256": _file_sha256(path) if path.is_file() else "",
    }


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _positive_decimal_field(
    row: Mapping[str, object],
    *field_names: str,
) -> Decimal | None:
    value = _first_text(row, *field_names)
    if not value:
        return None
    try:
        parsed = _decimal_value(value, field_names[0])
    except ValidationError:
        return None
    if parsed <= Decimal("0"):
        return None
    return parsed


def _decimal_value(value: object, field_name: str) -> Decimal:
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a finite Decimal.") from exc
    if not parsed.is_finite():
        raise ValidationError(f"{field_name} must be a finite Decimal.")
    return parsed


def _decimal_text(value: object) -> str:
    return format(_decimal_value(value, "decimal").normalize(), "f")


def _decimal_or_empty(value: Decimal | None) -> str:
    return "" if value is None else _decimal_text(value)


def _is_true(value: object) -> bool:
    if type(value) is bool:
        return value
    if type(value) is str:
        return value.strip().lower() == "true"
    return False


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item).strip())
    if value in (None, ""):
        return ()
    return (str(value),)


def _first_text(row: Mapping[str, object], *field_names: str) -> str:
    wanted = {_field_lookup_key(field_name) for field_name in field_names}
    for key, value in row.items():
        if _field_lookup_key(key) in wanted:
            return _text(value)
    return ""


def _text(value: object) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "true" if value else "false"
    return str(value).strip()


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _field_lookup_key(value: object) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a no-submit crypto Paper OMS dry-run record.",
    )
    parser.add_argument(
        "--handoff-path",
        type=Path,
        default=CRYPTO_PAPER_OMS_DRY_RUN_DEFAULT_HANDOFF,
        help="Path to v5.5 paper_oms_handoff.json.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=CRYPTO_PAPER_OMS_DRY_RUN_DEFAULT_OUTPUT_ROOT,
        help="Output root for ignored dry-run artifacts.",
    )
    parser.add_argument(
        "--allow-fixture-backed",
        action="store_true",
        help="Allow fixture-backed selected candidates for explicit fixture tests.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    record = run_crypto_paper_oms_dry_run(
        handoff_path=args.handoff_path,
        output_root=args.output_root,
        allow_fixture_backed=args.allow_fixture_backed,
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(record), sort_keys=True))
    else:
        artifacts = record.get("artifact_paths")
        artifact_map = artifacts if isinstance(artifacts, Mapping) else {}
        print("crypto_paper_oms_dry_run_status=" + _text(record.get("dry_run_status")))
        print("approval_state=" + _text(record.get("approval_state")))
        print(
            "broker_action_permitted="
            + _text(record.get("broker_action_permitted", False))
        )
        print("intended_action=" + _text(record.get("intended_action")))
        print("selected_candidate_id=" + _text(record.get("selected_candidate_id")))
        print("selected_backing=" + _text(record.get("selected_backing")))
        print("rounded_qty=" + _text(record.get("rounded_qty")))
        print("derived_preview_value=" + _text(record.get("derived_preview_value")))
        print("preview_cap=" + _text(record.get("preview_cap")))
        print("dry_run_id=" + _text(record.get("dry_run_id")))
        print("idempotency_key=" + _text(record.get("idempotency_key")))
        print("blockers=" + ",".join(_string_sequence(record.get("blockers"))))
        print("paper_submit_authorized=false")
        print("paper_submit_performed=false")
        print("broker_mutation_performed=false")
        print("live_mutation_performed=false")
        print(
            "artifact_paper_oms_dry_run_json="
            + _text(artifact_map.get("paper_oms_dry_run_json"))
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
