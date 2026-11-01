# tests/test_exceptions.py
"""Contrato de la jerarquía de excepciones de dominio."""

import inspect

import pytest

from gh_organizer.core import exceptions as exc


def _all_error_classes() -> list[type[exc.GhOrganizerError]]:
    return [
        obj
        for _name, obj in inspect.getmembers(exc, inspect.isclass)
        if issubclass(obj, exc.GhOrganizerError)
    ]


def test_hierarchy_is_complete() -> None:
    classes = _all_error_classes()
    # GhOrganizerError + todas sus subclases del módulo
    assert exc.GhOrganizerError in classes
    assert len(classes) > 15


@pytest.mark.parametrize("cls", _all_error_classes(), ids=lambda c: c.__name__)
def test_every_exception_has_a_user_message(cls: type[exc.GhOrganizerError]) -> None:
    """Si no hay mensaje amigable, el error no debería existir."""
    message = cls.user_message
    assert isinstance(message, str)
    assert message.strip()
    assert message == message.strip()


@pytest.mark.parametrize("cls", _all_error_classes(), ids=lambda c: c.__name__)
def test_every_exception_is_domain_error(cls: type[exc.GhOrganizerError]) -> None:
    error = cls()
    assert isinstance(error, exc.GhOrganizerError)
    assert isinstance(error, Exception)


def test_default_message_falls_back_to_user_message() -> None:
    error = exc.GhOrganizerError()
    assert str(error) == exc.GhOrganizerError.user_message


def test_user_message_can_be_overridden_per_instance() -> None:
    error = exc.GhOrganizerError(message="boom", user_message="💥 petó")
    assert error.user_message == "💥 petó"
    assert str(error) == "boom"


def test_missing_scope_includes_scope_name() -> None:
    error = exc.MissingScopeError("read:user")
    assert "read:user" in error.user_message
    assert error.missing_scope == "read:user"


def test_repo_access_error_includes_repo_name() -> None:
    assert "user/repo" in exc.RepoAccessError("user/repo").user_message


def test_clone_errors_include_path() -> None:
    assert "/tmp/x" in exc.TargetExistsError("/tmp/x").user_message
    assert "/tmp/x" in exc.ClonePermissionError("/tmp/x").user_message


def test_git_clone_failed_keeps_detail() -> None:
    error = exc.GitCloneFailedError("fatal: repository not found")
    assert "repository not found" in error.user_message
    assert error.detail == "fatal: repository not found"


def test_git_clone_failed_without_detail_ends_in_period() -> None:
    assert exc.GitCloneFailedError().user_message.endswith(".")


def test_folder_errors_keep_builtin_compatibility() -> None:
    """Los consumidores antiguos capturaban KeyError/ValueError."""
    assert isinstance(exc.FolderNotFoundError("A"), KeyError)
    assert isinstance(exc.FolderExistsError("A"), ValueError)
    assert isinstance(exc.InvalidFolderNameError(), ValueError)


def test_folder_not_found_str_has_no_keyerror_quotes() -> None:
    assert (
        str(exc.FolderNotFoundError("Trabajo"))
        == exc.FolderNotFoundError("Trabajo").args[0]
    )
    assert "'" not in str(exc.FolderNotFoundError("Trabajo"))


def test_no_builtin_shadowing() -> None:
    """`PermissionError` no debe existir en el módulo: sombrearía el builtin."""
    assert not hasattr(exc, "PermissionError")
    assert hasattr(exc, "ClonePermissionError")


def test_config_write_error_includes_hint() -> None:
    message = exc.ConfigWriteError().user_message
    assert "~/.config/github-organizer/" in message
