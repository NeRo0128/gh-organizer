# src/github_organizer/ui/modals/folder_picker.py
import logging
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static, Tree
from textual.widgets.tree import TreeNode

from github_organizer.services import FolderManager
from github_organizer.ui import keybindings
from github_organizer.ui.icons import ICON_EMPTY, ICON_FOLDER
from github_organizer.ui.styles import MODALS_CSS

logger = logging.getLogger(__name__)


class FolderModal(ModalScreen[str | None]):
    """Gestor de colecciones: crear, mover, renombrar y eliminar.

    Flujo de teclado:
      ↑/↓        navegar árbol
      ←/→        colapsar / expandir (solo con foco en árbol)
      Tab        alternar foco entre árbol e input
      n          crear hija de la carpeta seleccionada
      a          crear colección en la raíz
      r          renombrar carpeta seleccionada
      d          eliminar carpeta seleccionada
      Enter      (input) crear · (árbol, modo mover) mover repo aquí
      Esc        cerrar / cancelar rename / cancelar confirmación
    """

    BINDINGS: ClassVar[list[BindingType]] = keybindings.FOLDER_PICKER

    CSS_PATH = MODALS_CSS

    def __init__(self, repo_name: str | None = None, mode: str = "move") -> None:
        """mode: 'move' (asignar repo) o 'create' (crear/editar colecciones)."""
        super().__init__()
        self.repo_name = repo_name
        self.mode = mode
        self._state: str = "creating"  # creating | renaming | confirming
        self._target_path: str = ""
        self._expanded_paths: set[str] = set()
        self._selected_path: str = ""
        self._suppress_events: bool = False
        logger.debug("FolderModal instanciada (mode=%s, repo=%s)", mode, repo_name)

    # ------------------------------------------------------------------ #
    #  Composición
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        with Center(), Vertical(id="modal-box") as box:
            if self.mode == "move":
                box.border_title = " Mover repositorio "
                yield Label(
                    f"📦 Mover [b cyan]{self.repo_name}[/b cyan] a:",
                    id="modal-title",
                )
            else:
                box.border_title = " Gestor de colecciones "
                yield Label("📁 Gestor de colecciones", id="modal-title")

            yield Tree(f"{ICON_FOLDER} Colecciones", id="folder-tree")
            yield Static("", id="context-label")
            yield Input(
                placeholder="Nombre de la nueva colección",
                id="folder-input",
            )
            yield Static("", id="hint-label")

    def on_mount(self) -> None:
        logger.debug("on_mount: modal montado (modo=%s)", self.mode)
        tree = self.query_one("#folder-tree", Tree)
        tree.show_root = True
        tree.root.data = ""
        tree.root.expand()

        # 👈 Inicializar con TODAS las carpetas expandidas
        folders = FolderManager().get_all()
        self._expanded_paths = set(folders.keys())

        self._rebuild_tree()
        tree.focus()
        logger.debug("on_mount: foco → %s", self.focused.id if self.focused else "None")

    # ------------------------------------------------------------------ #
    #  Reconstrucción del árbol
    # ------------------------------------------------------------------ #
    def _rebuild_tree(self, *, scroll: bool = True) -> None:
        """Reconstruye el árbol aplicando `_expanded_paths` y `_selected_path`.

        No sobrescribe `_expanded_paths`: eso es estado autoritativo.
        """
        logger.debug(
            "_rebuild_tree: expandidas=%s, seleccionada=%r, scroll=%s",
            self._expanded_paths,
            self._selected_path,
            scroll,
        )
        self._suppress_events = True

        tree = self.query_one("#folder-tree", Tree)
        tree.clear()
        tree.root.data = ""
        tree.root.expand()

        folders = FolderManager().get_all()
        nodes: dict[tuple, TreeNode] = {(): tree.root}

        # Filtrar expansiones que ya no existen (carpetas eliminadas)
        self._expanded_paths &= set(folders.keys())

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
            if scroll:
                tree.scroll_to_node(target)
        elif tree.root.children:
            first = tree.root.children[0]
            tree.select_node(first)
            if scroll:
                tree.scroll_to_node(first)
            if isinstance(first.data, str):
                self._selected_path = first.data
        else:
            tree.select_node(tree.root)
            self._selected_path = ""

        self._suppress_events = False
        self._update_context()

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
        # 👈 No capturamos expansión aquí: solo navegar no cambia la expansión.
        self._update_context()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Solo usado en modo 'move' para confirmar la carpeta destino."""
        if self._suppress_events:
            return
        logger.debug(
            "on_tree_node_selected: node=%r state=%s mode=%s",
            event.node.data,
            self._state,
            self.mode,
        )
        if self._state in ("renaming", "confirming"):
            return
        if self.mode == "move":
            data = event.node.data
            if isinstance(data, str) and data:
                logger.info("Moviendo repo a %r (dismiss)", data)
                self.dismiss(data)

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #
    def on_input_submitted(self, event: Input.Submitted) -> None:
        logger.debug(
            "on_input_submitted: value=%r state=%s",
            event.value,
            self._state,
        )
        if self._state == "renaming":
            self._confirm_rename()
            return
        if self._state == "confirming":
            return
        self._create_folder()

    # ------------------------------------------------------------------ #
    #  on_key
    # ------------------------------------------------------------------ #
    def on_key(self, event) -> None:
        key = event.key.lower()
        logger.debug(
            "on_key: key=%r state=%s focus=%s",
            key,
            self._state,
            self.focused.id if self.focused else "None",
        )

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

        # Navegación de árbol explícita, SOLO si el foco está en el árbol
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

    # ------------------------------------------------------------------ #
    #  Navegación manual del árbol
    # ------------------------------------------------------------------ #
    def _tree_cursor_left(self) -> None:
        """Left: colapsa si expandido; si no, sube al padre."""
        tree = self.query_one("#folder-tree", Tree)
        node = tree.cursor_node
        if node is None:
            return
        if node.children and node.is_expanded:
            node.collapse()
            if isinstance(node.data, str):
                self._expanded_paths.discard(node.data)
            logger.debug("_tree_cursor_left: colapsado %r", node.data)
        elif node.parent is not None:
            if node.parent is not tree.root or tree.show_root:
                tree.select_node(node.parent)
                logger.debug("_tree_cursor_left: subido a %r", node.parent.data)

    def _tree_cursor_right(self) -> None:
        """Right: expande si colapsado; si no, baja al primer hijo."""
        tree = self.query_one("#folder-tree", Tree)
        node = tree.cursor_node
        if node is None:
            return
        if node.children and not node.is_expanded:
            node.expand()
            if isinstance(node.data, str) and node.data:
                self._expanded_paths.add(node.data)
            logger.debug("_tree_cursor_right: expandido %r", node.data)
        elif node.children and node.is_expanded:
            tree.select_node(node.children[0])
            logger.debug("_tree_cursor_right: bajado a hijo %r", node.children[0].data)

    # ------------------------------------------------------------------ #
    #  Acciones
    # ------------------------------------------------------------------ #
    def _current_path(self) -> str:
        tree = self.query_one("#folder-tree", Tree)
        node = tree.cursor_node
        if node is None:
            return ""
        if node.data is None:
            return ""
        return node.data if isinstance(node.data, str) else ""

    def action_toggle_panel(self) -> None:
        logger.debug("action_toggle_panel")
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
        logger.debug("action_new_child_folder: padre=%r", path)
        self._selected_path = path
        input_w = self.query_one("#folder-input", Input)
        input_w.value = ""
        input_w.placeholder = (
            f"Nueva colección dentro de {path}" if path else "Nombre en la raíz"
        )
        input_w.focus()
        self._update_context()

    def action_new_root_folder(self) -> None:
        logger.debug("action_new_root_folder")
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
        logger.debug("action_rename_folder: path=%r", path)
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
        logger.debug("action_delete_folder: path=%r", path)
        if not path:
            self.notify(
                "Selecciona una carpeta (no la raíz).", severity="warning", timeout=2
            )
            return
        folders = FolderManager()
        repos, subs = folders.count_descendants(path)
        if repos == 0 and subs == 0:
            logger.info("Eliminando carpeta vacía: %r", path)
            self._delete_path(path)
            return
        self._state = "confirming"
        self._target_path = path
        self._update_context()

    def action_handle_escape(self) -> None:
        logger.debug("action_handle_escape (state=%s)", self._state)
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
            logger.debug("_create_folder: input vacío, ignorado")
            return

        parent = self._selected_path
        full_path = f"{parent}/{value}" if parent else value
        logger.info("Creando carpeta %r", full_path)

        folders = FolderManager()
        folders.create_folder(full_path)

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

        self.notify(f"📁 Creada: {full_path}", severity="information", timeout=2)

    def _confirm_rename(self) -> None:
        new_name = self.query_one("#folder-input", Input).value.strip().strip("/")
        logger.debug("_confirm_rename: new_name=%r old=%r", new_name, self._target_path)
        if not new_name:
            self._cancel_special_state()
            return

        old_path = self._target_path
        folders = FolderManager()
        try:
            new_path = folders.rename_folder(old_path, new_name)
        except (KeyError, ValueError) as e:
            logger.warning("Rename falló: %s", e)
            self.notify(f"No se pudo renombrar: {e}", severity="error", timeout=3)
            self._cancel_special_state()
            return

        # Remapear prefijos en el set de expansión
        self._expanded_paths = {
            (new_path + p[len(old_path) :]) if p.startswith(old_path) else p
            for p in self._expanded_paths
        }
        self._selected_path = new_path
        self._cancel_special_state()
        self._rebuild_tree()

        # 👈 Notificación de rename
        self.notify(
            f"✏️  Renombrada: {old_path} → {new_path}",
            severity="information",
            timeout=2,
        )

    def _delete_path(self, path: str) -> None:
        """Elimina `path` y sus descendientes, manteniendo la posición visual del árbol."""
        logger.info("Eliminando carpeta %r", path)
        folders = FolderManager()
        folders.delete_folder(path)

        # Limpiar expansiones de las rutas eliminadas
        self._expanded_paths = {
            p
            for p in self._expanded_paths
            if not (p == path or p.startswith(path + "/"))
        }

        remaining = sorted(FolderManager().get_all().keys())
        next_path: str | None = None
        for p in remaining:
            if p > path:
                next_path = p
                break
        if next_path is None and remaining:
            next_path = remaining[-1]
        self._selected_path = next_path or ""

        self._rebuild_tree(scroll=False)

        self.notify(
            f"🗑  Eliminada: {path}",
            severity="warning",
            timeout=2,
        )

    def _confirm_delete(self) -> None:
        self._delete_path(self._target_path)
        self._cancel_special_state()

    def _cancel_special_state(self) -> None:
        logger.debug("_cancel_special_state: volviendo a 'creating'")
        self._state = "creating"
        self._target_path = ""
        input_w = self.query_one("#folder-input", Input)
        input_w.value = ""
        input_w.placeholder = "Nombre de la nueva colección"
        self.query_one("#folder-tree", Tree).focus()
        self._update_context()
