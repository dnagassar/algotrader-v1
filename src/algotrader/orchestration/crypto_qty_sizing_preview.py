"""Deterministic no-submit crypto quantity sizing preview packet."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from pathlib import Path

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError

CRYPTO_QTY_SIZING_PREVIEW_SCHEMA_VERSION = "v5_4_crypto_qty_sizing_preview_v1"
CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_qty_sizing_preview/latest"
)
CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_ROUTER_DECISION = Path(
    "runs/opportunity_router/paper_read_repair_latest/router_decision.json"
)
CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_OPPORTUNITY_CANDIDATES = Path(
    "runs/opportunity_router/paper_read_repair_latest/opportunity_candidates.json"
)
CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_CRYPTO_ROUTER_INPUT_MANIFEST = Path(
    "runs/crypto_universe_refresh/paper_read_repair_latest/"
    "crypto_router_input_manifest.json"
)
CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_NOTIONAL_CAP = Decimal("25")

CRYPTO_QTY_SIZING_PREVIEW_REQUIRED_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "not_live_authorized",
    "profit_claim=none",
    "no_submit_mode",
    "sizing_preview_only",
)

CRYPTO_QTY_SIZING_PREVIEW_SAFE_ORDERABILITY_STATUSES = (
    "qty_orderable",
    "qty_orderable_notional_unobserved",
    "notional_orderable",
)

__all__ = [
    "CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_CRYPTO_ROUTER_INPUT_MANIFEST",
    "CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_NOTIONAL_CAP",
    "CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_OPPORTUNITY_CANDIDATES",
    "CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_ROUTER_DECISION",
    "CRYPTO_QTY_SIZING_PREVIEW_REQUIRED_LABELS",
    "CRYPTO_QTY_SIZING_PREVIEW_SAFE_ORDERABILITY_STATUSES",
    "CRYPTO_QTY_SIZING_PREVIEW_SCHEMA_VERSION",
    "build_crypto_qty_sizing_preview_packet",
    "main",
    "render_sizing_preview_markdown",
    "run_crypto_qty_sizing_preview",
    "write_crypto_qty_sizing_preview_artifacts",
]


def run_crypto_qty_sizing_preview(
    *,
    router_decision_path: Path | str = CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_ROUTER_DECISION,
    opportunity_candidates_path: Path | str = (
        CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_OPPORTUNITY_CANDIDATES
    ),
    crypto_router_input_manifest_path: Path | str = (
        CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_CRYPTO_ROUTER_INPUT_MANIFEST
    ),
    output_root: Path | str = CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_OUTPUT_ROOT,
    preview_notional_cap: Decimal | str = CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_NOTIONAL_CAP,
    allow_fixture_backed: bool = False,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Consume router/refresh artifacts and write a deterministic sizing preview."""

    router_path = Path(router_decision_path)
    candidates_path = Path(opportunity_candidates_path)
    manifest_path = Path(crypto_router_input_manifest_path)
    router_decision = _read_json_mapping(router_path)
    opportunity_candidates = _read_json_mapping(candidates_path)
    crypto_router_input_manifest = _read_json_mapping(manifest_path)

    orderability_path = _resolve_manifest_path(
        manifest_path,
        _first_nonempty(
            _first_text(
                crypto_router_input_manifest,
                "crypto_orderability_metadata_path",
            ),
            "crypto_orderability_metadata.json",
        ),
    )
    history_manifest_path = _resolve_manifest_path(
        manifest_path,
        _first_nonempty(
            _first_text(crypto_router_input_manifest, "crypto_history_manifest_path"),
            "crypto_history_manifest.json",
        ),
    )
    orderability_metadata = _read_json_mapping(orderability_path)
    history_manifest = _read_json_mapping(history_manifest_path)

    packet = build_crypto_qty_sizing_preview_packet(
        router_decision=router_decision,
        opportunity_candidates=opportunity_candidates,
        crypto_router_input_manifest=crypto_router_input_manifest,
        orderability_metadata=orderability_metadata,
        history_manifest=history_manifest,
        router_decision_source=router_path,
        opportunity_candidates_source=candidates_path,
        crypto_router_input_manifest_source=manifest_path,
        orderability_metadata_source=orderability_path,
        history_manifest_source=history_manifest_path,
        preview_notional_cap=preview_notional_cap,
        allow_fixture_backed=allow_fixture_backed,
    )
    if write_artifacts:
        packet["artifact_paths"] = write_crypto_qty_sizing_preview_artifacts(
            output_root,
            packet,
        )
    return packet


def build_crypto_qty_sizing_preview_packet(
    *,
    router_decision: Mapping[str, object],
    opportunity_candidates: Mapping[str, object],
    crypto_router_input_manifest: Mapping[str, object],
    orderability_metadata: Mapping[str, object],
    history_manifest: Mapping[str, object],
    router_decision_source: Path | str,
    opportunity_candidates_source: Path | str,
    crypto_router_input_manifest_source: Path | str,
    orderability_metadata_source: Path | str,
    history_manifest_source: Path | str,
    preview_notional_cap: Decimal | str = CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_NOTIONAL_CAP,
    allow_fixture_backed: bool = False,
) -> dict[str, object]:
    """Build a primitive-only no-submit sizing preview packet."""

    cap = _positive_decimal(preview_notional_cap, "preview_notional_cap")
    router_path = Path(router_decision_source)
    candidates_path = Path(opportunity_candidates_source)
    manifest_path = Path(crypto_router_input_manifest_source)
    orderability_path = Path(orderability_metadata_source)
    history_manifest_path = Path(history_manifest_source)
    as_of = _utc_datetime(
        _first_nonempty(
            _first_text(router_decision, "as_of"),
            _first_text(crypto_router_input_manifest, "as_of"),
        ),
        "as_of",
    )
    decision = _first_text(router_decision, "decision")
    selected_candidate = _selected_candidate(router_decision, opportunity_candidates)
    selected_candidate_id = _first_text(router_decision, "selected_candidate_id")
    if not selected_candidate_id:
        selected_candidate_id = _first_text(selected_candidate, "candidate_id")
    selected_symbol = _first_text(
        selected_candidate,
        "symbol",
        "selected_symbol",
    )
    selected_strategy = _first_text(
        selected_candidate,
        "strategy_id",
        "selected_strategy_id",
        "strategy",
    )
    selected_backing = _selected_candidate_backing(
        router_decision=router_decision,
        candidate=selected_candidate,
        crypto_router_input_manifest=crypto_router_input_manifest,
    )
    metadata_record = _matching_symbol_record(
        orderability_metadata.get("records"),
        selected_symbol,
    )
    history_record = _matching_symbol_record(
        history_manifest.get("records"),
        selected_symbol,
    )
    orderability_status = _first_nonempty(
        _first_text(metadata_record, "orderability_status"),
        _first_text(selected_candidate, "orderability_status"),
    )
    orderability_basis = _first_nonempty(
        _first_text(metadata_record, "orderability_basis"),
        _first_text(selected_candidate, "orderability_basis"),
    )

    latest_price = _latest_price(
        history_record=history_record,
        history_manifest_source=history_manifest_path,
        as_of=as_of,
    )
    blockers = list(
        _selection_blockers(
            router_decision=router_decision,
            selected_candidate=selected_candidate,
            selected_backing=selected_backing,
            orderability_status=orderability_status,
            allow_fixture_backed=allow_fixture_backed,
        )
    )
    min_order_size = _optional_positive_decimal(
        _first_text(metadata_record, "broker_observed_min_order_size", "min_order_size"),
        "min_order_size",
    )
    min_trade_increment = _optional_positive_decimal(
        _first_text(
            metadata_record,
            "broker_observed_min_trade_increment",
            "min_trade_increment",
        ),
        "min_trade_increment",
    )
    sizing_inputs_required = decision == "selected" and bool(selected_symbol)
    if sizing_inputs_required:
        if metadata_record == {}:
            blockers.append("missing_orderability_metadata")
        if latest_price is None:
            blockers.append("missing_latest_price")
        if min_order_size is None:
            blockers.append("missing_min_order_size")
        if min_trade_increment is None:
            blockers.append("missing_min_trade_increment")

    raw_qty: Decimal | None = None
    rounded_qty: Decimal | None = None
    derived_preview_value: Decimal | None = None
    if (
        sizing_inputs_required
        and latest_price is not None
        and min_order_size is not None
        and min_trade_increment is not None
    ):
        raw_qty = cap / latest_price
        rounded_qty = _round_down_to_increment(raw_qty, min_trade_increment)
        if rounded_qty < min_order_size:
            blockers.append("below_min_order_size")
        derived_preview_value = rounded_qty * latest_price

    derived_min_order_value = ""
    if latest_price is not None and min_order_size is not None:
        derived_min_order_value = _decimal_text(latest_price * min_order_size)

    labels = _preview_labels(
        selected_backing=selected_backing,
        orderability_status=orderability_status,
        crypto_router_input_manifest=crypto_router_input_manifest,
    )
    blockers = list(_dedupe(blockers))
    sizing_status = "blocked" if blockers else "preview_ready"
    preview = {
        "schema_version": CRYPTO_QTY_SIZING_PREVIEW_SCHEMA_VERSION,
        "as_of": as_of.isoformat(),
        "router_decision_source": str(router_path),
        "selected_candidate_id": selected_candidate_id,
        "selected_symbol": selected_symbol,
        "selected_strategy": selected_strategy,
        "selected_backing": selected_backing,
        "orderability_status": orderability_status,
        "orderability_basis": orderability_basis,
        "broker_observed_min_notional": _first_text(
            metadata_record,
            "broker_observed_min_notional",
            "min_notional",
        ),
        "broker_observed_min_order_size": _decimal_or_empty(min_order_size),
        "broker_observed_min_trade_increment": _decimal_or_empty(min_trade_increment),
        "broker_observed_price_increment": _first_text(
            metadata_record,
            "broker_observed_price_increment",
            "price_increment",
        ),
        "latest_price": _decimal_or_empty(latest_price),
        "preview_notional_cap": _decimal_text(cap),
        "raw_qty": _decimal_or_empty(raw_qty),
        "rounded_qty": _decimal_or_empty(rounded_qty),
        "derived_preview_value": _decimal_or_empty(derived_preview_value),
        "derived_min_order_value": derived_min_order_value,
        "sizing_status": sizing_status,
        "blockers": blockers,
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "profit_claim": "none",
        "labels": labels,
        "selection_reason": _first_text(router_decision, "selection_reason"),
        "router_decision": decision,
        "opportunity_candidates_source": str(candidates_path),
        "crypto_router_input_manifest_source": str(manifest_path),
        "orderability_metadata_source": str(orderability_path),
        "history_manifest_source": str(history_manifest_path),
        "paper_submit_performed_current_run": False,
        "broker_read_performed_current_run": False,
        "network_access_attempted": False,
        "live_endpoint_touched": False,
        "next_operator_action": _next_operator_action(sizing_status),
    }
    return {
        "schema_version": CRYPTO_QTY_SIZING_PREVIEW_SCHEMA_VERSION,
        "as_of": as_of.isoformat(),
        "sizing_preview": preview,
        "router_decision": {
            "decision": decision,
            "selection_reason": _first_text(router_decision, "selection_reason"),
            "selected_router_score": _first_text(
                router_decision,
                "selected_router_score",
            ),
        },
        "selected_candidate": dict(selected_candidate),
        "input_artifacts": {
            "router_decision": str(router_path),
            "opportunity_candidates": str(candidates_path),
            "crypto_router_input_manifest": str(manifest_path),
            "crypto_orderability_metadata": str(orderability_path),
            "crypto_history_manifest": str(history_manifest_path),
        },
        "safety": {
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_performed": False,
            "live_mutation_performed": False,
            "network_access_attempted": False,
            "broker_read_performed_current_run": False,
            "profit_claim": "none",
            "labels": labels,
        },
    }


def write_crypto_qty_sizing_preview_artifacts(
    output_root: Path | str,
    packet: Mapping[str, object],
) -> dict[str, str]:
    """Write ignored runtime artifacts for the no-submit sizing preview."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    preview = _mapping(packet.get("sizing_preview"))
    paths = {
        "sizing_preview_json": root / "sizing_preview.json",
        "sizing_preview_md": root / "sizing_preview.md",
        "operating_record": root / "operating_record.jsonl",
    }
    _write_json(paths["sizing_preview_json"], preview)
    paths["sizing_preview_md"].write_text(
        render_sizing_preview_markdown(packet) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    paths["operating_record"].write_text(
        json.dumps(
            _json_safe(
                {
                    "record_type": "crypto_qty_sizing_preview",
                    "schema_version": CRYPTO_QTY_SIZING_PREVIEW_SCHEMA_VERSION,
                    "as_of": packet.get("as_of", ""),
                    "sizing_status": preview.get("sizing_status", ""),
                    "selected_candidate_id": preview.get("selected_candidate_id", ""),
                    "selected_symbol": preview.get("selected_symbol", ""),
                    "blockers": preview.get("blockers", []),
                    "safety": packet.get("safety", {}),
                    "sizing_preview": preview,
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
        "schema_version": CRYPTO_QTY_SIZING_PREVIEW_SCHEMA_VERSION,
        "as_of": packet.get("as_of", ""),
        "artifact_root": str(root),
        "required_artifacts": {
            key: {"path": str(path), "sha256": _file_sha256(path)}
            for key, path in sorted(paths.items())
        },
        "input_artifacts": _input_artifact_manifest(packet.get("input_artifacts")),
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "network_access_attempted": False,
        "generated_under_runs": "runs" in root.parts,
        "labels": list(_string_sequence(_mapping(packet.get("safety")).get("labels"))),
        "profit_claim": "none",
    }
    _write_json(manifest_path, manifest)
    return {
        **{key: str(path) for key, path in paths.items()},
        "manifest": str(manifest_path),
    }


def render_sizing_preview_markdown(packet: Mapping[str, object]) -> str:
    """Render the operator-facing no-submit sizing preview."""

    preview = _mapping(packet.get("sizing_preview"))
    router = _mapping(packet.get("router_decision"))
    blockers = list(_string_sequence(preview.get("blockers")))
    min_notional = _first_text(preview, "broker_observed_min_notional")
    min_notional_status = "observed" if min_notional else "unobserved"
    return "\n".join(
        [
            "# Crypto Qty Sizing Preview",
            "",
            f"- selected candidate: `{preview.get('selected_candidate_id', '')}`",
            f"- selected symbol: `{preview.get('selected_symbol', '')}`",
            f"- selected strategy: `{preview.get('selected_strategy', '')}`",
            f"- selected backing: `{preview.get('selected_backing', '')}`",
            f"- router decision source: `{preview.get('router_decision_source', '')}`",
            f"- why selected by router: `{router.get('selection_reason', '')}`",
            f"- sizing basis: preview cap divided by latest local close, qty rounded down to broker-observed min_trade_increment",
            f"- latest price: `{preview.get('latest_price', '')}`",
            f"- preview cap: `{preview.get('preview_notional_cap', '')}`",
            f"- raw qty: `{preview.get('raw_qty', '')}`",
            f"- rounded qty: `{preview.get('rounded_qty', '')}`",
            f"- derived preview value: `{preview.get('derived_preview_value', '')}`",
            f"- min order size: `{preview.get('broker_observed_min_order_size', '')}`",
            f"- min trade increment: `{preview.get('broker_observed_min_trade_increment', '')}`",
            f"- min notional status: `{min_notional_status}`",
            f"- broker observed min notional: `{min_notional}`",
            f"- derived min order value estimate: `{preview.get('derived_min_order_value', '')}`",
            f"- sizing status: `{preview.get('sizing_status', '')}`",
            f"- blockers: `{', '.join(blockers) if blockers else 'none'}`",
            "- no-submit preview only: this packet does not authorize or perform paper submit, broker mutation, or live mutation.",
            "- broker acceptance: rounded qty is a deterministic preview estimate, not a guarantee of broker acceptance.",
            f"- next operator action: `{preview.get('next_operator_action', '')}`",
        ]
    )


def _selection_blockers(
    *,
    router_decision: Mapping[str, object],
    selected_candidate: Mapping[str, object],
    selected_backing: str,
    orderability_status: str,
    allow_fixture_backed: bool,
) -> tuple[str, ...]:
    blockers: list[str] = []
    decision = _first_text(router_decision, "decision")
    if decision == "no_trade":
        blockers.append("router_decision_no_trade")
    elif decision != "selected":
        blockers.append("router_decision_not_selected")
    if not selected_candidate:
        blockers.append("missing_selected_candidate")
        return _dedupe(blockers)
    if _first_text(selected_candidate, "asset_class") != "crypto":
        blockers.append("selected_candidate_not_crypto")
    if orderability_status not in CRYPTO_QTY_SIZING_PREVIEW_SAFE_ORDERABILITY_STATUSES:
        blockers.append("unsafe_orderability_status")
    if selected_backing == "fixture_backed" and not allow_fixture_backed:
        blockers.append("fixture_backed_candidate")
    if _first_text(selected_candidate, "freshness_status") == "stale_data":
        blockers.append("stale_candidate")
    history_status = _first_text(selected_candidate, "history_status")
    if history_status and history_status != "sufficient_history":
        blockers.append("insufficient_history")
    data_quality_status = _first_text(selected_candidate, "data_quality_status")
    if data_quality_status and data_quality_status != "valid":
        blockers.append("data_quality_blocked")
    if _first_text(selected_candidate, "blocker_status") == "blocked":
        blockers.append("candidate_blocked")
    candidate_blockers = set(_string_sequence(selected_candidate.get("blockers")))
    if "stale_data" in candidate_blockers:
        blockers.append("stale_candidate")
    if "insufficient_history" in candidate_blockers:
        blockers.append("insufficient_history")
    if "missing_data" in candidate_blockers or "missing_history" in candidate_blockers:
        blockers.append("data_quality_blocked")
    if any(
        blocker.startswith("metadata_")
        or blocker in {"metadata_missing", "metadata_partial", "not_orderable"}
        for blocker in candidate_blockers
    ):
        blockers.append("metadata_blocked")
    if any("safety" in blocker or "live" in blocker for blocker in candidate_blockers):
        blockers.append("safety_blocked")
    return _dedupe(blockers)


def _selected_candidate(
    router_decision: Mapping[str, object],
    opportunity_candidates: Mapping[str, object],
) -> Mapping[str, object]:
    selected_id = _first_text(router_decision, "selected_candidate_id")
    candidate = dict(_mapping(router_decision.get("selected_candidate")))
    if selected_id:
        for item in _mapping_sequence(opportunity_candidates.get("candidates")):
            if _first_text(item, "candidate_id") == selected_id:
                merged = dict(item)
                merged.update(candidate)
                return merged
    return candidate


def _selected_candidate_backing(
    *,
    router_decision: Mapping[str, object],
    candidate: Mapping[str, object],
    crypto_router_input_manifest: Mapping[str, object],
) -> str:
    explicit = _first_nonempty(
        _first_text(router_decision, "selected_candidate_backing"),
        _first_text(candidate, "candidate_backing"),
    )
    if explicit:
        return explicit
    labels = set(_string_sequence(candidate.get("labels"))) | set(
        _string_sequence(crypto_router_input_manifest.get("labels"))
    )
    source = _first_nonempty(
        _first_text(candidate, "source"),
        _first_text(crypto_router_input_manifest, "source_mode"),
    )
    if "fixture_backed" in labels or source == "offline_fixture":
        return "fixture_backed"
    if "real_local_artifact_backed" in labels or source == "local_replay":
        return "real_local_artifact_backed"
    if "paper_read_only" in labels or source == "paper_read_only":
        return "paper_read_only_artifact_backed"
    return "unknown"


def _preview_labels(
    *,
    selected_backing: str,
    orderability_status: str,
    crypto_router_input_manifest: Mapping[str, object],
) -> list[str]:
    labels: list[str] = list(CRYPTO_QTY_SIZING_PREVIEW_REQUIRED_LABELS)
    if orderability_status == "qty_orderable_notional_unobserved":
        labels.append("qty_orderable_notional_unobserved")
    if selected_backing == "paper_read_only_artifact_backed" or (
        _first_text(crypto_router_input_manifest, "source_mode") == "paper_read_only"
    ):
        labels.append("real_paper_read_backed")
    elif selected_backing == "real_local_artifact_backed":
        labels.append("real_local_artifact_backed")
    elif selected_backing == "fixture_backed":
        labels.append("fixture_backed")
    return list(_dedupe(labels))


def _latest_price(
    *,
    history_record: Mapping[str, object],
    history_manifest_source: Path,
    as_of: datetime,
) -> Decimal | None:
    direct = _optional_positive_decimal(
        _first_text(history_record, "latest_price", "latest_close", "close"),
        "latest_price",
    )
    if direct is not None:
        return direct
    data_path_text = _first_text(history_record, "data_path")
    if not data_path_text:
        return None
    data_path = _resolve_manifest_path(history_manifest_source, data_path_text)
    if not data_path.is_file():
        return None
    latest: tuple[datetime, Decimal] | None = None
    try:
        rows = csv.DictReader(data_path.read_text(encoding="utf-8-sig").splitlines())
    except OSError as exc:
        raise ValidationError(f"unable to read history CSV: {data_path}") from exc
    for row in rows:
        timestamp_text = _first_text(row, "timestamp", "datetime", "date", "t")
        close_text = _first_text(row, "close", "c")
        if not timestamp_text or not close_text:
            continue
        try:
            timestamp = _utc_datetime(timestamp_text, "timestamp")
            close = _positive_decimal(close_text, "close")
        except ValidationError:
            continue
        if timestamp > as_of:
            continue
        if latest is None or timestamp > latest[0]:
            latest = (timestamp, close)
    return None if latest is None else latest[1]


def _matching_symbol_record(
    records: object,
    symbol: str,
) -> Mapping[str, object]:
    normalized_symbol = _normalize_symbol(symbol)
    if not normalized_symbol:
        return {}
    for record in _mapping_sequence(records):
        record_symbol = _normalize_symbol(_first_text(record, "symbol"))
        if record_symbol == normalized_symbol:
            return record
    return {}


def _round_down_to_increment(value: Decimal, increment: Decimal) -> Decimal:
    steps = (value / increment).to_integral_value(rounding=ROUND_FLOOR)
    return steps * increment


def _input_artifact_manifest(value: object) -> dict[str, dict[str, str]]:
    artifacts: dict[str, dict[str, str]] = {}
    for name, path_text in sorted(_mapping(value).items()):
        path = Path(_required_string(str(path_text), "input_artifact_path"))
        artifacts[str(name)] = {
            "path": str(path),
            "sha256": _file_sha256(path) if path.is_file() else "",
        }
    return artifacts


def _next_operator_action(sizing_status: object) -> str:
    if sizing_status == "preview_ready":
        return "operator_review_sizing_preview_before_any_paper_submit_authorization"
    return "resolve_preview_blockers_then_rerun_router_or_refresh"


def _read_json_mapping(path: Path) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"unable to read JSON artifact: {path}") from exc
    if not isinstance(payload, Mapping):
        raise ValidationError(f"JSON artifact must contain an object: {path}")
    return payload


def _resolve_manifest_path(anchor_path: Path, value: object) -> Path:
    text = _required_string(_text(value), "manifest path")
    path = Path(text)
    if path.is_absolute():
        return path
    return anchor_path.parent / path


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


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mapping_sequence(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


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


def _first_nonempty(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


def _text(value: object) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "true" if value else "false"
    enum_value = getattr(value, "value", None)
    if type(enum_value) is str:
        return enum_value.strip()
    return str(value).strip()


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _normalize_symbol(value: object) -> str:
    return "".join(ch for ch in _text(value).upper() if ch.isalnum())


def _utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be a UTC ISO timestamp.") from exc
    else:
        raise ValidationError(f"{field_name} must be a timezone-aware UTC datetime.")
    if parsed.tzinfo is None:
        raise ValidationError(f"{field_name} must include timezone information.")
    try:
        return require_utc_datetime(parsed.astimezone(UTC))
    except ValidationError as exc:
        raise ValidationError(f"{field_name} must be a UTC datetime.") from exc


def _positive_decimal(value: object, field_name: str) -> Decimal:
    parsed = _decimal_value(value, field_name)
    if parsed <= Decimal("0"):
        raise ValidationError(f"{field_name} must be positive.")
    return parsed


def _optional_positive_decimal(value: object, field_name: str) -> Decimal | None:
    if not _text(value):
        return None
    try:
        return _positive_decimal(value, field_name)
    except ValidationError:
        return None


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
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic no-submit crypto qty sizing preview packet.",
    )
    parser.add_argument(
        "--router-decision",
        type=Path,
        default=CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_ROUTER_DECISION,
        help="Path to router_decision.json.",
    )
    parser.add_argument(
        "--opportunity-candidates",
        type=Path,
        default=CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_OPPORTUNITY_CANDIDATES,
        help="Path to opportunity_candidates.json.",
    )
    parser.add_argument(
        "--crypto-router-input-manifest",
        type=Path,
        default=CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_CRYPTO_ROUTER_INPUT_MANIFEST,
        help="Path to crypto_router_input_manifest.json.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_OUTPUT_ROOT,
        help="Output root for sizing preview artifacts.",
    )
    parser.add_argument(
        "--preview-notional-cap",
        default=str(CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_NOTIONAL_CAP),
        help="Paper-lab preview notional cap in USD.",
    )
    parser.add_argument(
        "--allow-fixture-backed",
        action="store_true",
        help="Allow fixture-backed selected candidates for explicit fixture tests.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=args.router_decision,
        opportunity_candidates_path=args.opportunity_candidates,
        crypto_router_input_manifest_path=args.crypto_router_input_manifest,
        output_root=args.output_root,
        preview_notional_cap=args.preview_notional_cap,
        allow_fixture_backed=args.allow_fixture_backed,
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(packet), sort_keys=True))
    else:
        preview = _mapping(packet.get("sizing_preview"))
        artifacts = _mapping(packet.get("artifact_paths"))
        print("crypto_qty_sizing_preview_status=" + _text(preview.get("sizing_status")))
        print("selected_candidate_id=" + _text(preview.get("selected_candidate_id")))
        print("selected_symbol=" + _text(preview.get("selected_symbol")))
        print("selected_backing=" + _text(preview.get("selected_backing")))
        print("latest_price=" + _text(preview.get("latest_price")))
        print("preview_notional_cap=" + _text(preview.get("preview_notional_cap")))
        print("raw_qty=" + _text(preview.get("raw_qty")))
        print("rounded_qty=" + _text(preview.get("rounded_qty")))
        print("derived_preview_value=" + _text(preview.get("derived_preview_value")))
        print("blockers=" + ",".join(_string_sequence(preview.get("blockers"))))
        print("paper_submit_authorized=false")
        print("paper_submit_performed=false")
        print("broker_mutation_performed=false")
        print("live_mutation_performed=false")
        print("artifact_sizing_preview_json=" + _text(artifacts.get("sizing_preview_json")))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
