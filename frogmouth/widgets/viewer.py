"""The markdown viewer itself."""

from __future__ import annotations

import re
from collections import deque
from pathlib import Path
from typing import Callable
from webbrowser import open as open_url

from httpx import URL, AsyncClient, HTTPStatusError, Limits, RequestError, Timeout
from markdown_it import MarkdownIt
from mdit_py_plugins import front_matter
from textual import work
from textual.app import ComposeResult
from textual.await_complete import AwaitComplete
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.message import Message
from textual.reactive import var
from textual.widgets import Markdown
from typing_extensions import Final

from .. import __version__
from ..dialogs import ErrorDialog
from ..utility.advertising import APPLICATION_TITLE, USER_AGENT

PLACEHOLDER = f"""\
# {APPLICATION_TITLE} {__version__}

Welcome to {APPLICATION_TITLE}!
"""

MAX_DOCUMENT_BYTES: Final[int] = 8 * 1024 * 1024
"""Maximum decoded size of a remote Markdown document."""

_DOWNLOAD_CHUNK_BYTES: Final[int] = 64 * 1024
_DOWNLOAD_TIMEOUT: Final[Timeout] = Timeout(
    connect=5.0, read=30.0, write=10.0, pool=5.0
)
_DOWNLOAD_LIMITS: Final[Limits] = Limits(
    max_connections=4, max_keepalive_connections=2, keepalive_expiry=5.0
)

# Match complete ECMA-48 terminal sequences before removing residual controls.
_TERMINAL_SEQUENCE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:\x1b\]|\x9d)[^\x07\x1b\x9c\n\r]*(?:\x07|\x1b\\|\x9c)?"
    r"|(?:\x1b[PX^_]|[\x90\x98\x9e\x9f])[^\x1b\x9c\n\r]*(?:\x1b\\|\x9c)?"
    r"|(?:\x1b\[|\x9b)[0-?]*[ -/]*[@-~]"
    r"|\x1b[ -/]*[0-~]"
)
_TERMINAL_CONTROL_RE: Final[re.Pattern[str]] = re.compile(
    r"[\x00-\x08\x0b-\x1f\x7f-\x9f]"
)


class DocumentTooLargeError(Exception):
    """Raised when a decoded document exceeds the configured limit."""

    def __init__(self, maximum_bytes: int) -> None:
        self.maximum_bytes = maximum_bytes
        super().__init__(
            f"Document is too large; maximum size is {maximum_bytes:,} bytes."
        )


class _UnsupportedDocumentTypeError(Exception):
    """Raised when a remote resource is not Markdown-compatible text."""


def _strip_terminal_controls(markdown: str) -> str:
    """Remove terminal escape sequences and control bytes from Markdown."""
    without_sequences = _TERMINAL_SEQUENCE_RE.sub("", markdown)
    return _TERMINAL_CONTROL_RE.sub("", without_sequences)


class SafeMarkdown(Markdown):
    """Markdown widget that sanitizes all content before parsing it."""

    def update(self, markdown: str) -> AwaitComplete:
        return super().update(_strip_terminal_controls(markdown))


async def download_markdown(client: AsyncClient, location: URL) -> str:
    """Download a Markdown document within the decoded-size limit."""
    async with client.stream(
        "GET",
        location,
        follow_redirects=True,
        headers={"user-agent": USER_AGENT},
        timeout=_DOWNLOAD_TIMEOUT,
    ) as response:
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if not any(
            content_type.startswith(f"text/{sub_type}")
            for sub_type in ("plain", "markdown", "x-markdown")
        ):
            raise _UnsupportedDocumentTypeError

        content = bytearray()
        async for chunk in response.aiter_bytes(chunk_size=_DOWNLOAD_CHUNK_BYTES):
            if len(content) + len(chunk) > MAX_DOCUMENT_BYTES:
                raise DocumentTooLargeError(MAX_DOCUMENT_BYTES)
            content.extend(chunk)

        return content.decode(response.encoding or "utf-8", errors="replace")


class History:
    """Holds the browsing history for the viewer."""

    MAXIMUM_HISTORY_LENGTH: Final[int] = 256
    """The maximum number of items we'll keep in history."""

    def __init__(self, history: list[Path | URL] | None = None) -> None:
        """Initialise the history object."""
        self._history: deque[Path | URL] = deque(
            history or [], maxlen=self.MAXIMUM_HISTORY_LENGTH
        )
        """The list that holds the history of locations visited."""
        self._current: int = max(len(self._history) - 1, 0)
        """The current location."""

    @property
    def location(self) -> Path | URL | None:
        """The current location in the history."""
        try:
            return self._history[self._current]
        except IndexError:
            return None

    @property
    def current(self) -> int | None:
        """The current location in history, or None if there is no current location."""
        return None if self.location is None else self._current

    @property
    def locations(self) -> list[Path | URL]:
        """The locations in the history."""
        return list(self._history)

    def remember(self, location: Path | URL) -> None:
        """Remember a new location in the history.

        Args:
            location: The location to remember.
        """
        self._history.append(location)
        self._current = len(self._history) - 1

    def back(self) -> bool:
        """Go back in the history.

        Returns:
            `True` if the location changed, `False` if not.
        """
        if self._current:
            self._current -= 1
            return True
        return False

    def forward(self) -> bool:
        """Go forward in the history.

        Returns:
            `True` if the location changed, `False` if not.
        """
        if self._current < len(self._history) - 1:
            self._current += 1
            return True
        return False

    def __delitem__(self, index: int) -> None:
        normalized_index = index if index >= 0 else len(self._history) + index
        del self._history[index]
        if normalized_index < self._current:
            self._current -= 1
        elif self._current >= len(self._history):
            self._current = max(len(self._history) - 1, 0)


class Viewer(VerticalScroll, can_focus=True, can_focus_children=True):
    """The markdown viewer class."""

    DEFAULT_CSS = """
    Viewer {
        width: 1fr;
        scrollbar-gutter: stable;
    }
    """

    BINDINGS = [
        Binding("w,k", "scroll_up", "", show=False),
        Binding("s,j", "scroll_down", "", show=False),
        Binding("space", "page_down", "", show=False),
        Binding("b", "page_up", "", show=False),
    ]
    """Bindings for the Markdown viewer widget."""

    history: var[History] = var(History)
    """The browsing history."""

    viewing_location: var[bool] = var(False)
    """Is an actual location being viewed?"""

    class ViewerMessage(Message):
        """Base class for viewer messages."""

        def __init__(self, viewer: Viewer) -> None:
            """Initialise the message.

            Args:
                viewer: The viewer sending the message.
            """
            super().__init__()
            self.viewer: Viewer = viewer
            """The viewer that sent the message."""

    class LocationChanged(ViewerMessage):
        """Message sent when the viewer location changes."""

    class HistoryUpdated(ViewerMessage):
        """Message sent when the history is updated."""

    def compose(self) -> ComposeResult:
        """Compose the markdown viewer."""
        yield SafeMarkdown(
            PLACEHOLDER,
            parser_factory=lambda: MarkdownIt("gfm-like").use(
                front_matter.front_matter_plugin
            ),
        )

    @property
    def document(self) -> Markdown:
        """The markdown document."""
        return self.query_one(Markdown)

    @property
    def location(self) -> Path | URL | None:
        """The location that is currently being visited."""
        return self.history.location if self.viewing_location else None

    def scroll_to_block(self, block_id: str) -> None:
        """Scroll the document to the given block ID.

        Args:
            block_id: The ID of the block to scroll to.
        """
        self.scroll_to_widget(self.document.query_one(f"#{block_id}"), top=True)

    def _post_load(self, location: Path | URL, remember: bool = True) -> None:
        """Perform some post-load tasks.

        Args:
            location: The location that has been loaded.
            remember: Should we remember the location in the history?
        """
        # We've loaded something fresh, ensure we're at the top.
        self.scroll_home(animate=False)
        # If we've made it in here we are viewing an actual location.
        self.viewing_location = True
        # Remember the location in the history if we're supposed to.
        if remember:
            self.history.remember(location)
            self.post_message(self.HistoryUpdated(self))
        # Let anyone else know we've changed location.
        self.post_message(self.LocationChanged(self))

    @work(exclusive=True)
    async def _local_load(self, location: Path, remember: bool = True) -> None:
        """Load a Markdown document from a local file.

        Args:
            location: The location to load from.
            remember: Should we remember the location in th ehistory?
        """
        try:
            await self.document.load(location)
        except OSError as error:
            self.app.push_screen(
                ErrorDialog(
                    "Error loading local document",
                    f"{location}\n\n{error}.",
                )
            )
        else:
            self._post_load(location, remember)

    @work(exclusive=True)
    async def _remote_load(self, location: URL, remember: bool = True) -> None:
        """Load a Markdown document from a URL.

        Args:
            location: The location to load from.
            remember: Should we remember the location in the history?
        """

        try:
            async with AsyncClient(
                limits=_DOWNLOAD_LIMITS, timeout=_DOWNLOAD_TIMEOUT
            ) as client:
                content = await download_markdown(client, location)
        except _UnsupportedDocumentTypeError:
            open_url(str(location))
            return
        except DocumentTooLargeError as error:
            self.app.push_screen(
                ErrorDialog("Document too large", f"{location}\n\n{error}")
            )
            return
        except RequestError as error:
            self.app.push_screen(ErrorDialog("Error getting document", str(error)))
            return
        except HTTPStatusError as error:
            self.app.push_screen(ErrorDialog("Error getting document", str(error)))
            return

        self.document.update(content)
        self._post_load(location, remember)

    def visit(self, location: Path | URL, remember: bool = True) -> None:
        """Visit a location.

        Args:
            location: The location to visit.
            remember: Should this visit be added to the history?
        """
        # Based on the type of the location, load up the content.
        if isinstance(location, Path):
            self._local_load(location.expanduser().resolve(), remember)
        elif isinstance(location, URL):
            self._remote_load(location, remember)
        else:
            raise ValueError("Unknown location type passed to the Markdown viewer")

    def reload(self) -> None:
        """Reload the current location."""
        if self.location is not None:
            self.visit(self.location, False)

    def show(self, content: str) -> None:
        """Show some direct text in the viewer.

        Args:
            content: The text to show.
        """
        self.viewing_location = False
        self.document.update(content)
        self.scroll_home(animate=False)

    def _jump(self, direction: Callable[[], bool]) -> None:
        """Jump in a particular direction within the history.

        Args:
            direction: A function that jumps in the desired direction.
        """
        if direction():
            if self.history.location is not None:
                self.visit(self.history.location, remember=False)

    def back(self) -> None:
        """Go back in the viewer history."""
        self._jump(self.history.back)

    def forward(self) -> None:
        """Go forward in the viewer history."""
        self._jump(self.history.forward)

    def load_history(self, history: list[Path | URL]) -> None:
        """Load up a history list from the given history.

        Args:
            history: The history load up from.
        """
        self.history = History(history)
        self.post_message(self.HistoryUpdated(self))

    def delete_history(self, history_id: int) -> None:
        """Delete an item from the history.

        Args:
            history_id: The ID of the history item to delete.
        """
        try:
            del self.history[history_id]
        except IndexError:
            pass
        else:
            self.post_message(self.HistoryUpdated(self))

    def clear_history(self) -> None:
        """Clear down the whole of history."""
        self.load_history([])
