# src/gh_organizer/i18n.py
"""Internacionalización con ``gettext`` (stdlib, sin dependencias externas).

Diseño:

* El **idioma fuente es el español**: los ``msgid`` de los catálogos son el
  texto tal cual está escrito en el código. Si falta una traducción, si el
  ``.mo`` no se ha compilado o si el idioma no está soportado, se muestra
  español en lugar de romperse (``gettext`` devuelve el ``msgid``).
* ``_()`` lee el catálogo **en cada llamada**, así que cambiar de idioma en
  caliente solo requiere volver a llamar a :func:`setup_i18n`.
* Los mensajes de ``logger`` NO se traducen a propósito: los logs son para
  depurar y deben ser estables y buscables independientemente del idioma de
  la interfaz.

Compilar catálogos tras editar un ``.po``::

    uv run python scripts/i18n.py compile
"""

from __future__ import annotations

import gettext
import locale
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DOMAIN = "gh_organizer"
SOURCE_LANGUAGE = "es"
SUPPORTED_LANGUAGES: tuple[str, ...] = ("es", "en")
AUTO = "auto"

LOCALES_DIR = Path(__file__).parent / "locales"

# ``NullTranslations`` devuelve el msgid sin tocar → español por defecto.
_translation: gettext.NullTranslations = gettext.NullTranslations()
_current_language: str = SOURCE_LANGUAGE


# ---------------------------------------------------------------------- #
#  API pública
# ---------------------------------------------------------------------- #
def _(message: str) -> str:
    """Traduce un mensaje (msgid en español) al idioma activo."""
    return _translation.gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    """Traduce con plurales."""
    return _translation.ngettext(singular, plural, n)


def current_language() -> str:
    """Código del idioma activo ('es' o 'en')."""
    return _current_language


def available_languages() -> tuple[str, ...]:
    """Idiomas soportados, sin contar 'auto'."""
    return SUPPORTED_LANGUAGES


def detect_system_language() -> str:
    """Idioma del sistema, limitado a ``SUPPORTED_LANGUAGES``.

    Se miran primero las variables POSIX (más fiables en contenedores y CI que
    ``locale.getlocale()``) y después ``locale`` como respaldo.
    """
    for variable in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        raw = os.environ.get(variable, "")
        # LANGUAGE puede ser una lista "en_US:es_ES"
        for candidate in raw.split(":"):
            code = _language_code(candidate)
            if code in SUPPORTED_LANGUAGES:
                logger.debug("Idioma detectado por %s=%r → %s", variable, raw, code)
                return code

    try:
        locale_code = locale.getlocale()[0] or ""
    except (ValueError, TypeError):  # locale inválido en el sistema
        locale_code = ""
    code = _language_code(locale_code)
    if code in SUPPORTED_LANGUAGES:
        logger.debug("Idioma detectado por locale → %s", code)
        return code

    logger.debug("No se pudo detectar el idioma del sistema, usando %s", SOURCE_LANGUAGE)
    return SOURCE_LANGUAGE


def resolve_language(language: str | None) -> str:
    """Convierte una preferencia ('auto', 'es', 'en', basura) en 'es' o 'en'."""
    if language in SUPPORTED_LANGUAGES:
        return str(language)
    if language not in (None, "", AUTO):
        logger.warning("Idioma no soportado %r, se ignora", language)
    return detect_system_language()


def setup_i18n(language: str | None = AUTO) -> str:
    """Activa el idioma indicado y devuelve el código finalmente aplicado.

    Es idempotente y se puede llamar varias veces (cambio en caliente desde
    la pantalla de ajustes).
    """
    global _translation, _current_language

    resolved = resolve_language(language)
    try:
        translation = gettext.translation(
            DOMAIN,
            localedir=str(LOCALES_DIR),
            languages=[resolved],
            fallback=False,
        )
    except (OSError, FileNotFoundError):
        logger.warning(
            "Sin catálogo para %r en %s; se usa el español", resolved, LOCALES_DIR
        )
        translation = gettext.NullTranslations()
        resolved = SOURCE_LANGUAGE

    _translation = translation
    _current_language = resolved
    logger.info("Idioma activo: %s", resolved)
    return resolved


def reset_i18n() -> None:
    """Vuelve al idioma fuente sin tocar disco (para tests)."""
    global _translation, _current_language
    _translation = gettext.NullTranslations()
    _current_language = SOURCE_LANGUAGE


def _language_code(raw: str) -> str:
    """'en_US.UTF-8@euro' → 'en'."""
    code = (raw or "").strip()
    if not code:
        return ""
    code = code.split(".")[0].split("@")[0].replace("-", "_")
    return code.split("_")[0].lower()
