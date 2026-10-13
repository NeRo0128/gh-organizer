# tests/test_folder_manager.py
"""Tests de FolderManager: creación, asignación, renombrado, borrado y apply_strategy."""

from pathlib import Path

import pytest

from github_organizer.core import Repo
from github_organizer.services import FolderManager
from github_organizer.services.folder import DEFAULT_FOLDERS
from github_organizer.services.organizer import by_language


# ---------------------------------------------------------------------- #
#  Inicialización y defaults
# ---------------------------------------------------------------------- #
def test_default_folders_created_on_first_run(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    for name in DEFAULT_FOLDERS:
        assert fm.exists(name)
        assert fm.get_repos_in_folder(name) == []


def test_existing_data_is_not_overwritten(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.assign_repo("alpha", "Personal")

    fm2 = FolderManager()
    assert fm2.get_repos_in_folder("Personal") == ["alpha"]


def test_folders_file_is_created(tmp_data_dirs: Path) -> None:
    FolderManager()
    assert (tmp_data_dirs / "folders.json").exists()


# ---------------------------------------------------------------------- #
#  Lecturas
# ---------------------------------------------------------------------- #
def test_exists_true_and_false(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    assert fm.exists("Personal") is True
    assert fm.exists("NoExiste") is False


def test_get_repos_in_folder_returns_empty_for_missing(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    assert fm.get_repos_in_folder("NoExiste") == []


def test_get_assigned_repo_names_is_union(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.assign_repo("a", "Personal")
    fm.assign_repo("b", "Trabajo")
    fm.assign_repo("c", "Trabajo")
    assert fm.get_assigned_repo_names() == {"a", "b", "c"}


def test_get_all_returns_internal_dict(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    data = fm.get_all()
    assert set(DEFAULT_FOLDERS).issubset(data.keys())


# ---------------------------------------------------------------------- #
#  Asignación
# ---------------------------------------------------------------------- #
def test_assign_repo_creates_folder_if_missing(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.assign_repo("alpha", "Nueva")
    assert fm.get_repos_in_folder("Nueva") == ["alpha"]


def test_assign_repo_moves_from_previous_folder(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.assign_repo("alpha", "Personal")
    fm.assign_repo("alpha", "Trabajo")
    assert fm.get_repos_in_folder("Personal") == []
    assert fm.get_repos_in_folder("Trabajo") == ["alpha"]


def test_assign_repo_no_duplicates(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.assign_repo("alpha", "Personal")
    fm.assign_repo("alpha", "Personal")
    assert fm.get_repos_in_folder("Personal") == ["alpha"]


def test_remove_repo_removes_from_wherever(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.assign_repo("alpha", "Personal")
    fm.remove_repo("alpha")
    assert fm.get_repos_in_folder("Personal") == []
    assert fm.get_assigned_repo_names() == set()


def test_remove_repo_noop_if_not_assigned(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.remove_repo("no-existe")  # no debe lanzar


# ---------------------------------------------------------------------- #
#  create_folder
# ---------------------------------------------------------------------- #
def test_create_folder_nested_creates_parents(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.create_folder("A/B/C")
    assert fm.exists("A")
    assert fm.exists("A/B")
    assert fm.exists("A/B/C")


def test_create_folder_idempotent(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.create_folder("X/Y")
    fm.create_folder("X/Y")  # no debe duplicar ni fallar
    assert fm.exists("X/Y")


# ---------------------------------------------------------------------- #
#  rename_folder
# ---------------------------------------------------------------------- #
def test_rename_folder_simple(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.create_folder("Viejo")
    new_path = fm.rename_folder("Viejo", "Nuevo")
    assert new_path == "Nuevo"
    assert fm.exists("Nuevo")
    assert not fm.exists("Viejo")


def test_rename_folder_updates_children(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.create_folder("Viejo/Hijo/Nieto")
    fm.rename_folder("Viejo", "Nuevo")
    assert fm.exists("Nuevo/Hijo")
    assert fm.exists("Nuevo/Hijo/Nieto")
    assert not fm.exists("Viejo/Hijo")


def test_rename_folder_raises_if_missing(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    with pytest.raises(KeyError):
        fm.rename_folder("NoExiste", "Otro")


def test_rename_folder_raises_on_empty_name(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.create_folder("X")
    with pytest.raises(ValueError):
        fm.rename_folder("X", "   ")


def test_rename_folder_raises_on_collision(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.create_folder("A")
    fm.create_folder("B")
    with pytest.raises(ValueError):
        fm.rename_folder("A", "B")


def test_rename_folder_same_name_is_noop(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.create_folder("A")
    assert fm.rename_folder("A", "A") == "A"


# ---------------------------------------------------------------------- #
#  delete_folder
# ---------------------------------------------------------------------- #
def test_delete_folder_removes_children(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.create_folder("A/B/C")
    fm.delete_folder("A")
    assert not fm.exists("A")
    assert not fm.exists("A/B")
    assert not fm.exists("A/B/C")


def test_delete_folder_noop_if_missing(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.delete_folder("NoExiste")  # no debe lanzar


# ---------------------------------------------------------------------- #
#  count_descendants
# ---------------------------------------------------------------------- #
def test_count_descendants(tmp_data_dirs: Path) -> None:
    fm = FolderManager()
    fm.create_folder("A/B/C")
    fm.assign_repo("r1", "A")
    fm.assign_repo("r2", "A/B")
    fm.assign_repo("r3", "A/B/C")
    total, sub = fm.count_descendants("A")
    assert total == 3
    assert sub == 2


def test_count_descendants_no_match_prefix(tmp_data_dirs: Path) -> None:
    """'AB' no debe contar como hijo de 'A'."""
    fm = FolderManager()
    fm.create_folder("A")
    fm.create_folder("AB")
    fm.assign_repo("r", "AB")
    total, sub = fm.count_descendants("A")
    assert total == 0
    assert sub == 0


# ---------------------------------------------------------------------- #
#  apply_strategy
# ---------------------------------------------------------------------- #
def test_apply_strategy_only_unassigned(
    tmp_data_dirs: Path, sample_repos: list[Repo]
) -> None:
    fm = FolderManager()
    fm.assign_repo("alpha", "Personal")
    moved, new_folders = fm.apply_strategy(sample_repos, by_language)
    # Solo beta, gamma, delta se mueven; alpha ya estaba asignado
    assert moved == 3
    # by_language crea "Lenguajes/Python", "Lenguajes/Go", "Lenguajes/Sin lenguaje"
    assert new_folders == 3


def test_apply_strategy_returns_zero_when_all_assigned(
    tmp_data_dirs: Path, sample_repos: list[Repo]
) -> None:
    fm = FolderManager()
    for repo in sample_repos:
        fm.assign_repo(repo.name, "Personal")
    moved, new_folders = fm.apply_strategy(sample_repos, by_language)
    assert moved == 0
    assert new_folders == 0


def test_apply_strategy_persists_to_disk(
    tmp_data_dirs: Path, sample_repos: list[Repo]
) -> None:
    fm = FolderManager()
    fm.apply_strategy(sample_repos, by_language)
    fm2 = FolderManager()
    assert "alpha" in fm2.get_repos_in_folder("Lenguajes/Python")
    assert "gamma" in fm2.get_repos_in_folder("Lenguajes/Go")
