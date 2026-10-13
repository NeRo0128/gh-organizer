# tests/test_integration_flow.py
"""Tests end-to-end: flujo completo de uso del FolderManager."""

from pathlib import Path

from github_organizer.core import Repo
from github_organizer.services import FolderManager
from github_organizer.services.organizer import by_language_and_visibility


def test_full_flow_organize_and_persist(
    tmp_data_dirs: Path, sample_repos: list[Repo]
) -> None:
    # 1. Primera ejecución: se crean las carpetas por defecto
    fm = FolderManager()
    assert fm.exists("Personal")
    assert fm.exists("Trabajo")

    # 2. El usuario asigna manualmente un repo
    fm.assign_repo("alpha", "Personal")

    # 3. Auto-organización: solo afecta a los no asignados
    moved, new_folders = fm.apply_strategy(sample_repos, by_language_and_visibility)
    assert moved == 3
    assert new_folders > 0

    # 4. Comprobamos el reparto
    assert fm.get_repos_in_folder("Personal") == ["alpha"]
    assert "beta" in fm.get_repos_in_folder("Privados/Python")
    assert "gamma" in fm.get_repos_in_folder("Públicos/Go")

    # 5. Simulamos reinicio: nuevo FolderManager lee de disco
    fm2 = FolderManager()
    assert fm2.get_repos_in_folder("Personal") == ["alpha"]
    assert fm2.get_assigned_repo_names() == {"alpha", "beta", "gamma", "delta"}


def test_move_repo_between_folders_persists(
    tmp_data_dirs: Path, sample_repos: list[Repo]
) -> None:
    fm = FolderManager()
    fm.assign_repo("alpha", "Personal")
    fm.assign_repo("alpha", "Trabajo")

    fm2 = FolderManager()
    assert fm2.get_repos_in_folder("Personal") == []
    assert fm2.get_repos_in_folder("Trabajo") == ["alpha"]


def test_delete_then_recreate(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.create_folder("Temporal")
    fm.delete_folder("Temporal")
    assert not fm.exists("Temporal")

    fm.create_folder("Temporal")
    assert fm.exists("Temporal")
    assert fm.get_repos_in_folder("Temporal") == []
