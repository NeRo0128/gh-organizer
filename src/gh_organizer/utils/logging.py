# src/gh_organizer/utils/logging.py
"""Configuración central de logging de la aplicación.

El logging va a archivo porque Textual se apodera de stdout/stderr.
Para activar DEBUG: export GH_ORG_LOG=DEBUG
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from gh_organizer.services.settings import LOG_DIR, LOG_FILE

_FORMAT = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Loggers de terceros que son ruidosos
_NOISY_LOGGERS = ["urllib3", "requests", "charset_normalizer"]


def setup_logging(level: str | None = None) -> None:
    """Configura el logging raíz de la app.

    Args:
        level: "DEBUG", "INFO", "WARNING", "ERROR" o "OFF".
               Si es None, lee de GH_ORG_LOG (default: INFO).
    """
    if level is None:
        level = os.environ.get("GH_ORG_LOG", "INFO").upper()

    if level == "OFF":
        logging.getLogger("gh_organizer").setLevel(logging.CRITICAL + 1)
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("gh_organizer")
    logger.setLevel(level)
    logger.handlers.clear()  # evita duplicados en reload

    # Handler de archivo con rotación
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT))
    logger.addHandler(handler)

    # Silenciar terceros ruidosos
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    # PyGithub: solo activar en DEBUG
    logging.getLogger("github").setLevel(
        logging.DEBUG if level == "DEBUG" else logging.WARNING
    )

    logger.info("=" * 60)
    logger.info("Logging inicializado (nivel=%s, archivo=%s)", level, LOG_FILE)
