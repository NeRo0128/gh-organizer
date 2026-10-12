# src/github_organizer/services/folder.py
import logging

from github_organizer.services.settings import load_folders, save_folders

logger = logging.getLogger(__name__)


class FolderManager:
    """Gestiona la organización personalizada de repositorios en carpetas."""

    def __init__(self) -> None:
        self._data: dict[str, list[str]] = load_folders()
        logger.debug("FolderManager inicializado con %d carpetas", len(self._data))

    # ------------------------------------------------------------------ #
    #  Lecturas
    # ------------------------------------------------------------------ #
    def get_all(self) -> dict[str, list[str]]:
        return self._data

    def exists(self, folder_path: str) -> bool:
        """Comprueba si una carpeta existe en el JSON."""
        return folder_path in self._data

    def get_repos_in_folder(self, folder_path: str) -> list[str]:
        return self._data.get(folder_path, [])

    def get_assigned_repo_names(self) -> set[str]:
        """Devuelve todos los nombres de repo que ya están en alguna carpeta."""
        assigned: set[str] = set()
        for repos in self._data.values():
            assigned.update(repos)
        logger.debug("Repos asignados en total: %d", len(assigned))
        return assigned

    # ------------------------------------------------------------------ #
    #  Asignación de repos
    # ------------------------------------------------------------------ #
    def assign_repo(self, repo_name: str, folder_path: str) -> None:
        """Asigna un repo a una carpeta, quitándolo de cualquier otra."""
        logger.debug("assign_repo(%r, %r)", repo_name, folder_path)
        self._remove_from_all(repo_name)
        self._data.setdefault(folder_path, []).append(repo_name)
        save_folders(self._data)
        logger.info("Repo %r asignado a %r", repo_name, folder_path)

    def remove_repo(self, repo_name: str) -> None:
        """Quita un repo de todas las carpetas."""
        logger.debug("remove_repo(%r)", repo_name)
        self._remove_from_all(repo_name)
        save_folders(self._data)
        logger.info("Repo %r desasignado", repo_name)

    def _remove_from_all(self, repo_name: str) -> None:
        for repos in self._data.values():
            if repo_name in repos:
                repos.remove(repo_name)

    # ------------------------------------------------------------------ #
    #  Gestión de carpetas
    # ------------------------------------------------------------------ #
    def create_folder(self, folder_path: str) -> None:
        """Crea la carpeta y todos sus padres intermedios si no existen."""
        logger.debug("create_folder(%r)", folder_path)
        parts = folder_path.split("/")
        created: list[str] = []
        for i in range(1, len(parts) + 1):
            partial = "/".join(parts[:i])
            if partial not in self._data:
                self._data[partial] = []
                created.append(partial)
        if created:
            save_folders(self._data)
            logger.info("Carpetas creadas: %s", created)
        else:
            logger.debug("create_folder: %r ya existía", folder_path)

    def rename_folder(self, old_path: str, new_name: str) -> str:
        """Renombra una carpeta y todas sus descendientes.

        Returns:
            La nueva ruta completa.

        Raises:
            KeyError: si old_path no existe.
            ValueError: si new_name está vacío o ya hay una carpeta con ese nombre.
        """
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
            logger.debug("rename_folder: no-op (mismo nombre)")
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
        save_folders(self._data)
        logger.info("Carpeta renombrada: %r → %r", old_path, new_path)
        return new_path

    def delete_folder(self, path: str) -> None:
        """Elimina una carpeta, sus descendientes y desasigna sus repos."""
        logger.debug("delete_folder(%r)", path)
        to_delete = [p for p in self._data if p == path or p.startswith(path + "/")]
        for p in to_delete:
            del self._data[p]
        save_folders(self._data)
        logger.info("Carpetas eliminadas: %s", to_delete)

    def count_descendants(self, path: str) -> tuple[int, int]:
        """Devuelve (repos, subcarpetas) contando esta carpeta y sus descendientes."""
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
