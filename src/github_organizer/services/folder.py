# src/github_organizer/services/folder.py
import logging

from github_organizer.core import Repo
from github_organizer.services import config
from github_organizer.services.organizer import Strategy

logger = logging.getLogger(__name__)

DEFAULT_FOLDERS = ["Personal", "Trabajo", "Proyectos", "Archivados"]


class FolderManager:
    """Gestiona la organización personalizada de repositorios en carpetas."""

    def __init__(self) -> None:
        self._data: dict[str, list[str]] = config.load().get("folders", {})
        self._ensure_defaults()
        logger.debug("FolderManager inicializado con %d carpetas", len(self._data))

    def _save(self) -> None:
        """Guarda solo la sección de carpetas en el config global."""
        full_config = config.load()
        full_config["folders"] = self._data
        config.save(full_config)

    def _ensure_defaults(self) -> None:
        """Crea las carpetas por defecto si el archivo está vacío (primera ejecución)."""
        if self._data:
            return
        logger.info(
            "Primera ejecución: creando carpetas por defecto %s", DEFAULT_FOLDERS
        )
        for name in DEFAULT_FOLDERS:
            self._data[name] = []
        self._save()

    # ------------------------------------------------------------------ #
    #  Lecturas
    # ------------------------------------------------------------------ #
    def get_all(self) -> dict[str, list[str]]:
        return self._data

    def exists(self, folder_path: str) -> bool:
        return folder_path in self._data

    def get_repos_in_folder(self, folder_path: str) -> list[str]:
        return self._data.get(folder_path, [])

    def get_assigned_repo_names(self) -> set[str]:
        assigned: set[str] = set()
        for repos in self._data.values():
            assigned.update(repos)
        logger.debug("Repos asignados en total: %d", len(assigned))
        return assigned

    # ------------------------------------------------------------------ #
    #  Asignación de repos
    # ------------------------------------------------------------------ #
    def assign_repo(self, repo_name: str, folder_path: str) -> None:
        logger.debug("assign_repo(%r, %r)", repo_name, folder_path)
        self._remove_from_all(repo_name)
        self._data.setdefault(folder_path, []).append(repo_name)
        self._save()
        logger.info("Repo %r asignado a %r", repo_name, folder_path)

    def remove_repo(self, repo_name: str) -> None:
        logger.debug("remove_repo(%r)", repo_name)
        self._remove_from_all(repo_name)
        self._save()
        logger.info("Repo %r desasignado", repo_name)

    def _remove_from_all(self, repo_name: str) -> None:
        for repos in self._data.values():
            if repo_name in repos:
                repos.remove(repo_name)

    # ------------------------------------------------------------------ #
    #  Gestión de carpetas
    # ------------------------------------------------------------------ #
    def create_folder(self, folder_path: str) -> None:
        logger.debug("create_folder(%r)", folder_path)
        parts = folder_path.split("/")
        created: list[str] = []
        for i in range(1, len(parts) + 1):
            partial = "/".join(parts[:i])
            if partial not in self._data:
                self._data[partial] = []
                created.append(partial)
        if created:
            self._save()
            logger.info("Carpetas creadas: %s", created)
        else:
            logger.debug("create_folder: %r ya existía", folder_path)

    def rename_folder(self, old_path: str, new_name: str) -> str:
        logger.debug("rename_folder(%r, %r)", old_path, new_name)
        if old_path not in self._data:
            raise KeyError(f"No existe la carpeta: {old_path}")

        new_name = new_name.strip().strip("/")
        if not new_name:
            raise ValueError("El nombre no puede estar vacío")

        parts = old_path.split("/")
        parts[-1] = new_name
        new_path = "/".join(parts)

        if new_path == old_path:
            return old_path
        if new_path in self._data:
            raise ValueError(f"Ya existe una colección con esa ruta: {new_path}")

        new_data: dict[str, list[str]] = {}
        for path, repos in self._data.items():
            if path == old_path:
                new_data[new_path] = repos
            elif path.startswith(old_path + "/"):
                suffix = path[len(old_path) :]
                new_data[new_path + suffix] = repos
            else:
                new_data[path] = repos

        self._data = new_data
        self._save()
        logger.info("Carpeta renombrada: %r → %r", old_path, new_path)
        return new_path

    def delete_folder(self, path: str) -> None:
        logger.debug("delete_folder(%r)", path)
        to_delete = [p for p in self._data if p == path or p.startswith(path + "/")]
        for p in to_delete:
            del self._data[p]
        self._save()
        logger.info("Carpetas eliminadas: %s", to_delete)

    def count_descendants(self, path: str) -> tuple[int, int]:
        total_repos = 0
        subfolders = 0
        for p, repo_list in self._data.items():
            if p == path:
                total_repos += len(repo_list)
            elif p.startswith(path + "/"):
                total_repos += len(repo_list)
                subfolders += 1
        logger.debug(
            "count_descendants(%r) → %d repos, %d subcarpetas",
            path,
            total_repos,
            subfolders,
        )
        return total_repos, subfolders

    # ------------------------------------------------------------------ #
    #  Auto-organización
    # ------------------------------------------------------------------ #
    def apply_strategy(
        self, repos: list[Repo], strategy_fn: Strategy
    ) -> tuple[int, int]:
        """Aplica una estrategia SOLO a los repos no asignados.

        Returns:
            (repos_movidos, carpetas_creadas)
        """
        assigned = self.get_assigned_repo_names()
        unassigned = [r for r in repos if r.name not in assigned]
        if not unassigned:
            logger.info("apply_strategy: no hay repos sin asignar")
            return 0, 0

        plan = strategy_fn(unassigned)
        folders_before = set(self._data.keys())

        for folder, repo_names in plan.items():
            self._data.setdefault(folder, [])
            for name in repo_names:
                self._data[folder].append(name)

        self._save()
        new_folders = set(self._data.keys()) - folders_before
        logger.info(
            "apply_strategy: %d repos movidos, %d carpetas nuevas",
            len(unassigned),
            len(new_folders),
        )
        return len(unassigned), len(new_folders)
