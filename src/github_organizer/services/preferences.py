# src/github_organizer/services/preferences.py
"""Preferencias del usuario persistidas (tema, etc.)."""

import json
import logging

from github_organizer.services.settings import DATA_DIR, ensure_dirs

logger = logging.getLogger(__name__)

PREFERENCES_FILE = DATA_DIR / "preferences.json"

DEFAULT_THEME = "github"
VALID_THEMES: tuple[str, ...] = (
    "github",
    "tokyo-night",
    "catppuccin-mocha",
    "github-light",
)


def load_theme() -> str:
    """Carga el tema preferido. Devuelve DEFAULT_THEME si no existe o es inválido."""
    ensure_dirs()
    if not PREFERENCES_FILE.exists():
        return DEFAULT_THEME
    try:
        with PREFERENCES_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Error leyendo preferences.json: %s", e)
        return DEFAULT_THEME

    theme = data.get("theme", DEFAULT_THEME)
    if theme not in VALID_THEMES:
        logger.warning("Tema desconocido %r, usando %r", theme, DEFAULT_THEME)
        return DEFAULT_THEME
    return theme


def save_theme(theme: str) -> None:
    """Guarda el tema preferido en disco."""
    if theme not in VALID_THEMES:
        logger.warning("Intento de guardar tema inválido: %r", theme)
        return
    ensure_dirs()

    data: dict = {}
    if PREFERENCES_FILE.exists():
        try:
            with PREFERENCES_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except OSError, json.JSONDecodeError:
            data = {}

    data["theme"] = theme
    try:
        with PREFERENCES_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Tema guardado: %s", theme)
    except OSError as e:
        logger.error("Error escribiendo preferences.json: %s", e)


def next_theme(current: str) -> str:
    """Devuelve el siguiente tema en el ciclo. Si `current` no es válido, devuelve el primero."""
    try:
        idx = VALID_THEMES.index(current)
    except ValueError:
        return VALID_THEMES[0]
    return VALID_THEMES[(idx + 1) % len(VALID_THEMES)]
