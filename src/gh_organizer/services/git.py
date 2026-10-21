# src/gh_organizer/services/git.py
"""Operaciones locales con git."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def clone_repo(url: str, target: Path) -> tuple[bool, str]:
    """Clona un repositorio.

    Args:
        url: URL HTTP(S) del repo.
        target: Ruta destino local.

    Returns:
        (ok, mensaje) — el mensaje es un error si ok=False.
    """
    if target.exists():
        return False, f"Ya existe: {target}"

    target.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Clonando %s → %s", url, target)

    try:
        result = subprocess.run(
            ["git", "clone", url, str(target)],
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Timeout clonando %s", url)
        return False, "Timeout (>5min)"
    except OSError as e:
        logger.error("Error lanzando git: %s", e)
        return False, f"Error: {e}"

    if result.returncode != 0:
        err = (result.stderr or "").strip()[:200] or "Error desconocido"
        logger.warning("git clone falló (rc=%d): %s", result.returncode, err)
        return False, err

    logger.info("Clonado OK: %s", target)
    return True, f"Clonado en {target}"
