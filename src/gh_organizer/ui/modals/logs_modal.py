# src/gh_organizer/ui/modals/logs_modal.py
"""Modal para ver los logs de la aplicación en tiempo real."""

import logging
import re
import shutil
import subprocess
import webbrowser
from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Center, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from gh_organizer.i18n import _
from gh_organizer.services.settings import LOG_DIR, LOG_FILE
from gh_organizer.ui import keybindings
from gh_organizer.ui.styles import MODALS_CSS

logger = logging.getLogger(__name__)

_TAIL_LINES = 200
_MAX_BYTES = 100_000

_LEVEL_COLORS = {
    "DEBUG": "dim",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold red",
}

_LEVEL_RE = re.compile(r"\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*\]")


def _read_tail(path: Path, n: int = _TAIL_LINES) -> list[str]:
    """Lee las últimas `n` líneas del archivo sin cargarlo entero."""
    if not path.exists():
        return []
    try:
        size = path.stat().st_size
        if size == 0:
            return []
        # Archivos pequeños: leer todo
        if size < _MAX_BYTES:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            return [ln.rstrip("\n") for ln in lines[-n:]]
        # Archivos grandes: leer solo el final
        with path.open("rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - _MAX_BYTES))
            data = f.read().decode("utf-8", errors="replace")
        return data.splitlines()[-n:]
    except OSError as e:
        logger.warning("No se pudo leer %s: %s", path, e)
        return []


def _format_line(line: str) -> str:
    """Colorea una línea de log según su nivel."""
    escaped = line.replace("[", r"\[")
    m = _LEVEL_RE.search(line)
    if m:
        color = _LEVEL_COLORS.get(m.group(1))
        if color:
            return f"[{color}]{escaped}[/{color}]"
    return escaped


def _copy_to_clipboard(text: str) -> tuple[bool, str]:
    """Copia texto al portapapeles usando la herramienta del sistema."""
    candidates: list[list[str]] = []
    if shutil.which("wl-copy"):
        candidates.append(["wl-copy"])
    if shutil.which("xclip"):
        candidates.append(["xclip", "-selection", "clipboard"])
    if shutil.which("xsel"):
        candidates.append(["xsel", "--clipboard", "--input"])
    if shutil.which("pbcopy"):
        candidates.append(["pbcopy"])

    if not candidates:
        return False, _(
            "No hay herramienta de portapapeles (instala wl-clipboard o xclip)."
        )

    for cmd in candidates:
        try:
            subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                check=True,
                timeout=5,
            )
            return True, ""
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Falló %s: %s", cmd[0], e)
            continue
    return False, _("Ninguna herramienta de portapapeles funcionó.")


class LogsModal(ModalScreen[None]):
    """Modal con las últimas líneas del archivo de log."""

    BINDINGS: ClassVar[list[BindingType]] = keybindings.LOGS
    CSS_PATH = MODALS_CSS

    CSS = """
    #logs-box {
        width: 110;
        height: 42;
        max-height: 92%;
    }

    #logs-content {
        height: 1fr;
        border: round $primary;
        padding: 0 1;
        background: $surface;
    }

    #logs-text {
        height: auto;
    }

    #logs-path {
        margin-top: 1;
        color: $text-muted;
        height: auto;
    }

    #logs-buttons {
        margin-top: 1;
        height: auto;
    }

    #logs-buttons Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Center(), Vertical(id="logs-box", classes="modal-box") as box:
            box.border_title = f" {_('Logs')} "
            yield Static(_("📋 Registros de la aplicación"), classes="modal-title")

            with VerticalScroll(id="logs-content"):
                yield Static(self._render_content(), id="logs-text", markup=True)

            yield Static(
                f"[dim]{_('Ruta')}:[/dim] {LOG_FILE}",
                id="logs-path",
                markup=True,
            )

            with Center(), Horizontal(id="logs-buttons"):
                yield Button(_("Copiar"), id="btn-copy", variant="primary")
                yield Button(_("Abrir carpeta"), id="btn-folder")
                yield Button(_("Refrescar"), id="btn-refresh")
                yield Button(_("Cerrar"), id="btn-close", variant="error")

    def _render_content(self) -> str:
        lines = _read_tail(LOG_FILE)
        if not lines:
            return f"[dim italic]{_('No hay logs disponibles todavía.')}[/dim italic]"
        return "\n".join(_format_line(ln) for ln in lines)

    # ---------------------------------------------------------------- #
    #  Acciones
    # ---------------------------------------------------------------- #
    def action_close(self) -> None:
        self.dismiss(None)

    def action_refresh(self) -> None:
        self.query_one("#logs-text", Static).update(self._render_content())
        self.notify(_("Logs actualizados"), timeout=2)

    def action_copy(self) -> None:
        try:
            content = LOG_FILE.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.warning("No se pudo leer el log: %s", e)
            self.notify(
                _("❌ No se pudo leer el archivo de log"),
                severity="error",
                timeout=3,
            )
            return
        ok, error = _copy_to_clipboard(content)
        if ok:
            self.notify(_("✅ Logs copiados al portapapeles"), timeout=3)
        else:
            self.notify(f"❌ {error}", severity="error", timeout=5)

    def action_open_folder(self) -> None:
        webbrowser.open(f"file://{LOG_DIR}")
        self.notify(_("📂 Abriendo carpeta de logs"), timeout=2)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button.id
        if btn == "btn-copy":
            self.action_copy()
        elif btn == "btn-folder":
            self.action_open_folder()
        elif btn == "btn-refresh":
            self.action_refresh()
        elif btn == "btn-close":
            self.action_close()
