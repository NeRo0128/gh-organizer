# src/github_organizer/services/organizer.py
"""Estrategias de organización automática de repositorios.

Cada estrategia es una función pura: recibe una lista de Repo y devuelve
un dict {ruta_carpeta: [nombres_de_repo]}.
"""

import logging
from collections.abc import Callable

from github_organizer.core import Repo

logger = logging.getLogger(__name__)

Strategy = Callable[[list[Repo]], dict[str, list[str]]]


def by_language(repos: list[Repo]) -> dict[str, list[str]]:
    """Agrupa por lenguaje principal. Los sin lenguaje van a 'Sin lenguaje'."""
    result: dict[str, list[str]] = {}
    for repo in repos:
        lang = repo.language or "Sin lenguaje"
        result.setdefault(f"Lenguajes/{lang}", []).append(repo.name)
    logger.debug("by_language: %d carpetas resultantes", len(result))
    return result


def by_visibility(repos: list[Repo]) -> dict[str, list[str]]:
    """Agrupa por visibilidad (Público / Privado)."""
    result: dict[str, list[str]] = {"Público": [], "Privado": []}
    for repo in repos:
        key = "Privado" if repo.private else "Público"
        result[key].append(repo.name)
    result = {k: v for k, v in result.items() if v}
    logger.debug("by_visibility: %d carpetas resultantes", len(result))
    return result


def by_language_and_visibility(repos: list[Repo]) -> dict[str, list[str]]:
    """Agrupa por visibilidad y anida lenguaje dentro de cada grupo."""
    result: dict[str, list[str]] = {}
    for repo in repos:
        vis = "Privados" if repo.private else "Públicos"
        lang = repo.language or "Sin lenguaje"
        result.setdefault(f"{vis}/{lang}", []).append(repo.name)
    logger.debug("by_language_and_visibility: %d carpetas resultantes", len(result))
    return result


# Registro: (nombre legible, función, descripción)
STRATEGIES: list[tuple[str, Strategy, str]] = [
    (
        "Por lenguaje",
        by_language,
        "Agrupa los repos en carpetas según su lenguaje principal",
    ),
    (
        "Por visibilidad",
        by_visibility,
        "Separa repos públicos y privados",
    ),
    (
        "Visibilidad + lenguaje",
        by_language_and_visibility,
        "Separa por visibilidad y anida el lenguaje dentro de cada grupo",
    ),
]
