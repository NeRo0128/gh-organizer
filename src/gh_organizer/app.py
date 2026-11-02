# src/gh_organizer/app.py
import logging
from typing import ClassVar

from textual.app import App
from textual.binding import BindingType

from gh_organizer.i18n import _, setup_i18n
from gh_organizer.services import load_token
from gh_organizer.services.dependencies import (
    check_all_dependencies,
    has_missing_critical,
)
from gh_organizer.services.preferences import load_language, load_theme
from gh_organizer.ui import keybindings
from gh_organizer.ui.modals import DependenciesModal
from gh_organizer.ui.screens import MainScreen, TokenScreen
from gh_organizer.ui.styles import ALL_THEMES, BASE_CSS

logger = logging.getLogger(__name__)


class GithubOrganizerApp(App):
    """Aplicación principal de GitHub Organizer."""

    BINDINGS: ClassVar[list[BindingType]] = keybindings.GLOBAL
    TITLE = "GitHub Organizer"
    SUB_TITLE = ""
    CSS_PATH = BASE_CSS
    i18n_dirty: bool = False

    def on_mount(self) -> None:
        """Activa el idioma, registra los temas y decide la pantalla inicial."""
        setup_i18n(load_language())
        self.sub_title = _("Organiza tus repositorios en carpetas personalizadas")

        for theme in ALL_THEMES:
            self.register_theme(theme)
        self.theme = load_theme()
        logger.info("Tema aplicado: %s", self.theme)

        # Verificación de dependencias antes de entrar a la app
        statuses = check_all_dependencies()
        if has_missing_critical(statuses):
            logger.warning("Faltan dependencias críticas, mostrando modal")
            self.push_screen(DependenciesModal(statuses), self._on_initial_deps_result)
        else:
            self._notify_optional_missing(statuses)
            self._proceed_to_main()

    def _notify_optional_missing(self, statuses) -> None:
        """Muestra warnings no bloqueantes para dependencias opcionales faltantes."""
        for s in statuses:
            if not s.available and not s.critical:
                self.notify(s.description, severity="warning", timeout=6)

    def _on_initial_deps_result(self, continue_: bool | None) -> None:
        """Callback del modal en el arranque: continuar o salir.

        `None` se trata como "no continuar" (más seguro: si el modal
        se cerró sin decisión explícita, pedimos al usuario que instale
        las dependencias antes de seguir).
        """
        if continue_ is True:
            self._proceed_to_main()
        else:
            logger.info("Usuario eligió salir al ver dependencias faltantes")
            self.exit()

    def _proceed_to_main(self) -> None:
        """Decide qué pantalla mostrar tras las comprobaciones iniciales."""
        logger.info("App montada. Token presente: %s", bool(load_token()))
        if load_token():
            self.push_screen(MainScreen())
        else:
            self.push_screen(TokenScreen())

    def action_push_token_screen(self) -> None:
        self.push_screen(TokenScreen())

    def action_show_dependencies(self) -> None:
        """Abre el modal de dependencias bajo demanda (Ctrl+D)."""
        statuses = check_all_dependencies()
        self.push_screen(DependenciesModal(statuses))

    def action_show_logs(self) -> None:
        """Abre el modal de logs bajo demanda (Ctrl+L)."""
        from gh_organizer.ui.modals import LogsModal

        self.push_screen(LogsModal())
