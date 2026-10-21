# src/gh_organizer/ui/widgets/commits_panel.py
"""Panel con los últimos commits del repositorio seleccionado."""

import logging

import requests
from github import GithubException
from textual import work
from textual.widgets import Static

from gh_organizer.core import Commit, Repo
from gh_organizer.services import GitHubClient, load_token
from gh_organizer.utils import format_date

logger = logging.getLogger(__name__)


class CommitsPanel(Static):
    """Carga y muestra los últimos 5 commits en un worker de fondo."""

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self.border_title = " Últimos commits "
        self._current_repo_full_name: str = ""
        self.show_empty()

    # ---------------------------------------------------------------- #
    #  API pública
    # ---------------------------------------------------------------- #
    def show_empty(self) -> None:
        self._current_repo_full_name = ""
        self.update(
            "[dim italic]Selecciona un repositorio para ver sus commits.[/dim italic]"
        )

    def show_for(self, repo: Repo) -> None:
        """Carga los commits del repo si no están ya cargados."""
        if self._current_repo_full_name == repo.full_name:
            return
        self._current_repo_full_name = repo.full_name
        self.update("[dim italic]⏳ Cargando commits...[/dim italic]")
        self._load_worker(repo.full_name)

    # ---------------------------------------------------------------- #
    #  Worker
    # ---------------------------------------------------------------- #
    @work(thread=True, exclusive=True, group="commits")
    def _load_worker(self, repo_full_name: str) -> None:
        token = load_token()
        if not token:
            self.app.call_from_thread(self._on_error, repo_full_name, "No hay token")
            return
        try:
            client = GitHubClient(token)
            commits = client.get_recent_commits(repo_full_name, limit=5)
            client.close()
        except GithubException as e:
            logger.warning("Error GitHub cargando commits: %s", e)
            self.app.call_from_thread(
                self._on_error, repo_full_name, f"Error GitHub: {e}"
            )
            return
        except requests.exceptions.RequestException as e:
            logger.warning("Error de red cargando commits: %s", e)
            self.app.call_from_thread(
                self._on_error, repo_full_name, f"Error de red: {e}"
            )
            return
        except Exception as e:
            logger.exception("Error inesperado cargando commits")
            self.app.call_from_thread(self._on_error, repo_full_name, f"Error: {e}")
            return

        self.app.call_from_thread(self._on_loaded, repo_full_name, commits)

    def _on_loaded(self, repo_full_name: str, commits: list[Commit]) -> None:
        if self._current_repo_full_name != repo_full_name:
            return  # el usuario cambió de repo mientras cargaba
        self._render_commits(commits)  # ← antes: self._render(commits)

    def _on_error(self, repo_full_name: str, message: str) -> None:
        if self._current_repo_full_name != repo_full_name:
            return
        self.update(f"[dim red]{message}[/dim red]")

    def _render_commits(self, commits: list[Commit]) -> None:
        if not commits:
            self.update("[dim italic]Este repositorio no tiene commits.[/dim italic]")
            return

        lines: list[str] = []
        for c in commits:
            msg = c.message
            if len(msg) > 60:
                msg = msg[:57] + "…"
            date = format_date(c.date)
            lines.append(
                f"[b cyan]{c.sha}[/b cyan]  {msg}  [dim]· {c.author} · {date}[/dim]"
            )
        self.update("\n".join(lines))
