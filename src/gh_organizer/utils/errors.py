# src/gh_organizer/utils/errors.py
"""Traductores de excepciones de terceros a excepciones de dominio.

Ningún ``GithubException``, ``OSError``, ``RequestException`` ni
``SubprocessError`` debe llegar a la UI: se convierten aquí primero.
"""

import logging
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager

from github import GithubException, RateLimitExceededException
from requests.exceptions import RequestException

from gh_organizer.core.exceptions import (
    ClonePermissionError,
    ConfigWriteError,
    DiskSpaceError,
    GhOrganizerError,
    GitCloneFailedError,
    InvalidTokenError,
    MissingScopeError,
    NetworkError,
    RateLimitError,
    RepoAccessError,
    TargetExistsError,
)

logger = logging.getLogger(__name__)


@contextmanager
def github_errors() -> Iterator[None]:
    """Envuelve llamadas a PyGithub y traduce lo que escape.

    Uso::

        with github_errors():
            repos = list(client.list_repos())
    """
    try:
        yield
    except GithubException as e:
        raise from_github(e) from e
    except RequestException as e:
        raise from_request(e) from e


def from_github(e: GithubException) -> GhOrganizerError:
    """Convierte una ``GithubException`` en una excepción de dominio."""
    logger.warning("GitHubException status=%s data=%s", e.status, e.data or "")

    # PyGithub ya distingue el rate limit con su propia subclase.
    if isinstance(e, RateLimitExceededException) or _is_rate_limited(e):
        return RateLimitError()

    if e.status == 401:
        return InvalidTokenError()

    if e.status == 403:
        return MissingScopeError("repo")

    if e.status == 404:
        return RepoAccessError()

    message = _github_message(e)
    return GhOrganizerError(user_message=f"❌ Error de GitHub: {message}")


def _is_rate_limited(e: GithubException) -> bool:
    headers = e.headers or {}
    if str(headers.get("x-ratelimit-remaining", "")).strip() == "0":
        return True
    return "rate limit" in _github_message(e).lower()


def _github_message(e: GithubException) -> str:
    if isinstance(e.data, dict):
        return str(e.data.get("message") or e.data)
    return str(e.data or e)


def from_request(e: RequestException) -> GhOrganizerError:
    """Convierte errores de red en una ``NetworkError``."""
    logger.warning("RequestException: %s", e)
    return NetworkError()


def from_git_clone(
    returncode: int,
    stderr: str,
    target_path: str,
) -> GhOrganizerError:
    """Analiza el stderr de ``git clone`` y devuelve una excepción específica."""
    stderr_lower = stderr.lower()

    if "no space left" in stderr_lower or "disk quota" in stderr_lower:
        return DiskSpaceError()

    if "permission denied" in stderr_lower:
        return ClonePermissionError(target_path)

    if "already exists" in stderr_lower:
        return TargetExistsError(target_path)

    detail = stderr.strip().splitlines()[0][:200] if stderr.strip() else ""
    if not detail:
        detail = f"git terminó con código {returncode}"
    return GitCloneFailedError(detail)


def from_os_error(e: OSError, context: str = "") -> GhOrganizerError:
    """Convierte ``OSError`` (subprocess, ficheros) en algo amigable."""
    logger.warning("OSError en %s: %s", context or "?", e)
    if isinstance(e, PermissionError):
        return ClonePermissionError(context)
    if e.errno == 28:  # ENOSPC
        return DiskSpaceError()
    return GhOrganizerError(user_message=f"❌ Error del sistema: {e.strerror or e}")


def from_subprocess_error(e: subprocess.SubprocessError) -> GhOrganizerError:
    """Convierte errores de ``subprocess`` en algo amigable."""
    logger.warning("SubprocessError: %s", e)
    if isinstance(e, subprocess.TimeoutExpired):
        from gh_organizer.core.exceptions import CloneTimeoutError

        return CloneTimeoutError()
    return GhOrganizerError(
        user_message="❌ Un comando externo falló. Revisa los logs para más detalles."
    )


def from_config_write(e: OSError, path: str = "") -> GhOrganizerError:
    """Convierte un fallo de escritura de configuración."""
    logger.error("No se pudo escribir la configuración (%s): %s", path or "?", e)
    return ConfigWriteError(path)
