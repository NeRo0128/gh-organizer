# src/github_organizer/models.py
from dataclasses import dataclass, field


@dataclass
class GitHubUser:
    login: str
    name: str | None = None
    avatar_url: str = ""


@dataclass
class Repo:
    """Representa un repositorio de GitHub."""

    name: str
    full_name: str  # "usuario/repo"
    description: str | None = None
    language: str | None = None
    private: bool = False
    html_url: str = ""
    updated_at: str = ""  # ISO 8601


@dataclass
class Folder:
    """Representa una carpeta personalizada del usuario."""

    path: str  # "Trabajo/Negocios/Web"
    repos: list[str] = field(default_factory=list)  # nombres de repos
