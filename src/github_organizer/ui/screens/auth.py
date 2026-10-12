# src/github_organizer/screens/token_screen.py
from typing import ClassVar

import requests
from github import GithubException
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static

from github_organizer.services import GitHubClient, load_token, save_token
from github_organizer.ui import keybinds


class TokenScreen(Screen):
    """Pantalla para introducir el token de GitHub."""

    CSS = """
    TokenScreen {
        align: center middle;
    }
    #token-container {
        width: 60;
        height: auto;
        padding: 1 2;
        border: round $primary;
    }
    #token-input {
        margin: 1 0;
    }
    #status {
        margin-top: 1;
        color: $text-muted;
    }
    """
    BINDINGS: ClassVar[list[BindingType]] = keybinds.AUTH

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

    # --- Validar el token contra GitHub antes de guardarlo ---
    status.update("⏳ Validando token con GitHub...")
    client = GitHubClient(token)
    try:
        user = client.get_authenticated_user()
    except GithubException as e:
        msg = e.data.get("message", str(e)) if isinstance(e.data, dict) else str(e)
        status.update(f"❌ Token inválido o sin permisos: {msg}")
        return
    except requests.exceptions.RequestException as e:
        status.update(f"🌐 Error de red: no se pudo contactar a GitHub ({e})")
        return
    finally:
        client.close()  # 👈 un solo cierre, siempre se ejecuta

    # --- Si llegamos aquí, el token es válido. Lo guardamos. ---
    if save_token(token):
        status.update(
            f"✅ Conectado como @{user.login} — token guardado en el keyring."
        )
    else:
        status.update(
            f"⚠️ Conectado como @{user.login}, pero no se pudo guardar en el "
            "keyring. Se usará solo para esta sesión."
        )

    self.set_timer(1.8, self.app.pop_screen)
