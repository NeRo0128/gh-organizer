# src/gh_organizer/ui/keybindings.py
"""Atajos de teclado centralizados."""

from textual.binding import Binding as _TextualBinding
from textual.binding import BindingType

from gh_organizer.i18n import _


class Binding(_TextualBinding):
    """``Binding`` cuya descripción se traduce al pintarla.

    Las listas de esta constante se evalúan al importar el módulo, es decir,
    antes de que exista un idioma activo. Guardamos el msgid (español) y
    traducimos en el *getter*, así el ``Footer`` y el ``HelpModal`` siempre
    muestran el idioma actual sin reconstruir las listas.
    """

    def __init__(self, key: str, action: str, description: str = "", **kwargs) -> None:
        self._msgid = description
        super().__init__(key, action, description, **kwargs)

    @property
    def description(self) -> str:
        return _(self._msgid)

    @description.setter
    def description(self, value: str) -> None:
        self._msgid = value


GLOBAL: list[BindingType] = [
    Binding("q", "quit", "Salir"),
    Binding("ctrl+c", "quit", "Salir"),
    Binding("ctrl+t", "push_token_screen", "Token"),
    Binding("ctrl+d", "show_dependencies", "Dependencias"),  # 👈 nuevo
]

MAIN: list[BindingType] = [
    Binding("r", "reload", "Recargar"),
    Binding("t", "set_token", "Token"),
    Binding("s", "open_settings", "Ajustes"),
    Binding("e", "expand_all", "Expandir"),
    Binding("c", "collapse_all", "Colapsar"),
    Binding("g", "clone_repo", "Clonar"),
    Binding("m", "move_repo", "Mover"),
    Binding("u", "unassign_repo", "Quitar"),
    Binding("n", "new_folder", "Nueva colección"),
    Binding("o", "organize", "Auto-organizar"),
    Binding("slash", "search", "Buscar"),
    Binding("question_mark", "show_help", "Ayuda"),
    Binding("ctrl+k", "cycle_theme", "Tema"),
]

AUTH: list[BindingType] = [
    Binding("escape", "app.pop_screen", "Cancelar"),
]

SETTINGS: list[BindingType] = [  # 👈 AÑADIR
    Binding("escape", "app.pop_screen", "Volver"),
]

FOLDER_PICKER: list[BindingType] = [
    Binding("tab", "toggle_panel", "Cambiar panel", priority=True),
    Binding("n", "new_child_folder", "Nueva hija", priority=True),
    Binding("a", "new_root_folder", "Nueva raíz", priority=True),
    Binding("r", "rename_folder", "Renombrar", priority=True),
    Binding("d", "delete_folder", "Eliminar", priority=True),
    Binding("escape", "handle_escape", "Cerrar", priority=True),
]

ORGANIZE: list[BindingType] = [
    Binding("up", "cursor_up", "Subir"),
    Binding("down", "cursor_down", "Bajar"),
    Binding("enter", "select", "Aplicar estrategia"),
    Binding("escape", "app.pop_screen", "Cancelar"),
]

HELP: list[BindingType] = [
    Binding("escape", "app.pop_screen", "Cerrar"),
]

DEPENDENCIES: list[BindingType] = [
    Binding("escape", "cancel", "Salir", priority=True),
    Binding("y", "confirm", "Continuar", priority=True),
    Binding("n", "cancel", "Salir", priority=True),
]
