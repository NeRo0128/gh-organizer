# src/gh_organizer/core/dependencies.py
"""Modelo de dependencias externas que la aplicación necesita.

Este módulo NO detecta si están instaladas, solo describe qué son,
si son críticas y cómo se instalan en cada sistema operativo.
La detección vive en services/dependencies.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DependencyName(str, Enum):
    """Identificadores estables de cada dependencia."""

    GIT = "git"
    KEYRING = "keyring"
    GH_CLI = "gh"


# Comandos de instalación por SO para cada dependencia.
# La clave "linux_arch" es específica de Arch/EndeavourOS, que es donde
# el maintainer prueba la app. Si no se detecta la distro, se cae a
# "linux_generic".
INSTALL_HINTS: dict[DependencyName, dict[str, str]] = {
    DependencyName.GIT: {
        "linux_arch": "sudo pacman -S git",
        "linux_debian": "sudo apt install git",
        "linux_fedora": "sudo dnf install git",
        "linux_generic": "Instala git con el gestor de paquetes de tu distro",
        "darwin": "brew install git",
        "windows": "winget install Git.Git",
    },
    DependencyName.KEYRING: {
        "linux_arch": "sudo pacman -S gnome-keyring",
        "linux_debian": "sudo apt install gnome-keyring",
        "linux_fedora": "sudo dnf install gnome-keyring",
        "linux_generic": "Instala un backend de keyring (gnome-keyring, kwallet, etc.)",
        "darwin": "Incluido en macOS (Llavero)",
        "windows": "Incluido en Windows (Credential Manager)",
    },
    DependencyName.GH_CLI: {
        "linux_arch": "sudo pacman -S github-cli",
        "linux_debian": "sudo apt install gh",
        "linux_fedora": "sudo dnf install gh",
        "linux_generic": "Instala GitHub CLI: https://cli.github.com",
        "darwin": "brew install gh",
        "windows": "winget install GitHub.cli",
    },
}


@dataclass
class DependencyStatus:
    """Estado de una dependencia externa en el sistema actual."""

    name: DependencyName
    available: bool
    critical: bool
    description: str
    install_hints: dict[str, str] = field(default_factory=dict)

    def install_command_for(self, os_key: str) -> str:
        """Devuelve el comando de instalación para el SO dado."""
        return self.install_hints.get(
            os_key, self.install_hints.get("linux_generic", "—")
        )
