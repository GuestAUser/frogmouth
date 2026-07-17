"""Provides a function for working out the data directory location."""

from os import name as os_name
from pathlib import Path

from xdg import xdg_data_home

from ..utility.advertising import ORGANISATION_NAME, PACKAGE_NAME


def data_directory() -> Path:
    """Get the location of the data directory.

    Returns:
        The location of the data directory.

    Note:
        As a side effect, if the directory doesn't exist it will be created.
    """
    target_directory = xdg_data_home() / ORGANISATION_NAME / PACKAGE_NAME
    target_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os_name != "nt":
        target_directory.chmod(0o700)
    return target_directory
