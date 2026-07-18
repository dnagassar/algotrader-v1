"""Immutable one-read snapshot for local production inputs."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path

from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class StableFileSnapshot:
    path: Path
    content: bytes
    sha256: str
    size: int
    modified_ns: int

    def text(self, encoding: str = "utf-8") -> str:
        try:
            return self.content.decode(encoding)
        except UnicodeDecodeError as exc:
            raise ValidationError("stable input file is not valid UTF-8.") from exc


def capture_stable_file(path: str | Path) -> StableFileSnapshot:
    """Read one stable file version or fail closed if it changes during capture."""

    resolved = Path(path)
    if not resolved.is_file():
        raise ValidationError(f"Input file not found: {resolved}")
    try:
        with resolved.open("rb") as stream:
            before = os.fstat(stream.fileno())
            content = stream.read()
            after = os.fstat(stream.fileno())
        current = resolved.stat()
    except OSError as exc:
        raise ValidationError("stable input file could not be read.") from exc

    identity_before = (before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_ino, after.st_size, after.st_mtime_ns)
    identity_current = (current.st_ino, current.st_size, current.st_mtime_ns)
    if identity_before != identity_after or identity_after != identity_current:
        raise ValidationError("input file changed during stable snapshot capture.")
    if len(content) != after.st_size:
        raise ValidationError("stable input file size does not match captured bytes.")
    if not content:
        raise ValidationError("stable input file is empty.")
    return StableFileSnapshot(
        path=resolved,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content),
        modified_ns=after.st_mtime_ns,
    )


__all__ = ["StableFileSnapshot", "capture_stable_file"]
