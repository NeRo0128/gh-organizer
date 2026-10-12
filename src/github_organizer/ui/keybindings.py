# src/github_organizer/ui/keybindings.py
"""Atajos de teclado centralizados.

Cada grupo corresponde a un contexto:
- GLOBAL: se aplican a nivel de App (todas las pantallas).
- MAIN: pantalla principal.
- AUTH: pantalla de token.
- FOLDER_PICKER: modal de carpetas.


Formato: (tecla, acción, descripción).
"""

from textual.binding import BindingType

# --- Globales (App) ---
GLOBAL: list[BindingType] = [
    ("q", "quit", "Salir"),
    ("ctrl+c", "quit", "Salir"),
    ("ctrl+t", "push_token_screen", "Token"),
]

# --- Pantalla principal ---
MAIN: list[BindingType] = [
    ("r", "reload", "Recargar"),
    ("t", "set_token", "Token"),
    ("e", "expand_all", "Expandir"),
    ("c", "collapse_all", "Colapsar"),
    ("m", "move_repo", "Mover"),
    ("u", "unassign_repo", "Quitar"),
    ("n", "new_folder", "Nueva carpeta"),
]

# --- Pantalla de autenticación ---
AUTH: list[BindingType] = [
    ("escape", "app.pop_screen", "Cancelar"),
]

# --- Modal de selección de carpeta ---
FOLDER_PICKER: list[BindingType] = [
    ("escape", "dismiss(None)", "Cancelar"),
]
