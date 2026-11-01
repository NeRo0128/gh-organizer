# src/gh_organizer/ui/modals/folder_picker.py
import logging
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static, Tree
from textual.widgets.tree import TreeNode

from gh_organizer.core.exceptions import GhOrganizerError
from gh_organizer.services import FolderManager
from gh_organizer.ui import keybindings
from gh_organizer.ui.icons import ICON_EMPTY, ICON_FOLDER
from gh_organizer.ui.styles import MODALS_CSS

logger = logging.getLogger(__name__)


class FolderModal(ModalScreen[str | None]):
    """Gestor de colecciones: crear, mover, renombrar y eliminar."""

    BINDINGS: ClassVar[list[BindingType]] = keybindings.FOLDER_PICKER
    CSS_PATH = MODALS_CSS

    # Solo estilos específicos. El ancho y borde vienen de .modal-box
    CSS = """
    #folder-tree {
        height: auto;
        min-height: 8;
        max-height: 14;
        border: round $primary;
        margin: 1 0;
    }

    #context-label {
        margin-top: 1;
        height: auto;
        color: $text;
    }

    #folder-input:focus {
        border: tall $accent;
        background: $boost;
    }
    """

    def __init__(self, repo_name: str | None = None, mode: str = "move") -> None:
        super().__init__()
        self.repo_name = repo_name
        self.mode = mode
        self._state: str = "creating"  # creating | renaming | confirming
        self._target_path: str = ""
        self._expanded_paths: set[str] = set()
        self._selected_path: str = ""
        self._suppress_events: bool = False

    def compose(self) -> ComposeResult:
        with Center(), Vertical(classes="modal-box") as box:
            if self.mode == "move":
                box.border_title = " Mover repositorio "
                yield Label(
                    f"📦 Mover [b cyan]{self.repo_name}[/b cyan] a:",
                    classes="modal-title",
                )
            else:
                box.border_title = " Gestor de colecciones "
                yield Label("📁 Gestor de colecciones", classes="modal-title")

            yield Tree(f"{ICON_FOLDER} Colecciones", id="folder-tree")
            yield Static("", id="context-label")
            yield Input(placeholder="Nombre de la nueva colección", id="folder-input")
            yield Static("", id="hint-label", classes="modal-hint")

    def on_mount(self) -> None:
        logger.debug("on_mount: modal montado (modo=%s)", self.mode)
        tree = self.query_one("#folder-tree", Tree)
        tree.show_root = True
        tree.root.data = ""
        tree.root.expand()

        # Expandir TODAS las carpetas al abrir el picker
        folders = FolderManager().get_all()
        self._expanded_paths = set(folders.keys())

        self._rebuild_tree()
        tree.focus()
        logger.debug("on_mount: foco → %s", self.focused.id if self.focused else "None")

    # ------------------------------------------------------------------ #
    #  Reconstrucción del árbol
    # ------------------------------------------------------------------ #
    def _rebuild_tree(self) -> None:
        """Reconstruye el árbol aplicando `_expanded_paths` y `_selected_path`."""
        self._suppress_events = True
        tree = self.query_one("#folder-tree", Tree)
        tree.clear()
        tree.root.data = ""
        tree.root.expand()

        folders = FolderManager().get_all()
        nodes: dict[tuple, TreeNode] = {(): tree.root}

        # Limpieza: descartar rutas que ya no existen
        self._expanded_paths &= self._all_valid_paths(folders)

        for path in sorted(folders.keys()):
            parts = path.split("/")
            for i in range(1, len(parts) + 1):
                partial = tuple(parts[:i])
                if partial not in nodes:
                    parent = nodes[partial[:-1]]
                    node = parent.add(f"{ICON_FOLDER} {parts[i - 1]}")
                    node.data = "/".join(parts[:i])
                    nodes[partial] = node

        if not folders:
            tree.root.add_leaf(f"[dim]{ICON_EMPTY} (sin colecciones todavía)[/dim]")

        # Aplicar expansión desde el set
        for partial, node in nodes.items():
            if partial and "/".join(partial) in self._expanded_paths:
                node.expand()

        # Restaurar / auto-seleccionar
        if self._selected_path and tuple(self._selected_path.split("/")) in nodes:
            target = nodes[tuple(self._selected_path.split("/"))]
            tree.select_node(target)
            tree.scroll_to_node(target)
        elif tree.root.children:
            first = tree.root.children[0]
            tree.select_node(first)
            tree.scroll_to_node(first)
            if isinstance(first.data, str):
                self._selected_path = first.data
        else:
            tree.select_node(tree.root)
            self._selected_path = ""

        # 👈 ¡AQUÍ ESTÁ EL TRUCO!
        # Solo activamos los eventos cuando Textual termine de dibujar este frame
        self.call_after_refresh(self._enable_events)
        self._update_context()

    def _enable_events(self) -> None:
        """Reactiva la escucha de eventos después de un ciclo de refresco."""
        self._suppress_events = False

    @staticmethod
    def _all_valid_paths(folder_data: dict[str, list[str]]) -> set[str]:
        paths: set[str] = set()
        for path in folder_data:
            parts = path.split("/")
            for i in range(1, len(parts) + 1):
                paths.add("/".join(parts[:i]))
        return paths

    # ------------------------------------------------------------------ #
    #  Contexto (label + hint)
    # ------------------------------------------------------------------ #
    def _update_context(self) -> None:
        label = self.query_one("#context-label", Static)
        hint = self.query_one("#hint-label", Static)
        input_w = self.query_one("#folder-input", Input)

        if self._state == "renaming":
            parent = "/".join(self._target_path.split("/")[:-1]) or "(raíz)"
            label.update(f"📍 Padre:  [dim]{parent}[/dim]   ✏️  Renombrando")
            hint.update("[b]Enter[/b]: confirmar · [b]Esc[/b]: cancelar")
            return

        if self._state == "confirming":
            folders = FolderManager()
            repos, subs = folders.count_descendants(self._target_path)
            label.update(
                f"⚠️  ¿Eliminar [b]{self._target_path}[/b]? "
                f"Contiene [b]{repos}[/b] repos y [b]{subs}[/b] subcarpetas."
            )
            hint.update("[b]y[/b]: eliminar · [b]n[/b]/[b]Esc[/b]: cancelar")
            return

        parent = self._selected_path or "(raíz)"

        if input_w.has_focus:
            label.update(f"✏️  Creando dentro de: [b cyan]{parent}[/b cyan]")
            if self.mode == "move":
                hint.update(
                    "[b]Enter[/b]: crear y mover aquí · [b]Tab[/b]: volver al árbol"
                )
            else:
                hint.update(
                    "[b]Enter[/b]: crear · [b]Tab[/b]: volver al árbol · [b]Esc[/b]: limpiar"
                )
        else:
            label.update(f"📍 Seleccionada: [b cyan]{parent}[/b cyan]")
            if self.mode == "move":
                hint.update(
                    "[b]Enter[/b]: mover aquí · [b]n[/b]: nueva hija · "
                    "[b]a[/b]: nueva raíz · [b]r[/b]: rename · [b]d[/b]: del · [b]Esc[/b]: cerrar"
                )
            else:
                hint.update(
                    "[b]n[/b]: nueva hija · [b]a[/b]: nueva raíz · "
                    "[b]Tab[/b]: escribir · [b]r[/b]: rename · [b]d[/b]: del · [b]Esc[/b]: cerrar"
                )

    # ------------------------------------------------------------------ #
    #  Eventos del árbol
    # ------------------------------------------------------------------ #
    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        if self._suppress_events:
            return
        data = event.node.data
        self._selected_path = data if isinstance(data, str) else ""
        self._update_context()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if self._suppress_events:
            return
        if self._state in ("renaming", "confirming"):
            return
        if self.mode == "move":
            data = event.node.data
            if isinstance(data, str) and data:
                self.dismiss(data)

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._state == "renaming":
            self._confirm_rename()
            return
        if self._state == "confirming":
            return
        self._create_folder()

    # ------------------------------------------------------------------ #
    #  on_key (Navegación manual y confirmaciones)
    # ------------------------------------------------------------------ #
    def on_key(self, event) -> None:
        key = event.key.lower()

        if self._state == "confirming":
            if key == "y":
                event.stop()
                self._confirm_delete()
            elif key == "n":
                event.stop()
                self._cancel_special_state()
            elif key != "escape":
                event.stop()
            return

        if self._state == "renaming":
            if key == "escape":
                event.stop()
                self._cancel_special_state()
            return

        tree = self.query_one("#folder-tree", Tree)
        if tree.has_focus:
            if key == "left":
                event.stop()
                self._tree_cursor_left()
                self._selected_path = self._current_path()
                self._update_context()
                return
            if key == "right":
                event.stop()
                self._tree_cursor_right()
                self._selected_path = self._current_path()
                self._update_context()
                return

    def _tree_cursor_left(self) -> None:
        tree = self.query_one("#folder-tree", Tree)
        node = tree.cursor_node
        if node is None:
            return
        if node.children and node.is_expanded:
            node.collapse()
            if isinstance(node.data, str) and node.data:
                self._expanded_paths.discard(node.data)
        elif node.parent is not None and node.parent is not tree.root:
            tree.select_node(node.parent)

    def _tree_cursor_right(self) -> None:
        tree = self.query_one("#folder-tree", Tree)
        node = tree.cursor_node
        if node is None:
            return
        if node.children and not node.is_expanded:
            node.expand()
            if isinstance(node.data, str) and node.data:
                self._expanded_paths.add(node.data)
        elif node.children and node.is_expanded:
            tree.select_node(node.children[0])

    # ------------------------------------------------------------------ #
    #  Acciones
    # ------------------------------------------------------------------ #
    def _current_path(self) -> str:
        tree = self.query_one("#folder-tree", Tree)
        node = tree.cursor_node
        if node is None or node.data is None:
            return ""
        return node.data if isinstance(node.data, str) else ""

    def action_toggle_panel(self) -> None:
        tree = self.query_one("#folder-tree", Tree)
        input_w = self.query_one("#folder-input", Input)
        if tree.has_focus:
            input_w.focus()
        else:
            tree.focus()
            self._selected_path = self._current_path()
        self._update_context()

    def action_new_child_folder(self) -> None:
        path = self._current_path()
        self._selected_path = path
        input_w = self.query_one("#folder-input", Input)
        input_w.value = ""
        input_w.placeholder = (
            f"Nueva colección dentro de {path}" if path else "Nombre en la raíz"
        )
        input_w.focus()
        self._update_context()

    def action_new_root_folder(self) -> None:
        self._selected_path = ""
        tree = self.query_one("#folder-tree", Tree)
        tree.select_node(tree.root)
        input_w = self.query_one("#folder-input", Input)
        input_w.value = ""
        input_w.placeholder = "Nombre de la nueva colección raíz"
        input_w.focus()
        self._update_context()

    def action_rename_folder(self) -> None:
        path = self._current_path()
        if not path:
            self.notify(
                "Selecciona una carpeta (no la raíz).", severity="warning", timeout=2
            )
            return
        self._state = "renaming"
        self._target_path = path
        input_w = self.query_one("#folder-input", Input)
        input_w.value = path.split("/")[-1]
        input_w.focus()
        input_w.action_end()
        self._update_context()

    def action_delete_folder(self) -> None:
        path = self._current_path()
        if not path:
            self.notify(
                "Selecciona una carpeta (no la raíz).", severity="warning", timeout=2
            )
            return
        folders = FolderManager()
        repos, subs = folders.count_descendants(path)
        if repos == 0 and subs == 0:
            try:
                folders.delete_folder(path)
            except GhOrganizerError as e:
                self.notify(e.user_message, severity="error", timeout=5)
                return
            self._expanded_paths = {
                p
                for p in self._expanded_paths
                if not (p == path or p.startswith(path + "/"))
            }
            self._selected_path = ""
            self._rebuild_tree()
            return
        self._state = "confirming"
        self._target_path = path
        self._update_context()

    def action_handle_escape(self) -> None:
        if self._state in ("renaming", "confirming"):
            self._cancel_special_state()
            return
        input_w = self.query_one("#folder-input", Input)
        if input_w.has_focus and input_w.value:
            input_w.value = ""
            return
        self.dismiss(None)

    # ------------------------------------------------------------------ #
    #  Operaciones
    # ------------------------------------------------------------------ #
    def _create_folder(self) -> None:
        value = self.query_one("#folder-input", Input).value.strip().strip("/")
        if not value:
            return

        parent = self._selected_path
        full_path = f"{parent}/{value}" if parent else value

        folders = FolderManager()
        try:
            folders.create_folder(full_path)
        except GhOrganizerError as e:
            self.notify(e.user_message, severity="error", timeout=5)
            return

        parts = full_path.split("/")
        for i in range(1, len(parts)):
            self._expanded_paths.add("/".join(parts[:i]))

        self._selected_path = full_path
        self._rebuild_tree()

        input_w = self.query_one("#folder-input", Input)
        input_w.value = ""
        input_w.placeholder = "Nombre de la nueva colección"
        self.query_one("#folder-tree", Tree).focus()
        self._update_context()

    def _confirm_rename(self) -> None:
        new_name = self.query_one("#folder-input", Input).value.strip().strip("/")
        if not new_name:
            self._cancel_special_state()
            return

        folders = FolderManager()
        old_path = self._target_path
        try:
            new_path = folders.rename_folder(old_path, new_name)
        except GhOrganizerError as e:
            self.notify(e.user_message, severity="error", timeout=4)
            self._cancel_special_state()
            return

        self._expanded_paths = {
            (new_path + p[len(old_path) :]) if p.startswith(old_path) else p
            for p in self._expanded_paths
        }
        self._selected_path = new_path
        self._cancel_special_state()
        self._rebuild_tree()

    def _confirm_delete(self) -> None:
        folders = FolderManager()
        try:
            folders.delete_folder(self._target_path)
        except GhOrganizerError as e:
            self.notify(e.user_message, severity="error", timeout=5)
            self._cancel_special_state()
            return
        self._expanded_paths = {
            p
            for p in self._expanded_paths
            if not (p == self._target_path or p.startswith(self._target_path + "/"))
        }
        self._selected_path = ""
        self._cancel_special_state()
        self._rebuild_tree()

    def _cancel_special_state(self) -> None:
        self._state = "creating"
        self._target_path = ""
        input_w = self.query_one("#folder-input", Input)
        input_w.value = ""
        input_w.placeholder = "Nombre de la nueva colección"
        self.query_one("#folder-tree", Tree).focus()
        self._update_context()
