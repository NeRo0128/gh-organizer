# src/gh_organizer/services/dependencies.py
"""Detección de dependencias externas del sistema."""

from __future__ import annotations

import logging
import platform
import shutil

from gh_organizer.core.dependencies import (
    INSTALL_HINTS,
    DependencyName,
    DependencyStatus,
)

logger = logging.getLogger(__name__)


def detect_os_key() -> str:
    """Devuelve una clave de SO para buscar en INSTALL_HINTS.

    Valores posibles: linux_arch, linux_debian, linux_fedora,
    linux_generic, darwin, windows.
    """
    system = platform.system()

    if system == "Darwin":
        return "darwin"
    if system == "Windows":
        return "windows"

    # Linux: intentar detectar la distro
    try:
        os_release = platform.freedesktop_os_release()
        ids = (os_release.get("ID", "") + " " + os_release.get("ID_LIKE", "")).lower()
        if "arch" in ids:
            return "linux_arch"
        if "debian" in ids or "ubuntu" in ids:
            return "linux_debian"
        if "fedora" in ids or "rhel" in ids:
            return "linux_fedora"
    except OSError, AttributeError:
        pass

    return "linux_generic"


def _check_git() -> bool:
    return shutil.which("git") is not None


def _check_keyring() -> bool:
    """Comprueba si el keyring tiene un backend funcional."""
    try:
        import keyring
        from keyring.backends import fail

        backend = keyring.get_keyring()
        # El backend FailKeyring significa que no hay keyring disponible
        return not isinstance(backend, fail.Keyring)
    except Exception:
        logger.exception("Error comprobando keyring")
        return False


def _check_gh_cli() -> bool:
    return shutil.which("gh") is not None


def check_all_dependencies() -> list[DependencyStatus]:
    """Detecta el estado de todas las dependencias externas."""
    os_key = detect_os_key()
    logger.debug("Detectando dependencias (os_key=%s)", os_key)

    checks = [
        (
            DependencyName.GIT,
            _check_git(),
            True,  # crítica
            "git es necesario para clonar repositorios.",
        ),
        (
            DependencyName.KEYRING,
            _check_keyring(),
            False,  # opcional (fallback en memoria)
            "El keyring guarda tu token de forma segura.",
        ),
        (
            DependencyName.GH_CLI,
            _check_gh_cli(),
            False,  # opcional (fallback a token manual)
            "GitHub CLI permite autenticarte sin copiar tokens.",
        ),
    ]

    statuses = [
        DependencyStatus(
            name=name,
            available=available,
            critical=critical,
            description=desc,
            install_hints=INSTALL_HINTS[name],
        )
        for name, available, critical, desc in checks
    ]

    for s in statuses:
        logger.info(
            "Dependencia %s: %s%s",
            s.name.value,
            "OK" if s.available else "FALTA",
            " (crítica)" if s.critical else "",
        )

    return statuses


def has_missing_critical(statuses: list[DependencyStatus]) -> bool:
    """True si falta alguna dependencia crítica."""
    return any(not s.available and s.critical for s in statuses)


def format_missing_summary(statuses: list[DependencyStatus], os_key: str) -> str:
    """Resumen textual de las dependencias faltantes (para logs o UI)."""
    missing = [s for s in statuses if not s.available]
    if not missing:
        return "Todas las dependencias están instaladas."
    lines = []
    for s in missing:
        cmd = s.install_command_for(os_key)
        critical = " (CRÍTICA)" if s.critical else ""
        lines.append(f"- {s.name.value}{critical}: {cmd}")
    return "\n".join(lines)
