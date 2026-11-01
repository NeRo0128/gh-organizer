# tests/test_error_handling.py
"""Traducción de excepciones de terceros a excepciones de dominio.

Ningún ``GithubException`` / ``OSError`` / ``RequestException`` /
``SubprocessError`` debe llegar a la UI.
"""

import errno
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests
from github import (
    BadCredentialsException,
    GithubException,
    RateLimitExceededException,
    UnknownObjectException,
)

from gh_organizer.core import exceptions as exc
from gh_organizer.services import config, tokens
from gh_organizer.services import git as git_service
from gh_organizer.services.github import GitHubClient
from gh_organizer.utils.errors import (
    from_config_write,
    from_git_clone,
    from_github,
    from_os_error,
    from_request,
    from_subprocess_error,
    github_errors,
)


# ---------------------------------------------------------------------- #
#  from_github
# ---------------------------------------------------------------------- #
def test_401_becomes_invalid_token() -> None:
    error = from_github(BadCredentialsException(401, {"message": "Bad credentials"}))
    assert isinstance(error, exc.InvalidTokenError)


def test_403_becomes_missing_scope() -> None:
    error = from_github(GithubException(403, {"message": "Resource not accessible"}))
    assert isinstance(error, exc.MissingScopeError)
    assert error.missing_scope == "repo"


def test_404_becomes_repo_access_error() -> None:
    error = from_github(UnknownObjectException(404, {"message": "Not Found"}))
    assert isinstance(error, exc.RepoAccessError)


def test_rate_limit_subclass_wins_over_403() -> None:
    error = from_github(RateLimitExceededException(403, {"message": "rate limited"}))
    assert isinstance(error, exc.RateLimitError)


def test_403_with_zero_remaining_is_rate_limit() -> None:
    error = from_github(
        GithubException(403, {"message": "nope"}, {"x-ratelimit-remaining": "0"})
    )
    assert isinstance(error, exc.RateLimitError)


def test_403_message_mentioning_rate_limit_is_rate_limit() -> None:
    error = from_github(GithubException(403, {"message": "API rate limit exceeded"}))
    assert isinstance(error, exc.RateLimitError)


def test_unknown_status_keeps_github_message_but_is_domain_error() -> None:
    error = from_github(GithubException(500, {"message": "boom"}))
    assert type(error) is exc.GhOrganizerError
    assert "boom" in error.user_message


def test_from_github_never_leaks_raw_exception_repr() -> None:
    error = from_github(GithubException(418, {"message": "teapot"}))
    assert "GithubException" not in error.user_message


# ---------------------------------------------------------------------- #
#  from_request / from_os_error / from_subprocess_error
# ---------------------------------------------------------------------- #
def test_request_exception_becomes_network_error() -> None:
    error = from_request(requests.exceptions.ConnectionError("dns"))
    assert isinstance(error, exc.NetworkError)


def test_os_permission_error_becomes_clone_permission_error() -> None:
    error = from_os_error(PermissionError(errno.EACCES, "denied"), "/tmp/x")
    assert isinstance(error, exc.ClonePermissionError)
    assert "/tmp/x" in error.user_message


def test_os_enospc_becomes_disk_space_error() -> None:
    error = from_os_error(OSError(errno.ENOSPC, "no space"))
    assert isinstance(error, exc.DiskSpaceError)


def test_os_generic_becomes_domain_error() -> None:
    error = from_os_error(OSError(errno.EIO, "io"), "context")
    assert type(error) is exc.GhOrganizerError


def test_subprocess_timeout_becomes_clone_timeout() -> None:
    error = from_subprocess_error(subprocess.TimeoutExpired(cmd="git", timeout=1))
    assert isinstance(error, exc.CloneTimeoutError)


def test_subprocess_generic_becomes_domain_error() -> None:
    error = from_subprocess_error(subprocess.SubprocessError("nope"))
    assert type(error) is exc.GhOrganizerError


def test_from_config_write_becomes_config_write_error() -> None:
    error = from_config_write(OSError(errno.EACCES, "denied"), "/tmp/config.toml")
    assert isinstance(error, exc.ConfigWriteError)
    assert "/tmp/config.toml" in error.user_message


# ---------------------------------------------------------------------- #
#  from_git_clone
# ---------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("stderr", "expected"),
    [
        ("fatal: No space left on device", exc.DiskSpaceError),
        ("error: Permission denied (publickey)", exc.ClonePermissionError),
        ("fatal: destination path 'x' already exists", exc.TargetExistsError),
        ("fatal: repository not found", exc.GitCloneFailedError),
    ],
)
def test_git_clone_stderr_mapping(stderr: str, expected: type) -> None:
    assert isinstance(from_git_clone(128, stderr, "/tmp/x"), expected)


def test_git_clone_empty_stderr_mentions_exit_code() -> None:
    error = from_git_clone(127, "", "/tmp/x")
    assert isinstance(error, exc.GitCloneFailedError)
    assert "127" in error.user_message


# ---------------------------------------------------------------------- #
#  github_errors (context manager)
# ---------------------------------------------------------------------- #
def test_github_errors_translates_and_chains() -> None:
    original = UnknownObjectException(404, {"message": "Not Found"})
    with pytest.raises(exc.RepoAccessError) as info, github_errors():
        raise original
    assert info.value.__cause__ is original


def test_github_errors_passes_domain_errors_through() -> None:
    original = exc.RateLimitError()
    with pytest.raises(exc.RateLimitError) as info, github_errors():
        raise original
    assert info.value is original


# ---------------------------------------------------------------------- #
#  GitHubClient traduce (sin red: se inyecta un doble)
# ---------------------------------------------------------------------- #
class _FakeUser:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def get_repos(self, **_kwargs):
        raise self._error


class _FakeGithub:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def get_user(self):
        return _FakeUser(self._error)

    def get_repo(self, _full_name: str):
        raise self._error

    def close(self) -> None:
        pass


def _client_with(error: Exception) -> GitHubClient:
    client = GitHubClient("ghp_fake_token")
    client._gh = _FakeGithub(error)  # type: ignore[assignment]
    return client


def test_client_list_repos_translates_401() -> None:
    client = _client_with(BadCredentialsException(401, {"message": "Bad"}))
    with pytest.raises(exc.InvalidTokenError):
        client.list_repos()


def test_client_verify_scope_translates_403() -> None:
    client = _client_with(GithubException(403, {"message": "Forbidden"}))
    with pytest.raises(exc.MissingScopeError):
        client.verify_repo_scope()


def test_client_get_recent_commits_includes_repo_name_on_404() -> None:
    client = _client_with(UnknownObjectException(404, {"message": "Not Found"}))
    with pytest.raises(exc.RepoAccessError) as info:
        client.get_recent_commits("user/private-repo")
    assert "user/private-repo" in info.value.user_message


def test_client_get_releases_translates_404() -> None:
    client = _client_with(UnknownObjectException(404, {"message": "Not Found"}))
    with pytest.raises(exc.RepoAccessError):
        client.get_releases("user/gone")


def test_client_close_never_raises() -> None:
    class Boom:
        def close(self) -> None:
            raise RuntimeError("boom")

    client = GitHubClient("ghp_fake_token")
    client._gh = Boom()  # type: ignore[assignment]
    client.close()  # no debe propagar


# ---------------------------------------------------------------------- #
#  services/git.py
# ---------------------------------------------------------------------- #
def test_clone_without_git_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(git_service.shutil, "which", lambda _name: None)
    with pytest.raises(exc.GitNotInstalledError):
        git_service.clone_repo("https://github.com/u/r.git", tmp_path / "r")


def test_clone_existing_target_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(git_service.shutil, "which", lambda _name: "git")
    target = tmp_path / "r"
    target.mkdir()
    with pytest.raises(exc.TargetExistsError) as info:
        git_service.clone_repo("https://github.com/u/r.git", target)
    assert str(target) in info.value.user_message


def test_clone_success_returns_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(git_service.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(
        git_service.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    target = tmp_path / "cloned"
    assert git_service.clone_repo("https://github.com/u/r.git", target) == target


def test_clone_failure_translates_stderr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(git_service.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(
        git_service.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=128, stdout="", stderr="fatal: repository not found"
        ),
    )
    with pytest.raises(exc.GitCloneFailedError) as info:
        git_service.clone_repo("https://github.com/u/r.git", tmp_path / "r")
    assert "repository not found" in info.value.user_message


def test_clone_timeout_raises_clone_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(git_service.shutil, "which", lambda _name: "git")

    def _timeout(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="git clone", timeout=300)

    monkeypatch.setattr(git_service.subprocess, "run", _timeout)
    with pytest.raises(exc.CloneTimeoutError):
        git_service.clone_repo("https://github.com/u/r.git", tmp_path / "r")


def test_clone_without_write_access_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(git_service.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(git_service.os, "access", lambda *_a: False)
    with pytest.raises(exc.ClonePermissionError):
        git_service.clone_repo("https://github.com/u/r.git", tmp_path / "r")


# ---------------------------------------------------------------------- #
#  services/config.py
# ---------------------------------------------------------------------- #
def test_config_save_error_becomes_config_write_error(
    tmp_data_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*_a, **_k):
        raise OSError(errno.EACCES, "denied")

    monkeypatch.setattr(config.tomli_w, "dump", _boom)
    with pytest.raises(exc.ConfigWriteError):
        config.save({"preferences": {}})


def test_corrupt_config_returns_defaults_and_reports(
    tmp_data_dirs: Path,
) -> None:
    config.CONFIG_FILE.write_text("esto [no es toml", encoding="utf-8")
    data = config.load()
    assert data["folders"] == {}
    error = config.consume_last_error()
    assert isinstance(error, exc.CorruptedConfigError)
    # El error se consume una sola vez
    assert config.consume_last_error() is None


def test_corrupt_config_is_backed_up(tmp_data_dirs: Path) -> None:
    config.CONFIG_FILE.write_text("esto [no es toml", encoding="utf-8")
    config.load()
    backups = list(config.CONFIG_FILE.parent.glob("config.toml.corrupt-*"))
    assert len(backups) == 1
    assert "no es toml" in backups[0].read_text(encoding="utf-8")


def test_missing_config_is_not_an_error(tmp_data_dirs: Path) -> None:
    config.load()
    assert config.consume_last_error() is None


# ---------------------------------------------------------------------- #
#  services/tokens.py
# ---------------------------------------------------------------------- #
def test_save_token_keyring_failure_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import keyring.errors

    def _fail(*_a, **_k):
        raise keyring.errors.KeyringError("no backend")

    monkeypatch.setattr(tokens.keyring, "set_password", _fail)
    with pytest.raises(exc.KeyringUnavailableError):
        tokens.save_token("ghp_x")


def test_save_token_success(monkeypatch: pytest.MonkeyPatch) -> None:
    stored: dict[str, str] = {}
    monkeypatch.setattr(
        tokens.keyring,
        "set_password",
        lambda service, user, value: stored.update({"token": value}),
    )
    tokens.save_token("ghp_x")
    assert stored["token"] == "ghp_x"


def test_load_token_keyring_failure_does_not_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import keyring.errors

    monkeypatch.delenv(tokens.TOKEN_ENV_VAR, raising=False)
    monkeypatch.setattr(tokens, "token_from_gh_cli", lambda: None)

    def _fail(*_a, **_k):
        raise keyring.errors.KeyringError("no backend")

    monkeypatch.setattr(tokens.keyring, "get_password", _fail)
    assert tokens.load_token() is None


def test_env_var_has_priority_over_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(tokens.TOKEN_ENV_VAR, "ghp_env")
    monkeypatch.setattr(tokens, "token_from_gh_cli", lambda: "ghp_cli")
    monkeypatch.setattr(tokens.keyring, "get_password", lambda *_a: "ghp_keyring")
    assert tokens.load_token() == "ghp_env"


def test_gh_cli_token_has_priority_over_keyring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(tokens.TOKEN_ENV_VAR, raising=False)
    monkeypatch.setattr(tokens, "token_from_gh_cli", lambda: "ghp_cli")
    monkeypatch.setattr(tokens.keyring, "get_password", lambda *_a: "ghp_keyring")
    assert tokens.load_token() == "ghp_cli"
