# src/github_organizer/ui/widgets/__init__.py
"""Widgets reutilizables que componen las pantallas."""

from github_organizer.ui.widgets.commits_panel import CommitsPanel
from github_organizer.ui.widgets.releases_panel import ReleasesPanel
from github_organizer.ui.widgets.repo_detail import RepoDetail
from github_organizer.ui.widgets.repo_tree import (
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
