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
        # Caché de la última carga remota
        self._cached_user_login: str = ""
        self._cached_repos: list[Repo] = []

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
    #  Acciones
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
            "Árbol reconstruido (%d repos, %d carpetas)", len(repos), len(folder_data)
        )

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
            self._build_tree()  # 👈 reconstruir sin llamar a GitHub

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
        self._build_tree()  # 👈 reconstruir sin llamar a GitHub

    def action_new_folder(self) -> None:
        from github_organizer.ui.modals import FolderModal

        logger.debug("Abriendo FolderModal (mode=create)")

        def handle_result(_result: str | None) -> None:
            self._build_tree()  # 👈 reconstruir sin llamar a GitHub

        self.app.push_screen(FolderModal(mode="create"), handle_result)

    # ------------------------------------------------------------------ #
    #  Utilidades
    # ------------------------------------------------------------------ #
    def _selected_repo(self) -> Repo | None:
        tree = self.query_one("#repo-tree", Tree)
        node = tree.cursor_node
        if node is None:
            return None
        return node.data if isinstance(node.data, Repo) else None

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
                    node = parent.add(f"{ICON_FOLDER} {parts[i - 1]}", expand=True)
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
