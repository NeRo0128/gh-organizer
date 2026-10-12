# src/github_organizer/services/folder.py
from github_organizer.services.settings import (  # 👈 antes: config
    load_folders,
    save_folders,
)


class FolderManager:
    """Gestiona la organización personalizada de repositorios en carpetas."""

    def __init__(self):
        self._data: dict[str, list[str]] = load_folders()

    def get_all(self) -> dict[str, list[str]]:
        return self._data

    def get_repos_in_folder(self, folder_path: str) -> list[str]:
        return self._data.get(folder_path, [])

    def get_assigned_repo_names(self) -> set[str]:
        """Devuelve todos los nombres de repo que ya están en alguna carpeta."""
        assigned: set[str] = set()
        for repos in self._data.values():
            assigned.update(repos)
        return assigned

    def assign_repo(self, repo_name: str, folder_path: str) -> None:
        """Asigna un repo a una carpeta, quitándolo de cualquier otra."""
        self._remove_from_all(repo_name)
        self._data.setdefault(folder_path, []).append(repo_name)
        save_folders(self._data)

    def remove_repo(self, repo_name: str) -> None:
        """Quita un repo de todas las carpetas."""
        self._remove_from_all(repo_name)
        save_folders(self._data)

    def create_folder(self, folder_path: str) -> None:
        if folder_path not in self._data:
            self._data[folder_path] = []
            save_folders(self._data)

    def delete_folder(self, folder_path: str) -> None:
        self._data.pop(folder_path, None)
        save_folders(self._data)

    def _remove_from_all(self, repo_name: str) -> None:
        for repos in self._data.values():
            if repo_name in repos:
                repos.remove(repo_name)
