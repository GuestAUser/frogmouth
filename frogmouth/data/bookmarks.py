from __future__ import annotations

from json import JSONEncoder, dumps
from pathlib import Path
from typing import Any, NamedTuple

from httpx import URL

from ..utility import is_likely_url
from .data_directory import data_directory
from .json_file import read_json_value, write_json_text


class Bookmark(NamedTuple):
    title: str
    location: Path | URL


def bookmarks_file() -> Path:
    return data_directory() / "bookmarks.json"


class BookmarkEncoder(JSONEncoder):
    def default(self, o: object) -> Any:
        return str(o) if isinstance(o, (Path, URL)) else o


def save_bookmarks(bookmarks: list[Bookmark]) -> None:
    write_json_text(
        bookmarks_file(), dumps(bookmarks, indent=4, cls=BookmarkEncoder)
    )


def load_bookmarks() -> list[Bookmark]:
    bookmarks = bookmarks_file()
    if not bookmarks.exists():
        return []
    saved_bookmarks = read_json_value(bookmarks)
    if not isinstance(saved_bookmarks, list):
        return []
    loaded_bookmarks: list[Bookmark] = []
    for saved_bookmark in saved_bookmarks:
        if not isinstance(saved_bookmark, list) or len(saved_bookmark) != 2:
            continue
        title, location = saved_bookmark
        if not isinstance(title, str) or not isinstance(location, str):
            continue
        loaded_bookmarks.append(
            Bookmark(
                title, URL(location) if is_likely_url(location) else Path(location)
            )
        )
    return loaded_bookmarks
