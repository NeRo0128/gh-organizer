# src/github_organizer/ui/modals/organize_modal.py
import logging
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

from github_organizer.services.organizer import STRATEGIES
from github_organizer.ui import keybindings
from github_organizer.ui.styles import MODALS_CSS

logger = logging.getLogger(__name__)


class OrganizeModal(ModalScreen[int | None]):
    """Modal para elegir una estrategia de auto-organización.

    Devuelve el índice de la estrategia elegida, o None si se cancela.
    """

    BINDINGS: ClassVar[list[BindingType]] = keybindings.ORGANIZE
    CSS_PATH = MODALS_CSS

    def __init__(self, unassigned_count: int, assigned_count: int) -> None:
        super().__init__()
        self._unassigned_count = unassigned_count
        self._assigned_count = assigned_count
        logger.debug(
            "OrganizeModal instanciada (sin asignar=%d, asignados=%d)",
            unassigned_count,
            assigned_count,
        )

    def compose(self) -> ComposeResult:
        with Center(), Vertical(id="organize-box") as box:
            box.border_title = " Auto-organizar "
            yield Label("📦 Auto-organizar repositorios", id="organize-title")
            yield Label("Elige cómo agrupar los repos sin asignar:")

            items = []
            for name, _fn, desc in STRATEGIES:
                items.append(ListItem(Label(f"[b]{name}[/b]\n[dim]{desc}[/dim]")))
            yield ListView(*items, id="strategy-list")

            yield Static(
                f"[dim]Repos que se verán afectados: [/dim][b]{self._unassigned_count}[/b]\n"
                f"[dim]Repos ya asignados (no se tocan): [/dim][b]{self._assigned_count}[/b]",
                id="summary",
            )
            yield Static(
                "[b]↑/↓[/b]: elegir · [b]Enter[/b]: aplicar · [b]Esc[/b]: cancelar",
                id="hint",
            )

    def on_mount(self) -> None:
        self.query_one("#strategy-list", ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        index = event.list_view.index
        logger.debug("Estrategia seleccionada: índice %s", index)
        self.dismiss(index)
