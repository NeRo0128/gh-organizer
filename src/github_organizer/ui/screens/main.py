# src/github_organizer/ui/screens/main.py
import logging
from typing import ClassVar

import requests
from github import GithubException
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, Tree
from textual.widgets.tree import TreeNode

from github_organizer.core import Repo
from github_organizer.services import FolderManager, GitHubClient, load_token
from github_organizer.services.tree_state import (
    DEFAULT_MODE,
    MODE_COLLAPSED,
    MODE_EXPANDED,
    load_expanded_paths,
    save_expanded_paths,
)
from github_organizer.ui import (
    ICON_EMPTY,
    ICON_FOLDER,
    ICON_GITHUB,
    ICON_GLOBE,
    ICON_LOCK,
    ICON_REPO,
    ICON_UNASSIGNED,
    ICON_WARNING,
    LANG_ICONS,
    keybindings,
)
from github_organizer.utils import format_date

logger = logging.getLogger(__name__)


class MainScreen(Screen):
    """Pantalla principal con árbol de carpetas y panel de detalle."""

    BINDINGS: ClassVar[list[BindingType]] = keybindings.MAIN

    CSS = """
    MainScreen {
        layout: vertical;
    }

    #topbar {
        height: 1;
        padding: 0 2;
        background: $boost;
        color: $text;
    }

    #main-layout {
        height: 1fr;
    }

    #repo-tree {
        width: 45%;
        border: round $primary;
        border-title-color: $accent;
        border-title-style: bold;
    }

    #detail-panel {
        width: 55%;
        border: round $accent;
        border-title-color: $accent;
        border-title-style: bold;
        padding: 1 2;
    }

    #detail-content {
        height: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._cached_user_login: str = ""
        self._cached_repos: list[Repo] = []
        self._expanded_paths: set[str] = self._init_expanded_paths()

    def _init_expanded_paths(self) -> set[str]:
        """Determina el estado inicial de expansión según el modo configurado."""
        mode = DEFAULT_MODE
        if mode == MODE_COLLAPSED:
            logger.debug("tree_state: modo collapsed")
            return set()
        if mode == MODE_EXPANDED:
            folders = set(FolderManager().get_all().keys())
            logger.debug("tree_state: modo expanded (%d rutas)", len(folders))
            return folders
        # remember
        return load_expanded_paths()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("⏳ Iniciando...", id="topbar")
        with Horizontal(id="main-layout"):
            yield Tree("Repositorios", id="repo-tree")
            with Vertical(id="detail-panel"):
                yield Static("", id="detail-content")
        yield Footer()

    def on_mount(self) -> None:
        logger.info("MainScreen montada")
        tree = self.query_one("#repo-tree", Tree)
        tree.show_root = False
        tree.border_title = " Repositorios "
        self.query_one("#detail-panel").border_title = " Detalles "
        self.query_one("#detail-content", Static).update(
            "[dim italic]Selecciona un repositorio para ver sus detalles.[/dim italic]"
        )
        tree.focus()
        self.action_reload()

    # ------------------------------------------------------------------ #
    #  Carga de datos
    # ------------------------------------------------------------------ #
    def action_reload(self) -> None:
        """Descarga repos de GitHub y reconstruye el árbol."""
        topbar = self.query_one("#topbar", Static)
        detail = self.query_one("#detail-content", Static)

        token = load_token()
        if not token:
            topbar.update("❌ No hay token. Pulsa [b]t[/b] para configurarlo.")
            return

        topbar.update("⏳ Cargando repositorios desde GitHub...")
        detail.update("[dim italic]Cargando...[/dim italic]")
        logger.info("Recargando repositorios desde GitHub...")

        try:
            client = GitHubClient(token)
            user = client.get_authenticated_user()
            repos = client.list_repos()
            client.close()
        except GithubException as e:
            logger.warning("Error de GitHub: %s", e)
            topbar.update(f"❌ Error de GitHub: {e}")
            return
        except requests.exceptions.RequestException as e:
            logger.warning("Error de red: %s", e)
            topbar.update(f"🌐 Error de red: {e}")
            return

        self._cached_user_login = user.login
        self._cached_repos = repos
        self._build_tree()

    # ------------------------------------------------------------------ #
    #  Construcción del árbol
    # ------------------------------------------------------------------ #
    def _build_tree(self) -> None:
        """Reconstruye el árbol usando la caché de repos (sin llamar a GitHub)."""
        topbar = self.query_one("#topbar", Static)
        tree = self.query_one("#repo-tree", Tree)
        detail = self.query_one("#detail-content", Static)

        tree.clear()
        detail.update(
            "[dim italic]Selecciona un repositorio para ver sus detalles.[/dim italic]"
        )

        repos = self._cached_repos
        folders = FolderManager()
        folder_data = folders.get_all()
        assigned = folders.get_assigned_repo_names()
        unassigned = [r for r in repos if r.name not in assigned]
        repos_by_name = {r.name: r for r in repos}

        self.app.sub_title = f"@{self._cached_user_login}"

        topbar.update(
            f"{ICON_GITHUB} [b]@{self._cached_user_login}[/b]   ·   "
            f"{ICON_REPO} [b]{len(repos)}[/b] repos   ·   "
            f"{ICON_FOLDER} [b]{len(folder_data)}[/b] colecciones   ·   "
            f"{ICON_WARNING} [b]{len(unassigned)}[/b] sin asignar"
        )

        # Limpieza: descartar rutas que ya no existen (incluye padres implícitos)
        self._expanded_paths &= self._all_valid_paths(folder_data)

        # Persistir el estado actual
        save_expanded_paths(self._expanded_paths)

        if unassigned:
            unassigned_node = tree.root.add(
                f"{ICON_UNASSIGNED} Sin asignar [dim]({len(unassigned)})[/dim]",
                expand=True,
            )
            for repo in sorted(unassigned, key=lambda r: r.name.lower()):
                unassigned_node.add_leaf(self._repo_label(repo), data=repo)

        if folder_data:
            folder_root = tree.root.add(
                f"{ICON_FOLDER} Colecciones [dim]({len(folder_data)})[/dim]",
                expand=True,
            )
            self._build_folder_tree(folder_root, folder_data, repos_by_name)

        tree.border_title = f" Repositorios · {len(repos)} "
        logger.debug(
            "Árbol reconstruido (%d repos, %d carpetas, %d expandidas)",
            len(repos),
            len(folder_data),
            len(self._expanded_paths),
        )

    def _build_folder_tree(
        self,
        root: TreeNode,
        folder_data: dict[str, list[str]],
        repos_by_name: dict[str, Repo],
    ) -> None:
        nodes: dict[tuple, TreeNode] = {(): root}
        for path in sorted(folder_data.keys()):
            parts = path.split("/")
            for i in range(1, len(parts) + 1):
                partial = tuple(parts[:i])
                if partial not in nodes:
                    parent = nodes[partial[:-1]]
                    full_path = "/".join(parts[:i])
                    node = parent.add(
                        f"{ICON_FOLDER} {parts[i - 1]}",
                        expand=full_path in self._expanded_paths,
                    )
                    node.data = full_path  # guardar ruta para on_key
                    nodes[partial] = node

            folder_node = nodes[tuple(parts)]
            repos_in = folder_data[path]
            if not repos_in:
                folder_node.add_leaf(f"[dim italic]{ICON_EMPTY} (vacía)[/dim italic]")
                continue
            for repo_name in repos_in:
                repo = repos_by_name.get(repo_name)
                if repo:
                    folder_node.add_leaf(self._repo_label(repo), data=repo)
                else:
                    folder_node.add_leaf(f"[dim]? {repo_name} (no encontrado)[/dim]")

    @staticmethod
    def _repo_label(repo: Repo) -> str:
        icon_char = LANG_ICONS.get(repo.language or "", ICON_REPO)
        lock = f" [yellow]{ICON_LOCK}[/yellow]" if repo.private else ""
        return f"{icon_char} {repo.name}{lock}"

    @staticmethod
    def _all_valid_paths(folder_data: dict[str, list[str]]) -> set[str]:
        """Todas las rutas válidas, incluyendo padres implícitos.

        Un padre es implícito si aparece solo como prefijo de otra clave.
        Ej: 'Lenguajes' cuando la clave real es 'Lenguajes/Python'.
        """
        paths: set[str] = set()
        for path in folder_data:
            parts = path.split("/")
            for i in range(1, len(parts) + 1):
                paths.add("/".join(parts[:i]))
        return paths

    @staticmethod
    def _compute_paths_with_content(folder_data: dict[str, list[str]]) -> set[str]:
        """Rutas que deben expandirse por tener contenido.

        Una carpeta "tiene contenido" si tiene repos directamente o algún
        descendiente con repos. Los ancestros de esas carpetas también se
        incluyen para que la descendencia sea visible.
        """
        paths: set[str] = set()
        for path, repos in folder_data.items():
            if not repos:
                continue
            parts = path.split("/")
            for i in range(1, len(parts) + 1):
                paths.add("/".join(parts[:i]))
        return paths

    # ------------------------------------------------------------------ #
    #  Navegación explícita del árbol (left/right)
    # ------------------------------------------------------------------ #
    def on_key(self, event) -> None:
        tree = self.query_one("#repo-tree", Tree)
        if not tree.has_focus:
            return

        key = event.key.lower()
        if key == "left":
            event.stop()
            self._tree_cursor_left()
        elif key == "right":
            event.stop()
            self._tree_cursor_right()

    def _tree_cursor_left(self) -> None:
        """Left: colapsa si expandido; si no, sube al padre."""
        tree = self.query_one("#repo-tree", Tree)
        node = tree.cursor_node
        if node is None:
            return
        if node.children and node.is_expanded:
            node.collapse()
            if isinstance(node.data, str) and node.data:
                self._expanded_paths.discard(node.data)
                save_expanded_paths(self._expanded_paths)
        elif node.parent is not None and node.parent is not tree.root:
            tree.select_node(node.parent)

    def _tree_cursor_right(self) -> None:
        """Right: expande si colapsado; si no, baja al primer hijo."""
        tree = self.query_one("#repo-tree", Tree)
        node = tree.cursor_node
        if node is None:
            return
        if node.children and not node.is_expanded:
            node.expand()
            if isinstance(node.data, str) and node.data:
                self._expanded_paths.add(node.data)
                save_expanded_paths(self._expanded_paths)
        elif node.children and node.is_expanded:
            tree.select_node(node.children[0])

    # ------------------------------------------------------------------ #
    #  Acciones
    # ------------------------------------------------------------------ #
    def action_set_token(self) -> None:
        from github_organizer.ui.screens import TokenScreen

        self.app.push_screen(TokenScreen())

    def action_expand_all(self) -> None:
        self.query_one("#repo-tree", Tree).root.expand_all()

    def action_collapse_all(self) -> None:
        self.query_one("#repo-tree", Tree).root.collapse_all()

    def action_move_repo(self) -> None:
        repo = self._selected_repo()
        if repo is None:
            self.notify(
                "Selecciona un repositorio primero.", severity="warning", timeout=3
            )
            return

        from github_organizer.ui.modals import FolderModal

        logger.debug("Abriendo FolderModal (mode=move, repo=%s)", repo.name)

        def handle_result(folder_path: str | None) -> None:
            if folder_path is None:
                return
            folders = FolderManager()
            folders.create_folder(folder_path)
            folders.assign_repo(repo.name, folder_path)
            self.notify(
                f"{ICON_FOLDER} {repo.name} → {folder_path}",
                severity="information",
                timeout=3,
            )
            # Expandir la ruta destino
            if folder_path:
                parts = folder_path.split("/")
                for i in range(1, len(parts) + 1):
                    self._expanded_paths.add("/".join(parts[:i]))
            self._build_tree()

        self.app.push_screen(
            FolderModal(repo_name=repo.name, mode="move"), handle_result
        )

    def action_unassign_repo(self) -> None:
        repo = self._selected_repo()
        if repo is None:
            self.notify(
                "Selecciona un repositorio primero.", severity="warning", timeout=3
            )
            return

        folders = FolderManager()
        if repo.name not in folders.get_assigned_repo_names():
            self.notify(
                f"{repo.name} no está asignado a ninguna carpeta.",
                severity="warning",
                timeout=3,
            )
            return

        folders.remove_repo(repo.name)
        self.notify(
            f"↩  {repo.name} devuelto a 'Sin asignar'",
            severity="information",
            timeout=3,
        )
        self._build_tree()

    def action_new_folder(self) -> None:
        from github_organizer.ui.modals import FolderModal

        logger.debug("Abriendo FolderModal (mode=create)")

        def handle_result(_result: str | None) -> None:
            self._build_tree()

        self.app.push_screen(FolderModal(mode="create"), handle_result)

    def action_organize(self) -> None:
        from github_organizer.services.organizer import STRATEGIES
        from github_organizer.ui.modals import OrganizeModal

        if not self._cached_repos:
            self.notify(
                "Carga los repositorios primero (pulsa r).",
                severity="warning",
                timeout=3,
            )
            return

        folders = FolderManager()
        assigned = folders.get_assigned_repo_names()
        unassigned_count = sum(1 for r in self._cached_repos if r.name not in assigned)
        assigned_count = len(assigned)

        if unassigned_count == 0:
            self.notify(
                "No hay repos sin asignar.",
                severity="information",
                timeout=3,
            )
            return

        logger.debug(
            "Abriendo OrganizeModal (sin asignar=%d, asignados=%d)",
            unassigned_count,
            assigned_count,
        )

        def handle_result(index: int | None) -> None:
            if index is None:
                return
            _name, strategy_fn, _desc = STRATEGIES[index]
            moved, new_folders = folders.apply_strategy(self._cached_repos, strategy_fn)
            if moved == 0:
                self.notify(
                    "No había repos sin asignar para organizar.",
                    severity="information",
                    timeout=3,
                )
                return

            # Expandir solo las rutas con contenido (las vacías quedan colapsadas)
            paths_with_content = self._compute_paths_with_content(
                FolderManager().get_all()
            )
            self._expanded_paths = paths_with_content
            self._build_tree()

            self.notify(
                f"📦 {moved} repos organizados en {new_folders} carpetas nuevas",
                severity="information",
                timeout=4,
            )

        self.app.push_screen(
            OrganizeModal(unassigned_count, assigned_count),
            handle_result,
        )

    # ------------------------------------------------------------------ #
    #  Utilidades
    # ------------------------------------------------------------------ #
    def _selected_repo(self) -> Repo | None:
        tree = self.query_one("#repo-tree", Tree)
        node = tree.cursor_node
        if node is None:
            return None
        return node.data if isinstance(node.data, Repo) else None

    # ------------------------------------------------------------------ #
    #  Detalle
    # ------------------------------------------------------------------ #
    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        self._update_detail(event.node)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        self._update_detail(event.node)

    def _update_detail(self, node: TreeNode) -> None:
        detail = self.query_one("#detail-content", Static)
        data = node.data
        if not isinstance(data, Repo):
            detail.update(
                "[dim italic]Selecciona un repositorio para ver sus detalles.[/dim italic]"
            )
            return

        icon_char = LANG_ICONS.get(data.language or "", ICON_REPO)
        lang = f"{icon_char} {data.language}" if data.language else "[dim]—[/dim]"
        visibility = f"{ICON_LOCK} Privado" if data.private else f"{ICON_GLOBE} Público"
        updated = format_date(data.updated_at)
        description = (
            data.description
            if data.description
            else "[dim italic]Sin descripción[/dim italic]"
        )

        detail.update(
            f"[b cyan]{icon_char} {data.name}[/b cyan]\n"
            f"\n"
            f"{description}\n"
            f"\n"
            f"[dim]{'─' * 40}[/dim]\n"
            f"\n"
            f"[b]Lenguaje     [/b]  {lang}\n"
            f"[b]Visibilidad  [/b]  {visibility}\n"
            f"[b]Actualizado  [/b]  {updated}\n"
            f"[b]Ruta         [/b]  [dim]{data.full_name}[/dim]\n"
            f"\n"
            f"[b]URL          [/b]  [u cyan]{data.html_url}[/u cyan]\n"
        )
