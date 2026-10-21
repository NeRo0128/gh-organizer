# src/gh_organizer/services/config.py
"""Gestión centralizada de configuración y estado en un único archivo TOML."""

import logging
import tomllib
from typing import Any

import tomli_w

from gh_organizer.services.settings import CONFIG_DIR, ensure_dirs

logger = logging.getLogger(__name__)

CONFIG_FILE = CONFIG_DIR / "config.toml"

# Estructura base si el archivo no existe o está corrupto
_DEFAULT_CONFIG = {
    "preferences": {
        "theme": "github",
        "tree_mode": "remember",
        "clone_dir": "~/github",
        "commits_limit": 5,
    },
    "folders": {},
    "tree_state": {"expanded_paths": []},
}


def load() -> dict[str, Any]:
    """Carga el archivo config.toml completo."""
    ensure_dirs()

    # Si el archivo no existe, devolvemos una copia limpia de los defaults
    if not CONFIG_FILE.exists():
        logger.debug("config.toml no existe, usando defaults")
        import copy

        return copy.deepcopy(_DEFAULT_CONFIG)

    try:
        with CONFIG_FILE.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        logger.error("Error leyendo config.toml: %s", e)
        import copy

        return copy.deepcopy(_DEFAULT_CONFIG)

    # Asegurar que las secciones principales existan
    for section, default_val in _DEFAULT_CONFIG.items():
        if section not in data:
            import copy

            data[section] = copy.deepcopy(default_val)
        elif isinstance(default_val, dict):
            # Rellenar claves faltantes dentro de la sección (ej. si añadimos un setting nuevo)
            for k, v in default_val.items():
                data[section].setdefault(k, v)

    return data


def save(data: dict[str, Any]) -> None:
    """Guarda el archivo config.toml completo."""
    ensure_dirs()
    try:
        with CONFIG_FILE.open("wb") as f:
            tomli_w.dump(data, f)
        logger.debug("config.toml guardado (%d secciones)", len(data))
    except OSError as e:
        logger.error("Error escribiendo config.toml: %s", e)
