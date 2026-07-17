from __future__ import annotations

from json import JSONEncoder, dumps
from pathlib import Path
from typing import Any

from httpx import URL

from ..utility import is_likely_url
from .data_directory import data_directory
from .json_file import read_json_value, write_json_text


def history_file() -> Path:
    return data_directory() / "history.json"


class HistoryEncoder(JSONEncoder):
    def default(self, o: object) -> Any:
        return str(o) if isinstance(o, (Path, URL)) else o


def save_history(history: list[Path | URL]) -> None:
    write_json_text(history_file(), dumps(history, indent=4, cls=HistoryEncoder))


def load_history() -> list[Path | URL]:
    history = history_file()
    if not history.exists():
        return []
    locations = read_json_value(history)
    if not isinstance(locations, list):
        return []
    return [
        URL(location) if is_likely_url(location) else Path(location)
        for location in locations
        if isinstance(location, str)
    ]
