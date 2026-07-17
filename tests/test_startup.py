from importlib import import_module
from importlib.metadata import version

from frogmouth import __version__


def test_application_entry_point_imports() -> None:
    app_module = import_module("frogmouth.app.app")
    assert callable(app_module.run)


def test_runtime_version_matches_package_metadata() -> None:
    assert __version__ == version("frogmouth")
