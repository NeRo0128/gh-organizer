# tests/test_logs_modal.py
"""Tests del modal de logs (parser y formato, sin UI)."""

from gh_organizer.ui.modals.logs_modal import _format_line, _read_tail


def test_read_tail_missing_file(tmp_path):
    """Archivo inexistente → lista vacía."""
    assert _read_tail(tmp_path / "missing.log") == []


def test_read_tail_empty_file(tmp_path):
    """Archivo vacío → lista vacía."""
    f = tmp_path / "empty.log"
    f.write_text("")
    assert _read_tail(f) == []


def test_read_tail_small_file(tmp_path):
    """Archivo pequeño → todas las líneas."""
    f = tmp_path / "small.log"
    f.write_text("\n".join(f"line {i}" for i in range(5)))
    lines = _read_tail(f, n=200)
    assert len(lines) == 5
    assert lines[0] == "line 0"


def test_read_tail_truncates(tmp_path):
    """Pide 3 líneas de 10 → devuelve las últimas 3."""
    f = tmp_path / "log.log"
    f.write_text("\n".join(f"line {i}" for i in range(10)))
    lines = _read_tail(f, n=3)
    assert len(lines) == 3
    assert lines[-1] == "line 9"


def test_format_line_info():
    """INFO se colorea en verde."""
    line = "2026-11-02 08:53:12 [INFO   ] app: hello"
    result = _format_line(line)
    assert "[green]" in result
    assert r"\[INFO" in result


def test_format_line_error():
    """ERROR se colorea en rojo."""
    line = "2026-11-02 08:53:12 [ERROR  ] app: boom"
    assert "[red]" in _format_line(line)


def test_format_line_warning():
    """WARNING se colorea en amarillo."""
    line = "2026-11-02 08:53:12 [WARNING] app: careful"
    assert "[yellow]" in _format_line(line)


def test_format_line_debug():
    """DEBUG se colorea en dim."""
    line = "2026-11-02 08:53:12 [DEBUG  ] app: details"
    assert "[dim]" in _format_line(line)


def test_format_line_no_level():
    """Sin nivel → se devuelve tal cual (escapado)."""
    line = "just a plain line"
    assert _format_line(line) == line


def test_format_line_escapes_user_brackets():
    """Los [ del mensaje se escapan."""
    line = "2026-11-02 [INFO   ] app: value=[abc]"
    result = _format_line(line)
    assert r"\[abc]" in result
