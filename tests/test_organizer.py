# tests/test_organizer.py
"""Tests de las estrategias de auto-organización."""

from github_organizer.core import Repo
from github_organizer.services.organizer import (
    STRATEGIES,
    by_language,
    by_language_and_visibility,
    by_visibility,
)


def test_by_language_groups_correctly(sample_repos: list[Repo]) -> None:
    result = by_language(sample_repos)
    assert set(result["Lenguajes/Python"]) == {"alpha", "beta"}
    assert result["Lenguajes/Go"] == ["gamma"]
    assert result["Lenguajes/Sin lenguaje"] == ["delta"]


def test_by_language_none_goes_to_sin_lenguaje() -> None:
    repos = [Repo(name="x", full_name="u/x", language=None)]
    assert by_language(repos) == {"Lenguajes/Sin lenguaje": ["x"]}


def test_by_language_empty_input() -> None:
    assert by_language([]) == {}


def test_by_visibility_splits(sample_repos: list[Repo]) -> None:
    result = by_visibility(sample_repos)
    assert set(result["Público"]) == {"alpha", "gamma"}
    assert set(result["Privado"]) == {"beta", "delta"}


def test_by_visibility_omits_empty_categories() -> None:
    repos = [Repo(name="pub", full_name="u/pub", private=False)]
    assert by_visibility(repos) == {"Público": ["pub"]}


def test_by_visibility_empty_input() -> None:
    assert by_visibility([]) == {}


def test_by_language_and_visibility(sample_repos: list[Repo]) -> None:
    result = by_language_and_visibility(sample_repos)
    assert result["Públicos/Python"] == ["alpha"]
    assert result["Privados/Python"] == ["beta"]
    assert result["Públicos/Go"] == ["gamma"]
    assert result["Privados/Sin lenguaje"] == ["delta"]


def test_strategies_registry_shape() -> None:
    assert len(STRATEGIES) == 3
    for name, fn, desc in STRATEGIES:
        assert isinstance(name, str) and name
        assert callable(fn)
        assert isinstance(desc, str) and desc


def test_strategies_do_not_mutate_input(sample_repos: list[Repo]) -> None:
    original = list(sample_repos)
    by_language(sample_repos)
    by_visibility(sample_repos)
    by_language_and_visibility(sample_repos)
    assert sample_repos == original


def test_strategies_include_expected_names() -> None:
    names = [s[0] for s in STRATEGIES]
    assert "Por lenguaje" in names
    assert "Por visibilidad" in names
    assert "Visibilidad + lenguaje" in names
