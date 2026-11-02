# src/gh_organizer/ui/widgets/status_bar.py
"""Barra de estado inferior con información útil y atajos esenciales."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from gh_organizer.i18n import _


class StatusBar(Horizontal):
    """Barra de estado que muestra el estado actual y atajos clave.

    Args:
        hints: Texto personalizado para el lado izquierdo. Si es None,
               usa el default de MainScreen ("? Ayuda · q Salir").
    """

    def __init__(self, hints: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._hints = hints

    def compose(self) -> ComposeResult:
        hints_text = (
            self._hints
            if self._hints is not None
            else f"[dim]?[/dim] {_('Ayuda')}  ·  [dim]q[/dim] {_('Salir')}"
        )
        yield Static(hints_text, id="status-left")
        yield Static(f"[dim]{_('Listo')}[/dim]", id="status-right")

    def set_status(self, message: str) -> None:
        """Actualiza el mensaje dinámico de la derecha."""
        self.query_one("#status-right", Static).update(f"[b]{message}[/b]")

    def set_hints(self, hints: str) -> None:
        """Actualiza el texto del lado izquierdo (para cambios de idioma)."""
        self._hints = hints
        self.query_one("#status-left", Static).update(hints)
