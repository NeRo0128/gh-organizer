# src/github_organizer/github_client.py
import logging
from dataclasses import dataclass

from github import Auth, Github
from github.Repository import Repository

from github_organizer.core import Repo

logger = logging.getLogger(__name__)  # Logger de nuestro módulo


@dataclass
class GitHubUser:
    login: str
    name: str | None
    avatar_url: str


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
