# src/github_organizer/ui/screens/main.py
"""Pantalla principal: orquesta el árbol, el detalle y los commits."""

import logging
import webbrowser
from pathlib import Path
from typing import ClassVar

import requests
from github import GithubException
from textual import work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Static
from textual.worker import get_current_worker

from github_organizer.core import Repo
from github_organizer.services import (
    FolderManager,
    GitHubClient,
    load_token,
    preferences,
)
from github_organizer.ui import (
    ICON_FOLDER,
    ICON_GITHUB,
    ICON_REPO,
    ICON_SEARCH,
    ICON_WARNING,
    keybindings,
)
from github_organizer.ui.styles import MAIN_CSS
from github_organizer.ui.widgets import (
    CommitsPanel,
    ReleasesPanel,
    RepoActivated,
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
        yield Static("⏳ Iniciando...", id="topbar", classes="screen-topbar")
        with Horizontal(id="main-layout"):
            with Vertical(id="tree-panel"):
                yield Input(
                    placeholder=f"{ICON_SEARCH} Buscar repo...", id="search-input"
                )
                yield RepoTree(id="repo-tree")
            with Vertical(id="detail-panel"):
                with Horizontal(id="detail-row"):
                    yield RepoDetail(id="detail-content")
                    yield ReleasesPanel(id="releases-panel")
                yield CommitsPanel(id="commits-panel")
        yield Footer()

    def on_mount(self) -> None:
        logger.info("MainScreen montada")
        # Ocultar el input de búsqueda por defecto
        self.query_one("#search-input", Input).display = False
        self.query_one(RepoTree).focus()
        self.action_reload()

    # ------------------------------------------------------------------ #
    #  Carga async
    # ------------------------------------------------------------------ #
    def action_reload(self) -> None:
        self.query_one("#topbar", Static).update("⏳ Cargando repositorios...")
        self._fetch_repos()

    @work(thread=True, exclusive=True, group="reload", exit_on_error=False)
    def _fetch_repos(self) -> None:
        worker = get_current_worker()
        token = load_token()
        if not token:
            self.app.call_from_thread(
                self._on_reload_error,
                "❌ No hay token. Pulsa [b]t[/b] para configurarlo.",
            )
            return
        try:
            client = GitHubClient(token)
            user = client.get_authenticated_user()
            repos = client.list_repos()
            client.close()
        except GithubException as e:
            logger.warning("Error de GitHub en worker: %s", e)
            if not worker.is_cancelled:
                self.app.call_from_thread(self._on_reload_error, f"❌ GitHub: {e}")
            return
        except requests.exceptions.RequestException as e:
            logger.warning("Error de red en worker: %s", e)
            if not worker.is_cancelled:
                self.app.call_from_thread(self._on_reload_error, f"🌐 Red: {e}")
            return
        except Exception as e:
            logger.exception("Error inesperado en worker")
            if not worker.is_cancelled:
                self.app.call_from_thread(self._on_reload_error, f"❌ {e}")
            return

        if worker.is_cancelled:
            return
        self.app.call_from_thread(self._on_reload_success, user.login, repos)

    def _on_reload_success(self, login: str, repos: list[Repo]) -> None:
        logger.info("Worker OK: %d repos para @%s", len(repos), login)
        self._cached_user_login = login
        self._cached_repos = repos
        self._rebuild_tree()

    def _on_reload_error(self, message: str) -> None:
        self.query_one("#topbar", Static).update(message)

    # ------------------------------------------------------------------ #
    #  Reconstrucción
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
        releases = self.query_one(ReleasesPanel)
        commits = self.query_one(CommitsPanel)
        if event.repo is None:
            detail.show_empty()
            releases.show_empty()
            commits.show_empty()
        else:
            detail.show(event.repo)
            releases.show_for(event.repo)
            commits.show_for(event.repo)

    def on_key(self, event) -> None:
        """Maneja atajos a nivel de pantalla."""
        # Si se pulsa Esc y el input de búsqueda está visible
        if event.key == "escape":
            input_w = self.query_one("#search-input", Input)
            if input_w.display:
                event.stop()  # Evitar que el Esc haga otra cosa
                self.action_search()  # action_search ya alterna: borra, oculta y enfoca el árbol
                return

    def on_repo_activated(self, event: RepoActivated) -> None:
        """Enter sobre un repo → abrir en navegador (solo si es público)."""
        if event.repo.private:
            self.notify(
                "🔒 El repositorio es privado. Ábrelo manualmente en GitHub.",
                severity="warning",
                timeout=4,
            )
            return

        webbrowser.open(event.repo.html_url)
        self.notify(f"🌐 Abriendo {event.repo.name}", timeout=2)

    # ------------------------------------------------------------------ #
    #  Búsqueda
    # ------------------------------------------------------------------ #
    def action_search(self) -> None:
        input_w = self.query_one("#search-input", Input)
        if input_w.display:
            input_w.value = ""
            input_w.display = False
            self.query_one(RepoTree).focus()
        else:
            input_w.display = True
            input_w.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.query_one(RepoTree).filter(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            self.query_one(RepoTree).focus()

    # ------------------------------------------------------------------ #
    #  Clonar
    # ------------------------------------------------------------------ #
    def action_clone_repo(self) -> None:
        repo = self.query_one(RepoTree).get_selected_repo()
        if repo is None:
            self.notify(
                "Selecciona un repositorio primero.",
                severity="warning",
                timeout=3,
            )
            return

        clone_dir_str = preferences.get("clone_dir", "~/github")
        clone_dir = Path(clone_dir_str).expanduser()
        target = clone_dir / repo.name

        if target.exists():
            self.notify(f"📂 Ya existe en {target}", severity="warning", timeout=3)
            return

        self.notify(f"⏳ Clonando {repo.name}...", timeout=3)
        self._clone_worker(repo.html_url, target, repo.name)

    @work(thread=True, exclusive=True, group="clone")
    def _clone_worker(self, url: str, target: Path, name: str) -> None:
        from github_organizer.services import git

        ok, msg = git.clone_repo(url, target)
        if ok:
            self.app.call_from_thread(self.notify, f"✅ {name}: {msg}", timeout=4)
        else:
            self.app.call_from_thread(
                self.notify, f"❌ {name}: {msg}", severity="error", timeout=5
            )

    # ------------------------------------------------------------------ #
    #  Acciones de carpetas
    # ------------------------------------------------------------------ #
    def action_set_token(self) -> None:
        from github_organizer.ui.screens import TokenScreen

        self.app.push_screen(TokenScreen())

    def action_open_settings(self) -> None:
        from github_organizer.ui.screens import SettingsScreen

        self.app.push_screen(SettingsScreen())

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
        from github_organizer.services.preferences import next_theme, save_theme

        new = next_theme(self.app.theme)
        self.app.theme = new
        save_theme(new)
        self.notify(f"🎨 Tema: [b]{new}[/b]", timeout=2)
