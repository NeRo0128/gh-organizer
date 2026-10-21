# src/gh_organizer/ui/widgets/__init__.py
"""Widgets reutilizables que componen las pantallas."""

from gh_organizer.ui.widgets.commits_panel import CommitsPanel
from gh_organizer.ui.widgets.releases_panel import ReleasesPanel
from gh_organizer.ui.widgets.repo_detail import RepoDetail
from gh_organizer.ui.widgets.repo_tree import (
    RepoActivated,
    RepoHighlighted,
    RepoTree,
)

__all__ = [
    "CommitsPanel",
    "ReleasesPanel",
    "RepoActivated",
    "RepoDetail",
    "RepoHighlighted",
    "RepoTree",
]
