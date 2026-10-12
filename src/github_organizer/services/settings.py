# src/github_organizer/config.py
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

APP_NAME = "github-organizer"

CONFIG_DIR = Path(user_config_dir(APP_NAME))
DATA_DIR = Path(user_data_dir(APP_NAME))
FOLDERS_FILE = DATA_DIR / "folders.json"

TOKEN_ENV_VAR = "GITHUB_TOKEN"


def ensure_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_folders() -> dict:
    import json

    ensure_dirs()
    if not FOLDERS_FILE.exists():
        return {}
    with FOLDERS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_folders(data: dict) -> None:
    import json

    ensure_dirs()
    with FOLDERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
