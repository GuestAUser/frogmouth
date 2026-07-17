"""Provides code for loading/saving configuration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache
from json import dumps
from os import name as os_name
from pathlib import Path

from xdg import xdg_config_home

from ..utility.advertising import ORGANISATION_NAME, PACKAGE_NAME
from .json_file import JsonValue, read_json_value, write_json_text


@dataclass
class Config:
    """The markdown viewer configuration."""

    theme: str = "textual-dark"
    """The registered dark theme to use."""

    light_mode: bool = False
    """Legacy preference retained while existing configuration is migrated."""

    markdown_extensions: list[str] = field(default_factory=lambda: [".md", ".markdown"])
    """What Markdown extensions will we look for?"""

    navigation_left: bool = True
    """Should navigation be docked to the left side of the screen?"""


def _config_from_json(value: JsonValue) -> Config:
    defaults = Config()
    if not isinstance(value, dict):
        return defaults

    theme = value.get("theme")
    light_mode = value.get("light_mode")
    markdown_extensions = value.get("markdown_extensions")
    navigation_left = value.get("navigation_left")
    if isinstance(markdown_extensions, list) and all(
        isinstance(extension, str) for extension in markdown_extensions
    ):
        parsed_extensions = [
            extension for extension in markdown_extensions if isinstance(extension, str)
        ]
    else:
        parsed_extensions = defaults.markdown_extensions
    return Config(
        theme=theme if isinstance(theme, str) else defaults.theme,
        light_mode=(
            light_mode if isinstance(light_mode, bool) else defaults.light_mode
        ),
        markdown_extensions=parsed_extensions,
        navigation_left=(
            navigation_left
            if isinstance(navigation_left, bool)
            else defaults.navigation_left
        ),
    )


def config_file() -> Path:
    """Get the path to the configuration file.

    Returns:
        The path to the configuration file.

    Note:
        As a side-effect, the configuration directory will be created if it
        does not exist.
    """
    config_dir = xdg_config_home() / ORGANISATION_NAME / PACKAGE_NAME
    config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os_name != "nt":
        config_dir.chmod(0o700)
    return config_dir / "configuration.json"


def save_config(config: Config) -> Config:
    """Save the given configuration to storage.

    Args:
        config: The configuration to save.

    Returns:
        The configuration.
    """
    write_json_text(config_file(), dumps(asdict(config), indent=4))
    load_config.cache_clear()
    return config


@lru_cache(maxsize=None)
def load_config() -> Config:
    """Load the configuration from storage.

    Returns:
        The configuration.

    Note:
        As a side-effect, if the configuration doesn't exist a default one
        will be saved to storage.

        This function is designed so that it's safe and low-cost to
        repeatedly call it. The configuration is cached and will only be
        loaded from storage when necessary.
    """
    source_file = config_file()
    if not source_file.exists():
        return save_config(Config())
    return _config_from_json(read_json_value(source_file))
