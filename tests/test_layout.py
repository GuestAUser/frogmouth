from argparse import Namespace

import pytest

from frogmouth.app.app import MarkdownViewer
from frogmouth.widgets import Navigation, Viewer


@pytest.mark.parametrize("terminal_width", [60, 80, 120])
@pytest.mark.anyio
async def test_navigation_preserves_document_width_on_narrow_terminals(
    terminal_width: int,
) -> None:
    app = MarkdownViewer(Namespace(file=[]))

    async with app.run_test(size=(terminal_width, 30)) as pilot:
        await pilot.press("ctrl+y")
        await pilot.pause()
        navigation = app.screen.query_one(Navigation)
        viewer = app.screen.query_one(Viewer)

        assert viewer.size.width >= terminal_width // 2 - 2
        assert navigation.size.width == min(terminal_width // 2, 44)
