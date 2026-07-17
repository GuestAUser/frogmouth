from __future__ import annotations

from collections.abc import Iterable

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option


class ThemeDialog(ModalScreen[str | None]):
    """Let the user select one registered dark theme."""

    DEFAULT_CSS = """
    ThemeDialog {
        align: center middle;
        background: $background 65%;
    }

    ThemeDialog > Vertical {
        width: 48;
        max-width: 90%;
        height: 22;
        max-height: 80%;
        background: $boost;
        border: thick $primary;
        padding: 1;
    }

    ThemeDialog Label {
        width: 100%;
        height: auto;
        padding: 0 1 1 1;
        text-style: bold;
    }

    ThemeDialog OptionList {
        height: 1fr;
        background: $panel;
        border: none;
    }

    ThemeDialog OptionList:focus {
        border: heavy $accent;
    }

    ThemeDialog #theme-hint {
        padding: 1 1 0 1;
        color: $text-muted;
        text-style: none;
    }
    """

    BINDINGS = [Binding("escape", "dismiss(None)", "", show=False)]

    def __init__(self, theme_names: Iterable[str], current_theme: str) -> None:
        super().__init__()
        self._theme_names = tuple(theme_names)
        self._current_theme = current_theme

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Choose a dark theme")
            yield OptionList(
                *(
                    Option(name.replace("-", " ").title(), id=name)
                    for name in self._theme_names
                ),
                id="theme-options",
            )
            yield Label("Enter selects · Esc cancels", id="theme-hint")

    def on_mount(self) -> None:
        options = self.query_one("#theme-options", OptionList)
        if self._current_theme in self._theme_names:
            options.highlighted = self._theme_names.index(self._current_theme)
        options.focus()

    @on(OptionList.OptionSelected)
    def select_theme(self, event: OptionList.OptionSelected) -> None:
        if event.option_id is not None:
            self.dismiss(event.option_id)
