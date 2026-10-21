# src/gh_organizer/app.py
import logging
from typing import ClassVar

from textual.app import App
from textual.binding import BindingType

from gh_organizer.services import load_token
from gh_organizer.services.preferences import load_theme
from gh_organizer.ui import keybindings
from gh_organizer.ui.screens import MainScreen, TokenScreen
from gh_organizer.ui.styles import ALL_THEMES, BASE_CSS

logger = logging.getLogger(__name__)


class GithubOrganizerApp(App):
    """Aplicación principal de GitHub Organizer."""

    BINDINGS: ClassVar[list[BindingType]] = keybindings.GLOBAL
    TITLE = "GitHub Organizer"
    SUB_TITLE = "Organiza tus repositorios en carpetas personalizadas"
    CSS_PATH = BASE_CSS

    def on_mount(self) -> None:
        """Registra los temas, aplica el guardado y decide la pantalla inicial."""
        for theme in ALL_THEMES:
            self.register_theme(theme)
        self.theme = load_theme()
        logger.info("Tema aplicado: %s", self.theme)

        logger.info("App montada. Token presente: %s", bool(load_token()))
        if load_token():
            self.push_screen(MainScreen())
        else:
            self.push_screen(TokenScreen())

    def action_push_token_screen(self) -> None:
        self.push_screen(TokenScreen())
