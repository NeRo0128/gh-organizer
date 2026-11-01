# src/gh_organizer/services/config.py
"""Gestión centralizada de configuración y estado en un único archivo TOML.

Un ``config.toml`` corrupto nunca debe romper el arranque (la app tiene que
poder abrirse para que el usuario lo arregle), pero tampoco debe perderse en
silencio: se guarda una copia ``config.toml.corrupt-<timestamp>`` y el error
queda disponible con :func:`consume_last_error` para que la UI avise.
"""

import copy
import logging
import shutil
import time
import tomllib
from typing import Any

import tomli_w

from gh_organizer.core.exceptions import ConfigWriteError, CorruptedConfigError
from gh_organizer.services.settings import CONFIG_DIR, ensure_dirs

logger = logging.getLogger(__name__)

CONFIG_FILE = CONFIG_DIR / "config.toml"

# Último error de lectura pendiente de mostrar (la UI lo consume una vez).
_last_error: CorruptedConfigError | None = None

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


def consume_last_error() -> CorruptedConfigError | None:
    """Devuelve (y limpia) el último error de lectura de configuración."""
    global _last_error
    error, _last_error = _last_error, None
    return error


def load() -> dict[str, Any]:
    """Carga el archivo config.toml completo."""
    global _last_error

    ensure_dirs()

    # Si el archivo no existe, devolvemos una copia limpia de los defaults
    if not CONFIG_FILE.exists():
        logger.debug("config.toml no existe, usando defaults")
        return copy.deepcopy(_DEFAULT_CONFIG)

    try:
        with CONFIG_FILE.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        logger.error("config.toml corrupto: %s", e)
        _backup_corrupt_file()
        _last_error = CorruptedConfigError()
        return copy.deepcopy(_DEFAULT_CONFIG)
    except OSError as e:
        # Sin permisos de lectura: defaults, pero avisando y sin sobrescribir.
        logger.error("Error leyendo config.toml: %s", e)
        _last_error = CorruptedConfigError()
        return copy.deepcopy(_DEFAULT_CONFIG)

    # Asegurar que las secciones principales existan
    for section, default_val in _DEFAULT_CONFIG.items():
        if section not in data:
            data[section] = copy.deepcopy(default_val)
        elif isinstance(default_val, dict):
            # Rellenar claves faltantes dentro de la sección (ej. si añadimos un setting nuevo)
            for k, v in default_val.items():
                data[section].setdefault(k, v)

    return data


def save(data: dict[str, Any]) -> None:
    """Guarda el archivo config.toml completo.

    Raises:
        ConfigWriteError: si no se puede escribir (permisos, disco lleno…).
    """
    ensure_dirs()
    try:
        with CONFIG_FILE.open("wb") as f:
            tomli_w.dump(data, f)
    except OSError as e:
        logger.error("Error escribiendo config.toml: %s", e)
        raise ConfigWriteError(str(CONFIG_FILE)) from e
    logger.debug("config.toml guardado (%d secciones)", len(data))


def _backup_corrupt_file() -> None:
    """Copia el config corrupto antes de que alguien lo sobrescriba con defaults."""
    backup = CONFIG_FILE.with_suffix(f".toml.corrupt-{time.strftime('%Y%m%d-%H%M%S')}")
    try:
        shutil.copy2(CONFIG_FILE, backup)
        logger.warning("Copia del config corrupto guardada en %s", backup)
    except OSError as e:
        logger.error("No se pudo respaldar el config corrupto: %s", e)
