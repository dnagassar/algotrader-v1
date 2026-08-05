"""Report the full-history delisting registry.

Offline: reads only what the pipeline already wrote. Prints the delisting event
population by year, then the stage B recovery rate with every stratum's
denominator alongside it. The V6.02 sample of seven produced a filer-type story
that a parser defect had manufactured, so no rate is printed on its own.

    PYTHONPATH=src python scripts/report_delisting_registry.py <run-root>
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, "src")

from algotrader.execution.edgar_delisting_pipeline import (  # noqa: E402
    load_stage_a_filings,
    summarize_stage_b,
)
from algotrader.research.delisting_registry import (  # noqa: E402
    TICKER_TAGGING_ERA_START,
    group_delisting_episodes,
)


def _rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _rate(resolved: int, total: int) -> str:
    return f"{resolved / total:.4f}" if total else "n/a"


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else "runs/v6_03_full_history_delisting_registry")

    quarters = _rows(root / "stage_a_quarters.jsonl")
    filings = load_stage_a_filings(root)
    episodes = group_delisting_episodes(filings)

    print("=== Stage A: delisting events ===")
    print(f"quarters_fetched          {len(quarters)}")
    print(f"index_bytes_read          {sum(int(q['byte_count']) for q in quarters):,d}")
    print(f"form_25_filings           {len(filings):,d}")
    print(f"delisting_episodes        {len(episodes):,d}")
    print(f"distinct_ciks             {len({e.cik for e in episodes}):,d}")
    if episodes:
        print(f"earliest_episode          {episodes[0].delisted_on.isoformat()}")
        print(f"latest_episode            {episodes[-1].delisted_on.isoformat()}")
    era = Counter(
        "tagging_era" if e.delisted_on >= TICKER_TAGGING_ERA_START else "pre_tagging_era"
        for e in episodes
    )
    for key in sorted(era):
        print(f"  {key:<24} {era[key]:,d}")

    print("\nepisodes by year")
    by_year = Counter(e.delisted_on.year for e in episodes)
    for year in sorted(by_year):
        print(f"  {year}  {by_year[year]:>6,d}  {'#' * min(60, by_year[year] // 10)}")

    resolutions = _rows(root / "stage_b_resolutions.jsonl")
    if not resolutions:
        print("\n=== Stage B: not yet run ===")
        return 0

    summary = summarize_stage_b(root)
    print("\n=== Stage B: symbol recovery ===")
    print(f"episodes_attempted        {summary['total']:,d}")
    print(f"resolved                  {summary['resolved']:,d}")
    print(f"recovery_rate             {_rate(int(summary['resolved']), int(summary['total']))}")
    print(f"distinct_symbols          {summary['distinct_symbols']:,d}")

    for stratum, buckets in summary["by"].items():
        print(f"\nrecovery by {stratum}")
        ordered = sorted(
            buckets.items(), key=lambda item: -int(item[1]["total"])
        )
        for key, bucket in ordered:
            total = int(bucket["total"])
            resolved = int(bucket["resolved"])
            label = key if key else "(blank)"
            print(f"  {label:<34} {resolved:>6,d} / {total:>6,d}   {_rate(resolved, total)}")

    manifest = _rows(root / "stage_b_manifest.jsonl")
    if manifest:
        print("\n=== Requests ===")
        print(f"stage_b_requests          {len(manifest):,d}")
        print(f"stage_b_bytes             {sum(int(m['byte_count']) for m in manifest):,d}")
        hosts = Counter(str(m["destination_host"]) for m in manifest)
        print(f"hosts                     {dict(sorted(hosts.items()))}")
        print(
            "allowlist_match_all       "
            f"{all(m['destination_allowlist_match'] for m in manifest)}"
        )
        print(
            "credentials_used_any      "
            f"{any(m['credentials_used'] for m in manifest)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
