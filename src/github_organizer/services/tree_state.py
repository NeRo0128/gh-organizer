# src/github_organizer/services/tree_state.py
"""Persistencia del estado de expansión del árbol de carpetas.

Guarda qué rutas están expandidas para que al reabrir la app el usuario
encuentre el árbol como lo dejó.

Modos (por ahora constantes, se moverán a settings cuando exista esa pantalla):
- remember: usar el estado guardado
- expanded: iniciar todo expandido
- collapsed: iniciar todo colapsado
"""

import json
import logging

from github_organizer.services.settings import DATA_DIR, ensure_dirs

logger = logging.getLogger(__name__)

TREE_STATE_FILE = DATA_DIR / "tree_state.json"

MODE_REMEMBER = "remember"
MODE_EXPANDED = "expanded"
MODE_COLLAPSED = "collapsed"

# 👈 Cambiar aquí para probar otros modos hasta que exista la pantalla de settings
DEFAULT_MODE = MODE_REMEMBER


def load_expanded_paths() -> set[str]:
    """Carga el conjunto de rutas expandidas desde disco."""
    ensure_dirs()
    if not TREE_STATE_FILE.exists():
        logger.debug("tree_state.json no existe, empezando vacío")
        return set()
    try:
        with TREE_STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        paths = set(data.get("expanded_paths", []))
        logger.debug("tree_state cargado: %d rutas expandidas", len(paths))
        return paths
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Error leyendo tree_state.json: %s", e)
        return set()


def save_expanded_paths(paths: set[str]) -> None:
    """Guarda el conjunto de rutas expandidas a disco."""
    ensure_dirs()
    try:
        with TREE_STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump({"expanded_paths": sorted(paths)}, f, indent=2)
        logger.debug("tree_state guardado: %d rutas expandidas", len(paths))
    except OSError as e:
        logger.error("Error escribiendo tree_state.json: %s", e)
