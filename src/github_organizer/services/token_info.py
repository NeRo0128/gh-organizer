# src/github_organizer/services/token_info.py
"""Información sobre el token de GitHub: permisos (scopes) detectados.

Un token PAT de GitHub tiene un conjunto de *scopes* que determinan qué
puede hacer. Los consultamos vía la cabecera `X-OAuth-Scopes` del endpoint
`/user` (una única llamada).
"""

import logging
from dataclasses import dataclass
from typing import Literal

import requests

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────── #
#  Catálogo de permisos
# ──────────────────────────────────────────────────────────────────── #
PermissionPriority = Literal["required", "optional", "future"]


@dataclass(frozen=True)
class TokenPermission:
    scope: str
    label: str
    description: str
    priority: PermissionPriority


TOKEN_PERMISSIONS: list[TokenPermission] = [
    TokenPermission(
        scope="repo",
        label="Repositorios (públicos y privados)",
        description="Ver repos, commits y releases",
        priority="required",
    ),
    TokenPermission(
        scope="read:user",
        label="Perfil del usuario",
        description="Ver tu nombre y avatar",
        priority="required",
    ),
    TokenPermission(
        scope="public_repo",
        label="Solo repos públicos",
        description="Alternativa a 'repo' (limitada)",
        priority="optional",
    ),
    TokenPermission(
        scope="read:org",
        label="Organizaciones",
        description="Ver repos de organizaciones",
        priority="future",
    ),
    TokenPermission(
        scope="workflow",
        label="GitHub Actions",
        description="Ver y gestionar workflows",
        priority="future",
    ),
    TokenPermission(
        scope="notifications",
        label="Notificaciones",
        description="Leer notificaciones",
        priority="future",
    ),
    TokenPermission(
        scope="gist",
        label="Gists",
        description="Gestionar gists",
        priority="future",
    ),
]

# Scopes recomendados al crear un token nuevo
RECOMMENDED_SCOPES: list[str] = [
    "repo",
    "read:user",
    "read:org",
    "workflow",
    "notifications",
    "gist",
]


# ──────────────────────────────────────────────────────────────────── #
#  Consulta al API
# ──────────────────────────────────────────────────────────────────── #
def get_token_scopes(token: str, timeout: float = 10.0) -> set[str]:
    """Consulta el endpoint /user y extrae los scopes del token.

    Devuelve un set vacío si el token no tiene scopes (fine-grained tokens
    no usan esta cabecera) o si la petición falla.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        r = requests.get(
            "https://api.github.com/user", headers=headers, timeout=timeout
        )
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.warning("Error consultando scopes: %s", e)
        return set()

    header = r.headers.get("X-OAuth-Scopes", "")
    scopes = {s.strip() for s in header.split(",") if s.strip()}
    logger.debug("Scopes detectados: %s", sorted(scopes))
    return scopes


def mask_token(token: str, prefix: int = 4, suffix: int = 4) -> str:
    """Enmascara un token para mostrarlo: 'ghp_…aBcD'."""
    if not token:
        return "—"
    if len(token) <= prefix + suffix + 1:
        return "•" * len(token)
    return f"{token[:prefix]}…{token[-suffix:]}"


def build_token_creation_url() -> str:
    """URL para crear un nuevo PAT con los scopes recomendados pre-seleccionados."""
    scopes = ",".join(RECOMMENDED_SCOPES)
    return (
        "https://github.com/settings/tokens/new"
        f"?description=GitHub%20Organizer&scopes={scopes}"
    )
