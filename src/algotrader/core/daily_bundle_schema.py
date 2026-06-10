"""Shared daily bundle schema and contract constants.

This module provides common constants defining the structure, file lists,
and schema elements for daily operator bundles.
"""

# Core generated files that are part of the daily bundle (excluding the manifest itself)
DAILY_BUNDLE_GENERATED_FILES: list[str] = [
    "cycle.jsonl",
    "brief.jsonl",
    "brief.txt",
    "gate.jsonl",
    "dashboard.txt",
]

# The manifest file name
BUNDLE_MANIFEST_FILE: str = "bundle_manifest.jsonl"

# All required files that must exist for status validation (including the manifest)
DAILY_BUNDLE_REQUIRED_FILES: list[str] = DAILY_BUNDLE_GENERATED_FILES + [BUNDLE_MANIFEST_FILE]
