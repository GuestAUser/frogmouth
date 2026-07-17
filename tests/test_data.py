from importlib import import_module
from json import dumps
from os import name as os_name
from pathlib import Path
from stat import S_IMODE
from typing import NoReturn

import pytest

from frogmouth.data import Bookmark, Config
from frogmouth.data.config import config_file as resolve_config_file


def _deny_read(
    path: Path, encoding: str | None = None, errors: str | None = None
) -> NoReturn:
    del path, encoding, errors
    raise PermissionError


def test_malformed_config_recovers_defaults(isolated_config: Path) -> None:
    config_module = import_module("frogmouth.data.config")
    isolated_config.write_text("{broken", encoding="utf-8")
    config_module.load_config.cache_clear()

    assert config_module.load_config() == Config()


def test_malformed_history_recovers_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_module = import_module("frogmouth.data.history")
    path = tmp_path / "history.json"
    path.write_text("[broken", encoding="utf-8")
    monkeypatch.setattr(history_module, "history_file", lambda: path)

    assert history_module.load_history() == []


def test_malformed_bookmarks_recovers_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bookmarks_module = import_module("frogmouth.data.bookmarks")
    path = tmp_path / "bookmarks.json"
    path.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(bookmarks_module, "bookmarks_file", lambda: path)

    assert bookmarks_module.load_bookmarks() == []


def test_saved_state_is_private_and_valid_json(
    tmp_path: Path, isolated_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_module = import_module("frogmouth.data.config")
    history_module = import_module("frogmouth.data.history")
    bookmarks_module = import_module("frogmouth.data.bookmarks")
    history_path = tmp_path / "history.json"
    bookmarks_path = tmp_path / "bookmarks.json"
    monkeypatch.setattr(history_module, "history_file", lambda: history_path)
    monkeypatch.setattr(bookmarks_module, "bookmarks_file", lambda: bookmarks_path)

    config_module.save_config(Config(theme="nord"))
    history_module.save_history([Path("README.md")])
    bookmarks_module.save_bookmarks([Bookmark("Readme", Path("README.md"))])

    for path in (isolated_config, history_path, bookmarks_path):
        assert S_IMODE(path.stat().st_mode) == 0o600
        assert not tuple(path.parent.glob(f".{path.name}.*.tmp"))


def test_config_preserves_valid_values_and_ignores_unknown_keys(
    isolated_config: Path,
) -> None:
    config_module = import_module("frogmouth.data.config")
    isolated_config.write_text(
        dumps(
            {
                "theme": "nord",
                "light_mode": "invalid",
                "markdown_extensions": [".md", 7],
                "navigation_left": False,
                "future_option": True,
            }
        ),
        encoding="utf-8",
    )
    config_module.load_config.cache_clear()

    assert config_module.load_config() == Config(theme="nord", navigation_left=False)


def test_config_wrong_top_level_recovers_defaults(isolated_config: Path) -> None:
    config_module = import_module("frogmouth.data.config")
    isolated_config.write_text("[]", encoding="utf-8")
    config_module.load_config.cache_clear()

    assert config_module.load_config() == Config()


def test_history_preserves_valid_entries_from_malformed_items(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_module = import_module("frogmouth.data.history")
    path = tmp_path / "history.json"
    path.write_text(dumps(["README.md", 7, ["nested"], None]), encoding="utf-8")
    monkeypatch.setattr(history_module, "history_file", lambda: path)

    assert history_module.load_history() == [Path("README.md")]


def test_history_wrong_top_level_recovers_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_module = import_module("frogmouth.data.history")
    path = tmp_path / "history.json"
    path.write_text('{"location": "README.md"}', encoding="utf-8")
    monkeypatch.setattr(history_module, "history_file", lambda: path)

    assert history_module.load_history() == []


def test_bookmarks_preserve_valid_entries_from_malformed_items(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bookmarks_module = import_module("frogmouth.data.bookmarks")
    path = tmp_path / "bookmarks.json"
    path.write_text(
        dumps(
            [
                ["Readme", "README.md"],
                ["Missing location"],
                [7, "invalid-title.md"],
                ["Extra", "README.md", "value"],
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(bookmarks_module, "bookmarks_file", lambda: path)

    assert bookmarks_module.load_bookmarks() == [Bookmark("Readme", Path("README.md"))]


def test_bookmarks_wrong_top_level_recovers_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bookmarks_module = import_module("frogmouth.data.bookmarks")
    path = tmp_path / "bookmarks.json"
    path.write_text('{"title": "Readme"}', encoding="utf-8")
    monkeypatch.setattr(bookmarks_module, "bookmarks_file", lambda: path)

    assert bookmarks_module.load_bookmarks() == []


@pytest.mark.parametrize(
    ("module_name", "file_function", "load_function", "expected"),
    [
        ("frogmouth.data.config", "config_file", "load_config", Config()),
        ("frogmouth.data.history", "history_file", "load_history", []),
        ("frogmouth.data.bookmarks", "bookmarks_file", "load_bookmarks", []),
    ],
)
def test_invalid_utf8_state_recovers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    file_function: str,
    load_function: str,
    expected: Config | list[Path] | list[Bookmark],
) -> None:
    module = import_module(module_name)
    path = tmp_path / "state.json"
    path.write_bytes(b"\xff")
    monkeypatch.setattr(module, file_function, lambda: path)
    loader = getattr(module, load_function)
    if load_function == "load_config":
        loader.cache_clear()

    assert loader() == expected


@pytest.mark.parametrize(
    (
        "module_name",
        "file_function",
        "load_function",
        "serialized_state",
        "expected",
    ),
    [
        (
            "frogmouth.data.config",
            "config_file",
            "load_config",
            '{"theme": "nord"}',
            Config(),
        ),
        (
            "frogmouth.data.history",
            "history_file",
            "load_history",
            '["README.md"]',
            [],
        ),
        (
            "frogmouth.data.bookmarks",
            "bookmarks_file",
            "load_bookmarks",
            '[["Readme", "README.md"]]',
            [],
        ),
    ],
)
def test_unreadable_state_recovers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    file_function: str,
    load_function: str,
    serialized_state: str,
    expected: Config | list[Path] | list[Bookmark],
) -> None:
    module = import_module(module_name)
    path = tmp_path / "state.json"
    path.write_text(serialized_state, encoding="utf-8")
    monkeypatch.setattr(module, file_function, lambda: path)
    monkeypatch.setattr(Path, "read_text", _deny_read)
    loader = getattr(module, load_function)
    if load_function == "load_config":
        loader.cache_clear()

    assert loader() == expected


@pytest.mark.skipif(os_name == "nt", reason="POSIX permissions are unavailable")
def test_config_directory_is_private(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_module = import_module("frogmouth.data.config")
    monkeypatch.setattr(config_module, "xdg_config_home", lambda: tmp_path)

    directory = resolve_config_file().parent

    assert S_IMODE(directory.stat().st_mode) == 0o700


@pytest.mark.skipif(os_name == "nt", reason="POSIX permissions are unavailable")
def test_data_directory_is_private(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_directory_module = import_module("frogmouth.data.data_directory")
    monkeypatch.setattr(data_directory_module, "xdg_data_home", lambda: tmp_path)

    directory = data_directory_module.data_directory()

    assert S_IMODE(directory.stat().st_mode) == 0o700
