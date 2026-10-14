# src/github_organizer/ui/keybindings.py
"""Atajos de teclado centralizados.

Cada grupo corresponde a un contexto:
- GLOBAL: se aplican a nivel de App (todas las pantallas).
- MAIN: pantalla principal.
- AUTH: pantalla de token.
- FOLDER_PICKER: modal de colecciones.
- ORGANIZE: modal de auto-organización.
"""

from textual.binding import Binding, BindingType

# --- Globales (App) ---
GLOBAL: list[BindingType] = [
    Binding("q", "quit", "Salir"),
    Binding("ctrl+c", "quit", "Salir"),
    Binding("ctrl+shift+t", "push_token_screen", "Token"),
]

# --- Pantalla principal ---
MAIN: list[BindingType] = [
    Binding("r", "reload", "Recargar"),
    Binding("t", "set_token", "Token"),
    Binding("e", "expand_all", "Expandir"),
    Binding("c", "collapse_all", "Colapsar"),
    Binding("m", "move_repo", "Mover"),
    Binding("u", "unassign_repo", "Quitar"),
    Binding("n", "new_folder", "Nueva colección"),
    Binding("o", "organize", "Auto-organizar"),
    Binding("ctrl+t", "cycle_theme", "Tema", show=True),
    Binding("comma", "open_settings", "Settings", show=True),
]

# --- Pantalla de autenticación ---
AUTH: list[BindingType] = [
    Binding("escape", "app.pop_screen", "Cancelar"),
]

# --- Modal de gestión de colecciones ---
FOLDER_PICKER: list[BindingType] = [
    Binding("tab", "toggle_panel", "Cambiar panel", priority=True),
    Binding("n", "new_child_folder", "Nueva hija", priority=True),
    Binding("a", "new_root_folder", "Nueva raíz", priority=True),
    Binding("r", "rename_folder", "Renombrar", priority=True),
    Binding("d", "delete_folder", "Eliminar", priority=True),
    Binding("escape", "handle_escape", "Cerrar", priority=True),
]

# --- Modal de auto-organización ---
ORGANIZE: list[BindingType] = [
    Binding("escape", "app.pop_screen", "Cancelar"),
]

# --- Pantalla de settings ---
SETTINGS: list[BindingType] = [
    Binding("escape", "app.pop_screen", "Cerrar", priority=True),
]
