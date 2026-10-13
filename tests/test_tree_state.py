# tests/test_tree_state.py
"""Tests de persistencia del estado de expansión del árbol."""

import json
from pathlib import Path

from github_organizer.services import tree_state
from github_organizer.services.tree_state import (
    DEFAULT_MODE,
    MODE_COLLAPSED,
    MODE_EXPANDED,
    MODE_REMEMBER,
    load_expanded_paths,
    save_expanded_paths,
)


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


def test_load_handles_corrupt_json(tmp_data_dirs: Path) -> None:
    tree_state.TREE_STATE_FILE.write_text("{not valid json", encoding="utf-8")
    assert load_expanded_paths() == set()


def test_load_handles_empty_file(tmp_data_dirs: Path) -> None:
    tree_state.TREE_STATE_FILE.write_text("", encoding="utf-8")
    assert load_expanded_paths() == set()


def test_load_handles_missing_key(tmp_data_dirs: Path) -> None:
    tree_state.TREE_STATE_FILE.write_text('{"otra_cosa": 1}', encoding="utf-8")
    assert load_expanded_paths() == set()


def test_save_writes_sorted_json(tmp_data_dirs: Path) -> None:
    save_expanded_paths({"C", "A", "B"})
    raw = tree_state.TREE_STATE_FILE.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert data == {"expanded_paths": ["A", "B", "C"]}


def test_mode_constants_exist() -> None:
    assert MODE_REMEMBER == "remember"
    assert MODE_EXPANDED == "expanded"
    assert MODE_COLLAPSED == "collapsed"


def test_default_mode_is_remember() -> None:
    assert DEFAULT_MODE == MODE_REMEMBER
