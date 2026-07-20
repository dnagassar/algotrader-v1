"""Unit tests for V5.33.2 atomic receipt persistence repair."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from algotrader.cli import _write_receipt_atomically


def test_atomic_persistence_success(tmp_path: Path) -> None:
    dest = tmp_path / "receipts" / "test_receipt.json"
    data = {"zebra": 1, "apple": 2, "mango": "test"}

    _write_receipt_atomically(dest, data)

    assert dest.is_file()
    content = dest.read_bytes()

    # Exactly one terminal newline
    assert content.endswith(b"\n")
    assert not content.endswith(b"\n\n")

    # Sorted keys and indented json
    decoded = json.loads(content.decode("utf-8"))
    assert decoded == data
    lines = content.decode("utf-8").splitlines()
    assert lines[1].strip().startswith('"apple"')

    # Verify no temp files left behind in destination parent
    temp_files = list(dest.parent.glob("tmp_*"))
    assert len(temp_files) == 0


def test_atomic_persistence_failure_cleanup_and_sanitization(tmp_path: Path) -> None:
    dest = tmp_path / "fail_receipt.json"
    data = {"key": "value"}

    # Simulate error during json dump or fsync
    with patch("os.fsync", side_effect=OSError("Disk full or permission denied at /secret/path/filename.tmp")):
        with pytest.raises(RuntimeError) as exc_info:
            _write_receipt_atomically(dest, data)

        # Ensure only the stable error classification is raised
        assert str(exc_info.value) == "receipt_persistence_failed"
        assert exc_info.value.__cause__ is None  # Cause hidden to prevent path leaks

    # Verify temp file removed after failure
    temp_files = list(tmp_path.glob("tmp_*"))
    assert len(temp_files) == 0
