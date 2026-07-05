"""No-submit crypto paper-submit approval packet builder.

This module consumes a v5.6 crypto Paper OMS dry-run artifact and writes an
operator-review packet for a possible future bounded paper submit/cancel
certification. It does not read a broker, submit orders, or authorize mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path

from algotrader.errors import ValidationError

CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_SCHEMA_VERSION = (
    "v5_7_crypto_paper_submit_approval_packet_v1"
)
CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_DEFAULT_DRY_RUN = Path(
    "runs/crypto_paper_oms_dry_run/latest/paper_oms_dry_run.json"
)
CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_paper_submit_approval_packet/latest"
)
CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUESTED_SCOPE = (
    "bounded_paper_submit_cancel_certification"
)

CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_ACCEPTED_BACKINGS = (
    "real_local_artifact_backed",
    "real_paper_read_backed",
)
CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_SOURCE_REQUIRED_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "not_live_authorized",
    "profit_claim=none",
    "no_submit_mode",
    "paper_oms_dry_run_only",
    "approval_required",
    "pre_broker_preview_only",
    "not_submittable",
)
CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUIRED_LABELS = (
    *CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_SOURCE_REQUIRED_LABELS,
    "paper_submit_approval_packet_only",
    "operator_review_required",
)
CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUIRED_FALSE_FLAGS = (
    "broker_action_permitted",
    "paper_submit_authorized",
    "paper_submit_performed",
    "broker_mutation_performed",
    "live_mutation_performed",
    "live_endpoint_touched",
    "credential_values_exposed",
)
CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_EXTRA_FALSE_SOURCE_FLAGS = (
    "broker_read_performed_current_run",
    "network_access_attempted",
)
CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_DISALLOWED_ACTIONS = (
    "current_paper_submit",
    "current_paper_cancel",
    "paper_replace",
    "paper_close",
    "paper_liquidate",
    "live_trading",
    "live_submit",
    "live_cancel",
    "live_replace",
    "live_close",
    "live_liquidate",
    "broker_read",
    "broker_mutation",
    "credential_exposure",
    "capital_change",
    "paid_service_or_new_secret",
)

__all__ = [
    "CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_ACCEPTED_BACKINGS",
    "CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_DEFAULT_DRY_RUN",
    "CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_DISALLOWED_ACTIONS",
    "CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUESTED_SCOPE",
    "CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUIRED_FALSE_FLAGS",
    "CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUIRED_LABELS",
    "CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_SCHEMA_VERSION",
    "build_crypto_paper_submit_approval_packet",
    "main",
    "render_crypto_paper_submit_approval_packet_markdown",
    "run_crypto_paper_submit_approval_packet",
    "write_crypto_paper_submit_approval_packet_artifacts",
]


def run_crypto_paper_submit_approval_packet(
    *,
    dry_run_path: Path | str = CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_DEFAULT_DRY_RUN,
    output_root: Path | str = (
        CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_DEFAULT_OUTPUT_ROOT
    ),
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Read a v5.6 dry-run and write a no-submit operator approval packet."""

    source_path = Path(dry_run_path)
    dry_run = _read_json_mapping(source_path)
    packet = build_crypto_paper_submit_approval_packet(
        dry_run=dry_run,
        dry_run_source=source_path,
    )
    if write_artifacts:
        packet["artifact_paths"] = (
            write_crypto_paper_submit_approval_packet_artifacts(
                output_root,
                packet,
            )
        )
    return packet


def build_crypto_paper_submit_approval_packet(
    *,
    dry_run: Mapping[str, object],
    dry_run_source: Path | str,
) -> dict[str, object]:
    """Build a primitive-only packet that requests future operator review."""

    source_path = Path(dry_run_source)
    source_labels = list(_string_sequence(dry_run.get("labels")))
    dry_run_status = _first_text(dry_run, "dry_run_status")
    source_approval_state = _first_text(dry_run, "approval_state")
    selected_candidate_id = _first_text(dry_run, "selected_candidate_id")
    selected_backing = _first_text(dry_run, "selected_backing")
    symbol = _first_text(dry_run, "symbol")
    asset_class = _first_text(dry_run, "asset_class")
    intended_action = _first_text(dry_run, "intended_action")
    dry_run_id = _first_text(dry_run, "dry_run_id")
    pre_broker_order_id = _first_text(
        dry_run,
        "pre_broker_order_id",
        "preview_client_order_id",
    )
    idempotency_key = _first_text(dry_run, "idempotency_key")
    rounded_qty = _positive_decimal_field(dry_run, "rounded_qty")
    derived_preview_value = _positive_decimal_field(
        dry_run,
        "derived_preview_value",
    )
    preview_cap = _positive_decimal_field(
        dry_run,
        "preview_cap",
        "preview_notional_cap",
        "max_preview_value",
    )
    missing_required_labels = _missing_required_source_labels(
        source_labels=source_labels,
        selected_backing=selected_backing,
    )
    source_blockers = list(_string_sequence(dry_run.get("blockers")))
    blockers = _approval_packet_blockers(
        dry_run=dry_run,
        dry_run_status=dry_run_status,
        source_approval_state=source_approval_state,
        intended_action=intended_action,
        asset_class=asset_class,
        selected_candidate_id=selected_candidate_id,
        selected_backing=selected_backing,
        rounded_qty=rounded_qty,
        derived_preview_value=derived_preview_value,
        preview_cap=preview_cap,
        dry_run_id=dry_run_id,
        pre_broker_order_id=pre_broker_order_id,
        idempotency_key=idempotency_key,
        source_blockers=source_blockers,
        missing_required_labels=missing_required_labels,
    )
    approval_packet_status = (
        "blocked" if blockers else "ready_for_operator_review"
    )
    qty_text = _decimal_or_empty(rounded_qty)
    preview_value_text = _decimal_or_empty(derived_preview_value)
    cap_text = _decimal_or_empty(preview_cap)
    required_operator_phrase = _required_operator_phrase(
        symbol=symbol,
        dry_run_id=dry_run_id,
        pre_broker_order_id=pre_broker_order_id,
        qty=qty_text,
        cap=cap_text,
    )
    labels = _approval_packet_labels(
        source_labels=source_labels,
        selected_backing=selected_backing,
    )
    next_operator_action = _next_operator_action(approval_packet_status)

    return {
        "schema_version": CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_SCHEMA_VERSION,
        "as_of": _first_text(dry_run, "as_of"),
        "dry_run_source": str(source_path),
        "approval_packet_status": approval_packet_status,
        "approval_state": "not_authorized",
        "source_approval_state": source_approval_state,
        "broker_action_permitted": False,
        "requested_future_authorization_scope": (
            CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUESTED_SCOPE
        ),
        "dry_run_id": dry_run_id,
        "pre_broker_order_id": pre_broker_order_id,
        "idempotency_key": idempotency_key,
        "selected_candidate_id": selected_candidate_id,
        "selected_backing": selected_backing,
        "symbol": symbol,
        "asset_class": asset_class,
        "intended_action": intended_action,
        "rounded_qty": qty_text,
        "derived_preview_value": preview_value_text,
        "preview_cap": cap_text,
        "exact_candidate_id": selected_candidate_id,
        "exact_symbol": symbol,
        "exact_asset_class": asset_class,
        "exact_intended_action": intended_action,
        "exact_qty": qty_text,
        "exact_preview_value": preview_value_text,
        "exact_cap": cap_text,
        "required_operator_phrase": required_operator_phrase,
        "disallowed_actions": list(
            CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_DISALLOWED_ACTIONS
        ),
        "blockers": blockers,
        "source_blockers": source_blockers,
        "missing_required_labels": missing_required_labels,
        "paper_submit_authorized": False,
        "paper_cancel_authorized": False,
        "paper_submit_performed": False,
        "paper_cancel_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "broker_read_performed_current_run": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "labels": labels,
        "no_submit_statement": (
            "This packet is an operator-review request only. No paper submit "
            "is authorized by this packet, and no broker mutation is permitted."
        ),
        "next_operator_action": next_operator_action,
        "source_dry_run_summary": _source_dry_run_summary(dry_run),
    }


def write_crypto_paper_submit_approval_packet_artifacts(
    output_root: Path | str,
    packet: Mapping[str, object],
) -> dict[str, str]:
    """Write ignored runtime artifacts for the no-submit approval packet."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "paper_submit_approval_packet_json": (
            root / "paper_submit_approval_packet.json"
        ),
        "paper_submit_approval_packet_md": (
            root / "paper_submit_approval_packet.md"
        ),
        "operating_record": root / "operating_record.jsonl",
    }
    _write_json(paths["paper_submit_approval_packet_json"], packet)
    paths["paper_submit_approval_packet_md"].write_text(
        render_crypto_paper_submit_approval_packet_markdown(packet) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    paths["operating_record"].write_text(
        json.dumps(
            _json_safe(
                {
                    "record_type": "crypto_paper_submit_approval_packet",
                    "schema_version": (
                        CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_SCHEMA_VERSION
                    ),
                    "as_of": packet.get("as_of", ""),
                    "dry_run_source": packet.get("dry_run_source", ""),
                    "approval_packet_status": packet.get(
                        "approval_packet_status",
                        "",
                    ),
                    "approval_state": "not_authorized",
                    "requested_future_authorization_scope": (
                        CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUESTED_SCOPE
                    ),
                    "broker_action_permitted": False,
                    "paper_submit_authorized": False,
                    "paper_submit_performed": False,
                    "broker_mutation_performed": False,
                    "live_mutation_performed": False,
                    "live_endpoint_touched": False,
                    "credential_values_exposed": False,
                    "dry_run_id": packet.get("dry_run_id", ""),
                    "pre_broker_order_id": packet.get("pre_broker_order_id", ""),
                    "idempotency_key": packet.get("idempotency_key", ""),
                    "selected_candidate_id": packet.get(
                        "selected_candidate_id",
                        "",
                    ),
                    "symbol": packet.get("symbol", ""),
                    "rounded_qty": packet.get("rounded_qty", ""),
                    "derived_preview_value": packet.get(
                        "derived_preview_value",
                        "",
                    ),
                    "preview_cap": packet.get("preview_cap", ""),
                    "blockers": packet.get("blockers", []),
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
        "schema_version": CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_SCHEMA_VERSION,
        "as_of": packet.get("as_of", ""),
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
            "paper_oms_dry_run": _artifact_reference(
                _first_text(packet, "dry_run_source")
            ),
        },
        "approval_packet_status": packet.get("approval_packet_status", ""),
        "approval_state": "not_authorized",
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
        "labels": list(_string_sequence(packet.get("labels"))),
        "profit_claim": "none",
    }
    _write_json(manifest_path, manifest)
    return {
        **{key: str(path) for key, path in paths.items()},
        "manifest": str(manifest_path),
    }


def render_crypto_paper_submit_approval_packet_markdown(
    packet: Mapping[str, object],
) -> str:
    """Render the operator-facing no-submit approval packet."""

    blockers = list(_string_sequence(packet.get("blockers")))
    return "\n".join(
        [
            "# Crypto Paper Submit Approval Packet",
            "",
            f"- dry-run source: `{packet.get('dry_run_source', '')}`",
            f"- dry-run id: `{packet.get('dry_run_id', '')}`",
            f"- pre-broker order id: `{packet.get('pre_broker_order_id', '')}`",
            f"- idempotency key: `{packet.get('idempotency_key', '')}`",
            f"- selected candidate: `{packet.get('selected_candidate_id', '')}`",
            f"- intended action: `{packet.get('intended_action', '')}`",
            f"- symbol: `{packet.get('symbol', '')}`",
            f"- qty: `{packet.get('rounded_qty', '')}`",
            (
                "- derived preview value: "
                f"`{packet.get('derived_preview_value', '')}`"
            ),
            f"- cap: `{packet.get('preview_cap', '')}`",
            f"- current approval state: `{packet.get('approval_state', '')}`",
            (
                "- requested future authorization scope: "
                f"`{packet.get('requested_future_authorization_scope', '')}`"
            ),
            (
                "- approval packet status: "
                f"`{packet.get('approval_packet_status', '')}`"
            ),
            f"- blockers: `{','.join(blockers)}`",
            "",
            "## Future Authorization Phrase",
            "",
            str(packet.get("required_operator_phrase", "")),
            "",
            "## Current Authority",
            "",
            (
                "No paper submit is authorized by this packet. Broker action "
                "remains blocked, approval_state remains not_authorized, and "
                "all submit/mutation/live flags remain false."
            ),
            "",
            "## Next Operator Action",
            "",
            str(packet.get("next_operator_action", "")),
            "",
            "Labels: " + ", ".join(_string_sequence(packet.get("labels"))),
        ]
    )


def _approval_packet_blockers(
    *,
    dry_run: Mapping[str, object],
    dry_run_status: str,
    source_approval_state: str,
    intended_action: str,
    asset_class: str,
    selected_candidate_id: str,
    selected_backing: str,
    rounded_qty: Decimal | None,
    derived_preview_value: Decimal | None,
    preview_cap: Decimal | None,
    dry_run_id: str,
    pre_broker_order_id: str,
    idempotency_key: str,
    source_blockers: Sequence[str],
    missing_required_labels: Sequence[str],
) -> list[str]:
    blockers: list[str] = []
    if dry_run_status != "blocked_not_authorized":
        blockers.append("dry_run_status_not_blocked_not_authorized")
    if source_blockers:
        blockers.append("dry_run_contains_source_blockers")
    if source_approval_state != "not_authorized":
        blockers.append("approval_state_not_not_authorized")
    if asset_class != "crypto":
        blockers.append("asset_class_not_crypto")
    if intended_action != "buy_preview":
        blockers.append("intended_action_not_buy_preview")
    if not selected_candidate_id:
        blockers.append("missing_selected_candidate_id")
    if selected_backing not in CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_ACCEPTED_BACKINGS:
        blockers.append("unsupported_selected_backing")
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
    if not dry_run_id:
        blockers.append("missing_dry_run_id")
    if not pre_broker_order_id:
        blockers.append("missing_pre_broker_order_id")
    if not idempotency_key:
        blockers.append("missing_idempotency_key")
    blockers.extend(
        _false_flag_blockers(
            dry_run,
            CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUIRED_FALSE_FLAGS,
        )
    )
    blockers.extend(
        _false_flag_blockers(
            dry_run,
            CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_EXTRA_FALSE_SOURCE_FLAGS,
        )
    )
    if _first_text(dry_run, "profit_claim") != "none":
        blockers.append("profit_claim_not_none")
    if missing_required_labels:
        blockers.append("missing_required_safety_labels")
    return list(_dedupe(blockers))


def _missing_required_source_labels(
    *,
    source_labels: Sequence[str],
    selected_backing: str,
) -> list[str]:
    required = list(CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_SOURCE_REQUIRED_LABELS)
    if selected_backing in CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_ACCEPTED_BACKINGS:
        required.append(selected_backing)
    else:
        required.append("real_local_artifact_backed_or_real_paper_read_backed")
    label_set = set(source_labels)
    return [label for label in required if label not in label_set]


def _approval_packet_labels(
    *,
    source_labels: Sequence[str],
    selected_backing: str,
) -> list[str]:
    labels = [
        *source_labels,
        *CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUIRED_LABELS,
    ]
    if selected_backing in CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_ACCEPTED_BACKINGS:
        labels.append(selected_backing)
    return list(_dedupe(labels))


def _false_flag_blockers(
    row: Mapping[str, object],
    field_names: Sequence[str],
) -> list[str]:
    blockers: list[str] = []
    for field_name in field_names:
        value = _first_value(row, field_name)
        if _is_true(value):
            blockers.append(f"{field_name}_true")
        elif not _is_false(value):
            blockers.append(f"{field_name}_not_false")
    return blockers


def _required_operator_phrase(
    *,
    symbol: str,
    dry_run_id: str,
    pre_broker_order_id: str,
    qty: str,
    cap: str,
) -> str:
    return (
        f"Authorized for v5.8: perform one bounded {symbol} Alpaca paper "
        f"submit/cancel certification using dry_run_id {dry_run_id}, "
        f"pre_broker_order_id {pre_broker_order_id}, qty {qty}, max "
        f"notional {cap}. This authorizes exactly one paper order submit "
        "attempt and its cancel/reconciliation path only. It does not "
        "authorize live trading, additional orders, replacement, liquidation, "
        "close-all, capital changes, credential exposure, or paid services."
    )


def _source_dry_run_summary(dry_run: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": _first_text(dry_run, "schema_version"),
        "as_of": _first_text(dry_run, "as_of"),
        "dry_run_status": _first_text(dry_run, "dry_run_status"),
        "approval_state": _first_text(dry_run, "approval_state"),
        "broker_action_permitted": _is_true(
            _first_value(dry_run, "broker_action_permitted")
        ),
        "intended_action": _first_text(dry_run, "intended_action"),
        "asset_class": _first_text(dry_run, "asset_class"),
        "symbol": _first_text(dry_run, "symbol"),
        "selected_candidate_id": _first_text(dry_run, "selected_candidate_id"),
        "selected_backing": _first_text(dry_run, "selected_backing"),
        "dry_run_id": _first_text(dry_run, "dry_run_id"),
        "pre_broker_order_id": _first_text(dry_run, "pre_broker_order_id"),
        "idempotency_key": _first_text(dry_run, "idempotency_key"),
        "blockers": list(_string_sequence(dry_run.get("blockers"))),
        "labels": list(_string_sequence(dry_run.get("labels"))),
        "paper_submit_authorized": _is_true(
            _first_value(dry_run, "paper_submit_authorized")
        ),
        "paper_submit_performed": _is_true(
            _first_value(dry_run, "paper_submit_performed")
        ),
        "broker_mutation_performed": _is_true(
            _first_value(dry_run, "broker_mutation_performed")
        ),
        "live_mutation_performed": _is_true(
            _first_value(dry_run, "live_mutation_performed")
        ),
        "live_endpoint_touched": _is_true(
            _first_value(dry_run, "live_endpoint_touched")
        ),
        "credential_values_exposed": _is_true(
            _first_value(dry_run, "credential_values_exposed")
        ),
    }


def _next_operator_action(approval_packet_status: str) -> str:
    if approval_packet_status == "ready_for_operator_review":
        return (
            "operator_may_copy_the_exact_required_operator_phrase_into_the_"
            "next_v5_8_authorization_milestone_if_choosing_to_authorize_one_"
            "bounded_paper_submit_cancel_certification"
        )
    return "repair_dry_run_safety_blockers_then_rerun_v5_6_dry_run_and_v5_7_packet"


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


def _is_false(value: object) -> bool:
    if type(value) is bool:
        return value is False
    if type(value) is str:
        return value.strip().lower() == "false"
    return False


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item).strip())
    if value in (None, ""):
        return ()
    return (str(value),)


def _first_text(row: Mapping[str, object], *field_names: str) -> str:
    return _text(_first_value(row, *field_names))


def _first_value(row: Mapping[str, object], *field_names: str) -> object:
    wanted = {_field_lookup_key(field_name) for field_name in field_names}
    for key, value in row.items():
        if _field_lookup_key(key) in wanted:
            return value
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
        description="Build a no-submit crypto paper-submit approval packet.",
    )
    parser.add_argument(
        "--dry-run-path",
        type=Path,
        default=CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_DEFAULT_DRY_RUN,
        help="Path to v5.6 paper_oms_dry_run.json.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_DEFAULT_OUTPUT_ROOT,
        help="Output root for ignored approval-packet artifacts.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    packet = run_crypto_paper_submit_approval_packet(
        dry_run_path=args.dry_run_path,
        output_root=args.output_root,
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(packet), sort_keys=True))
    else:
        artifacts = packet.get("artifact_paths")
        artifact_map = artifacts if isinstance(artifacts, Mapping) else {}
        print(
            "approval_packet_status="
            + _text(packet.get("approval_packet_status"))
        )
        print("approval_state=" + _text(packet.get("approval_state")))
        print(
            "requested_future_authorization_scope="
            + _text(packet.get("requested_future_authorization_scope"))
        )
        print(
            "broker_action_permitted="
            + _text(packet.get("broker_action_permitted", False))
        )
        print("paper_submit_authorized=false")
        print("paper_submit_performed=false")
        print("broker_mutation_performed=false")
        print("live_mutation_performed=false")
        print("live_endpoint_touched=false")
        print("credential_values_exposed=false")
        print("selected_candidate_id=" + _text(packet.get("selected_candidate_id")))
        print("symbol=" + _text(packet.get("symbol")))
        print("rounded_qty=" + _text(packet.get("rounded_qty")))
        print("derived_preview_value=" + _text(packet.get("derived_preview_value")))
        print("preview_cap=" + _text(packet.get("preview_cap")))
        print("dry_run_id=" + _text(packet.get("dry_run_id")))
        print("pre_broker_order_id=" + _text(packet.get("pre_broker_order_id")))
        print("idempotency_key=" + _text(packet.get("idempotency_key")))
        print("blockers=" + ",".join(_string_sequence(packet.get("blockers"))))
        print(
            "artifact_paper_submit_approval_packet_json="
            + _text(artifact_map.get("paper_submit_approval_packet_json"))
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
