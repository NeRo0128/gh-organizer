# src/github_organizer/app.py
import logging
from typing import ClassVar

logger = logging.getLogger(__name__)
from textual.app import App
from textual.binding import BindingType

from github_organizer.services import load_token
from github_organizer.ui import keybindings
from github_organizer.ui.screens import MainScreen, TokenScreen


class GithubOrganizerApp(App):
    """Aplicación principal de GitHub Organizer."""

    BINDINGS: ClassVar[list[BindingType]] = keybindings.GLOBAL
    TITLE = "GitHub Organizer"
    SUB_TITLE = "Organiza tus repositorios en carpetas personalizadas"

    def on_mount(self) -> None:
        """Decide qué pantalla mostrar al arrancar."""
        logger.info("App montada. Token presente: %s", bool(load_token()))
        if load_token():
            self.push_screen(MainScreen())
        else:
            self.push_screen(TokenScreen())

    def action_push_token_screen(self) -> None:
        self.push_screen(TokenScreen())
