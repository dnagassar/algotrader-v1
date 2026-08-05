"""Read-only SEC EDGAR adapter for delisting discovery.

Opens a fourth external destination in a repository that was deliberately
limited to two. The addition is recorded in the V6.02 design note and keeps the
architecture of the existing adapters:

- GET only, asserted rather than assumed;
- two allowlisted hosts, both SEC;
- **no credentials** — EDGAR is public and this module has no code path that can
  read an environment variable, dotenv, or credential store;
- SEC's fair-access policy requires a User-Agent carrying contact information,
  so one is mandatory and validated rather than optional;
- `dry_run` builds and records the exact request without opening a socket;
- every response is hashed into a receipt before use.

It cannot place an order, read an account, or touch a broker.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import gzip
import hashlib
import http.client
import json
from pathlib import Path

from algotrader.errors import ValidationError

__all__ = [
    "DESTINATION_ALLOWLIST",
    "EdgarRequestConfig",
    "build_edgar_request",
    "run_edgar_fetch",
]

ARCHIVE_HOST = "www.sec.gov"
DATA_HOST = "data.sec.gov"
DESTINATION_ALLOWLIST = (ARCHIVE_HOST, DATA_HOST)
_METHOD = "GET"
_APPROVED_KINDS = ("form_index", "submissions", "document")


@dataclass(frozen=True, slots=True)
class EdgarRequestConfig:
    """One bounded, read-only public EDGAR request."""

    kind: str
    user_agent: str
    output_root: Path | str
    year: int | None = None
    quarter: int | None = None
    cik: str | None = None
    path: str | None = None
    mode: str = "dry_run"
    live_fetch_authorized: bool = False

    def __post_init__(self) -> None:
        if self.kind not in _APPROVED_KINDS:
            raise ValidationError(f"kind is not approved: {self.kind}")
        # SEC fair access: a request without identifying contact information is
        # refused by policy, so it is refused here rather than sent and blocked.
        agent = str(self.user_agent).strip()
        if len(agent) < 10 or "@" not in agent:
            raise ValidationError(
                "SEC requires a User-Agent containing contact information."
            )
        object.__setattr__(self, "user_agent", agent)
        if self.mode not in ("dry_run", "live_fetch"):
            raise ValidationError(f"unsupported mode: {self.mode}")
        if self.mode == "live_fetch" and not self.live_fetch_authorized:
            raise ValidationError("live fetch requires explicit authorization.")
        if self.mode == "dry_run" and self.live_fetch_authorized:
            raise ValidationError("authorization flag requires live fetch mode.")
        if self.kind == "form_index":
            if self.year is None or self.quarter not in (1, 2, 3, 4):
                raise ValidationError("form_index requires year and quarter 1-4.")
        elif self.kind == "submissions":
            if not self.cik:
                raise ValidationError("submissions requires a CIK.")
            object.__setattr__(self, "cik", str(self.cik).strip().zfill(10))
        elif not self.path:
            raise ValidationError("document requires an archive path.")
        object.__setattr__(self, "output_root", Path(self.output_root))


def build_edgar_request(config: EdgarRequestConfig) -> dict[str, object]:
    """Build the exact request without performing any network access."""

    if config.kind == "form_index":
        host = ARCHIVE_HOST
        path = f"/Archives/edgar/full-index/{config.year}/QTR{config.quarter}/form.idx"
    elif config.kind == "submissions":
        host = DATA_HOST
        path = f"/submissions/CIK{config.cik}.json"
    else:
        host = ARCHIVE_HOST
        path = config.path if config.path.startswith("/") else f"/{config.path}"
        if ".." in path:
            raise ValidationError("archive path must not traverse directories.")
    if host not in DESTINATION_ALLOWLIST:
        raise ValidationError("destination host is not allowlisted.")
    return {
        "method": _METHOD,
        "scheme": "https",
        "destination_host": host,
        "destination_path": path,
        "destination_allowlist": list(DESTINATION_ALLOWLIST),
        "destination_allowlist_match": True,
        "url": f"https://{host}{path}",
        "kind": config.kind,
        "user_agent_supplied": True,
        "credentials_used": False,
        "authenticated": False,
    }


def run_edgar_fetch(
    config: EdgarRequestConfig,
    *,
    http_get: object | None = None,
) -> dict[str, object]:
    """Fetch one public EDGAR artifact, or plan it without touching the network."""

    request = build_edgar_request(config)
    root = Path(config.output_root)
    stem = _stem(config)
    receipt: dict[str, object] = {
        "record_type": "edgar_public_fetch_receipt",
        "schema_version": 1,
        "kind": config.kind,
        "mode": config.mode,
        "provider_request": request,
        "network_method_allowlist": [_METHOD],
        "network_destination_allowlist_enforced": True,
        "credential_access_attempted": False,
        "credential_values_exposed": False,
        "authenticated_request": False,
        "broker_access_attempted": False,
        "paper_submit_attempted": False,
        "live_authorized": False,
        "live_trading_performed": False,
        "recorded_at": datetime.now(UTC).isoformat(),
    }

    if config.mode == "dry_run":
        receipt.update(
            {
                "network_access_attempted": False,
                "refresh_state": "dry_run_request_plan_built",
                "byte_count": 0,
                "raw_response_path": "",
                "raw_response_sha256": "",
                "http_outcome_category": "not_attempted",
            }
        )
        _write_jsonl(root / f"{stem}_receipt.jsonl", receipt)
        return receipt

    payload = (http_get or _https_get)(
        request["destination_host"], request["destination_path"], config.user_agent
    )
    raw_path = root / f"{stem}.bin"
    _write_bytes(raw_path, payload)
    receipt.update(
        {
            "network_access_attempted": True,
            "refresh_state": "accepted_public_fetch",
            "byte_count": len(payload),
            "raw_response_path": str(raw_path),
            "raw_response_sha256": hashlib.sha256(payload).hexdigest(),
            "http_outcome_category": "success",
        }
    )
    _write_jsonl(root / f"{stem}_receipt.jsonl", receipt)
    return receipt


def _stem(config: EdgarRequestConfig) -> str:
    if config.kind == "form_index":
        return f"form_index_{config.year}_qtr{config.quarter}"
    if config.kind == "submissions":
        return f"submissions_{config.cik}"
    return "document_" + hashlib.sha256(
        str(config.path).encode()
    ).hexdigest()[:16]


def _https_get(host: str, path: str, user_agent: str, timeout: float = 60.0) -> bytes:
    if host not in DESTINATION_ALLOWLIST:
        raise ValidationError("destination host is not allowlisted.")
    connection = http.client.HTTPSConnection(host, timeout=timeout)
    try:
        connection.request(
            _METHOD,
            path,
            headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"},
        )
        response = connection.getresponse()
        body = response.read()
        if response.getheader("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        if response.status != 200:
            raise ValidationError(
                f"EDGAR request failed with status {response.status}."
            )
        return body
    finally:
        connection.close()


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _write_jsonl(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", required=True, choices=_APPROVED_KINDS)
    parser.add_argument("--user-agent", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--year", type=int)
    parser.add_argument("--quarter", type=int)
    parser.add_argument("--cik")
    parser.add_argument("--path")
    parser.add_argument("--mode", default="dry_run", choices=("dry_run", "live_fetch"))
    parser.add_argument("--live-fetch-authorized", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        receipt = run_edgar_fetch(
            EdgarRequestConfig(
                kind=args.kind,
                user_agent=args.user_agent,
                output_root=args.output_root,
                year=args.year,
                quarter=args.quarter,
                cik=args.cik,
                path=args.path,
                mode=args.mode,
                live_fetch_authorized=args.live_fetch_authorized,
            )
        )
    except (OSError, ValidationError, ValueError) as exc:
        print(f"edgar_fetch_status=blocked:{exc}")
        return 2
    print(f"edgar_fetch_status={receipt['refresh_state']}")
    print(f"bytes={receipt['byte_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
