#!/usr/bin/env python3
"""Herramienta de internacionalización de GitHub Organizer.

Uso::

    uv run python scripts/i18n.py compile     # .po → .mo (todos los idiomas)
    uv run python scripts/i18n.py stats       # entradas sin traducir
    uv run python scripts/i18n.py new-lang fr # esqueleto de un idioma nuevo

El compilador es Python puro (stdlib): no hace falta tener instalado
``gettext``/``msgfmt`` ni añadir dependencias, y el resultado binario se
regenera idéntico en cualquier máquina.
"""

from __future__ import annotations

import ast
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
LOCALES = SRC / "gh_organizer" / "locales"
DOMAIN = "gh_organizer"
SOURCE_LANGUAGE = "es"


# ---------------------------------------------------------------------- #
#  Parser .po mínimo (suficiente para nuestros catálogos)
# ---------------------------------------------------------------------- #
def parse_po(path: Path) -> dict[str, str]:
    """Devuelve {msgid: msgstr} de un catálogo .po.

    Soporta comentarios, entradas vacías, ``msgid_plural`` (se ignora) y
    strings partidas en varias líneas.
    """
    entries: dict[str, str] = {}
    msgid: str | None = None
    msgstr = ""
    current = None  # "msgid" | "msgstr" | None
    saw_plural = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("msgid_plural"):
            saw_plural = True
            current = None
            continue
        if line.startswith("msgid "):
            if msgid is not None and not saw_plural:
                entries[msgid] = msgstr
            msgid = _unquote(line[len("msgid ") :])
            msgstr = ""
            saw_plural = False
            current = "msgid"
            continue
        if line.startswith("msgstr "):
            msgstr = _unquote(line[len("msgstr ") :])
            current = "msgstr"
            continue
        if line.startswith('"'):
            if current == "msgid":
                msgid = (msgid or "") + _unquote(line)
            elif current == "msgstr":
                msgstr += _unquote(line)
            continue

    if msgid is not None and not saw_plural:
        entries[msgid] = msgstr
    return entries


def _unquote(literal: str) -> str:
    """``"a\\nb"`` → ``a<salto>b`` (respeta el charset UTF-8 del archivo)."""
    try:
        return ast.literal_eval(literal.strip())
    except (SyntaxError, ValueError):
        return literal.strip().strip('"')


# ---------------------------------------------------------------------- #
#  Escritor .mo (formato GNU gettext)
# ---------------------------------------------------------------------- #
def compile_catalog(po_path: Path, mo_path: Path) -> int:
    """Compila ``po_path`` en ``mo_path`` y devuelve el nº de entradas."""
    entries = {k: v for k, v in parse_po(po_path).items() if v or k == ""}
    if "" not in entries:
        entries[""] = (
            "Content-Type: text/plain; charset=UTF-8\n"
            "Content-Transfer-Encoding: 8bit\n"
            f"Language: {po_path.parent.parent.name}\n"
        )

    # gettext exige las claves ordenadas para su búsqueda binaria.
    keys = sorted(entries, key=lambda k: k.encode("utf-8"))
    values = [entries[k].encode("utf-8") for k in keys]
    ids = [k.encode("utf-8") for k in keys]

    n = len(keys)
    keystart = 7 * 4 + 16 * n
    offsets = []
    offset = keystart
    for raw in ids:
        offsets.append((len(raw), offset))
        offset += len(raw) + 1
    for raw in values:
        offsets.append((len(raw), offset))
        offset += len(raw) + 1

    output = bytearray()
    output += struct.pack(
        "<7I",
        0x950412DE,  # magic
        0,  # versión
        n,  # nº de strings
        28,  # offset de la tabla de msgid
        28 + 8 * n,  # offset de la tabla de msgstr
        0,  # tamaño de la tabla hash (sin hash)
        keystart + sum(len(raw) + 1 for raw in ids + values),
    )
    for length, start in offsets:
        output += struct.pack("<2I", length, start)
    for raw in ids + values:
        output += raw + b"\0"

    mo_path.parent.mkdir(parents=True, exist_ok=True)
    mo_path.write_bytes(bytes(output))
    return n


# ---------------------------------------------------------------------- #
#  Comandos
# ---------------------------------------------------------------------- #
def cmd_compile() -> int:
    total = 0
    for po_path in sorted(LOCALES.glob("*/LC_MESSAGES/*.po")):
        mo_path = po_path.with_suffix(".mo")
        count = compile_catalog(po_path, mo_path)
        print(f"  {po_path.parent.parent.name}: {count} entradas → {mo_path.name}")
        total += 1
    if not total:
        print("No se encontró ningún .po", file=sys.stderr)
        return 1
    print(f"Compilados {total} catálogos.")
    return 0


def source_msgids() -> set[str]:
    """Todos los msgid literales que aparecen en el código (``_("...")``)."""
    found: set[str] = set()
    for path in SRC.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_"
                and node.args
            ):
                try:
                    value = ast.literal_eval(node.args[0])
                except (ValueError, SyntaxError):
                    continue  # msgid dinámico: _(row.label)
                if isinstance(value, str):
                    found.add(value)
    return found


def cmd_stats() -> int:
    reference = parse_po(LOCALES / SOURCE_LANGUAGE / "LC_MESSAGES" / f"{DOMAIN}.po")
    missing_in_source = source_msgids() - set(reference)
    if missing_in_source:
        print(f"msgid usados en el código y ausentes del .po ({SOURCE_LANGUAGE}):")
        for msg in sorted(missing_in_source):
            print(f"  - {msg!r}")

    status = 0
    for po_path in sorted(LOCALES.glob("*/LC_MESSAGES/*.po")):
        lang = po_path.parent.parent.name
        entries = parse_po(po_path)
        untranslated = [
            msgid for msgid, msgstr in entries.items() if msgid and not msgstr
        ]
        print(
            f"{lang}: {len(entries)} entradas, {len(untranslated)} sin traducir"
        )
        for msgid in untranslated:
            print(f"  - {msgid!r}")
        if missing_in_source or untranslated:
            status = 1
    return status


def cmd_new_lang(lang: str) -> int:
    reference = LOCALES / SOURCE_LANGUAGE / "LC_MESSAGES" / f"{DOMAIN}.po"
    if not reference.exists():
        print(f"No existe el catálogo de referencia {reference}", file=sys.stderr)
        return 1
    target = LOCALES / lang / "LC_MESSAGES" / f"{DOMAIN}.po"
    if target.exists():
        print(f"{target} ya existe", file=sys.stderr)
        return 1
    header = reference.read_text(encoding="utf-8").split("msgid")[0]
    header = header.replace(f'"Language: {SOURCE_LANGUAGE}\\n"', f'"Language: {lang}\\n"')
    entries = parse_po(reference)
    chunks = [header]
    for msgid in sorted(entries):
        if not msgid:
            continue
        literal = '"' + msgid.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
        chunks.append(f"msgid {literal}\nmsgstr \"\"\n")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(chunks), encoding="utf-8")
    print(f"Creado {target} ({len(chunks) - 1} entradas por traducir).")
    print("Recuerda añadir el idioma a SUPPORTED_LANGUAGES en src/gh_organizer/i18n.py")
    return 0


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "compile"
    if command == "compile":
        return cmd_compile()
    if command == "stats":
        return cmd_stats()
    if command == "new-lang":
        if len(argv) < 3:
            print("Uso: scripts/i18n.py new-lang <código>", file=sys.stderr)
            return 2
        return cmd_new_lang(argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
