# src/gh_organizer/ui/widgets/releases_panel.py
"""Panel con las últimas releases del repositorio seleccionado."""

import logging

from textual import work
from textual.widgets import Static

from gh_organizer.core import Release, Repo
from gh_organizer.core.exceptions import GhOrganizerError, MissingTokenError
from gh_organizer.i18n import _
from gh_organizer.services import GitHubClient, load_token
from gh_organizer.utils import format_date

logger = logging.getLogger(__name__)


class ReleasesPanel(Static):
    """Carga y muestra las últimas 5 releases en un worker de fondo."""

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self.border_title = " Releases "
        self._current_repo_full_name: str = ""
        self.show_empty()

    # ---------------------------------------------------------------- #
    #  API pública
    # ---------------------------------------------------------------- #
    def show_empty(self) -> None:
        self._current_repo_full_name = ""
        self.update(
            f"[dim italic]{_('Selecciona un repositorio para ver sus releases.')}[/dim italic]"
        )

    def show_for(self, repo: Repo) -> None:
        """Carga las releases del repo si no están ya cargadas."""
        if self._current_repo_full_name == repo.full_name:
            return
        self._current_repo_full_name = repo.full_name
        self.update(f"[dim italic]⏳ {_('Cargando releases...')}[/dim italic]")
        self._load_worker(repo.full_name)

    # ---------------------------------------------------------------- #
    #  Worker
    # ---------------------------------------------------------------- #
    @work(thread=True, exclusive=True, group="releases")
    def _load_worker(self, repo_full_name: str) -> None:
        try:
            token = load_token()
            if not token:
                raise MissingTokenError()
            client = GitHubClient(token)
            try:
                releases = client.get_releases(repo_full_name, limit=5)
            finally:
                client.close()
        except GhOrganizerError as e:
            logger.warning("Error cargando releases de %s: %s", repo_full_name, e)
            self.app.call_from_thread(self._on_error, repo_full_name, e.localized_message)
            return
        except Exception:
            logger.exception("Error inesperado cargando releases")
            self.app.call_from_thread(
                self._on_error, repo_full_name, GhOrganizerError().localized_message
            )
            return

        self.app.call_from_thread(self._on_loaded, repo_full_name, releases)

    def _on_loaded(self, repo_full_name: str, releases: list[Release]) -> None:
        if self._current_repo_full_name != repo_full_name:
            return  # el usuario cambió de repo mientras cargaba
        self._render_releases(releases)

    def _on_error(self, repo_full_name: str, message: str) -> None:
        if self._current_repo_full_name != repo_full_name:
            return
        self.update(f"[dim red]{message}[/dim red]")

    # ---------------------------------------------------------------- #
    #  Render
    # ---------------------------------------------------------------- #
    def _render_releases(self, releases: list[Release]) -> None:
        if not releases:
            self.update(
                f"[dim italic]{_('Este repositorio no tiene releases publicadas.')}[/dim italic]"
            )
            return

        lines: list[str] = []
        for idx, r in enumerate(releases):
            badges: list[str] = []
            if r.prerelease:
                badges.append("[magenta]pre-release[/magenta]")
            elif idx == 0:
                badges.append("[yellow]Latest[/yellow]")

            date = format_date(r.published_at)
            name = self._truncate(r.name)
            badge_str = " · ".join(badges)
            meta = f"[dim]· {date}[/dim]"
            if badge_str:
                meta = f"[dim]·[/dim] {badge_str} [dim]· {date}[/dim]"

            lines.append(f"[b cyan]{name}[/b cyan]  {meta}")
            if r.body:
                lines.append(f"  [dim]{r.body}[/dim]")

        self.update("\n".join(lines))

    # ---------------------------------------------------------------- #
    #  Utilidades
    # ---------------------------------------------------------------- #
    @staticmethod
    def _truncate(text: str, max_len: int = 80) -> str:
        """Trunca un texto largo añadiendo '…' al final."""
        return text if len(text) <= max_len else text[: max_len - 1] + "…"
