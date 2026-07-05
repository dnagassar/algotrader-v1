"""No-submit crypto Paper OMS approval handoff packet.

This module consumes the v5.4 crypto quantity sizing preview and produces a
pre-broker operator review packet. It does not create broker clients, read a
broker, submit paper orders, or mutate broker state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.orchestration.crypto_qty_sizing_preview import (
    CRYPTO_QTY_SIZING_PREVIEW_REQUIRED_LABELS,
    CRYPTO_QTY_SIZING_PREVIEW_SAFE_ORDERABILITY_STATUSES,
)

CRYPTO_PAPER_OMS_HANDOFF_SCHEMA_VERSION = "v5_5_crypto_paper_oms_handoff_v1"
CRYPTO_PAPER_OMS_HANDOFF_DEFAULT_SIZING_PREVIEW = Path(
    "runs/crypto_qty_sizing_preview/latest/sizing_preview.json"
)
CRYPTO_PAPER_OMS_HANDOFF_DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_paper_oms_handoff/latest"
)

CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_LABELS = (
    *CRYPTO_QTY_SIZING_PREVIEW_REQUIRED_LABELS,
    "paper_oms_handoff_only",
    "approval_required",
)
CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_FALSE_FLAGS = (
    "paper_submit_authorized",
    "paper_submit_performed",
    "broker_mutation_performed",
    "live_mutation_performed",
)
CRYPTO_PAPER_OMS_HANDOFF_ACCEPTED_BACKINGS = (
    "real_local_artifact_backed",
    "real_paper_read_backed",
)

__all__ = [
    "CRYPTO_PAPER_OMS_HANDOFF_ACCEPTED_BACKINGS",
    "CRYPTO_PAPER_OMS_HANDOFF_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_PAPER_OMS_HANDOFF_DEFAULT_SIZING_PREVIEW",
    "CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_FALSE_FLAGS",
    "CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_LABELS",
    "CRYPTO_PAPER_OMS_HANDOFF_SCHEMA_VERSION",
    "build_crypto_paper_oms_handoff_packet",
    "main",
    "render_paper_oms_handoff_markdown",
    "run_crypto_paper_oms_handoff",
    "write_crypto_paper_oms_handoff_artifacts",
]


def run_crypto_paper_oms_handoff(
    *,
    sizing_preview_path: Path | str = CRYPTO_PAPER_OMS_HANDOFF_DEFAULT_SIZING_PREVIEW,
    output_root: Path | str = CRYPTO_PAPER_OMS_HANDOFF_DEFAULT_OUTPUT_ROOT,
    allow_fixture_backed: bool = False,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Read a v5.4 sizing preview and write a no-submit handoff packet."""

    source_path = Path(sizing_preview_path)
    payload = _read_json_mapping(source_path)
    sizing_preview = _preview_mapping(payload)
    packet = build_crypto_paper_oms_handoff_packet(
        sizing_preview=sizing_preview,
        sizing_preview_source=source_path,
        allow_fixture_backed=allow_fixture_backed,
    )
    if write_artifacts:
        packet["artifact_paths"] = write_crypto_paper_oms_handoff_artifacts(
            output_root,
            packet,
        )
    return packet


def build_crypto_paper_oms_handoff_packet(
    *,
    sizing_preview: Mapping[str, object],
    sizing_preview_source: Path | str,
    allow_fixture_backed: bool = False,
) -> dict[str, object]:
    """Build a primitive-only pre-broker approval handoff packet."""

    source_path = Path(sizing_preview_source)
    source_labels = list(_string_sequence(sizing_preview.get("labels")))
    source_blockers = list(_string_sequence(sizing_preview.get("blockers")))
    selected_candidate_id = _first_text(sizing_preview, "selected_candidate_id")
    symbol = _first_text(sizing_preview, "selected_symbol", "symbol")
    strategy_id = _first_text(
        sizing_preview,
        "selected_strategy",
        "strategy_id",
        "selected_strategy_id",
    )
    source_selected_backing = _first_text(sizing_preview, "selected_backing")
    selected_backing = _canonical_backing(
        source_selected_backing,
        source_labels=source_labels,
    )
    asset_class = _asset_class(sizing_preview, selected_candidate_id)
    orderability_status = _first_text(sizing_preview, "orderability_status")
    orderability_basis = _first_text(sizing_preview, "orderability_basis")
    sizing_status = _first_text(sizing_preview, "sizing_status")
    router_decision = _first_text(sizing_preview, "router_decision")
    profit_claim = _first_text(sizing_preview, "profit_claim")

    latest_price = _positive_decimal_field(sizing_preview, "latest_price")
    preview_notional_cap = _positive_decimal_field(
        sizing_preview,
        "preview_notional_cap",
    )
    rounded_qty = _positive_decimal_field(sizing_preview, "rounded_qty")
    derived_preview_value = _positive_decimal_field(
        sizing_preview,
        "derived_preview_value",
    )
    min_order_size = _positive_decimal_field(
        sizing_preview,
        "broker_observed_min_order_size",
    )
    min_trade_increment = _positive_decimal_field(
        sizing_preview,
        "broker_observed_min_trade_increment",
    )

    missing_required_labels = _missing_required_labels(
        source_labels=source_labels,
        selected_backing=selected_backing,
        allow_fixture_backed=allow_fixture_backed,
    )
    blockers = _handoff_blockers(
        sizing_preview=sizing_preview,
        source_blockers=source_blockers,
        selected_candidate_id=selected_candidate_id,
        symbol=symbol,
        strategy_id=strategy_id,
        asset_class=asset_class,
        selected_backing=selected_backing,
        source_selected_backing=source_selected_backing,
        orderability_status=orderability_status,
        orderability_basis=orderability_basis,
        sizing_status=sizing_status,
        router_decision=router_decision,
        latest_price=latest_price,
        preview_notional_cap=preview_notional_cap,
        rounded_qty=rounded_qty,
        derived_preview_value=derived_preview_value,
        min_order_size=min_order_size,
        min_trade_increment=min_trade_increment,
        missing_required_labels=missing_required_labels,
        profit_claim=profit_claim,
        allow_fixture_backed=allow_fixture_backed,
    )
    handoff_status = "blocked" if blockers else "approval_required"
    intended_action = "buy_preview" if handoff_status == "approval_required" else "no_action"
    labels = _handoff_labels(
        source_labels=source_labels,
        selected_backing=selected_backing,
        allow_fixture_backed=allow_fixture_backed,
    )
    as_of = _first_text(sizing_preview, "as_of")
    quantity_text = _decimal_or_empty(rounded_qty)
    latest_price_text = _decimal_or_empty(latest_price)
    cap_text = _decimal_or_empty(preview_notional_cap)
    derived_value_text = _decimal_or_empty(derived_preview_value)
    next_operator_action = _next_operator_action(handoff_status)
    approval_state = "not_authorized"
    required_operator_authorization = (
        "explicit_operator_approval_required_before_any_separate_future_paper_submit"
    )

    execution_intent = {
        "intent_status": handoff_status,
        "pre_broker": True,
        "asset_class": asset_class,
        "symbol": symbol,
        "strategy_id": strategy_id,
        "side": "buy" if intended_action == "buy_preview" else "",
        "quantity": quantity_text,
        "notional": derived_value_text,
        "source_sizing_preview": str(source_path),
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
    }
    execution_plan = {
        "plan_status": handoff_status,
        "immutable": True,
        "pre_broker": True,
        "approval_state": approval_state,
        "submit_allowed": False,
        "broker_request_created": False,
        "broker_request_sent": False,
        "intended_action": intended_action,
        "asset_class": asset_class,
        "symbol": symbol,
        "strategy_id": strategy_id,
        "quantity": quantity_text,
        "max_preview_value": cap_text,
        "blockers": blockers,
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
    }
    packet = {
        "schema_version": CRYPTO_PAPER_OMS_HANDOFF_SCHEMA_VERSION,
        "as_of": as_of,
        "sizing_preview_source": str(source_path),
        "handoff_status": handoff_status,
        "approval_state": approval_state,
        "intended_action": intended_action,
        "asset_class": asset_class,
        "symbol": symbol,
        "strategy_id": strategy_id,
        "selected_candidate_id": selected_candidate_id,
        "selected_backing": selected_backing,
        "source_selected_backing": source_selected_backing,
        "orderability_status": orderability_status,
        "orderability_basis": orderability_basis,
        "latest_price": latest_price_text,
        "preview_notional_cap": cap_text,
        "rounded_qty": quantity_text,
        "derived_preview_value": derived_value_text,
        "max_preview_value": cap_text,
        "blockers": blockers,
        "source_blockers": source_blockers,
        "missing_required_labels": missing_required_labels,
        "required_operator_authorization": required_operator_authorization,
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "broker_read_performed_current_run": False,
        "network_access_attempted": False,
        "live_endpoint_touched": False,
        "profit_claim": "none",
        "labels": labels,
        "source_sizing_status": sizing_status,
        "source_router_decision": router_decision,
        "next_operator_action": next_operator_action,
        "no_submit_statement": (
            "This packet does not submit or authorize submission and cannot "
            "cancel, replace, close, liquidate, or mutate broker state."
        ),
        "execution_intent": execution_intent,
        "execution_plan": execution_plan,
        "source_sizing_preview": dict(sizing_preview),
    }
    return packet


def write_crypto_paper_oms_handoff_artifacts(
    output_root: Path | str,
    packet: Mapping[str, object],
) -> dict[str, str]:
    """Write ignored runtime artifacts for the no-submit approval handoff."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "paper_oms_handoff_json": root / "paper_oms_handoff.json",
        "paper_oms_handoff_md": root / "paper_oms_handoff.md",
        "operating_record": root / "operating_record.jsonl",
    }
    _write_json(paths["paper_oms_handoff_json"], packet)
    paths["paper_oms_handoff_md"].write_text(
        render_paper_oms_handoff_markdown(packet) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    paths["operating_record"].write_text(
        json.dumps(
            _json_safe(
                {
                    "record_type": "crypto_paper_oms_handoff",
                    "schema_version": CRYPTO_PAPER_OMS_HANDOFF_SCHEMA_VERSION,
                    "as_of": packet.get("as_of", ""),
                    "handoff_status": packet.get("handoff_status", ""),
                    "approval_state": packet.get("approval_state", ""),
                    "intended_action": packet.get("intended_action", ""),
                    "selected_candidate_id": packet.get("selected_candidate_id", ""),
                    "selected_backing": packet.get("selected_backing", ""),
                    "blockers": packet.get("blockers", []),
                    "paper_submit_authorized": False,
                    "paper_submit_performed": False,
                    "broker_mutation_performed": False,
                    "live_mutation_performed": False,
                    "broker_read_performed_current_run": False,
                    "network_access_attempted": False,
                    "live_endpoint_touched": False,
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
        "schema_version": CRYPTO_PAPER_OMS_HANDOFF_SCHEMA_VERSION,
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
        "input_artifacts": {
            "sizing_preview": _artifact_reference(
                _first_text(packet, "sizing_preview_source")
            ),
        },
        "handoff_status": packet.get("handoff_status", ""),
        "approval_state": "not_authorized",
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "broker_read_performed_current_run": False,
        "network_access_attempted": False,
        "live_endpoint_touched": False,
        "generated_under_runs": "runs" in root.parts,
        "labels": list(_string_sequence(packet.get("labels"))),
        "profit_claim": "none",
    }
    _write_json(manifest_path, manifest)
    return {
        **{key: str(path) for key, path in paths.items()},
        "manifest": str(manifest_path),
    }


def render_paper_oms_handoff_markdown(packet: Mapping[str, object]) -> str:
    """Render the operator-facing no-submit Paper OMS handoff brief."""

    blockers = list(_string_sequence(packet.get("blockers")))
    flags = {
        "paper_submit_authorized": packet.get("paper_submit_authorized", False),
        "paper_submit_performed": packet.get("paper_submit_performed", False),
        "broker_mutation_performed": packet.get("broker_mutation_performed", False),
        "live_mutation_performed": packet.get("live_mutation_performed", False),
        "broker_read_performed_current_run": packet.get(
            "broker_read_performed_current_run",
            False,
        ),
        "network_access_attempted": packet.get("network_access_attempted", False),
        "live_endpoint_touched": packet.get("live_endpoint_touched", False),
    }
    return "\n".join(
        [
            "# Crypto Paper OMS Approval Handoff",
            "",
            f"- selected candidate: `{packet.get('selected_candidate_id', '')}`",
            f"- selected strategy: `{packet.get('strategy_id', '')}`",
            f"- selected backing/provenance: `{packet.get('selected_backing', '')}`",
            f"- intended preview action: `{packet.get('intended_action', '')}`",
            f"- asset class: `{packet.get('asset_class', '')}`",
            f"- symbol: `{packet.get('symbol', '')}`",
            f"- orderability status: `{packet.get('orderability_status', '')}`",
            f"- orderability basis: `{packet.get('orderability_basis', '')}`",
            f"- latest price: `{packet.get('latest_price', '')}`",
            f"- rounded qty: `{packet.get('rounded_qty', '')}`",
            f"- derived preview value: `{packet.get('derived_preview_value', '')}`",
            f"- cap used: `{packet.get('preview_notional_cap', '')}`",
            f"- max preview value: `{packet.get('max_preview_value', '')}`",
            f"- handoff status: `{packet.get('handoff_status', '')}`",
            f"- approval state: `{packet.get('approval_state', '')}`",
            f"- blockers: `{', '.join(blockers) if blockers else 'none'}`",
            f"- safety flags: `{_flag_summary(flags)}`",
            "- no-submit statement: this packet does not submit or authorize submission.",
            "- mutation statement: this packet cannot cancel, replace, close, liquidate, or mutate broker state.",
            f"- exact next operator action: `{packet.get('next_operator_action', '')}`",
            "",
            "Labels: " + ", ".join(_string_sequence(packet.get("labels"))),
        ]
    )


def _handoff_blockers(
    *,
    sizing_preview: Mapping[str, object],
    source_blockers: Sequence[str],
    selected_candidate_id: str,
    symbol: str,
    strategy_id: str,
    asset_class: str,
    selected_backing: str,
    source_selected_backing: str,
    orderability_status: str,
    orderability_basis: str,
    sizing_status: str,
    router_decision: str,
    latest_price: Decimal | None,
    preview_notional_cap: Decimal | None,
    rounded_qty: Decimal | None,
    derived_preview_value: Decimal | None,
    min_order_size: Decimal | None,
    min_trade_increment: Decimal | None,
    missing_required_labels: Sequence[str],
    profit_claim: str,
    allow_fixture_backed: bool,
) -> list[str]:
    blockers: list[str] = list(source_blockers)
    if sizing_status == "blocked":
        blockers.append("upstream_sizing_blocked")
    elif sizing_status != "preview_ready":
        blockers.append("sizing_status_not_preview_ready")
    if router_decision == "no_trade":
        blockers.append("router_decision_no_trade")
    elif router_decision != "selected":
        blockers.append("router_decision_not_selected")
    if not selected_candidate_id:
        blockers.append("missing_selected_candidate")
    if not symbol:
        blockers.append("missing_symbol")
    if not strategy_id:
        blockers.append("missing_selected_strategy")
    if asset_class != "crypto":
        blockers.append("selected_candidate_not_crypto")
    if source_selected_backing == "fixture_backed" and not allow_fixture_backed:
        blockers.append("fixture_backed_candidate")
    if (
        selected_backing not in CRYPTO_PAPER_OMS_HANDOFF_ACCEPTED_BACKINGS
        and not (allow_fixture_backed and selected_backing == "fixture_backed")
    ):
        blockers.append("unsupported_selected_backing")
    if orderability_status not in CRYPTO_QTY_SIZING_PREVIEW_SAFE_ORDERABILITY_STATUSES:
        blockers.append("unsafe_orderability_status")
    if not orderability_basis:
        blockers.append("missing_orderability_basis")
    if latest_price is None:
        blockers.append("missing_or_invalid_latest_price")
    if preview_notional_cap is None:
        blockers.append("missing_or_invalid_preview_notional_cap")
    if rounded_qty is None:
        blockers.append("missing_or_invalid_rounded_qty")
    if derived_preview_value is None:
        blockers.append("missing_or_invalid_derived_preview_value")
    if min_order_size is None:
        blockers.append("missing_min_order_size")
    if min_trade_increment is None:
        blockers.append("missing_min_trade_increment")
    if (
        preview_notional_cap is not None
        and derived_preview_value is not None
        and derived_preview_value > preview_notional_cap
    ):
        blockers.append("derived_preview_value_exceeds_cap")
    for field_name in CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_FALSE_FLAGS:
        if _is_true(sizing_preview.get(field_name)):
            blockers.append(f"{field_name}_true")
    if profit_claim != "none":
        blockers.append("profit_claim_not_none")
    if missing_required_labels:
        blockers.append("missing_required_safety_labels")
    if _source_blockers_require_repair(source_blockers):
        blockers.append("source_blockers_require_repair")
    return list(_dedupe(blockers))


def _missing_required_labels(
    *,
    source_labels: Sequence[str],
    selected_backing: str,
    allow_fixture_backed: bool,
) -> list[str]:
    required = list(CRYPTO_QTY_SIZING_PREVIEW_REQUIRED_LABELS)
    if selected_backing in CRYPTO_PAPER_OMS_HANDOFF_ACCEPTED_BACKINGS:
        required.append(selected_backing)
    elif allow_fixture_backed and selected_backing == "fixture_backed":
        required.append("fixture_backed")
    else:
        required.append("real_local_artifact_backed_or_real_paper_read_backed")
    label_set = set(source_labels)
    return [label for label in required if label not in label_set]


def _handoff_labels(
    *,
    source_labels: Sequence[str],
    selected_backing: str,
    allow_fixture_backed: bool,
) -> list[str]:
    labels: list[str] = [*source_labels, *CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_LABELS]
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


def _asset_class(sizing_preview: Mapping[str, object], selected_candidate_id: str) -> str:
    explicit = _first_text(sizing_preview, "asset_class", "selected_asset_class")
    if explicit:
        return explicit
    prefix = selected_candidate_id.split(":", maxsplit=1)[0].strip()
    return prefix


def _source_blockers_require_repair(source_blockers: Sequence[str]) -> bool:
    for blocker in source_blockers:
        normalized = blocker.strip().lower()
        if (
            "stale" in normalized
            or "insufficient_history" in normalized
            or "metadata" in normalized
            or "missing_history" in normalized
            or "missing_data" in normalized
        ):
            return True
    return False


def _next_operator_action(handoff_status: str) -> str:
    if handoff_status == "approval_required":
        return "operator_review_handoff_packet_before_any_separate_paper_submit_authorization"
    return "repair_handoff_blockers_then_rerun_sizing_preview_and_handoff"


def _preview_mapping(payload: Mapping[str, object]) -> Mapping[str, object]:
    nested = payload.get("sizing_preview")
    if isinstance(nested, Mapping):
        return nested
    return payload


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
    field_name: str,
) -> Decimal | None:
    value = _first_text(row, field_name)
    if not value:
        return None
    try:
        parsed = _decimal_value(value, field_name)
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


def _flag_summary(flags: Mapping[str, object]) -> str:
    return ", ".join(
        f"{name}={str(value).lower()}" for name, value in sorted(flags.items())
    )


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
        description="Build a no-submit crypto Paper OMS approval handoff packet.",
    )
    parser.add_argument(
        "--sizing-preview",
        type=Path,
        default=CRYPTO_PAPER_OMS_HANDOFF_DEFAULT_SIZING_PREVIEW,
        help="Path to v5.4 sizing_preview.json.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=CRYPTO_PAPER_OMS_HANDOFF_DEFAULT_OUTPUT_ROOT,
        help="Output root for ignored handoff artifacts.",
    )
    parser.add_argument(
        "--allow-fixture-backed",
        action="store_true",
        help="Allow fixture-backed selected candidates for explicit fixture tests.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    packet = run_crypto_paper_oms_handoff(
        sizing_preview_path=args.sizing_preview,
        output_root=args.output_root,
        allow_fixture_backed=args.allow_fixture_backed,
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(packet), sort_keys=True))
    else:
        artifacts = packet.get("artifact_paths")
        artifact_map = artifacts if isinstance(artifacts, Mapping) else {}
        print("crypto_paper_oms_handoff_status=" + _text(packet.get("handoff_status")))
        print("approval_state=" + _text(packet.get("approval_state")))
        print("intended_action=" + _text(packet.get("intended_action")))
        print("selected_candidate_id=" + _text(packet.get("selected_candidate_id")))
        print("selected_backing=" + _text(packet.get("selected_backing")))
        print("latest_price=" + _text(packet.get("latest_price")))
        print("rounded_qty=" + _text(packet.get("rounded_qty")))
        print("derived_preview_value=" + _text(packet.get("derived_preview_value")))
        print("preview_notional_cap=" + _text(packet.get("preview_notional_cap")))
        print("blockers=" + ",".join(_string_sequence(packet.get("blockers"))))
        print("paper_submit_authorized=false")
        print("paper_submit_performed=false")
        print("broker_mutation_performed=false")
        print("live_mutation_performed=false")
        print(
            "artifact_paper_oms_handoff_json="
            + _text(artifact_map.get("paper_oms_handoff_json"))
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
