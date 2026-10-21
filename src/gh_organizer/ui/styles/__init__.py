# src/gh_organizer/ui/styles/__init__.py
"""Temas y rutas a las hojas de estilo TCSS."""

from pathlib import Path

from gh_organizer.ui.styles.themes import ALL_THEMES

STYLES_DIR = Path(__file__).parent

BASE_CSS = STYLES_DIR / "base.tcss"
MAIN_CSS = STYLES_DIR / "main.tcss"
AUTH_CSS = STYLES_DIR / "auth.tcss"
MODALS_CSS = STYLES_DIR / "modals.tcss"
SETTINGS_CSS = STYLES_DIR / "settings.tcss"

__all__ = [
    "ALL_THEMES",
    "AUTH_CSS",
    "BASE_CSS",
    "MAIN_CSS",
    "MODALS_CSS",
    "SETTINGS_CSS",
    "STYLES_DIR",
]
