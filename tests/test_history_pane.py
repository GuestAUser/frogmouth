from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import OptionList

from frogmouth.widgets.navigation_panes.history import Entry, History


class HistoryApp(App[None]):
    def compose(self) -> ComposeResult:
        yield History()


@pytest.mark.anyio
async def test_history_update_preserves_reverse_chronological_order() -> None:
    locations = [Path(f"document-{index}.md") for index in range(3)]
    app = HistoryApp()

    async with app.run_test() as pilot:
        history = app.query_one(History)
        history.update_from(locations)
        await pilot.pause()
        entries = app.query_one(OptionList).options

        assert [entry.location for entry in entries if isinstance(entry, Entry)] == [
            *reversed(locations)
        ]
