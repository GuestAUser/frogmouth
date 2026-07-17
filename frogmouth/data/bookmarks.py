"""Provides code for saving and loading bookmarks."""

from __future__ import annotations

from json import JSONEncoder, dumps
from pathlib import Path
from typing import Any, NamedTuple

from httpx import URL

from ..utility import is_likely_url
from .data_directory import data_directory
from .json_file import read_json_value, write_json_text


class Bookmark(NamedTuple):
    """A bookmark."""

    title: str
    """The title of the bookmark."""
    location: Path | URL
    """The location of the bookmark."""


def bookmarks_file() -> Path:
    """Get the location of the bookmarks file.

    Returns:
        The location of the bookmarks file.
    """
    return data_directory() / "bookmarks.json"


class BookmarkEncoder(JSONEncoder):
    """JSON encoder for the bookmark data."""

    def default(self, o: object) -> Any:
        """Handle the Path and URL values.

        Args:
            o: The object to handle.

        Return:
            The encoded object.
        """
        return str(o) if isinstance(o, (Path, URL)) else o


def save_bookmarks(bookmarks: list[Bookmark]) -> None:
    """Save the given bookmarks.

    Args:
        bookmarks: The bookmarks to save.
    """
    write_json_text(
        bookmarks_file(), dumps(bookmarks, indent=4, cls=BookmarkEncoder)
    )


def load_bookmarks() -> list[Bookmark]:
    """Load the bookmarks.

    Returns:
        The bookmarks.
    """
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
