"""The main application class for the viewer."""

from argparse import ArgumentParser, Namespace
from webbrowser import open as open_url

from textual import __version__ as textual_version  # pylint: disable=no-name-in-module
from textual.app import App

from .. import __version__
from ..data import load_config
from ..screens import Main
from ..utility.advertising import APPLICATION_TITLE, PACKAGE_NAME


class MarkdownViewer(App[None]):
    """The main application class."""

    TITLE = APPLICATION_TITLE
    """The main title for the application."""

    ENABLE_COMMAND_PALETTE = False

    def __init__(self, cli_args: Namespace) -> None:
        """Initialise the application.

        Args:
            cli_args: The command line arguments.
        """
        super().__init__()
        self._args = cli_args
        configured_theme = load_config().theme
        theme = self.available_themes.get(configured_theme)
        self.theme = configured_theme if theme is not None and theme.dark else "textual-dark"

    def on_mount(self) -> None:
        """Set up the application after the DOM is ready."""
        self.push_screen(Main(" ".join(self._args.file) if self._args.file else None))

    def action_visit(self, url: str) -> None:
        """Visit the given URL, via the operating system.

        Args:
            url: The URL to visit.
        """
        open_url(url)


def get_args() -> Namespace:
    """Parse and return the command line arguments.

    Returns:
        The result of parsing the arguments.
    """

    parser = ArgumentParser(
        prog=PACKAGE_NAME,
        description=f"{APPLICATION_TITLE} -- A Markdown viewer for the terminal.",
        epilog=f"v{__version__}",
    )

    parser.add_argument(
        "-v",
        "--version",
        help="Show version information.",
        action="version",
        version=f"%(prog)s {__version__} (Textual v{textual_version})",
    )

    parser.add_argument("file", help="The Markdown file to view", nargs="*")

    return parser.parse_args()


def run() -> None:
    """Run the application."""
    MarkdownViewer(get_args()).run()
