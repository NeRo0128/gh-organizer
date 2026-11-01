# src/gh_organizer/ui/widgets/status_bar.py
"""Barra de estado inferior con información útil y atajos esenciales."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from gh_organizer.i18n import _


class StatusBar(Horizontal):
    """Barra de estado que muestra el estado actual y atajos clave."""

    def compose(self) -> ComposeResult:
        # Lado izquierdo: Atajos esenciales y estado
        yield Static(
            f"[dim]?[/dim] {_('Ayuda')}  ·  [dim]q[/dim] {_('Salir')}  ·  ",
            id="status-left",
        )
        # Lado derecho: Mensaje dinámico (se actualizará desde la pantalla)
        yield Static(f"[dim]{_('Listo')}[/dim]", id="status-right")

    def set_status(self, message: str) -> None:
        """Actualiza el mensaje dinámico de la derecha."""
        self.query_one("#status-right", Static).update(f"[b]{message}[/b]")
