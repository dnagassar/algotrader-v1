"""Full-history driver for the EDGAR delisting registry.

V6.02 proved the chain on one quarter by hand. This runs it across every
quarter EDGAR publishes, which is what turns a demonstration into a registry
and what makes a recovery rate measurable rather than anecdotal.

Two stages, run and resumed independently:

- **Stage A** enumerates every Form 25 / 25-NSE filing from the quarterly
  `form.idx` files. One request per quarter, no per-company cost.
- **Stage B** resolves a trading symbol for each delisting episode:
  `submissions` -> the last periodic report filed at or before the delisting ->
  that document's cover-page inline XBRL.

Everything network-facing goes through `edgar_delisting_adapter.edgar_get`, so
the GET-only, two-SEC-hosts, no-credentials guarantees hold in one place. This
module has no code path that can read an environment variable, dotenv, or
credential store.

Operating notes that are properties of the code, not conventions:

- Requests are paced below SEC's fair-access ceiling by a monotonic clock.
- Both stages append JSONL and skip work already recorded, so an interrupted
  run resumes without refetching.
- `form.idx` is ~50 MB per quarter and the documents run to tens of MB. Neither
  is retained: each payload is hashed into the manifest, parsed, and dropped.
  The manifest carries the sha256, so what was fetched stays auditable.
- `dry_run` performs zero network access and plans the request set instead.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path
import time

from algotrader.errors import ValidationError
from algotrader.execution.edgar_delisting_adapter import (
    EdgarRequestConfig,
    build_edgar_request,
    edgar_get,
)
from algotrader.research.delisting_registry import (
    RECOVERY_STRATA,
    TICKER_TAGGING_ERA_START,
    DelistingEpisode,
    DelistingFiling,
    build_delisting_records,
    extract_trading_symbols,
    group_delisting_episodes,
    parse_form_index,
    price_admission_window,
    select_symbol_source_filing,
    summarize_symbol_recovery,
    symbol_from_document_name,
)

__all__ = [
    "EDGAR_FULL_INDEX_FIRST_QUARTER",
    "DelistingPipelineConfig",
    "export_registry",
    "load_stage_a_filings",
    "quarters_in_range",
    "run_stage_a",
    "run_stage_b",
    "summarize_stage_b",
]

# EDGAR's quarterly full-index archive begins here; earlier filings were paper.
EDGAR_FULL_INDEX_FIRST_QUARTER = (1993, 1)
# SEC fair access permits ten requests a second. Six leaves headroom, because
# being throttled mid-run is worse than finishing slightly later.
_DEFAULT_REQUEST_INTERVAL_SECONDS = 1.0 / 6.0

_STAGE_A_FILINGS = "stage_a_filings.jsonl"
_STAGE_A_QUARTERS = "stage_a_quarters.jsonl"
_STAGE_B_RESOLUTIONS = "stage_b_resolutions.jsonl"
_STAGE_B_MANIFEST = "stage_b_manifest.jsonl"
_REGISTRY = "delisting_registry.jsonl"

_OUTCOME_RESOLVED = "resolved"
_OUTCOME_NO_TAG = "no_tag_in_source_filing"
_OUTCOME_NO_REPORT = "no_eligible_periodic_report"
_OUTCOME_WINDOW = "submissions_window_insufficient"
_OUTCOME_NO_PRIMARY_DOCUMENT = "source_filing_has_no_primary_document"
_OUTCOME_SUBMISSIONS_FAILED = "submissions_unavailable"
_OUTCOME_DOCUMENT_FAILED = "document_unavailable"


@dataclass(frozen=True, slots=True)
class DelistingPipelineConfig:
    """One full-history run of the delisting registry."""

    user_agent: str
    output_root: Path | str
    mode: str = "dry_run"
    live_fetch_authorized: bool = False
    start_quarter: tuple[int, int] = EDGAR_FULL_INDEX_FIRST_QUARTER
    end_quarter: tuple[int, int] | None = None
    # Cover-page tagging phased in from 2019, so earlier episodes are recorded
    # by stage A and deliberately not fetched by stage B.
    resolve_from: date = TICKER_TAGGING_ERA_START
    max_resolutions: int = 0
    request_interval_seconds: float = _DEFAULT_REQUEST_INTERVAL_SECONDS

    def __post_init__(self) -> None:
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
        if self.request_interval_seconds < 0.1:
            raise ValidationError(
                "request interval must respect SEC fair access (>= 0.1s)."
            )
        object.__setattr__(self, "output_root", Path(self.output_root))


@dataclass
class _Pacer:
    """Holds requests below the fair-access ceiling using a monotonic clock."""

    interval: float
    _last: float = field(default=0.0)

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last
        if self._last and elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self._last = time.monotonic()


def quarters_in_range(
    start: tuple[int, int],
    end: tuple[int, int],
) -> tuple[tuple[int, int], ...]:
    """Every (year, quarter) from `start` through `end`, inclusive."""

    for label, value in (("start", start), ("end", end)):
        if value[1] not in (1, 2, 3, 4):
            raise ValidationError(f"{label} quarter must be 1-4.")
    if start > end:
        raise ValidationError("start quarter must not follow end quarter.")
    quarters: list[tuple[int, int]] = []
    year, quarter = start
    while (year, quarter) <= end:
        quarters.append((year, quarter))
        year, quarter = (year + 1, 1) if quarter == 4 else (year, quarter + 1)
    return tuple(quarters)


def current_quarter(today: date) -> tuple[int, int]:
    return today.year, (today.month - 1) // 3 + 1


# --- stage A ---------------------------------------------------------------


def run_stage_a(
    config: DelistingPipelineConfig,
    *,
    http_get: Callable[[str, str, str], bytes] | None = None,
    today: date | None = None,
) -> dict[str, object]:
    """Enumerate every Form 25 / 25-NSE filing across the requested quarters."""

    root = Path(config.output_root)
    end = config.end_quarter or current_quarter(today or datetime.now(UTC).date())
    quarters = quarters_in_range(config.start_quarter, end)
    done = {
        (int(row["year"]), int(row["quarter"]))
        for row in _read_jsonl(root / _STAGE_A_QUARTERS)
    }
    pending = [quarter for quarter in quarters if quarter not in done]

    if config.mode == "dry_run":
        return {
            "record_type": "delisting_stage_a_summary",
            "mode": "dry_run",
            "network_access_attempted": False,
            "quarters_in_range": len(quarters),
            "quarters_already_recorded": len(quarters) - len(pending),
            "quarters_to_fetch": len(pending),
            "planned_requests": [
                build_edgar_request(_index_config(config, year, quarter))["url"]
                for year, quarter in pending
            ],
        }

    fetch = http_get or edgar_get
    pacer = _Pacer(config.request_interval_seconds)
    filings_written = 0
    failures: list[dict[str, object]] = []
    for year, quarter in pending:
        request = build_edgar_request(_index_config(config, year, quarter))
        pacer.wait()
        try:
            payload = fetch(
                request["destination_host"], request["destination_path"], config.user_agent
            )
        except (OSError, ValidationError) as exc:
            failures.append({"year": year, "quarter": quarter, "error": str(exc)})
            continue
        filings = parse_form_index(payload)
        for filing in filings:
            _append_jsonl(
                root / _STAGE_A_FILINGS,
                {
                    "form_type": filing.form_type,
                    "company": filing.company,
                    "cik": filing.cik,
                    "filed": filing.filed.isoformat(),
                    "archive_path": filing.archive_path,
                    "source_year": year,
                    "source_quarter": quarter,
                },
            )
        filings_written += len(filings)
        # Written last, so an interruption mid-quarter re-fetches that quarter
        # rather than recording it as complete with partial rows.
        _append_jsonl(
            root / _STAGE_A_QUARTERS,
            {
                "year": year,
                "quarter": quarter,
                "url": request["url"],
                "byte_count": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "delisting_filings": len(filings),
                "raw_response_retained": False,
                "fetched_at": datetime.now(UTC).isoformat(),
            },
        )
    return {
        "record_type": "delisting_stage_a_summary",
        "mode": "live_fetch",
        "network_access_attempted": True,
        "quarters_in_range": len(quarters),
        "quarters_fetched": len(pending) - len(failures),
        "quarters_failed": len(failures),
        "failures": failures,
        "delisting_filings_written": filings_written,
        "filings_path": str(root / _STAGE_A_FILINGS),
    }


def _index_config(
    config: DelistingPipelineConfig, year: int, quarter: int
) -> EdgarRequestConfig:
    return EdgarRequestConfig(
        kind="form_index",
        user_agent=config.user_agent,
        output_root=config.output_root,
        year=year,
        quarter=quarter,
    )


def load_stage_a_filings(root: Path | str) -> tuple[DelistingFiling, ...]:
    """Re-read stage A output, deduplicated.

    A quarter refetched after an interruption can repeat rows, and a filing can
    legitimately appear in the index twice, so identity is the whole row.
    """

    seen: set[tuple[str, str, str, str]] = set()
    filings: list[DelistingFiling] = []
    for row in _read_jsonl(Path(root) / _STAGE_A_FILINGS):
        key = (
            str(row["cik"]),
            str(row["form_type"]),
            str(row["filed"]),
            str(row["archive_path"]),
        )
        if key in seen:
            continue
        seen.add(key)
        filings.append(
            DelistingFiling(
                form_type=str(row["form_type"]),
                company=str(row["company"]),
                cik=str(row["cik"]),
                filed=date.fromisoformat(str(row["filed"])),
                archive_path=str(row["archive_path"]),
            )
        )
    return tuple(filings)


# --- stage B ---------------------------------------------------------------


def run_stage_b(
    config: DelistingPipelineConfig,
    *,
    http_get: Callable[[str, str, str], bytes] | None = None,
) -> dict[str, object]:
    """Resolve trading symbols for delisting episodes inside the tagging era."""

    root = Path(config.output_root)
    episodes = group_delisting_episodes(load_stage_a_filings(root))
    eligible = [
        episode for episode in episodes if episode.delisted_on >= config.resolve_from
    ]
    resolved_keys = {
        (str(row["cik"]), str(row["delisted_on"]))
        for row in _read_jsonl(root / _STAGE_B_RESOLUTIONS)
    }
    unresolved = [
        episode
        for episode in eligible
        if (episode.cik, episode.delisted_on.isoformat()) not in resolved_keys
    ]
    pending = (
        unresolved[: config.max_resolutions]
        if config.max_resolutions > 0
        else unresolved
    )

    if config.mode == "dry_run":
        return {
            "record_type": "delisting_stage_b_summary",
            "mode": "dry_run",
            "network_access_attempted": False,
            "episodes_total": len(episodes),
            "episodes_in_tagging_era": len(eligible),
            "episodes_already_resolved": len(eligible) - len(unresolved),
            "episodes_to_resolve": len(pending),
        }

    fetch = http_get or edgar_get
    pacer = _Pacer(config.request_interval_seconds)
    counts: dict[str, int] = {}
    for episode in pending:
        row = _resolve_episode(config, episode, fetch=fetch, pacer=pacer, root=root)
        counts[str(row["outcome"])] = counts.get(str(row["outcome"]), 0) + 1
        _append_jsonl(root / _STAGE_B_RESOLUTIONS, row)
    return {
        "record_type": "delisting_stage_b_summary",
        "mode": "live_fetch",
        "network_access_attempted": True,
        "episodes_total": len(episodes),
        "episodes_in_tagging_era": len(eligible),
        "episodes_attempted": len(pending),
        "outcomes": dict(sorted(counts.items())),
        "resolutions_path": str(root / _STAGE_B_RESOLUTIONS),
    }


def _resolve_episode(
    config: DelistingPipelineConfig,
    episode: DelistingEpisode,
    *,
    fetch: Callable[[str, str, str], bytes],
    pacer: _Pacer,
    root: Path,
) -> dict[str, object]:
    row: dict[str, object] = {
        "cik": episode.cik,
        "company": episode.company,
        "delisted_on": episode.delisted_on.isoformat(),
        "last_filed_on": episode.last_filed_on.isoformat(),
        "delisting_filing_count": episode.filing_count,
        "era": (
            "tagging_era"
            if episode.delisted_on >= TICKER_TAGGING_ERA_START
            else "pre_tagging_era"
        ),
        "entity_type": "",
        "sic_description": "",
        "source_form": "",
        "source_filed": "",
        "source_document": "",
        "symbols": [],
        "exchange": "",
        "document_name_symbol": "",
        "ticker_recoverable": False,
        "resolved_at": datetime.now(UTC).isoformat(),
    }

    submissions_request = build_edgar_request(
        EdgarRequestConfig(
            kind="submissions",
            user_agent=config.user_agent,
            output_root=config.output_root,
            cik=episode.cik,
        )
    )
    pacer.wait()
    try:
        payload = fetch(
            submissions_request["destination_host"],
            submissions_request["destination_path"],
            config.user_agent,
        )
    except (OSError, ValidationError) as exc:
        row["outcome"] = _OUTCOME_SUBMISSIONS_FAILED
        row["error"] = str(exc)
        return row
    _record_request(root, submissions_request, payload, episode.cik)

    try:
        submissions = json.loads(payload)
    except json.JSONDecodeError as exc:
        row["outcome"] = _OUTCOME_SUBMISSIONS_FAILED
        row["error"] = f"unparseable submissions payload: {exc}"
        return row

    row["entity_type"] = str(submissions.get("entityType", ""))
    row["sic_description"] = str(submissions.get("sicDescription", ""))
    filings, window_reaches_delisting = _recent_filings(submissions, episode.delisted_on)
    chosen = select_symbol_source_filing(filings, delisted_on=episode.delisted_on)
    if chosen is None:
        row["outcome"] = (
            _OUTCOME_NO_REPORT if window_reaches_delisting else _OUTCOME_WINDOW
        )
        return row

    row["source_form"] = str(chosen["form"])
    row["source_filed"] = str(chosen["filed"])
    row["source_document"] = str(chosen["primary"])
    if not str(chosen["primary"]).strip():
        # Older filings carry no primary document in the index. There is
        # nothing to fetch, so say that rather than spending a request on a 404.
        row["outcome"] = _OUTCOME_NO_PRIMARY_DOCUMENT
        return row
    document_path = (
        f"/Archives/edgar/data/{int(episode.cik)}/"
        f"{str(chosen['accession']).replace('-', '')}/{chosen['primary']}"
    )
    document_request = build_edgar_request(
        EdgarRequestConfig(
            kind="document",
            user_agent=config.user_agent,
            output_root=config.output_root,
            path=document_path,
        )
    )
    pacer.wait()
    try:
        document = fetch(
            document_request["destination_host"],
            document_request["destination_path"],
            config.user_agent,
        )
    except (OSError, ValidationError) as exc:
        row["outcome"] = _OUTCOME_DOCUMENT_FAILED
        row["error"] = str(exc)
        return row
    _record_request(root, document_request, document, episode.cik)

    symbols, exchange = extract_trading_symbols(document)
    row["symbols"] = list(symbols)
    row["exchange"] = exchange
    row["document_name_symbol"] = symbol_from_document_name(str(chosen["primary"]))
    row["ticker_recoverable"] = bool(symbols)
    row["outcome"] = _OUTCOME_RESOLVED if symbols else _OUTCOME_NO_TAG
    return row


def _recent_filings(
    submissions: Mapping[str, object],
    delisted_on: date,
) -> tuple[list[dict[str, object]], bool]:
    """The `recent` filing window, and whether it reaches past the delisting.

    EDGAR caps `recent` at a thousand filings and pages the rest. If that
    window starts after the delisting we cannot see the report we need, which
    is a different answer from "no such report exists" and is recorded as one.
    """

    recent = submissions.get("filings", {})
    recent = recent.get("recent", {}) if isinstance(recent, Mapping) else {}
    forms = list(recent.get("form", []))
    dates = list(recent.get("filingDate", []))
    accessions = list(recent.get("accessionNumber", []))
    primaries = list(recent.get("primaryDocument", []))
    filings: list[dict[str, object]] = []
    for form, filed, accession, primary in zip(
        forms, dates, accessions, primaries, strict=False
    ):
        try:
            filed_on = date.fromisoformat(str(filed))
        except ValueError:
            continue
        filings.append(
            {
                "form": str(form),
                "filed": filed_on,
                "accession": str(accession),
                "primary": str(primary),
            }
        )
    if not filings:
        return filings, True
    oldest = min(item["filed"] for item in filings)
    return filings, oldest <= delisted_on


def _record_request(
    root: Path, request: Mapping[str, object], payload: bytes, cik: str
) -> None:
    _append_jsonl(
        root / _STAGE_B_MANIFEST,
        {
            "record_type": "edgar_public_fetch_receipt",
            "cik": cik,
            "kind": request["kind"],
            "method": request["method"],
            "url": request["url"],
            "destination_host": request["destination_host"],
            "destination_allowlist_match": request["destination_allowlist_match"],
            "credentials_used": False,
            "authenticated": False,
            "byte_count": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "raw_response_retained": False,
            "fetched_at": datetime.now(UTC).isoformat(),
        },
    )


def export_registry(root: Path | str) -> dict[str, object]:
    """Write the consolidated registry: one record per delisting episode.

    This is the artifact the rest of the program consumes. Every record carries
    the window in which a price series for its ticker can be trusted — through
    the delisting, never after — because a symbol observed after that date
    belongs to whoever holds it now.

    Episodes with no recovered symbol are written too. A delisting nobody can
    name is still a delisting, and dropping it would rebuild the survivorship
    bias this exists to reduce.
    """

    root = Path(root)
    resolved = {
        (str(row["cik"]), str(row["delisted_on"])): row
        for row in _read_jsonl(root / _STAGE_B_RESOLUTIONS)
    }
    episodes = group_delisting_episodes(load_stage_a_filings(root))
    resolutions = []
    for episode in episodes:
        row = resolved.get((episode.cik, episode.delisted_on.isoformat()), {})
        resolutions.append(
            {
                "cik": episode.cik,
                "company": episode.company,
                "delisted_on": episode.delisted_on,
                "symbols": tuple(row.get("symbols", ())),
                "exchange": str(row.get("exchange", "")),
                "symbol_source": "cover_page_xbrl" if row.get("symbols") else "none",
            }
        )
    records = build_delisting_records(resolutions)
    outcomes = {
        (str(row["cik"]), str(row["delisted_on"])): str(row.get("outcome", ""))
        for row in _read_jsonl(root / _STAGE_B_RESOLUTIONS)
    }
    path = root / _REGISTRY
    if path.exists():
        path.unlink()
    for record in records:
        payload = record.as_payload()
        payload["price_admission_window"] = price_admission_window(record)
        payload["outcome"] = outcomes.get(
            (record.cik, record.delisted_on.isoformat()), "not_attempted"
        )
        _append_jsonl(path, payload)
    return {
        "record_type": "delisting_registry_export",
        "records": len(records),
        "records_with_symbols": sum(1 for r in records if r.ticker_recoverable),
        "distinct_symbols": len({s for r in records for s in r.symbols}),
        "registry_path": str(path),
    }


def summarize_stage_b(root: Path | str) -> dict[str, object]:
    """Recovery counts over whatever stage B has recorded so far.

    Stratified by the **source filing's** year as well as the delisting's,
    because that is where the cover-page tagging boundary actually falls: a
    company delisting in early 2019 is described by a report filed in 2018,
    which predates the mandate entirely. Stratifying only on the delisting date
    reads that as a coverage failure.
    """

    rows = [
        dict(row, source_filed_year=str(row.get("source_filed", ""))[:4] or "none")
        for row in _read_jsonl(Path(root) / _STAGE_B_RESOLUTIONS)
    ]
    summary = summarize_symbol_recovery(
        rows, strata=(*RECOVERY_STRATA, "source_filed_year")
    )
    summary["distinct_symbols"] = len(
        {symbol for row in rows for symbol in row.get("symbols", [])}
    )
    return summary


# --- storage ---------------------------------------------------------------


def _append_jsonl(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")


def _read_jsonl(path: Path) -> Iterator[dict[str, object]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


# --- command line ----------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", required=True, choices=("a", "b", "summary", "export")
    )
    parser.add_argument("--user-agent", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--mode", default="dry_run", choices=("dry_run", "live_fetch"))
    parser.add_argument("--live-fetch-authorized", action="store_true")
    parser.add_argument("--start-year", type=int, default=EDGAR_FULL_INDEX_FIRST_QUARTER[0])
    parser.add_argument("--start-quarter", type=int, default=EDGAR_FULL_INDEX_FIRST_QUARTER[1])
    parser.add_argument("--end-year", type=int)
    parser.add_argument("--end-quarter", type=int)
    parser.add_argument("--resolve-from", default=TICKER_TAGGING_ERA_START.isoformat())
    parser.add_argument("--max-resolutions", type=int, default=0)
    parser.add_argument(
        "--request-interval-seconds",
        type=float,
        default=_DEFAULT_REQUEST_INTERVAL_SECONDS,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.stage in ("summary", "export"):
            result = (
                summarize_stage_b(args.output_root)
                if args.stage == "summary"
                else export_registry(args.output_root)
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        config = DelistingPipelineConfig(
            user_agent=args.user_agent,
            output_root=args.output_root,
            mode=args.mode,
            live_fetch_authorized=args.live_fetch_authorized,
            start_quarter=(args.start_year, args.start_quarter),
            end_quarter=(
                (args.end_year, args.end_quarter)
                if args.end_year and args.end_quarter
                else None
            ),
            resolve_from=date.fromisoformat(args.resolve_from),
            max_resolutions=args.max_resolutions,
            request_interval_seconds=args.request_interval_seconds,
        )
        summary = run_stage_a(config) if args.stage == "a" else run_stage_b(config)
    except (OSError, ValidationError, ValueError) as exc:
        print(f"delisting_pipeline_status=blocked:{exc}")
        return 2
    print(f"delisting_pipeline_status=completed_stage_{args.stage}")
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
