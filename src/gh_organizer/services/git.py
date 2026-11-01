# src/gh_organizer/services/git.py
"""Operaciones locales con git.

``clone_repo`` no devuelve códigos de error: o termina bien, o lanza una
subclase de ``GhOrganizerError`` con un ``user_message`` listo para la UI.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path

from gh_organizer.core.exceptions import (
    ClonePermissionError,
    CloneTimeoutError,
    GitNotInstalledError,
    TargetExistsError,
)
from gh_organizer.utils.errors import from_git_clone, from_os_error

logger = logging.getLogger(__name__)

CLONE_TIMEOUT_SECONDS = 300


def ensure_git_available() -> None:
    """Lanza ``GitNotInstalledError`` si ``git`` no está en el PATH."""
    if shutil.which("git") is None:
        logger.error("git no está instalado o no está en el PATH")
        raise GitNotInstalledError()


def clone_repo(url: str, target: Path) -> Path:
    """Clona ``url`` en ``target``.

    Args:
        url: URL HTTP(S) del repo.
        target: Ruta destino local.

    Returns:
        La ruta donde quedó el clon.

    Raises:
        GhOrganizerError: (o subclase) con ``user_message`` para el usuario.
    """
    ensure_git_available()

    target = target.expanduser()
    if target.exists():
        raise TargetExistsError(str(target))

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise from_os_error(e, str(target.parent)) from e

    if not os.access(target.parent, os.W_OK | os.X_OK):
        raise ClonePermissionError(str(target.parent))

    logger.info("Clonando %s → %s", url, target)

    try:
        result = subprocess.run(
            ["git", "clone", url, str(target)],
            capture_output=True,
            text=True,
            check=False,
            timeout=CLONE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as e:
        logger.warning("Timeout clonando %s", url)
        raise CloneTimeoutError() from e
    except OSError as e:
        raise from_os_error(e, str(target)) from e

    if result.returncode != 0:
        error = from_git_clone(result.returncode, result.stderr or "", str(target))
        logger.warning(
            "git clone falló (rc=%d): %s", result.returncode, error.user_message
        )
        raise error

    logger.info("Clonado OK: %s", target)
    return target


__all__ = ["CLONE_TIMEOUT_SECONDS", "clone_repo", "ensure_git_available"]
