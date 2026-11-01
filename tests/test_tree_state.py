# tests/test_tree_state.py
"""Tests de persistencia del estado de expansión del árbol.

Desde la migración a un único config.toml, tree_state ya no tiene fichero
propio: escribe la sección ``[tree_state]`` del config.
"""

import tomllib
from pathlib import Path

from gh_organizer.services import config
from gh_organizer.services.tree_state import (
    DEFAULT_MODE,
    MODE_COLLAPSED,
    MODE_EXPANDED,
    MODE_REMEMBER,
    load_expanded_paths,
    save_expanded_paths,
)


def _read_config() -> dict:
    with config.CONFIG_FILE.open("rb") as f:
        return tomllib.load(f)


def test_load_returns_empty_when_file_missing(tmp_data_dirs: Path) -> None:
    assert load_expanded_paths() == set()


def test_save_and_load_roundtrip(tmp_data_dirs: Path) -> None:
    paths = {"A", "A/B", "X/Y/Z"}
    save_expanded_paths(paths)
    assert load_expanded_paths() == paths


def test_save_empty_set(tmp_data_dirs: Path) -> None:
    save_expanded_paths(set())
    assert load_expanded_paths() == set()


def test_save_overwrites_previous(tmp_data_dirs: Path) -> None:
    save_expanded_paths({"A"})
    save_expanded_paths({"B"})
    assert load_expanded_paths() == {"B"}


def test_load_handles_corrupt_toml(tmp_data_dirs: Path) -> None:
    config.CONFIG_FILE.write_text("{not valid toml", encoding="utf-8")
    assert load_expanded_paths() == set()


def test_load_handles_empty_file(tmp_data_dirs: Path) -> None:
    config.CONFIG_FILE.write_text("", encoding="utf-8")
    assert load_expanded_paths() == set()


def test_load_handles_missing_key(tmp_data_dirs: Path) -> None:
    config.CONFIG_FILE.write_text("[tree_state]\nother = 1\n", encoding="utf-8")
    assert load_expanded_paths() == set()


def test_save_writes_sorted_list(tmp_data_dirs: Path) -> None:
    save_expanded_paths({"C", "A", "B"})
    assert _read_config()["tree_state"]["expanded_paths"] == ["A", "B", "C"]


def test_save_preserves_other_sections(tmp_data_dirs: Path, sample_repos: list) -> None:
    """Guardar el árbol NO debe borrar carpetas ni preferencias."""
    from gh_organizer.services import FolderManager

    FolderManager().assign_repo("alpha", "Personal")
    save_expanded_paths({"Personal"})

    data = _read_config()
    assert data["folders"]["Personal"] == ["alpha"]
    assert "preferences" in data


def test_mode_constants_exist() -> None:
    assert MODE_REMEMBER == "remember"
    assert MODE_EXPANDED == "expanded"
    assert MODE_COLLAPSED == "collapsed"


def test_default_mode_is_remember() -> None:
    assert DEFAULT_MODE == MODE_REMEMBER
