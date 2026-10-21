# src/gh_organizer/ui/widgets/releases_panel.py
"""Panel con las últimas releases del repositorio seleccionado."""

import logging

import requests
from github import GithubException
from textual import work
from textual.widgets import Static

from gh_organizer.core import Release, Repo
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
            "[dim italic]Selecciona un repositorio para ver sus releases.[/dim italic]"
        )

    def show_for(self, repo: Repo) -> None:
        """Carga las releases del repo si no están ya cargadas."""
        if self._current_repo_full_name == repo.full_name:
            return
        self._current_repo_full_name = repo.full_name
        self.update("[dim italic]⏳ Cargando releases...[/dim italic]")
        self._load_worker(repo.full_name)

    # ---------------------------------------------------------------- #
    #  Worker
    # ---------------------------------------------------------------- #
    @work(thread=True, exclusive=True, group="releases")
    def _load_worker(self, repo_full_name: str) -> None:
        token = load_token()
        if not token:
            self.app.call_from_thread(self._on_error, repo_full_name, "No hay token")
            return
        try:
            client = GitHubClient(token)
            releases = client.get_releases(repo_full_name, limit=5)
            client.close()
        except GithubException as e:
            logger.warning("Error GitHub cargando releases: %s", e)
            self.app.call_from_thread(
                self._on_error, repo_full_name, f"Error GitHub: {e}"
            )
            return
        except requests.exceptions.RequestException as e:
            logger.warning("Error de red cargando releases: %s", e)
            self.app.call_from_thread(
                self._on_error, repo_full_name, f"Error de red: {e}"
            )
            return
        except Exception as e:
            logger.exception("Error inesperado cargando releases")
            self.app.call_from_thread(self._on_error, repo_full_name, f"Error: {e}")
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
                "[dim italic]Este repositorio no tiene releases publicadas.[/dim italic]"
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
