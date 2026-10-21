# src/gh_organizer/ui/keybindings.py
"""Atajos de teclado centralizados."""

from textual.binding import Binding, BindingType

GLOBAL: list[BindingType] = [
    Binding("q", "quit", "Salir"),
    Binding("ctrl+c", "quit", "Salir"),
    Binding("ctrl+t", "push_token_screen", "Token"),
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
    Binding("ctrl+k", "cycle_theme", "Tema"),
]

AUTH: list[BindingType] = [
    Binding("escape", "app.pop_screen", "Cancelar"),
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
    Binding("escape", "app.pop_screen", "Cancelar"),
]
SETTINGS: list[BindingType] = [
    Binding("escape", "app.pop_screen", "Volver"),
]
