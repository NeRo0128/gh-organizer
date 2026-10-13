# src/github_organizer/ui/screens/main.py
"""Pantalla principal: orquesta el árbol, el detalle y los commits."""

import logging
from typing import ClassVar

import requests
from github import GithubException
from textual import work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from github_organizer.core import Repo
from github_organizer.services import FolderManager, GitHubClient, load_token
from github_organizer.services.preferences import next_theme, save_theme
from github_organizer.ui import (
    ICON_FOLDER,
    ICON_GITHUB,
    ICON_REPO,
    ICON_WARNING,
    keybindings,
)
from github_organizer.ui.styles import MAIN_CSS
from github_organizer.ui.widgets import (
    CommitsPanel,
    RepoDetail,
    RepoHighlighted,
    RepoTree,
)

logger = logging.getLogger(__name__)


class MainScreen(Screen):
    """Pantalla principal."""

    BINDINGS: ClassVar[list[BindingType]] = keybindings.MAIN
    CSS_PATH = MAIN_CSS

    def __init__(self) -> None:
        super().__init__()
        self._cached_user_login: str = ""
        self._cached_repos: list[Repo] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("⏳ Iniciando...", id="topbar")
        with Horizontal(id="main-layout"):
            yield RepoTree(id="repo-tree")
            with Vertical(id="detail-panel"):
                yield RepoDetail(id="detail-content")
                yield CommitsPanel(id="commits-panel")
        yield Footer()

    def on_mount(self) -> None:
        logger.info("MainScreen montada")
        self.query_one(RepoTree).focus()
        self.action_reload()

    # ------------------------------------------------------------------ #
    #  Carga async
    # ------------------------------------------------------------------ #
    def action_reload(self) -> None:
        topbar = self.query_one("#topbar", Static)

        token = load_token()
        if not token:
            topbar.update("❌ No hay token. Pulsa [b]t[/b] para configurarlo.")
            return

        topbar.update("⏳ Cargando repositorios desde GitHub...")
        self.query_one(RepoDetail).show_empty()
        self.query_one(CommitsPanel).show_empty()
        logger.info("Recargando repositorios desde GitHub...")

        self._reload_worker(token)

    @work(thread=True, exclusive=True, group="reload")
    def _reload_worker(self, token: str) -> None:
        try:
            client = GitHubClient(token)
            user = client.get_authenticated_user()
            repos = client.list_repos()
            client.close()
        except GithubException as e:
            logger.warning("Error de GitHub en worker: %s", e)
            self.app.call_from_thread(self._on_reload_error, f"❌ Error de GitHub: {e}")
            return
        except requests.exceptions.RequestException as e:
            logger.warning("Error de red en worker: %s", e)
            self.app.call_from_thread(self._on_reload_error, f"🌐 Error de red: {e}")
            return
        except Exception as e:
            logger.exception("Error inesperado en worker")
            self.app.call_from_thread(self._on_reload_error, f"❌ Error: {e}")
            return

        self.app.call_from_thread(self._on_reload_success, user, repos)

    def _on_reload_success(self, user, repos: list[Repo]) -> None:
        logger.info("Worker OK: %d repos para @%s", len(repos), user.login)
        self._cached_user_login = user.login
        self._cached_repos = repos
        self._rebuild_tree()

    def _on_reload_error(self, message: str) -> None:
        self.query_one("#topbar", Static).update(message)

    # ------------------------------------------------------------------ #
    #  Reconstrucción del árbol + topbar
    # ------------------------------------------------------------------ #
    def _rebuild_tree(self) -> None:
        topbar = self.query_one("#topbar", Static)

        repos = self._cached_repos
        folder_data = FolderManager().get_all()
        assigned: set[str] = set()
        for names in folder_data.values():
            assigned.update(names)
        unassigned_count = sum(1 for r in repos if r.name not in assigned)

        self.app.sub_title = f"@{self._cached_user_login}"
        topbar.update(
            f"{ICON_GITHUB} [b]@{self._cached_user_login}[/b]   ·   "
            f"{ICON_REPO} [b]{len(repos)}[/b] repos   ·   "
            f"{ICON_FOLDER} [b]{len(folder_data)}[/b] colecciones   ·   "
            f"{ICON_WARNING} [b]{unassigned_count}[/b] sin asignar"
        )

        self.query_one(RepoTree).rebuild(repos, folder_data)

    # ------------------------------------------------------------------ #
    #  Reacción a selección en el árbol
    # ------------------------------------------------------------------ #
    def on_repo_highlighted(self, event: RepoHighlighted) -> None:
        detail = self.query_one(RepoDetail)
        commits = self.query_one(CommitsPanel)
        if event.repo is None:
            detail.show_empty()
            commits.show_empty()
        else:
            detail.show(event.repo)
            commits.show_for(event.repo)

    # ------------------------------------------------------------------ #
    #  Acciones
    # ------------------------------------------------------------------ #
    def action_set_token(self) -> None:
        from github_organizer.ui.screens import TokenScreen

        self.app.push_screen(TokenScreen())

    def action_expand_all(self) -> None:
        self.query_one(RepoTree).root.expand_all()

    def action_collapse_all(self) -> None:
        self.query_one(RepoTree).root.collapse_all()

    def action_move_repo(self) -> None:
        repo = self.query_one(RepoTree).get_selected_repo()
        if repo is None:
            self.notify(
                "Selecciona un repositorio primero.",
                severity="warning",
                timeout=3,
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
            self.query_one(RepoTree).expand_folder(folder_path)
            self._rebuild_tree()

        self.app.push_screen(
            FolderModal(repo_name=repo.name, mode="move"), handle_result
        )

    def action_unassign_repo(self) -> None:
        repo = self.query_one(RepoTree).get_selected_repo()
        if repo is None:
            self.notify(
                "Selecciona un repositorio primero.",
                severity="warning",
                timeout=3,
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
        self._rebuild_tree()

    def action_new_folder(self) -> None:
        from github_organizer.ui.modals import FolderModal

        logger.debug("Abriendo FolderModal (mode=create)")

        def handle_result(_result: str | None) -> None:
            self._rebuild_tree()

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

            tree = self.query_one(RepoTree)
            paths = tree.paths_with_content(FolderManager().get_all())
            tree.set_expanded_paths(paths)
            self._rebuild_tree()

            self.notify(
                f"📦 {moved} repos organizados en {new_folders} carpetas nuevas",
                severity="information",
                timeout=4,
            )

        self.app.push_screen(
            OrganizeModal(unassigned_count, assigned_count),
            handle_result,
        )

    def action_cycle_theme(self) -> None:
        """Cicla entre los temas disponibles y persiste la elección."""
        new = next_theme(self.app.theme)
        self.app.theme = new
        save_theme(new)
        self.notify(f"🎨 Tema: [b]{new}[/b]", timeout=2)
