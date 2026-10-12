# src/github_organizer/app.py
from typing import ClassVar

from textual.app import App
from textual.binding import BindingType

from github_organizer.services import load_token
from github_organizer.ui import keybinds
from github_organizer.ui.screens import MainScreen, TokenScreen


class GithubOrganizerApp(App):
    """Aplicación principal de GitHub Organizer."""

    BINDINGS: ClassVar[list[BindingType]] = keybinds.GLOBAL
    TITLE = "GitHub Organizer"
    SUB_TITLE = "Organiza tus repositorios en carpetas personalizadas"

    def on_mount(self) -> None:
        """Decide qué pantalla mostrar al arrancar."""
        if load_token():
            self.push_screen(MainScreen())
        else:
            self.push_screen(TokenScreen())

    def action_push_token_screen(self) -> None:
        self.push_screen(TokenScreen())
