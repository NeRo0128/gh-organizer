# src/gh_organizer/ui/modals/dependencies_modal.py
"""Modal de diagnóstico de dependencias externas."""

from __future__ import annotations

import logging
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from gh_organizer.i18n import _
from gh_organizer.services.dependencies import detect_os_key
from gh_organizer.ui import keybindings
from gh_organizer.ui.icons import ICON_CHECK, ICON_CROSS
from gh_organizer.ui.styles import MODALS_CSS

logger = logging.getLogger(__name__)


class DependenciesModal(ModalScreen[bool]):
    """Muestra el estado de las dependencias y guía al usuario.

    Retorna True si el usuario quiere continuar (con o sin dependencias),
    False si prefiere salir para instalarlas.
    """

    BINDINGS: ClassVar[list[BindingType]] = keybindings.DEPENDENCIES

    CSS_PATH = MODALS_CSS

    def __init__(self, statuses: list) -> None:
        super().__init__()
        self._statuses = statuses
        self._os_key = detect_os_key()

    def compose(self) -> ComposeResult:
        missing_critical = [s for s in self._statuses if not s.available and s.critical]
        missing_optional = [
            s for s in self._statuses if not s.available and not s.critical
        ]

        with Center(), Vertical(classes="modal-box") as box:
            box.border_title = f" {_('Verificación de dependencias')} "

            yield Label(_("🔍 Estado de dependencias"), classes="modal-title")

            lines: list[str] = []
            for s in self._statuses:
                if s.available:
                    icon = f"[green]{ICON_CHECK}[/green]"
                    status_text = _("instalado")
                    color = "green"
                else:
                    icon = f"[red]{ICON_CROSS}[/red]"
                    status_text = _("no instalado")
                    color = "red"

                critical_marker = (
                    f" [yellow]{_('(crítica)')}[/yellow]" if s.critical else ""
                )
                lines.append(
                    f"{icon} [b]{s.name.value}[/b]{critical_marker} "
                    f"[{color}]— {status_text}[/{color}]"
                )
                if not s.available:
                    cmd = s.install_command_for(self._os_key)
                    lines.append(f"   [dim]→ {cmd}[/dim]")

            yield Static("\n".join(lines), id="dep-list")

            if missing_critical:
                yield Label(
                    _(
                        "⚠️  Falta una dependencia crítica. "
                        "La app funcionará pero no podrás clonar repositorios."
                    ),
                    id="dep-warning",
                )
            elif missing_optional:
                yield Label(
                    _(
                        "ℹ️  Algunas dependencias opcionales faltan. "
                        "La app funcionará con funcionalidad reducida."
                    ),
                    id="dep-info",
                )

            with Center():
                if missing_critical:
                    yield Button(
                        _("Continuar de todas formas"),
                        id="btn-continue",
                        variant="warning",
                    )
                else:
                    yield Button(_("Entendido"), id="btn-continue", variant="primary")
                yield Button(_("Salir"), id="btn-exit", variant="error")

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-continue":
            logger.info("Usuario eligió continuar")
            self.dismiss(True)
        elif event.button.id == "btn-exit":
            logger.info("Usuario eligió salir")
            self.dismiss(False)
