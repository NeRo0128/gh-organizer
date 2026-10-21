# src/github_organizer/services/tree_state.py
"""Persistencia del estado de expansión del árbol en config.toml."""

import logging

from github_organizer.services import config

logger = logging.getLogger(__name__)

MODE_REMEMBER = "remember"
MODE_EXPANDED = "expanded"
MODE_COLLAPSED = "collapsed"

DEFAULT_MODE = MODE_REMEMBER


def load_expanded_paths() -> set[str]:
    """Carga el conjunto de rutas expandidas desde config.toml."""
    data = config.load()
    paths = data.get("tree_state", {}).get("expanded_paths", [])
    logger.debug("tree_state cargado: %d rutas expandidas", len(paths))
    return set(paths)


def save_expanded_paths(paths: set[str]) -> None:
    """Guarda el conjunto de rutas expandidas en config.toml."""
    full_config = config.load()
    full_config["tree_state"] = {"expanded_paths": sorted(paths)}
    config.save(full_config)
    logger.debug("tree_state guardado: %d rutas expandidas", len(paths))
