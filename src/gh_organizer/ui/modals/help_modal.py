# src/gh_organizer/ui/modals/help_modal.py
import logging
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Center, Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from gh_organizer.i18n import _
from gh_organizer.ui import keybindings
from gh_organizer.ui.keybindings import Binding
from gh_organizer.ui.styles import MODALS_CSS

logger = logging.getLogger(__name__)

_KEY_DISPLAY = {
    "slash": "/",
    "question_mark": "?",
    "escape": "Esc",
    "tab": "Tab",
    "space": "Espacio",
    "enter": "Enter",
    "backspace": "Backspace",
    "left": "←",
    "right": "→",
    "up": "↑",
    "down": "↓",
}


def _display_key(key: str) -> str:
    if key in _KEY_DISPLAY:
        return _(_KEY_DISPLAY[key])
    if key.startswith("ctrl+"):
        return "Ctrl+" + key[5:].upper()
    return key


class HelpModal(ModalScreen[None]):
    """Pantalla de ayuda con todos los atajos de teclado."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "app.pop_screen", "Cerrar", priority=True),
        Binding("question_mark", "app.pop_screen", "Cerrar", priority=True),
        Binding("q", "app.pop_screen", "Cerrar", priority=True),
    ]

    CSS_PATH = MODALS_CSS

    # Solo sobreescribimos el ancho. El resto viene de .modal-box
    CSS = """
    .modal-box {
        width: 120;
    }
    #help-grid {
        grid-size: 3;
        grid-gutter: 1 2;
        height: auto;
        width: 100%;
    }
    #help-grid > Static {
        height: auto;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Center(), Vertical(classes="modal-box") as box:
            box.border_title = f" {_('Ayuda')} "
            yield Static(f"📖 {_('Atajos de teclado')}", classes="modal-title")

            with Grid(id="help-grid"):
                yield Static(self._build_section(_("Global"), keybindings.GLOBAL))
                yield Static(self._build_section(_("Principal"), keybindings.MAIN))
                yield Static(
                    self._build_section(_("Colecciones"), keybindings.FOLDER_PICKER)
                )

                yield Static(
                    self._build_section(_("Auto-organizar"), keybindings.ORGANIZE)
                )
                yield Static(self._build_section(_("Ajustes"), keybindings.SETTINGS))
                yield Static("")

            yield Static(
                f"[dim]{_('Pulsa [b]Esc[/b] o [b]?[/b] para cerrar')}[/dim]",
                classes="modal-hint",
            )

    @staticmethod
    def _build_section(title: str, bindings: list[BindingType]) -> str:
        lines = [f"[b yellow]{title}[/b yellow]"]
        has_items = False

        for b in bindings:
            key_str = ""
            desc = ""
            if isinstance(b, Binding):
                if not b.show:
                    continue
                key_str = b.key
                desc = b.description or b.action
            elif isinstance(b, tuple):
                key_str = b[0]
                desc = b[2] if len(b) > 2 else ""

            if not key_str:
                continue

            key = _display_key(key_str)
            lines.append(f"  [b cyan]{key:<10}[/b cyan] [dim]{desc}[/dim]")
            has_items = True

        # Si no hay atajos, mostramos un mensaje
        if not has_items:
            lines.append(f"  [dim italic]{_('(Sin atajos)')}[/dim italic]")

        return "\n".join(lines)
