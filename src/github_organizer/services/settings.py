# src/github_organizer/services/settings.py
import json
import logging
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir, user_log_dir

logger = logging.getLogger(__name__)

APP_NAME = "github-organizer"

CONFIG_DIR = Path(user_config_dir(APP_NAME))
DATA_DIR = Path(user_data_dir(APP_NAME))
LOG_DIR = Path(user_log_dir(APP_NAME))
FOLDERS_FILE = DATA_DIR / "folders.json"
LOG_FILE = LOG_DIR / "app.log"
TOKEN_ENV_VAR = "GITHUB_TOKEN"


def ensure_dirs() -> None:
    """Crea los directorios necesarios si no existen."""
    for d in (CONFIG_DIR, DATA_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


def load_folders() -> dict:
    """Carga el archivo JSON de carpetas. Devuelve {} si no existe."""
    ensure_dirs()
    if not FOLDERS_FILE.exists():
        logger.debug("folders.json no existe todavía, devolviendo {}")
        return {}
    try:
        with FOLDERS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("folders.json cargado: %d claves", len(data))
        return data
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Error leyendo folders.json: %s", e)
        return {}


def save_folders(data: dict) -> None:
    """Guarda el archivo JSON de carpetas."""
    ensure_dirs()
    try:
        with FOLDERS_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug("folders.json guardado: %d claves", len(data))
    except OSError as e:
        logger.error("Error escribiendo folders.json: %s", e)
        raise
