from argparse import Namespace

import pytest
from textual.widgets import OptionList

from frogmouth.app.app import MarkdownViewer

@pytest.mark.anyio
async def test_theme_selector_lists_only_dark_themes() -> None:
    app = MarkdownViewer(Namespace(file=[]))

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("f10")
        selector = app.screen.query_one("#theme-options", OptionList)
        theme_names = [option.id for option in selector.options]

        assert theme_names
        assert all(
            theme_name is not None and app.available_themes[theme_name].dark
            for theme_name in theme_names
        )
        assert not {
            name for name, theme in app.available_themes.items() if not theme.dark
        }.intersection(theme_names)


@pytest.mark.anyio
async def test_selected_theme_is_persisted_and_restored() -> None:
    app = MarkdownViewer(Namespace(file=[]))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("f10")
        selector = app.screen.query_one("#theme-options", OptionList)
        selector.highlighted = selector.option_count - 1
        await pilot.press("enter")
        selected_theme = app.theme

    assert selected_theme != "textual-dark"
    assert app.available_themes[selected_theme].dark
    restored_app = MarkdownViewer(Namespace(file=[]))
    assert restored_app.theme == selected_theme


@pytest.mark.anyio
async def test_escape_closes_selector_without_changing_theme() -> None:
    app = MarkdownViewer(Namespace(file=[]))
    original_theme = app.theme

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("f10")
        await pilot.press("down")
        await pilot.press("escape")
        assert not app.screen.query("#theme-options")
        assert app.theme == original_theme
