# src/gh_organizer/ui/screens/auth.py
"""Pantalla para introducir el Personal Access Token de GitHub."""

import os
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static

from gh_organizer.core.exceptions import GhOrganizerError, KeyringUnavailableError
from gh_organizer.services import GitHubClient, load_token, save_token
from gh_organizer.services.settings import TOKEN_ENV_VAR
from gh_organizer.ui import keybindings
from gh_organizer.ui.styles import AUTH_CSS


class TokenScreen(Screen):
    """Pantalla para introducir el token de GitHub."""

    CSS_PATH = AUTH_CSS
    BINDINGS: ClassVar[list[BindingType]] = keybindings.AUTH

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Center(), Vertical(id="token-container"):
            yield Static("🔑 Introduce tu Personal Access Token de GitHub")
            yield Input(
                placeholder="ghp_...",
                password=True,
                id="token-input",
            )
            yield Button("Guardar token", id="save-btn", variant="primary")
            yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        if load_token():
            self.query_one("#status", Static).update(
                "✅ Ya hay un token guardado. Introduce uno nuevo para reemplazarlo."
            )
        self.query_one("#token-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "save-btn":
            return

        token = self.query_one("#token-input", Input).value.strip()
        status = self.query_one("#status", Static)

        if not token:
            status.update("❌ El token no puede estar vacío.")
            return

        if len(token) < 20:
            status.update(
                "❌ El token parece demasiado corto. Revisa que lo hayas copiado completo."
            )
            return

        # --- Validar el token (y sus permisos) antes de guardarlo ---
        status.update("⏳ Validando token con GitHub...")
        client = GitHubClient(token)
        try:
            user = client.get_authenticated_user()
            # Petición mínima extra: un token válido pero sin scope `repo`
            # autentica bien y falla aquí con MissingScopeError.
            client.verify_repo_scope()
        except GhOrganizerError as e:
            status.update(e.user_message)
            return
        finally:
            client.close()  # un solo cierre, siempre se ejecuta

        try:
            save_token(token)
        except KeyringUnavailableError as e:
            message = f"⚠️ Conectado como @{user.login}. {e.user_message}"
        else:
            message = f"✅ Conectado como @{user.login} — token guardado en el keyring."

        if os.environ.get(TOKEN_ENV_VAR):
            message += (
                f"\n[dim]⚠️ {TOKEN_ENV_VAR} está definido y tiene prioridad sobre "
                "el token guardado.[/dim]"
            )

        status.update(message)
        self.set_timer(2.5, self.app.pop_screen)
