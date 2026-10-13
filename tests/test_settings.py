# tests/test_settings.py
"""Tests de persistencia de folders.json y creación de directorios."""

import json
from pathlib import Path

from github_organizer.services import settings
from github_organizer.services.settings import (
    ensure_dirs,
    load_folders,
    save_folders,
)


def test_ensure_dirs_creates_everything(tmp_data_dirs: Path, tmp_path: Path) -> None:
    # Borramos lo que creó la fixture y volvemos a crearlo
    import shutil

    for name in ("config", "data", "log"):
        shutil.rmtree(tmp_path / name)
    ensure_dirs()
    assert settings.CONFIG_DIR.exists()
    assert settings.DATA_DIR.exists()
    assert settings.LOG_DIR.exists()


def test_load_returns_empty_when_missing(tmp_data_dirs: Path) -> None:
    assert load_folders() == {}


def test_save_and_load_roundtrip(tmp_data_dirs: Path) -> None:
    data = {"Personal": ["alpha"], "Trabajo/Clientes": ["beta", "gamma"]}
    save_folders(data)
    assert load_folders() == data


def test_save_preserves_unicode(tmp_data_dirs: Path) -> None:
    data = {"Públicos": ["ñandú", "café"]}
    save_folders(data)
    assert load_folders() == data


def test_load_handles_corrupt_json(tmp_data_dirs: Path) -> None:
    settings.FOLDERS_FILE.write_text("no es json", encoding="utf-8")
    assert load_folders() == {}


def test_save_creates_parent_dirs(tmp_data_dirs: Path, tmp_path: Path) -> None:
    # Borramos el directorio data para forzar a que save_folders lo recree
    import shutil

    shutil.rmtree(tmp_data_dirs)
    save_folders({"A": []})
    assert settings.FOLDERS_FILE.exists()


def test_save_writes_indented_json(tmp_data_dirs: Path) -> None:
    save_folders({"A": ["x"]})
    raw = settings.FOLDERS_FILE.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert parsed == {"A": ["x"]}
    assert "\n" in raw  # indent=2 produce saltos de línea
