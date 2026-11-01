# src/gh_organizer/ui/modals/organize_modal.py
import logging
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

from gh_organizer.i18n import _
from gh_organizer.services.organizer import STRATEGIES
from gh_organizer.ui import keybindings
from gh_organizer.ui.styles import MODALS_CSS

logger = logging.getLogger(__name__)


class OrganizeModal(ModalScreen[int | None]):
    """Modal para elegir una estrategia de auto-organización."""

    BINDINGS: ClassVar[list[BindingType]] = keybindings.ORGANIZE
    CSS_PATH = MODALS_CSS

    # Solo estilos específicos de este modal
    CSS = """
    #strategy-list {
        height: auto;
        max-height: 12;
        margin: 1 0;
        border: round $primary;
    }
    """

    def __init__(self, unassigned_count: int, assigned_count: int) -> None:
        super().__init__()
        self._unassigned_count = unassigned_count
        self._assigned_count = assigned_count

    def compose(self) -> ComposeResult:
        # 👈 Usamos classes="modal-box" y classes="modal-title" para los estilos globales
        with Center(), Vertical(classes="modal-box") as box:
            box.border_title = f" {_('Auto-organizar')} "

            yield Label(
                f"📦 {_('Auto-organizar repositorios')}", classes="modal-title"
            )
            yield Label(_("Elige cómo agrupar los repos sin asignar:"))

            items = []
            for name, _fn, desc in STRATEGIES:
                items.append(
                    ListItem(Label(f"[b]{_(name)}[/b]\n[dim]{_(desc)}[/dim]"))
                )
            yield ListView(*items, id="strategy-list")

            yield Static(
                f"[dim]{_('Repos que se verán afectados:')} [/dim]"
                f"[b]{self._unassigned_count}[/b]\n"
                f"[dim]{_('Repos ya asignados (no se tocan):')} [/dim]"
                f"[b]{self._assigned_count}[/b]",
            )

            # 👈 Usamos classes="modal-hint" para el texto de ayuda
            yield Static(
                _(
                    "[b]↑/↓[/b]: elegir · [b]Enter[/b]: aplicar · "
                    "[b]Esc[/b]: cancelar"
                ),
                classes="modal-hint",
            )

    def on_mount(self) -> None:
        self.query_one("#strategy-list", ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.list_view.index)
