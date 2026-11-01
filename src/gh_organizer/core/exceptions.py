# src/gh_organizer/core/exceptions.py
"""Jerarquía de excepciones del dominio de la aplicación.

Todas las excepciones que hereden de :class:`GhOrganizerError` exponen:

* ``user_message``: el texto en español (es el ``msgid`` del catálogo). Para
  mostrarlo en la UI hay que usar :attr:`GhOrganizerError.localized_message`,
  que lo traduce al idioma activo en el momento de pintarlo.
* ``localized_message``: propiedad que devuelve el mensaje traducido.

Regla de oro: si un error NO tiene un mensaje amigable, no debería llegar a
la UI. Los traductores de ``gh_organizer.utils.errors`` se encargan de
convertir excepciones de terceros en alguna de estas.
"""

from __future__ import annotations

from gh_organizer.i18n import _


class GhOrganizerError(Exception):
    """Excepción base. Todas las excepciones de dominio heredan de aquí."""

    user_message: str = "❌ Ha ocurrido un error inesperado."

    def __init__(self, message: str = "", user_message: str = "") -> None:
        if user_message:
            self.user_message = user_message
        super().__init__(message or self.user_message)

    @property
    def localized_message(self) -> str:
        """``user_message`` traducido al idioma activo."""
        return _(self.user_message)


# ──────────────────────────────────────────────────────────────────── #
#  Autenticación
# ──────────────────────────────────────────────────────────────────── #
class AuthError(GhOrganizerError):
    """Problemas con el token de GitHub."""

    user_message = "🔒 Problema con tu token de GitHub."


class MissingTokenError(AuthError):
    """No hay ningún token configurado."""

    user_message = "❌ No hay token. Pulsa [b]t[/b] para configurarlo."


class InvalidTokenError(AuthError):
    """Token inválido, expirado o revocado."""

    user_message = (
        "❌ Token inválido o expirado. Pulsa [b]t[/b] para configurar uno nuevo."
    )


class MissingScopeError(AuthError):
    """El token no tiene los permisos (scopes) necesarios."""

    def __init__(self, missing_scope: str = "repo") -> None:
        self.missing_scope = missing_scope
        super().__init__(
            user_message=_(
                "🔒 Tu token no tiene el permiso [b]%(scope)s[/b].\n"
                "Edítalo en GitHub → Settings → Developer settings → Tokens."
            )
            % {"scope": missing_scope}
        )


class RateLimitError(AuthError):
    """Demasiadas peticiones a la API de GitHub."""

    user_message = (
        "⏳ Has alcanzado el límite de peticiones de GitHub. "
        "Espera unos minutos e inténtalo de nuevo."
    )


class RepoAccessError(AuthError):
    """No se puede acceder a un repositorio concreto."""

    def __init__(self, repo_name: str = "") -> None:
        if repo_name:
            message = _("🔒 No tienes acceso al repositorio [b]%(repo)s[/b].") % {
                "repo": repo_name
            }
        else:
            message = _("🔒 No tienes acceso a este repositorio.")
        super().__init__(user_message=message)


# ──────────────────────────────────────────────────────────────────── #
#  Red
# ──────────────────────────────────────────────────────────────────── #
class NetworkError(GhOrganizerError):
    """Problemas de conectividad con GitHub."""

    user_message = "🌐 No se pudo conectar con GitHub. Revisa tu conexión a internet."


# ──────────────────────────────────────────────────────────────────── #
#  Dependencias del sistema
# ──────────────────────────────────────────────────────────────────── #
class DependencyError(GhOrganizerError):
    """Falta una dependencia externa del sistema."""

    user_message = "⚠️ Falta una dependencia del sistema."


class GitNotInstalledError(DependencyError):
    """``git`` no está en el PATH."""

    user_message = (
        "⚠️ [b]git[/b] no está instalado en tu sistema.\n"
        "Instálalo para poder clonar repositorios."
    )


class KeyringUnavailableError(DependencyError):
    """El keyring del sistema no está disponible."""

    user_message = (
        "⚠️ El keyring del sistema no está disponible.\n"
        "El token solo se guardará en memoria para esta sesión."
    )


# ──────────────────────────────────────────────────────────────────── #
#  Clonado de repositorios
# ──────────────────────────────────────────────────────────────────── #
class CloneError(GhOrganizerError):
    """Error al clonar un repositorio."""

    user_message = "❌ No se pudo clonar el repositorio."


class TargetExistsError(CloneError):
    """El directorio destino ya existe."""

    def __init__(self, path: str = "") -> None:
        if path:
            message = _("📂 Ya existe un repositorio en [b]%(path)s[/b].") % {
                "path": path
            }
        else:
            message = _("📂 Ya existe un repositorio.")
        super().__init__(user_message=message)


class DiskSpaceError(CloneError):
    """No hay suficiente espacio en disco."""

    user_message = "💾 No hay suficiente espacio en disco para clonar el repositorio."


class ClonePermissionError(CloneError):
    """Sin permisos para escribir en el directorio destino.

    Nota: deliberadamente NO se llama ``PermissionError`` para no sombrear el
    builtin, que se sigue usando en los ``except`` de ``services/git.py``.
    """

    def __init__(self, path: str = "") -> None:
        if path:
            message = _("📂 No tienes permisos para escribir en [b]%(path)s[/b].") % {
                "path": path
            }
        else:
            message = _("📂 No tienes permisos para escribir.")
        super().__init__(user_message=message)


class CloneTimeoutError(CloneError):
    """``git clone`` superó el tiempo máximo."""

    user_message = (
        "⏰ El clonado tardó más de 5 minutos. "
        "Comprueba tu conexión e inténtalo de nuevo."
    )


class GitCloneFailedError(CloneError):
    """``git clone`` falló por otra razón (repo inexistente, red, etc.)."""

    def __init__(self, detail: str = "") -> None:
        self.detail = detail
        if detail:
            message = _("❌ No se pudo clonar: %(detail)s") % {"detail": detail}
        else:
            message = _("❌ No se pudo clonar.")
        super().__init__(user_message=message)


# ──────────────────────────────────────────────────────────────────── #
#  Configuración
# ──────────────────────────────────────────────────────────────────── #
class ConfigError(GhOrganizerError):
    """Error al leer o escribir la configuración."""

    user_message = "⚙️ Error con la configuración de la aplicación."


class CorruptedConfigError(ConfigError):
    """El archivo ``config.toml`` está corrupto o no se pudo leer."""

    user_message = (
        "⚙️ El archivo de configuración está corrupto. "
        "Se han restaurado los valores por defecto y se guardó una copia."
    )


class ConfigWriteError(ConfigError):
    """No se pudo escribir ``config.toml``."""

    def __init__(self, path: str = "") -> None:
        suffix = f" ({path})" if path else ""
        super().__init__(
            user_message=(
                _(
                    "⚙️ No se pudo guardar la configuración. "
                    "Comprueba los permisos de [b]~/.config/github-organizer/[/b]"
                )
                + suffix
            )
        )


# ──────────────────────────────────────────────────────────────────── #
#  Colecciones (carpetas)
#
#  Heredan TAMBIÉN de KeyError/ValueError para no romper a los consumidores
#  actuales que capturaban esos builtins.
# ──────────────────────────────────────────────────────────────────── #
class FolderError(GhOrganizerError):
    """Error al manipular colecciones."""

    user_message = "📁 No se pudo modificar la colección."


class FolderNotFoundError(FolderError, KeyError):
    """La colección indicada no existe."""

    def __init__(self, path: str = "") -> None:
        self.path = path
        super().__init__(
            user_message=_("📁 No existe la colección [b]%(path)s[/b].")
            % {"path": path}
        )

    def __str__(self) -> str:  # evita el repr entrecomillado de KeyError
        return self.args[0] if self.args else ""


class FolderExistsError(FolderError, ValueError):
    """Ya existe una colección con esa ruta / nombre inválido."""

    def __init__(self, path: str = "") -> None:
        self.path = path
        super().__init__(
            user_message=_("📁 Ya existe una colección con la ruta [b]%(path)s[/b].")
            % {"path": path}
        )


class InvalidFolderNameError(FolderError, ValueError):
    """Nombre de colección vacío o no válido."""

    user_message = "📁 El nombre de la colección no puede estar vacío."
