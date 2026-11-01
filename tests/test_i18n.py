# tests/test_i18n.py
"""Tests del sistema de internacionalización (gettext)."""

from __future__ import annotations

import importlib.util
import locale
import re
from pathlib import Path

import pytest

from gh_organizer import i18n
from gh_organizer.core import exceptions as ex
from gh_organizer.services import config, preferences

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def load_tool():
    """Carga scripts/i18n.py como módulo (no es un paquete)."""
    spec = importlib.util.spec_from_file_location("i18n_tool", SCRIPTS / "i18n.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()
PO_EN = i18n.LOCALES_DIR / "en" / "LC_MESSAGES" / f"{i18n.DOMAIN}.po"
PO_ES = i18n.LOCALES_DIR / "es" / "LC_MESSAGES" / f"{i18n.DOMAIN}.po"


@pytest.fixture(autouse=True)
def _reset_language():
    """Cada test empieza y termina en español, sin importar el orden."""
    i18n.reset_i18n()
    yield
    i18n.reset_i18n()


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Borra las variables de idioma para probar la detección por locale."""
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


# ──────────────────────────────────────────────────────────────────── #
#  _() y setup_i18n()
# ──────────────────────────────────────────────────────────────────── #
def test_default_is_spanish_source():
    assert i18n.current_language() == "es"
    assert i18n._("Salir") == "Salir"


def test_setup_i18n_english_translates():
    assert i18n.setup_i18n("en") == "en"
    assert i18n._("Salir") == "Quit"
    assert i18n._("Colecciones") == "Collections"
    assert i18n._("Cargando commits...") == "Loading commits..."


def test_setup_i18n_spanish_keeps_source():
    assert i18n.setup_i18n("es") == "es"
    assert i18n._("Salir") == "Salir"


def test_translation_is_lazy():
    """La función ``_`` importada antes del cambio también traduce."""
    shortcut = i18n._
    shortcut("Guardar token")
    i18n.setup_i18n("en")
    assert shortcut("Guardar token") == "Save token"


def test_unknown_key_returns_msgid():
    i18n.setup_i18n("en")
    assert i18n._("Este texto no existe en el catálogo") == (
        "Este texto no existe en el catálogo"
    )


def test_available_languages():
    assert i18n.available_languages() == ("es", "en")


def test_setup_i18n_accepts_auto(clean_env, monkeypatch):
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    assert i18n.setup_i18n("auto") == "en"


def test_setup_i18n_idempotent():
    assert i18n.setup_i18n("en") == "en"
    assert i18n.setup_i18n("en") == "en"
    assert i18n._("Salir") == "Quit"


def test_missing_catalog_falls_back_to_spanish(monkeypatch, tmp_path):
    monkeypatch.setattr(i18n, "LOCALES_DIR", tmp_path / "locales")
    assert i18n.setup_i18n("en") == "es"
    assert i18n._("Salir") == "Salir"


# ──────────────────────────────────────────────────────────────────── #
#  Detección del idioma del sistema
# ──────────────────────────────────────────────────────────────────── #
@pytest.mark.parametrize(
    ("variable", "value", "expected"),
    [
        ("LC_ALL", "es_ES.UTF-8", "es"),
        ("LC_ALL", "en_US.UTF-8", "en"),
        ("LANG", "en_GB.utf8", "en"),
        ("LANG", "es_AR", "es"),
        ("LC_MESSAGES", "en", "en"),
        ("LANGUAGE", "fr:en", "en"),
    ],
)
def test_detect_from_environment(
    clean_env, monkeypatch, variable, value, expected
):
    monkeypatch.setenv(variable, value)
    assert i18n.detect_system_language() == expected


def test_detect_unsupported_env_falls_back(clean_env):
    clean_env.setenv("LANG", "C")
    assert i18n.detect_system_language() == "es"


def test_detect_uses_locale_when_no_env(clean_env, monkeypatch):
    monkeypatch.setattr(locale, "getlocale", lambda: ("en_US", "UTF-8"))
    assert i18n.detect_system_language() == "en"


def test_detect_handles_broken_locale(clean_env, monkeypatch):
    def boom():
        raise ValueError("locale inválido")

    monkeypatch.setattr(locale, "getlocale", boom)
    assert i18n.detect_system_language() == "es"


def test_detect_empty_locale(clean_env, monkeypatch):
    monkeypatch.setattr(locale, "getlocale", lambda: (None, None))
    assert i18n.detect_system_language() == "es"


def test_language_code_parsing():
    assert i18n._language_code("en_US.UTF-8") == "en"
    assert i18n._language_code("es-ES") == "es"
    assert i18n._language_code("ca_ES@valencia") == "ca"
    assert i18n._language_code("") == ""


def test_resolve_language_keeps_valid_codes():
    assert i18n.resolve_language("en") == "en"
    assert i18n.resolve_language("es") == "es"


# ──────────────────────────────────────────────────────────────────── #
#  Excepciones de dominio
# ──────────────────────────────────────────────────────────────────── #
def test_exception_user_message_is_the_msgid():
    """``user_message`` sigue en español: es la clave del catálogo."""
    i18n.setup_i18n("en")
    error = ex.MissingTokenError()
    assert "No hay token" in error.user_message
    assert "No token found" in error.localized_message


def test_exception_localized_message_english():
    i18n.setup_i18n("en")
    assert "Unable" not in ex.GhOrganizerError().localized_message
    assert "unexpected error" in ex.GhOrganizerError().localized_message


def test_exception_localized_message_spanish():
    error = ex.InvalidTokenError()
    assert error.localized_message == error.user_message


def test_exception_with_scope_is_translated():
    i18n.setup_i18n("en")
    error = ex.MissingScopeError("repo")
    assert "repo" in error.localized_message
    assert "permission" in error.localized_message


def test_exception_with_path_is_translated():
    i18n.setup_i18n("en")
    error = ex.TargetExistsError("/tmp/demo")
    assert "/tmp/demo" in error.localized_message
    assert "already exists" in error.localized_message


def test_folder_errors_keep_builtin_compat():
    assert isinstance(ex.FolderNotFoundError("x"), KeyError)
    assert isinstance(ex.FolderExistsError("x"), ValueError)


# ──────────────────────────────────────────────────────────────────── #
#  Preferencias
# ──────────────────────────────────────────────────────────────────── #
def test_language_default_is_auto():
    assert preferences.DEFAULTS["language"] == "auto"


def test_language_is_not_a_pending_setting():
    """Está implementado de verdad: no debe aparecer como pendiente."""
    assert not preferences.is_pending("language")


def test_invalid_language_falls_back_to_auto(tmp_data_dirs):
    config.save(
        {
            "preferences": {"language": "fr"},
            "folders": {},
            "tree_state": {},
        }
    )
    assert preferences.load_language() == "auto"


def test_language_preference_roundtrip(tmp_data_dirs):
    preferences.set_value("language", "en")
    assert preferences.load_language() == "en"


# ──────────────────────────────────────────────────────────────────── #
#  Integridad de los catálogos
# ──────────────────────────────────────────────────────────────────── #
def test_every_source_msgid_is_in_the_catalog():
    """Si alguien añade ``_("...")`` y olvida el .po, este test lo detecta."""
    catalogs = {lang: TOOL.parse_po(PO) for lang, PO in (("es", PO_ES), ("en", PO_EN))}
    missing = TOOL.source_msgids() - set(catalogs["en"])
    assert not missing, f"msgid sin entrada en el .po: {sorted(missing)}"


def test_english_catalog_has_no_untranslated_entries():
    entries = TOOL.parse_po(PO_EN)
    untranslated = [msgid for msgid, msgstr in entries.items() if msgid and not msgstr]
    assert not untranslated


def test_spanish_catalog_is_identity():
    """El catálogo español repite el msgid (idioma fuente explícito)."""
    for msgid, msgstr in TOOL.parse_po(PO_ES).items():
        if not msgid:  # cabecera del catálogo (metadatos)
            continue
        assert msgid == msgstr


def test_format_placeholders_are_preserved():
    """Una traducción no puede perder ni renombrar un ``%(nombre)s``."""
    pattern = re.compile(r"%\((\w+)\)s")
    for msgid, msgstr in TOOL.parse_po(PO_EN).items():
        assert set(pattern.findall(msgid)) == set(pattern.findall(msgstr)), msgid


def test_mo_files_are_compiled_and_up_to_date(tmp_path):
    """El .mo del repo debe coincidir con el .po (si no, falta recompilar)."""
    for lang, po_path in (("es", PO_ES), ("en", PO_EN)):
        reference = tmp_path / f"{lang}.mo"
        TOOL.compile_catalog(po_path, reference)
        committed = po_path.with_suffix(".mo")
        assert committed.exists(), f"falta {committed} (scripts/i18n.py compile)"
        assert committed.read_bytes() == reference.read_bytes(), (
            f"{committed} está desactualizado: ejecuta scripts/i18n.py compile"
        )


def test_compiled_catalog_is_readable_by_gettext():
    import gettext

    with PO_EN.with_suffix(".mo").open("rb") as handle:
        catalog = gettext.GNUTranslations(handle)
    assert catalog.gettext("Salir") == "Quit"
    assert catalog.info()["content-type"] == "text/plain; charset=UTF-8"


# ──────────────────────────────────────────────────────────────────── #
#  Atajos de teclado (Footer / HelpModal)
# ──────────────────────────────────────────────────────────────────── #
def test_keybindings_are_translated_lazily():
    from gh_organizer.ui import keybindings

    assert keybindings.MAIN[0].description == "Recargar"
    assert keybindings.SETTINGS[0].description == "Volver"

    i18n.setup_i18n("en")

    assert keybindings.MAIN[0].description == "Reload"
    assert keybindings.SETTINGS[0].description == "Back"
    # Los metadatos del Binding no se pierden al heredar de Binding.
    assert keybindings.FOLDER_PICKER[0].priority is True
    assert keybindings.MAIN[0].key == "r"
    assert keybindings.MAIN[0].action == "reload"
