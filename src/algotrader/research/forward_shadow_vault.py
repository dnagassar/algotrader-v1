"""Vault eligibility: prove a symbol has never been acquired in this repository.

Contamination is a property of what the analyst has seen, not of the calendar.
A market this repository has never requested is, for our own selection bias,
equivalent to data that has not happened yet — and unlike future data it is
available immediately.

That claim is only worth anything if it can be checked rather than asserted.
Every acquisition in this repository leaves a receipt, so the set of symbols we
have ever touched is enumerable. This module enumerates it and refuses any
symbol with evidence against it.

The scan is deliberately over-inclusive. A false "already acquired" costs one
discarded candidate; a false "never acquired" silently readmits the bias the
vault exists to exclude. Ties therefore go to exclusion.

What this proves: no acquisition receipt, canonical artifact, or data manifest
in this repository references the symbol. What it cannot prove: that no human
ever looked at a chart elsewhere. That limit is real and is stated in the
report rather than hidden.

This module is local and research-only. It cannot load credentials, reach a
network or broker, mutate a paper account, or authorize live capital.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import re

from algotrader.errors import ValidationError

__all__ = [
    "SymbolAcquisitionEvidence",
    "VAULT_SCAN_VERSION",
    "assert_vault_eligible",
    "build_vault_eligibility_report",
    "main",
    "scan_acquired_symbols",
]

VAULT_SCAN_VERSION = "v5_90_forward_shadow_vault_scan_v1"

_SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,14}$")
_CANONICAL_CSV_PATTERN = re.compile(
    r"^(?P<symbol>[a-z0-9\-]+)_daily_.*canonical\.csv$"
)
_RAW_RESPONSE_PATTERN = re.compile(r"^(?P<symbol>[a-z0-9\-]+)_raw_[a-z0-9]+\.json$")
_NORMALIZED_PATTERN = re.compile(r"^(?P<symbol>[a-z0-9\-]+)_normalized\.csv$")
_REFRESH_LOG_PATTERN = re.compile(r"^(?P<symbol>[a-z0-9\-]+)_refresh_manifest\.jsonl$")

_MANIFEST_SYMBOL_KEYS = (
    "symbols",
    "valid_symbols",
    "blocked_symbols",
    "candidate_symbols",
    "baseline_symbols",
    "canary_symbols",
)


@dataclass(frozen=True, slots=True)
class SymbolAcquisitionEvidence:
    """One concrete reason a symbol is not vault eligible."""

    symbol: str
    evidence_kind: str
    evidence_path: str

    def as_payload(self) -> dict[str, str]:
        return {
            "symbol": self.symbol,
            "evidence_kind": self.evidence_kind,
            "evidence_path": self.evidence_path,
        }


def scan_acquired_symbols(
    repo_root: Path | str = Path("."),
    *,
    runs_subdirectory: str = "runs",
) -> dict[str, tuple[SymbolAcquisitionEvidence, ...]]:
    """Enumerate every symbol with acquisition evidence in this repository."""

    root = Path(repo_root)
    runs = root / runs_subdirectory
    found: dict[str, list[SymbolAcquisitionEvidence]] = {}

    def record(symbol: object, kind: str, path: Path) -> None:
        normalized = _normalize(symbol)
        if normalized is None:
            return
        try:
            display = str(path.relative_to(root))
        except ValueError:
            display = str(path)
        found.setdefault(normalized, []).append(
            SymbolAcquisitionEvidence(normalized, kind, display)
        )

    if not runs.is_dir():
        return {}

    for path in runs.rglob("*"):
        if not path.is_file():
            continue
        name = path.name

        for pattern, kind in (
            (_CANONICAL_CSV_PATTERN, "canonical_artifact_filename"),
            (_RAW_RESPONSE_PATTERN, "raw_provider_response_filename"),
            (_NORMALIZED_PATTERN, "normalized_artifact_filename"),
            (_REFRESH_LOG_PATTERN, "refresh_log_filename"),
        ):
            match = pattern.match(name)
            if match:
                record(match.group("symbol").upper(), kind, path)
                break

        if name.endswith("_refresh_manifest.jsonl"):
            for line in _read_lines(path):
                payload = _load_json_text(line)
                if isinstance(payload, Mapping):
                    record(payload.get("symbol"), "refresh_receipt_symbol", path)
        elif name.endswith("manifest.json") or name.endswith("_manifest.json"):
            payload = _load_json_text(_read_text(path))
            if isinstance(payload, Mapping):
                _record_manifest_symbols(payload, path, record)

    return {
        symbol: tuple(evidence) for symbol, evidence in sorted(found.items())
    }


def build_vault_eligibility_report(
    symbols: Sequence[str],
    *,
    repo_root: Path | str = Path("."),
) -> dict[str, object]:
    """Report per-symbol vault eligibility without raising."""

    requested = _validated_symbols(symbols)
    acquired = scan_acquired_symbols(repo_root)
    rows: list[dict[str, object]] = []
    eligible: list[str] = []
    ineligible: list[str] = []
    for symbol in requested:
        evidence = acquired.get(symbol, ())
        if evidence:
            ineligible.append(symbol)
        else:
            eligible.append(symbol)
        rows.append(
            {
                "symbol": symbol,
                "vault_eligible": not evidence,
                "evidence_count": len(evidence),
                "evidence": [item.as_payload() for item in evidence[:5]],
            }
        )
    return {
        "record_type": "forward_shadow_vault_eligibility_report",
        "scan_version": VAULT_SCAN_VERSION,
        "requested_symbols": list(requested),
        "vault_eligible_symbols": eligible,
        "ineligible_symbols": ineligible,
        "all_requested_symbols_eligible": not ineligible,
        "distinct_acquired_symbols_in_repository": len(acquired),
        "symbol_reports": rows,
        "proves": (
            "no acquisition receipt, canonical artifact, or data manifest in "
            "this repository references the symbol"
        ),
        "does_not_prove": (
            "that no person ever inspected this market outside this repository, "
            "nor that a published rule's author was blind to it"
        ),
        "safety": {
            "network_access_performed": False,
            "credential_access_performed": False,
            "broker_access_performed": False,
            "paper_mutation_performed": False,
            "live_authorized": False,
        },
    }


def assert_vault_eligible(
    symbols: Sequence[str],
    *,
    repo_root: Path | str = Path("."),
) -> dict[str, object]:
    """Return the eligibility report, or fail closed if any symbol was touched."""

    report = build_vault_eligibility_report(symbols, repo_root=repo_root)
    if not report["all_requested_symbols_eligible"]:
        offenders = ", ".join(str(item) for item in report["ineligible_symbols"])
        raise ValidationError(
            "vault eligibility refused: this repository has already acquired "
            f"{offenders}; those symbols carry our own selection history."
        )
    return report


def _record_manifest_symbols(
    payload: Mapping[str, object],
    path: Path,
    record,
) -> None:
    for key in _MANIFEST_SYMBOL_KEYS:
        value = payload.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for item in value:
                record(item, f"data_manifest_{key}", path)
    mapping = payload.get("provider_symbol_map")
    if isinstance(mapping, Mapping):
        for key, value in mapping.items():
            record(key, "data_manifest_provider_symbol_map", path)
            record(value, "data_manifest_provider_symbol_map", path)
    rows = payload.get("symbol_data")
    if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)):
        for row in rows:
            if isinstance(row, Mapping):
                record(row.get("symbol"), "data_manifest_symbol_data", path)
                record(row.get("provider_symbol"), "data_manifest_symbol_data", path)
    record(payload.get("symbol"), "data_manifest_symbol", path)


def _normalize(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().upper()
    if not text or not _SYMBOL_PATTERN.match(text):
        return None
    return text


def _validated_symbols(symbols: Sequence[str]) -> tuple[str, ...]:
    if isinstance(symbols, (str, bytes)) or not isinstance(symbols, Iterable):
        raise ValidationError("symbols must be a sequence of tickers.")
    resolved: list[str] = []
    for item in symbols:
        normalized = _normalize(item)
        if normalized is None:
            raise ValidationError(f"invalid symbol: {item!r}")
        if normalized not in resolved:
            resolved.append(normalized)
    if not resolved:
        raise ValidationError("at least one symbol is required.")
    return tuple(resolved)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _read_lines(path: Path) -> list[str]:
    return [line for line in _read_text(path).splitlines() if line.strip()]


def _load_json_text(text: str) -> object:
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forward-shadow-vault",
        description=(
            "Check whether symbols have ever been acquired in this repository."
        ),
    )
    parser.add_argument("--symbol", action="append", default=[], required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = build_vault_eligibility_report(
            args.symbol, repo_root=args.repo_root
        )
    except (OSError, ValidationError) as exc:
        print(f"forward_shadow_vault_status=blocked:{exc}")
        return 2
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    else:
        print("# Forward-shadow vault eligibility")
        print("")
        for row in report["symbol_reports"]:
            state = "ELIGIBLE" if row["vault_eligible"] else "ALREADY ACQUIRED"
            print(f"- {row['symbol']}: {state} ({row['evidence_count']} evidence)")
            for item in row["evidence"]:
                print(f"    - {item['evidence_kind']}: {item['evidence_path']}")
        print("")
        print(f"- Proves: {report['proves']}")
        print(f"- Does not prove: {report['does_not_prove']}")
    return 0 if report["all_requested_symbols_eligible"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
