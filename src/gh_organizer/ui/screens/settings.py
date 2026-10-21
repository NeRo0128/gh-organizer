# src/gh_organizer/ui/screens/settings.py
"""Pantalla de configuración.

Navegación:
    Tab / Shift+Tab   → cambiar de sección
    ↑ / ↓             → moverse entre opciones de la sección actual
    ← / →             → cambiar el valor de la opción seleccionada
    Enter             → activar opciones de tipo "action"
    Esc               → cerrar

Los ajustes aún NO conectados a lógica se muestran en `dim yellow` con un
⏳ al final, para saber de un vistazo qué queda por implementar.
"""

import logging
import webbrowser
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from gh_organizer.services import load_token, preferences
from gh_organizer.services.token_info import (
    TOKEN_PERMISSIONS,
    build_token_creation_url,
    get_token_scopes,
    mask_token,
)
from gh_organizer.services.tokens import delete_token
from gh_organizer.ui import (
    ICON_COG,
    ICON_FOLDER,
    ICON_KEY,
    ICON_PALETTE,
    ICON_SLIDERS,
    keybindings,
)
from gh_organizer.ui.styles import SETTINGS_CSS

logger = logging.getLogger(__name__)

OptionKind = Literal["select", "switch", "info", "action"]


# ──────────────────────────────────────────────────────────────────── #
#  Catálogo de ajustes por sección
# ──────────────────────────────────────────────────────────────────── #
@dataclass
class SettingRow:
    """Definición de una opción de Settings."""

    key: str
    label: str
    kind: OptionKind
    value: Any = None
    choices: list[str] = field(default_factory=list)
    values: list[Any] = field(default_factory=list)
    as_markup: bool = False


SETTINGS_CATALOG: dict[str, list[SettingRow]] = {
    "appearance": [
        SettingRow(
            "theme",
            "Tema",
            "select",
            choices=["GitHub Dark", "Tokyo Night", "Catppuccin Mocha", "GitHub Light"],
            values=["github", "tokyo-night", "catppuccin-mocha", "github-light"],
        ),
        SettingRow(
            "tree_mode",
            "Modo del árbol al abrir",
            "select",
            choices=["Recordar", "Expandir todo", "Colapsar todo"],
            values=["remember", "expanded", "collapsed"],
        ),
        SettingRow("show_nerd_icons", "Mostrar iconos Nerd Font", "switch"),
        SettingRow(
            "tree_width",
            "Ancho del árbol",
            "select",
            choices=["25%", "33%", "45%"],
            values=["25", "33", "45"],
        ),
        SettingRow("animations", "Animaciones", "switch"),
    ],
    "repositories": [
        SettingRow(
            "clone_dir",
            "Directorio de clones",
            "select",
            choices=["~/github", "~/code", "~/projects", "~/repos"],
            values=["~/github", "~/code", "~/projects", "~/repos"],
        ),
        SettingRow(
            "commits_limit",
            "Commits a mostrar",
            "select",
            choices=["5", "10", "20"],
            values=[5, 10, 20],
        ),
        SettingRow(
            "releases_limit",
            "Releases a mostrar",
            "select",
            choices=["5", "10", "20"],
            values=[5, 10, 20],
        ),
        SettingRow("exclude_forks", "Excluir forks", "switch"),
        SettingRow("exclude_archived", "Excluir archivados", "switch"),
        SettingRow(
            "sort_by",
            "Ordenar repos por",
            "select",
            choices=["Actualizado", "Nombre", "Estrellas"],
            values=["updated", "name", "stars"],
        ),
    ],
    "organizacion": [
        SettingRow(
            "default_strategy",
            "Estrategia por defecto",
            "select",
            choices=["Por lenguaje", "Por visibilidad", "Visibilidad + lenguaje"],
            values=["Por lenguaje", "Por visibilidad", "Visibilidad + lenguaje"],
        ),
        SettingRow("confirm_organize", "Confirmar antes de organizar", "switch"),
        SettingRow("confirm_delete_folder", "Confirmar antes de eliminar", "switch"),
    ],
    # "account" se construye aparte (contiene info y acciones)
}


SECTION_TITLES: dict[str, str] = {
    "appearance": "Apariencia",
    "repositories": "Repositorios",
    "organizacion": "Organización",
    "account": "Cuenta",
}

SECTION_ICONS: dict[str, str] = {
    "appearance": ICON_PALETTE,
    "repositories": ICON_FOLDER,
    "organizacion": ICON_COG,
    "account": ICON_KEY,
}


class SettingsScreen(Screen):
    """Pantalla con 4 secciones de configuración."""

    BINDINGS: ClassVar[list[BindingType]] = keybindings.SETTINGS
    CSS_PATH = SETTINGS_CSS

    SECTIONS: ClassVar[list[str]] = [
        "appearance",
        "repositories",
        "organizacion",
        "account",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._active_section: int = 0
        self._active_option: int = 0
        self._prefs: dict = {}
        self._account_scopes: set[str] = set()
        self._account_token: str = ""

    # ---------------------------------------------------------------- #
    #  Composición
    # ---------------------------------------------------------------- #
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="settings-topbar")
        with Horizontal(id="settings-tabs"):
            for i, sid in enumerate(self.SECTIONS):
                yield Static(
                    f"{SECTION_ICONS[sid]}  {SECTION_TITLES[sid]}",
                    id=f"tab-{i}",
                    classes="tab-item",
                )
        with VerticalScroll(id="settings-content") as content:
            content.border_title = " Configuración "
            yield Vertical(id="section-options")
        yield Footer()

    def on_mount(self) -> None:
        self._prefs = preferences.load_all()
        self._load_account_info()
        self._update_topbar()
        self._render_section()
        self._update_tabs()

    def _load_account_info(self) -> None:
        token = load_token() or ""
        self._account_token = token
        self._account_scopes = get_token_scopes(token) if token else set()

    # ---------------------------------------------------------------- #
    #  Render
    # ---------------------------------------------------------------- #
    def _section_id(self) -> str:
        return self.SECTIONS[self._active_section]

    def _update_tabs(self) -> None:
        for i, _sid in enumerate(self.SECTIONS):
            tab = self.query_one(f"#tab-{i}", Static)
            tab.set_class(i == self._active_section, "-active")

    def _render_section(self) -> None:
        sid = self._section_id()

        # Actualizar el título del panel derecho (border-title)
        content = self.query_one("#settings-content")
        content.border_title = f" {SECTION_TITLES[sid]} "

        container = self.query_one("#section-options", Vertical)
        container.remove_children()

        if sid == "account":
            self._build_account(container)
        else:
            for row in SETTINGS_CATALOG.get(sid, []):
                row.value = self._prefs.get(row.key, preferences.DEFAULTS.get(row.key))
                container.mount(self._build_row(row))

        count = len(container.children)
        self._active_option = min(self._active_option, max(0, count - 1))
        self._update_highlight()

    def _update_highlight(self) -> None:
        container = self.query_one("#section-options", Vertical)
        for i, child in enumerate(container.children):
            child.set_class(i == self._active_option, "-selected")
        # Auto-scroll al elemento seleccionado
        if container.children:
            container.children[self._active_option].scroll_visible()

    def _update_topbar(self) -> None:
        topbar = self.query_one("#settings-topbar", Static)
        theme_names = {
            "github": "GitHub Dark",
            "tokyo-night": "Tokyo Night",
            "catppuccin-mocha": "Catppuccin",
            "github-light": "GitHub Light",
        }
        theme_display = theme_names.get(self._prefs.get("theme", "github"), "—")
        topbar.update(
            f"{ICON_SLIDERS}  [b]Configuración[/b]   ·   "
            f"{ICON_PALETTE} Tema: [b]{theme_display}[/b]"
        )

    # ---------------------------------------------------------------- #
    #  Fila genérica
    # ---------------------------------------------------------------- #
    def _build_row(self, row: SettingRow) -> Static:
        pending = preferences.is_pending(row.key) and row.kind in ("select", "switch")
        text = self._format_row(row, pending)
        w = Static(text, classes="option", markup=True)
        if pending:
            w.add_class("-pending")
        w.data = {  # type: ignore[attr-defined]
            "key": row.key,
            "label": row.label,
            "kind": row.kind,
            "value": row.value,
            "choices": row.choices,
            "values": row.values,
            "as_markup": row.as_markup,
            "pending": pending,
        }
        return w

    def _format_row(self, row: SettingRow, pending: bool) -> str:
        marker = "  [yellow]⏳[/yellow]" if pending else ""
        if pending:
            # Toda la fila en dim yellow para distinguir a simple vista
            if row.kind == "select":
                idx = (
                    row.values.index(row.value)
                    if row.values and row.value in row.values
                    else 0
                )
                display = row.choices[idx] if row.choices else str(row.value)
                return (
                    f"[dim yellow]{row.label:<26}  ‹ {display} ›{marker}[/dim yellow]"
                )
            if row.kind == "switch":
                state = "✓" if row.value else " "
                return f"[dim yellow]{row.label:<26}  [ {state} ]{marker}[/dim yellow]"
            return f"[dim yellow]{row.label}{marker}[/dim yellow]"

        # Implementado → colores normales
        if row.kind == "select":
            idx = (
                row.values.index(row.value)
                if row.values and row.value in row.values
                else 0
            )
            display = row.choices[idx] if row.choices else str(row.value)
            return (
                f"[b]{row.label:<26}[/b]  [dim]‹[/dim] "
                f"[cyan]{display}[/cyan] [dim]›[/dim]"
            )
        if row.kind == "switch":
            box = "[green]✓[/green]" if row.value else "[dim] [/dim]"
            return f"[b]{row.label:<26}[/b]  [ {box} ]"
        value_str = str(row.value) if row.as_markup else f"[dim]{row.value}[/dim]"
        return f"[b]{row.label:<26}[/b]  {value_str}"

    # ---------------------------------------------------------------- #
    #  Sección Cuenta
    # ---------------------------------------------------------------- #
    def _build_account(self, parent: Vertical) -> None:
        token = self._account_token
        # Token actual
        parent.mount(
            self._build_row(
                SettingRow(
                    "_token_info",
                    "Token actual",
                    "info",
                    value=mask_token(token) if token else "[red]no configurado[/red]",
                    as_markup=True,
                )
            )
        )
        # Contador de permisos
        detected = sum(1 for p in TOKEN_PERMISSIONS if p.scope in self._account_scopes)
        parent.mount(
            self._build_row(
                SettingRow(
                    "_scopes_count",
                    "Permisos detectados",
                    "info",
                    value=f"{detected}/{len(TOKEN_PERMISSIONS)}",
                )
            )
        )
        # Permisos individuales
        for perm in TOKEN_PERMISSIONS:
            has = perm.scope in self._account_scopes
            if has:
                icon, color = "✅", "green"
            elif perm.priority == "required":
                icon, color = "❌", "red"
            elif perm.priority == "future":
                icon, color = "⚠️ ", "yellow"
            else:
                icon, color = "⚪", "dim"
            suffix = ""
            if perm.priority == "future" and not has:
                suffix = " [dim](bloqueará funciones futuras)[/dim]"
            parent.mount(
                self._build_row(
                    SettingRow(
                        f"_perm_{perm.scope}",
                        f"  {icon}  {perm.scope}",
                        "info",
                        value=f"[{color}]{perm.label}[/{color}]{suffix}",
                        as_markup=True,
                    )
                )
            )
        # Acciones
        parent.mount(
            self._build_row(
                SettingRow(
                    "_create_token",
                    "→ Crear nuevo token",
                    "action",
                    value="[dim]Enter para abrir GitHub en el navegador[/dim]",
                    as_markup=True,
                )
            )
        )
        parent.mount(
            self._build_row(
                SettingRow(
                    "_logout",
                    "→ Cerrar sesión",
                    "action",
                    value="[dim]Enter para eliminar el token guardado[/dim]",
                    as_markup=True,
                )
            )
        )

    # ---------------------------------------------------------------- #
    #  Navegación
    # ---------------------------------------------------------------- #
    def on_key(self, event) -> None:
        key = event.key.lower()

        if key == "tab":
            event.stop()
            self._next_section(+1)
        elif key in ("shift+tab", "backtab"):
            event.stop()
            self._next_section(-1)
        elif key in ("up", "k"):
            event.stop()
            self._move_option(-1)
        elif key in ("down", "j"):
            event.stop()
            self._move_option(+1)
        elif key == "left":
            event.stop()
            self._cycle_value(-1)
        elif key == "right":
            event.stop()
            self._cycle_value(+1)
        elif key == "enter":
            event.stop()
            self._activate()
        elif key == "escape":
            event.stop()
            self.app.pop_screen()

    def _next_section(self, delta: int) -> None:
        self._active_section = (self._active_section + delta) % len(self.SECTIONS)
        self._active_option = 0
        self._render_section()
        self._update_tabs()

    def _move_option(self, delta: int) -> None:
        container = self.query_one("#section-options", Vertical)
        n = len(container.children)
        if n == 0:
            return
        self._active_option = (self._active_option + delta) % n
        self._update_highlight()

    def _current_widget(self) -> Static | None:
        container = self.query_one("#section-options", Vertical)
        if not container.children:
            return None
        return container.children[self._active_option]  # type: ignore[return-value]

    # ---------------------------------------------------------------- #
    #  Cambio de valor
    # ---------------------------------------------------------------- #
    def _cycle_value(self, delta: int) -> None:
        w = self._current_widget()
        if w is None:
            return
        data = w.data  # type: ignore[attr-defined]
        kind = data["kind"]

        if kind == "select" and data["values"]:
            values = data["values"]
            idx = values.index(data["value"]) if data["value"] in values else 0
            new_value = values[(idx + delta) % len(values)]
            data["value"] = new_value
            self._redraw_row(w, data)
            self._apply_change(data["key"], new_value)
        elif kind == "switch":
            new_value = not bool(data["value"])
            data["value"] = new_value
            self._redraw_row(w, data)
            self._apply_change(data["key"], new_value)

    def _redraw_row(self, w: Static, data: dict) -> None:
        row = SettingRow(
            key=data["key"],
            label=data["label"],
            kind=data["kind"],
            value=data["value"],
            choices=data["choices"],
            values=data["values"],
            as_markup=data["as_markup"],
        )
        w.update(self._format_row(row, pending=data.get("pending", False)))

    def _apply_change(self, key: str, value) -> None:
        self._prefs[key] = value
        preferences.set_value(key, value)
        if key == "theme":
            self.app.theme = value
            self._update_topbar()  # ← refrescar la línea de contexto
        if preferences.is_pending(key):
            logger.info("Ajuste '%s' guardado (pendiente de implementar)", key)

    # ---------------------------------------------------------------- #
    #  Enter
    # ---------------------------------------------------------------- #
    def _activate(self) -> None:
        w = self._current_widget()
        if w is None:
            return
        data = w.data  # type: ignore[attr-defined]
        if data["kind"] != "action":
            return
        key = data["key"]
        if key == "_create_token":
            url = build_token_creation_url()
            logger.info("Abriendo navegador: %s", url)
            webbrowser.open(url)
            self.notify(
                "🌐 Abriendo GitHub en el navegador…",
                severity="information",
                timeout=3,
            )
        elif key == "_logout":
            self._logout()

    def _logout(self) -> None:
        if not self._account_token:
            self.notify("No hay token guardado.", severity="warning", timeout=2)
            return
        delete_token()
        self._account_token = ""
        self._account_scopes = set()
        self._render_section()
        self.notify("🔒 Token eliminado.", severity="information", timeout=3)
