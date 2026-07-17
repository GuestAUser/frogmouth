"""Provides shared JSON file persistence."""

from __future__ import annotations

from json import JSONDecodeError, loads
from os import fdopen, fsync
from pathlib import Path
from tempfile import mkstemp
from typing import TypeAlias


JsonValue: TypeAlias = (
    str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)


def read_json_value(path: Path) -> JsonValue | None:
    try:
        return loads(path.read_text(encoding="utf-8"))
    except (JSONDecodeError, UnicodeDecodeError, OSError):
        return None


def write_json_text(path: Path, content: str) -> None:
    descriptor, temporary_name = mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary_path = Path(temporary_name)
    try:
        with fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            fsync(temporary_file.fileno())
        temporary_path.chmod(0o600)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
