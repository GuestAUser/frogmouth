from os import name as os_name
from pathlib import Path

from xdg import xdg_data_home

from ..utility.advertising import ORGANISATION_NAME, PACKAGE_NAME


def data_directory() -> Path:
    """Return the app data directory, creating it with private permissions."""
    target_directory = xdg_data_home() / ORGANISATION_NAME / PACKAGE_NAME
    target_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os_name != "nt":
        target_directory.chmod(0o700)
    return target_directory
