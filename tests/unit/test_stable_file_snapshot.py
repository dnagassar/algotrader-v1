from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.stable_file_snapshot import capture_stable_file


def test_capture_uses_one_immutable_content_version(tmp_path: Path) -> None:
    path = tmp_path / "bars.csv"
    path.write_text("date,symbol,close\n2026-07-10,SPY,100\n", encoding="utf-8")

    snapshot = capture_stable_file(path)
    path.write_text("date,symbol,close\n2026-07-10,SPY,200\n", encoding="utf-8")

    assert "SPY,100" in snapshot.text()
    assert "SPY,200" not in snapshot.text()
    assert snapshot.size == len(snapshot.content)
    assert len(snapshot.sha256) == 64


def test_empty_input_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_bytes(b"")

    with pytest.raises(ValidationError, match="empty"):
        capture_stable_file(path)
