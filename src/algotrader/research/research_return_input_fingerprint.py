"""Stable digest helper for research return input snapshots."""

import hashlib
import json

from algotrader.research.research_return_input import ResearchReturnInputSnapshot
from algotrader.research.research_return_input_consistency import (
    validate_research_return_input_snapshot_consistency,
)

__all__ = [
    "research_return_input_snapshot_fingerprint",
]


def research_return_input_snapshot_fingerprint(
    snapshot: ResearchReturnInputSnapshot,
) -> str:
    """Return a deterministic content hash for a candidate-only snapshot.

    The digest does not certify source, methodology, data, strategy, or
    downstream use.
    """

    validate_research_return_input_snapshot_consistency(snapshot)
    payload = snapshot.to_dict()
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
