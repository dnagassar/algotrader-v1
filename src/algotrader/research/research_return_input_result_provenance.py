"""Provenance verifier for return-input-derived research results."""

from __future__ import annotations

from algotrader.errors import ValidationError
from algotrader.research.replay_result import SyntheticResearchResult
from algotrader.research.research_return_input_package import ResearchReturnInputPackage

__all__ = [
    "validate_research_result_matches_return_input_package",
]


def validate_research_result_matches_return_input_package(
    package: ResearchReturnInputPackage,
    result: SyntheticResearchResult,
) -> SyntheticResearchResult:
    """Verify result and package provenance linkage only.

    This confirms the Phase 127 manifest convention for a result already built
    from a return-input package. It does not certify source, methodology,
    no-lookahead status, strategy validity, trading readiness, or downstream
    use.
    """

    checked_package = _package(package)
    checked_result = _result(result)
    manifest = checked_result.snapshot.manifest

    if manifest.fixture_id != checked_package.snapshot.snapshot_id:
        raise ValidationError("result fixture_id must match package snapshot_id.")

    if manifest.checksum != f"sha256:{checked_package.fingerprint}":
        raise ValidationError("result checksum must match package fingerprint.")

    return checked_result


def _package(value: ResearchReturnInputPackage) -> ResearchReturnInputPackage:
    if not isinstance(value, ResearchReturnInputPackage):
        raise ValidationError("package must be a ResearchReturnInputPackage.")

    return value


def _result(value: SyntheticResearchResult) -> SyntheticResearchResult:
    if not isinstance(value, SyntheticResearchResult):
        raise ValidationError("result must be a SyntheticResearchResult.")

    return value
