# src/github_organizer/services/preferences.py
"""Preferencias del usuario persistidas en preferences.json.

Esquema plano: un único JSON con todas las claves. La estructura es
tolerante — si falta una clave, se usa DEFAULTS. Si el JSON tiene claves
desconocidas, se preservan al guardar.
"""

import json
import logging
from typing import Any

from github_organizer.services.settings import DATA_DIR, ensure_dirs

logger = logging.getLogger(__name__)

PREFERENCES_FILE = DATA_DIR / "preferences.json"

# ──────────────────────────────────────────────────────────────────── #
#  Esquema
# ──────────────────────────────────────────────────────────────────── #
DEFAULTS: dict[str, Any] = {
    # Apariencia
    "theme": "github",
    "tree_mode": "remember",
    "show_nerd_icons": True,
    "tree_width": "33",
    "animations": True,
    # Repositorios
    "clone_dir": "~/github",
    "commits_limit": 5,
    "releases_limit": 5,
    "exclude_forks": False,
    "exclude_archived": False,
    "sort_by": "updated",
    # Organización
    "default_strategy": "Por lenguaje",
    "confirm_organize": True,
    "confirm_delete_folder": True,
}

# Ajustes cuya UI existe pero cuya lógica aún no está conectada.
# En Settings se muestran en color distinto para saber qué queda por hacer.
PENDING_SETTINGS: frozenset[str] = frozenset(
    {
        "tree_mode",
        "show_nerd_icons",
        "tree_width",
        "animations",
        "clone_dir",
        "commits_limit",
        "releases_limit",
        "exclude_forks",
        "exclude_archived",
        "sort_by",
        "default_strategy",
        "confirm_organize",
        "confirm_delete_folder",
    }
)

VALID_THEMES: tuple[str, ...] = (
    "github",
    "tokyo-night",
    "catppuccin-mocha",
    "github-light",
)
VALID_TREE_MODES: tuple[str, ...] = ("remember", "expanded", "collapsed")


# ──────────────────────────────────────────────────────────────────── #
#  Carga / guardado
# ──────────────────────────────────────────────────────────────────── #
def load_all() -> dict[str, Any]:
    """Devuelve el dict de preferencias con DEFAULTS aplicados para claves faltantes."""
    ensure_dirs()
    if not PREFERENCES_FILE.exists():
        return dict(DEFAULTS)

    try:
        with PREFERENCES_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Error leyendo preferences.json: %s", e)
        return dict(DEFAULTS)

    if not isinstance(data, dict):
        logger.warning("preferences.json no es un dict, usando defaults")
        return dict(DEFAULTS)

    # Migración suave: claves faltantes → defaults; se preservan desconocidas
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in data.items() if v is not None})

    # Validación de enumerados
    if merged["theme"] not in VALID_THEMES:
        merged["theme"] = DEFAULTS["theme"]
    if merged["tree_mode"] not in VALID_TREE_MODES:
        merged["tree_mode"] = DEFAULTS["tree_mode"]

    return merged


def save_all(data: dict[str, Any]) -> None:
    """Guarda el dict entero de preferencias."""
    ensure_dirs()
    try:
        with PREFERENCES_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug("preferences guardadas: %d claves", len(data))
    except OSError as e:
        logger.error("Error escribiendo preferences.json: %s", e)


# ──────────────────────────────────────────────────────────────────── #
#  Acceso puntual
# ──────────────────────────────────────────────────────────────────── #
def get(key: str, default: Any = None) -> Any:
    """Lee una preferencia concreta."""
    if default is not None:
        return load_all().get(key, default)
    return load_all().get(key, DEFAULTS.get(key))


def set_value(key: str, value: Any) -> None:
    """Escribe una preferencia concreta, preservando el resto."""
    data = load_all()
    data[key] = value
    save_all(data)
    logger.info("Preference %r = %r", key, value)


def reset() -> None:
    """Restaura todas las preferencias a DEFAULTS."""
    save_all(dict(DEFAULTS))
    logger.info("Preferencias reseteadas a defaults")


def is_pending(key: str) -> bool:
    """True si el ajuste existe en la UI pero su lógica no está conectada."""
    return key in PENDING_SETTINGS


# ──────────────────────────────────────────────────────────────────── #
#  Helpers específicos (compatibilidad)
# ──────────────────────────────────────────────────────────────────── #
def load_theme() -> str:
    return get("theme")


def save_theme(theme: str) -> None:
    if theme not in VALID_THEMES:
        logger.warning("Intento de guardar tema inválido: %r", theme)
        return
    set_value("theme", theme)


def next_theme(current: str) -> str:
    try:
        idx = VALID_THEMES.index(current)
    except ValueError:
        return VALID_THEMES[0]
    return VALID_THEMES[(idx + 1) % len(VALID_THEMES)]
