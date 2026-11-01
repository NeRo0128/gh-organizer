# tests/test_i18n_ui.py
"""Tests de integración del cambio de idioma en la interfaz."""

from __future__ import annotations

import asyncio

import pytest
from textual.app import App
from textual.widgets import Static

from gh_organizer import i18n
from gh_organizer.services import config, preferences
from gh_organizer.ui.screens import settings as settings_mod
from gh_organizer.ui.screens.main import MainScreen
from gh_organizer.ui.screens.settings import SETTINGS_CATALOG, SettingsScreen


class SettingsHarness(App):
    """App mínima que monta solo la pantalla de ajustes."""

    def on_mount(self) -> None:
        self.push_screen(SettingsScreen())


@pytest.fixture(autouse=True)
def _reset_language():
    i18n.reset_i18n()
    yield
    i18n.reset_i18n()


@pytest.fixture
def offline_account(monkeypatch: pytest.MonkeyPatch) -> None:
    """Evita que la pantalla llame a GitHub para leer los scopes."""
    monkeypatch.setattr(settings_mod, "load_token", lambda: None)
    monkeypatch.setattr(settings_mod, "get_token_scopes", lambda token: set())


def language_row():
    return next(row for row in SETTINGS_CATALOG["appearance"] if row.key == "language")


def rendered_rows(screen: SettingsScreen) -> list[str]:
    options = screen.query_one("#section-options")
    return [str(child.render()) for child in options.children]


# ──────────────────────────────────────────────────────────────────── #
#  Catálogo (sin Textual)
# ──────────────────────────────────────────────────────────────────── #
def test_language_row_is_in_the_catalog():
    row = language_row()
    assert row.label == "Idioma"
    assert row.values == ["auto", "es", "en"]
    assert row.kind == "select"


# ──────────────────────────────────────────────────────────────────── #
#  Integración con la pantalla real
#  (asyncio.run en lugar de pytest-asyncio para no añadir dependencias)
# ──────────────────────────────────────────────────────────────────── #
def test_settings_renders_language_row(tmp_data_dirs, offline_account):
    async def scenario() -> None:
        app = SettingsHarness()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            texts = rendered_rows(app.screen)
            assert any("Idioma" in text for text in texts)
            assert any("Automático" in text for text in texts)

    asyncio.run(scenario())


def test_changing_language_updates_tabs_and_marks_app(
    tmp_data_dirs, offline_account
):
    async def scenario() -> None:
        app = SettingsHarness()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.screen
            await pilot.pause()
            assert "Apariencia" in str(screen.query_one("#tab-0", Static).render())

            preferences.set_value("language", "en")
            screen._prefs = preferences.load_all()
            screen._apply_language("en")
            await pilot.pause()

            assert i18n.current_language() == "en"
            assert app.i18n_dirty is True
            assert "Appearance" in str(screen.query_one("#tab-0", Static).render())
            assert "Settings" in str(
                screen.query_one("#settings-topbar", Static).render()
            )

    asyncio.run(scenario())


def test_language_change_persists_and_rerenders_rows(
    tmp_data_dirs, offline_account
):
    async def scenario() -> None:
        app = SettingsHarness()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.screen
            await pilot.pause()

            preferences.set_value("language", "en")
            screen._prefs = preferences.load_all()
            screen._apply_language("en")
            await pilot.pause()

            assert preferences.load_language() == "en"
            texts = rendered_rows(screen)
            assert any("Language" in text for text in texts)
            assert any("Tree mode on open" in text for text in texts)
            assert any("Remember" in text for text in texts)

    asyncio.run(scenario())


def test_switching_back_to_spanish_restores_source_texts(
    tmp_data_dirs, offline_account
):
    async def scenario() -> None:
        app = SettingsHarness()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.screen
            await pilot.pause()
            screen._apply_language("en")
            await pilot.pause()
            screen._apply_language("es")
            await pilot.pause()

            assert i18n.current_language() == "es"
            assert "Apariencia" in str(screen.query_one("#tab-0", Static).render())

    asyncio.run(scenario())


# ──────────────────────────────────────────────────────────────────── #
#  MainScreen: recompone al volver de Ajustes con otro idioma
# ──────────────────────────────────────────────────────────────────── #
class MainHarness(App):
    """App mínima que monta solo la pantalla principal."""

    def on_mount(self) -> None:
        self.push_screen(MainScreen())


def test_main_screen_recomposes_after_language_change(tmp_data_dirs, monkeypatch):
    from textual.screen import Screen
    from textual.widgets import Input

    from gh_organizer.ui.screens import main as main_mod

    monkeypatch.setattr(main_mod, "load_token", lambda: None)  # sin red

    async def scenario() -> None:
        app = MainHarness()
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.pause()
            screen = app.screen
            assert "Buscar" in screen.query_one("#search-input", Input).placeholder

            i18n.setup_i18n("en")
            app.i18n_dirty = True
            app.push_screen(Screen())
            await pilot.pause()
            app.pop_screen()
            await pilot.pause()
            await pilot.pause()

            assert app.i18n_dirty is False
            search = screen.query_one("#search-input", Input)
            assert "Search" in search.placeholder
            assert search.display is False
            # El árbol se ha vuelto a montar y sigue ahí.
            assert screen.query_one("#repo-tree") is not None

    asyncio.run(scenario())


# ──────────────────────────────────────────────────────────────────── #
#  Arranque real de la app con otro idioma
# ──────────────────────────────────────────────────────────────────── #
def test_app_boots_in_english(tmp_data_dirs, monkeypatch):
    import gh_organizer.app as app_mod
    from gh_organizer.ui.screens import auth as auth_mod

    config.save(
        {
            "preferences": {"language": "en"},
            "folders": {},
            "tree_state": {},
        }
    )
    # Sin token: debe montarse TokenScreen, ya traducida.
    monkeypatch.setattr(app_mod, "load_token", lambda: None)
    monkeypatch.setattr(auth_mod, "load_token", lambda: None)

    async def scenario() -> None:
        app = app_mod.GithubOrganizerApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.pause()
            assert type(app.screen).__name__ == "TokenScreen"
            assert i18n.current_language() == "en"
            assert app.sub_title == "Organize your repositories into custom folders"
            texts = [
                str(w.render())
                for w in app.screen.walk_children()
                if isinstance(w, Static)
            ]
            assert any("Enter your GitHub Personal Access Token" in t for t in texts)

    asyncio.run(scenario())
