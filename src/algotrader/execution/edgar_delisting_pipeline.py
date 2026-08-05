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
    ARCHIVE_HOST,
    DATA_HOST,
    EdgarRequestConfig,
    build_edgar_request,
    edgar_get,
)
from algotrader.research.delisting_registry import (
    DELISTING_FORMS,
    RECOVERY_STRATA,
    TICKER_TAGGING_ERA_START,
    DelistingEpisode,
    DelistingFiling,
    FundSeries,
    attribute_delisted_symbols,
    build_delisting_records,
    extract_cover_page_classes,
    extract_trading_symbols,
    group_delisting_episodes,
    parse_filing_header_series,
    parse_form25_security,
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
    "run_stage_c",
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
_STAGE_C_ATTRIBUTIONS = "stage_c_attributions.jsonl"
_REGISTRY = "delisting_registry.jsonl"

_OUTCOME_RESOLVED = "resolved"
_OUTCOME_NO_TAG = "no_tag_in_source_filing"
_OUTCOME_NO_REPORT = "no_eligible_periodic_report"
_OUTCOME_WINDOW = "submissions_window_insufficient"
_OUTCOME_NO_PRIMARY_DOCUMENT = "source_filing_has_no_primary_document"
# Fund filings whose SGML header carries SERIES-AND-CLASSES-CONTRACTS-DATA.
_SERIES_BEARING_FORMS = frozenset(
    {
        "497", "497K", "497J", "485BPOS", "485APOS", "485BXT",
        "NPORT-P", "NPORT-EX", "N-CEN", "N-CSR", "N-CSRS", "N-Q", "N-PX",
        "24F-2NT", "N-MFP", "N-MFP2", "N-MFP3",
    }
)
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
    # Stage C only. Funds and operating companies resolve through different
    # sources, and the fund half is what an ETF universe needs.
    entity_scope: str = "all"
    max_header_scans: int = 8

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
        if self.entity_scope not in ("all", "investment", "non_investment"):
            raise ValidationError(f"unsupported entity scope: {self.entity_scope}")
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


def _filing_columns(
    submissions: Mapping[str, object],
) -> tuple[list[str], list[str], list[str]]:
    filings = submissions.get("filings", {})
    recent = filings.get("recent", {}) if isinstance(filings, Mapping) else {}
    if not isinstance(recent, Mapping):
        return [], [], []
    return (
        [str(value) for value in recent.get("form", [])],
        [str(value) for value in recent.get("filingDate", [])],
        [str(value) for value in recent.get("accessionNumber", [])],
    )


def _window_reaches(dates: Sequence[str], delisted_on: date) -> bool:
    parsed = []
    for value in dates:
        try:
            parsed.append(date.fromisoformat(value))
        except ValueError:
            continue
    return bool(parsed) and min(parsed) <= delisted_on


def _older_submission_pages(submissions: Mapping[str, object]) -> list[str]:
    filings = submissions.get("filings", {})
    files = filings.get("files", []) if isinstance(filings, Mapping) else []
    names = []
    for entry in files if isinstance(files, list) else []:
        if isinstance(entry, Mapping) and entry.get("name"):
            names.append(str(entry["name"]))
    return names


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


# --- stage C: exact per-security attribution -------------------------------


def run_stage_c(
    config: DelistingPipelineConfig,
    *,
    http_get: Callable[[str, str, str], bytes] | None = None,
) -> dict[str, object]:
    """Attribute each delisting to the security that actually delisted.

    Stage B answered "did this CIK delist, and what tickers appear on its cover
    page". That conflated a filer with its securities and marked `AAPL` as
    delisted. Stage C asks the Form 25 which class it covers, then resolves only
    that class — through cover-page triples for operating companies, or through
    fund series data for registered funds, which stage B could not name at all.
    """

    root = Path(config.output_root)
    episodes = group_delisting_episodes(load_stage_a_filings(root))
    by_key = {(e.cik, e.delisted_on.isoformat()): e for e in episodes}
    entity_types = {
        (str(row["cik"]), str(row["delisted_on"])): str(row.get("entity_type", ""))
        for row in _read_jsonl(root / _STAGE_B_RESOLUTIONS)
    }
    filings_by_key: dict[tuple[str, str], list[DelistingFiling]] = {}
    for filing in load_stage_a_filings(root):
        for key, episode in by_key.items():
            if filing.cik == episode.cik and (
                episode.delisted_on <= filing.filed <= episode.last_filed_on
            ):
                filings_by_key.setdefault(key, []).append(filing)

    done = {
        (str(row["cik"]), str(row["delisted_on"]))
        for row in _read_jsonl(root / _STAGE_C_ATTRIBUTIONS)
    }
    pending = []
    for key, episode in sorted(by_key.items(), key=lambda kv: kv[1].delisted_on):
        if episode.delisted_on < config.resolve_from or key in done:
            continue
        known = entity_types.get(key, "")
        # An unknown type cannot be filtered here; stage C settles it after one
        # small submissions fetch rather than guessing.
        if known and not _in_entity_scope(config.entity_scope, known):
            continue
        pending.append((key, episode))
    if config.max_resolutions > 0:
        pending = pending[: config.max_resolutions]

    if config.mode == "dry_run":
        return {
            "record_type": "delisting_stage_c_summary",
            "mode": "dry_run",
            "network_access_attempted": False,
            "entity_scope": config.entity_scope,
            "episodes_to_attribute": len(pending),
        }

    fetch = http_get or edgar_get
    pacer = _Pacer(config.request_interval_seconds)
    counts: dict[str, int] = {}
    for key, episode in pending:
        row = _attribute_episode(
            config,
            episode,
            filings=filings_by_key.get(key, ()),
            entity_type=entity_types.get(key, ""),
            fetch=fetch,
            pacer=pacer,
            root=root,
        )
        counts[str(row["attribution"])] = counts.get(str(row["attribution"]), 0) + 1
        _append_jsonl(root / _STAGE_C_ATTRIBUTIONS, row)
    return {
        "record_type": "delisting_stage_c_summary",
        "mode": "live_fetch",
        "network_access_attempted": True,
        "entity_scope": config.entity_scope,
        "episodes_attributed": len(pending),
        "attributions": dict(sorted(counts.items())),
        "attributions_path": str(root / _STAGE_C_ATTRIBUTIONS),
    }


def _in_entity_scope(scope: str, entity_type: str) -> bool:
    if scope == "all":
        return True
    if scope == "investment":
        return entity_type == "investment"
    return entity_type != "investment"


def _accession_from_archive_path(archive_path: str) -> str:
    return archive_path.rsplit("/", 1)[-1].removesuffix(".txt")


def _attribute_episode(
    config: DelistingPipelineConfig,
    episode: DelistingEpisode,
    *,
    filings: Sequence[DelistingFiling],
    entity_type: str,
    fetch: Callable[[str, str, str], bytes],
    pacer: _Pacer,
    root: Path,
) -> dict[str, object]:
    row: dict[str, object] = {
        "cik": episode.cik,
        "company": episode.company,
        "delisted_on": episode.delisted_on.isoformat(),
        "entity_type": entity_type,
        "delisted_classes": [],
        "symbols": [],
        "exchange": "",
        "route": "",
        "candidate_count": 0,
        "attributed_at": datetime.now(UTC).isoformat(),
    }

    # Each description is kept with the date of the Form 25 that carried it. An
    # episode spans every filing within a year, but a sponsor winding down a
    # range of funds files across months, and the funds stop trading on their
    # own dates. Stamping them all with the episode's earliest date truncates
    # real price history — FRN's Form 25 is dated 2019-02-28 and it traded to
    # 2020-02-14.
    dated_classes: list[tuple[date, str]] = []
    for filing in filings:
        accession = _accession_from_archive_path(filing.archive_path)
        path = (
            f"/Archives/edgar/data/{int(episode.cik)}/"
            f"{accession.replace('-', '')}/primary_doc.xml"
        )
        payload = _try_fetch(config, path, fetch=fetch, pacer=pacer, root=root,
                             cik=episode.cik, kind="document")
        if payload is None:
            continue
        described = parse_form25_security(payload)["description_class_security"]
        if described:
            dated_classes.append((filing.filed, described))
    classes = list(dict.fromkeys(described for _, described in dated_classes))
    row["delisted_classes"] = list(classes)
    if not classes:
        row["attribution"] = "form25_class_unreadable"
        return row

    # Fetched here rather than taken from stage B, so stage C can cover
    # episodes stage B never classified — the fund route reads filing headers,
    # which reach back to 2006, where the cover-page route starts in 2019.
    payload = _try_fetch(
        config, f"/submissions/CIK{episode.cik}.json", fetch=fetch, pacer=pacer,
        root=root, cik=episode.cik, kind="submissions", host=DATA_HOST,
    )
    submissions: Mapping[str, object] = {}
    if payload is not None:
        try:
            submissions = json.loads(payload)
        except json.JSONDecodeError:
            submissions = {}
    if not submissions:
        row["attribution"] = "no_candidate_classes"
        row["route"] = "submissions_unavailable"
        return row
    entity_type = entity_type or str(submissions.get("entityType", ""))
    row["entity_type"] = entity_type
    if not _in_entity_scope(config.entity_scope, entity_type):
        # Only knowable after the submissions fetch for episodes stage B never
        # classified. Stopping here costs one small request, not a document.
        row["attribution"] = "out_of_entity_scope"
        row["route"] = "skipped"
        return row

    if entity_type == "investment":
        candidates, route = _fund_series_candidates(
            config, episode, classes, submissions,
            fetch=fetch, pacer=pacer, root=root,
        )
        cover: Sequence[object] = ()
    else:
        cover, route = _cover_page_candidates(
            config, episode, submissions, fetch=fetch, pacer=pacer, root=root
        )
        candidates = ()
    row["route"] = route

    symbols: list[str] = []
    exchange = ""
    attributions: list[str] = []
    candidate_count = 0
    # symbol -> the security it names, so later work can classify a ticker
    # without guessing from the episode's other funds.
    symbol_classes: dict[str, str] = {}
    symbol_delisted_on: dict[str, str] = {}
    for filed_on, described in dated_classes:
        result = attribute_delisted_symbols(
            described,
            cover_page_classes=cover,
            fund_series=candidates,
            # A filing header lists only its own filing's series, so a single
            # hit there is "one was found", not "only one exists".
            candidates_are_complete=entity_type != "investment",
        )
        attributions.append(str(result["attribution"]))
        candidate_count = max(candidate_count, int(result["candidate_count"]))
        for symbol in result["symbols"]:
            if symbol not in symbols:
                symbols.append(str(symbol))
            # The latest Form 25 naming a security is the one that removed it;
            # earlier filings in the episode concern other funds.
            stamped = symbol_delisted_on.get(str(symbol))
            if stamped is None or filed_on.isoformat() > stamped:
                symbol_delisted_on[str(symbol)] = filed_on.isoformat()
        for title, matched in result.get("matched_pairs", ()):
            for symbol in matched:
                symbol_classes.setdefault(str(symbol), str(title))
        exchange = exchange or str(result.get("exchange", ""))
    row["symbols"] = symbols
    row["symbol_classes"] = symbol_classes
    row["symbol_delisted_on"] = symbol_delisted_on
    row["exchange"] = exchange
    row["candidate_count"] = candidate_count
    row["ticker_recoverable"] = bool(symbols)
    # The episode's outcome is its best per-class outcome: one identified class
    # is a real result even when a sibling class stayed ambiguous.
    for preferred in (
        "matched_multiple_classes",
        "matched_delisted_class",
        "sole_registered_class",
        "ambiguous_class_match",
        "unmatched_delisted_class",
        "no_candidate_classes",
    ):
        if preferred in attributions:
            row["attribution"] = preferred
            break
    else:
        row["attribution"] = "no_candidate_classes"
    return row


def _cover_page_candidates(
    config: DelistingPipelineConfig,
    episode: DelistingEpisode,
    submissions: Mapping[str, object],
    *,
    fetch: Callable[[str, str, str], bytes],
    pacer: _Pacer,
    root: Path,
) -> tuple[Sequence[object], str]:
    filings, _ = _recent_filings(submissions, episode.delisted_on)
    chosen = select_symbol_source_filing(filings, delisted_on=episode.delisted_on)
    if chosen is None or not str(chosen["primary"]).strip():
        return (), "no_eligible_periodic_report"
    path = (
        f"/Archives/edgar/data/{int(episode.cik)}/"
        f"{str(chosen['accession']).replace('-', '')}/{chosen['primary']}"
    )
    document = _try_fetch(config, path, fetch=fetch, pacer=pacer, root=root,
                          cik=episode.cik, kind="document")
    if document is None:
        return (), "document_unavailable"
    return extract_cover_page_classes(document), "cover_page"


def _fund_series_candidates(
    config: DelistingPipelineConfig,
    episode: DelistingEpisode,
    classes: Sequence[str],
    submissions: Mapping[str, object],
    *,
    fetch: Callable[[str, str, str], bytes],
    pacer: _Pacer,
    root: Path,
) -> tuple[Sequence[FundSeries], str]:
    """Find the fund series behind a delisting.

    Submission headers carry it: a few kilobytes each, and EDGAR's series data
    reaches back to 2006 where N-CEN begins only in 2018. Each header names
    only its own filing's series, so several are scanned until one matches the
    delisted class.
    """

    forms, dates, accessions = _filing_columns(submissions)
    if not _window_reaches(dates, episode.delisted_on):
        # `recent` caps at a thousand filings, so a prolific trust's window can
        # begin after the delisting. The older pages are where its history is.
        for page in _older_submission_pages(submissions):
            payload = _try_fetch(
                config, f"/submissions/{page}", fetch=fetch, pacer=pacer, root=root,
                cik=episode.cik, kind="submissions", host=DATA_HOST,
            )
            if payload is None:
                continue
            try:
                older = json.loads(payload)
            except json.JSONDecodeError:
                continue
            more_forms, more_dates, more_accessions = _filing_columns(
                {"filings": {"recent": older}}
            )
            forms += more_forms
            dates += more_dates
            accessions += more_accessions
            if _window_reaches(dates, episode.delisted_on):
                break

    eligible = []
    for form, filed, accession in zip(forms, dates, accessions, strict=False):
        try:
            filed_on = date.fromisoformat(str(filed))
        except ValueError:
            continue
        if filed_on > episode.delisted_on or str(form) in DELISTING_FORMS:
            continue
        # Series/class data rides on fund filings; notices and certifications
        # carry none, and scanning them wastes the budget.
        rank = 0 if str(form) in _SERIES_BEARING_FORMS else 1
        eligible.append((rank, -filed_on.toordinal(), str(accession)))
    eligible = [(item[0], item[1], item[2]) for item in sorted(eligible)]
    if not eligible:
        # EDGAR caps `recent` at a thousand filings. A prolific trust's window
        # can start after the delisting, which is a different answer from
        # "this trust filed nothing", and is recorded as one.
        return (), "submissions_window_insufficient"

    seen: list[FundSeries] = []
    for _, _, accession in eligible[: config.max_header_scans]:
        path = (
            f"/Archives/edgar/data/{int(episode.cik)}/"
            f"{accession.replace('-', '')}/{accession}-index-headers.html"
        )
        header = _try_fetch(config, path, fetch=fetch, pacer=pacer, root=root,
                            cik=episode.cik, kind="document")
        if header is None:
            continue
        for series in parse_filing_header_series(header):
            if series.symbols and series.name not in {s.name for s in seen}:
                seen.append(series)
        if any(
            attribute_delisted_symbols(
                described, fund_series=seen, candidates_are_complete=False
            )["symbols"]
            for described in classes
        ):
            return tuple(seen), "filing_header"
    return tuple(seen), "filing_header_exhausted"


def _try_fetch(
    config: DelistingPipelineConfig,
    path: str,
    *,
    fetch: Callable[[str, str, str], bytes],
    pacer: _Pacer,
    root: Path,
    cik: str,
    kind: str,
    host: str = ARCHIVE_HOST,
) -> bytes | None:
    request = {
        "kind": kind,
        "method": "GET",
        "url": f"https://{host}{path}",
        "destination_host": host,
        "destination_allowlist_match": host in (ARCHIVE_HOST, DATA_HOST),
    }
    pacer.wait()
    try:
        payload = fetch(host, path, config.user_agent)
    except (OSError, ValidationError):
        return None
    _record_request(root, request, payload, cik)
    return payload


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
        "--stage", required=True, choices=("a", "b", "c", "summary", "export")
    )
    parser.add_argument(
        "--entity-scope", default="all",
        choices=("all", "investment", "non_investment"),
    )
    parser.add_argument("--max-header-scans", type=int, default=8)
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
            entity_scope=args.entity_scope,
            max_header_scans=args.max_header_scans,
        )
        runner = {"a": run_stage_a, "b": run_stage_b, "c": run_stage_c}[args.stage]
        summary = runner(config)
    except (OSError, ValidationError, ValueError) as exc:
        print(f"delisting_pipeline_status=blocked:{exc}")
        return 2
    print(f"delisting_pipeline_status=completed_stage_{args.stage}")
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
