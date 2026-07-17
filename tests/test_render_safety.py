from argparse import Namespace
from pathlib import Path

import pytest

from frogmouth.app.app import MarkdownViewer
from frogmouth.data import Bookmark
from frogmouth.widgets import Viewer
from frogmouth.widgets.navigation_panes.bookmarks import Entry as BookmarkEntry
from frogmouth.widgets.navigation_panes.history import Entry as HistoryEntry


def test_navigation_labels_render_untrusted_markup_literally() -> None:
    payload = "[@click=app.screenshot('.bashrc','~')]safe[/]"
    history_location = Path("/tmp") / f"{payload}.md"
    bookmark_prompt = BookmarkEntry._as_prompt(Bookmark(payload, Path("README.md")))
    history_prompt = HistoryEntry._as_prompt(history_location)

    assert payload in bookmark_prompt.plain
    assert history_location.name in history_prompt.plain
    assert str(history_location.parent) in history_prompt.plain
    for prompt in (bookmark_prompt, history_prompt):
        assert not any(getattr(span.style, "meta", None) for span in prompt.spans)


def test_local_history_label_preserves_filename_parent_hierarchy() -> None:
    prompt = HistoryEntry._as_prompt(Path("/tmp/report.md"))

    assert prompt.plain == "📄 report.md\n/tmp"
    assert [
        (prompt.plain[span.start : span.end], str(span.style)) for span in prompt.spans
    ] == [("report.md", "bold"), ("/tmp", "dim")]


@pytest.mark.anyio
async def test_terminal_controls_are_removed_from_direct_content() -> None:
    app = MarkdownViewer(Namespace(file=[]))
    payload = "# Safe\n\x1b]52;c;YXR0YWNr\x07after"

    async with app.run_test(size=(100, 30)) as pilot:
        viewer = app.screen.query_one(Viewer)
        viewer.show(payload)
        await pilot.pause()

        assert viewer.document.source == "# Safe\nafter"
