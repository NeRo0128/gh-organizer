# tests/conftest.py
"""Fixtures compartidas para toda la suite de tests.

Todas las pruebas que toquen disco redirigen CONFIG_DIR / DATA_DIR / LOG_DIR y,
sobre todo, ``services.config.CONFIG_FILE`` a un directorio temporal
(tmp_path). Nunca se toca la configuración real del usuario
(~/.config/github-organizer).
"""

from pathlib import Path

import pytest

from gh_organizer.core import Repo
from gh_organizer.services import config, settings


@pytest.fixture
def tmp_data_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirige todos los directorios y archivos de persistencia a tmp_path.

    Devuelve el directorio de datos. La configuración real (config.toml) queda
    en ``tmp_path / "config"``.
    """
    config_dir = tmp_path / "config"
    data = tmp_path / "data"
    log = tmp_path / "log"
    for d in (config_dir, data, log):
        d.mkdir(parents=True, exist_ok=True)

    # settings.py — se consultan en tiempo de llamada, así que basta con
    # sobreescribirlos en el módulo.
    monkeypatch.setattr(settings, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(settings, "DATA_DIR", data)
    monkeypatch.setattr(settings, "LOG_DIR", log)
    monkeypatch.setattr(settings, "FOLDERS_FILE", data / "folders.json")
    monkeypatch.setattr(settings, "LOG_FILE", log / "app.log")

    # config.py — CONFIG_FILE se calcula en import-time, hay que parchearlo
    # explícitamente (si no, los tests escribirían en ~/.config real).
    monkeypatch.setattr(config, "CONFIG_FILE", config_dir / "config.toml")
    config.consume_last_error()  # limpia errores de tests anteriores

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
