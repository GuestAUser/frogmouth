from collections.abc import Iterator
from importlib import import_module
from pathlib import Path

import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Path]:
    config_module = import_module("frogmouth.data.config")
    path = tmp_path / "configuration.json"
    monkeypatch.setattr(config_module, "config_file", lambda: path)
    config_module.load_config.cache_clear()
    yield path
    config_module.load_config.cache_clear()
