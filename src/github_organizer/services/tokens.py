# src/github_organizer/services/tokens.py
import logging
import os
import shutil
import subprocess

import keyring
import keyring.errors

from github_organizer.services.settings import TOKEN_ENV_VAR

logger = logging.getLogger(__name__)

SERVICE_NAME = "github-organizer"
USERNAME = "github_token"


def save_token(token: str) -> bool:
    """Guarda el token en el keyring. Devuelve True si tuvo éxito."""
    try:
        keyring.set_password(SERVICE_NAME, USERNAME, token)
        logger.info("Token guardado en el keyring del sistema")
        return True
    except keyring.errors.KeyringError as e:
        logger.warning("No se pudo guardar en el keyring: %s", e)
        return False


def load_token() -> str | None:
    """Devuelve el token desde: env var → gh CLI → keyring."""
    env_token = os.environ.get(TOKEN_ENV_VAR)
    if env_token:
        logger.debug("Token obtenido desde variable de entorno %s", TOKEN_ENV_VAR)
        return env_token

    gh_token = token_from_gh_cli()
    if gh_token:
        logger.debug("Token obtenido desde gh CLI")
        return gh_token

    try:
        token = keyring.get_password(SERVICE_NAME, USERNAME)
        if token:
            logger.debug("Token obtenido desde el keyring")
            return token
    except keyring.errors.KeyringError as e:
        logger.warning("Error al leer del keyring: %s", e)

    logger.debug("No se encontró token en ninguna fuente")
    return None


def delete_token() -> None:
    """Elimina el token del keyring."""
    try:
        keyring.delete_password(SERVICE_NAME, USERNAME)
        logger.info("Token eliminado del keyring")
    except keyring.errors.KeyringError as e:
        logger.warning("No se pudo eliminar del keyring: %s", e)


def token_from_gh_cli() -> str | None:
    """Intenta obtener el token desde el CLI oficial `gh`, si está instalado."""
    if not shutil.which("gh"):
        logger.debug("gh CLI no está instalado en el PATH")
        return None
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            token = result.stdout.strip()
            if token:
                return token
            logger.debug("gh auth token devolvió salida vacía")
        else:
            logger.debug(
                "gh auth token falló (rc=%d): %s",
                result.returncode,
                result.stderr.strip(),
            )
    except (subprocess.SubprocessError, OSError) as e:
        logger.warning("Error ejecutando gh: %s", e)
    return None
