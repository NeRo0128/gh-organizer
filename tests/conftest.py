# tests/conftest.py
"""Fixtures compartidas para toda la suite de tests.

Todas las pruebas que toquen disco redirigen CONFIG_DIR / DATA_DIR / LOG_DIR
a un directorio temporal (tmp_path). Nunca se toca el directorio real del
usuario (~/.local/share/github-organizer).
"""

from pathlib import Path

import pytest

from github_organizer.core import Repo
from github_organizer.services import settings, tree_state


@pytest.fixture
def tmp_data_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirige todos los directorios y archivos de persistencia a tmp_path.

    Devuelve el directorio de datos (donde viven folders.json y tree_state.json).
    """
    config = tmp_path / "config"
    data = tmp_path / "data"
    log = tmp_path / "log"
    for d in (config, data, log):
        d.mkdir(parents=True, exist_ok=True)

    # settings.py — se consultan en tiempo de llamada, así que basta con
    # sobreescribirlos en el módulo.
    monkeypatch.setattr(settings, "CONFIG_DIR", config)
    monkeypatch.setattr(settings, "DATA_DIR", data)
    monkeypatch.setattr(settings, "LOG_DIR", log)
    monkeypatch.setattr(settings, "FOLDERS_FILE", data / "folders.json")
    monkeypatch.setattr(settings, "LOG_FILE", log / "app.log")

    # tree_state.py — TREE_STATE_FILE se calcula en import-time, hay que
    # parchearlo explícitamente.
    monkeypatch.setattr(tree_state, "DATA_DIR", data)
    monkeypatch.setattr(tree_state, "TREE_STATE_FILE", data / "tree_state.json")

    return data


@pytest.fixture
def sample_repos() -> list[Repo]:
    """Cuatro repos de prueba: 2 Python (1 público/1 privado), 1 Go, 1 sin lenguaje."""
    return [
        Repo(
            name="alpha",
            full_name="user/alpha",
            description="Alpha repo",
            language="Python",
            private=False,
            html_url="https://github.com/user/alpha",
            updated_at="2025-01-15T10:00:00+00:00",
        ),
        Repo(
            name="beta",
            full_name="user/beta",
            description="Beta repo",
            language="Python",
            private=True,
            html_url="https://github.com/user/beta",
            updated_at="2025-02-20T10:00:00+00:00",
        ),
        Repo(
            name="gamma",
            full_name="user/gamma",
            description=None,
            language="Go",
            private=False,
            html_url="https://github.com/user/gamma",
            updated_at="2025-03-10T10:00:00+00:00",
        ),
        Repo(
            name="delta",
            full_name="user/delta",
            description="Delta repo",
            language=None,
            private=True,
            html_url="https://github.com/user/delta",
            updated_at="2024-12-01T10:00:00+00:00",
        ),
    ]
