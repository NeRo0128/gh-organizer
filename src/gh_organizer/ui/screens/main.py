# src/gh_organizer/ui/screens/main.py
"""Pantalla principal: orquesta el árbol, el detalle y los commits."""

import logging
import webbrowser
from pathlib import Path
from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Header, Input, Static
from textual.worker import get_current_worker

from gh_organizer.core import Repo
from gh_organizer.core.exceptions import (
    GhOrganizerError,
    GitNotInstalledError,
    MissingTokenError,
)
from gh_organizer.i18n import _
from gh_organizer.services import (
    FolderManager,
    GitHubClient,
    load_token,
    preferences,
)
from gh_organizer.services import config as config_service
from gh_organizer.services import git as git_service
from gh_organizer.ui import (
    ICON_FOLDER,
    ICON_GITHUB,
    ICON_REPO,
    ICON_WARNING,
    keybindings,
)
from gh_organizer.ui.styles import MAIN_CSS
from gh_organizer.ui.widgets import (
    CommitsPanel,
    ReleasesPanel,
    RepoActivated,
    RepoDetail,
    RepoHighlighted,
    RepoTree,
    StatusBar,
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
        yield Static(f"⏳ {_('Iniciando...')}", id="topbar", classes="screen-topbar")
        with Horizontal(id="main-layout"):
            with Vertical(id="tree-panel"):
                yield Input(placeholder=f"🔍 {_('Buscar repo...')}", id="search-input")
                yield RepoTree(id="repo-tree")
            with Vertical(id="detail-panel"):
                with Horizontal(id="detail-row"):
                    yield RepoDetail(id="detail-content")
                    yield ReleasesPanel(id="releases-panel")
                yield CommitsPanel(id="commits-panel")
        yield StatusBar(id="statusbar")

    def on_mount(self) -> None:
        logger.info("MainScreen montada")
        # Ocultar el input de búsqueda por defecto
        self.query_one("#search-input", Input).display = False
        # Si el config.toml estaba corrupto en el arranque, avisar una sola vez.
        config_error = config_service.consume_last_error()
        if config_error is not None:
            self.notify(
                config_error.localized_message,
                severity="warning",
                timeout=8,
            )
        self.query_one(RepoTree).focus()
        self.action_reload()

    # ------------------------------------------------------------------ #
    #  Cambio de idioma en caliente
    # ------------------------------------------------------------------ #
    def on_screen_resume(self) -> None:
        """Se ejecuta al volver a esta pantalla (p. ej. al cerrar Ajustes).

        Si el idioma cambió, se recompone para que los textos estáticos del
        compose (placeholders, títulos…) aparezcan en el idioma nuevo.
        """
        if not getattr(self.app, "i18n_dirty", False):
            return
        self.app.i18n_dirty = False
        self.refresh(recompose=True)
        self.call_after_refresh(self._after_recompose)

    def _after_recompose(self) -> None:
        # compose() ha recreado los widgets: hay que devolver el estado inicial
        # sin volver a pedir datos a GitHub.
        self.query_one("#search-input", Input).display = False
        self.query_one(RepoTree).focus()
        self._rebuild_tree()

    # ------------------------------------------------------------------ #
    #  Carga async
    # ------------------------------------------------------------------ #
    def action_reload(self) -> None:
        self.query_one(StatusBar).set_status(f"⏳ {_('Cargando repositorios...')}")
        self._fetch_repos()

    @work(thread=True, exclusive=True, group="reload", exit_on_error=False)
    def _fetch_repos(self) -> None:
        worker = get_current_worker()
        try:
            token = load_token()
            if not token:
                raise MissingTokenError()

            client = GitHubClient(token)
            try:
                user = client.get_authenticated_user()
                repos = client.list_repos()
            finally:
                client.close()
        except GhOrganizerError as e:
            logger.warning("Error de dominio cargando repos: %s", e)
            if not worker.is_cancelled:
                self.app.call_from_thread(self._on_reload_error, e.localized_message)
            return
        except Exception:
            logger.exception("Error inesperado en worker")
            if not worker.is_cancelled:
                self.app.call_from_thread(
                    self._on_reload_error, GhOrganizerError().localized_message
                )
            return

        if worker.is_cancelled:
            return
        self.app.call_from_thread(self._on_reload_success, user.login, repos)

    def _on_reload_success(self, login: str, repos: list[Repo]) -> None:
        self._cached_user_login = login
        self._cached_repos = repos
        self._rebuild_tree()
        self.query_one(StatusBar).set_status(
            f"✅ {_('%(count)s repos cargados') % {'count': len(repos)}}"
        )

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
            f"{ICON_REPO} [b]{len(repos)}[/b] {_('repos')}   ·   "
            f"{ICON_FOLDER} [b]{len(folder_data)}[/b] {_('colecciones')}   ·   "
            f"{ICON_WARNING} [b]{unassigned_count}[/b] {_('sin asignar')}"
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
                _("🔒 El repositorio es privado. Ábrelo manualmente en GitHub."),
                severity="warning",
                timeout=4,
            )
            return

        webbrowser.open(event.repo.html_url)
        self.notify(_("🌐 Abriendo %(name)s") % {"name": event.repo.name}, timeout=2)

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
                _("Selecciona un repositorio primero."),
                severity="warning",
                timeout=3,
            )
            return

        # Feedback inmediato: no lanzamos un worker que va a fallar seguro.
        try:
            git_service.ensure_git_available()
        except GitNotInstalledError as e:
            self.notify(e.localized_message, severity="error", timeout=6)
            return

        clone_dir_str = preferences.get("clone_dir", "~/github")
        clone_dir = Path(clone_dir_str).expanduser()
        target = clone_dir / repo.name

        if target.exists():
            self.notify(
                _("📂 Ya existe en %(path)s") % {"path": target},
                severity="warning",
                timeout=3,
            )
            return

        self.notify(_("⏳ Clonando %(name)s...") % {"name": repo.name}, timeout=3)
        self._clone_worker(repo.html_url, target, repo.name)

    @work(thread=True, exclusive=True, group="clone")
    def _clone_worker(self, url: str, target: Path, name: str) -> None:
        try:
            cloned_to = git_service.clone_repo(url, target)
        except GhOrganizerError as e:
            logger.warning("Fallo clonando %s: %s", name, e)
            self.app.call_from_thread(
                self.notify, e.localized_message, severity="error", timeout=6
            )
            return
        except Exception:
            logger.exception("Error inesperado clonando %s", name)
            self.app.call_from_thread(
                self.notify,
                GhOrganizerError().localized_message,
                severity="error",
                timeout=6,
            )
            return

        self.app.call_from_thread(
            self.notify,
            _("✅ %(name)s clonado en %(path)s") % {"name": name, "path": cloned_to},
            timeout=4,
        )

    # ------------------------------------------------------------------ #
    #  Acciones de carpetas
    # ------------------------------------------------------------------ #
    def action_set_token(self) -> None:
        from gh_organizer.ui.screens import TokenScreen

        self.app.push_screen(TokenScreen())

    def action_open_settings(self) -> None:
        from gh_organizer.ui.screens import SettingsScreen

        self.app.push_screen(SettingsScreen())

    def action_expand_all(self) -> None:
        self.query_one(RepoTree).root.expand_all()

    def action_collapse_all(self) -> None:
        self.query_one(RepoTree).root.collapse_all()

    def action_move_repo(self) -> None:
        repo = self.query_one(RepoTree).get_selected_repo()
        if repo is None:
            self.notify(
                _("Selecciona un repositorio primero."),
                severity="warning",
                timeout=3,
            )
            return

        from gh_organizer.ui.modals import FolderModal

        logger.debug("Abriendo FolderModal (mode=move, repo=%s)", repo.name)

        def handle_result(folder_path: str | None) -> None:
            if folder_path is None:
                return
            try:
                folders = FolderManager()
                folders.create_folder(folder_path)
                folders.assign_repo(repo.name, folder_path)
            except GhOrganizerError as e:
                self.notify(e.localized_message, severity="error", timeout=5)
                return
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
                _("Selecciona un repositorio primero."),
                severity="warning",
                timeout=3,
            )
            return

        folders = FolderManager()
        if repo.name not in folders.get_assigned_repo_names():
            self.notify(
                _("%(name)s no está asignado a ninguna carpeta.") % {"name": repo.name},
                severity="warning",
                timeout=3,
            )
            return

        try:
            folders.remove_repo(repo.name)
        except GhOrganizerError as e:
            self.notify(e.localized_message, severity="error", timeout=5)
            return

        self.notify(
            _("↩  %(name)s devuelto a 'Sin asignar'") % {"name": repo.name},
            severity="information",
            timeout=3,
        )
        self._rebuild_tree()

    def action_new_folder(self) -> None:
        from gh_organizer.ui.modals import FolderModal

        logger.debug("Abriendo FolderModal (mode=create)")

        def handle_result(_result: str | None) -> None:
            self._rebuild_tree()

        self.app.push_screen(FolderModal(mode="create"), handle_result)

    def action_organize(self) -> None:
        from gh_organizer.services.organizer import STRATEGIES
        from gh_organizer.ui.modals import OrganizeModal

        if not self._cached_repos:
            self.notify(
                _("Carga los repositorios primero (pulsa r)."),
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
                _("No hay repos sin asignar."),
                severity="information",
                timeout=3,
            )
            return

        def handle_result(index: int | None) -> None:
            if index is None:
                return
            _name, strategy_fn, _desc = STRATEGIES[index]
            try:
                moved, new_folders = folders.apply_strategy(
                    self._cached_repos, strategy_fn
                )
            except GhOrganizerError as e:
                self.notify(e.localized_message, severity="error", timeout=6)
                return
            if moved == 0:
                self.notify(
                    _("No había repos sin asignar para organizar."),
                    severity="information",
                    timeout=3,
                )
                return

            tree = self.query_one(RepoTree)
            paths = tree.paths_with_content(FolderManager().get_all())
            tree.set_expanded_paths(paths)
            self._rebuild_tree()

            self.notify(
                _("📦 %(moved)s repos organizados en %(folders)s carpetas nuevas")
                % {"moved": moved, "folders": new_folders},
                severity="information",
                timeout=4,
            )

        self.app.push_screen(
            OrganizeModal(unassigned_count, assigned_count),
            handle_result,
        )

    def action_cycle_theme(self) -> None:
        from gh_organizer.services.preferences import next_theme, save_theme

        new = next_theme(self.app.theme)
        self.app.theme = new
        try:
            save_theme(new)
        except GhOrganizerError as e:
            self.notify(e.localized_message, severity="warning", timeout=5)
            return
        self.notify(_("🎨 Tema: [b]%(theme)s[/b]") % {"theme": new}, timeout=2)

    def action_show_help(self) -> None:
        """Abre el modal de ayuda con todos los atajos de teclado."""
        from gh_organizer.ui.modals import HelpModal

        logger.debug("Abriendo HelpModal")
        self.app.push_screen(HelpModal())
