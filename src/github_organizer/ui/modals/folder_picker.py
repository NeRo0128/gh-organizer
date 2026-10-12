# src/github_organizer/screens/folder_modal.py
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from github_organizer.services import FolderManager
from github_organizer.ui import keybinds


class FolderModal(ModalScreen[str | None]):
    """Modal para escribir/asignar una ruta de carpeta.

    Devuelve la ruta seleccionada (str) o None si se cancela.
    """

    BINDINGS: ClassVar[list[BindingType]] = keybinds.FOLDER_PICKER

    CSS = """
    FolderModal {
        align: center middle;
    }

    #modal-box {
        width: 70;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $accent;
        border-title-color: $accent;
        border-title-style: bold;
    }

    #modal-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #folder-input {
        margin: 1 0;
    }

    #existing-folders {
        height: auto;
        max-height: 8;
        margin-top: 1;
        padding: 0 1;
        color: $text-muted;
    }

    .modal-buttons {
        height: auto;
        align-horizontal: right;
        margin-top: 1;
    }

    .modal-buttons Button {
        margin-left: 2;
    }
    """

    def __init__(self, repo_name: str | None = None, mode: str = "move") -> None:
        """mode: 'move' (asignar repo) o 'create' (crear carpeta vacía)."""
        super().__init__()
        self.repo_name = repo_name
        self.mode = mode

    def compose(self) -> ComposeResult:
        folders = FolderManager()
        existing = sorted(folders.get_all().keys())

        with Center(), Vertical(id="modal-box") as box:
            if self.mode == "move":
                box.border_title = " Mover repositorio "
                yield Label(
                    f"📦 Mover [b cyan]{self.repo_name}[/b cyan] a carpeta:",
                    id="modal-title",
                )
            else:
                box.border_title = " Nueva carpeta "
                yield Label("📁 Crear nueva carpeta:", id="modal-title")

            yield Input(
                placeholder="Trabajo/Negocios/Web  (usa / para anidar)",
                id="folder-input",
            )

            if existing:
                preview = "\n".join(f"  📁 {p}" for p in existing[:6])
                extra = (
                    f"\n  [dim]… y {len(existing) - 6} más[/dim]"
                    if len(existing) > 6
                    else ""
                )
                yield Static(
                    f"[b]Carpetas existentes:[/b]\n{preview}{extra}",
                    id="existing-folders",
                )
            else:
                yield Static(
                    "[dim]Aún no tienes carpetas. Escribe una ruta para crear la primera.[/dim]",
                    id="existing-folders",
                )

            with Center(classes="modal-buttons"):
                yield Button("Cancelar", id="cancel-btn")
                yield Button("Aceptar", variant="primary", id="accept-btn")

    def on_mount(self) -> None:
        self.query_one("#folder-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._accept()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "accept-btn":
            self._accept()

    def _accept(self) -> None:
        value = self.query_one("#folder-input", Input).value.strip().strip("/")
        if not value:
            return
        self.dismiss(value)
