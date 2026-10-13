# src/github_organizer/services/github.py

import logging
from typing import cast

from github import Auth, Github
from github.Commit import Commit as GHCommit  # ← el tipo real de PyGithub
from github.Repository import Repository

from github_organizer.core import Commit, GitHubUser, Repo

logger = logging.getLogger(__name__)


class GitHubClient:
    def __init__(self, token: str):
        logger.debug("Inicializando GitHubClient")
        auth = Auth.Token(token)
        self._gh = Github(auth=auth)
        logger.info("Cliente de GitHub creado correctamente")

    def close(self) -> None:
        self._gh.close()
        logger.debug("Cliente de GitHub cerrado")

    def list_repos(self) -> list[Repo]:
        """Lista los repositorios personales del usuario autenticado.

        Usa type="owner" para excluir repos de organizaciones (ej. CuCoders).
        """
        logger.info("Solicitando repositorios personales (type=owner)")
        user = self._gh.get_user()
        repos: list[Repo] = []
        for repo in user.get_repos(type="owner"):
            repos.append(self._to_repo(repo))
        logger.info("Se obtuvieron %d repositorios personales", len(repos))
        return repos

    @staticmethod
    def _to_repo(repo: Repository) -> Repo:
        return Repo(
            name=repo.name,
            full_name=repo.full_name,
            description=repo.description,
            language=repo.language,
            private=repo.private,
            html_url=repo.html_url,
            updated_at=repo.updated_at.isoformat() if repo.updated_at else "",
        )

    def get_authenticated_user(self) -> GitHubUser:
        """Devuelve el usuario autenticado, útil para confirmar el login."""
        user = self._gh.get_user()
        return GitHubUser(
            login=user.login,
            name=user.name,
            avatar_url=user.avatar_url,
        )

    def get_recent_commits(self, repo_full_name: str, limit: int = 5) -> list[Commit]:
        """Devuelve los últimos `limit` commits de un repo.

        Lanza GithubException si el repo no existe o no hay permisos.
        """
        repo = self._gh.get_repo(repo_full_name)
        commits: list[Commit] = []

        # PyGithub tipa get_commits() como PaginatedList[GithubObject] por stubs
        # incompletos. El runtime devuelve objetos Commit reales, así que
        # casteamos para que el LSP no se queje de .commit / .sha.
        gh_commits = cast("list[GHCommit]", repo.get_commits()[:limit])

        for c in gh_commits:
            git_author = c.commit.author
            author_name = git_author.name if git_author and git_author.name else "—"
            date_iso = (
                git_author.date.isoformat() if git_author and git_author.date else ""
            )
            first_line = c.commit.message.split("\n", 1)[0]
            commits.append(
                Commit(
                    sha=c.sha[:7],
                    message=first_line,
                    author=author_name,
                    date=date_iso,
                )
            )
        return commits
